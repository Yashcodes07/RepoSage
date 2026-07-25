"""
Phase 5 milestone script.

Usage:
    python compare_reranking.py "where is auth handled"

Shows the fused (RRF) ranking vs the reranked ranking side by side —
this is the direct evidence for whether the cross-encoder is actually
cleaning up noise like the `get_connections` false-positive seen in
Phase 4, or just reordering things that were already fine.
"""

import argparse

from vector_index import get_client, get_collection, query_vector
from keyword_index import KeywordIndex
from fusion import reciprocal_rank_fusion
from reranker import rerank

# Pull a wider candidate pool from fusion than we'll actually keep —
# the reranker's job is to pick the best subset, not just re-sort a
# list that's already been cut down to size.
FUSION_CANDIDATE_POOL = 15


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--top-n", type=int, default=6, help="Final chunk count after reranking")
    parser.add_argument("--chroma-dir", default="./chroma_store")
    parser.add_argument("--bm25-path", default="./bm25_index.pkl")
    args = parser.parse_args()

    client = get_client(args.chroma_dir)
    collection = get_collection(client)
    vector_results = query_vector(collection, args.query, top_k=FUSION_CANDIDATE_POOL)

    kw_index = KeywordIndex()
    kw_index.load(args.bm25_path)
    keyword_results = kw_index.query(args.query, top_k=FUSION_CANDIDATE_POOL)

    fused = reciprocal_rank_fusion(vector_results, keyword_results, top_n=FUSION_CANDIDATE_POOL)
    reranked = rerank(args.query, fused, top_n=args.top_n)

    print(f"Query: {args.query!r}\n")

    print(f"--- Fused (RRF), top {args.top_n} of {len(fused)} candidates ---")
    for i, r in enumerate(fused[: args.top_n], 1):
        print(f"  {i}. {r.file_path}:{r.start_line}-{r.end_line}  [{r.name}]  rrf={r.fusion_score:.4f}")

    print(f"\n--- Reranked, top {args.top_n} ---")
    for i, r in enumerate(reranked, 1):
        print(f"  {i}. {r.file_path}:{r.start_line}-{r.end_line}  [{r.name}]  rerank_score={r.rerank_score:.4f}")

    # Flag anything the reranker dropped that fusion had in its top N —
    # this is the noise-filtering effect made visible.
    fused_top_ids = {r.id for r in fused[: args.top_n]}
    reranked_ids = {r.id for r in reranked}
    dropped = fused_top_ids - reranked_ids
    added = reranked_ids - fused_top_ids
    if dropped:
        print(f"\n[compare] Reranker DROPPED from fusion's top {args.top_n}:")
        for r in fused[: args.top_n]:
            if r.id in dropped:
                print(f"    {r.file_path}:{r.start_line}-{r.end_line}  [{r.name}]")
    if added:
        print(f"\n[compare] Reranker PROMOTED from lower in the candidate pool:")
        for r in reranked:
            if r.id in added:
                print(f"    {r.file_path}:{r.start_line}-{r.end_line}  [{r.name}]")
    if not dropped and not added:
        print(f"\n[compare] Reranker kept the same top {args.top_n} chunks as fusion (just re-ordered, or agreed).")


if __name__ == "__main__":
    main()