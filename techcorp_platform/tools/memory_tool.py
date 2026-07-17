"""Memory Tool — persistent, semantic memory backed by PostgreSQL + Qdrant.

Postgres stores the raw text (source of truth). Qdrant stores embeddings for semantic search.
"""

import asyncio

from qdrant_client import QdrantClient, models

from ..config import QDRANT_URL, MEMORY_COLLECTION, DENSE_MODEL
from ..conversations import (
    insert_memory,
    update_memory,
    search_memories,
    recent_memories,
    clear_memories,
    bump_memory_usage,
    _get_memory_by_id,
)
from .base import BaseTool, ToolResult
from .rag_tool import _get_dense_model


class MemoryTool(BaseTool):
    name = "memory"
    description = """Store and search enterprise knowledge across conversations. Use this to remember
project details, deadlines, budgets, team assignments, meeting decisions, vendor/client information,
technical architecture decisions, process documentation, and business metrics.
The memory persists across sessions and is searched semantically (synonyms and paraphrases work).

Valid actions: 'store' (save enterprise context), 'search' (semantic search), 'recent' (get latest entries),
'clear' (delete all entries). There is no 'retrieve' action — use 'search' with a descriptive query.
When recalling business context or operational knowledge, always use action='search'."""

    # ── Qdrant helpers ──────────────────────────────────────────────────────

    def _get_qdrant_client(self) -> QdrantClient:
        """Lazy-init QdrantClient (no network on construction)."""
        if not hasattr(self, "_qdrant_client") or self._qdrant_client is None:
            self._qdrant_client = QdrantClient(url=QDRANT_URL, timeout=30)
        return self._qdrant_client

    def _ensure_memory_collection(self):
        """Create the Qdrant memory collection if it doesn't exist."""
        client = self._get_qdrant_client()
        existing = {col.name for col in client.get_collections().collections}
        if MEMORY_COLLECTION in existing:
            return
        client.create_collection(
            collection_name=MEMORY_COLLECTION,
            vectors_config={
                "dense": models.VectorParams(size=384, distance=models.Distance.COSINE),
            },
        )

    def _embed(self, text: str) -> list[float]:
        """Embed a single text into a 384-dim vector."""
        model = _get_dense_model(DENSE_MODEL)
        return model.encode([text]).tolist()[0]

    # ── Execute ─────────────────────────────────────────────────────────────

    async def execute(
        self,
        action: str = "search",
        query: str = "",
        content: str = "",
        entity_type: str = "project_detail",
        confidence: float = 0.5,
        source: str = "user",
        **kwargs,
    ) -> ToolResult:
        # The LLM planner sometimes hallucinates parameter names (text, fact, message,
        # info, etc.) instead of "content". Accept any non-empty string kwarg as
        # fallback for content, preferring common aliases first.
        if not content:
            for alias in ("text", "message", "fact", "info", "data", "value"):
                val = kwargs.pop(alias, "")
                if val:
                    content = val
                    break
            # Last resort: grab the first non-empty string kwarg
            if not content:
                for val in kwargs.values():
                    if isinstance(val, str) and val.strip():
                        content = val
                        break
        if action == "store":
            return await self._store_memory(content, entity_type, confidence, source)
        elif action == "search":
            category = kwargs.get("category") or kwargs.get("entity_type")
            return await self._search_memory(query, category)
        elif action == "recent":
            return await self._recent_memories(int(kwargs.get("limit", 10)))
        elif action == "clear":
            await clear_memories()
            # Also wipe the Qdrant collection
            try:
                client = self._get_qdrant_client()
                client.delete_collection(MEMORY_COLLECTION)
                self._ensure_memory_collection()
            except Exception:
                pass
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"message": "Memory cleared."},
            )
        else:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Unknown action: {action}. Use 'store', 'search', 'recent', or 'clear'.",
            )

    async def _store_memory(self, content: str, entity_type: str, confidence: float = 0.5, source: str = "user") -> ToolResult:
        # Semantic dedup: check Qdrant for a near-identical existing entry
        existing = await self._find_semantic_match(content, entity_type)
        if existing:
            await update_memory(
                entry_id=existing["id"],
                content=content,
                entity_type=entity_type,
                confidence=confidence,
                source=source,
            )
            # Re-embed and upsert into Qdrant with same point_id (overwrites old vector)
            try:
                self._ensure_memory_collection()
                vec = await asyncio.to_thread(self._embed, content)
                client = self._get_qdrant_client()
                client.upsert(
                    collection_name=MEMORY_COLLECTION,
                    points=[models.PointStruct(
                        id=existing["id"],
                        vector={"dense": vec},
                        payload={"entity_type": entity_type},
                    )],
                )
            except Exception as e:
                print(f"[memory] Qdrant upsert (update) failed for id={existing['id']}: {e}", flush=True)
            existing["content"] = content
            existing["type"] = entity_type
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"stored": existing, "updated": True},
                metadata={"entry_id": existing["id"]},
            )

        entry = await insert_memory(
            content=content,
            entity_type=entity_type,
            confidence=confidence,
            source=source,
        )
        # Upsert into Qdrant with the new Postgres ID
        try:
            self._ensure_memory_collection()
            vec = await asyncio.to_thread(self._embed, content)
            client = self._get_qdrant_client()
            client.upsert(
                collection_name=MEMORY_COLLECTION,
                points=[models.PointStruct(
                    id=entry["id"],
                    vector={"dense": vec},
                    payload={"entity_type": entity_type},
                )],
            )
        except Exception as e:
            print(f"[memory] Qdrant upsert (insert) failed for id={entry['id']}: {e}", flush=True)
        return ToolResult(
            tool_name=self.name,
            success=True,
            data={"stored": entry},
            metadata={"entry_id": entry["id"]},
        )

    async def _find_semantic_match(self, content: str, entity_type: str) -> dict | None:
        """Check Qdrant for a near-identical existing entry. Returns it or None.

        If the top Qdrant hit has cosine similarity >= 0.75, treat it as the same fact
        and update instead of inserting a duplicate. Searches across ALL entity types
        — the LLM planner may assign different categories to the same underlying fact.
        Point IDs are the Postgres integer IDs — no mapping needed.
        """
        DEDUP_THRESHOLD = 0.75
        try:
            self._ensure_memory_collection()
            vec = await asyncio.to_thread(self._embed, content)
            client = self._get_qdrant_client()
            results = client.query_points(
                collection_name=MEMORY_COLLECTION,
                query=vec,
                limit=1,
                with_payload=True,
                using="dense",
            )
            if results.points and results.points[0].score and results.points[0].score >= DEDUP_THRESHOLD:
                pg_id = results.points[0].id  # point ID is the Postgres integer
                if isinstance(pg_id, int):
                    # Direct lookup by ID — avoids missing older entries
                    entry = await _get_memory_by_id(pg_id)
                    if entry:
                        return entry
            return None
        except Exception as e:
            print(f"[memory] Semantic dedup search failed: {e}", flush=True)
            return None

    async def _search_memory(self, query: str, entity_type: str = "") -> ToolResult:
        """Semantic search across memory entries via Qdrant embeddings + Postgres fetch."""
        if not query:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"results": [], "query": ""},
            )

        results = await search_memories(query=query, entity_type=entity_type)

        # Bump usage for matched entries
        for entry in results:
            await bump_memory_usage(entry["id"])

        # Count total entries for metadata
        all_recent = await recent_memories(limit=1000)

        return ToolResult(
            tool_name=self.name,
            success=True,
            data={
                "query": query,
                "results": results,
                "total_entries": len(all_recent),
            },
            metadata={"match_count": len(results)},
        )

    async def _recent_memories(self, limit: int = 10) -> ToolResult:
        results = await recent_memories(limit=limit)
        all_entries = await recent_memories(limit=1000)
        return ToolResult(
            tool_name=self.name,
            success=True,
            data={"results": results, "total_entries": len(all_entries)},
            metadata={"limit": limit},
        )

    def _input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["store", "search", "recent", "clear"],
                    "description": "Action: 'store' a fact, 'search' memories, get 'recent' entries, or 'clear' all",
                },
                "query": {
                    "type": "string",
                    "description": "Search query (for 'search' action)",
                },
                "content": {
                    "type": "string",
                    "description": "Content to store (for 'store' action)",
                },
                "entity_type": {
                    "type": "string",
                    "enum": ["project_detail", "task", "deadline", "budget", "team_structure",
                             "meeting_decision", "vendor_customer", "technical_context",
                             "process_workflow", "employee_info", "business_metric",
                             "conversation_summary"],
                    "description": "Category of enterprise memory for filtered retrieval",
                    "default": "project_detail",
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence score 0.0-1.0 (for 'store' action)",
                    "default": 0.5,
                },
                "source": {
                    "type": "string",
                    "enum": ["user", "system", "inferred"],
                    "description": "Origin of the memory entry",
                    "default": "user",
                },
            },
            "required": ["action"],
        }
