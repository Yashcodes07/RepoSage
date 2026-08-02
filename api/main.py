"""
Phase 3-6+ FastAPI app.

Run:
    uvicorn main:app --reload

Endpoints:
    GET  /health
    GET  /stats          - real index size + which repo is actually indexed
    POST /ask            - direct RAG pipeline (Phase 3-5)
    POST /ask/agentic     - LangGraph agent: router + multi-hop (Phase 6)
    POST /index           - clone + index a repo live (Phase 8 addition)
"""

import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import (
    AskRequest,
    AskResponse,
    AgenticAskResponse,
    CitationOut,
    IndexRequest,
    IndexResponse,
)

from .rag_pipeline import answer_question
from .agent import run_agentic_query
from .indexing_service import index_repo, IndexingError
from .config import CHROMA_DIR, BM25_PATH
from indexing.vector_index import (
    get_client as get_chroma_client,
    get_collection as get_chroma_collection,
)
app = FastAPI(
    title="Codebase RAG API",
    description="Ask natural-language questions about an indexed codebase and get cited answers.",
    version="0.6.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def stats():
    """
    Reports the real current index size AND which repo was actually
    indexed (from indexing/index_metadata.json) — separate from
    whatever URL a user has typed into the frontend's citation-link
    field, which does NOT by itself change what's indexed.
    """
    try:
        client = get_chroma_client(CHROMA_DIR)
        collection = get_chroma_collection(client)
        chunk_count = collection.count()
    except Exception:
        chunk_count = None

    indexed_repo_url = None
    indexed_at = None
    metadata_path = Path(CHROMA_DIR).parent / "index_metadata.json"
    if metadata_path.exists():
        try:
            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
            indexed_repo_url = meta.get("repo_url")
            indexed_at = meta.get("indexed_at")
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "chunk_count": chunk_count,
        "indexed_repo_url": indexed_repo_url,
        "indexed_at": indexed_at,
    }


def _citations_out(citations) -> list[CitationOut]:
    return [
        CitationOut(
            file_path=c.file_path,
            start_line=c.start_line,
            end_line=c.end_line,
            name=c.name,
            code=c.code,
        )
        for c in citations
    ]


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    try:
        result = answer_question(request.question, top_k=request.top_k)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    return AskResponse(
        question=request.question,
        answer=result.answer,
        citations=_citations_out(result.citations),
        retrieved_chunk_count=result.retrieved_chunk_count,
    )


@app.post("/ask/agentic", response_model=AgenticAskResponse)
def ask_agentic(request: AskRequest):
    """
    Routes through the LangGraph agent (router -> simple / multi-hop
    decomposition / clarify) instead of always doing a single
    retrieve-then-answer pass. Kept as a separate endpoint from /ask
    so both can be compared directly.
    """
    try:
        result = run_agentic_query(request.question)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    return AgenticAskResponse(
        question=request.question,
        answer=result.answer,
        citations=_citations_out(result.citations),
        retrieved_chunk_count=result.retrieved_chunk_count,
        route=result.route,
        sub_questions=result.sub_questions,
        needs_clarification=result.needs_clarification,
    )


@app.post("/index", response_model=IndexResponse)
def index(request: IndexRequest):
    """
    Clones and indexes a repo live, replacing whatever was previously
    indexed. Defined as a plain sync function (not async def) —
    FastAPI/Starlette automatically runs sync route handlers in a
    thread pool, so a slow clone+index doesn't block other concurrent
    requests like /ask. Response simply takes as long as indexing does
    (a few seconds for a typical repo, based on real testing — large
    repos will take longer).
    """
    try:
        result = index_repo(request.repo_url, CHROMA_DIR, BM25_PATH)
    except IndexingError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error while indexing: {e}")

    return IndexResponse(**result)