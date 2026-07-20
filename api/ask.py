"""
Phase 3 milestone script.

Usage:
    python ask.py "where is auth handled"

Runs the full pipeline directly from the terminal — no server needed —
so you can prove end-to-end RAG works before wiring up FastAPI/frontend.
"""

import argparse

from rag_pipeline import answer_question


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question", help="Question about the indexed codebase")
    parser.add_argument("--top-k", type=int, default=6)
    args = parser.parse_args()

    print(f"Question: {args.question}\n")
    print("Retrieving relevant code and generating answer...\n")

    result = answer_question(args.question, top_k=args.top_k)

    print("--- Answer ---")
    print(result.answer)

    print(f"\n--- Retrieved {result.retrieved_chunk_count} chunks ---")
    for c in result.citations:
        print(f"  {c.as_string()}  [{c.name or 'unnamed'}]")


if __name__ == "__main__":
    main()
