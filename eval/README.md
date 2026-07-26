# Phase 7: Evaluation Harness (RAGAS)

## What this does
Runs 15 hand-labeled questions through the real, live RAG pipeline
(`api/rag_pipeline.py` — whatever your current `RERANK_ENABLED`
setting is) and scores the results with RAGAS across three metrics:

- **Faithfulness** — does the answer only contain claims actually
  supported by the retrieved code? (catches hallucination)
- **Answer Relevancy** — does the answer actually address the
  question asked, not just recite nearby context?
- **Context Precision** — are the truly relevant chunks ranked near
  the top of what was retrieved, compared against a hand-written
  reference answer?

This is what turns "I built a RAG system" into "I measured my RAG
system" — a real, defensible metrics table instead of a claim.

## Files
- `eval_dataset.json` — 15 hand-labeled QA pairs grounded in actual
  QueDB code (auth flow, hybrid search, SQL agent, connections, error
  handling), each with a written reference answer
- `ragas_setup.py` — wires up the judge LLM and embeddings RAGAS
  needs (see "Dependency choices" below for why these specific ones)
- `run_eval.py` — runs the dataset through the live pipeline, scores
  it, prints per-question and aggregate results, saves to JSON
- `compare_configs.py` — runs the full eval twice (RERANK_ENABLED
  true vs false) and prints a quantified before/after table — the
  measured version of Phase 5's manual query-by-query comparison

## Setup
```bash
pip install -r requirements.txt
```
Reuses `api/`'s `.env` — make sure `GROQ_API_KEY` is already set there
(no new API key needed for the judge LLM).

## Run
```bash
python run_eval.py
```
Or to quantify the Phase 5 reranking decision properly:
```bash
python compare_configs.py
```
Note: this doubles the number of Groq calls (15 questions × 2 configs,
each needing a generation call + several RAGAS judge calls) — expect
a few minutes and a real chunk of your Groq free-tier quota.

## Dependency choices, and why

**Pinned versions matter here.** `ragas` (both the latest 0.4.x and
0.3.9) has a real upstream bug: it eagerly imports
`langchain_community.chat_models.vertexai` at module load time, but
current `langchain-community` (0.4.x) has removed that submodule as
part of sunsetting the package. This isn't a local environment issue —
it reproduces in a completely clean virtual environment. The fix is
pinning `langchain-community==0.3.19` (a version that still has the
submodule) alongside `ragas==0.3.9`. If a future `ragas` release fixes
this, the pin can be relaxed — check before assuming it's still needed.

**LLM (judge model): Groq via its OpenAI-compatible endpoint**
(`https://api.groq.com/openai/v1`), using RAGAS's current recommended
`llm_factory` pattern with a plain `openai` client rather than the
older `LangchainLLMWrapper` (deprecated, though still functional).
This reuses the exact same `GROQ_API_KEY` already configured in
`api/.env` — no second API key, no new provider account.

**Embeddings: reused from Phase 2, not a new dependency.**
`AnswerRelevancy` is the only metric here that needs an embedding
model, and Groq doesn't serve embeddings (it's LLM-inference only).
Rather than pulling in `sentence-transformers`/`torch` for a single
metric — repeating Phase 5's multi-GB dependency problem — this wraps
ChromaDB's own `ONNXMiniLM_L6_V2` embedding function (already used in
`indexing/vector_index.py`, no torch required) as a LangChain-
compatible `Embeddings` class.

## Verified in this environment
- Reproduced the `ragas`/`langchain-community` incompatibility from
  scratch in an isolated virtual environment (not sandbox
  contamination — a real, current packaging bug), then confirmed the
  exact pinned version combination above resolves cleanly with no
  import errors and no dependency-resolver conflicts
- All object construction verified: `llm_factory` against Groq's
  OpenAI-compatible endpoint, the `ChromaONNXEmbeddings` wrapper's
  interface, all 3 metrics constructing with `llm`/`embeddings`
  correctly wired, `SingleTurnSample`/`EvaluationDataset` construction
- `run_eval.py`'s full wiring tested end-to-end with a mocked
  `answer_question()` call: dataset loads correctly (15/15 valid
  entries), pipeline integration produces correctly-shaped
  `SingleTurnSample` objects, and — this was a real bug caught before
  shipping — confirmed retrieved context uses actual code content, not
  just citation labels (an earlier draft only passed
  `"auth.py:20-27 [login]"` to RAGAS, which would have made
  faithfulness scoring meaningless since there'd be no real content to
  check claims against)
- **Not tested here**: an actual live Groq-judged RAGAS run, since
  that needs your real `GROQ_API_KEY` and makes real API calls. Run
  `run_eval.py` on your machine to get real scores.

## Bug fixed along the way
`api/rag_pipeline.py`'s `Citation` dataclass didn't carry the actual
retrieved code — only file path, line numbers, and name. Fine for
display, but useless for evaluation: RAGAS's faithfulness metric needs
to check the answer's claims against real content, not a label. Added
a `code` field to `Citation`, populated it in `_extract_citations()`.
Backward compatible — existing callers (the FastAPI `/ask` endpoint,
`ask.py`) are unaffected since the field has a default value.

## Next: Phase 8 (frontend) or Phase 6 (agentic layer)

---

## Rate limits (real, hit during actual testing)

Groq's free tier caps tokens-per-minute per model (8000 TPM for
`openai/gpt-oss-120b` at the time of testing). Running 15 questions
through a code-heavy RAG pipeline, plus RAGAS's own judge-LLM calls on
top, can burn through that quickly — this isn't a bug, it's the real
free-tier ceiling.

Three layers of defense against it:

1. **`api/llm.py`** now retries on `RateLimitError` with real backoff
   (10s → 20s → 40s → 60s → 60s, 5 attempts) instead of crashing
   immediately. This also improves the live `/ask` endpoint, not just
   eval.
2. **RAGAS's own concurrency reduced** — `run_eval.py` passes
   `RunConfig(max_workers=2)` instead of RAGAS's default of 16. RAGAS
   makes several internal judge calls per question (faithfulness and
   context precision each call the LLM multiple times); 16 of those
   firing at once against an 8000 TPM cap is likely what actually blew
   through the limit, not just the 15 generation calls.
3. **Checkpointing** — `run_eval.py` saves each question's result to
   `<out-file>.checkpoint.json` as soon as it's computed, not just at
   the end. If a run still hits a wall partway through, re-run with
   `--resume` to skip already-completed questions instead of
   re-spending API quota re-answering them from scratch.

```bash
python run_eval.py --resume
```

If you hit rate limits repeatedly even with these in place, the
underlying fix is a paid Groq tier (link in the error message) or
switching `GROQ_MODEL` in `api/.env` to a smaller/cheaper model with a
higher free-tier TPM allowance — trading judge-model quality for
throughput.
