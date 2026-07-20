"""
Thin wrapper around the Groq client. Keeps the prompt/response
handling in one place so rag_pipeline.py doesn't need to know
anything about the Groq SDK directly.
"""

from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL

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


def get_client() -> Groq:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key "
            "(get one free at https://console.groq.com/keys)."
        )
    return Groq(api_key=GROQ_API_KEY)


def generate_answer(question: str, context: str) -> str:
    """
    Sends the question + retrieved context to Groq and returns the
    model's answer text.
    """
    client = get_client()

    user_prompt = f"""Code context:
{context}

Question: {question}

Answer the question using only the code context above, with citations."""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,  # low temperature: we want grounded, consistent answers
        max_tokens=1024,
    )
    return response.choices[0].message.content
