"""Report Generator Tool — plans reports; the ReAct loop executes them.

Two-phase flow:
  1. propose — analyzes the request (with the live DB schema) and returns a
     report plan for user approval; the plan is stored in the reports table.
  2. generate — returns the approved plan as an execution briefing; the agent
     loop runs the queries via the normal tools (sql_query, memory, rag_search,
     python_execute) and writes the report as its final answer, which app.py
     persists to the reports table.
"""

import asyncio
import json
from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError, model_validator

from ..config import DEEPSEEK_MODEL, get_openai_client
from ..conversations import insert_report, update_report, get_report
from .base import BaseTool, ToolResult


def _get_llm():
    return get_openai_client()


PROPOSE_PROMPT = """You are a report planning assistant for TechCorp Enterprise AI Platform.
Given a user's report request, plan a structured report and submit it by calling the
submit_report_plan tool. You MUST call the tool — never answer in plain text.

Available data sources:
- SQL tables (PostgreSQL) with their exact columns:
{schema}
- Memory: stored enterprise context (project details, deadlines, team structures,
  meeting decisions, vendor/client info, technical decisions, budgets)
- RAG: internal knowledge base (policies, engineering standards, compliance docs,
  HR guides, IT procedures across 12 departments)

Rules for sql_queries:
- Use ONLY the tables and columns listed above — NEVER invent column names.
- Standard PostgreSQL syntax, SELECT statements only."""


# The planner submits its plan through this tool — structured arguments instead
# of free-text JSON, so truncated/markdown-wrapped output can't corrupt plans.
# NOTE: DeepSeek thinking mode rejects forced tool_choice ("required" or
# by-name), so the call uses tool_choice="auto" + the MUST-call instruction,
# with non-compliance handled by the retry loop.
_SUBMIT_PLAN_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_report_plan",
        "description": "Submit the finalized report plan. You MUST call this tool — never answer in plain text.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Report title"},
                "description": {"type": "string", "description": "One-sentence summary of what this report covers"},
                "sections": {"type": "array", "items": {"type": "string"}, "description": "Ordered section headings"},
                "data_sources": {"type": "array", "items": {"type": "string"}, "description": "Tables/sources the report draws on"},
                "sql_queries": {"type": "array", "items": {"type": "string"},
                                "description": "PostgreSQL SELECT statements using only the listed tables/columns"},
                "python_analysis": {"type": "string", "description": "Brief description of analysis needed (aggregations, trends)"},
                "memory_query": {"type": "string", "description": "What to search enterprise memory for"},
                "rag_query": {"type": "string", "description": "What to search the knowledge base for (policies, docs)"},
            },
            "required": ["title", "sections", "sql_queries"],
        },
    },
}

_RETRY_BACKOFF = 0.5  # seconds; exponential between propose attempts


class ReportPlanModel(BaseModel):
    """Validated report plan submitted by the planner via submit_report_plan."""
    title: str
    description: str = ""
    sections: list[str]
    data_sources: list[str] = []
    sql_queries: list[str] = []
    python_analysis: str = ""
    memory_query: str = ""
    rag_query: str = ""

    @model_validator(mode="after")
    def _validate_plan(self):
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.sections:
            raise ValueError("sections must not be empty")
        if not (self.sql_queries or self.rag_query or self.memory_query):
            raise ValueError("plan has no data queries (sql_queries/rag_query/memory_query all empty)")
        return self


BRIEFING_INSTRUCTIONS = (
    "Execute this plan NOW. Run every query in sql_queries via the sql_query tool, "
    "batching them as parallel tool calls in ONE turn. Then, only where the plan "
    "specifies them: memory (action='search') with memory_query, rag_search with "
    "rag_query, python_execute for python_analysis. Finally write the COMPLETE "
    "report as your final answer — Markdown ONLY: start with '# <title>', one "
    "'## <section>' heading per listed section, specific numbers from the tool "
    "results, report_date as the report date, and a Sources section at the end. "
    "Output nothing outside the report."
)


