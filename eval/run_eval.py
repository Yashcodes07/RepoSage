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
# question). At 16 concurrent requests, this alone can burst past a
# free-tier per-minute token cap almost immediately. Lower concurrency
# = slower but actually completes instead of crashing.
RAGAS_MAX_WORKERS = 2


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
    dataset = EvaluationDataset(samples=samples)

    print("\nScoring with RAGAS (faithfulness, answer_relevancy, context_precision)...")
    metrics = get_metrics()
    # max_workers=2 (not RAGAS's default of 16) — avoids bursting past
    # Groq's free-tier per-minute token cap with concurrent judge calls.
    run_config = RunConfig(max_workers=RAGAS_MAX_WORKERS)
    result = evaluate(dataset=dataset, metrics=metrics, run_config=run_config)

    df = result.to_pandas()
    print("\n=== Per-question scores ===")
    print(df[["user_input", "faithfulness", "answer_relevancy", "llm_context_precision_with_reference"]]
          .to_string(index=False))

    print("\n=== Aggregate scores ===")
    for col in ["faithfulness", "answer_relevancy", "llm_context_precision_with_reference"]:
        print(f"  {col}: {df[col].mean():.3f}")

    out_path = Path(args.out)
    df.to_json(out_path, orient="records", indent=2)
    print(f"\nSaved full results to {out_path.resolve()}")
    print(f"(Checkpoint file {checkpoint_path.name} left in place — safe to delete once you're happy with the results.)")


if __name__ == "__main__":
    main()
