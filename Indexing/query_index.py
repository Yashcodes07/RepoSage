"""
Phase 2 milestone script.

Usage:
    python query_index.py "where is auth handled"

Runs the SAME query against the vector index and the keyword index
SEPARATELY (no fusion/reranking yet — that's Phase 4/5) and prints
both result sets side by side, so you can see where they agree,
where they disagree, and why hybrid search will matter later.
"""

import argparse

from vector_index import get_client, get_collection, query_vector
from keyword_index import KeywordIndex


def print_results(title: str, results: list[dict]) -> None:
    print(f"\n--- {title} ---")
    if not results:
        print("  (no results)")
        return
    for r in results:
        loc = f"{r['file_path']}:{r['start_line']}-{r['end_line']}"
        name = r["name"] or "(unnamed)"
        print(f"  {r['score']:.3f}  {loc}  [{name}]")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="Natural language or keyword query")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--chroma-dir", default="./chroma_store")
    parser.add_argument("--bm25-path", default="./bm25_index.pkl")
    args = parser.parse_args()

    # Vector retrieval
    client = get_client(args.chroma_dir)
    collection = get_collection(client)
    vector_results = query_vector(collection, args.query, top_k=args.top_k)

    # Keyword retrieval
    kw_index = KeywordIndex()
    kw_index.load(args.bm25_path)
    keyword_results = kw_index.query(args.query, top_k=args.top_k)

    print(f"Query: {args.query!r}")
    print_results("Vector search (embeddings)", vector_results)
    print_results("Keyword search (BM25)", keyword_results)

    vector_ids = {r["id"] for r in vector_results}
    keyword_ids = {r["id"] for r in keyword_results}
    overlap = vector_ids & keyword_ids
    print(f"\n[query_index] Overlap: {len(overlap)}/{args.top_k} chunks "
          f"appeared in both result sets")


if __name__ == "__main__":
    main()