"""
Phase 3 config: environment variables and paths to the index built
in Phase 2.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# openai/gpt-oss-120b is Groq's recommended replacement for
# llama-3.3-70b-versatile, which Groq is shutting down on 2026-08-16.
# Override via .env if you want a different model.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Paths to Phase 2's index — indexing/ is a sibling folder of api/
_PROJECT_ROOT = Path(__file__).parent.parent
CHROMA_DIR = str(_PROJECT_ROOT / "indexing" / "chroma_store")
BM25_PATH = str(_PROJECT_ROOT / "indexing" / "bm25_index.pkl")
INDEXING_DIR = str(_PROJECT_ROOT / "indexing")

DEFAULT_TOP_K = 6
