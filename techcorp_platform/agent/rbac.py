"""RBAC — role permissions, prompt context, and hard per-tool-call gates.

Moved out of planner.py so both the planner (prompt blocks) and the ReAct
loop (hard gates) can use them without circular imports. planner.py
re-exports the public names for backward compatibility.
"""

# ── Known database table names (derived from data/*.csv) ──────────────────────

_KNOWN_TABLES: set[str] = {
    "audit_logs", "change_requests", "company_announcements",
    "customers", "departments", "employees",
    "incident_reports", "internal_emails", "jira_issues",
    "meeting_notes", "meeting_schedule", "products",
    "projects", "release_notes", "slack_conversations",
    "subscriptions", "support_tickets",
}

# ── RBAC Role Emulation ───────────────────────────────────────────────────────

ROLE_PERMISSIONS = {
    'engineering_admin': {
        'forbidden_tables': [],
        'forbidden_departments': [],
        'label': 'Engineering Admin',
    },
    'sales_intern': {
        'forbidden_tables': ['employees', 'incident_reports', 'audit_logs', 'internal_emails'],
        'forbidden_departments': ['Finance', 'Legal', 'HR'],
        'label': 'Sales Intern',
    },
    'support_agent': {
        'allowed_tables': ['support_tickets', 'customers'],
        'allowed_departments': ['Customer_Support', 'Engineering', 'IT', 'Operations', 'Sales'],
        'label': 'Support Agent',
    },
}

# Full list of KB departments — used to compute complements from forbidden lists
_ALL_KB_DEPARTMENTS = [
    'AI', 'Customer_Support', 'Engineering', 'Finance', 'HR',
    'IT', 'Legal', 'Marketing', 'Operations', 'Sales', 'Security',
]


def _build_role_context(role: str | None) -> str:
    """Build a prompt block describing access restrictions for the given role.

    Includes both SQL table restrictions AND RAG department restrictions so the
    model can proactively refuse queries outside the role's scope — rather than
    searching and returning partial/irrelevant results.
    """
    if not role or role == 'engineering_admin':
        return ""

    perms = ROLE_PERMISSIONS.get(role, {})
    label = perms.get('label', role)
    lines = [
        "## Role-Based Access Control",
        f"You are acting as **{label}**.",
    ]

    # SQL table restrictions
    if perms.get('allowed_tables'):
        lines.append(
            f"You may ONLY query these database tables: {', '.join(perms['allowed_tables'])}. "
            "All other tables are off-limits."
        )
    elif perms.get('forbidden_tables'):
        lines.append(
            f"You must NOT query these database tables: {', '.join(perms['forbidden_tables'])}. "
        )

    # RAG department restrictions (so the model can refuse upfront)
    allowed_depts = _get_allowed_departments(role)
    if allowed_depts:
        lines.append(
            f"You may ONLY search these knowledge base departments: {', '.join(allowed_depts)}. "
        )
        # Build explicit "off-limits" list for clarity
        off_limits = [d for d in _ALL_KB_DEPARTMENTS if d not in allowed_depts]
        if off_limits:
            lines.append(
                f"OFF-LIMITS departments (do NOT search these under any circumstances): "
                f"{', '.join(off_limits)}. "
                f"If the user's question relates to topics handled by these departments "
                f"(e.g. HR policies, Finance documents, Legal compliance), "
                f"refuse immediately without searching."
            )
    elif perms.get('forbidden_departments'):
        forbidden = perms['forbidden_departments']
        lines.append(
            f"OFF-LIMITS departments: {', '.join(forbidden)}. "
            f"You must NOT search these. If the user asks about topics in these "
            f"departments, refuse immediately without searching."
        )

    lines.append(
        "If the user asks for data or documents outside your permissions, "
        "refuse immediately — do not search, do not attempt workarounds, "
        "do not cite adjacent documents. Simply explain the limitation."
    )
    return "\n".join(lines)


def _get_allowed_departments(role: str | None) -> list[str] | None:
    """Return the list of allowed KB departments for the given role.

    Returns None for engineering_admin (no filter needed — full access).
    """
    if not role or role == 'engineering_admin':
        return None

    perms = ROLE_PERMISSIONS.get(role, {})
    allowed = perms.get('allowed_departments')
    if allowed:
        return allowed

    forbidden = perms.get('forbidden_departments', [])
    if forbidden:
        return [d for d in _ALL_KB_DEPARTMENTS if d not in forbidden]

    return None


def apply_rbac(tool_name: str, params: dict, role: str | None) -> tuple[dict, str | None]:
    """Hard per-tool-call gate. Returns (possibly-updated params, denial or None).

    - rag_search: injects allowed_departments (Qdrant-level enforcement)
    - sql_query: blocks queries referencing tables outside the role's scope
    """
    if not role or role == 'engineering_admin':
        return params, None

    perms = ROLE_PERMISSIONS.get(role, {})

    if tool_name == "rag_search":
        allowed_depts = _get_allowed_departments(role)
        if allowed_depts:
            params = {**params, "allowed_departments": allowed_depts}
        return params, None

    if tool_name == "sql_query":
        query_text = (params.get("query") or "").lower()
        allowed = perms.get("allowed_tables")
        forbidden = perms.get("forbidden_tables", [])
        referenced = [t for t in sorted(_KNOWN_TABLES) if t in query_text]

        if allowed:
            unauthorized = [t for t in referenced if t not in allowed]
        else:
            unauthorized = [t for t in referenced if t in forbidden]

        if unauthorized:
            return params, (
                f"Access denied: {', '.join(unauthorized)} "
                f"not available at your access level ({perms.get('label', role)})."
            )

    return params, None