# RepoSage

A codebase RAG agent — point it at a GitHub repo, ask questions in plain English, get answers grounded in real, cited source code.

**Live demo:** [reposage-lake.vercel.app](https://reposage-lake.vercel.app)

---

## What it does

Most code search tools give you keyword matches. RepoSage retrieves real, coherent chunks of code via hybrid search, decomposes complex questions across multiple files when needed, and answers with every claim traceable back to an exact `file:line` — so you can verify it instead of just trusting it.

## How it works

```
Ingest      →  Clone the repo, parse every file with tree-sitter into
                function/class-level chunks — not naive text splitting.

Index       →  Embed each chunk into a vector store, build a parallel
                BM25 keyword index over the same chunks.

Retrieve    →  Run hybrid search (vector + BM25) on a question, fuse
                rankings with Reciprocal Rank Fusion.

Route       →  An agent classifies the question: direct lookup,
                multi-hop (needs decomposing across files), or too
                vague — ask for clarification instead of guessing.

Synthesize  →  Retrieved code is passed to an LLM, which answers with
                every claim cited to a specific file and line range.
```

## Tech stack

- **Ingestion:** `tree-sitter` (Python/JS/TS AST parsing), `GitPython`
- **Retrieval:** `ChromaDB` (vector search) + `rank_bm25` (keyword search), fused with Reciprocal Rank Fusion
- **Agent:** `LangGraph` — router + multi-hop decomposition
- **LLM:** Groq (`openai/gpt-oss-120b`)
- **Backend:** FastAPI
- **Frontend:** React, TypeScript, Tailwind v4, Vite
- **Eval:** RAGAS (faithfulness, answer relevancy, context precision)

## A few engineering decisions worth knowing about

- **Reranking was built, tested, and turned off.** A cross-encoder reranker was implemented and evaluated across real queries — it never beat hybrid fusion alone, and actively hurt results on genuinely semantic questions (the model favored literal token overlap over which chunk was actually correct). Rather than ship it because it was built, the evaluation data drove the decision to disable it by default. Full writeup in [`indexing/README.md`](./indexing/README.md).
- **Hybrid search, not just embeddings.** BM25 catches exact identifier matches that vector search alone can miss (e.g. `handleRetry`); fusion combines both signals per query.
- **Live re-indexing from the UI.** Paste any GitHub URL and the app clones, chunks, and rebuilds both indexes on demand — no CLI needed for normal use.

## Repo structure

```
ingestion/    Phase 1 — clone + AST-based chunking
indexing/     Phase 2/4/5 — vector + BM25 indexes, fusion, reranking (off by default)
api/          FastAPI backend — RAG pipeline, LangGraph agent, live indexing endpoint
eval/         RAGAS evaluation harness
frontend/     React chat UI + landing page
```

Each folder has its own README with setup steps and what was verified at that stage.

## Running locally

```bash
# 1. Backend
cd api
pip install -r requirements-deploy.txt   # see repo root
cp .env.example .env                      # add your GROQ_API_KEY
uvicorn main:app --reload

# 2. Frontend
cd frontend
npm install
npm run dev
```

Then open the frontend, paste a repo URL, hit **Index**, and start asking questions.

## Deployment

- **Frontend:** Vercel
- **Backend:** FastAPI app, deployable to Render/Railway — see `requirements-deploy.txt` at the repo root for the consolidated dependency list used for deployment.
