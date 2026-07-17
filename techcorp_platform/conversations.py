"""Conversation and message persistence — raw SQL via psycopg2.

   Tables: conversations (UUID pk), messages (serial pk, FK to conversations).
   Follows the project pattern: no ORM, direct psycopg2 connections.
"""

import asyncio
import uuid
import json
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor

from .config import DATABASE_URL


def _get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_conversation_tables():
    """Create conversations and messages tables if they don't exist."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id UUID PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT 'New Chat',
                    summary TEXT DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL DEFAULT '',
                    sources JSONB DEFAULT '[]',
                    tools_used JSONB DEFAULT '[]',
                    intent TEXT DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
                ON messages(conversation_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_created_at
                ON messages(conversation_id, created_at)
            """)
            # Add summary column if it doesn't exist (for existing databases)
            cur.execute("""
                ALTER TABLE conversations ADD COLUMN IF NOT EXISTS summary TEXT DEFAULT ''
            """)
            # Widen the role constraint to allow 'system' (for existing databases
            # created before system messages were introduced)
            cur.execute("""
                ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_role_check
            """)
            cur.execute("""
                ALTER TABLE messages ADD CONSTRAINT messages_role_check
                CHECK (role IN ('user', 'assistant', 'system'))
            """)
        conn.commit()
    finally:
        conn.close()


def create_conversation(title: str = "New Chat") -> str:
    """Create a new conversation, return its UUID as a string."""
    conv_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (%s, %s, %s, %s)",
                (conv_id, title, now, now),
            )
        conn.commit()
    finally:
        conn.close()
    return conv_id


def save_message(
    conversation_id: str,
    role: str,
    content: str,
    sources: list[dict] | None = None,
    tools_used: list[str] | None = None,
    intent: str = "",
) -> int:
    """Save a message to a conversation. Returns the message id."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO messages (conversation_id, role, content, sources, tools_used, intent)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    conversation_id,
                    role,
                    content,
                    json.dumps(sources or []),
                    json.dumps(tools_used or []),
                    intent,
                ),
            )
            msg_id = cur.fetchone()[0]

            # Touch conversation updated_at
            cur.execute(
                "UPDATE conversations SET updated_at = NOW() WHERE id = %s",
                (conversation_id,),
            )

            # Auto-title: use first 60 chars of first user message
            cur.execute(
                "SELECT title FROM conversations WHERE id = %s",
                (conversation_id,),
            )
            row = cur.fetchone()
            if row and row[0] == "New Chat" and role == "user":
                title = content[:60].replace("\n", " ").strip()
                cur.execute(
                    "UPDATE conversations SET title = %s WHERE id = %s",
                    (title, conversation_id),
                )

        conn.commit()
        return msg_id
    finally:
        conn.close()


def get_recent_messages(conversation_id: str, limit: int = 5) -> list[dict]:
    """Return the most recent messages for a conversation.

    Returns oldest-first ordering for prompt injection.
    """
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT role, content FROM (
                       SELECT role, content, created_at FROM messages
                       WHERE conversation_id = %s
                       ORDER BY created_at DESC
                       LIMIT %s
                   ) sub ORDER BY created_at ASC""",
                (conversation_id, limit),
            )
            return [{"role": r["role"], "content": r["content"]} for r in cur.fetchall()]
    finally:
        conn.close()


def list_conversations() -> list[dict]:
    """List all conversations ordered by most recently updated."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT c.id, c.title, c.created_at, c.updated_at,
                       COUNT(m.id) AS message_count
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                GROUP BY c.id
                ORDER BY c.updated_at DESC
            """)
            rows = cur.fetchall()
            result = []
            for row in rows:
                result.append({
                    "id": row["id"],
                    "title": row["title"],
                    "created_at": row["created_at"].isoformat(),
                    "updated_at": row["updated_at"].isoformat(),
                    "message_count": row["message_count"],
                })
            return result
    finally:
        conn.close()


def get_conversation(conv_id: str) -> dict | None:
    """Get a conversation with all its messages."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE id = %s",
                (conv_id,),
            )
            conv_row = cur.fetchone()
            if not conv_row:
                return None

            cur.execute(
                "SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
                (conv_id,),
            )
            msg_rows = cur.fetchall()

            messages = []
            for row in msg_rows:
                messages.append({
                    "id": row["id"],
                    "role": row["role"],
                    "content": row["content"],
                    "sources": row["sources"] if isinstance(row["sources"], list) else json.loads(row["sources"] or "[]"),
                    "tools_used": row["tools_used"] if isinstance(row["tools_used"], list) else json.loads(row["tools_used"] or "[]"),
                    "intent": row["intent"],
                    "created_at": row["created_at"].isoformat(),
                })

            return {
                "id": conv_row["id"],
                "title": conv_row["title"],
                "created_at": conv_row["created_at"].isoformat(),
                "updated_at": conv_row["updated_at"].isoformat(),
                "messages": messages,
            }
    finally:
        conn.close()


def delete_conversation(conv_id: str) -> bool:
    """Delete a conversation and its messages (CASCADE). Returns True if deleted."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM conversations WHERE id = %s",
                (conv_id,),
            )
            deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()


