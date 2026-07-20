"""
Phase 3 core: the actual "basic RAG" loop.

    question -> vector retrieval (Phase 2) -> build context -> Groq -> answer

No fusion or reranking yet (Phase 4/5) — this uses vector search alone,
which is what makes it a fair baseline to compare fusion against later.
"""

import sys
from pathlib import Path
from dataclasses import dataclass

from config import CHROMA_DIR, INDEXING_DIR, DEFAULT_TOP_K

# indexing/ is a sibling folder, not a Python package — add it to the
# path so we can import Phase 2's vector_index.py directly instead of
# duplicating that code here.
sys.path.insert(0, INDEXING_DIR)

from vector_index import get_client as get_chroma_client, get_collection, query_vector  # noqa: E402
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


def build_context(chunks: list[dict]) -> str:
    """
    Formats retrieved chunks into a single string the LLM can read,
    with each chunk clearly labeled with its citation so the model
    can copy the exact (file:line) format into its answer.
    """
    if not chunks:
        return "(no relevant code found)"

    parts = []
    for c in chunks:
        label = f"{c['file_path']}:{c['start_line']}-{c['end_line']}"
        name = c.get("name") or "unnamed"
        code = c.get("code", c.get("code_preview", ""))
        parts.append(
            f"--- Chunk ({label}) — {name} ---\n{code}"
        )
    return "\n\n".join(parts)


def _extract_citations(chunks: list[dict]) -> list[Citation]:
    return [
        Citation(
            file_path=c["file_path"],
            start_line=c["start_line"],
            end_line=c["end_line"],
            name=c.get("name", ""),
        )
        for c in chunks
    ]


def answer_question(question: str, top_k: int = DEFAULT_TOP_K) -> RagAnswer:
    """
    Runs the full Phase 3 loop for a single question.
    """
    client = get_chroma_client(CHROMA_DIR)
    collection = get_collection(client)

    chunks = query_vector(collection, question, top_k=top_k)
    context = build_context(chunks)
    answer_text = generate_answer(question, context)

    return RagAnswer(
        answer=answer_text,
        citations=_extract_citations(chunks),
        retrieved_chunk_count=len(chunks),
    )
