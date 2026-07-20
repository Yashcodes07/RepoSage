"""
Vector index: embeds chunks and stores them in ChromaDB.

Uses ChromaDB's built-in ONNXMiniLM_L6_V2 embedding function instead of
sentence-transformers + torch. Same MiniLM model family, but ~90MB and
no torch dependency — this matters because the free-tier deploy targets
(Render 512MB, Railway free tier) can't comfortably fit a torch install.
"""

from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from chunk_ids import generate_chunk_ids

COLLECTION_NAME = "code_chunks"


def get_client(persist_dir: str = "./chroma_store") -> chromadb.ClientAPI:
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=persist_dir)


def get_collection(client: chromadb.ClientAPI):
    embed_fn = embedding_functions.ONNXMiniLM_L6_V2()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )


def _get_prebuilt_ids(chunks: list[dict]) -> list[str]:
    return generate_chunk_ids(chunks)


def index_chunks(collection, chunks: list[dict], batch_size: int = 64) -> None:
    """
    Embeds and upserts chunks into the ChromaDB collection in batches.
    We embed `name + code` (not just raw code) so identifier names carry
    extra weight in the embedding — helps semantic queries like
    "where is the retry logic" match a function named `retry_query`.
    """
    # Generate all IDs up front, over the FULL chunk list, so duplicate
    # file:line ranges get consistent '#1', '#2' suffixes regardless of
    # which batch they land in.
    all_ids = _get_prebuilt_ids(chunks)

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        ids = all_ids[i : i + batch_size]
        documents = [f"{c.get('name', '')}\n{c['code']}" for c in batch]
        metadatas = [
            {
                "file_path": c["file_path"],
                "start_line": c["start_line"],
                "end_line": c["end_line"],
                "name": c.get("name", ""),
                "language": c["language"],
                "node_type": c["node_type"],
            }
            for c in batch
        ]
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)


def query_vector(collection, query_text: str, top_k: int = 10) -> list[dict]:
    """
    Returns top_k chunks ranked by embedding similarity only.
    Each result: {id, file_path, start_line, end_line, name, code_preview, distance}
    """
    results = collection.query(query_texts=[query_text], n_results=top_k)

    output = []
    ids = results["ids"][0]
    metadatas = results["metadatas"][0]
    documents = results["documents"][0]
    distances = results["distances"][0]

    for id_, meta, doc, dist in zip(ids, metadatas, documents, distances):
        output.append(
            {
                "id": id_,
                "file_path": meta["file_path"],
                "start_line": meta["start_line"],
                "end_line": meta["end_line"],
                "name": meta["name"],
                "code_preview": doc[:200],
                "score": 1 - dist,  # cosine distance -> similarity
            }
        )
    return output