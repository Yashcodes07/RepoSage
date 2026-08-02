"""
Live "index this repo" service, called from POST /index.

Reuses Phase 1's ingest_repo() and Phase 2's vector_index/keyword_index
functions directly — no reimplementation, same logic the CLI scripts
(ingestion/ingest.py, indexing/build_index.py) already use and were
already tested with.

Runs as a plain sync function. FastAPI/Starlette automatically runs
sync `def` route handlers in a thread pool, so this doesn't block
other concurrent requests (e.g. /ask) while a clone+index is running —
same pattern already used by every other endpoint in this API.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "ingestion"))
sys.path.insert(0, str(_PROJECT_ROOT / "indexing"))

from ingest import ingest_repo  # noqa: E402
from vector_index import get_client, get_collection, index_chunks, reset_collection  # noqa: E402
from keyword_index import KeywordIndex  # noqa: E402


class IndexingError(Exception):
    """Raised when cloning/parsing/indexing fails, with a message safe to show the user."""


def index_repo(repo_url: str, chroma_dir: str, bm25_path: str) -> dict:
    """
    Clones + chunks the given repo, then builds a fresh vector + BM25
    index from it — replacing whatever was indexed before (this is a
    full re-index, not an incremental add). Returns metadata about
    what was indexed; raises IndexingError with a clear message on
    failure (e.g. bad URL, zero parseable files).

    chroma_dir/bm25_path are passed in explicitly (not imported from
    config here) deliberately: both api/config.py and
    ingestion/config.py are named `config.py`, and this module also
    inserts ingestion/ onto sys.path — importing `config` here would
    be at real risk of silently resolving to the WRONG one depending
    on what else has already been imported first. Explicit parameters
    sidestep the ambiguity entirely instead of relying on import order.
    """
    try:
        chunks = ingest_repo(repo_url)
    except Exception as e:
        raise IndexingError(f"Couldn't clone or parse that repo: {e}") from e

    if not chunks:
        raise IndexingError(
            "Cloned the repo, but found 0 parseable source files. "
            "This chunker currently only supports Python and JS/TS/JSX/TSX — "
            "a repo that's mostly notebooks, other languages, or docs won't "
            "produce any chunks."
        )

    chunk_dicts = [c.__dict__ for c in chunks]

    # Vector index — reset first so a previous repo's vectors don't
    # linger alongside the new ones (upsert only overwrites matching
    # IDs, it never deletes stale ones — see vector_index.py).
    client = get_client(chroma_dir)
    reset_collection(client)
    collection = get_collection(client)
    index_chunks(collection, chunk_dicts)

    # BM25 index
    kw_index = KeywordIndex()
    kw_index.build(chunk_dicts)
    kw_index.save(bm25_path)

    indexed_at = datetime.now(timezone.utc).isoformat()

    # Same metadata file /stats already reads — so the UI immediately
    # reflects the new repo without any other change needed.
    index_metadata_path = Path(chroma_dir).parent / "index_metadata.json"
    index_metadata_path.write_text(
        json.dumps({
            "repo_url": repo_url,
            "chunk_count": len(chunks),
            "indexed_at": indexed_at,
        }, indent=2),
        encoding="utf-8",
    )

    return {
        "repo_url": repo_url,
        "chunk_count": len(chunks),
        "indexed_at": indexed_at,
    }