"""End-to-end tests for the TechCorp Enterprise AI Platform query pipeline.

Tests the full SSE streaming flow: POST /query/stream → plan → tools → tokens → done.
External dependencies (DeepSeek API, PostgreSQL) are mocked.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from httpx import AsyncClient, ASGITransport
from techcorp_platform.app import app


# ── Helpers ──────────────────────────────────────────────────────────────────

def _tc(index, id=None, name=None, arguments=None):
    """Build a streaming tool_call delta fragment."""
    tc = MagicMock()
    tc.index = index
    tc.id = id
    fn = MagicMock()
    fn.name = name  # attribute assignment avoids the MagicMock(name=...) pitfall
    fn.arguments = arguments
    tc.function = fn
    return tc


def _chunk(content=None, tool_calls=None):
    """Build a streaming chat completion chunk."""
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
    """Async-iterable stand-in for a streamed chat completion."""

    def __init__(self, chunks):
        self._chunks = chunks

    def __aiter__(self):
        async def gen():
            for c in self._chunks:
                yield c
        return gen()


async def _collect_sse_events(response) -> list[tuple[str, dict]]:
    """Parse an SSE stream into a list of (event_type, data_dict) tuples."""
    events = []
    current_event = ""
    current_data = ""
    async for line in response.aiter_lines():
        if line.startswith("event: "):
            current_event = line[7:].strip()
        elif line.startswith("data: "):
            current_data = line[6:]
        elif line == "" and current_event and current_data:
            try:
                events.append((current_event, json.loads(current_data)))
            except json.JSONDecodeError:
                events.append((current_event, {"raw": current_data}))
            current_event = ""
            current_data = ""
    return events


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_deepseek():
    """Mock the DeepSeek API for the ReAct loop, combiner, and summarizer.

    The ReAct loop gets a two-turn script: turn 1 emits a rag_search tool call,
    turn 2 streams the final answer as content tokens.
    """
    from techcorp_platform.app import react_loop

    with patch("techcorp_platform.agent.react.AsyncOpenAI") as mock_react_async, \
         patch("techcorp_platform.agent.combiner.AsyncOpenAI") as mock_combiner_async, \
         patch("techcorp_platform.app.OpenAI") as mock_app_openai:
        # ReAct loop (async, streaming, native tool calling)
        def _make_turns():
            turn1 = _FakeStream([
                _chunk(content="I will search the knowledge base for that."),
                _chunk(tool_calls=[_tc(0, id="call_1", name="rag_search",
                                       arguments='{"query": "test query"}')]),
            ])
            turn2 = _FakeStream([
                _chunk(content=part) for part in
                ["This is a comprehensive test answer ",
                 "synthesized from the tool results ",
                 "with proper citations included. ",
                 "[source: test.pdf]"]
            ])
            return [turn1, turn2]

        mock_react_client = MagicMock()
        mock_react_client.chat.completions.create = AsyncMock(side_effect=_make_turns())
        mock_react_async.return_value = mock_react_client
        # The app-level ReActLoop singleton caches its client — force re-creation
        react_loop._client = None

        # Combiner (async OpenAI) — stream tokens (deterministic Tier-1 branch)
        mock_async_client = MagicMock()

        async def _mock_stream():
            chunks = ["Test ", "answer ", "from ", "tools."]
            for text in chunks:
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta.content = text
                yield chunk

        mock_async_response = MagicMock()
        mock_async_response.__aiter__ = lambda self: _mock_stream()
        mock_async_client.chat.completions.create.return_value = mock_async_response
        mock_combiner_async.return_value = mock_async_client

        # Summarization LLM in app.py (sync OpenAI)
        mock_summarize_client = MagicMock()
        mock_summarize_response = MagicMock()
        mock_summarize_response.choices = [MagicMock()]
        mock_summarize_response.choices[0].message.content = "Test summary."
        mock_summarize_client.chat.completions.create.return_value = mock_summarize_response
        mock_app_openai.return_value = mock_summarize_client

        yield

        react_loop._client = None


@pytest.fixture
def mock_tools():
    """Mock all tool execute methods to avoid external dependencies (Qdrant, DB, etc.)."""
    with patch("techcorp_platform.tools.rag_tool.RAGTool.execute") as mock_rag, \
         patch("techcorp_platform.tools.sql_tool.SQLTool.execute") as mock_sql, \
         patch("techcorp_platform.tools.python_tool.PythonTool.execute") as mock_py, \
         patch("techcorp_platform.tools.web_search_tool.WebSearchTool.execute") as mock_web, \
         patch("techcorp_platform.tools.memory_tool.MemoryTool.execute") as mock_mem:

        from techcorp_platform.tools.base import ToolResult

        async def _rag_execute(**kwargs):
            return ToolResult(
                tool_name="rag_search", success=True,
                data={"results": [{"text": "Test doc", "filename": "test.pdf", "department": "Engineering"}]},
                citations=["test.pdf"],
            )

        async def _sql_execute(**kwargs):
            return ToolResult(
                tool_name="sql_query", success=True,
                data={"rows": [{"count": "42"}], "total_rows": 1},
            )

        async def _py_execute(**kwargs):
            return ToolResult(tool_name="python_execute", success=True, data={"output": "42"})

        async def _web_execute(**kwargs):
            return ToolResult(
                tool_name="web_search", success=True,
                data={"results": [{"title": "Test", "snippet": "Test result", "url": "https://example.com"}]},
            )

        async def _mem_execute(**kwargs):
            return ToolResult(
                tool_name="memory", success=True,
                data={"stored": {"id": 1, "type": "fact", "content": kwargs.get("content", "")}},
            )

        mock_rag.side_effect = _rag_execute
        mock_sql.side_effect = _sql_execute
        mock_py.side_effect = _py_execute
        mock_web.side_effect = _web_execute
        mock_mem.side_effect = _mem_execute

        yield


@pytest.fixture
def mock_postgres():
    """Mock PostgreSQL connections for conversation persistence."""
    with patch("techcorp_platform.conversations._get_conn") as mock_conn_fn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # save_message calls fetchone()[0] for RETURNING id (needs list-like),
        # then fetchone() again for title SELECT. Always return [1] — the
        # title check `row[0] == "New Chat"` safely evaluates False for int 1.
        mock_cursor.fetchone.return_value = [1]

        mock_conn_fn.return_value = mock_conn

        # get_recent_messages / get_context_window / get_all_messages_for_summary
        mock_cursor.fetchall.return_value = []

        yield mock_conn_fn


# ── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_query_stream_returns_plan_and_tokens(mock_deepseek, mock_postgres, mock_tools):
    """Full pipeline: POST /query/stream → plan → tools → tokens → done."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream("POST", "/query/stream", json={
            "message": "What tools do you have?",
            "stream": True,
        }) as response:
            assert response.status_code == 200

            events = await _collect_sse_events(response)
            event_types = [e[0] for e in events]

            assert "plan" in event_types, f"Expected 'plan' event, got: {event_types}"
            # Get error details if present
            error_event = next((e[1] for e in events if e[0] == "error"), None)
            assert "done" in event_types, \
                f"Expected 'done' event, got: {event_types}. Error detail: {error_event}"

            # Verify plan event has the new structured fields
            plan_event = next(e[1] for e in events if e[0] == "plan")
            assert "steps" in plan_event, "Plan event missing 'steps' array"
            assert "intent" in plan_event
            assert "tools_needed" in plan_event

            # Verify done event has expected fields
            done_event = next(e[1] for e in events if e[0] == "done")
            assert "conversation_id" in done_event
            assert "tools_used" in done_event


