"""
Phase 1 milestone script.

Usage:
    python ingest.py <github_repo_url> [--out chunks.json]

Clones the repo, walks the tree, parses every source file with
tree-sitter, and prints/saves the resulting chunks with their
file:line metadata — proving the chunking step works before any
LLM/embedding is involved.
"""

import argparse
import json
import shutil
from pathlib import Path

from repo_loader import clone_repo, walk_repo
from chunker import chunk_file, chunk_whole_file_as_fallback, CodeChunk


def ingest_repo(repo_url: str, keep_clone: bool = False) -> list[CodeChunk]:
    # dest_dir=None makes clone_repo() create a proper OS temp dir
    # (e.g. /tmp/codebase_rag_xxxx on Mac/Linux) instead of a hardcoded path.
    repo_root = clone_repo(repo_url, dest_dir=None)

    try:
        source_files = walk_repo(repo_root)
        print(f"[ingest] {len(source_files)} source files found\n")

        all_chunks: list[CodeChunk] = []
        for sf in source_files:
            try:
                text = sf.absolute_path.read_text(encoding="utf-8", errors="ignore")
            except OSError as e:
                print(f"[skip] {sf.relative_path}: {e}")
                continue

            file_chunks = chunk_file(sf.relative_path, sf.language, text)

            # If tree-sitter found nothing (e.g. a tiny __init__.py), keep
            # the file as a single fallback chunk rather than losing it.
            if not file_chunks and text.strip():
                file_chunks = [chunk_whole_file_as_fallback(sf.relative_path, sf.language, text)]

            all_chunks.extend(file_chunks)

        return all_chunks
    finally:
        if not keep_clone:
            shutil.rmtree(repo_root, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_url", help="GitHub repo URL, e.g. https://github.com/user/repo.git")
    parser.add_argument("--out", default="chunks.json", help="Where to save the chunk data")
    parser.add_argument("--preview", type=int, default=15, help="How many chunks to print to console")
    args = parser.parse_args()

    chunks = ingest_repo(args.repo_url)

    print(f"[ingest] Extracted {len(chunks)} chunks total\n")
    print(f"--- Preview (first {args.preview}) ---\n")
    for c in chunks[: args.preview]:
        print(f"[{c.language}] {c.citation()}  ({c.node_type}: {c.name or 'unnamed'})")

    out_path = Path(args.out)
    out_path.write_text(
        json.dumps([c.__dict__ for c in chunks], indent=2),
        encoding="utf-8",
    )
    print(f"\n[ingest] Saved {len(chunks)} chunks to {out_path.resolve()}")


if __name__ == "__main__":
    main()