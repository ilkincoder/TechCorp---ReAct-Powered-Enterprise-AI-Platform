"""Unit tests for the native tool-calling ReAct loop (agent/react.py)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from techcorp_platform.agent.react import ReActLoop
from techcorp_platform.tools.base import ToolResult


# ── Stream helpers ───────────────────────────────────────────────────────────

def _tc(index, id=None, name=None, arguments=None):
    """Build a tool_call delta fragment."""
    tc = MagicMock()
    tc.index = index
    tc.id = id
    fn = MagicMock()
    fn.name = name  # attribute assignment avoids the MagicMock(name=...) pitfall
    fn.arguments = arguments
    tc.function = fn
    return tc


def _chunk(content=None, tool_calls=None):
    chunk = MagicMock()
    delta = MagicMock()
    delta.content = content
    delta.tool_calls = tool_calls
    choice = MagicMock()
    choice.delta = delta
    choice.finish_reason = None
    chunk.choices = [choice]
    return chunk


class _FakeStream:
    def __init__(self, chunks):
        self._chunks = chunks

    def __aiter__(self):
        async def gen():
            for c in self._chunks:
                yield c
        return gen()


class _FakeTool:
    def __init__(self, results):
        self._results = list(results)

    async def execute(self, **kwargs):
        self.last_kwargs = kwargs
        return self._results.pop(0)


def _loop_with(turns, tools):
    """Build a ReActLoop with a mocked client (side_effect=turns) and fake tools."""
    loop = ReActLoop()
    loop.tool_map = tools
    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=turns)
    loop._client = client
    return loop


TOOL_SCHEMAS = [
    {"name": "rag_search", "description": "Search KB",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "sql_query", "description": "Run SQL",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "web_search", "description": "Search web",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
]


async def _collect(loop, message="test question", **kwargs):
    return [ev async for ev in loop.run_stream(message, TOOL_SCHEMAS, **kwargs)]


# ── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_two_turn_flow_emits_plan_tools_and_tokens():
    """Turn 1: goal sentence + rag_search call. Turn 2: streamed answer."""
    turn1 = _FakeStream([
        _chunk(content="I will search the knowledge base."),
        _chunk(tool_calls=[_tc(0, id="call_1", name="rag_search", arguments='{"query": "vacation policy"}')]),
    ])
    answer = "The vacation policy allows 20 days per year. " * 3  # >50 chars
    turn2 = _FakeStream([_chunk(content=part) for part in [answer[:100], answer[100:]]])

    rag = _FakeTool([ToolResult(tool_name="rag_search", success=True,
                                data={"results": [{"text": "doc"}]}, citations=["policy.pdf"])])
    loop = _loop_with([turn1, turn2], {"rag_search": rag})

    events = await _collect(loop)
    kinds = [e.kind for e in events]

    assert kinds[0] == "plan"
    plan = events[0].payload
    assert plan["tools_needed"] == ["rag_search"]
    assert plan["steps"][0]["tool"] == "rag_search"
    assert plan["intent"]

    assert "reasoning" in kinds
    assert "tool_start" in kinds
    tr = next(e.payload for e in events if e.kind == "tool_result")
    assert tr["success"] is True

    assert "sources" in kinds
    sources = next(e.payload for e in events if e.kind == "sources")
    assert sources["sources"] == [{"tool": "rag_search", "citation": "policy.pdf"}]

    tokens = "".join(e.payload["text"] for e in events if e.kind == "token")
    assert answer in tokens or tokens in answer or len(tokens) > 50

    # Observation was fed back: second create call includes a role:tool message
    second_call = loop._client.chat.completions.create.call_args_list[1]
    messages = second_call.kwargs["messages"]
    assert any(m.get("role") == "tool" for m in messages)


@pytest.mark.asyncio
async def test_parallel_tool_calls_in_one_turn():
    """Two tool_calls in one turn → both executed, all tool_starts precede results."""
    turn1 = _FakeStream([
        _chunk(tool_calls=[
            _tc(0, id="c1", name="rag_search", arguments='{"query": "a"}'),
            _tc(1, id="c2", name="web_search", arguments='{"query": "b"}'),
        ]),
    ])
    turn2 = _FakeStream([_chunk(content="Answer synthesized from both tools, done.")])

    rag = _FakeTool([ToolResult(tool_name="rag_search", success=True, data={"results": []})])
    web = _FakeTool([ToolResult(tool_name="web_search", success=True, data={"results": []})])
    loop = _loop_with([turn1, turn2], {"rag_search": rag, "web_search": web})

    events = await _collect(loop)
    kinds = [e.kind for e in events]

    starts = [i for i, k in enumerate(kinds) if k == "tool_start"]
    result_events = [i for i, k in enumerate(kinds) if k == "tool_result"]
    assert len(starts) == 2 and len(result_events) == 2
    assert max(starts) < min(result_events), "all tool_starts must precede tool_results"

    plan = next(e.payload for e in events if e.kind == "plan")
    assert plan["tools_needed"] == ["rag_search", "web_search"]


@pytest.mark.asyncio
async def test_sql_failure_then_retry_synthesizes_tool_retry():
    """SQL fails → next turn retries SQL → tool_retry + attempt-tagged events."""
    turn1 = _FakeStream([
        _chunk(tool_calls=[_tc(0, id="c1", name="sql_query", arguments='{"query": "SELECT phone FROM employees"}')]),
    ])
    turn2 = _FakeStream([
        _chunk(content="Column missing, probing the schema instead."),
        _chunk(tool_calls=[_tc(0, id="c2", name="sql_query", arguments='{"query": "SELECT column_name FROM information_schema.columns"}')]),
    ])
    turn3 = _FakeStream([_chunk(content="The phone column does not exist in the database schema.")])

    sql = _FakeTool([
        ToolResult(tool_name="sql_query", success=False, error='column "phone" does not exist'),
        ToolResult(tool_name="sql_query", success=True, data={"rows": [{"column_name": "email"}], "total_rows": 1}),
    ])
    loop = _loop_with([turn1, turn2, turn3], {"sql_query": sql})

    events = await _collect(loop)
    kinds = [e.kind for e in events]

    retry = next(e.payload for e in events if e.kind == "tool_retry")
    assert retry["tool"] == "sql_query"
    assert retry["attempt"] == 1
    assert "phone" in retry["original_query"]
    assert retry["error"]

    # Second turn's calls emit plan_step (plan already emitted) with attempt on tool_start
    assert "plan_step" in kinds
    attempt_starts = [e.payload for e in events if e.kind == "tool_start" and e.payload.get("attempt")]
    assert len(attempt_starts) == 1

    # Recovery succeeded → normal streamed answer, no controlled message
    tokens = "".join(e.payload["text"] for e in events if e.kind == "token")
    assert "does not exist" in tokens


@pytest.mark.asyncio
async def test_sql_unrecoverable_yields_controlled_message():
    """SQL fails, model answers without retrying → tool_retry_failed + controlled text."""
    turn1 = _FakeStream([
        _chunk(tool_calls=[_tc(0, id="c1", name="sql_query", arguments='{"query": "SELECT ssn FROM employees"}')]),
    ])
    turn2 = _FakeStream([_chunk(content="I could not find that data anywhere.")])

    sql = _FakeTool([ToolResult(tool_name="sql_query", success=False, error='column "ssn" does not exist')])
    loop = _loop_with([turn1, turn2], {"sql_query": sql})

    events = await _collect(loop)
    kinds = [e.kind for e in events]

    assert "tool_retry_failed" in kinds
    tokens = "".join(e.payload["text"] for e in events if e.kind == "token")
    assert "could not be found in the database" in tokens


@pytest.mark.asyncio
async def test_rbac_denial_inside_loop():
    """sales_intern querying employees → denial observation, no execution."""
    turn1 = _FakeStream([
        _chunk(tool_calls=[_tc(0, id="c1", name="sql_query", arguments='{"query": "SELECT salary FROM employees"}')]),
    ])
    turn2 = _FakeStream([_chunk(content="That data is outside your access scope.")])

    sql = _FakeTool([])  # must never be called
    loop = _loop_with([turn1, turn2], {"sql_query": sql})

    events = await _collect(loop, role="sales_intern")

    tr = next(e.payload for e in events if e.kind == "tool_result")
    assert tr["success"] is False
    assert "Access denied" in tr["summary"]
    assert any(e.kind == "system_note" for e in events)
    assert not hasattr(sql, "last_kwargs"), "tool must not execute on RBAC denial"


@pytest.mark.asyncio
async def test_invalid_arguments_bounce_as_validation_warning():
    """Missing required param → validation_warning + failed observation, model recovers."""
    turn1 = _FakeStream([
        _chunk(tool_calls=[_tc(0, id="c1", name="rag_search", arguments='{"top_k": 3}')]),  # missing query
    ])
    turn2 = _FakeStream([_chunk(content="Let me answer without the search then, sorry.")])

    loop = _loop_with([turn1, turn2], {"rag_search": _FakeTool([])})

    events = await _collect(loop)
    kinds = [e.kind for e in events]

    assert "validation_warning" in kinds
    warning = next(e.payload for e in events if e.kind == "validation_warning")
    assert "query" in warning["warnings"][0]
    tr = next(e.payload for e in events if e.kind == "tool_result")
    assert tr["success"] is False


@pytest.mark.asyncio
async def test_disambiguation_aborts_loop():
    """Ambiguity checker returning options → disambiguate event, loop stops."""
    turn1 = _FakeStream([
        _chunk(tool_calls=[_tc(0, id="c1", name="sql_query", arguments='{"query": "SELECT * FROM employees WHERE first_name ILIKE \'%John%\'"}')]),
    ])

    async def checker(query_text):
        return {"field": "employee_name", "query": "John",
                "options": [{"employee_id": 1}, {"employee_id": 2}]}

    loop = _loop_with([turn1], {"sql_query": _FakeTool([])})
    events = await _collect(loop, ambiguity_checker=checker)
    kinds = [e.kind for e in events]

    assert kinds[-1] == "disambiguate"
    assert "token" not in kinds


@pytest.mark.asyncio
async def test_max_iterations_forces_final_answer():
    """After MAX_ITERATIONS tool turns, the next call uses tool_choice='none'."""
    tool_turn = lambda i: _FakeStream([
        _chunk(tool_calls=[_tc(0, id=f"c{i}", name="rag_search", arguments='{"query": "again"}')]),
    ])
    final = _FakeStream([_chunk(content="Final forced answer after hitting the limit.")])
    turns = [tool_turn(i) for i in range(ReActLoop.MAX_ITERATIONS)] + [final]

    rag = _FakeTool([
        ToolResult(tool_name="rag_search", success=True, data={"results": []})
        for _ in range(ReActLoop.MAX_ITERATIONS)
    ])
    loop = _loop_with(turns, {"rag_search": rag})

    events = await _collect(loop)

    calls = loop._client.chat.completions.create.call_args_list
    assert len(calls) == ReActLoop.MAX_ITERATIONS + 1
    assert calls[-1].kwargs.get("tool_choice") == "none"
    tokens = "".join(e.payload["text"] for e in events if e.kind == "token")
    assert "Final forced answer" in tokens


@pytest.mark.asyncio
async def test_max_iterations_override():
    """A per-run max_iterations overrides the class default (report runs use a higher budget)."""
    tool_turn = lambda i: _FakeStream([
        _chunk(tool_calls=[_tc(0, id=f"c{i}", name="rag_search", arguments='{"query": "again"}')]),
    ])
    final = _FakeStream([_chunk(content="Forced answer at the overridden limit.")])
    turns = [tool_turn(0), tool_turn(1), final]

    rag = _FakeTool([
        ToolResult(tool_name="rag_search", success=True, data={"results": []})
        for _ in range(2)
    ])
    loop = _loop_with(turns, {"rag_search": rag})

    events = await _collect(loop, max_iterations=2)

    calls = loop._client.chat.completions.create.call_args_list
    assert len(calls) == 3
    assert calls[-1].kwargs.get("tool_choice") == "none"
    tokens = "".join(e.payload["text"] for e in events if e.kind == "token")
    assert "Forced answer at the overridden limit" in tokens


@pytest.mark.asyncio
async def test_direct_answer_without_tools():
    """Answer turn with no tool use → empty plan + tokens."""
    long_answer = "This platform provides rag_search, sql_query and more tools. " * 5
    turn1 = _FakeStream([_chunk(content=part) for part in
                         [long_answer[i:i + 60] for i in range(0, len(long_answer), 60)]])
    loop = _loop_with([turn1], {})

    events = await _collect(loop, "what can you do?")
    kinds = [e.kind for e in events]

    plan = next(e.payload for e in events if e.kind == "plan")
    assert plan["tools_needed"] == []
    assert "sources" in kinds
    tokens = "".join(e.payload["text"] for e in events if e.kind == "token")
    assert len(tokens) > 50


@pytest.mark.asyncio
async def test_first_turn_exception_emits_fallback():
    """LLM failure on turn 1 → fallback event so app.py can use the deterministic path."""
    loop = ReActLoop()
    loop.tool_map = {}
    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=Exception("boom"))
    loop._client = client

    events = await _collect(loop)
    assert len(events) == 1
    assert events[0].kind == "fallback"


# ── Leaked tool-call markup (DeepSeek DSML-in-content failure mode) ─────────

LEAK = (
    '<｜｜DSML｜｜tool_calls> <｜｜DSML｜｜invoke name="python_execute"> '
    '<｜｜DSML｜｜parameter name="code" string="true">print("analysis")'
    "</｜｜DSML｜｜parameter> </｜｜DSML｜｜invoke> </｜｜DSML｜｜tool_calls>"
) * 3  # comfortably past the 240-char answer threshold


def _leak_stream():
    return _FakeStream([_chunk(content=LEAK[i:i + 80]) for i in range(0, len(LEAK), 80)])


@pytest.mark.asyncio
async def test_markup_leak_retried_then_clean_answer():
    """Markup-as-content turn → silent retry with corrective nudge → clean answer."""
    turn1 = _FakeStream([
        _chunk(tool_calls=[_tc(0, id="c1", name="sql_query", arguments='{"query": "SELECT MIN(salary) FROM employees"}')]),
    ])
    turn3 = _FakeStream([_chunk(content="The minimum salary is $60,053 across active employees.")])

    sql = _FakeTool([ToolResult(tool_name="sql_query", success=True,
                                data={"rows": [{"min": 60053}], "total_rows": 1})])
    loop = _loop_with([turn1, _leak_stream(), turn3], {"sql_query": sql})

    events = await _collect(loop)
    tokens = "".join(e.payload["text"] for e in events if e.kind == "token")
    assert "DSML" not in tokens
    assert "minimum salary" in tokens

    calls = loop._client.chat.completions.create.call_args_list
    assert len(calls) == 3
    third_messages = calls[2].kwargs["messages"]
    assert any(
        m.get("role") == "system" and "tool-call markup" in (m.get("content") or "")
        for m in third_messages
    )
    # The leaked turn contributed no plan_step/tool_start of its own
    assert sum(1 for e in events if e.kind == "tool_start") == 1


@pytest.mark.asyncio
async def test_markup_leak_twice_emits_fallback_stream():
    """Markup leaks on the retry too → fallback_stream carrying collected results."""
    turn1 = _FakeStream([
        _chunk(tool_calls=[_tc(0, id="c1", name="sql_query", arguments='{"query": "SELECT AVG(salary) FROM employees"}')]),
    ])
    sql = _FakeTool([ToolResult(tool_name="sql_query", success=True,
                                data={"rows": [{"avg": 126683.78}], "total_rows": 1})])
    loop = _loop_with([turn1, _leak_stream(), _leak_stream()], {"sql_query": sql})

    events = await _collect(loop)
    assert events[-1].kind == "fallback_stream"
    payload = events[-1].payload
    assert payload["results"] and payload["results"][0]["tool"] == "sql_query"
    tokens = "".join(e.payload["text"] for e in events if e.kind == "token")
    assert "DSML" not in tokens


@pytest.mark.asyncio
async def test_short_markup_leak_does_not_flush():
    """A short leaked-markup turn (below the answer threshold) is retried, never flushed."""
    turn1 = _FakeStream([_chunk(content="<｜｜DSML｜｜tool_calls>")])
    turn2 = _FakeStream([_chunk(content="Hello! How can I help you today?")])
    loop = _loop_with([turn1, turn2], {})

    events = await _collect(loop, "hi")
    tokens = "".join(e.payload["text"] for e in events if e.kind == "token")
    assert "DSML" not in tokens
    assert "How can I help" in tokens
    assert len(loop._client.chat.completions.create.call_args_list) == 2


# ── Tool picker (forced tool) ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forced_tool_adds_system_instruction():
    """forced_tool → system message tells the model to use that specific tool."""
    turn1 = _FakeStream([_chunk(content="Let me search the web for that.")])

    loop = _loop_with([turn1], {})
    await _collect(loop, "latest postgresql version", forced_tool="web_search")

    create_messages = loop._client.chat.completions.create.call_args.kwargs["messages"]
    system = next(m["content"] for m in create_messages if m["role"] == "system")
    assert "explicitly selected" in system
    assert "web_search" in system


# ── Report briefing flow (loop-native report generation) ────────────────────

@pytest.mark.asyncio
async def test_report_briefing_observation_reaches_model():
    """generate returns a briefing → loop feeds it back → model runs the plan's SQL → report answer."""
    turn1 = _FakeStream([
        _chunk(tool_calls=[_tc(0, id="c1", name="report_generator", arguments='{"action": "generate", "report_id": 7}')]),
    ])
    turn2 = _FakeStream([
        _chunk(tool_calls=[_tc(0, id="c2", name="sql_query", arguments='{"query": "SELECT status, COUNT(*) FROM support_tickets GROUP BY status"}')]),
    ])
    turn3 = _FakeStream([_chunk(content="# Ticket Report\n## Overview\n57 tickets are open.")])

    briefing = ToolResult(
        tool_name="report_generator",
        success=True,
        data={
            "report_id": 7,
            "title": "Ticket Report",
            "sections": ["Overview"],
            "sql_queries": ["SELECT status, COUNT(*) FROM support_tickets GROUP BY status"],
            "instructions": "Execute this plan NOW.",
        },
    )
    report = _FakeTool([briefing])
    sql = _FakeTool([ToolResult(tool_name="sql_query", success=True,
                                data={"rows": [{"status": "Open", "count": 57}], "total_rows": 1})])
    loop = _loop_with([turn1, turn2, turn3], {"report_generator": report, "sql_query": sql})

    events = await _collect(loop, "Generate report #7: Ticket Report")

    # The briefing observation was fed back to the model before turn 2
    second_call = loop._client.chat.completions.create.call_args_list[1]
    tool_msgs = [m for m in second_call.kwargs["messages"] if m.get("role") == "tool"]
    assert any("sql_queries" in m["content"] and "Execute this plan NOW" in m["content"] for m in tool_msgs)

    # Both tools ran, and the final answer is the report
    starts = [e.payload["tool"] for e in events if e.kind == "tool_start"]
    assert starts == ["report_generator", "sql_query"]
    tokens = "".join(e.payload["text"] for e in events if e.kind == "token")
    assert "# Ticket Report" in tokens and "57" in tokens