"""Planner Agent — Tier-1 heuristic routing (no LLM).

LLM-driven planning now lives inside the ReAct loop (react.py), which uses
native tool calling. This module keeps only the deterministic Tier-1 fast
paths that bypass the LLM entirely, plus the SQL-intent heuristics.
"""

from .plan_schema import Plan
from .rbac import (  # noqa: F401 — re-exported for backward compatibility (app.py imports these)
    _KNOWN_TABLES,
    ROLE_PERMISSIONS,
    _ALL_KB_DEPARTMENTS,
)

_QUERY_CONTEXT_WORDS: set[str] = {
    "query", "database", "table", "row", "column", "sql",
    "count", "list", "how many", "who", "show", "get", "find",
}

_SQL_KEYWORDS: set[str] = {
    "select", "from", "where", "join", "insert", "update", "delete",
    "group by", "having", "limit", "union", "order by",
}


def _detect_explicit_sql(message: str) -> dict | None:
    """Tier 1: user typed a raw SELECT...FROM — return plan dict to skip LLM entirely."""
    import re

    if re.search(r'\bSELECT\b\s+.+\s+\bFROM\b\s+', message, re.IGNORECASE | re.DOTALL):
        return {
            "intent": "Execute SQL query on structured business data",
            "tools_needed": ["sql_query"],
            "reasoning": "Message contains an explicit SQL SELECT statement.",
            "queries": {"sql_query": {"query": message.strip()}},
            "steps": [
                {"tool": "sql_query", "goal": "Execute explicit SQL query", "params": {"query": message.strip()}}
            ],
        }
    return None


def _detect_gibberish(user_message: str) -> dict | None:
    """Tier 1: detect keyboard smashes and unintelligible input — skip LLM entirely.

    Returns a plan dict with no tools so the caller can respond gracefully
    instead of routing nonsense to memory or search.

    Detects:
    - Words with no vowels at all (e.g. "zxcvbnm", "qwerty")
    - Consecutive keyboard-row sequences of 3+ characters (catches "sadasd" via "asd")
    - Very high consonant-to-vowel ratio in longer words (>80% consonants, len > 5)
    - Words made of only 2-3 distinct letters, 6+ chars (e.g. "sadasd", "ababab")
    """
    import re

    msg = user_message.strip()
    if not msg:
        return None

    words = msg.split()

    # Keyboard rows (left-to-right and right-to-left for each row)
    _KB_ROWS = [
        "qwertyuiop", "asdfghjkl", "zxcvbnm",
        "poiuytrewq", "lkjhgfdsa", "mnbvcxz",
    ]

    def _looks_like_gibberish(word: str) -> bool:
        w = word.lower()
        if len(w) < 3:
            return False
        # No vowels at all
        if not re.search(r'[aeiouy]', w):
            return True
        # Contains a keyboard-row run of 3+ consecutive keys
        for row in _KB_ROWS:
            for i in range(len(row) - 3):
                if row[i:i + 3] in w:
                    return True
        # Very high consonant ratio in a longer word (>80% consonants, len > 5)
        vowels = sum(1 for c in w if c in 'aeiouy')
        if len(w) > 5 and vowels / len(w) < 0.2:
            return True
        # Only 2-3 distinct letters in a 6+ character word (e.g. "sadasd", "ababab")
        if len(w) >= 6:
            distinct = len(set(w))
            if distinct <= 3:
                return True
        return False

    gibberish_count = sum(1 for w in words if _looks_like_gibberish(w))

    # Majority of words are gibberish → unintelligible input
    if gibberish_count > len(words) * 0.5:
        return {
            "intent": "Unintelligible input — no recognizable request found",
            "tools_needed": [],
            "reasoning": "Input appears to be random keyboard characters or unintelligible text.",
            "queries": {},
            "steps": [],
        }

    return None