def update_conversation_summary(conversation_id: str, summary: str) -> None:
    """Store a running summary for a conversation."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE conversations SET summary = %s, updated_at = NOW() WHERE id = %s",
                (summary, conversation_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_conversation_summary(conversation_id: str) -> str:
    """Get the stored summary for a conversation."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT summary FROM conversations WHERE id = %s",
                (conversation_id,),
            )
            row = cur.fetchone()
            return row[0] if row and row[0] else ""
    finally:
        conn.close()


def get_conversation_title(conversation_id: str) -> str:
    """Get the title for a conversation (lightweight — no messages)."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT title FROM conversations WHERE id = %s",
                (conversation_id,),
            )
            row = cur.fetchone()
            return row[0] if row and row[0] else "New Chat"
    finally:
        conn.close()


def get_context_window(conversation_id: str, recent_limit: int = 3) -> dict:
    """Return {summary, recent} for prompt injection.

    summary: stored running summary of older messages (empty if none)
    recent: last N messages in oldest-first order
    """
    summary = get_conversation_summary(conversation_id)
    recent = get_recent_messages(conversation_id, limit=recent_limit)
    return {"summary": summary, "recent": recent}


def count_messages(conversation_id: str) -> int:
    """Count total messages in a conversation."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM messages WHERE conversation_id = %s",
                (conversation_id,),
            )
            row = cur.fetchone()
            return row[0] if row else 0
    finally:
        conn.close()


def get_all_messages_for_summary(conversation_id: str, exclude_last: int = 3) -> list[dict]:
    """Get all messages except the most recent N, for summarization."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT role, content FROM (
                       SELECT role, content, created_at FROM messages
                       WHERE conversation_id = %s
                       ORDER BY created_at DESC
                       OFFSET %s
                   ) sub ORDER BY created_at ASC""",
                (conversation_id, exclude_last),
            )
            return [{"role": r["role"], "content": r["content"]} for r in cur.fetchall()]
    finally:
        conn.close()


# ── Persistent Memory Table ──────────────────────────────────────────────────

def init_memory_table():
    """Create the memories table if it doesn't exist."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id SERIAL PRIMARY KEY,
                    type TEXT NOT NULL DEFAULT 'project_detail',
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    confidence REAL NOT NULL DEFAULT 0.5,
                    last_used TIMESTAMPTZ,
                    times_used INTEGER NOT NULL DEFAULT 0,
                    source TEXT NOT NULL DEFAULT 'user'
                )
            """)
        conn.commit()
    finally:
        conn.close()


