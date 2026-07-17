"""Adapters between BaseTool schemas / results and the OpenAI function-calling format."""

import json


def to_openai_tools(tool_schemas: list[dict]) -> list[dict]:
    """Convert Anthropic-style {name, description, input_schema} schemas
    into the OpenAI function-calling `tools=` format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
            },
        }
        for t in tool_schemas
    ]


def serialize_observation(result_dict: dict, max_chars: int = 4000) -> str:
    """Serialize a ToolResult dict into a `role:"tool"` message payload.

    Caps size so multi-turn loops don't blow up the context: SQL rows are
    truncated to 50 (total_rows preserved), and the final JSON is capped
    at max_chars with success/error always kept intact.
    """
    obs = {
        "tool": result_dict.get("tool"),
        "success": result_dict.get("success"),
        "error": result_dict.get("error", ""),
        "data": result_dict.get("data"),
        "citations": result_dict.get("citations", []),
    }

    data = obs["data"]
    if isinstance(data, dict) and isinstance(data.get("rows"), list) and len(data["rows"]) > 50:
        obs["data"] = {**data, "rows": data["rows"][:50], "rows_truncated": True}

    text = json.dumps(obs, default=str)
    if len(text) > max_chars:
        # Replace the data payload with a truncated string rather than cutting
        # the JSON envelope mid-structure.
        obs["data"] = json.dumps(obs["data"], default=str)[: max_chars // 2] + "…(truncated)"
        text = json.dumps(obs, default=str)
    return text


def summarize_result(result: dict) -> str:
    """Create a one-line summary of a tool result for streaming display."""
    tool = result.get("tool", "")
    data = result.get("data") or {}
    if tool == "rag_search":
        count = len(data.get("results", []))
        return f"Found {count} document{'' if count == 1 else 's'}"
    elif tool == "sql_query":
        total = data.get("total_rows", 0)
        return f"Returned {total} row{'' if total == 1 else 's'}"
    elif tool == "python_execute":
        out = data.get("output", "")
        return out[:100].replace("\n", " ") if out else "Code executed"
    elif tool == "web_search":
        count = len(data.get("results", []))
        return f"Found {count} web result{'' if count == 1 else 's'}"
    elif tool == "memory":
        count = len(data.get("results", []))
        return f"Found {count} memor{'y' if count == 1 else 'ies'}"
    elif tool == "report_generator":
        if data.get("requires_approval"):
            return f"Report proposal: {data.get('title', 'Untitled')}"
        return f"Report: {data.get('title', 'Untitled')}"
    return "Done"