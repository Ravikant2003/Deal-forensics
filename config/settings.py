import os
from dotenv import load_dotenv

# Disable ChromaDB telemetry BEFORE any chromadb import
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

# Suppress torch warnings
os.environ["TORCH_CLASSES_SKIP"] = "True"

load_dotenv()

# ── LLM Provider: 'groq' or 'ollama' ─────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")  # Change to "ollama" for local

# ── Groq (cloud LLM) ────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AGENT_MODEL = "llama-3.3-70b-versatile"
SUPERVISOR_MODEL = "llama-3.3-70b-versatile"

# ── Ollama (local LLM) ──────────────────────────────────────────────────────────
OLLAMA_MODEL = "llama3.1:8b"
OLLAMA_BASE_URL = "http://localhost:11434"

# ── Embeddings ────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ── ChromaDB ──────────────────────────────────────────────────────────────────
CHROMA_PATH = "./chroma_db"
CHROMA_COLLECTION = "deals_data"

# ── Data paths ────────────────────────────────────────────────────────────────
SAMPLE_DEALS_PATH = "data/sample_deals.json"
CRM_DATA_PATH = "data/crm_data.json"
BENCHMARKS_PATH = "data/benchmarks.json"
PROMPTS_PATH = "config/prompts.yaml"

# ── RAG settings ─────────────────────────────────────────────────────────────
BM25_WEIGHT = 0.4
VECTOR_WEIGHT = 0.6
RAG_TOP_K = 3
USE_RERANKER = "false"  # Set to "true" to enable CrossEncoder reranking (requires sentence-transformers)