async def insert_memory(
    content: str = "",
    entity_type: str = "project_detail",
    confidence: float = 0.5,
    source: str = "user",
) -> dict:
    """Insert a new memory entry, return it as a dict."""
    def _run():
        conn = _get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO memories (type, content, confidence, source)
                       VALUES (%s, %s, %s, %s) RETURNING *""",
                    (entity_type, content, confidence, source),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row) if row else {}
        finally:
            conn.close()

    return await asyncio.to_thread(_run)


async def update_memory(
    entry_id: int,
    content: str,
    entity_type: str,
    confidence: float,
    source: str,
) -> None:
    """Update an existing memory entry's content and metadata."""
    def _run():
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE memories SET content = %s, type = %s, confidence = %s,
                       source = %s, created_at = NOW() WHERE id = %s""",
                    (content, entity_type, confidence, source, entry_id),
                )
            conn.commit()
        finally:
            conn.close()

    await asyncio.to_thread(_run)


async def search_memories(
    query: str = "",
    entity_type: str = "",
    limit: int = 20,
) -> list[dict]:
    """Search memories semantically using Qdrant embeddings, then fetch full entries from Postgres.

    Returns results sorted by relevance (Qdrant cosine similarity score).
    An empty query returns the most recent entries.
    """
    if not query:
        return await recent_memories(limit=limit)

    def _run():
        from qdrant_client import QdrantClient, models
        from .config import QDRANT_URL, MEMORY_COLLECTION, DENSE_MODEL
        from .tools.rag_tool import _get_dense_model

        # Embed the query
        model = _get_dense_model(DENSE_MODEL)
        query_vec = model.encode([query]).tolist()[0]

        # Build optional entity_type filter
        qdrant_filter = None
        if entity_type:
            qdrant_filter = models.Filter(
                must=[models.FieldCondition(
                    key="entity_type", match=models.MatchValue(value=entity_type)
                )]
            )

        # Search Qdrant
        client = QdrantClient(url=QDRANT_URL, timeout=30)
        try:
            results = client.query_points(
                collection_name=MEMORY_COLLECTION,
                query=query_vec,
                limit=limit,
                with_payload=True,
                query_filter=qdrant_filter,
                using="dense",
            )
        except Exception:
            return []  # Collection doesn't exist or Qdrant is down

        # Extract pg_ids and scores — point ID is the Postgres integer
        pg_ids = []
        score_map = {}
        for point in results.points:
            if isinstance(point.id, int):
                pid = point.id
                pg_ids.append(pid)
                score_map[pid] = point.score

        if not pg_ids:
            return []

        # Fetch full entries from Postgres
        conn = _get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM memories WHERE id = ANY(%s)",
                    (pg_ids,),
                )
                rows = [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

        # Sort by Qdrant score (highest first) and attach relevance
        for row in rows:
            row["relevance"] = round(score_map.get(row["id"], 0.0), 3)
        rows.sort(key=lambda r: score_map.get(r["id"], 0.0), reverse=True)

        return rows

    return await asyncio.to_thread(_run)


async def recent_memories(limit: int = 10) -> list[dict]:
    """Return the most recent memory entries."""
    def _run():
        conn = _get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM memories ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    return await asyncio.to_thread(_run)


async def clear_memories() -> None:
    """Delete all memory entries."""
    def _run():
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM memories")
            conn.commit()
        finally:
            conn.close()

    await asyncio.to_thread(_run)


async def _get_memory_by_id(entry_id: int) -> dict | None:
    """Fetch a single memory entry by its ID. Returns None if not found."""
    def _run():
        conn = _get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM memories WHERE id = %s", (entry_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    return await asyncio.to_thread(_run)


async def bump_memory_usage(entry_id: int) -> None:
    """Increment times_used and update last_used for a memory entry."""
    def _run():
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE memories SET times_used = times_used + 1, last_used = NOW() WHERE id = %s",
                    (entry_id,),
                )
            conn.commit()
        finally:
            conn.close()

    return await asyncio.to_thread(_run)


# ── Reports Table ─────────────────────────────────────────────────────────────

def init_reports_table():
    """Create the reports table if it doesn't exist."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL DEFAULT '',
                    data_sources TEXT[] DEFAULT '{}',
                    plan JSONB DEFAULT '{}',
                    conversation_id UUID,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
        conn.commit()
    finally:
        conn.close()


async def insert_report(
    title: str = "",
    data_sources: list[str] | None = None,
    plan: dict | None = None,
    conversation_id: str | None = None,
) -> dict:
    """Insert a new report (pending). Returns the row as a dict."""
    def _run():
        conn = _get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO reports (title, data_sources, plan, conversation_id, status)
                       VALUES (%s, %s, %s, %s, 'pending')
                       RETURNING *""",
                    (
                        title,
                        data_sources or [],
                        json.dumps(plan or {}),
                        conversation_id,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row) if row else {}
        finally:
            conn.close()

    return await asyncio.to_thread(_run)


async def update_report(
    report_id: int,
    content: str | None = None,
    status: str | None = None,
) -> None:
    """Update a report's content and/or status."""
    def _run():
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                if content is not None and status is not None:
                    cur.execute(
                        "UPDATE reports SET content = %s, status = %s WHERE id = %s",
                        (content, status, report_id),
                    )
                elif content is not None:
                    cur.execute(
                        "UPDATE reports SET content = %s WHERE id = %s",
                        (content, report_id),
                    )
                elif status is not None:
                    cur.execute(
                        "UPDATE reports SET status = %s WHERE id = %s",
                        (status, report_id),
                    )
            conn.commit()
        finally:
            conn.close()

    await asyncio.to_thread(_run)


async def get_report(report_id: int) -> dict | None:
    """Get a single report by ID."""
    def _run():
        conn = _get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM reports WHERE id = %s", (report_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    return await asyncio.to_thread(_run)


async def get_reports(limit: int = 20) -> list[dict]:
    """List recent reports, newest first."""
    def _run():
        conn = _get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM reports ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    return await asyncio.to_thread(_run)