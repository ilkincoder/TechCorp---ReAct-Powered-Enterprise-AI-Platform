"""Result Combiner — merges tool outputs into grounded answer via DeepSeek V4 Pro."""

import asyncio
import json
from openai import AsyncOpenAI

from ..config import DEEPSEEK_MODEL, get_async_openai_client


def _format_context_block(summary: str = "", recent: list[dict] | None = None) -> str:
    """Format conversation context (summary + recent messages) into a prompt block.

    Mirrors the format used by PlannerAgent.
    """
    parts = []
    if summary:
        parts.append(f"## Conversation Summary\n{summary}")
    if recent:
        history_lines = []
        for msg in recent:
            label = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"] if msg["role"] == "user" else msg["content"][:300]
            history_lines.append(f"{label}: {content}")
        parts.append("## Recent Messages\n" + "\n".join(history_lines) +
            "\n\nUse the summary and recent messages to answer questions about what was previously said.")
    return "\n\n".join(parts) if parts else ""


def _inject_role_context(system_prompt: str, role: str | None) -> str:
    """Prepend role-awareness instructions to the combiner system prompt.

    This is defense-in-depth: ensures the combiner doesn't accidentally reveal
    restricted data that might have slipped through tool-level enforcement.
    """
    if not role or role == 'engineering_admin':
        return system_prompt

    role_labels = {
        'sales_intern': 'Sales Intern',
        'support_agent': 'Support Agent',
    }
    label = role_labels.get(role, role)
    role_note = (
        f"## Current Access Level\n"
        f"You are responding as a **{label}**. "
        f"If the tool results contain data the user should not see at this access level, "
        f"do not include it in your answer. Instead, note that the information is outside "
        f"the current access scope.\n\n"
    )
    return role_note + system_prompt


COMBINER_GROUNDING_RULES = """1. Every factual claim must cite its source — use [source: filename] or [source: SQL query].
2. If tool results conflict, note the discrepancy.
3. Structure: summary first, then details, then sources.
4. **CRITICAL — Missing or unavailable data**: If a SQL query failed because the requested
   column or table does not exist in the database, do NOT improvise, guess, or fall back to
   similar data (e.g., do NOT show emails when the user asked for phone numbers). Acknowledge
   the limitation clearly and briefly. Do not suggest alternatives or workarounds unless
   the user explicitly asks for them.
5. If the user asks what tools you have or what you can do, answer from the platform description
   above — do NOT say you have no information. You ARE the platform.
6. If tool results are empty or not relevant, fall back to what you know about the platform
   and suggest what the user might try (e.g., "I searched the knowledge base but found no
   relevant documents. You could try asking about a specific policy or querying the database.").
7. Be natural, not robotic. No LaTeX or formula blocks, no bullet-point walls unless the user
   explicitly asked for a list. Write like a colleague explaining something in Slack —
   direct, conversational, brief."""


COMBINER_SYSTEM_PROMPT = f"""You are the TechCorp Enterprise AI assistant — a capable, natural-sounding
colleague who answers questions by synthesizing tool results into clear, conversational replies.
Lead with the answer; keep it brief; cite sources only when they add real weight. Speak like a
human explaining something to a coworker, not a report.

## About the TechCorp AI Platform
You have access to these tools:
- **rag_search** — Search the internal knowledge base (company policies, engineering standards,
  compliance docs, HR guides, IT procedures, security policies, onboarding, and more across
  departments: AI, Engineering, HR, IT, Legal, Finance, Sales, Marketing, Operations, Security,
  Customer_Support).
- **sql_query** — Query structured business data in PostgreSQL. 17 tables available:
  employees, departments, customers, products, subscriptions, projects, support_tickets,
  incident_reports, jira_issues, meeting_schedule, meeting_notes, internal_emails,
  slack_conversations, company_announcements, audit_logs, change_requests, release_notes.
- **python_execute** — Run Python code in a sandbox for data analysis, charts, calculations.
- **web_search** — Search the external internet for current events, industry news, competitors.
- **memory** — Store and recall facts across conversations (persistent memory).

## Rules
{COMBINER_GROUNDING_RULES}
"""


def _is_fast_path(result: dict) -> bool:
    """Return True if a single successful tool result can skip LLM synthesis.

    RAG search and memory search need the LLM to synthesize chunks/entries
    into a coherent answer. Memory store (has "stored" key) and other tools
    can use the fast formatting path.
    """
    if not result.get("success"):
        return False
    tool = result.get("tool", "")
    if tool in ("rag_search",):
        return False
    if tool == "memory":
        data = result.get("data") or {}
        # Store has "stored" key — fast acknowledgement is fine.
        # Search has "results" key — needs LLM synthesis.
        if "stored" not in data:
            return False
    return True


