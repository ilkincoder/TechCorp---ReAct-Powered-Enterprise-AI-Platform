"""TechCorp Enterprise AI Platform — FastAPI Application.

   Architecture: User → Planner Agent → Select Tools
   → (RAG | SQL | Python | Web Search | Email | Calendar | Memory)
   → Combine Results → Grounded Answer + Citations
"""

import asyncio
import json
import re
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .tools import get_tool_schemas, get_tool_map
from .agent import PlannerAgent, ReActLoop, ResultCombiner
from .agent.planner import ROLE_PERMISSIONS, _ALL_KB_DEPARTMENTS
from .agent.rbac import apply_rbac
from .agent.tool_adapter import summarize_result as _summarize_result
from .agent.plan_schema import validate_plan
from .conversations import (
    init_conversation_tables,
    init_memory_table,
    init_reports_table,
    create_conversation,
    save_message,
    list_conversations,
    get_conversation,
    delete_conversation,
    get_context_window,
    get_all_messages_for_summary,
    update_conversation_summary,
    get_conversation_summary,
    count_messages,
    get_conversation_title,
    get_reports,
    get_report,
    update_report,
)
from .config import (
    DEEPSEEK_MODEL,
    LANGSMITH_TRACING, LANGSMITH_API_KEY, LANGSMITH_PROJECT,
    get_openai_client,
)


