"""RAG Tool — Qdrant-powered hybrid search with cross-encoder re-ranking.

Indexes knowledge base PDFs into Qdrant with dual vectors (dense + sparse),
then retrieves via weighted hybrid fusion and re-ranks with a cross-encoder.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional

from qdrant_client import QdrantClient, models

from ..config import (
    KB_DIR,
    QDRANT_URL,
    QDRANT_COLLECTION,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    DENSE_MODEL,
    SPARSE_MODEL,
    CROSS_ENCODER_MODEL,
    HYBRID_ALPHA,
    RERANK_TOP_K_INITIAL,
)
from .base import BaseTool, ToolResult

# ═══════════════════════════════════════════════════════════════════════════════
# Module-level model singletons — loaded once, shared across all RAGTool instances
# ═══════════════════════════════════════════════════════════════════════════════

_dense_model = None
_sparse_model = None
_cross_encoder = None
_dense_name: Optional[str] = None
_sparse_name: Optional[str] = None
_cross_encoder_name: Optional[str] = None


def _get_dense_model(model_name: str):
    global _dense_model, _dense_name
    if _dense_model is None or _dense_name != model_name:
        from sentence_transformers import SentenceTransformer

        _dense_model = SentenceTransformer(model_name)
        _dense_name = model_name
    return _dense_model


def _get_sparse_model(model_name: str):
    global _sparse_model, _sparse_name
    if _sparse_model is None or _sparse_name != model_name:
        from fastembed import SparseTextEmbedding

        _sparse_model = SparseTextEmbedding(model_name=model_name)
        _sparse_name = model_name
    return _sparse_model


def _get_cross_encoder(model_name: str):
    global _cross_encoder, _cross_encoder_name
    if _cross_encoder is None or _cross_encoder_name != model_name:
        from sentence_transformers import CrossEncoder

        _cross_encoder = CrossEncoder(model_name)
        _cross_encoder_name = model_name
    return _cross_encoder


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: NLTK sentence tokenizer (one-time download)
# ═══════════════════════════════════════════════════════════════════════════════

_nltk_ready = False


def _ensure_nltk():
    global _nltk_ready
    if _nltk_ready:
        return
    import nltk

    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)
    _nltk_ready = True


# ═══════════════════════════════════════════════════════════════════════════════
# RAG Tool
# ═══════════════════════════════════════════════════════════════════════════════


class RAGTool(BaseTool):
    name = "rag_search"
    description = (
        "Search the TechCorp knowledge base (policies, guides, documentation) "
        "for relevant information. Use this for questions about company policies, "
        "engineering standards, compliance, HR, IT, security, and any internal "
        "procedures. Supports filtering by department or filename."
    )

    def __init__(self):
        self._client: Optional[QdrantClient] = None
        self._index_state_path = KB_DIR.parent / "data" / "qdrant_index_state.json"

    # ── client management ──────────────────────────────────────────────────

    def _get_client(self) -> QdrantClient:
        """Return a connected QdrantClient (lazy init, no network on construction)."""
        if self._client is None:
            self._client = QdrantClient(url=QDRANT_URL, timeout=30)
        return self._client

    # ── chunking ───────────────────────────────────────────────────────────

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
        """Split text into sentence-aware overlapping chunks."""
        _ensure_nltk()
        from nltk import sent_tokenize

        sentences = sent_tokenize(text)
        if not sentences:
            return []

        chunks = []
        current_chunk = ""
        overlap_buffer = ""

        for sentence in sentences:
            trial = (current_chunk + " " + sentence).strip()

            if len(trial) <= chunk_size:
                current_chunk = trial
            else:
                if current_chunk:
                    chunks.append(current_chunk)

                # Start a new chunk: carry overlap from the end of the previous one
                if overlap > 0 and len(current_chunk) > overlap:
                    # Walk backwards through current_chunk sentences to build overlap buffer
                    overlap_buffer = ""
                    rev_sentences = sent_tokenize(current_chunk)
                    for s in reversed(rev_sentences):
                        candidate = (s + " " + overlap_buffer).strip()
                        if len(candidate) <= overlap:
                            overlap_buffer = candidate
                        else:
                            break
                    current_chunk = (overlap_buffer + " " + sentence).strip()
                else:
                    current_chunk = sentence

        if current_chunk.strip():
            chunks.append(current_chunk)

        return chunks

    # ── file hashing (incremental indexing) ────────────────────────────────

    @staticmethod
    def _compute_file_hash(pdf_path: Path) -> str:
        """SHA-256 hex digest of a file's contents."""
        sha = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                sha.update(block)
        return sha.hexdigest()

    # ── collection setup ───────────────────────────────────────────────────

    def _ensure_collection(self):
        """Create the Qdrant collection if it does not exist."""
        client = self._get_client()

        collection_exists = any(
            col.name == QDRANT_COLLECTION
            for col in client.get_collections().collections
        )
        if collection_exists:
            return

        from qdrant_client.models import (
            Distance,
            SparseVectorParams,
            VectorParams,
        )

        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config={
                "dense": VectorParams(size=384, distance=Distance.COSINE),
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(),
            },
        )

    # ── index building ─────────────────────────────────────────────────────

    def _load_index_state(self) -> dict[str, str]:
        """Load {file_path: content_hash} from the state file."""
        if self._index_state_path.exists():
            return json.loads(self._index_state_path.read_text())
        return {}

    def _save_index_state(self, state: dict[str, str]):
        """Persist {file_path: content_hash} to disk."""
        self._index_state_path.parent.mkdir(parents=True, exist_ok=True)
        self._index_state_path.write_text(json.dumps(state, indent=2))

    def _build_index(
        self,
        force: bool = False,
        department: Optional[str] = None,
        progress_callback=None,
    ) -> dict:
        """Build or update the Qdrant vector index from knowledge base PDFs.

        Args:
            force: Re-index all PDFs from scratch (ignore hash cache).
            department: Only index a specific department folder.
            progress_callback: Optional callable(done, total, current_file).

        Returns:
            Stats dict: {total_pdfs, indexed, skipped, removed, total_chunks}.
        """
        import fitz  # pymupdf

        self._ensure_collection()
        client = self._get_client()
        dense = _get_dense_model(DENSE_MODEL)
        sparse = _get_sparse_model(SPARSE_MODEL)
        old_state = self._load_index_state() if not force else {}
        new_state: dict[str, str] = {}

        pdf_files = sorted(KB_DIR.rglob("*.pdf"))
        if department:
            pdf_files = [p for p in pdf_files if p.parent.name == department]

        stats = {
            "total_pdfs": len(pdf_files),
            "indexed": 0,
            "skipped": 0,
            "removed": 0,
            "total_chunks": 0,
        }

        if not pdf_files:
            # Clean up: delete points for removed PDFs
            removed = set(old_state.keys()) - {str(p) for p in pdf_files}
            for path_str in removed:
                filename = Path(path_str).name
                client.delete(
                    collection_name=QDRANT_COLLECTION,
                    points_selector=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="filename", match=models.MatchValue(value=filename)
                            )
                        ]
                    ),
                )
                stats["removed"] += 1
            self._save_index_state(new_state)
            return stats

        global_point_offset = 0

        for idx, pdf_path in enumerate(pdf_files):
            path_str = str(pdf_path)
            file_hash = self._compute_file_hash(pdf_path)

            if not force and path_str in old_state and old_state[path_str] == file_hash:
                new_state[path_str] = file_hash
                stats["skipped"] += 1
                if progress_callback:
                    progress_callback(idx + 1, len(pdf_files), pdf_path.name)
                continue

            department_name = pdf_path.parent.name
            filename = pdf_path.name

            try:
                doc = fitz.open(pdf_path)
                text = ""
                for page in doc:
                    text += page.get_text() + "\n"
                doc.close()

                if not text.strip():
                    new_state[path_str] = file_hash
                    stats["skipped"] += 1
                    if progress_callback:
                        progress_callback(idx + 1, len(pdf_files), pdf_path.name)
                    continue

                chunks = self._chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
                if not chunks:
                    new_state[path_str] = file_hash
                    stats["skipped"] += 1
                    if progress_callback:
                        progress_callback(idx + 1, len(pdf_files), pdf_path.name)
                    continue

                # Delete old points for this file before re-indexing
                client.delete(
                    collection_name=QDRANT_COLLECTION,
                    points_selector=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="filename", match=models.MatchValue(value=filename)
                            )
                        ]
                    ),
                )

                # Embed and upsert in batches
                batch_size = 50
                total_chunks = len(chunks)

                for i in range(0, total_chunks, batch_size):
                    batch = chunks[i : i + batch_size]
                    dense_embeddings = dense.encode(batch).tolist()
                    sparse_embeddings = list(sparse.embed(batch))

                    points = []
                    for k, chunk_text in enumerate(batch):
                        chunk_idx = i + k
                        sparse_vec = sparse_embeddings[k]
                        points.append(
                            models.PointStruct(
                                id=global_point_offset + chunk_idx,
                                vector={
                                    "dense": dense_embeddings[k],
                                    "sparse": models.SparseVector(
                                        indices=sparse_vec.indices.tolist()
                                        if hasattr(sparse_vec.indices, "tolist")
                                        else list(sparse_vec.indices),
                                        values=sparse_vec.values.tolist()
                                        if hasattr(sparse_vec.values, "tolist")
                                        else list(sparse_vec.values),
                                    ),
                                },
                                payload={
                                    "text": chunk_text,
                                    "filename": filename,
                                    "department": department_name,
                                    "chunk_idx": chunk_idx,
                                    "text_snippet": chunk_text[:200],
                                },
                            )
                        )

                    client.upsert(
                        collection_name=QDRANT_COLLECTION,
                        points=points,
                    )

                global_point_offset += total_chunks
                new_state[path_str] = file_hash
                stats["indexed"] += 1
                stats["total_chunks"] += total_chunks

            except Exception as e:
                print(f"  [RAG] Skipping {pdf_path.name}: {e}")
                continue

            if progress_callback:
                progress_callback(idx + 1, len(pdf_files), pdf_path.name)

        # Delete points for PDFs that no longer exist on disk
        existing_paths = {str(p) for p in pdf_files}
        removed = set(old_state.keys()) - existing_paths
        for path_str in removed:
            filename = Path(path_str).name
            client.delete(
                collection_name=QDRANT_COLLECTION,
                points_selector=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="filename", match=models.MatchValue(value=filename)
                        )
                    ]
                ),
            )
            stats["removed"] += 1

        self._save_index_state(new_state)
        return stats

    # ── execution (search) ─────────────────────────────────────────────────

    async def execute(
        self,
        query: str = "",
        top_k: int = 5,
        department: Optional[str] = None,
        filename: Optional[str] = None,
        allowed_departments: Optional[list[str]] = None,
        **kwargs,
    ) -> ToolResult:
        """Hybrid search + cross-encoder re-rank over the knowledge base."""
        self._ensure_collection()
        client = self._get_client()

        # Check if index has points
        collection_info = client.get_collection(QDRANT_COLLECTION)
        if collection_info.points_count == 0:
            # Lazy first-index
            self._build_index()

        collection_info = client.get_collection(QDRANT_COLLECTION)
        if collection_info.points_count == 0:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="Knowledge base index is empty. No PDFs found.",
            )

        try:
            dense_model = _get_dense_model(DENSE_MODEL)
            sparse_model = _get_sparse_model(SPARSE_MODEL)

            # ── Encode query ────────────────────────────────────────────
            dense_vec = dense_model.encode([query]).tolist()[0]
            sparse_vecs = list(sparse_model.embed([query]))
            sparse_vec = sparse_vecs[0]

            sparse_indices = (
                sparse_vec.indices.tolist()
                if hasattr(sparse_vec.indices, "tolist")
                else list(sparse_vec.indices)
            )
            sparse_values = (
                sparse_vec.values.tolist()
                if hasattr(sparse_vec.values, "tolist")
                else list(sparse_vec.values)
            )

            # ── Build Qdrant filter ─────────────────────────────────────
            qdrant_filter = None
            filter_conditions = []
            if allowed_departments:
                # Multi-department filter (RBAC) — MatchAny takes precedence
                filter_conditions.append(
                    models.FieldCondition(
                        key="department", match=models.MatchAny(any=allowed_departments)
                    )
                )
            elif department:
                filter_conditions.append(
                    models.FieldCondition(
                        key="department", match=models.MatchValue(value=department)
                    )
                )
            if filename:
                filter_conditions.append(
                    models.FieldCondition(
                        key="filename", match=models.MatchValue(value=filename)
                    )
                )
            if filter_conditions:
                qdrant_filter = models.Filter(must=filter_conditions)

            # ── Dense retrieval ─────────────────────────────────────────
            initial_limit = RERANK_TOP_K_INITIAL

            dense_result = client.query_points(
                collection_name=QDRANT_COLLECTION,
                query=dense_vec,
                using="dense",
                limit=initial_limit,
                with_payload=True,
                query_filter=qdrant_filter,
            )

            # ── Sparse retrieval ────────────────────────────────────────
            sparse_result = client.query_points(
                collection_name=QDRANT_COLLECTION,
                query=models.SparseVector(
                    indices=sparse_indices,
                    values=sparse_values,
                ),
                using="sparse",
                limit=initial_limit,
                with_payload=True,
                query_filter=qdrant_filter,
            )

            # ── Normalize & fuse scores ─────────────────────────────────
            def _normalize_scores(points):
                if not points:
                    return {}
                scores = [p.score for p in points if p.score is not None]
                if not scores:
                    return {}
                mn, mx = min(scores), max(scores)
                if mx == mn:
                    return {p.id: 1.0 for p in points}
                return {p.id: (p.score - mn) / (mx - mn) for p in points}

            dense_norm = _normalize_scores(dense_result.points)
            sparse_norm = _normalize_scores(sparse_result.points)

            # Collect all candidates with fused scores
            candidate_map: dict[str, dict] = {}
            for point in dense_result.points:
                payload = point.payload or {}
                candidate_map[point.id] = {
                    "id": point.id,
                    "text": payload.get("text", ""),
                    "filename": payload.get("filename", "unknown"),
                    "department": payload.get("department", "unknown"),
                    "dense_score": dense_norm.get(point.id, 0.0),
                    "sparse_score": 0.0,
                }

            for point in sparse_result.points:
                s_score = sparse_norm.get(point.id, 0.0)
                if point.id in candidate_map:
                    candidate_map[point.id]["sparse_score"] = s_score
                else:
                    payload = point.payload or {}
                    candidate_map[point.id] = {
                        "id": point.id,
                        "text": payload.get("text", ""),
                        "filename": payload.get("filename", "unknown"),
                        "department": payload.get("department", "unknown"),
                        "dense_score": 0.0,
                        "sparse_score": s_score,
                    }

            alpha = HYBRID_ALPHA
            for c in candidate_map.values():
                c["fused_score"] = (
                    alpha * c["dense_score"] + (1 - alpha) * c["sparse_score"]
                )

            candidates = sorted(
                candidate_map.values(),
                key=lambda c: c["fused_score"],
                reverse=True,
            )

            # ── Cross-encoder re-ranking ────────────────────────────────
            if len(candidates) > 1:
                cross = _get_cross_encoder(CROSS_ENCODER_MODEL)
                pairs = [(query, c["text"]) for c in candidates]
                ce_scores = cross.predict(pairs, show_progress_bar=False)

                for c, ce_score in zip(candidates, ce_scores):
                    c["ce_score"] = float(ce_score)

                candidates.sort(key=lambda c: c.get("ce_score", 0.0), reverse=True)
            else:
                # Single candidate — no re-ranking needed
                for c in candidates:
                    c["ce_score"] = c["fused_score"]

            # ── Top-k results ───────────────────────────────────────────
            top_candidates = candidates[: min(top_k, len(candidates))]

            results = []
            citations = []
            for c in top_candidates:
                results.append({
                    "text": c["text"],
                    "filename": c["filename"],
                    "department": c["department"],
                    "relevance": round(c.get("ce_score", c["fused_score"]), 3),
                })
                if c["filename"] not in citations:
                    citations.append(c["filename"])

            return ToolResult(
                tool_name=self.name,
                success=True,
                data={
                    "query": query,
                    "results": results,
                    "total_docs": collection_info.points_count,
                },
                citations=citations,
                metadata={
                    "top_k": top_k,
                    "retrieval_method": "hybrid+rerank",
                    "initial_candidates": len(candidates),
                    "reranked_to": len(top_candidates),
                    "department_filter": department,
                    "filename_filter": filename,
                },
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(e),
            )

    # ── schema ─────────────────────────────────────────────────────────────

    def _input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant knowledge base documents",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 5, max 20)",
                    "default": 5,
                },
                "department": {
                    "type": "string",
                    "description": "Filter results to a specific department folder (e.g., 'HR', 'Engineering', 'IT')",
                },
                "allowed_departments": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter results to multiple allowed departments (RBAC). Takes precedence over 'department'.",
                },
                "filename": {
                    "type": "string",
                    "description": "Filter results to a specific file (e.g., 'it-onboarding.pdf')",
                },
            },
            "required": ["query"],
        }
