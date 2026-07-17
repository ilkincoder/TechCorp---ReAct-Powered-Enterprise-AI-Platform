# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## Project Memory System

**Do NOT use Claude Code's built-in memory system** (the `memory/` directory with markdown files). This project has its own MemoryTool backed by PostgreSQL.

When you need to store or recall information across conversations:
- Use the **MemoryTool** (`action="store"` / `action="search"`) — it persists to Postgres
- Do NOT write to `memory/MEMORY.md` or create memory files in the `memory/` directory
- The `memory/` directory should remain empty at all times

## Token Cost Reference

Use this when evaluating whether a pattern, method, or feature is token-expensive. Answer briefly: verdict → why → cheaper alternative (if any).

### Expensive (avoid or cache aggressively)

| Pattern | Why |
|---|---|
| Large system prompts | Counted on every request — even if unchanged |
| Long conversation history | Full history re-sent each turn; grows linearly |
| Vision / image input | Images tile into many tokens (e.g. 1024×1024 ≈ 1600+ tokens) |
| PDF / document processing | Entire document text injected into context each call |
| Tool use with many iterations | Each tool call + result adds a full round-trip |
| Extended thinking | Thinking tokens billed but invisible |
| Agentic loops | Every step re-sends context + history + instructions |
| Many few-shot examples | Each example adds tokens to every request |

### Moderate

| Pattern | Notes |
|---|---|
| Streaming | Same token count as non-streaming — latency, not cost |
| Structured output (JSON mode) | Slightly more output tokens if schema verbose |
| Tool definitions | Schemas are input tokens — keep concise |
| Short system prompt examples | Moderate if brief; expensive with many long ones |

### Cheap

| Pattern | Why |
|---|---|
| Prompt caching | Cached prefix tokens billed at ~10% of normal input rate |
| Short single-turn calls | No history overhead; minimal context |
| Smaller models (Haiku) | Much lower per-token price |
| `max_tokens` output cap | Hard-caps output to avoid runaway costs |
| Batch API | ~50% cost reduction for non-real-time workloads |

### Quick Verdicts

- **Store full vs. summarized chat history?** → Summarize. Full history grows unbounded, re-billed every turn.
- **API in a loop (agent)?** → Expensive. Each iteration re-sends full context. Minimize depth, cache system prompt.
- **Streaming vs. normal call?** → No token difference. Streaming is latency, not price.
- **Pass full PDF every time?** → Expensive. Use RAG to extract only relevant chunks.
- **Vision input?** → Expensive. Resize/compress before sending.
- **Tool definitions?** → Slight cost. Keep schemas concise; remove unused tools.
- **Extended thinking worth it?** → Only when reasoning quality is critical. Thinking tokens are billed and hidden.