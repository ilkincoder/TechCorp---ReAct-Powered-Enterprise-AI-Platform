"""Unit tests for the report generator tool (tools/report_tool.py)."""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from techcorp_platform.tools.report_tool import ReportTool
from techcorp_platform.tools.base import ToolResult


VALID_PLAN_ARGS = json.dumps({
    "title": "Ticket & Incident Report",
    "description": "Overview of tickets and incidents",
    "sections": ["Overview", "Trends"],
    "data_sources": ["support_tickets"],
    "sql_queries": ["SELECT ticket_id, status FROM support_tickets"],
})

SCHEMA_RESULT = ToolResult(
    tool_name="sql_query",
    success=True,
    data={"rows": [
        {"table_name": "support_tickets", "column_name": "ticket_id"},
        {"table_name": "support_tickets", "column_name": "status"},
        {"table_name": "incident_reports", "column_name": "incident_id"},
    ]},
)


def _tool_call_response(args_json, finish_reason="tool_calls"):
    """Mock chat completion whose message carries a submit_report_plan call."""
    response = MagicMock()
    choice = MagicMock()
    choice.finish_reason = finish_reason
    if args_json is None:
        choice.message.tool_calls = None
    else:
        tc = MagicMock()
        tc.function.name = "submit_report_plan"
        tc.function.arguments = args_json
        choice.message.tool_calls = [tc]
    choice.message.reasoning_content = "thinking trace"
    response.choices = [choice]
    return response


def _client_with(*responses):
    client = MagicMock()
    if len(responses) == 1:
        client.chat.completions.create.return_value = responses[0]
    else:
        client.chat.completions.create.side_effect = list(responses)
    return client


# ── propose ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_propose_prompt_contains_live_schema():
    """Propose gives the planner real column names and the submit_report_plan tool."""
    client = _client_with(_tool_call_response(VALID_PLAN_ARGS))

    tool = ReportTool()
    with patch("techcorp_platform.tools.sql_tool.SQLTool.execute", AsyncMock(return_value=SCHEMA_RESULT)), \
         patch("techcorp_platform.tools.report_tool.insert_report", AsyncMock(return_value={"id": 8})) as insert_mock, \
         patch("techcorp_platform.tools.report_tool._get_llm", return_value=client):
        result = await tool.execute(action="propose", query="ticket report")

    assert result.success is True
    assert result.data["report_id"] == 8
    assert result.data["requires_approval"] is True
    insert_mock.assert_awaited_once()

    kwargs = client.chat.completions.create.call_args.kwargs
    system_prompt = kwargs["messages"][0]["content"]
    assert "support_tickets: ticket_id, status" in system_prompt
    assert "incident_reports: incident_id" in system_prompt
    assert "NEVER invent column names" in system_prompt
    assert kwargs["tools"][0]["function"]["name"] == "submit_report_plan"
    assert kwargs["tool_choice"] == "auto"  # thinking mode rejects forced tool_choice


@pytest.mark.asyncio
async def test_propose_retries_on_truncation_then_succeeds():
    """finish_reason='length' → never parsed; error fed forward; retry succeeds."""
    client = _client_with(
        _tool_call_response(None, finish_reason="length"),
        _tool_call_response(VALID_PLAN_ARGS),
    )

    tool = ReportTool()
    with patch("techcorp_platform.tools.sql_tool.SQLTool.execute", AsyncMock(return_value=SCHEMA_RESULT)), \
         patch("techcorp_platform.tools.report_tool.insert_report", AsyncMock(return_value={"id": 9})), \
         patch("techcorp_platform.tools.report_tool._get_llm", return_value=client), \
         patch("techcorp_platform.tools.report_tool._RETRY_BACKOFF", 0):
        result = await tool.execute(action="propose", query="ticket report")

    assert result.success is True
    calls = client.chat.completions.create.call_args_list
    assert len(calls) == 2
    second_messages = calls[1].kwargs["messages"]
    assert any(
        m["role"] == "user" and "Previous attempt failed" in m["content"] and "truncated" in m["content"]
        for m in second_messages
    )


@pytest.mark.asyncio
async def test_propose_rejects_unusable_plan_after_retries():
    """Plans with no data queries fail validation on every attempt → clean failure, nothing stored."""
    bad_args = json.dumps({"title": "T", "sections": ["Overview"], "sql_queries": []})
    client = _client_with(*[_tool_call_response(bad_args) for _ in range(3)])

    tool = ReportTool()
    with patch("techcorp_platform.tools.sql_tool.SQLTool.execute", AsyncMock(return_value=SCHEMA_RESULT)), \
         patch("techcorp_platform.tools.report_tool.insert_report", AsyncMock()) as insert_mock, \
         patch("techcorp_platform.tools.report_tool._get_llm", return_value=client), \
         patch("techcorp_platform.tools.report_tool._RETRY_BACKOFF", 0):
        result = await tool.execute(action="propose", query="ticket report")

    assert result.success is False
    assert "after 3 attempts" in result.error
    insert_mock.assert_not_called()
    assert len(client.chat.completions.create.call_args_list) == 3


# ── generate (briefing) ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_returns_briefing_from_stored_plan():
    """generate returns the saved plan as an execution briefing — no LLM, no execution."""
    stored = {
        "id": 7,
        "title": "Ticket Report",
        "plan": {
            "title": "Ticket Report",
            "sections": ["Overview", "Trends"],
            "sql_queries": ["SELECT status, COUNT(*) FROM support_tickets GROUP BY status"],
            "memory_query": "ticket context",
            "rag_query": "SLA policy",
        },
    }
    tool = ReportTool()
    llm = MagicMock()

    with patch("techcorp_platform.tools.report_tool.get_report", AsyncMock(return_value=stored)), \
         patch("techcorp_platform.tools.report_tool.update_report", AsyncMock()) as update_mock, \
         patch("techcorp_platform.tools.report_tool._get_llm", llm):
        result = await tool.execute(action="generate", report_id=7)

    assert result.success is True
    data = result.data
    assert data["report_id"] == 7
    assert data["sections"] == ["Overview", "Trends"]
    assert data["sql_queries"] == stored["plan"]["sql_queries"]
    assert "Execute this plan NOW" in data["instructions"]
    assert data["report_date"]  # real date injected for the report writer
    # Status flipped to generating; no LLM call happened
    update_mock.assert_awaited_once_with(7, status="generating")
    llm.assert_not_called()


@pytest.mark.asyncio
async def test_generate_unknown_report_id_errors():
    """generate for a nonexistent report → clean error, no crash."""
    tool = ReportTool()
    with patch("techcorp_platform.tools.report_tool.get_report", AsyncMock(return_value=None)):
        result = await tool.execute(action="generate", report_id=999)

    assert result.success is False
    assert "999" in result.error
