"""ReAct Loop — Think → Act → Observe → Reflect, via native tool calling.

The model drives the loop: each turn it either emits tool_calls (executed
here, observations appended as role:"tool" messages) or streams the final
answer. Observations from step N ground the parameters of step N+1.
"""

import asyncio
from dataclasses import dataclass

from openai import AsyncOpenAI

from ..config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL
from ..tools import get_tool_map
from .combiner import COMBINER_GROUNDING_RULES
from .rbac import apply_rbac, _build_role_context
from .tool_adapter import to_openai_tools, serialize_observation, summarize_result
from .tool_params import validate_tool_args


@dataclass
class LoopEvent:
    """Internal event emitted by run_stream(); app.py maps kinds onto SSE events.

    Kinds mirroring SSE events: plan, plan_step, reasoning, validation_warning,
    tool_start, tool_result, tool_retry, tool_retry_failed, disambiguate,
    sources, token.
    Internal-only kinds (not forwarded as SSE): system_note (save as a system
    message), fallback (turn-1 LLM failure — caller should fall back to the
    deterministic path).
    """
    kind: str
    payload: dict


AGENT_SYSTEM_PROMPT = """You are the TechCorp Enterprise AI assistant — an agent that answers
user questions by calling tools and synthesizing their results into a grounded, cited answer.

## Routing Guidelines
- Questions about company policies, procedures, standards, compliance, how-to guides → **rag_search**
- Questions about people (employees, who leads, who manages), counts (how many), lists of things,
  customers, tickets, projects, incidents, meetings, emails, Slack messages → **sql_query**
- Data analysis, calculations, charts, statistics → **python_execute**
- External events, competitors, industry news, current affairs → **web_search**
- Enterprise context previously stored (project details, deadlines, budgets, team assignments,
  meeting decisions, vendor/customer info) → **memory** with action "search". This includes
  questions with "I", "my", "me", "we", "our".
- If the user is sharing business information rather than asking a question → **memory** with
  action "store".
- If the user asks to generate, create, or make a NEW report, summary document, or dashboard →
  **report_generator** with action "propose" and the request as `query`. Do NOT manually combine
  SQL + Python + RAG for reports.
- APPROVAL CALLBACK — CRITICAL: a message starting with "Generate report #<id>" (sent by the UI's
  Approve button), or a bare "yes"/"approve"/"go ahead" immediately after a report proposal →
  **report_generator** with action "generate" and report_id=<id> (taken from the message, or from
  the most recent proposal). NEVER call "propose" for these messages — re-proposing an already
  approved report is an error. The "generate" call returns an EXECUTION BRIEFING: follow it
  exactly — batch all its sql_queries as parallel sql_query calls in ONE turn, run the other
  searches it specifies, then write the final answer as the complete report in Markdown ONLY
  (title heading, one section per listed section, report_date as the date, no text outside
  the report). The finished report is saved to the Reports section automatically and is NOT
  shown in chat — so the final answer must be the report itself, nothing else.
- Meta-questions about available tools or platform capabilities → answer directly from this prompt.

## SQL Generation — CRITICAL
When the user asks for specific data (columns, fields, entities), include those exact field
names in the SQL — even if they don't appear in the schema below. Do NOT silently drop
requested fields — a query that fails with "column does not exist" is BETTER than a query
that silently omits what the user asked for; you will see the error and can try a different
approach (e.g. probing information_schema.columns). Never use SELECT * — always list specific
columns. Only SELECT statements are allowed — never INSERT, UPDATE, DELETE, or DROP.

## Available Data
{schema_context}

## How to work
1. Before your FIRST tool call, state your goal in one short sentence, then call the tool(s).
2. After each tool result, decide: call more tools (you may use results from earlier steps to
   build the next call's parameters), or write the final answer.
3. If a tool fails, try a DIFFERENT approach — do not repeat the same call. If a SQL query
   fails twice, stop retrying and explain what data is unavailable.
4. When you have what you need, write the final answer following these rules:
{grounding_rules}
"""

# After this many characters of leading content with no tool_calls, treat the
# turn as the final answer and start streaming tokens immediately.
_ANSWER_BUFFER_THRESHOLD = 240