def _detect_statement(user_message: str, conversation_history: list[dict] | None = None) -> dict | None:
    """Tier 1: detect declarative context-sharing statements — route to memory: store.

    A statement is a message where the user is providing information, not asking
    a question or requesting an action. Returns a plan dict to skip the LLM entirely.

    Examples:
    - "The Phoenix project deadline is Sept 15"              → store
    - "I need to order 500 widgets for manufacturing"        → store
    - "Also, the Q3 budget is $50k"                          → store (follow-on)
    - "We're migrating the auth service to PostgreSQL 16"    → store
    - "How many employees?"                                  → NOT a statement (question)
    - "Remember the vendor agreed to 10% discount"           → NOT caught here (has explicit keyword)
    """
    import re

    msg = user_message.strip()

    # Skip if it looks like a question
    if "?" in msg:
        return None

    msg_lower = msg.lower()

    # Skip if it starts with a question word or command word
    _QUESTION_STARTS = (
        r"^(who|what|where|when|why|how|can|could|would|will|do|does|did|"
        r"is|are|was|were|should|may|might|shall|show|list|find|get|tell|"
        r"search|look|query|run|execute|calculate|compute|explain|describe|"
        r"summarize|compare|analyze|check|give|provide)"
    )
    if re.match(_QUESTION_STARTS, msg_lower):
        return None

    # Skip explicit remember/save — routed by the model in the ReAct loop
    if re.search(r"\b(remember|save|recall)\b", msg_lower):
        return None

    # Skip if too long (likely not a simple statement)
    if len(msg) > 300:
        return None

    # Follow-on signals — building on prior context (needs history to be present)
    _FOLLOW_ON_STARTS = (
        r"^(also\b|and\b|additionally\b|plus\b|moreover\b|furthermore\b|"
        r"besides\b|in addition\b|likewise\b|similarly\b)"
    )
    is_follow_on = bool(re.match(_FOLLOW_ON_STARTS, msg_lower))
    has_history = bool(conversation_history)

    if is_follow_on and has_history:
        return {
            "intent": "Store follow-on enterprise context",
            "tools_needed": ["memory"],
            "reasoning": "Follow-on signal detected with conversation history — user is building on prior business context.",
            "queries": {"memory": {"action": "store", "content": user_message, "entity_type": "project_detail"}},
            "steps": [
                {"tool": "memory", "goal": "Store follow-on enterprise context", "params": {"action": "store", "content": user_message, "entity_type": "project_detail"}}
            ],
        }

    # Enterprise context-sharing markers — corporate, project, team, vendor, technical
    _CONTEXT_MARKERS = (
        # Project / milestone patterns
        r"\b((phoenix|atlas|titan|horizon|quantum|vertex|mercury|apollo|nova)\s+)?(project|initiative)\s+(deadline|budget|goal|status|deliverable|milestone|phase|owner|start)",
        r"\b(q[1-4]|sprint|phase|milestone|release)\s+(deadline|budget|goal|status|deliverable|plan|review|retrospective)",
        r"\b(the\s+)?(deadline|budget|timeline|priority|roadmap)\s+(for|is|was|will|has|changed|updated|moved|set|approved)",
        # Budget / financial
        r"\b(budget|capex|opex|forecast|spend|cost|revenue|allocation)\s+(is|was|for|will|has|approved|allocated|requested|set at|estimated at)",
        r"\b\$[\d,.]+[kKmMbB]?\s+(budget|spend|cost|allocation|approved|requested)",
        # Team / organizational
        r"\b(team|department|squad|pod|group)\s+(is|are|will|has|need|plan|responsible|working|leading|handling|owning)",
        r"\b(we|engineering|marketing|sales|hr|finance|ops|legal|product|design|support|security|devops)\s+(are|is|need|will|plan|decided|agreed|using|migrating|switching|adopting|deploying|testing)",
        # Employee / role
        r"\b(employee|contractor|intern|lead|manager|director|vp|engineer|analyst)\s+\w+\s+(is|works|joined|left|manages|reports|handles|oversees|leads|runs)",
        # Vendor / customer
        r"\b(vendor|supplier|partner|client|customer|account)\s+(is|has|will|needs|requires|requested|agreed|provided|offered|quoted|delivered|signed)",
        r"\b(contract|agreement|sla|msa|nd|nda|po|purchase\s+order|invoice)\s+(is|has|was|will|signed|renewed|expired|approved|pending)",
        # Meeting / decisions
        r"\b(meeting|standup|sync|review|retro|retrospective|workshop|presentation)\s+(notes|outcome|decision|action\s+item|summary|minutes|recording)",
        r"\b(we|team)\s+(decided|agreed|resolved|concluded|determined|aligned)\s+(to|on|that)",
        # Technical / architecture
        r"\b(server|database|api|service|microservice|deployment|pipeline|cluster|environment|stack|architecture|infrastructure)\s+(is|are|using|running|deployed|configured|migrated|scaled|updated|upgraded)",
        r"\b(migrating|upgrading|switching|moving|refactoring|rewriting|consolidating)\s+(to|from|the)",
        # Compliance / policy
        r"\b(compliance|regulatory|policy|sox|gdpr|hipaa|pci|iso|soc2?|security|audit)\s+(requires|mandates|states|needs|deadline|review|assessment)",
        r"\b(policy|procedure|guideline|standard)\s+(is|has|was|will|requires|mandates|states|updated|approved|published)",
        # First-person enterprise context (keep useful ones from original)
        r"\b(i\s+(need|have|work|manage|handle|run|lead|oversee|report|ordered|requested|approved|escalated|assigned))",
        r"\b(my\s+(project|team|department|manager|deadline|budget|task|goal|sprint|deliverable|assignment|initiative|stakeholder|vendor|client))",
        r"\b(our\s+(project|team|company|department|budget|deadline|goal|plan|strategy|roadmap|vendor|client|partner))",
        r"\b(this\s+is\s+(about|for|our|the)\s+(project|initiative|task|deadline|budget|vendor|issue|ticket|request|change|migration|deployment|release))",
        # Business metrics / KPIs
        r"\b(kpi|metric|okr|sla|slo|slr|csat|nps|churn|retention|conversion|uptime|latency|throughput|error rate|availability)\s+(is|was|target|goal|threshold|current|at)",
    )
    if any(re.search(p, msg_lower) for p in _CONTEXT_MARKERS):
        return {
            "intent": "Store enterprise context provided by user",
            "tools_needed": ["memory"],
            "reasoning": "User is providing business/enterprise context — project details, deadlines, team info, vendor updates, or technical decisions.",
            "queries": {"memory": {"action": "store", "content": user_message, "entity_type": "project_detail"}},
            "steps": [
                {"tool": "memory", "goal": "Store enterprise context", "params": {"action": "store", "content": user_message, "entity_type": "project_detail"}}
            ],
        }

    return None


