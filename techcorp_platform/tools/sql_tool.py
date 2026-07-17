"""SQL Tool — PostgreSQL-backed query engine over TechCorp structured data."""

import re

import psycopg2

from ..config import DATABASE_URL
from .base import BaseTool, ToolResult


class SQLTool(BaseTool):
    name = "sql_query"
    description = """Query the TechCorp structured database (PostgreSQL). Use this for questions
about employees, departments, customers, products, subscriptions, support tickets,
projects, meetings, incidents, Jira issues, emails, Slack messages, or any
structured business data. The database contains 17 tables with full referential
integrity. Use standard PostgreSQL SQL syntax."""

    def __init__(self):
        self._conn = None
        self._schema = {}

    async def _ensure_connected(self):
        """Connect to PostgreSQL if not already connected."""
        if self._conn is not None and not self._conn.closed:
            return

        self._conn = psycopg2.connect(DATABASE_URL)
        self._conn.autocommit = True

    async def execute(self, query: str = "", params: tuple | None = None, **kwargs) -> ToolResult:
        """Execute a SQL query against the TechCorp PostgreSQL database.

        params: optional bind parameters for %s placeholders (internal use —
        not exposed in the LLM tool schema).
        """
        await self._ensure_connected()

        if not query.strip():
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="SQL query is empty.",
            )

        cleaned = query.strip().rstrip(";")

        # Safety: only SELECT allowed
        if not re.match(r"^\s*SELECT\b", cleaned, re.IGNORECASE):
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="Only SELECT queries are allowed for safety.",
            )

        try:
            cursor = self._conn.cursor()
            cursor.execute(cleaned, params)
            columns = [d[0] for d in cursor.description] if cursor.description else []

            rows = cursor.fetchall()
            total = len(rows)

            # Format as list of dicts
            data = []
            for row in rows[:100]:
                data.append(dict(zip(columns, [str(v) if v is not None else "" for v in row])))

            cursor.close()

            return ToolResult(
                tool_name=self.name,
                success=True,
                data={
                    "query": cleaned,
                    "columns": columns,
                    "rows": data,
                    "total_rows": total,
                    "truncated": total > 100,
                },
                citations=[f"SQL: {cleaned[:80]}..."],
                metadata={"row_count": total},
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(e),
                data={"query": cleaned},
            )

    def _input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "PostgreSQL SELECT query to execute against the TechCorp database",
                },
            },
            "required": ["query"],
        }