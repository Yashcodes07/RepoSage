"""
Thin wrapper around the Groq client. Keeps the prompt/response
handling in one place so rag_pipeline.py doesn't need to know
anything about the Groq SDK directly.
"""

import time

from groq import Groq, RateLimitError

from .config import GROQ_API_KEY, GROQ_MODEL

SYSTEM_PROMPT = """You are a code assistant answering questions about a specific \
codebase. You will be given retrieved code chunks, each labeled with its exact \
file path and line range.

Rules:
- Answer ONLY using the provided code chunks. Do not invent code, functions, \
or behavior that isn't shown.
- Every factual claim about the code MUST be followed by a citation in the \
exact format (file_path:start_line-end_line).
- If the provided chunks don't contain enough information to answer, say so \
plainly instead of guessing.
- Be concise and technical — the reader is a developer, not a beginner.
"""

# Free-tier Groq limits are per-minute (tokens per minute, not just
# requests per minute). A single 429 can mean "the whole rolling window
# is full" — retrying instantly just fails again. These backoff times
# are deliberately generous (not the SDK's default sub-second backoff)
# to actually clear a per-minute window rather than burn through retries.
MAX_RATE_LIMIT_RETRIES = 5
BACKOFF_SECONDS = [10, 20, 40, 60, 60]  # one entry per retry attempt


def get_client() -> Groq:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key "
            "(get one free at https://console.groq.com/keys)."
        )
    # max_retries=0 here because we handle RateLimitError ourselves below
    # with longer, minute-aware backoff — the SDK's own default backoff
    # is sub-second and not long enough to clear a per-minute TPM cap.
    return Groq(api_key=GROQ_API_KEY, max_retries=0)


def generate_answer(question: str, context: str) -> str:
    """
    Sends the question + retrieved context to Groq and returns the
    model's answer text. Retries on rate-limit errors with backoff long
    enough to actually clear Groq's per-minute token window, instead of
    crashing mid-run (important for eval/run_eval.py, which makes many
    calls back-to-back).
    """
    client = get_client()

    user_prompt = f"""Code context:
{context}

Question: {question}

Answer the question using only the code context above, with citations."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    last_error = None
    for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.1,  # low temperature: we want grounded, consistent answers
                max_tokens=1024,
            )
            return response.choices[0].message.content
        except RateLimitError as e:
            last_error = e
            if attempt >= MAX_RATE_LIMIT_RETRIES:
                break
            wait = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
            print(f"  [rate limit] hit, waiting {wait}s before retry "
                  f"({attempt + 1}/{MAX_RATE_LIMIT_RETRIES})...")
            time.sleep(wait)

    raise last_error