# Phase 3: Basic RAG (FastAPI + Groq)

## What this does
Wires Phase 2's vector index to Groq's LLM, closing the loop:

```
question -> vector retrieval (Phase 2) -> build context -> Groq LLM -> cited answer
```

This is intentionally **vector-search-only** — no hybrid fusion, no
reranking yet (Phase 4/5). That makes it a clean baseline: once Phase 4
adds hybrid fusion, you can directly compare "vector-only answer" vs.
"hybrid-fusion answer" on the same questions for your README/interview.

## Files
- `config.py` — env vars, model choice, paths to Phase 2's index
- `llm.py` — thin wrapper around the Groq client + system prompt that
  enforces citations
- `rag_pipeline.py` — the actual RAG loop: retrieve -> build context ->
  call LLM -> return structured answer + citations
- `schemas.py` — Pydantic request/response models
- `main.py` — FastAPI app (`/ask`, `/health`)
- `ask.py` — CLI for testing without running the server

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and add your GROQ_API_KEY (free at https://console.groq.com/keys)
```

Make sure Phase 2's index already exists (run from `indexing/` if not):
```bash
cd ../indexing
python build_index.py --chunks ../ingestion/chunks.json
cd ../api
```

## Run — CLI (fastest way to test)
```bash
python ask.py "where is auth handled"
```

## Run — API server
```bash
uvicorn main:app --reload
```
Then open http://localhost:8000/docs for the interactive Swagger UI,
or:
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "where is auth handled", "top_k": 6}'
```

## Verified in this environment
- Cross-folder import of Phase 2's `vector_index.py` from `api/` — confirmed working
- `build_context()` correctly labels each chunk with its `file:line` citation and
  passes full code (not a truncated preview) to the LLM
- Full FastAPI request/response cycle tested end-to-end (`/health`, `/ask`)
  with a mocked LLM call — confirmed the API layer, schema validation,
  and citation serialization all work correctly
- **Not tested here**: an actual live Groq API call, since that needs
  your personal `GROQ_API_KEY`. Run `python ask.py "..."` on your machine
  to see the real answer.

## Bug fixed along the way
`vector_index.py` (Phase 2) originally truncated retrieved code to a
200-character preview for CLI display. That's fine for a terminal
printout but was silently starving the LLM of most of each function's
body. Fixed by returning both the full `code` and a separate
`code_preview` field — Phase 3 uses `code`, Phase 2's CLI still uses
`code_preview`.

## Next: Phase 4
Add Reciprocal Rank Fusion so BM25 and vector search both contribute
to what gets sent to the LLM — should directly improve cases like
"where is auth handled" where vector search alone ranked the right
answer 3rd instead of 1st.