class ResultCombiner:
    """Synthesizes multiple tool outputs into a single grounded answer using DeepSeek."""

    def __init__(self, model: str | None = None):
        self.model = model or DEEPSEEK_MODEL
        self._client = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = get_async_openai_client()
        return self._client

    async def combine_stream(
        self,
        user_message: str,
        tool_results: list[dict],
        intent: str = "",
        conversation_history: list[dict] | None = None,
        summary: str = "",
        role: str | None = None,
    ):
        """Async generator that yields answer text chunks for SSE streaming.

        For multi-tool results: streams DeepSeek output token-by-token via AsyncOpenAI.
        For single-tool results: yields formatted text in line-based chunks with
        small inter-chunk delays so the SSE client receives events progressively.
        """
        # Fast path: single tool result that doesn't need LLM synthesis.
        # RAG and memory-search always stream through the LLM for proper synthesis.
        if len(tool_results) == 1 and _is_fast_path(tool_results[0]):
            text = self._format_single_result(user_message, tool_results[0], conversation_history)
            for chunk in self._chunk_text(text):
                yield chunk
                # Let the event loop flush this chunk to the SSE client
                await asyncio.sleep(0.02)
            return

        # Multi-tool: stream DeepSeek output token-by-token via AsyncOpenAI
        try:
            client = self._get_client()
            results_json = json.dumps(tool_results, indent=2, default=str)
            user_content = (
                f"User question: {user_message}\n\n"
                f"Intent: {intent}\n\n"
                f"Tool results:\n{results_json}\n\n"
                "Synthesize a complete, cited answer."
            )
            # Inject context: summary + recent messages
            context_block = _format_context_block(summary, conversation_history)
            if context_block:
                user_content = context_block + "\n\n" + user_content

            system_prompt = _inject_role_context(COMBINER_SYSTEM_PROMPT, role)

            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=2048,
                temperature=0.1,
                stream=True,
            )
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception:
            # Fallback: yield graceful message when LLM is unreachable
            for chunk in self._chunk_text("I'm sorry — the system is currently unavailable. Please try again in a moment."):
                yield chunk
                await asyncio.sleep(0.02)

    def _chunk_text(self, text: str, chunk_size: int = 80):
        """Yield text in natural chunks (by line, then by word groups)."""
        lines = text.split("\n")
        for line in lines:
            if len(line) <= chunk_size:
                yield line + "\n"
            else:
                # Break long lines into word-group chunks
                words = line.split(" ")
                buf = ""
                for word in words:
                    if len(buf) + len(word) + 1 > chunk_size and buf:
                        yield buf + " "
                        buf = word
                    else:
                        buf = (buf + " " + word) if buf else word
                if buf:
                    yield buf + "\n"

    def _format_single_result(self, question: str, result: dict, conversation_history: list[dict] | None = None) -> str:
        """Format a single tool result."""
        data = result.get("data") or {}
        tool = result.get("tool", "unknown")

        if tool == "rag_search":
            chunks = data.get("results", [])
            if not chunks:
                return f"I searched the knowledge base but found no relevant information."
            answer = f"**Knowledge Base Results:**\n\n"
            for i, chunk in enumerate(chunks[:5], 1):
                answer += f"{i}. {chunk['text'][:500]}\n   *Source: {chunk.get('filename', 'unknown')} ({chunk.get('department', '')})*\n\n"
            return answer

        elif tool == "sql_query":
            rows = data.get("rows", [])
            total = data.get("total_rows", 0)
            if not rows:
                return f"Query returned no results."
            answer = f"**Database Results** ({total} rows):\n\n"
            if len(rows) <= 10:
                for row in rows:
                    answer += "- " + " | ".join(f"{k}: {v}" for k, v in list(row.items())[:6]) + "\n"
            else:
                answer += f"Showing {min(len(rows), 100)} of {total} rows:\n"
                for row in rows[:5]:
                    answer += "- " + " | ".join(f"{k}: {v}" for k, v in list(row.items())[:6]) + "\n"
            return answer

        elif tool == "python_execute":
            return f"**Python Output:**\n```\n{data.get('output', '(no output)')}\n```"

        elif tool == "web_search":
            results = data.get("results", [])
            if not results:
                return f"Web search returned no results."
            answer = f"**Web Search Results:**\n\n"
            for r in results[:5]:
                answer += f"- **{r.get('title', 'Untitled')}**\n  {r.get('snippet', '')[:300]}\n  {r.get('url', '')}\n\n"
            return answer

        elif tool == "memory":
            # Store action — acknowledge to the user
            if "stored" in data:
                return f"Got it — I've noted that. ✓"
            results = data.get("results", [])
            if not results:
                # Fallback: use conversation history if available
                if conversation_history:
                    answer = "I don't have any stored memories, but here's what was said recently in this conversation:\n\n"
                    for msg in conversation_history:
                        label = "You" if msg["role"] == "user" else "Assistant"
                        answer += f"**{label}:** {msg['content'][:300]}\n\n"
                    return answer
                return "No relevant memories found."
            answer = "**Memory Results:**\n\n"
            for m in results:
                answer += f"- [{m.get('type', 'fact')}] {m.get('content', '')}\n"
            return answer

        return f"Tool '{tool}' returned: {json.dumps(data, indent=2, default=str)[:1000]}"