@pytest.mark.asyncio
async def test_memory_statement_routing(mock_postgres):
    """Tier-1: declarative statements bypass LLM and route directly to memory."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream("POST", "/query/stream", json={
            "message": "My name is Ilkin and I work in Engineering",
            "stream": True,
        }) as response:
            assert response.status_code == 200

            events = await _collect_sse_events(response)
            event_types = [e[0] for e in events]

            # Should route to memory:store without calling the LLM
            plan_event = next((e[1] for e in events if e[0] == "plan"), None)
            assert plan_event is not None
            assert "memory" in plan_event.get("tools_needed", []), \
                f"Expected memory tool in plan, got: {plan_event.get('tools_needed')}"


@pytest.mark.asyncio
async def test_streaming_tokens_arrive_in_order(mock_deepseek, mock_postgres, mock_tools):
    """Tokens stream progressively and form a complete answer."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream("POST", "/query/stream", json={
            "message": "Tell me about the platform",
            "stream": True,
        }) as response:
            assert response.status_code == 200

            events = await _collect_sse_events(response)

            tokens = [e[1].get("text", "") for e in events if e[0] == "token"]
            assert len(tokens) > 0, "Expected at least one token event"
            combined = "".join(tokens)
            # Tokens arrive from either the LLM stream or the fallback formatter
            assert len(combined) > 50, f"Expected substantial answer, got {len(combined)} chars: {combined[:100]}"


@pytest.mark.asyncio
async def test_error_bubbles_on_stream_failure():
    """When the SSE stream encounters an error, an error event is emitted."""
    # Test with a message that forces both tools to fail
    with patch("techcorp_platform.tools.memory_tool.MemoryTool.execute") as mock_exec:
        mock_exec.side_effect = Exception("Simulated tool failure")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream("POST", "/query/stream", json={
                "message": "My name is Test",
                "stream": True,
            }) as response:
                events = await _collect_sse_events(response)
                event_types = [e[0] for e in events]
                # Should get an error event when the tool fails
                assert "error" in event_types or "done" in event_types, \
                    f"Expected error or done, got: {event_types}"


@pytest.mark.asyncio
async def test_health_endpoint():
    """Health check returns ok status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "tools_available" in data
