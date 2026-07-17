# UI Test Scenarios — Manual Tool Verification

Manual test plan for the 6 agent tools, exercised through the chat UI. One scenario per tool.

## Setup (once, before testing)

1. Start the stack: `docker compose up --build` (app + PostgreSQL + Qdrant).
2. Index the knowledge base (required for Scenario 1):
   `docker compose exec app python scripts/index_knowledge_base.py`
3. Start the frontend: `cd frontend && npm install && npm run dev`
4. Open **http://localhost:5173** → click **Chat**.
5. Backend sanity check: `curl http://localhost:8000/health` → `200`.

## How to verify which tool ran

After every answer, open the **Insights panel** (right side; on narrow windows it overlays — click to expand):

- **Plan** — the steps the agent chose.
- **Tools used** — each tool listed with `✓` (success) or `✖` (error).
- **Sources** — citation count and list.
- **Latency** — response time.

A scenario **passes** only if the expected tool shows `✓` in "Tools used" AND the answer content matches the expectation below.

---

## Scenario 1 — `rag_search` (knowledge base / PDF policies)

**Prompt:** `What is our production access policy?`

**Alternate:** `How does the customer escalation process work?`

**Expected:**
- Plan shows a `rag_search` step; "Tools used" shows `✓ rag_search`.
- Answer is grounded in the policy PDF (Security / Customer_Support department docs), streamed token by token.
- **Sources** panel lists at least 1 citation with a PDF filename (e.g. `08_TechCorp_Production_Access_Policy.pdf`).

**Fail signs:** 0 sources, generic answer not tied to a document, or `web_search` used instead.

---

## Scenario 2 — `sql_query` (structured database)

**Prompt:** `How many employees are in the database?`

**Alternate:** `List the 5 highest-paid active employees with their job titles.`

**Expected:**
- "Tools used" shows `✓ sql_query`.
- Answer contains concrete numbers/rows consistent with the seeded data (e.g. employee names like David Williams — CEO).
- Asking a follow-up (`And how many are in each department?`) also routes to `sql_query` and returns a per-department breakdown.

**Fail signs:** the model invents numbers with no `sql_query` in "Tools used".

---

## Scenario 3 — `python_execute` (sandboxed analysis)

**Prompt:** `Use Python to calculate the year-over-year growth if revenue went from 1.2M to 1.8M.`

**Alternate:** `Analyze the salary distribution of employees with Python — min, max, mean, median.` (should chain `sql_query` → `python_execute`)

**Expected:**
- "Tools used" shows `✓ python_execute` (alternate: both `✓ sql_query` and `✓ python_execute`).
- Answer contains the computed result (50% growth for the primary prompt), not an estimate.

**Fail signs:** answer computed "in the model's head" with no `python_execute` in "Tools used".

---

## Scenario 4 — `web_search` (live internet, DuckDuckGo)

**Precondition:** container has internet access; `.env` has `SEARCH_PROVIDER=duckduckgo` (default).

**Prompt:** `What is the latest stable version of PostgreSQL right now?`

**Alternate:** `Search the web for current news about enterprise AI regulations.`

**Expected:**
- "Tools used" shows `✓ web_search`.
- Answer references current external information; result titles/URLs appear in the answer or Sources.

**Fail signs:** answer from stale internal knowledge with no `web_search` step; `✖ web_search` (usually network/rate-limit — retry once; a `tool_retry` badge may appear first).

---

## Scenario 5 — `memory` (persistent store + semantic search)

**Step A — store.**
**Prompt:** `Remember that the Q3 platform migration deadline is September 30.`

**Expected:** "Tools used" shows `✓ memory`; answer acknowledges with "Got it — I've noted that. ✓".

**Step B — recall in a NEW conversation.**
Start a new conversation (sidebar → new chat), then:
**Prompt:** `What do you remember about the Q3 migration?`

**Expected:**
- "Tools used" shows `✓ memory`.
- Answer returns the stored fact (September 30 deadline) — proving persistence across conversations (PostgreSQL + Qdrant), not chat history.

**Fail signs:** Step B answers "I don't have any stored memories" or relies on visible chat history instead of the memory tool.

---

## Scenario 6 — `report_generator` (two-phase: propose → approve → generate)

**Prompt:** `Generate a report on the current state of support tickets and open incidents.`

**Expected — Phase 1 (propose):**
- An **approval card** appears in chat: "Generate report: **<title>**?" with **✓ Approve** / decline buttons. No report is created yet.

**Action:** click **✓ Approve** (this sends `Generate report #<id>: <title>` automatically).

**Expected — Phase 2 (generate):**
- Chat immediately shows **"✅ Report approved — generating the report now…"** — generation reuses the SAME report id; a new proposal card or new report ID after Approve is a **FAIL**.
- Insights panel shows the individual data steps live: `✓ report_generator` plus `✓ sql_query` (and `memory`/`rag_search` if planned) — one step per query.
- When finished, chat shows **"Report #N is ready — please check the Reports section for the final version."** The **full report text must NOT appear in chat**.
- Navigate to the **Reports** page (`/reports`): the report first appears under "Generating…", then flips to done (page polls every 10s). Content has real numbers and today's date.

**Step B — reject flow.** Start a fresh report request, and click **✗ Reject** on the proposal card.

**Expected:**
- The card disappears and a notice appears in chat inviting you to describe the exact report you want.
- Typing a refined description (e.g. `Only critical tickets, grouped by team`) produces a NEW proposal card reflecting it.

**Fail signs:** report generated without the approval card; clicking Approve creates another proposal instead of generating; stored report empty or dated in the past.

---

## Optional cross-check — RBAC (affects all tools)

If a role is active (Engineering Admin / Sales Intern / Support Agent), repeat Scenario 2 with a table forbidden for that role (e.g. as **Sales Intern**: `Show me all employee salaries`).
**Expected:** access is refused per role restrictions rather than returning the data.

## Result log

| # | Tool             | Date | Pass/Fail | Notes |
|---|------------------|------|-----------|-------|
| 1 | rag_search       |      | Pass      |       |
| 2 | sql_query        |      | Pass      |       |
| 3 | python_execute   |      | Pass      |       |
| 4 | web_search       |      | Pass      |       |
| 5 | memory           |      | Pass      |       |
| 6 | report_generator |      | Pass      |       |