def _detect_personal_query(user_message: str) -> dict | None:
    """Tier 1: detect queries about the user's own stored facts — route to memory:search.

    Catches patterns like:
    - "What deadlines do I have?"
    - "What are my tasks?"
    - "Tell me about my project"
    - "What do you know about me?"
    - "What's my budget?"

    Returns a plan dict with memory:search, or None if no match.
    """
    import re

    msg = user_message.strip()
    msg_lower = msg.lower()

    # Must be a question or a "tell/show me" request
    if "?" not in msg and not msg_lower.startswith(("tell me about", "show me")):
        return None

    # Personal-fact retrieval patterns
    _PERSONAL_QUERY_PATTERNS = (
        r"what\s+(are\s+my|is\s+my|do\s+i\s+have|did\s+i)\b",
        r"tell\s+me\s+about\s+my\b",
        r"what\s+do\s+you\s+(know|remember|have)\s+about\s+me\b",
        r"what(?:'s|\s+is)\s+my\b",
        r"do\s+i\s+have\s+(any|a|an)\b",
        r"show\s+me\s+my\b",
    )

    is_personal = any(re.search(p, msg_lower) for p in _PERSONAL_QUERY_PATTERNS)
    if not is_personal:
        return None

    # Double-check for personal pronouns to avoid false positives
    _PERSONAL_PRONOUNS = (r"\bmy\b", r"\bme\b", r"\bi\s", r"\bi've\b", r"\bi'm\b")
    if not any(re.search(p, msg_lower) for p in _PERSONAL_PRONOUNS):
        return None

    # Don't intercept explicit SQL/data queries
    if _has_sql_intent(user_message):
        return None

    return {
        "intent": "Retrieve enterprise context and stored information from memory",
        "tools_needed": ["memory"],
        "reasoning": "User is asking about stored enterprise context (project details, deadlines, budgets, team info).",
        "queries": {"memory": {"action": "search", "query": user_message}},
        "steps": [
            {"tool": "memory", "goal": "Search persistent memory for enterprise context", "params": {"action": "search", "query": user_message}}
        ],
    }


def _has_sql_intent(message: str) -> bool:
    """Tiers 2 & 3: message signals data-query intent but needs LLM to generate SQL.

    Tier 2: known table name + query-context word (list, show, how many, who, etc.)
    Tier 3: two or more distinct SQL keywords
    """
    import re

    msg_lower = message.lower()

    # Tier 2: known table name + query-language context
    if any(tbl in msg_lower for tbl in _KNOWN_TABLES) and any(
        w in msg_lower for w in _QUERY_CONTEXT_WORDS
    ):
        return True

    # Tier 3: two or more distinct SQL keywords
    matched = {kw for kw in _SQL_KEYWORDS if re.search(rf'\b{re.escape(kw)}\b', msg_lower)}
    if len(matched) >= 2:
        return True

    return False


class PlannerAgent:
    """Tier-1 heuristic router. LLM planning happens inside the ReAct loop."""

    def fast_plan(self, user_message: str, conversation_history: list[dict] | None = None) -> Plan | None:
        """Return a deterministic Tier-1 plan, or None if the query needs the ReAct loop.

        No LLM call is ever made here — this is the zero-latency path for
        gibberish, explicit SQL, memory statements, personal queries, and
        follow-on searches.
        """
        for detect in (
            lambda: _detect_gibberish(user_message),
            lambda: _detect_explicit_sql(user_message),
            lambda: _detect_statement(user_message, conversation_history),
            lambda: _detect_personal_query(user_message),
        ):
            plan_dict = detect()
            if plan_dict is not None:
                return Plan.from_dict(plan_dict)
        return None