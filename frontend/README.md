# Phase 8: Frontend (RepoSage)

React + TypeScript + Tailwind v4 chat UI for the codebase RAG agent
built in Phases 1-6. Talks to the FastAPI backend in `api/`.

## What it looks like
A two-pane layout: a sidebar (repo URL for citation links, real index
stats pulled from `/stats`) and a chat thread. Every answer shows:
- **The answer itself**, rendered as markdown
- **Citation chips** — click one to peek the actual retrieved code
  inline, or open it on GitHub at the exact line range
- **A pipeline trace** — the real router decision, sub-questions (for
  multi-hop), and retrieval steps behind that specific answer, instead
  of a generic spinner. This is deliberate: the whole point of this
  project is the retrieval engineering underneath, so the UI makes
  that visible rather than hiding it.

Toggle **agentic mode** below the input to route questions through
Phase 6's LangGraph agent (`/ask/agentic`) instead of the direct
pipeline (`/ask`) — lets you compare both on the same question.

## Setup
```bash
npm install
```

## Run
Start the backend first (from `api/`):
```bash
uvicorn main:app --reload
```
Then, from this folder:
```bash
npm run dev
```
Open the URL Vite prints (typically http://localhost:5173). API calls
to `/api/*` are proxied to `http://localhost:8000` in dev — see
`vite.config.ts`. No `.env` needed for local development.

## Build
```bash
npm run build
```

## Backend changes made to support this frontend
Two real fixes, not just new frontend code:

1. **`api/schemas.py` + `api/main.py`** — `CitationOut` didn't include
   the actual retrieved code, only file path/line numbers/name. The
   citation-peek feature (this UI's main differentiator) needs real
   content to show, not just a label. Added a `code` field, populated
   it in both `/ask` and `/ask/agentic`'s citation conversion. Verified
   with a real test — citations now correctly include code content.

2. **`api/main.py`** — added `GET /stats`, reporting the real current
   ChromaDB chunk count. The original Phase 8 plan implied a live
   "index this repo" button, but no backend endpoint exists yet for
   triggering ingestion via API (Phases 1-2 are still CLI-only) —
   rather than build a UI that promises a feature that doesn't work,
   the sidebar honestly shows real index stats and explains that
   indexing currently runs via the CLI scripts.

## Verified in this environment
- `npx tsc -b` — zero type errors (caught and fixed one real type-
  narrowing bug in `PipelineTrace.tsx` before this was clean)
- `npm run build` — clean production build, no errors or warnings
  (caught and fixed a CSS `@import` ordering issue)
- Dev server boots and serves the correct HTML shell
- Backend: `/ask`, `/ask/agentic`, and the new `/stats` endpoint all
  tested with FastAPI's TestClient and mocked pipeline calls

**Not tested here**: an actual live browser render, or a real backend
connection (no Groq quota available today — see `eval/README.md`).
Visual appearance is unverified beyond the compiled build succeeding;
worth a quick look once you run it locally to confirm it reads the way
it was designed to.

## A natural next step, not built here
A real `POST /index` endpoint wrapping the Phase 1-2 ingestion
pipeline as a background task, so the sidebar's repo URL field could
actually trigger indexing instead of just labeling citation links.
Would need progress polling (ingestion/embedding takes time) — the
sidebar's index-status panel is already structured to make this a
fairly small addition later.
