"""
Runs run_eval.py twice — once with RERANK_ENABLED=false, once with
RERANK_ENABLED=true — and prints the aggregate scores side by side.

This is the quantified version of Phase 5's manual before/after
comparison: instead of eyeballing 3 example queries, this scores all
15 eval questions with RAGAS under both configurations.

Usage:
    python compare_configs.py

Note: this makes 2x as many Groq API calls as a single run_eval.py
run (15 questions x 2 configs, each needing a generation call plus
several RAGAS judge calls) — expect it to take a few minutes and use
a meaningful chunk of your Groq free-tier quota.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

CONFIGS = [
    ("fusion_only", "false", "results_fusion_only.json"),
    ("fusion_plus_rerank", "true", "results_fusion_rerank.json"),
]


def run_config(rerank_enabled: str, out_file: str) -> None:
    env = {"RERANK_ENABLED": rerank_enabled}
    print(f"\n{'='*60}\nRunning with RERANK_ENABLED={rerank_enabled}\n{'='*60}")
    result = subprocess.run(
        [sys.executable, "run_eval.py", "--out", out_file],
        env={**os.environ, **env},
    )
    if result.returncode != 0:
        print(f"WARNING: run_eval.py exited with code {result.returncode} for RERANK_ENABLED={rerank_enabled}")


def load_aggregate(path: str) -> dict:
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    metrics = ["faithfulness", "answer_relevancy", "llm_context_precision_with_reference"]
    return {
        m: sum(r[m] for r in records) / len(records)
        for m in metrics
    }


def main():
    for label, rerank_enabled, out_file in CONFIGS:
        run_config(rerank_enabled, out_file)

    print(f"\n{'='*60}\nCOMPARISON\n{'='*60}")
    aggregates = {}
    for label, _, out_file in CONFIGS:
        if Path(out_file).exists():
            aggregates[label] = load_aggregate(out_file)

    metrics = ["faithfulness", "answer_relevancy", "llm_context_precision_with_reference"]
    header = f"{'metric':<40}" + "".join(f"{label:>20}" for label, _, _ in CONFIGS)
    print(header)
    for m in metrics:
        row = f"{m:<40}"
        for label, _, _ in CONFIGS:
            val = aggregates.get(label, {}).get(m)
            row += f"{val:>20.3f}" if val is not None else f"{'N/A':>20}"
        print(row)


if __name__ == "__main__":
    main()