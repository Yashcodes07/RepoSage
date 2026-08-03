"""
Phase 4 milestone script.

Usage:
    python compare_retrieval.py "where is auth handled"

Shows vector-only, BM25-only, and RRF-fused results side by side for
the same query, so you can see exactly what fusion changed — this is
the before/after comparison for your README.
"""

import argparse

from vector_index import get_client, get_collection, query_vector
from keyword_index import KeywordIndex
from fusion import reciprocal_rank_fusion


def print_ranked(title: str, items: list, get_label) -> None:
    print(f"\n--- {title} ---")
    for i, item in enumerate(items, start=1):
        print(f"  {i}. {get_label(item)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--chroma-dir", default="./chroma_store")
    parser.add_argument("--bm25-path", default="./bm25_index.pkl")
    args = parser.parse_args()

    client = get_client(args.chroma_dir)
    collection = get_collection(client)
    vector_results = query_vector(collection, args.query, top_k=args.top_k)

    kw_index = KeywordIndex()
    kw_index.load(args.bm25_path)
    keyword_results = kw_index.query(args.query, top_k=args.top_k)

    fused = reciprocal_rank_fusion(vector_results, keyword_results, top_n=args.top_k)

    print(f"Query: {args.query!r}\n")

    print_ranked(
        "Vector only",
        vector_results,
        lambda r: f"{r['file_path']}:{r['start_line']}-{r['end_line']}  [{r['name']}]  score={r['score']:.3f}",
    )
    print_ranked(
        "BM25 only",
        keyword_results,
        lambda r: f"{r['file_path']}:{r['start_line']}-{r['end_line']}  [{r['name']}]  score={r['score']:.2f}",
    )
    print_ranked(
        "Fused (RRF)",
        fused,
        lambda r: f"{r.file_path}:{r.start_line}-{r.end_line}  [{r.name}]  "
        f"rrf={r.fusion_score:.4f}  found_in={'+'.join(r.found_in)}",
    )

    # Highlight rank changes for the top fused result specifically —
    # this is the number worth putting in a README.
    if fused:
        top = fused[0]
        vec_rank = next((i + 1 for i, r in enumerate(vector_results) if r["id"] == top.id), None)
        bm25_rank = next((i + 1 for i, r in enumerate(keyword_results) if r["id"] == top.id), None)
        print(f"\n[compare] Top fused result: {top.file_path}:{top.start_line}-{top.end_line}")
        print(f"[compare]   -> vector-only rank: {vec_rank or 'not in top ' + str(args.top_k)}")
        print(f"[compare]   -> BM25-only rank:   {bm25_rank or 'not in top ' + str(args.top_k)}")


if __name__ == "__main__":
    main()