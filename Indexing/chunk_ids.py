"""
Shared logic for turning a chunk into a stable, globally unique ID.

Why this exists: `file_path:start_line-end_line` looks unique but isn't
always — e.g. two separate single-line arrow functions on the same line
(common in JSX, like `onClick={() => doThing()}` next to another one-liner)
can share identical start/end lines. ChromaDB requires hard-unique IDs, so
without disambiguation, indexing a real repo can crash on the very first
JSX-heavy project.

Both vector_index.py and keyword_index.py must use this SAME function,
building IDs from chunks in the SAME order, so a chunk's ID matches
across both indexes — this matters later in Phase 4 when we fuse results
from both retrievers by ID.
"""


def generate_chunk_ids(chunks: list[dict]) -> list[str]:
    """
    Returns a list of IDs, one per chunk, in the same order as the input.
    First occurrence of a given file:line-range gets the plain ID;
    any repeat gets a '#1', '#2', ... suffix appended.
    """
    seen_counts: dict[str, int] = {}
    ids: list[str] = []

    for chunk in chunks:
        base_id = f"{chunk['file_path']}:{chunk['start_line']}-{chunk['end_line']}"
        count = seen_counts.get(base_id, 0)

        ids.append(base_id if count == 0 else f"{base_id}#{count}")
        seen_counts[base_id] = count + 1

    return ids