class ReportTool(BaseTool):
    name = "report_generator"
    description = """Plan and generate structured business reports. Two actions: 'propose'
(plan a report from the user's request and ask for approval) and 'generate' (returns the
approved plan as an execution briefing — pass only report_id; you then execute the plan's
queries with the other tools and write the report yourself)."""

    async def execute(
        self,
        action: str = "propose",
        report_id: int | None = None,
        **kwargs,
    ) -> ToolResult:
        if action == "propose":
            return await self._propose(kwargs.get("query", ""))
        elif action == "generate":
            return await self._briefing(report_id)
        else:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Unknown action: {action}. Use 'propose' or 'generate'.",
            )

    async def _propose(self, query: str) -> ToolResult:
        """Analyze the request and return a plan for approval.

        The planner submits the plan via the submit_report_plan tool; the
        arguments are validated with ReportPlanModel. Truncation, missing
        tool calls, and invalid plans get bounded retries with the error
        fed forward so the model can correct itself.
        """
        if not query.strip():
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="No query provided for report proposal.",
            )

        schema = await self._get_db_schema()
        client = _get_llm()
        messages = [
            {"role": "system", "content": PROPOSE_PROMPT.format(schema=schema)},
            {"role": "user", "content": query},
        ]

        last_err = "unknown error"
        choice = None
        for attempt in range(3):
            if attempt:
                await asyncio.sleep(_RETRY_BACKOFF * 2 ** (attempt - 1))
            try:
                response = await asyncio.to_thread(
                    lambda: client.chat.completions.create(
                        model=DEEPSEEK_MODEL,
                        messages=messages,
                        tools=[_SUBMIT_PLAN_TOOL],
                        tool_choice="auto",
                        # Reasoning tokens count against this budget — leave
                        # ample headroom or the plan gets truncated.
                        max_tokens=4096,
                        temperature=0.2,
                    )
                )
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
                continue

            choice = response.choices[0]
            # Truncation first — never parse a cut-off response
            if choice.finish_reason == "length":
                last_err = "response truncated (reasoning exhausted the token budget)"
            elif not choice.message.tool_calls:
                last_err = "you must submit the plan by calling submit_report_plan, not as text"
            else:
                try:
                    args = json.loads(choice.message.tool_calls[0].function.arguments or "{}")
                    plan = ReportPlanModel(**args).model_dump()
                except (json.JSONDecodeError, TypeError, ValidationError) as e:
                    last_err = f"plan validation failed: {e}"
                else:
                    # Store pending report in DB
                    report = await insert_report(
                        title=plan["title"],
                        data_sources=plan["data_sources"],
                        plan=plan,
                    )
                    return ToolResult(
                        tool_name=self.name,
                        success=True,
                        data={
                            "report_id": report["id"],
                            "title": plan["title"],
                            "description": plan["description"],
                            "sections": plan["sections"],
                            "data_sources": plan["data_sources"],
                            "status": "pending_approval",
                            "requires_approval": True,
                        },
                        metadata={"report_id": report["id"]},
                    )

            # Feed the error forward so the retry can correct itself. (Never
            # append the assistant tool-call turn — an unanswered tool_call
            # in the thread would be rejected by the API.)
            messages.append({
                "role": "user",
                "content": f"Previous attempt failed: {last_err}. Call submit_report_plan again with a corrected plan.",
            })

        # All attempts exhausted — log the reasoning trace for debugging
        if choice is not None:
            reasoning = getattr(choice.message, "reasoning_content", "") or ""
            if reasoning:
                print(f"[report_propose] raw reasoning trace: {reasoning[:500]}")
        return ToolResult(
            tool_name=self.name,
            success=False,
            error=f"Report planner failed after 3 attempts: {last_err} — please try again.",
        )

    async def _briefing(self, report_id: int | None) -> ToolResult:
        """Return the approved plan as an execution briefing for the agent loop."""
        if not report_id:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="report_id is required for generation.",
            )

        stored = await get_report(report_id)
        if not stored:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Report #{report_id} not found — propose a report first.",
            )
        if not stored.get("plan"):
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Report #{report_id} has no usable plan — please create a new proposal.",
            )

        plan = stored["plan"]
        await update_report(report_id, status="generating")

        return ToolResult(
            tool_name=self.name,
            success=True,
            data={
                "report_id": report_id,
                "title": plan.get("title") or stored.get("title") or "Untitled Report",
                "sections": plan.get("sections", []),
                "sql_queries": plan.get("sql_queries", []),
                "memory_query": plan.get("memory_query", ""),
                "rag_query": plan.get("rag_query", ""),
                "python_analysis": plan.get("python_analysis", ""),
                "report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "instructions": BRIEFING_INSTRUCTIONS,
            },
            metadata={"report_id": report_id},
        )

    # ── Internal helpers ─────────────────────────────────────────────────────

    async def _get_db_schema(self) -> str:
        """Live table/column list so planned SQL uses real column names."""
        from .sql_tool import SQLTool
        result = await SQLTool().execute(
            query=(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' ORDER BY table_name, ordinal_position"
            )
        )
        if not (result.success and result.data):
            return "(schema unavailable)"
        tables: dict[str, list[str]] = {}
        for row in result.data.get("rows", []):
            tables.setdefault(row["table_name"], []).append(row["column_name"])
        return "\n".join(f"  - {t}: {', '.join(cols)}" for t, cols in tables.items())

    def _input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["propose", "generate"],
                    "description": "Action: 'propose' to plan a report, 'generate' to get the approved plan's execution briefing",
                },
                "query": {
                    "type": "string",
                    "description": "The user's report request (for 'propose' action)",
                },
                "report_id": {
                    "type": "integer",
                    "description": "The report ID from the proposal step (required for 'generate' action)",
                },
            },
            "required": ["action"],
        }
