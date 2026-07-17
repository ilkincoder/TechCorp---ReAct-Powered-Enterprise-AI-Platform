"""Tool base class — all tools implement this interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Standardized output from any tool."""
    tool_name: str
    success: bool
    data: Any = None
    error: str = ""
    citations: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "tool": self.tool_name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "citations": self.citations,
            "metadata": self.metadata,
        }


class BaseTool(ABC):
    """Every tool in the platform extends this."""

    name: str = "base"
    description: str = ""

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        ...

    def schema(self) -> dict:
        """Return the tool schema for LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self._input_schema(),
        }

    @abstractmethod
    def _input_schema(self) -> dict:
        """JSON Schema for the tool's input parameters."""
        ...