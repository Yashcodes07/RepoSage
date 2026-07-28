"""
Phase 6 milestone script.

Usage:
    python ask_agentic.py "how does the retry loop interact with the schema explorer"

Same as ask.py, but routes through the LangGraph agent — shows which
route was chosen (simple/multi_hop/clarify) and, for multi-hop
questions, the sub-questions it decomposed into.
"""

import argparse

from agent import run_agentic_query


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    args = parser.parse_args()

    print(f"Question: {args.question}\n")
    result = run_agentic_query(args.question)

    print(f"--- Route: {result.route} ---")
    if result.sub_questions:
        print("Sub-questions:")
        for sq in result.sub_questions:
            print(f"  - {sq}")
        print()

    print("--- Answer ---")
    print(result.answer)

    if not result.needs_clarification:
        print(f"\n--- Retrieved {result.retrieved_chunk_count} chunks ---")
        for c in result.citations:
            print(f"  {c.as_string()}  [{c.name or 'unnamed'}]")


if __name__ == "__main__":
    main()