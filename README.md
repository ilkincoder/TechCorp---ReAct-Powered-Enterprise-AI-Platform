# TechCorp Enterprise AI Platform

An enterprise AI assistant that answers questions over live company data by **reasoning, selecting tools, and grounding every answer in real sources** — a ReAct agent loop orchestrating SQL, hybrid RAG, sandboxed Python, web search, persistent memory, and a human-approved report pipeline, with full step-by-step transparency in the UI.

```
User → ReAct Agent Loop → Tool Selection → Execution (SQL / RAG / Python / Web / Memory)
     → Grounded, Cited Answer  +  Live Transparency Panel (plan, steps, sources, latency)
```

## What it does

Ask it anything about the company — *"How many open incidents are critical?"*, *"What's our production access policy?"*, *"Generate a report on support ticket aging"* — and it:

1. **Plans** which tools it needs (deterministic fast-paths for simple queries, LLM tool-calling for the rest)
2. **Executes** them with role-based access control, self-correcting failed SQL along the way
3. **Streams** a cited answer token-by-token, while an Insights panel shows every step: the plan, each tool call, its runtime, and the sources used

## Agent tools

| Tool | Backing | What it does |
|------|---------|--------------|
| `sql_query` | PostgreSQL 16 (17 tables) | Structured company data — employees, tickets, incidents, projects, customers |
| `rag_search` | Qdrant | Hybrid search over policy PDFs: dense (MiniLM) + sparse (SPLADE) + cross-encoder reranking |
| `python_execute` | Sandboxed runtime | Data analysis and calculations on retrieved data |
| `web_search` | DuckDuckGo | Current external information |
| `memory` | PostgreSQL + Qdrant | Persistent semantic memory across conversations — store facts, recall them in any future session |
| `report_generator` | Full pipeline | Two-phase, human-approved business reports (see below) |

## Human-in-the-loop report pipeline

The most involved flow in the platform:

1. **Propose** — a planner LLM receives the *live database schema* (`information_schema`) and submits a structured plan (sections + SQL queries) via a tool call, validated with Pydantic and retried with error feed-forward on failure. Nothing invalid ever reaches the user.
2. **Approve** — the UI renders the proposal summary with Approve / Reject. Rejecting invites the user to describe exactly what they want instead.
3. **Execute** — on approval, the *agent loop itself* runs the saved plan: each SQL query is a visible, RBAC-gated, self-correcting tool step.
4. **Deliver** — the finished report is persisted server-side and appears on the Reports page; the chat receives only a completion notice, never a wall of text.

## Engineering highlights

Decisions and hard-won fixes worth reading the code for:

- **Loop-native orchestration** — report generation originally lived in a nested mini-pipeline inside the tool (its own planner, SQL runner, RAG search). It was rebuilt to run *through* the main agent loop, eliminating duplicated logic, closing an RBAC bypass, and gaining SQL self-correction and per-step UI transparency for free.
- **Reasoning-model realities** — the LLM's hidden reasoning tokens count against `max_tokens` (diagnosed via `finish_reason: "length"` truncating plan JSON mid-string), and thinking mode rejects forced `tool_choice`. The propose pipeline works around both: generous token budgets, `auto` tool choice with a must-call contract, truncation detection *before* parsing, and bounded retries that feed the exact error back to the model.
- **Stream classification guard** — reasoning models occasionally emit their native tool-call token markup as plain text. The loop detects the leak before committing to "answer" mode, silently retries the turn with a corrective message, and degrades to combiner synthesis if it recurs — raw markup can never reach the user.
- **Deterministic persistence** — report content is saved by the server when the stream completes, never by asking the model to call a "save" tool. State changes don't depend on LLM compliance.
- **RBAC at the tool layer** — per-role table and knowledge-base department gates (`apply_rbac`) enforced on every tool call, not just in the prompt.
- **Tiered routing** — deterministic fast-paths (explicit SQL, memory statements, gibberish) skip the LLM entirely; everything else goes through native tool calling with pre-query name disambiguation.

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI · Python 3.14 · SSE streaming |
| LLM | DeepSeek V4 Pro (OpenAI-compatible API, native tool calling) |
| Database | PostgreSQL 16 |
| Vector store | Qdrant (dense + sparse collections) |
| Embeddings | all-MiniLM-L6-v2 · SPLADE · ms-marco cross-encoder (all local) |
| Frontend | React 19 · Vite · Tailwind · SSE client with live tool progress |
| Infra | Docker Compose (app + PostgreSQL + Qdrant) |
| Testing | pytest — 20 unit tests with fully mocked LLM streams |

## Quick start

**Prerequisites:** Docker, Node 18+, a DeepSeek API key.

```bash
# 1. Configure — copy the template and fill in the secrets
#    (DEEPSEEK_API_KEY and POSTGRES_PASSWORD are required)
cp .env.example .env

# 2. Start the stack (app + PostgreSQL + Qdrant; DB auto-seeds from data/*.csv)
docker compose up -d --build

# 3. Index the knowledge base PDFs into Qdrant (incremental on re-runs)
docker compose exec app python scripts/index_knowledge_base.py

# 4. Frontend
cd frontend && npm install && npm run dev
```

Open **http://localhost:5173** — Dashboard first, then **Chat** to talk to the agent. Backend sanity check: `curl http://localhost:8000/health`.

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/query/stream` | SSE streaming query — events: `plan`, `tool_start`, `tool_result`, `token`, `sources`, `done` |
| `GET/POST` | `/conversations` | List / create conversations |
| `GET/DELETE` | `/conversations/{id}` | Fetch with messages / delete |
| `GET` | `/reports` · `/reports/{id}` | Generated reports |
| `GET` | `/dashboard/stats` | Aggregated dashboard metrics |
| `GET` | `/tools` · `/tools/{name}` | Tool schemas |
| `GET` | `/health` | Health check |

## Testing

```bash
python -m pytest tests/test_react_loop.py tests/test_report_tool.py -q   # 20 tests
```

Unit tests mock the LLM stream chunk-by-chunk to cover the loop's hard paths: parallel tool calls, SQL retry synthesis, RBAC denials, argument validation, max-iteration forcing, markup-leak recovery, and the report briefing flow. [`UI_TEST_SCENARIOS.md`](UI_TEST_SCENARIOS.md) contains the manual end-to-end test plan — one scenario per tool, all passing.

## Project structure

```
techcorp_platform/
├── app.py                # FastAPI endpoints, SSE orchestration, report persistence
├── conversations.py      # PostgreSQL persistence (conversations, memory, reports)
├── agent/
│   ├── react.py          # ReAct loop — native tool calling, streaming, leak guard
│   ├── planner.py        # Tier-1 deterministic routing (no LLM)
│   ├── combiner.py       # Result synthesis / fallback streaming
│   ├── rbac.py           # Role permissions + per-tool-call gates
│   └── tool_params.py    # Pydantic validation of model-emitted tool arguments
├── tools/                # The 6 agent tools
frontend/src/             # React SPA — chat, dashboard, reports, insights panel
scripts/                  # init_db.py (seed), index_knowledge_base.py (RAG index)
data/                     # Seed CSVs (17 tables)
knowledge_base/           # Policy PDFs by department
tests/                    # pytest suites (mocked LLM streams)
```

## Roadmap

- Report export (PDF/download) and scheduled briefings
- Document upload → auto-indexed into RAG
- Conversation search and agent execution timeline
- Cost-per-query tracking

---

*Built as a hands-on deep dive into agentic AI engineering: tool-calling loops, hybrid retrieval, human-in-the-loop workflows, and the practical failure modes of reasoning LLMs in production.*