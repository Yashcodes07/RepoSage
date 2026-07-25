"""
Diagnostic script — run this on YOUR machine (not in a sandbox without
model access) to understand why the reranker demoted the correct
`login` chunk below noise for "where is auth handled".

Compares three things for the same known-relevant vs known-irrelevant
chunks:
    1. Bare code only (the ORIGINAL, buggy behavior)
    2. file_path + name + code (the FIX applied in reranker.py)
    3. A sanity check: does the model even rank an obviously-relevant
       vs obviously-irrelevant snippet correctly at all?

If (2) fixes the ranking -> it was a missing-context problem, the fix
in reranker.py is sufficient.

If (2) does NOT fix it, and (3) also looks wrong -> this specific
model likely doesn't transfer well to code at all, regardless of
context. In that case, the honest move is to run with
RERANK_ENABLED=false (already supported — see api/config.py) rather
than trust a reranker that's actively making things worse.

Usage:
    python diagnose_reranker.py
"""

import json

from sentence_transformers import CrossEncoder

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def main():
    print(f"Loading {MODEL_NAME}...")
    model = CrossEncoder(MODEL_NAME)

    chunks = json.load(open("../ingestion/chunks.json"))
    login = next(c for c in chunks if c["name"] == "login" and "auth.py" in c["file_path"])
    setAuth = next(c for c in chunks if c["name"] == "setAuth")
    noise = next(
        (c for c in chunks if c["name"] == "get_connections"),
        chunks[0],  # fallback if chunk names have changed since this was written
    )

    query = "where is auth handled"

    print(f"\nQuery: {query!r}")
    print(f"Known RELEVANT chunks: login, setAuth")
    print(f"Known IRRELEVANT chunk: {noise['name']}\n")

    # --- Test 1: bare code only (original behavior) ---
    pairs_bare = [(query, c["code"]) for c in (login, setAuth, noise)]
    scores_bare = model.predict(pairs_bare)
    print("--- Bare code only (ORIGINAL) ---")
    print(f"  login:    {scores_bare[0]:.4f}")
    print(f"  setAuth:  {scores_bare[1]:.4f}")
    print(f"  {noise['name']:10s}{scores_bare[2]:.4f}  <- should be LOWER than the two above")

    # --- Test 2: file_path + name + code (the fix) ---
    pairs_enriched = [
        (query, f"{c['file_path']}\n{c['name']}\n{c['code']}") for c in (login, setAuth, noise)
    ]
    scores_enriched = model.predict(pairs_enriched)
    print("\n--- file_path + name + code (FIX) ---")
    print(f"  login:    {scores_enriched[0]:.4f}")
    print(f"  setAuth:  {scores_enriched[1]:.4f}")
    print(f"  {noise['name']:10s}{scores_enriched[2]:.4f}  <- should be LOWER than the two above")

    # --- Test 3: sanity check on obviously clean text (no code at all) ---
    # If the model can't even get THIS right, it's not a code-specific
    # problem — something more fundamental is off.
    sanity_pairs = [
        ("where is auth handled", "Authentication is handled in the login function, which validates credentials and issues a JWT token."),
        ("where is auth handled", "This function retrieves a list of database connections for the current user."),
    ]
    sanity_scores = model.predict(sanity_pairs)
    print("\n--- Sanity check: plain English, not code ---")
    print(f"  relevant sentence:   {sanity_scores[0]:.4f}")
    print(f"  irrelevant sentence: {sanity_scores[1]:.4f}")
    print(f"  (if relevant > irrelevant here, the model works fine on prose —")
    print(f"   confirms the problem is specifically about CODE, not the model being broken)")

    # --- Verdict ---
    print("\n=== Verdict ===")
    fix_worked = scores_enriched[0] > scores_enriched[2] and scores_enriched[1] > scores_enriched[2]
    bare_worked = scores_bare[0] > scores_bare[2] and scores_bare[1] > scores_bare[2]
    if fix_worked and not bare_worked:
        print("Adding file_path+name FIXED the ranking. Missing context was the problem.")
        print("-> The fix already applied to reranker.py should resolve this. Rebuild and re-test.")
    elif fix_worked and bare_worked:
        print("Both versions ranked correctly here — the earlier failure may be query/chunk specific.")
        print("-> Re-run compare_reranking.py with the fix and see if the real pipeline improves.")
    else:
        print("Adding context did NOT fix the ranking.")
        print("-> This looks like a genuine domain-mismatch problem: ms-marco-MiniLM-L-6-v2 is")
        print("   trained on natural-language passages, not code, and may not transfer reliably")
        print("   here regardless of context. Recommend setting RERANK_ENABLED=false in api/.env")
        print("   and relying on Phase 4's fusion ranking, which already tested correctly.")


if __name__ == "__main__":
    main()