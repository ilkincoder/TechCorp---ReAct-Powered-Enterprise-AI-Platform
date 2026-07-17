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

# ── Server ────────────────────────────────────────────────────────────────────
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))