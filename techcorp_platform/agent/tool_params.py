"""Pydantic models validating tool-call arguments emitted by the model."""

import json
from typing import Literal

from pydantic import BaseModel, ValidationError


class SqlQueryParams(BaseModel):
    query: str


class RagSearchParams(BaseModel):
    query: str
    top_k: int = 5
    department: str | None = None
    filename: str | None = None
    allowed_departments: list[str] | None = None


class PythonExecuteParams(BaseModel):
    code: str


class WebSearchParams(BaseModel):
    query: str
    num_results: int = 5


class MemoryParams(BaseModel):
    action: Literal["store", "search", "recent", "clear"]
    query: str | None = None
    content: str | None = None
    entity_type: str | None = None
    confidence: float | None = None
    source: str | None = None
    limit: int | None = None


class ReportGeneratorParams(BaseModel):
    action: Literal["propose", "generate"]
    query: str | None = None
    report_id: int | None = None


_PARAM_MODELS: dict[str, type[BaseModel]] = {
    "sql_query": SqlQueryParams,
    "rag_search": RagSearchParams,
    "python_execute": PythonExecuteParams,
    "web_search": WebSearchParams,
    "memory": MemoryParams,
    "report_generator": ReportGeneratorParams,
}


def validate_tool_args(tool_name: str, raw_json: str) -> tuple[dict | None, str | None]:
    """Parse and validate a tool call's JSON arguments.

    Returns (params, None) on success or (None, error_message) on failure.
    The error message is fed back to the model as a tool observation so it
    can correct itself.
    """
    try:
        data = json.loads(raw_json or "{}")
    except json.JSONDecodeError as e:
        return None, f"Arguments are not valid JSON: {e}"

    if not isinstance(data, dict):
        return None, "Arguments must be a JSON object."

    model = _PARAM_MODELS.get(tool_name)
    if model is None:
        return None, f"Unknown tool: {tool_name}"

    try:
        parsed = model(**data)
    except ValidationError as e:
        errors = "; ".join(
            f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in e.errors()
        )
        return None, f"Invalid arguments for {tool_name}: {errors}"

    return parsed.model_dump(exclude_none=True), None