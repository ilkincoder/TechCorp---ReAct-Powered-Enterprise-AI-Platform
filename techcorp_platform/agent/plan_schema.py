"""Plan schema — structured dataclasses for planner output and validation."""

from dataclasses import dataclass, field

MAX_ITERATIONS = 5


@dataclass
class ToolStep:
    """A single tool execution step within a plan."""
    tool: str
    goal: str
    params: dict = field(default_factory=dict)
    status: str = "pending"  # pending | running | success | failed | skipped
    execution_time_ms: int | None = None
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "goal": self.goal,
            "params": self.params,
            "status": self.status,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
        }


@dataclass
class Plan:
    """A validated execution plan from the planner agent."""
    intent: str
    reasoning: str
    tools_needed: list[str]
    steps: list[ToolStep]
    queries: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Plan":
        """Parse a plan from a dictionary (LLM output or Tier-1 result)."""
        steps_data = data.get("steps", [])
        steps = []
        for s in steps_data:
            if isinstance(s, ToolStep):
                steps.append(s)
            else:
                steps.append(ToolStep(
                    tool=s.get("tool", ""),
                    goal=s.get("goal", s.get("query", "")),
                    params=s.get("params", {}),
                ))

        # If no steps provided but tools_needed and queries exist, infer steps
        if not steps and data.get("tools_needed"):
            queries = data.get("queries", {})
            for tool_name in data["tools_needed"]:
                params = queries.get(tool_name, {})
                steps.append(ToolStep(
                    tool=tool_name,
                    goal=params.get("query", params.get("goal", "")),
                    params=params,
                ))

        return cls(
            intent=data.get("intent", ""),
            reasoning=data.get("reasoning", ""),
            tools_needed=data.get("tools_needed", []),
            steps=steps,
            queries=data.get("queries", {}),
        )


def validate_plan(plan: Plan, tool_map: dict) -> tuple[bool, list[str], list[str]]:
    """Validate a plan against the tool registry.

    Returns (is_valid, errors, warnings).
    Errors are fatal — the plan cannot execute.
    Warnings are advisory — the plan can proceed but may be suboptimal.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check: at least one tool
    if not plan.tools_needed:
        errors.append("Plan has no tools_needed — nothing to execute.")
        return (False, errors, warnings)

    # Check: step count within limits
    if len(plan.tools_needed) > MAX_ITERATIONS:
        errors.append(
            f"Plan requests {len(plan.tools_needed)} tools, "
            f"max is {MAX_ITERATIONS}."
        )

    # Check: tools exist
    for tool_name in plan.tools_needed:
        if tool_name not in tool_map:
            errors.append(f"Unknown tool: '{tool_name}'")

    # Check: each step has params
    for step in plan.steps:
        if step.tool not in tool_map:
            continue  # already reported above
        if not step.params or all(v == "" or v is None for v in step.params.values()):
            errors.append(
                f"Tool '{step.tool}' has no parameters — "
                f"cannot execute without input."
            )

    # Check: no duplicate sequential calls with identical params
    for i in range(len(plan.steps) - 1):
        current = plan.steps[i]
        next_step = plan.steps[i + 1]
        if current.tool == next_step.tool and current.params == next_step.params:
            warnings.append(
                f"Duplicate call to '{current.tool}' with identical params "
                f"at steps {i + 1} and {i + 2}."
            )

    # Check: SQL queries are non-empty strings
    for step in plan.steps:
        if step.tool == "sql_query":
            query = step.params.get("query", "")
            if not query or not isinstance(query, str) or not query.strip():
                errors.append(
                    f"SQL query for '{step.tool}' is empty — "
                    f"cannot execute."
                )

    # Check: RAG queries are non-empty
    for step in plan.steps:
        if step.tool == "rag_search":
            query = step.params.get("query", "")
            if not query or not isinstance(query, str) or not query.strip():
                warnings.append(
                    f"RAG query for '{step.tool}' is empty — "
                    f"may return no results."
                )

    is_valid = len(errors) == 0
    return (is_valid, errors, warnings)
