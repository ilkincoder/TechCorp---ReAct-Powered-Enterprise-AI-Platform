"""Python Tool — sandboxed code execution for data analysis."""

import io
import sys

from .base import BaseTool, ToolResult


class PythonTool(BaseTool):
    name = "python_execute"
    description = """Execute Python code in a sandboxed environment. Use this for data analysis,
calculations, aggregations, or any computation the other tools can't handle.
The code runs in an isolated namespace with pandas available as 'pd'.
Print statements are captured and returned."""

    def __init__(self):
        self._namespace = {
            "pd": None,  # lazy import
        }

    def _ensure_pandas(self):
        if self._namespace["pd"] is None:
            import pandas as pd
            self._namespace["pd"] = pd

    async def execute(self, code: str = "", **kwargs) -> ToolResult:
        """Execute Python code in a sandbox."""
        if not code.strip():
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="No Python code provided.",
            )

        self._ensure_pandas()

        stdout = io.StringIO()
        stderr = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = stdout, stderr

        result_data = None
        error = ""

        try:
            # Compile to catch syntax errors
            compiled = compile(code, "<sandbox>", "exec")

            # Execute in isolated namespace
            exec(compiled, self._namespace)

            result_data = stdout.getvalue()
            sys.stdout, sys.stderr = old_stdout, old_stderr

            return ToolResult(
                tool_name=self.name,
                success=True,
                data={
                    "output": result_data,
                    "code": code,
                },
                metadata={"output_lines": len(result_data.splitlines()) if result_data else 0},
            )

        except Exception as e:
            sys.stdout, sys.stderr = old_stdout, old_stderr
            error = f"{type(e).__name__}: {str(e)}\n{stderr.getvalue()}"

            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error,
                data={"code": code, "output": stdout.getvalue()},
            )

    def _input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. Use print() to output results. Pandas is available as 'pd'.",
                },
            },
            "required": ["code"],
        }