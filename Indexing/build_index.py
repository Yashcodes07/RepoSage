"""
Phase 2 build script.

Usage:
    python build_index.py --chunks ../ingestion/chunks.json

Loads the chunks produced by Phase 1 and builds:
  1. A ChromaDB vector index (persisted to ./chroma_store)
  2. A BM25 keyword index (persisted to ./bm25_index.pkl)

Both indexes are built from the exact same chunk list, so at query
time we can compare/combine results from each retriever fairly.
"""

import argparse
import json
import time
from pathlib import Path

from vector_index import get_client, get_collection, index_chunks, reset_collection
from keyword_index import KeywordIndex


def load_chunks(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not data:
        raise ValueError(f"No chunks found in {path} — run Phase 1 ingest.py first")
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", default="../ingestion/chunks.json")
    parser.add_argument("--chroma-dir", default="./chroma_store")
    parser.add_argument("--bm25-path", default="./bm25_index.pkl")
    args = parser.parse_args()

    chunks = load_chunks(args.chunks)
    print(f"[build_index] Loaded {len(chunks)} chunks from {args.chunks}")

    # --- Vector index ---
    t0 = time.time()
    client = get_client(args.chroma_dir)
    reset_collection(client)  # always a clean rebuild — see reset_collection() docstring
    collection = get_collection(client)
    index_chunks(collection, chunks)
    print(f"[build_index] Vector index built in {time.time() - t0:.1f}s "
          f"({collection.count()} vectors in '{collection.name}')")

    # --- Keyword index ---
    t0 = time.time()
    kw_index = KeywordIndex()
    kw_index.build(chunks)
    kw_index.save(args.bm25_path)
    print(f"[build_index] BM25 index built in {time.time() - t0:.1f}s "
          f"({len(kw_index.entries)} entries, saved to {args.bm25_path})")

    print("\n[build_index] Done. Run query_index.py to test retrieval.")


if __name__ == "__main__":
    main()