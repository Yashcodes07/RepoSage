"""
Keyword index: BM25 over the same chunks the vector index uses.

Why this exists alongside embeddings: embeddings are good at "what does
this code do conceptually" but often miss exact identifier matches —
a query like "what does handleRetry do" benefits from literal keyword
matching on `handleRetry`, which BM25 nails and embeddings sometimes
fuzz over. Hybrid search fuses both (see fusion.py).
"""

import pickle
import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from chunk_ids import generate_chunk_ids

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass
class BM25Entry:
    id: str
    file_path: str
    start_line: int
    end_line: int
    name: str
    code: str            # full chunk text, for LLM context
    code_preview: str     # short preview, for CLI/debug printing


def _tokenize(text: str) -> list[str]:
    """
    Simple identifier-aware tokenizer. Splits camelCase and snake_case
    into sub-tokens too (e.g. "handleRetry" -> ["handleRetry", "handle",
    "Retry"]) so partial-name queries still match.
    """
    raw_tokens = _TOKEN_RE.findall(text)
    tokens = []
    for tok in raw_tokens:
        tokens.append(tok.lower())
        # split snake_case
        if "_" in tok:
            tokens.extend(p.lower() for p in tok.split("_") if p)
        # split camelCase
        camel_parts = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", tok)
        if len(camel_parts) > 1:
            tokens.extend(p.lower() for p in camel_parts)
    return tokens


class KeywordIndex:
    def __init__(self):
        self.bm25: BM25Okapi | None = None
        self.entries: list[BM25Entry] = []

    def build(self, chunks: list[dict]) -> None:
        self.entries = []
        corpus_tokens = []
        ids = generate_chunk_ids(chunks)
        for chunk_id, c in zip(ids, chunks):
            # Include the file path alongside name+code. Without this, a
            # query like "auth" can completely miss a chunk in auth.py if
            # the word "auth" never appears as its own token in the code
            # body — the filename itself is a real keyword signal BM25
            # should get to use, not just an embedding-only signal.
            text = f"{c['file_path']} {c.get('name', '')} {c['code']}"
            corpus_tokens.append(_tokenize(text))
            self.entries.append(
                BM25Entry(
                    id=chunk_id,
                    file_path=c["file_path"],
                    start_line=c["start_line"],
                    end_line=c["end_line"],
                    name=c.get("name", ""),
                    code=c["code"],
                    code_preview=c["code"][:200],
                )
            )
        self.bm25 = BM25Okapi(corpus_tokens)

    def query(self, query_text: str, top_k: int = 10) -> list[dict]:
        if self.bm25 is None:
            raise RuntimeError("KeywordIndex.build() must be called before query()")

        query_tokens = _tokenize(query_text)
        scores = self.bm25.get_scores(query_tokens)

        ranked = sorted(
            zip(self.entries, scores), key=lambda pair: pair[1], reverse=True
        )[:top_k]

        return [
            {
                "id": entry.id,
                "file_path": entry.file_path,
                "start_line": entry.start_line,
                "end_line": entry.end_line,
                "name": entry.name,
                "code": entry.code,
                "code_preview": entry.code_preview,
                "score": float(score),
            }
            for entry, score in ranked
            if score > 0
        ]

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump({"bm25": self.bm25, "entries": self.entries}, f)

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.bm25 = data["bm25"]
        self.entries = data["entries"]