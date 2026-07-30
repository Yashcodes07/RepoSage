"""
Phase 7 milestone script.

Usage:
    python run_eval.py
    python run_eval.py --out results_fusion_only.json
    python run_eval.py --resume    # skip questions already in the checkpoint file

Runs every question in eval_dataset.json through the actual RAG
pipeline (api/rag_pipeline.py — whatever RERANK_ENABLED is currently
set to in api/.env), collects the real retrieved context + generated
answer for each, then scores the whole set with RAGAS.

This measures the SYSTEM AS IT ACTUALLY RUNS, not a mocked version —
if RERANK_ENABLED=true, you're evaluating fusion+rerank; if false,
you're evaluating fusion alone. Run it twice (flipping the env var
between runs, or use compare_configs.py to automate that) to get a
real quantified before/after instead of the qualitative comparison
from Phase 5.

Checkpointing: each question's result is saved to a checkpoint file as
soon as it's computed, not just at the end. If a run crashes partway
(e.g. hits Groq's per-minute rate limit — real free-tier constraint,
not a bug), re-run with --resume to pick up where it left off instead
of re-spending API quota re-answering questions you already have.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from ragas import evaluate, EvaluationDataset, SingleTurnSample
from ragas.run_config import RunConfig

from ragas_setup import get_metrics

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "api"))

from rag_pipeline import answer_question  # noqa: E402
from config import RERANK_ENABLED  # noqa: E402

# Seconds to wait between questions, on top of llm.py's own rate-limit
# retry logic — an extra safety margin against Groq's per-minute token
# cap when running the full 15-question set back to back.
INTER_QUESTION_SLEEP_SECONDS = 3

# RAGAS defaults to max_workers=16 for its own internal judge-LLM calls
# (faithfulness/context_precision each make several sub-calls per
# question). Even at max_workers=2, concurrent judge calls were
# compounding against each other's TPM usage within the same 60s
# window (confirmed: hit a real 429 with "Used 10920, Requested 2748"
# against a 12000 cap — two jobs eating the same budget at once).
# Fully sequential (1) is slower but keeps usage predictable.
RAGAS_MAX_WORKERS = 1

# RAGAS's own defaults (max_retries=10, max_wait=60) are meant for
# transient errors like rate limits, but they also apply to
# DETERMINISTIC failures (a malformed request that will never
# succeed) — meaning a single bad job could burn up to 10 retries x
# 60s = 10 minutes before giving up. Tightened here since the known
# deterministic failures (AnswerRelevancy's n>1 issue, oversized
# requests) are already fixed at the source. These numbers are now
# tuned for genuinely transient TPM waits specifically, which have
# consistently been short (8-20s) in testing — 5 retries x 45s gives
# generous room to clear one without waiting forever on a lost cause.
RAGAS_MAX_RETRIES = 5
RAGAS_MAX_WAIT_SECONDS = 45

# RAGAS's own executor has no built-in control over TOTAL call rate —
# only concurrency (max_workers) and per-job retry/backoff. Even fully
# sequential (max_workers=1), jobs fire back-to-back with no pacing,
# and each question's 3 metrics can total many large sub-calls —
# confirmed: hit 429s within the first 3-4 jobs even sequentially.
# Batching the evaluate() call itself, with a real sleep between
# batches, is the only way to guarantee the TPM window actually clears
# between groups of calls.
SCORING_BATCH_SIZE = 2
SCORING_BATCH_SLEEP_SECONDS = 60

# Some retrieved chunks are large (60-120+ line classes/components), and
# up to 6 get concatenated per question — this can exceed a judge
# model's per-request TPM ceiling in a single call (confirmed: hit a
# real 413 "request too large" error). Beyond raw size, some RAGAS
# metrics (context precision) make roughly one internal sub-call PER
# retrieved chunk — so 6 chunks isn't just "more text," it's several
# more expensive API calls per question. Capping both size AND count
# directly reduces call volume, not just per-call size.
MAX_CONTEXT_CHARS_PER_CHUNK = 600
MAX_CONTEXTS_PER_SAMPLE = 3


def truncate_for_scoring(samples: list[SingleTurnSample]) -> list[SingleTurnSample]:
    truncated = []
    for s in samples:
        contexts = s.retrieved_contexts[:MAX_CONTEXTS_PER_SAMPLE]
        contexts = [
            c if len(c) <= MAX_CONTEXT_CHARS_PER_CHUNK
            else c[:MAX_CONTEXT_CHARS_PER_CHUNK] + "\n... (truncated for judge LLM context limits)"
            for c in contexts
        ]
        truncated.append(
            SingleTurnSample(
                user_input=s.user_input,
                response=s.response,
                retrieved_contexts=contexts,
                reference=s.reference,
            )
        )
    return truncated


def load_eval_dataset(path: str) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_checkpoint(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_checkpoint(path: Path, checkpoint: dict) -> None:
    path.write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")


def sample_to_dict(qa_id: str, sample: SingleTurnSample) -> dict:
    return {
        "id": qa_id,
        "user_input": sample.user_input,
        "response": sample.response,
        "retrieved_contexts": sample.retrieved_contexts,
        "reference": sample.reference,
    }


def dict_to_sample(d: dict) -> SingleTurnSample:
    return SingleTurnSample(
        user_input=d["user_input"],
        response=d["response"],
        retrieved_contexts=d["retrieved_contexts"],
        reference=d["reference"],
    )


def run_pipeline_over_dataset(
    qa_pairs: list[dict], checkpoint_path: Path, resume: bool
) -> list[SingleTurnSample]:
    checkpoint = load_checkpoint(checkpoint_path) if resume else {}
    if checkpoint:
        print(f"Resuming: {len(checkpoint)} question(s) already in checkpoint, skipping those.\n")

    samples_by_id = {}
    for i, qa in enumerate(qa_pairs, 1):
        qa_id = qa["id"]
        if qa_id in checkpoint:
            print(f"[{i}/{len(qa_pairs)}] {qa['question']!r} — skipped (already in checkpoint)")
            samples_by_id[qa_id] = dict_to_sample(checkpoint[qa_id])
            continue

        print(f"[{i}/{len(qa_pairs)}] {qa['question']!r}")
        result = answer_question(qa["question"])
        # Use the REAL retrieved code as context, not just the citation
        # label — RAGAS's faithfulness metric checks whether the
        # answer's claims are actually supported by this text, so it
        # needs the real content, not "file.py:20-27 [login]".
        retrieved_texts = [
            f"{c.file_path}:{c.start_line}-{c.end_line} [{c.name}]\n{c.code}"
            for c in result.citations
        ]
        sample = SingleTurnSample(
            user_input=qa["question"],
            response=result.answer,
            retrieved_contexts=retrieved_texts or ["(no context retrieved)"],
            reference=qa["reference"],
        )
        samples_by_id[qa_id] = sample

        # Save progress immediately — don't wait until all 15 are done.
        checkpoint[qa_id] = sample_to_dict(qa_id, sample)
        save_checkpoint(checkpoint_path, checkpoint)

        if i < len(qa_pairs):
            time.sleep(INTER_QUESTION_SLEEP_SECONDS)

    # Return in original dataset order
    return [samples_by_id[qa["id"]] for qa in qa_pairs]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="eval_dataset.json")
    parser.add_argument("--out", default="results.json")
    parser.add_argument("--resume", action="store_true",
                         help="Skip questions already answered in the checkpoint file")
    args = parser.parse_args()

    print(f"RERANK_ENABLED = {RERANK_ENABLED}\n")

    qa_pairs = load_eval_dataset(args.dataset)
    checkpoint_path = Path(args.out).with_suffix(".checkpoint.json")

    print(f"Running RAG pipeline over {len(qa_pairs)} questions...\n")
    samples = run_pipeline_over_dataset(qa_pairs, checkpoint_path, args.resume)
    # Truncate/cap here, not in run_pipeline_over_dataset/checkpoint —
    # the checkpoint keeps full untruncated data; only the copy sent to
    # RAGAS for scoring is size-capped, to fit judge model TPM limits.
    scoring_samples = truncate_for_scoring(samples)

    print("\nScoring with RAGAS (faithfulness, answer_relevancy, context_precision)...")
    metrics = get_metrics()
    run_config = RunConfig(
        max_workers=RAGAS_MAX_WORKERS,
        max_retries=RAGAS_MAX_RETRIES,
        max_wait=RAGAS_MAX_WAIT_SECONDS,
    )

    scores_checkpoint_path = Path(args.out).with_suffix(".scores_checkpoint.json")
    scores_checkpoint = load_checkpoint(scores_checkpoint_path) if args.resume else {}
    if scores_checkpoint:
        print(f"Resuming scoring: {len(scores_checkpoint)} question(s) already scored, skipping.\n")

    all_records = []
    batches = [
        scoring_samples[i:i + SCORING_BATCH_SIZE]
        for i in range(0, len(scoring_samples), SCORING_BATCH_SIZE)
    ]
    for batch_num, batch in enumerate(batches, 1):
        # Skip any batch whose questions are ALL already scored
        unscored = [s for s in batch if s.user_input not in scores_checkpoint]
        if not unscored:
            print(f"[batch {batch_num}/{len(batches)}] already scored, skipping")
            continue

        print(f"[batch {batch_num}/{len(batches)}] scoring {len(unscored)} question(s)...")
        batch_dataset = EvaluationDataset(samples=unscored)
        result = evaluate(dataset=batch_dataset, metrics=metrics, run_config=run_config)
        batch_records = result.to_pandas().to_dict(orient="records")

        for rec in batch_records:
            scores_checkpoint[rec["user_input"]] = rec
        save_checkpoint(scores_checkpoint_path, scores_checkpoint)

        if batch_num < len(batches):
            print(f"  waiting {SCORING_BATCH_SLEEP_SECONDS}s before next batch "
                  f"(lets the judge model's per-minute quota clear)...")
            time.sleep(SCORING_BATCH_SLEEP_SECONDS)

    # Assemble final results in original question order
    for s in scoring_samples:
        if s.user_input in scores_checkpoint:
            all_records.append(scores_checkpoint[s.user_input])

    metric_cols = ["faithfulness", "answer_relevancy", "llm_context_precision_with_reference"]
    print("\n=== Per-question scores ===")
    for rec in all_records:
        scores_str = "  ".join(f"{c}={rec.get(c, float('nan')):.3f}" for c in metric_cols)
        print(f"  {rec['user_input'][:60]:<60}  {scores_str}")

    print("\n=== Aggregate scores ===")
    for col in metric_cols:
        vals = [rec[col] for rec in all_records if rec.get(col) is not None]
        avg = sum(vals) / len(vals) if vals else float("nan")
        print(f"  {col}: {avg:.3f}  (n={len(vals)}/{len(all_records)})")

    out_path = Path(args.out)
    out_path.write_text(json.dumps(all_records, indent=2), encoding="utf-8")
    print(f"\nSaved full results to {out_path.resolve()}")
    print(f"(Checkpoints left in place: {checkpoint_path.name}, {scores_checkpoint_path.name} "
          f"— safe to delete once you're happy with the results.)")


if __name__ == "__main__":
    main()