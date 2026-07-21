"""
Phase 4 core: hybrid RAG loop.

    question -> vector retrieval + BM25 retrieval -> RRF fusion -> build context -> Groq -> answer

Upgraded from Phase 3's vector-only retrieval. See indexing/fusion.py
for the fusion logic itself.
"""

import sys
from pathlib import Path
from dataclasses import dataclass

from config import CHROMA_DIR, BM25_PATH, INDEXING_DIR, DEFAULT_TOP_K

# indexing/ is a sibling folder, not a Python package — add it to the
# path so we can import Phase 2/4's retrieval code directly instead of
# duplicating it here.
sys.path.insert(0, INDEXING_DIR)

from fusion import hybrid_query  # noqa: E402
from llm import generate_answer  # noqa: E402


@dataclass
class Citation:
    file_path: str
    start_line: int
    end_line: int
    name: str

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
        )
        for c in chunks
    ]


def answer_question(question: str, top_k: int = DEFAULT_TOP_K) -> RagAnswer:
    """
    Runs the full Phase 4 loop for a single question: hybrid retrieval
    (vector + BM25, fused via RRF) -> context -> Groq -> cited answer.
    """
    chunks = hybrid_query(CHROMA_DIR, BM25_PATH, question, top_n=top_k)
    context = build_context(chunks)
    answer_text = generate_answer(question, context)

    return RagAnswer(
        answer=answer_text,
        citations=_extract_citations(chunks),
        retrieved_chunk_count=len(chunks),
    )