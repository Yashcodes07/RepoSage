"""
Phase 4: Reciprocal Rank Fusion (RRF).

Vector search and BM25 each return their own ranked list for a query.
RRF combines them into one list without needing to compare raw scores
directly (which you can't do fairly — cosine similarity and BM25 scores
live on completely different scales). Instead it only looks at each
chunk's *rank* in each list:

    score(chunk) = sum over each retriever of  1 / (k + rank_in_that_retriever)

A chunk ranked #1 in both lists scores highest. A chunk that only shows
up in one list still contributes, just less. k=60 is the constant used
in the original RRF paper and by systems like Elasticsearch's hybrid
search — it softens the impact of rank 1 vs rank 2 so a single retriever
can't dominate just by having a huge score gap.
"""

from dataclasses import dataclass

from vector_index import get_client, get_collection, query_vector
from keyword_index import KeywordIndex

RRF_K = 60


@dataclass
class FusedResult:
    id: str
    file_path: str
    start_line: int
    end_line: int
    name: str
    code: str
    fusion_score: float
    found_in: list[str]  # e.g. ["vector", "keyword"] or just ["vector"]


def reciprocal_rank_fusion(
    vector_results: list[dict],
    keyword_results: list[dict],
    k: int = RRF_K,
    top_n: int = 8,
) -> list[FusedResult]:
    """
    Merges two independently-ranked result lists into one fused ranking.
    """
    scores: dict[str, float] = {}
    sources: dict[str, list[str]] = {}
    chunk_data: dict[str, dict] = {}

    for rank, item in enumerate(vector_results, start=1):
        cid = item["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        sources.setdefault(cid, []).append("vector")
        chunk_data[cid] = item

    for rank, item in enumerate(keyword_results, start=1):
        cid = item["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        sources.setdefault(cid, []).append("keyword")
        chunk_data.setdefault(cid, item)  # don't overwrite if vector already has it

    ranked_ids = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)[:top_n]

    results = []
    for cid, score in ranked_ids:
        d = chunk_data[cid]
        results.append(
            FusedResult(
                id=cid,
                file_path=d["file_path"],
                start_line=d["start_line"],
                end_line=d["end_line"],
                name=d.get("name", ""),
                code=d.get("code", d.get("code_preview", "")),
                fusion_score=score,
                found_in=sources[cid],
            )
        )
    return results


def hybrid_query(
    chroma_dir: str,
    bm25_path: str,
    query_text: str,
    top_k_per_retriever: int = 10,
    top_n: int = 8,
) -> list[FusedResult]:
    """
    Runs both retrievers independently, then fuses. This is the function
    Phase 3's rag_pipeline.py swaps in to replace vector-only retrieval.
    """
    client = get_client(chroma_dir)
    collection = get_collection(client)
    vector_results = query_vector(collection, query_text, top_k=top_k_per_retriever)

    kw_index = KeywordIndex()
    kw_index.load(bm25_path)
    keyword_results = kw_index.query(query_text, top_k=top_k_per_retriever)

    return reciprocal_rank_fusion(vector_results, keyword_results, top_n=top_n)