app = FastAPI(
    title="TechCorp Enterprise AI Platform",
    description="AI Employee that reasons about problems and chooses the correct tools.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global instances ──────────────────────────────────────────────────────

planner = PlannerAgent()
combiner = ResultCombiner()
react_loop = ReActLoop()
tool_map = get_tool_map()
tool_schemas = get_tool_schemas()

# Report generation runs get a higher tool-turn budget than regular queries.
REPORT_MAX_ITERATIONS = 10


def _build_schema_context() -> str:
    """Build a summary of available data for the planner — tables with columns."""
    from pathlib import Path
    import csv as csv_mod
    from .config import KB_DIR, DATA_DIR

    parts = []

    # Knowledge base departments
    kb_dir = KB_DIR
    if kb_dir.exists():
        depts = sorted(
            d.name for d in kb_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
        if depts:
            parts.append(
                f"**Knowledge Base departments** ({len(depts)}): "
                + ", ".join(depts)
            )

    # Database tables with columns
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if csv_files:
        table_lines = []
        for csv_path in csv_files:
            table_name = csv_path.stem.replace("-", "_").replace(" ", "_").lower()
            try:
                with open(csv_path, newline="") as f:
                    reader = csv_mod.DictReader(f)
                    if reader.fieldnames:
                        cols = [
                            c.replace("-", "_").replace(" ", "_").lower().strip("_")
                            for c in reader.fieldnames
                        ]
                        table_lines.append(f"    {table_name}: {', '.join(cols)}")
                    else:
                        table_lines.append(f"    {table_name}")
            except Exception:
                table_lines.append(f"    {table_name}")
        parts.append(
            f"**Database tables with columns** ({len(csv_files)}):\n"
            + "\n".join(table_lines)
        )

    return "\n".join(parts) if parts else ""


schema_context = _build_schema_context()

# ── RBAC pre-check: keyword → department mapping for restricted queries ──────

_RESTRICTED_TOPICS: dict[str, list[str]] = {
    'HR': ['code of conduct', 'employee handbook', 'onboarding', 'travel policy',
           'expense policy', 'hr policy', 'human resources'],
    'Finance': ['budget', 'forecast', 'expense report', 'finance policy',
                'audit report', 'financial', 'salary', 'compensation'],
    'Legal': ['compliance', 'contract', 'legal', 'regulation', 'ip policy',
              'data usage', 'governance'],
}

# Keywords that map to restricted tables
_RESTRICTED_TABLE_TERMS: dict[str, list[str]] = {
    'employees': ['employee', 'salary', 'salaries', 'manager', 'hire date', 'job title'],
    'incident_reports': ['incident', 'p1 incident', 'p2 incident', 'p3 incident', 'root cause'],
    'audit_logs': ['audit log', 'audit trail'],
    'internal_emails': ['internal email', 'sender', 'recipient'],
}


def _check_restricted_query(message: str, role: str) -> str | None:
    """Return a refusal reason if the query targets a restricted department or table.

    Returns None if the query is allowed. This is a hard pre-check — the LLM
    is never called for clearly out-of-scope queries.
    """
    perms = ROLE_PERMISSIONS.get(role, {})
    allowed_depts = perms.get('allowed_departments')
    allowed_tables = perms.get('allowed_tables')
    forbidden_tables = perms.get('forbidden_tables', [])
    forbidden_depts = perms.get('forbidden_departments', [])

    msg_lower = message.lower()

    # ── Check restricted SQL table keywords ──
    if allowed_tables:
        # support_agent: explicit allowlist — block keywords for non-allowed tables
        for table, terms in _RESTRICTED_TABLE_TERMS.items():
            if table not in allowed_tables:
                for term in terms:
                    if term in msg_lower:
                        return (
                            f"'{term}' relates to the {table} table, "
                            f"which is outside your access scope."
                        )
    elif forbidden_tables:
        # sales_intern: blocklist — block keywords for forbidden tables
        for table in forbidden_tables:
            for term in _RESTRICTED_TABLE_TERMS.get(table, [table]):
                if term in msg_lower:
                    return (
                        f"'{term}' relates to the {table} table, "
                        f"which is outside your access scope."
                    )

    # ── Check explicit department mentions ──
    for dept in forbidden_depts:
        if dept.lower() in msg_lower:
            return f"The {dept} department is outside your access scope."

    if allowed_depts:
        for dept in _ALL_KB_DEPARTMENTS:
            if dept not in allowed_depts and dept.lower() in msg_lower:
                return f"The {dept} department is outside your access scope."

    # ── Check department topic keywords ──
    restricted_depts = set(forbidden_depts) if forbidden_depts else set(_ALL_KB_DEPARTMENTS) - set(allowed_depts or [])
    for dept in restricted_depts:
        keywords = _RESTRICTED_TOPICS.get(dept, [])
        for kw in keywords:
            if kw in msg_lower:
                return f"'{kw}' relates to the {dept} department, which is outside your access scope."

    return None


# ── Models ─────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    message: str
    session_id: str | None = None
    role: str | None = None
    tool: str | None = None  # UI tool picker — force a specific tool for this query


# ── Startup ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Initialize conversation tables and memory collection on startup."""
    try:
        init_conversation_tables()
        init_memory_table()
        init_reports_table()
    except Exception as e:
        print(f"[startup] Could not init conversation tables: {e}")
    try:
        from .tools.memory_tool import MemoryTool
        MemoryTool()._ensure_memory_collection()
    except Exception as e:
        print(f"[startup] Could not init memory Qdrant collection: {e}")

    # LangSmith tracing status (tracing is applied per-client in config.py)
    if LANGSMITH_TRACING and LANGSMITH_API_KEY:
        print(f"[startup] LangSmith tracing enabled — project: {LANGSMITH_PROJECT}")
    else:
        print("[startup] LangSmith tracing disabled")


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "TechCorp Enterprise AI Platform",
        "version": "1.0.0",
        "architecture": "User → Planner Agent → Select Tools → Combine → Grounded Answer + Citations",
        "tools": [t["name"] for t in tool_schemas],
        "endpoints": {
            "POST /query/stream": "Send a query to the AI employee (SSE stream)",
            "GET /tools": "List all available tools",
            "GET /tools/{name}": "Get tool schema and status",
            "GET /health": "Health check",
        },
    }


async def _maybe_summarize(conversation_id: str, message_count: int) -> None:
    """Regenerate conversation summary every 6 messages, or when missing.

    Summarizes all messages except the last 3 using an LLM call.
    Runs asynchronously — failures are non-blocking but logged.
    """
    if message_count < 6:
        return

    # Trigger at normal cadence (every 6 msgs) OR when summary is missing (catch-up)
    if message_count % 6 != 0:
        existing = get_conversation_summary(conversation_id)
        if existing:
            return  # Summary exists, wait for next cadence point

    try:
        older = get_all_messages_for_summary(conversation_id, exclude_last=3)
        if not older:
            return

        # Build conversation transcript
        transcript = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:400]}"
            for m in older
        )

        prompt = (
            "Summarize the key facts, decisions, and context from this conversation. "
            "Be concise. Include: user preferences, named entities (people, projects), "
            "deadlines, project details, and any information the user explicitly shared. "
            "Exclude trivial greetings and tool-selection mechanics.\n\n"
            f"{transcript}\n\nSummary:"
        )

        client = get_openai_client()
        response = await asyncio.to_thread(
            lambda: client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": "You are a conversation summarizer. Write a concise, factual summary in 2-4 sentences."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=512,
                temperature=0.1,
            )
        )
        summary = (response.choices[0].message.content or "").strip()
        if summary:
            update_conversation_summary(conversation_id, summary)
    except Exception as e:
        print(f"[summarize] Failed for conversation {conversation_id}: {type(e).__name__}: {e}", flush=True)


