"""TechCorp Enterprise AI Platform — configuration."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
KB_DIR = ROOT / "knowledge_base"

# ── LLM (DeepSeek) ───────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# ── Qdrant (RAG vector store) ───────────────────────────────────────────────
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "knowledge_base")
MEMORY_COLLECTION = os.getenv("QDRANT_MEMORY_COLLECTION", "memory")

# ── RAG Pipeline ─────────────────────────────────────────────────────────────
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
DENSE_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
SPARSE_MODEL = os.getenv("SPARSE_MODEL", "prithivida/Splade_PP_en_v1")
CROSS_ENCODER_MODEL = os.getenv("CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
HYBRID_ALPHA = float(os.getenv("HYBRID_ALPHA", "0.7"))
RERANK_TOP_K_INITIAL = int(os.getenv("RERANK_TOP_K_INITIAL", "20"))

# ── PostgreSQL ───────────────────────────────────────────────────────────────
POSTGRES_USER = os.getenv("POSTGRES_USER", "techcorp")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")  # required — set in .env
POSTGRES_DB = os.getenv("POSTGRES_DB", "techcorp_enterprise")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# ── Web Search ─────────────────────────────────────────────────────────────
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "")
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "duckduckgo")

# ── LangSmith Tracing ───────────────────────────────────────────────────────
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "techcorp-enterprise")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")


def _wrap_client(client):
    """Apply LangSmith tracing wrapper if enabled, otherwise return as-is."""
    if LANGSMITH_TRACING and LANGSMITH_API_KEY:
        from langsmith import wrappers
        return wrappers.wrap_openai(client)
    return client


def get_openai_client() -> "OpenAI":
    """Return a synchronous OpenAI client (LangSmith-traced when configured)."""
    from openai import OpenAI
    return _wrap_client(OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    ))


def get_async_openai_client() -> "AsyncOpenAI":
    """Return an async OpenAI client (LangSmith-traced when configured)."""
    from openai import AsyncOpenAI
    return _wrap_client(AsyncOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    ))

# ── Server ────────────────────────────────────────────────────────────────────
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))