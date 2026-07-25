# Phase 2: Indexing

## What this does
Takes the `chunks.json` produced by Phase 1 and builds two parallel,
independent indexes over the same chunks:

1. **Vector index** (`vector_index.py`) — embeds each chunk and stores
   it in ChromaDB (persisted locally, no hosted vector DB cost).
2. **Keyword index** (`keyword_index.py`) — builds a BM25 index over
   the same chunks, with identifier-aware tokenization (splits
   `camelCase` / `snake_case` so partial-name queries still match).

At this phase the two retrievers are queried **separately** —
no fusion or reranking yet (that's Phase 4/5). The goal here is just
to prove both retrievers return sensible results independently.

## A note on the embedding model
`vector_index.py` uses ChromaDB's built-in `ONNXMiniLM_L6_V2` embedding
function rather than `sentence-transformers` + `torch`. Same MiniLM
model family, but ~90MB instead of a multi-GB torch install — this
matters because the free-tier deploy targets (Render 512MB, Railway
free tier) can't comfortably fit torch. It downloads its ONNX weights
on first use.

## Setup
```bash
pip install -r requirements.txt
```

## Run
```bash
# 1. Build both indexes from Phase 1's output
python build_index.py --chunks ../ingestion/chunks.json

# 2. Query both retrievers separately and compare
python query_index.py "where is auth handled"
python query_index.py "hybrid search retry logic"
```

## Verified milestone (run on QueDB's 282 chunks from Phase 1)
- **BM25 keyword index**: built instantly, no network dependency.
  Query `"hybrid search retry"` correctly surfaced `hybrid_ask`,
  `run_hybrid_query`, and `handleHybrid` as the top results — exact
  identifier matching working as intended.
- **Vector index (ChromaDB)**: upsert/query wiring verified correct
  (IDs, metadata, retrieval all confirmed working). Note: the actual
  ONNX model download was blocked in this sandboxed dev environment,
  which only allows a fixed list of domains (pypi, npm, github) and
  not Chroma's model host — this is a sandbox restriction, not a code
  issue. It will download normally on your own machine or deployment.

## Next: Phase 4 (Phase 3 wires this into a basic FastAPI + LLM endpoint first)
Fuse the two result sets with Reciprocal Rank Fusion, so identifier
matches (BM25) and conceptual matches (embeddings) both contribute to
the final ranking.

---

## Phase 5: Reranking

Adds a cross-encoder on top of Phase 4's fusion, narrowing a wide
candidate pool (15) down to the final top-N (6) actually sent to the LLM.

### Files
- `reranker.py` — wraps `cross-encoder/ms-marco-MiniLM-L-6-v2` (via
  `sentence-transformers`), re-scoring each fused candidate by reading
  the query and chunk together in one forward pass
- `compare_reranking.py` — milestone CLI: fused ranking vs reranked
  ranking, side by side, showing exactly what got dropped/promoted

### Why a cross-encoder, and why this specific model
Vector search and BM25 both score a query against a chunk *without
ever looking at them together* — vector search compares two
independently-computed embeddings, BM25 counts token overlap. A
cross-encoder reads the query and chunk **together** and outputs one
relevance score, which is meaningfully more accurate — but expensive,
so it only runs on a small candidate pool from fusion, not the whole
index. `ms-marco-MiniLM-L-6-v2` was chosen over the originally-planned
`bge-reranker-base` for size (~80MB vs ~1.1GB) — both need
`sentence-transformers` + `torch` either way, so this was about
keeping the *model* itself as light as possible, not avoiding torch.

### Important — deployment cost of this phase
This is the heaviest dependency added in the whole project.
`sentence-transformers` requires `torch`, and a default `pip install
torch` pulls several GB of CUDA packages even for CPU-only use — this
filled a 9GB-free sandbox during development. On your own machine this
just costs disk space and install time, but **it will very likely not
fit on Render/Railway free tier** (512MB RAM), unlike everything in
Phases 1-4.

Two ways to handle this for deployment:
1. **Toggle it off** — `api/config.py` reads `RERANK_ENABLED` from
   `.env`. Set `RERANK_ENABLED=false` to skip reranking entirely and
   fall back to fusion's own ranking — no torch import happens at all
   in that path (verified: see api/README.md).
2. **Swap for an API-based reranker** — e.g. Cohere's rerank API has a
   free tier and needs no local model/torch at all. Would mean
   replacing `_get_model()`/`rerank()` internals in `reranker.py` but
   keeping the same `RerankedResult` interface.

### Verified in this environment
- `torch` install reproducibly consumes multiple GB and can exhaust
  disk even with 9GB free — confirmed firsthand, not a hypothetical
- `rerank()` wiring verified correct with a mocked cross-encoder:
  correctly sorts by score, correctly truncates to `top_n`, correctly
  drops a low-scoring noise chunk (simulating the real
  `get_connections` false-positive from Phase 4's actual test run)
- Both `RERANK_ENABLED=true` and `=false` code paths tested — the
  `false` path confirmed to avoid importing `reranker.py`/torch at all
- **Not tested here**: actual `ms-marco-MiniLM-L-6-v2` inference,
  since the model + torch couldn't be installed in this sandbox. Run
  `compare_reranking.py` on your machine to see real scores.

### Next: Phase 6 (agentic layer with LangGraph) or Phase 7 (eval harness)

---

## Known issue found during real testing: reranking evaluated and disabled by default

**TL;DR: tested across 3 real queries on this codebase; reranking never
beat Phase 4's fusion, and actively hurt results on the 2 genuinely
semantic queries. `RERANK_ENABLED` now defaults to `false`.**

### The evaluation

| Query | Fusion alone | With reranking | Verdict |
|---|---|---|---|
| "where is auth handled" | `login` (real implementation) ranked #1 | `login` demoted to #5, below two frontend callers matching on a literal `/auth/login` string | Reranking worse |
| "what happens when a query fails" | `run_nl_query` (actual error/retry handling) ranked #2 | Demoted to #5, replaced by 3 functions whose only qualification is containing the literal word "query" in their name | Reranking worse |
| "get_current_user function" | `get_current_user` ranked #1 (near-exact identifier match) | Still #1 | No change — fusion already had this right |

Zero out of three queries got better with reranking. The two where it
actively hurt were exactly the queries that require real semantic
understanding rather than keyword overlap — precisely the case
reranking is supposed to help with most.

### Root cause
`cross-encoder/ms-marco-MiniLM-L-6-v2` is trained on MS MARCO — real
Bing search queries paired with natural-language web passages, never
code. An early fix (feeding the model `file_path + name + code`
instead of bare code) measurably helped in isolation — it pulled
`login` back into the top 6 for the auth query, from being dropped
entirely. But in the full pipeline, that same fix backfired on other
queries: this codebase's file/function names repeat common domain
words (`query`, `auth`, `user`) constantly, so adding file paths gave
the model more surface area to shallow-match on literal tokens instead
of understanding what the code actually does. The model consistently
favors literal lexical overlap over which chunk is *actually* the
right answer — expected behavior for a passage-search model, but
actively counterproductive here.

### Decision
`api/config.py` and `api/.env.example` now default `RERANK_ENABLED` to
`false`. `reranker.py` and `compare_reranking.py` are still fully
implemented and usable (`RERANK_ENABLED=true` in `.env`) — this isn't
deleted code, it's a deliberately-off feature with the evaluation data
to justify the call. `diagnose_reranker.py` remains for anyone who
wants to test a different reranker model against this same methodology.

### For the interview
This is arguably a stronger story than "I added reranking and it
worked" — implementing a technique, testing it rigorously with a
before/after methodology across multiple query types, finding it
doesn't hold up, diagnosing *why* using the model's own documented
training data, and making a evidence-based decision not to ship it —
is closer to real production ML engineering than blindly following a
tutorial's phase list.

### A better long-term fix, if revisited
A code-aware reranker (e.g. one fine-tuned on CodeSearchNet-style
query-code pairs) or an API-based option like Cohere rerank would
likely transfer better than a pure prose-search model. Not implemented
here — flagging as a real next step, not pretending this is solved.