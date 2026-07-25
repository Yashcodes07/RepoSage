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

# Phase 5: reranking. Fusion pulls a wider candidate pool, the
# cross-encoder narrows it down to DEFAULT_TOP_K for the LLM.
#
# Default is FALSE based on real evaluation (see indexing/README.md,
# "Known issue" section): across 3 test queries on this codebase, the
# cross-encoder (ms-marco-MiniLM-L-6-v2, trained on prose search, not
# code) never beat fusion's own ranking, and actively demoted the
# correct answer on both genuinely semantic queries tested. Set to
# true only after you've validated it helps on YOUR queries.
FUSION_CANDIDATE_POOL = 15
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "false").lower() == "true"