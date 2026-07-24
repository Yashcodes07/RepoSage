"""
Phase 5: cross-encoder reranking.

Why this exists on top of fusion (Phase 4): vector search and BM25 both
score a query against a chunk WITHOUT ever looking at them together —
vector search compares two independently-computed embeddings, BM25
counts token overlap. A cross-encoder is different: it reads the query
and the chunk TOGETHER in a single forward pass and outputs one
relevance score. That's much more accurate, but much more expensive —
you can't precompute it offline like embeddings, it has to run at
query time for every candidate. So the pattern is:

    fusion (cheap, broad) -> top ~15 candidates -> reranker (expensive, precise) -> top 6

This is also where the noise you saw in Phase 4 (e.g. `get_connections`
showing up in fused results purely because BM25 liked a token overlap)
gets cleaned up — a cross-encoder actually reads the chunk's code and
can tell it isn't really about auth, instead of just counting words.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2 — a small (~80MB), widely
used reranker. NOT bge-reranker-base — that model is larger and, more
importantly, running ANY cross-encoder locally requires sentence-
transformers + torch, which is a much heavier dependency than anything
used in Phases 1-4 (multiple GB with CUDA deps on a default pip
install). See README for the free-tier deployment implication and a
lighter alternative (Cohere's rerank API) if this doesn't fit your
target deploy environment.
"""

from dataclasses import dataclass

RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_model_cache = None


@dataclass
class RerankedResult:
    id: str
    file_path: str
    start_line: int
    end_line: int
    name: str
    code: str
    rerank_score: float
    fusion_score: float
    found_in: list[str]  # carried through from fusion, for debugging/comparison


def _get_model():
    """
    Lazily loads and caches the cross-encoder model. Import is deferred
    inside this function (not at module top) so that importing
    reranker.py doesn't force a torch import/model download for code
    that only needs the RerankedResult type or doesn't rerank at all.
    """
    global _model_cache
    if _model_cache is None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as e:
            raise RuntimeError(
                "sentence-transformers is not installed. Run "
                "`pip install sentence-transformers` (Phase 5's requirements.txt). "
                "Note: this pulls in torch, a multi-GB dependency — see README."
            ) from e
        _model_cache = CrossEncoder(RERANKER_MODEL_NAME)
    return _model_cache


def rerank(query: str, candidates: list, top_n: int = 6) -> list[RerankedResult]:
    """
    Re-scores fused candidates with a cross-encoder and returns the
    top_n, sorted by rerank score descending.

    `candidates` is the list of FusedResult objects from fusion.py.
    Pass a larger candidate pool than you actually want back (e.g. 15
    fused candidates -> reranked down to 6) — the reranker's value is
    in choosing the best subset, not in re-ordering an already-tiny list.
    """
    if not candidates:
        return []

    model = _get_model()

    pairs = [(query, c.code) for c in candidates]
    scores = model.predict(pairs)  # higher = more relevant

    scored = list(zip(candidates, scores))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    top = scored[:top_n]

    return [
        RerankedResult(
            id=c.id,
            file_path=c.file_path,
            start_line=c.start_line,
            end_line=c.end_line,
            name=c.name,
            code=c.code,
            rerank_score=float(score),
            fusion_score=c.fusion_score,
            found_in=c.found_in,
        )
        for c, score in top
    ]