@app.post("/query/stream")
async def query_stream(req: QueryRequest):
    """Streaming endpoint — SSE events for real-time AI response."""

    async def event_generator():
        conversation_id = req.session_id
        full_answer = ""
        all_sources = []
        all_tools_used = []
        intent = ""
        # Approval-flow marker: the Approve button sends "Generate report #N: ..."
        report_match = re.match(r"^Generate report #(\d+)", req.message or "")
        report_buffer: list[str] = []
        briefing_ok = False
        # UI tool picker: force a specific tool (ignored for report approvals —
        # briefing execution needs the full toolset; unknown names ignored)
        forced_tool = req.tool if (req.tool in tool_map and not report_match) else None

        try:
            # Create conversation if not provided
            if not conversation_id:
                conversation_id = create_conversation()
                yield _sse("meta", {"conversation_id": conversation_id})

            # Save user message
            save_message(conversation_id, "user", req.message)

            # Phase 0: RBAC pre-check — catch restricted-department queries
            # before the LLM runs so restricted roles can't search HR/Finance/Legal
            if req.role and req.role != 'engineering_admin':
                restricted = _check_restricted_query(req.message, req.role)
                if restricted:
                    yield _sse("plan", {
                        "intent": "Query blocked by access control",
                        "tools_needed": [],
                        "reasoning": restricted,
                        "steps": [],
                    })
                    refusal = (
                        f"I'm unable to help with that request. {restricted} "
                        f"As a {ROLE_PERMISSIONS.get(req.role, {}).get('label', req.role)}, "
                        f"this information is outside your access scope."
                    )
                    full_answer = refusal
                    yield _sse("token", {"text": refusal})
                    save_message(conversation_id, "assistant", full_answer, intent="Query blocked by access control")
                    save_message(conversation_id, "system",
                        f"[Access blocked for {ROLE_PERMISSIONS.get(req.role, {}).get('label', req.role)}: {restricted}]")
                    yield _sse("done", {
                        "conversation_id": conversation_id,
                        "title": get_conversation_title(conversation_id),
                        "intent": "Query blocked by access control",
                        "tools_used": [],
                    })
                    return

            # Phase 1: Tier-1 fast plan (deterministic, no LLM) or ReAct loop.
            # An explicit tool selection outranks the Tier-1 heuristics.
            ctx = get_context_window(conversation_id, recent_limit=3)
            plan = None if forced_tool else planner.fast_plan(req.message, conversation_history=ctx["recent"])

            if plan is not None:
                # ── Deterministic branch: Tier-1 plan → tools → combiner ──
                intent = plan.intent
                tools_to_use = plan.tools_needed
                queries = plan.queries

                # Handle unintelligible input — no tools to execute, respond gracefully
                if not tools_to_use:
                    yield _sse("plan", {
                        "intent": intent,
                        "tools_needed": [],
                        "reasoning": plan.reasoning,
                        "steps": [],
                    })
                    graceful_msg = "I couldn't understand that. Could you rephrase your question?"
                    full_answer = graceful_msg
                    yield _sse("token", {"text": graceful_msg})
                    save_message(conversation_id, "assistant", full_answer, intent=intent)
                    yield _sse("done", {
                        "conversation_id": conversation_id,
                        "title": get_conversation_title(conversation_id),
                        "intent": intent,
                        "tools_used": [],
                    })
                    return

                # Validate plan and surface issues
                is_valid, validation_errors, validation_warnings = validate_plan(plan, tool_map)
                if validation_warnings:
                    yield _sse("validation_warning", {"warnings": validation_warnings})
                if validation_errors:
                    yield _sse("validation_error", {"errors": validation_errors})
                    # Filter out invalid tools, keep valid ones
                    tools_to_use = [t for t in tools_to_use if t in tool_map]
                    if not tools_to_use:
                        yield _sse("error", {"message": f"Plan validation failed: {'; '.join(validation_errors)}"})
                        return

                yield _sse("plan", {
                    "intent": intent,
                    "tools_needed": tools_to_use,
                    "reasoning": plan.reasoning,
                    "steps": [s.to_dict() for s in plan.steps],
                })

                if plan.reasoning:
                    yield _sse("reasoning", {"text": plan.reasoning})

                # Phase 2: Act — execute the Tier-1 plan's tools
                results = []
                for tool_name in tools_to_use:
                    tool = tool_map.get(tool_name)
                    if not tool:
                        continue

                    yield _sse("tool_start", {"tool": tool_name})

                    params = queries.get(tool_name, {})

                    # Pre-query disambiguation: probe for ambiguous name-based queries
                    if tool_name == "sql_query":
                        query_text = params.get("query", "")
                        sql_tool = tool_map.get("sql_query")
                        if sql_tool and query_text:
                            ambiguity = await _check_name_ambiguity(query_text, sql_tool)
                            if ambiguity:
                                yield _sse("tool_result", {
                                    "tool": tool_name,
                                    "success": False,
                                    "summary": f"Ambiguous — {len(ambiguity['options'])} matches found",
                                })
                                yield _sse("disambiguate", ambiguity)
                                return  # Stop — wait for user to select

                    # ── RBAC hard gates (RAG department filter + SQL table gate) ──
                    params, denial = apply_rbac(tool_name, params, req.role)
                    if denial:
                        yield _sse("tool_result", {
                            "tool": tool_name,
                            "success": False,
                            "summary": denial,
                        })
                        all_tools_used.append(tool_name)
                        results.append({
                            "tool_name": tool_name,
                            "success": False,
                            "error": denial,
                        })
                        save_message(conversation_id, "system", f"[Access blocked: {denial}]")
                        continue

                    result = await tool.execute(**params)
                    result_dict = result.to_dict()
                    results.append(result_dict)
                    all_tools_used.append(tool_name)

                    result_event = {
                        "tool": tool_name,
                        "success": result.success,
                        "summary": _summarize_result(result_dict),
                    }
                    report_data = result_dict.get("data") or {}
                    if isinstance(report_data, dict) and report_data.get("requires_approval"):
                        result_event["requires_approval"] = True
                        result_event["report_id"] = report_data.get("report_id")
                        result_event["title"] = report_data.get("title")
                        result_event["description"] = report_data.get("description")
                        result_event["sections"] = report_data.get("sections", [])
                        result_event["data_sources"] = report_data.get("data_sources", [])
                    yield _sse("tool_result", result_event)

                    if not result.success:
                        continue

                    # Extract citations
                    if result_dict.get("citations"):
                        for c in result_dict["citations"]:
                            all_sources.append({"tool": tool_name, "citation": c})

                # Phase 3: Stream the combined answer
                yield _sse("sources", {"sources": all_sources})

                async for token_chunk in combiner.combine_stream(
                    user_message=req.message,
                    tool_results=results,
                    intent=intent,
                    conversation_history=ctx["recent"],
                    summary=ctx["summary"],
                    role=req.role,
                ):
                    full_answer += token_chunk
                    yield _sse("token", {"text": token_chunk})

            else:
                # ── ReAct branch: native tool-calling loop drives everything ──
                sql_tool = tool_map.get("sql_query")

                async def _ambiguity_checker(query_text: str):
                    if sql_tool and query_text:
                        return await _check_name_ambiguity(query_text, sql_tool)
                    return None

                react_failed = False
                run_schemas = (
                    [s for s in tool_schemas if s["name"] == forced_tool]
                    if forced_tool else tool_schemas
                )
                async for ev in react_loop.run_stream(
                    req.message,
                    run_schemas,
                    schema_context,
                    conversation_history=ctx["recent"],
                    summary=ctx["summary"],
                    role=req.role,
                    ambiguity_checker=_ambiguity_checker,
                    max_iterations=REPORT_MAX_ITERATIONS if report_match else None,
                    forced_tool=forced_tool,
                ):
                    kind, payload = ev.kind, ev.payload

                    # Internal-only events — never forwarded as SSE
                    if kind == "system_note":
                        save_message(conversation_id, "system", payload.get("text", ""))
                        continue
                    if kind == "fallback":
                        react_failed = True
                        break
                    if kind == "fallback_stream":
                        # Final turn failed mid-loop — synthesize via combiner
                        async for token_chunk in combiner.combine_stream(
                            user_message=req.message,
                            tool_results=payload.get("results", []),
                            intent=intent,
                            conversation_history=ctx["recent"],
                            summary=ctx["summary"],
                            role=req.role,
                        ):
                            full_answer += token_chunk
                            yield _sse("token", {"text": token_chunk})
                        break

                    # Bookkeeping from forwarded events
                    if kind == "plan":
                        intent = payload.get("intent", "")
                    elif kind == "sources":
                        all_sources = payload.get("sources", [])
                    elif kind == "token":
                        if report_match:
                            # Report runs: the answer IS the report — hold it
                            # back from chat; it is persisted to the reports
                            # table after the loop completes.
                            report_buffer.append(payload.get("text", ""))
                            continue
                        full_answer += payload.get("text", "")
                    elif kind == "tool_start":
                        all_tools_used.append(payload.get("tool", ""))
                    elif kind == "tool_result":
                        if (
                            payload.get("tool") == "report_generator"
                            and payload.get("success")
                            and not payload.get("requires_approval")
                        ):
                            # Briefing accepted — acknowledge in chat
                            briefing_ok = True
                            ack = "✅ Report approved — generating the report now…\n\n"
                            full_answer += ack
                            yield _sse(kind, payload)
                            yield _sse("token", {"text": ack})
                            continue

                    yield _sse(kind, payload)

                    if kind == "disambiguate":
                        return  # Stop — wait for user to select

                if react_failed:
                    # Turn-1 LLM failure — deterministic fallback: RAG + combiner
                    intent = req.message
                    yield _sse("plan", {
                        "intent": intent,
                        "tools_needed": ["rag_search"],
                        "reasoning": "Agent loop unavailable — falling back to knowledge base search.",
                        "steps": [{
                            "tool": "rag_search", "goal": "Search knowledge base",
                            "params": {"query": req.message}, "status": "pending",
                            "execution_time_ms": None, "error": "",
                        }],
                    })
                    results = []
                    rag_tool = tool_map.get("rag_search")
                    if rag_tool:
                        yield _sse("tool_start", {"tool": "rag_search"})
                        params, _ = apply_rbac("rag_search", {"query": req.message}, req.role)
                        result = await rag_tool.execute(**params)
                        result_dict = result.to_dict()
                        results.append(result_dict)
                        all_tools_used.append("rag_search")
                        yield _sse("tool_result", {
                            "tool": "rag_search",
                            "success": result.success,
                            "summary": _summarize_result(result_dict),
                        })
                        if result.success:
                            for c in result_dict.get("citations") or []:
                                all_sources.append({"tool": "rag_search", "citation": c})
                    yield _sse("sources", {"sources": all_sources})
                    async for token_chunk in combiner.combine_stream(
                        user_message=req.message,
                        tool_results=results,
                        intent=intent,
                        conversation_history=ctx["recent"],
                        summary=ctx["summary"],
                        role=req.role,
                    ):
                        full_answer += token_chunk
                        yield _sse("token", {"text": token_chunk})

                # Dedupe tool usage (loop may start the same tool across turns)
                all_tools_used = list(dict.fromkeys(t for t in all_tools_used if t))

            # Report runs: persist the held-back report, notify in chat
            buffered = "".join(report_buffer)
            if report_match and briefing_ok and buffered:
                report_id = int(report_match.group(1))
                try:
                    await update_report(report_id, content=buffered, status="completed")
                except Exception:
                    pass  # non-critical
                notice = f"Report #{report_id} is ready — please check the Reports section for the final version."
                full_answer += notice
                yield _sse("token", {"text": notice})
            elif report_match and buffered:
                # Briefing failed — the model's explanation was held back; flush it
                full_answer += buffered
                yield _sse("token", {"text": buffered})

            # Save assistant message
            save_message(
                conversation_id,
                "assistant",
                full_answer,
                sources=all_sources,
                tools_used=all_tools_used,
                intent=intent,
            )

            # Regenerate conversation summary periodically (every 6 messages)
            try:
                msg_count = count_messages(conversation_id)
                await _maybe_summarize(conversation_id, msg_count)
            except Exception:
                pass  # non-critical

            yield _sse("done", {
                "conversation_id": conversation_id,
                "title": get_conversation_title(conversation_id),
                "intent": intent,
                "tools_used": all_tools_used,
            })

        except Exception as e:
            # Save partial answer if any
            if full_answer:
                try:
                    save_message(
                        conversation_id,
                        "assistant",
                        full_answer,
                        sources=all_sources,
                        tools_used=all_tools_used,
                        intent=intent,
                    )
                except Exception:
                    pass
            yield _sse("error", {"message": "I'm sorry — the system is currently unavailable. Please try again in a moment."})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(event: str, data: dict) -> str:
    """Format a Server-Sent Event line."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _check_name_ambiguity(query_text: str, sql_tool) -> dict | None:
    """Pre-query disambiguation: probe if the SQL filters employees by name.

    Extracts name literals from =, LIKE, or ILIKE on first_name / last_name
    columns, then checks how many employees match. If > 1, the query is
    ambiguous and the user should pick.

    Returns {"field": str, "query": str, "options": [...]} for disambiguation,
    or None if unambiguous (0-1 matches or no name-based filter detected).
    """
    import re

    # Extract name literals from: first_name [= LIKE ILIKE] 'Name'
    # Handles table-qualified columns (e.first_name) and plain (first_name)
    patterns = re.findall(
        r"(?:\w+\.)?\bfirst_name\b\s*(?:NOT\s+)?(?:I?LIKE|~~\*?|=)\s*'([^']*)'",
        query_text, re.IGNORECASE,
    )
    patterns += re.findall(
        r"(?:\w+\.)?\blast_name\b\s*(?:NOT\s+)?(?:I?LIKE|~~\*?|=)\s*'([^']*)'",
        query_text, re.IGNORECASE,
    )

    if not patterns:
        return None

    # Clean captured fragments (strip % wildcards, trim whitespace)
    search_term = " ".join(p.replace("%", "").strip() for p in patterns)

    # Parameterized probe — the term comes from user input, so it is bound via
    # %s placeholders (never interpolated) with ILIKE wildcards escaped.
    escaped = (
        search_term.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    )
    pattern = f"%{escaped}%"
    probe = (
        "SELECT e.employee_id, e.first_name, e.last_name, e.job_title, "
        "(SELECT d.department_name FROM departments d "
        " WHERE d.department_id = e.department_id) AS department_name "
        "FROM employees e "
        "WHERE e.first_name ILIKE %s "
        "   OR e.last_name ILIKE %s "
        "ORDER BY e.employee_id"
    )
    result = await sql_tool.execute(query=probe, params=(pattern, pattern))
    if not result.success:
        return None

    rows = (result.data or {}).get("rows", [])
    if len(rows) <= 1:
        return None

    return {
        "field": "employee_name",
        "query": search_term,
        "options": rows,
    }




@app.get("/dashboard/stats")
async def dashboard_stats():
    """Return live stats for the dashboard cards from PostgreSQL."""
    sql_tool = tool_map.get("sql_query")
    if not sql_tool:
        raise HTTPException(status_code=500, detail="SQL tool not available")

    try:
        # Incidents: open count, critical (P1) count, latest title
        incidents_open = await sql_tool.execute(
            "SELECT COUNT(*) as count FROM incident_reports WHERE status IN ('Investigating', 'In Progress')"
        )
        incidents_critical = await sql_tool.execute(
            "SELECT COUNT(*) as count FROM incident_reports WHERE severity = 'P1' AND status NOT IN ('Resolved', 'Closed')"
        )
        incidents_latest = await sql_tool.execute(
            "SELECT title, created_at FROM incident_reports ORDER BY created_at DESC LIMIT 1"
        )

        # Tickets: by status
        tickets = await sql_tool.execute(
            "SELECT status, COUNT(*) as count FROM support_tickets GROUP BY status ORDER BY count DESC"
        )

        # Projects: by status
        projects = await sql_tool.execute(
            "SELECT status, COUNT(*) as count FROM projects GROUP BY status"
        )

        # Subscriptions: by status
        subscriptions = await sql_tool.execute(
            "SELECT status, COUNT(*) as count FROM subscriptions GROUP BY status"
        )

        # Employees: total + departments
        employees = await sql_tool.execute(
            "SELECT COUNT(*) as count FROM employees"
        )
        departments = await sql_tool.execute(
            "SELECT COUNT(*) as count FROM departments"
        )

        # ── Detail lists for modal views ──────────────────────────────────

        incidents_list = await sql_tool.execute(
            "SELECT title, severity, status, created_at FROM incident_reports "
            "WHERE status NOT IN ('Resolved', 'Closed') "
            "ORDER BY CASE severity WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 WHEN 'P3' THEN 3 ELSE 4 END, created_at DESC LIMIT 10"
        )
        tickets_list = await sql_tool.execute(
            "SELECT subject AS title, priority, status, created_date AS created_at FROM support_tickets "
            "WHERE status NOT IN ('Closed') "
            "ORDER BY CASE priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, created_date DESC LIMIT 10"
        )
        projects_list = await sql_tool.execute(
            "SELECT p.project_id AS id, p.project_name AS name, p.status, "
            "e.first_name || ' ' || e.last_name AS owner, p.start_date, p.end_date "
            "FROM projects p LEFT JOIN employees e ON p.lead_employee_id = e.employee_id "
            "ORDER BY CASE p.status WHEN 'In Progress' THEN 1 WHEN 'Planning' THEN 2 ELSE 3 END, p.project_name LIMIT 20"
        )
        subscriptions_list = await sql_tool.execute(
            "SELECT s.subscription_id, s.status, p.product_name AS plan_type "
            "FROM subscriptions s LEFT JOIN products p ON s.product_id = p.product_id "
            "ORDER BY s.status, p.product_name LIMIT 20"
        )
        departments_list = await sql_tool.execute(
            "SELECT d.department_name, COUNT(e.employee_id) AS headcount "
            "FROM departments d LEFT JOIN employees e ON e.department_id = d.department_id "
            "GROUP BY d.department_name ORDER BY headcount DESC"
        )

        # Severity breakdown for open incidents
        severity_breakdown = await sql_tool.execute(
            "SELECT severity, COUNT(*) as count FROM incident_reports "
            "WHERE status NOT IN ('Resolved', 'Closed') "
            "GROUP BY severity ORDER BY severity"
        )

        # ── Build response ──────────────────────────────────────────────

        def _extract_count(result) -> int:
            rows = (result.data or {}).get("rows", [])
            if rows:
                return int(list(rows[0].values())[0])
            return 0

        def _extract_status_map(result) -> dict:
            rows = (result.data or {}).get("rows", [])
            return {r.get("status", "Unknown"): int(r.get("count", 0)) for r in rows}

        def _extract_rows(result) -> list:
            return (result.data or {}).get("rows", [])

        def _project_progress(row) -> int:
            """Derive progress % from elapsed time between start and end dates."""
            status = row.get("status", "")
            if status == "Completed":
                return 100
            if status == "Planning":
                return 0
            try:
                start = date.fromisoformat(str(row.get("start_date"))[:10])
                end = date.fromisoformat(str(row.get("end_date"))[:10])
            except (TypeError, ValueError):
                return 0
            total_days = (end - start).days
            if total_days <= 0:
                return 0
            elapsed = (date.today() - start).days
            return max(0, min(100, round(elapsed / total_days * 100)))

        project_rows = [
            {
                "id": r.get("id"),
                "name": r.get("name", ""),
                "status": r.get("status", ""),
                "owner": r.get("owner") or "",
                "progress": _project_progress(r),
                "dueDate": str(r["end_date"])[:10] if r.get("end_date") else None,
            }
            for r in _extract_rows(projects_list)
        ]

        latest_rows = (incidents_latest.data or {}).get("rows", [])
        latest_incident = latest_rows[0] if latest_rows else {}

        def _extract_severity_map(result) -> dict:
            rows = (result.data or {}).get("rows", [])
            return {r.get("severity", "Unknown"): int(r.get("count", 0)) for r in rows}

        inc_open = _extract_count(incidents_open)
        tix_map = _extract_status_map(tickets)
        tix_open = tix_map.get("Open", 0)
        proj_map = _extract_status_map(projects)
        sub_map = _extract_status_map(subscriptions)
        sub_total = sum(sub_map.values())

        return {
            "incidents": {
                "open": inc_open,
                "critical": _extract_count(incidents_critical),
                "latest_title": latest_incident.get("title", ""),
                "latest_time": latest_incident.get("created_at", ""),
                "bySeverity": _extract_severity_map(severity_breakdown),
                "list": _extract_rows(incidents_list),
            },
            "tickets": {
                **{k: v for k, v in tix_map.items() if k != "list"},
                "list": _extract_rows(tickets_list),
            },
            "projects": {
                **{k: v for k, v in proj_map.items() if k != "list"},
                "list": project_rows,
            },
            "subscriptions": {
                **{k: v for k, v in sub_map.items() if k != "list"},
                "total": sub_total,
                "list": _extract_rows(subscriptions_list),
            },
            "employees": {
                "total": _extract_count(employees),
                "departments": _extract_count(departments),
                "departmentNames": [r.get("department_name", "") for r in _extract_rows(departments_list)],
                "list": _extract_rows(departments_list),
            },
            "itemsNeedAttention": inc_open + tix_open,
            "projectsInFlight": proj_map.get("In Progress", 0) + proj_map.get("Planning", 0),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations")
async def list_convs():
    """List all conversations."""
    return {"conversations": list_conversations()}


@app.post("/conversations")
async def create_conv():
    """Create a new conversation."""
    conv_id = create_conversation()
    return {"id": conv_id, "title": "New Chat"}


@app.get("/conversations/{conv_id}")
async def get_conv(conv_id: str):
    """Get a conversation with all its messages."""
    conv = get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@app.delete("/conversations/{conv_id}")
async def delete_conv(conv_id: str):
    """Delete a conversation and its messages."""
    deleted = delete_conversation(conv_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}


@app.get("/reports")
async def list_reports():
    """List all generated reports, newest first."""
    try:
        reports = await get_reports(limit=20)
        return {"reports": reports}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports/{report_id}")
async def get_report_endpoint(report_id: int):
    """Get a single report by ID with full content."""
    try:
        report = await get_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools")
async def list_tools():
    """List all available tools with their schemas."""
    return {
        "tools": [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["input_schema"],
            }
            for t in tool_schemas
        ]
    }


@app.get("/tools/{name}")
async def get_tool(name: str):
    """Get a specific tool's schema."""
    tool = tool_map.get(name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    return {"name": name, "schema": tool.schema()}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "tools_available": len(tool_map)}

