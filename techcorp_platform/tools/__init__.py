"""Tool registry — all tools available to the agent."""

from .base import BaseTool, ToolResult
from .rag_tool import RAGTool
from .sql_tool import SQLTool
from .python_tool import PythonTool
from .web_search_tool import WebSearchTool
from .memory_tool import MemoryTool
from .report_tool import ReportTool


def get_all_tools() -> list[BaseTool]:
    """Return initialized instances of all available tools."""
    return [
        RAGTool(),
        SQLTool(),
        PythonTool(),
        WebSearchTool(),
        MemoryTool(),
        ReportTool(),
    ]


def get_tool_schemas() -> list[dict]:
    """Return Anthropic-compatible tool schemas for all tools."""
    return [t.schema() for t in get_all_tools()]


def get_tool_map() -> dict[str, BaseTool]:
    """Return name → tool instance mapping."""
    return {t.name: t for t in get_all_tools()}


__all__ = [
    "BaseTool", "ToolResult",
    "RAGTool", "SQLTool", "PythonTool", "WebSearchTool",
    "MemoryTool", "ReportTool",
    "get_all_tools", "get_tool_schemas", "get_tool_map",
]