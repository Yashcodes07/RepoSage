"""
Phase 7 milestone script.

Usage:
    python run_eval.py
    python run_eval.py --out results_fusion_only.json

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
"""

import argparse
import json
import sys
from pathlib import Path

from ragas import evaluate, EvaluationDataset, SingleTurnSample

from ragas_setup import get_metrics

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "api"))

from rag_pipeline import answer_question  # noqa: E402
from config import RERANK_ENABLED  # noqa: E402


def load_eval_dataset(path: str) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_pipeline_over_dataset(qa_pairs: list[dict]) -> list[SingleTurnSample]:
    samples = []
    for i, qa in enumerate(qa_pairs, 1):
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
        samples.append(
            SingleTurnSample(
                user_input=qa["question"],
                response=result.answer,
                retrieved_contexts=retrieved_texts or ["(no context retrieved)"],
                reference=qa["reference"],
            )
        )
    return samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="eval_dataset.json")
    parser.add_argument("--out", default="results.json")
    args = parser.parse_args()

    print(f"RERANK_ENABLED = {RERANK_ENABLED}\n")

    qa_pairs = load_eval_dataset(args.dataset)
    print(f"Running RAG pipeline over {len(qa_pairs)} questions...\n")
    samples = run_pipeline_over_dataset(qa_pairs)
    dataset = EvaluationDataset(samples=samples)

    print("\nScoring with RAGAS (faithfulness, answer_relevancy, context_precision)...")
    metrics = get_metrics()
    result = evaluate(dataset=dataset, metrics=metrics)

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


if __name__ == "__main__":
    main()