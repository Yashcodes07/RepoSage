"""
Phase 3 FastAPI app.

Run:
    uvicorn main:app --reload

Then either hit POST /ask directly, or open http://localhost:8000/docs
for the interactive Swagger UI (FastAPI generates this automatically).
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from schemas import AskRequest, AskResponse, AgenticAskResponse, CitationOut
from rag_pipeline import answer_question
from agent import run_agentic_query
from config import CHROMA_DIR
from vector_index import get_client as get_chroma_client, get_collection as get_chroma_collection

app = FastAPI(
    title="Codebase RAG API",
    description="Ask natural-language questions about an indexed codebase and get cited answers.",
    version="0.1.0",  # Phase 3: basic RAG, vector search only
)

# Wide-open CORS for local development (Phase 8's frontend will hit this
# from a different port). Tighten this before deploying publicly.
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
    indexed (from indexing/index_metadata.json, written by
    indexing/build_index.py) — separate from whatever URL a user has
    typed into the frontend's citation-link field, which does NOT
    trigger indexing on its own. This lets the UI be honest when those
    two disagree, instead of silently answering about a different repo
    than the one the person typed.
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


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    try:
        result = answer_question(request.question, top_k=request.top_k)
    except RuntimeError as e:
        # e.g. missing GROQ_API_KEY
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    citations = [
        CitationOut(
            file_path=c.file_path,
            start_line=c.start_line,
            end_line=c.end_line,
            name=c.name,
            code=c.code,
        )
        for c in result.citations
    ]

    return AskResponse(
        question=request.question,
        answer=result.answer,
        citations=citations,
        retrieved_chunk_count=result.retrieved_chunk_count,
    )


@app.post("/ask/agentic", response_model=AgenticAskResponse)
def ask_agentic(request: AskRequest):
    """
    Phase 6: routes through the LangGraph agent (router -> simple /
    multi-hop decomposition / clarify) instead of always doing a
    single retrieve-then-answer pass. Kept as a SEPARATE endpoint from
    /ask (not a replacement) so both can be compared directly — same
    pattern as RERANK_ENABLED being toggleable rather than a hard swap.
    """
    try:
        result = run_agentic_query(request.question)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    citations = [
        CitationOut(
            file_path=c.file_path,
            start_line=c.start_line,
            end_line=c.end_line,
            name=c.name,
            code=c.code,
        )
        for c in result.citations
    ]

    return AgenticAskResponse(
        question=request.question,
        answer=result.answer,
        citations=citations,
        retrieved_chunk_count=result.retrieved_chunk_count,
        route=result.route,
        sub_questions=result.sub_questions,
        needs_clarification=result.needs_clarification,
    )