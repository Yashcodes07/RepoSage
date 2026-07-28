"""
Phase 5 core: hybrid RAG loop with reranking.

    question -> vector + BM25 retrieval -> RRF fusion (wide pool)
             -> cross-encoder rerank (narrow down) -> build context -> Groq -> answer

Upgraded from Phase 4's fusion-only retrieval. See indexing/reranker.py
for the reranking logic itself. Reranking can be disabled via the
RERANK_ENABLED env var (falls back to fusion's own ranking) — useful
if you're deploying somewhere too memory-constrained for the
cross-encoder's torch dependency; see indexing/README.md.
"""

import sys
from pathlib import Path
from dataclasses import dataclass

from config import (
    CHROMA_DIR,
    BM25_PATH,
    INDEXING_DIR,
    DEFAULT_TOP_K,
    FUSION_CANDIDATE_POOL,
    RERANK_ENABLED,
)

# indexing/ is a sibling folder, not a Python package — add it to the
# path so we can import Phase 2/4/5's retrieval code directly instead
# of duplicating it here.
sys.path.insert(0, INDEXING_DIR)

from vector_index import get_client, get_collection, query_vector  # noqa: E402
from keyword_index import KeywordIndex  # noqa: E402
from fusion import reciprocal_rank_fusion  # noqa: E402
from llm import generate_answer  # noqa: E402

if RERANK_ENABLED:
    from reranker import rerank  # noqa: E402


@dataclass
class Citation:
    file_path: str
    start_line: int
    end_line: int
    name: str
    code: str = ""

    def as_string(self) -> str:
        return f"{self.file_path}:{self.start_line}-{self.end_line}"


@dataclass
class RagAnswer:
    answer: str
    citations: list[Citation]
    retrieved_chunk_count: int


def build_context(chunks: list) -> str:
    """
    Formats retrieved (fused) chunks into a single string the LLM can
    read, with each chunk clearly labeled with its citation so the
    model can copy the exact (file:line) format into its answer.
    """
    if not chunks:
        return "(no relevant code found)"

    parts = []
    for c in chunks:
        label = f"{c.file_path}:{c.start_line}-{c.end_line}"
        name = c.name or "unnamed"
        parts.append(
            f"--- Chunk ({label}) — {name} ---\n{c.code}"
        )
    return "\n\n".join(parts)


def _extract_citations(chunks: list) -> list[Citation]:
    return [
        Citation(
            file_path=c.file_path,
            start_line=c.start_line,
            end_line=c.end_line,
            name=c.name,
            code=c.code,
        )
        for c in chunks
    ]


def retrieve_chunks(question: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Runs hybrid retrieval (vector + BM25 fusion, optional rerank) and
    returns the raw chunk objects — no LLM call yet. Split out from
    answer_question() so Phase 6's agent can retrieve separately per
    sub-question during multi-hop decomposition, then synthesize once
    across the combined results, instead of generating an intermediate
    answer for each sub-question.
    """
    client = get_client(CHROMA_DIR)
    collection = get_collection(client)
    vector_results = query_vector(collection, question, top_k=FUSION_CANDIDATE_POOL)

    kw_index = KeywordIndex()
    kw_index.load(BM25_PATH)
    keyword_results = kw_index.query(question, top_k=FUSION_CANDIDATE_POOL)

    fused = reciprocal_rank_fusion(vector_results, keyword_results, top_n=FUSION_CANDIDATE_POOL)

    if RERANK_ENABLED:
        return rerank(question, fused, top_n=top_k)
    return fused[:top_k]


def answer_question(question: str, top_k: int = DEFAULT_TOP_K) -> RagAnswer:
    """
    Runs the full Phase 5 loop for a single question: hybrid retrieval
    (vector + BM25) -> RRF fusion over a wide candidate pool ->
    cross-encoder rerank down to top_k -> context -> Groq -> cited answer.
    """
    chunks = retrieve_chunks(question, top_k)
    context = build_context(chunks)
    answer_text = generate_answer(question, context)

    return RagAnswer(
        answer=answer_text,
        citations=_extract_citations(chunks),
        retrieved_chunk_count=len(chunks),
    )