# Model tool-call token markup that must never reach the user as text.
# DeepSeek occasionally emits its native tool-call format in `content`
# instead of the structured tool_calls field (most often with long
# code-heavy arguments). Detected before answer-commit; the turn is
# retried once, then degraded via fallback_stream.
_TOOL_MARKUP_MARKERS = ("<｜｜DSML｜｜", "<｜tool▁call")


def _has_tool_markup(text: str) -> bool:
    return any(m in text for m in _TOOL_MARKUP_MARKERS)


def _goal_from_call(tool_name: str, params: dict) -> str:
    """Short human-readable goal string for a tool call (shown in the plan UI)."""
    if tool_name == "sql_query":
        q = (params.get("query") or "").replace("\n", " ")
        return f"Query database: {q[:120]}" if q else "Query database"
    if tool_name == "rag_search":
        return f"Search knowledge base: {params.get('query', '')[:100]}"
    if tool_name == "web_search":
        return f"Search web: {params.get('query', '')[:100]}"
    if tool_name == "python_execute":
        return "Run Python analysis"
    if tool_name == "memory":
        return f"Memory {params.get('action', 'search')}"
    if tool_name == "report_generator":
        return f"Report: {params.get('action', 'propose')}"
    return f"Execute {tool_name}"


def _first_sentence(text: str, fallback: str) -> str:
    text = (text or "").strip()
    if not text:
        return fallback
    for sep in (". ", "\n"):
        if sep in text:
            return text.split(sep, 1)[0].strip().rstrip(".") + "."
    return text[:200]


class ReActLoop:
    """Executes the ReAct pattern with native tool calling.

    Each turn the model either emits tool_calls (executed here, observations
    fed back) or streams the final answer. Bounded by MAX_ITERATIONS tool turns.
    """

    MAX_ITERATIONS = 5

    def __init__(self, model: str | None = None):
        self.model = model or DEEPSEEK_MODEL
        self.tool_map = get_tool_map()
        self._client = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
            )
        return self._client

    def _build_messages(
        self,
        user_message: str,
        schema_context: str,
        conversation_history: list[dict] | None,
        summary: str,
        role: str | None,
        forced_tool: str | None = None,
    ) -> list[dict]:
        system_parts = [
            AGENT_SYSTEM_PROMPT.format(
                schema_context=schema_context or "(no schema context available)",
                grounding_rules=COMBINER_GROUNDING_RULES,
            )
        ]
        role_block = _build_role_context(role)
        if role_block:
            system_parts.append(role_block)
        if forced_tool:
            system_parts.append(
                f"## Tool Selection\nThe user explicitly selected the **{forced_tool}** tool "
                "for this query. Use it to answer — do not attempt to use any other tool."
            )
        if summary:
            system_parts.append(f"## Conversation Summary\n{summary}")

        messages: list[dict] = [{"role": "system", "content": "\n\n".join(system_parts)}]
        for msg in conversation_history or []:
            content = msg.get("content", "")
            if msg.get("role") == "assistant":
                content = content[:400]
            messages.append({"role": msg.get("role", "user"), "content": content})
        messages.append({"role": "user", "content": user_message})
        return messages

    async def run_stream(
        self,
        user_message: str,
        tool_schemas: list[dict],
        schema_context: str = "",
        conversation_history: list[dict] | None = None,
        summary: str = "",
        role: str | None = None,
        ambiguity_checker=None,
        max_iterations: int | None = None,
        forced_tool: str | None = None,
    ):
        """Async generator yielding LoopEvents for the full ReAct loop.

        ambiguity_checker: optional async callable (sql_query_text) -> dict | None;
        a non-None return emits a `disambiguate` event and aborts the loop.
        max_iterations: per-run tool-turn limit override (report runs use a
        higher budget); defaults to MAX_ITERATIONS.
        forced_tool: user-selected tool from the UI picker — the caller passes
        a filtered tool_schemas list; this adds the must-use system instruction.
        """
        messages = self._build_messages(
            user_message, schema_context, conversation_history, summary, role,
            forced_tool=forced_tool,
        )
        openai_tools = to_openai_tools(tool_schemas)
        client = self._get_client()

        all_sources: list[dict] = []
        results: list[dict] = []
        plan_emitted = False
        tool_turns = 0
        turn_limit = max_iterations or self.MAX_ITERATIONS
        # SQL retry-synthesis state (preserves the tool_retry UI contract)
        last_sql_failure: dict | None = None
        sql_retry_count = 0
        sql_unrecoverable = False
        # Leaked tool-call-markup turns get one silent retry
        leak_retries = 0

        while True:
            force_answer = tool_turns >= turn_limit
            kwargs: dict = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 2048,
                "stream": True,
            }
            if not force_answer:
                kwargs["tools"] = openai_tools
            else:
                kwargs["tools"] = openai_tools
                kwargs["tool_choice"] = "none"

            try:
                response = await client.chat.completions.create(**kwargs)
            except Exception as e:
                if tool_turns == 0 and not plan_emitted:
                    # First turn failed — signal the caller to fall back
                    yield LoopEvent("fallback", {"error": f"{type(e).__name__}: {e}"})
                    return
                yield LoopEvent("fallback_stream", {
                    "results": results, "sources": all_sources,
                    "error": f"{type(e).__name__}: {e}",
                })
                return

            # ── Consume the stream, classifying tool turn vs answer turn ──
            mode = "unknown"  # -> "tool" | "answer" | "leak"
            content_buffer: list[str] = []
            buffered_len = 0
            streamed_answer = False
            tool_calls_acc: dict[int, dict] = {}

            async for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta is None:
                    continue

                if getattr(delta, "tool_calls", None):
                    if mode in ("answer", "leak"):
                        # Answer already streaming (avoid a mixed turn) or the
                        # turn is a discarded markup leak — ignore late calls.
                        continue
                    mode = "tool"
                    for tc in delta.tool_calls:
                        acc = tool_calls_acc.setdefault(
                            tc.index, {"id": "", "name": "", "arguments": ""}
                        )
                        if tc.id:
                            acc["id"] = tc.id
                        fn = getattr(tc, "function", None)
                        if fn is not None:
                            if getattr(fn, "name", None):
                                acc["name"] = fn.name
                            if getattr(fn, "arguments", None):
                                acc["arguments"] += fn.arguments

                if getattr(delta, "content", None):
                    if mode == "answer":
                        yield LoopEvent("token", {"text": delta.content})
                    elif mode == "leak":
                        continue  # discard — the turn is retried after the stream
                    else:
                        content_buffer.append(delta.content)
                        buffered_len += len(delta.content)
                        if mode == "unknown" and _has_tool_markup("".join(content_buffer)):
                            # Model emitted tool-call markup as text — never
                            # stream it; retry or fall back after the stream.
                            # (Joined-buffer check catches markers split across
                            # chunks; the buffer is small pre-commit.)
                            mode = "leak"
                            continue
                        if mode == "unknown" and buffered_len > _ANSWER_BUFFER_THRESHOLD:
                            # Long leading content with no tool_calls — final answer.
                            mode = "answer"
                            for ev in self._begin_answer(
                                plan_emitted, user_message, all_sources,
                                last_sql_failure, sql_retry_count, results,
                            ):
                                if ev.kind == "controlled_answer":
                                    # Data unrecoverable — suppress model output
                                    yield LoopEvent("token", {"text": ev.payload["text"]})
                                    return
                                yield ev
                            plan_emitted = True
                            last_sql_failure = None
                            yield LoopEvent("token", {"text": "".join(content_buffer)})
                            content_buffer = []
                            streamed_answer = True

            reasoning_text = "".join(content_buffer)

            # ── Leaked tool-call markup — retry once, then fall back ────
            # (Also catches short leaks that ended below the answer threshold.)
            # Once mode == "answer" is committed after 240 clean chars, streamed
            # tokens can't be recalled — but the failure mode starts the turn
            # with markup, which the pre-commit check above catches.
            if mode == "leak" or (
                not tool_calls_acc
                and not streamed_answer
                and _has_tool_markup(reasoning_text)
            ):
                if leak_retries == 0:
                    leak_retries = 1
                    messages.append({
                        "role": "system",
                        "content": (
                            "Your previous response contained raw tool-call markup "
                            "as text and was discarded. Use the tools API to call "
                            "tools — never write tool-call syntax in your answer."
                        ),
                    })
                    continue
                yield LoopEvent("fallback_stream", {
                    "results": results, "sources": all_sources,
                    "error": "model emitted malformed tool-call markup",
                })
                return

            # Strip any markup fragment from reasoning shown in the UI/transcript
            for _marker in _TOOL_MARKUP_MARKERS:
                _idx = reasoning_text.find(_marker)
                if _idx != -1:
                    reasoning_text = reasoning_text[:_idx].rstrip()

            # ── Answer turn ─────────────────────────────────────────────
            if not tool_calls_acc:
                if not streamed_answer:
                    # Short answer fully buffered — flush now
                    controlled = None
                    for ev in self._begin_answer(
                        plan_emitted, user_message, all_sources,
                        last_sql_failure, sql_retry_count, results,
                    ):
                        if ev.kind == "controlled_answer":
                            controlled = ev.payload["text"]
                            break
                        yield ev
                    if controlled is not None:
                        yield LoopEvent("token", {"text": controlled})
                        return
                    yield LoopEvent("token", {"text": reasoning_text or ""})
                return

            # ── Tool turn ───────────────────────────────────────────────
            tool_turns += 1
            ordered = [tool_calls_acc[i] for i in sorted(tool_calls_acc)]

            # Parse + validate arguments per call
            calls = []
            for acc in ordered:
                params, err = validate_tool_args(acc["name"], acc["arguments"])
                calls.append({
                    "id": acc["id"] or f"call_{tool_turns}_{len(calls)}",
                    "name": acc["name"],
                    "raw_arguments": acc["arguments"],
                    "params": params,
                    "validation_error": err,
                })

            # SQL retry synthesis: previous sql_query failed → is this a retry?
            retry_attempt = 0
            if last_sql_failure is not None:
                if any(c["name"] == "sql_query" for c in calls):
                    sql_retry_count += 1
                    retry_attempt = sql_retry_count
                    yield LoopEvent("tool_retry", {
                        "tool": "sql_query",
                        "attempt": retry_attempt,
                        "original_query": last_sql_failure.get("query", ""),
                        "error": last_sql_failure.get("error", ""),
                        "message": "Retrying with a different SQL approach",
                    })
                else:
                    yield LoopEvent("tool_retry_failed", {
                        "tool": "sql_query",
                        "attempt": sql_retry_count + 1,
                        "message": "No alternative approach available — data not found in database",
                    })
                    sql_unrecoverable = True
                last_sql_failure = None

            # Plan event (first tool turn) / plan_step events (later turns)
            step_dicts = [
                {
                    "tool": c["name"],
                    "goal": _goal_from_call(c["name"], c["params"] or {}),
                    "params": c["params"] or {},
                    "status": "pending",
                    "execution_time_ms": None,
                    "error": "",
                }
                for c in calls
            ]
            if not plan_emitted:
                yield LoopEvent("plan", {
                    "intent": _first_sentence(reasoning_text, user_message),
                    "tools_needed": [c["name"] for c in calls],
                    "reasoning": reasoning_text,
                    "steps": step_dicts,
                })
                plan_emitted = True
            else:
                for step in step_dicts:
                    yield LoopEvent("plan_step", step)

            if reasoning_text:
                yield LoopEvent("reasoning", {"text": reasoning_text})

            # Append the assistant tool-call turn to the transcript
            messages.append({
                "role": "assistant",
                "content": reasoning_text or None,
                "tool_calls": [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {"name": c["name"], "arguments": c["raw_arguments"] or "{}"},
                    }
                    for c in calls
                ],
            })

            # ── Execute the calls (concurrently when >1) ────────────────
            runnable = []
            for c in calls:
                if c["validation_error"]:
                    yield LoopEvent("validation_warning", {"warnings": [c["validation_error"]]})
                    c["result"] = {
                        "tool": c["name"], "success": False,
                        "error": c["validation_error"], "data": None, "citations": [],
                    }
                    continue

                params, denial = apply_rbac(c["name"], c["params"], role)
                c["params"] = params
                if denial:
                    c["result"] = {
                        "tool": c["name"], "success": False,
                        "error": denial, "data": None, "citations": [],
                    }
                    yield LoopEvent("system_note", {"text": f"[Access blocked: {denial}]"})
                    continue

                # Pre-query name disambiguation for SQL
                if c["name"] == "sql_query" and ambiguity_checker is not None:
                    ambiguity = await ambiguity_checker(params.get("query", ""))
                    if ambiguity:
                        yield LoopEvent("tool_result", {
                            "tool": c["name"],
                            "success": False,
                            "summary": f"Ambiguous — {len(ambiguity['options'])} matches found",
                        })
                        yield LoopEvent("disambiguate", ambiguity)
                        return  # Stop — wait for the user to select

                if c["name"] not in self.tool_map:
                    c["result"] = {
                        "tool": c["name"], "success": False,
                        "error": f"Unknown tool: {c['name']}", "data": None, "citations": [],
                    }
                    continue
                runnable.append(c)

            for c in runnable:
                event = {"tool": c["name"]}
                if retry_attempt and c["name"] == "sql_query":
                    event["attempt"] = retry_attempt
                    event["message"] = "Trying alternative approach"
                yield LoopEvent("tool_start", event)

            async def _run(call):
                try:
                    result = await self.tool_map[call["name"]].execute(**call["params"])
                    return result.to_dict()
                except Exception as e:
                    return {
                        "tool": call["name"], "success": False,
                        "error": f"{type(e).__name__}: {e}", "data": None, "citations": [],
                    }

            if runnable:
                executed = await asyncio.gather(*(_run(c) for c in runnable))
                for c, result_dict in zip(runnable, executed):
                    c["result"] = result_dict

            # ── Emit results + feed observations back ───────────────────
            for c in calls:
                result_dict = c["result"]
                results.append(result_dict)

                event = {
                    "tool": c["name"],
                    "success": result_dict.get("success", False),
                    "summary": (
                        result_dict.get("error", "Failed")
                        if not result_dict.get("success")
                        else summarize_result(result_dict)
                    ),
                }
                if retry_attempt and c["name"] == "sql_query":
                    event["attempt"] = retry_attempt
                data = result_dict.get("data") or {}
                if isinstance(data, dict) and data.get("requires_approval"):
                    event["requires_approval"] = True
                    event["report_id"] = data.get("report_id")
                    event["title"] = data.get("title")
                    event["description"] = data.get("description")
                    event["sections"] = data.get("sections", [])
                    event["data_sources"] = data.get("data_sources", [])
                yield LoopEvent("tool_result", event)

                if result_dict.get("success"):
                    for cit in result_dict.get("citations") or []:
                        all_sources.append({"tool": c["name"], "citation": cit})
                    if c["name"] == "sql_query":
                        sql_unrecoverable = False
                elif c["name"] == "sql_query" and not c["validation_error"]:
                    last_sql_failure = {
                        "query": (c["params"] or {}).get("query", ""),
                        "error": result_dict.get("error", ""),
                    }

                observation = serialize_observation(result_dict)
                if (
                    c["name"] == "sql_query"
                    and not result_dict.get("success")
                    and sql_retry_count >= 1
                ):
                    observation += (
                        "\n\nDo NOT retry SQL again. Explain to the user what data "
                        "is unavailable."
                    )
                messages.append({
                    "role": "tool",
                    "tool_call_id": c["id"],
                    "content": observation,
                })

            # Track unrecoverable SQL for the controlled final message
            if last_sql_failure is not None and sql_retry_count >= 1:
                sql_unrecoverable = True

        # (unreachable — loop exits via returns above)

    def _begin_answer(
        self,
        plan_emitted: bool,
        user_message: str,
        all_sources: list[dict],
        last_sql_failure: dict | None,
        sql_retry_count: int,
        results: list[dict],
    ) -> list[LoopEvent]:
        """Events to emit right before streaming the final answer.

        Returns a controlled_answer event instead when SQL failed and no tool
        produced a successful result — preserving the deterministic
        'data not found' message.
        """
        events: list[LoopEvent] = []
        if not plan_emitted:
            # Direct answer with no tool use (greeting, refusal, meta question)
            events.append(LoopEvent("plan", {
                "intent": "Direct answer",
                "tools_needed": [],
                "reasoning": "",
                "steps": [],
            }))
        if last_sql_failure is not None:
            events.append(LoopEvent("tool_retry_failed", {
                "tool": "sql_query",
                "attempt": sql_retry_count + 1,
                "message": "No alternative approach available — data not found in database",
            }))
        events.append(LoopEvent("sources", {"sources": all_sources}))
        any_success = any(r.get("success") for r in results)
        if last_sql_failure is not None and not any_success:
            events.append(LoopEvent("controlled_answer", {
                "text": (
                    "The requested data could not be found in the database. "
                    "Please reach out to your lead or supervisor for further assistance."
                ),
            }))
        return events