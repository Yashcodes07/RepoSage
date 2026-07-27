"""
Wires up the LLM and embeddings RAGAS needs to judge answers, reusing
what's already in this project instead of adding new dependencies.

LLM (judge model): Groq exposes an OpenAI-compatible endpoint
(https://api.groq.com/openai/v1), so we point RAGAS's llm_factory —
its current recommended pattern — at Groq directly via the `openai`
client library. No langchain-groq needed, and it reuses the same
GROQ_API_KEY already set up in api/.env from Phase 3.

Embeddings: RAGAS's AnswerRelevancy metric needs an embedding model.
Groq doesn't serve embeddings (it's LLM-inference only), and pulling
in sentence-transformers/torch just for this would repeat the Phase 5
dependency problem for a single metric. Instead this wraps ChromaDB's
own ONNXMiniLM_L6_V2 embedding function (already used in indexing/
vector_index.py, works without torch) as a LangChain-compatible
Embeddings class, so RAGAS can use it directly.
"""

import sys
from pathlib import Path

from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import Faithfulness, AnswerRelevancy, LLMContextPrecisionWithReference
from langchain_groq import ChatGroq
from langchain_core.embeddings import Embeddings
from chromadb.utils import embedding_functions

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "api"))
sys.path.insert(0, str(_PROJECT_ROOT / "indexing"))

from config import GROQ_API_KEY  # noqa: E402  (from api/config.py)

# Deliberately NOT reusing api/config.py's GROQ_MODEL (openai/gpt-oss-120b)
# for the judge LLM. That model's daily quota (200K tokens/day on Groq's
# free tier) gets exhausted fast once you add RAGAS's own judge calls on
# top of normal generation — confirmed directly from a real 429 error:
# "tokens per day (TPD): Limit 200000, Used 197946". Waiting doesn't
# meaningfully help since it's a DAILY cap, not a per-minute one.
#
# llama-3.1-8b-instant's TPM cap (6000) turned out too small for some
# single requests here — code-heavy context can genuinely exceed 6000
# tokens in one call, which is a hard per-request ceiling no retry can
# fix. llama-3.3-70b-versatile has double the TPM headroom (12,000) and
# also has its own separate, untouched daily quota.
JUDGE_MODEL = "llama-3.3-70b-versatile"


class ChromaONNXEmbeddings(Embeddings):
    """
    Adapts ChromaDB's ONNXMiniLM_L6_V2 embedding function (a simple
    __call__(list[str]) -> list[list[float]] interface) to LangChain's
    Embeddings interface (embed_documents / embed_query), which is what
    RAGAS's LangchainEmbeddingsWrapper expects.
    """

    def __init__(self):
        self._fn = embedding_functions.ONNXMiniLM_L6_V2()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._fn(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._fn([text])[0]


def get_ragas_llm():
    """
    Uses LangchainLLMWrapper(ChatGroq(...)), NOT ragas's newer
    llm_factory() — despite llm_factory being the currently-recommended
    pattern (and LangchainLLMWrapper being flagged as deprecated).

    Real, confirmed bug in ragas==0.3.9: its classic metrics
    (Faithfulness, AnswerRelevancy, LLMContextPrecisionWithReference)
    decide how to call the LLM using an `is_langchain_llm()` check —
    `hasattr(llm, "agenerate") and not hasattr(llm, "run_config")`.
    llm_factory()'s InstructorLLM has its own `agenerate` method but no
    `run_config`, so it gets MISCLASSIFIED as a LangChain LLM, and ragas
    then calls `.agenerate_prompt()` on it — a method InstructorLLM
    doesn't have — crashing with
    `AttributeError('InstructorLLM' object has no attribute
    'agenerate_prompt')` on every single metric call.

    LangchainLLMWrapper has `run_config`, so it's correctly NOT
    misclassified, and routes to the working code path instead. If a
    future ragas release fixes this detection bug, llm_factory would
    be the better long-term choice — check before switching back.
    """
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env in api/ "
            "and add your key (this eval harness reuses api/'s config)."
        )
    chat = ChatGroq(model=JUDGE_MODEL, groq_api_key=GROQ_API_KEY, max_tokens=2048)
    return LangchainLLMWrapper(chat)


def get_ragas_embeddings():
    return LangchainEmbeddingsWrapper(ChromaONNXEmbeddings())


def get_metrics():
    """
    Returns the 3 metrics used for evaluation, each wired to the same
    judge LLM (and embeddings, where needed).

    - Faithfulness: does the answer only contain claims supported by
      the retrieved context? (llm only)
    - AnswerRelevancy: does the answer actually address the question,
      not just recite context? (llm + embeddings)
    - LLMContextPrecisionWithReference: are the relevant chunks ranked
      near the top of what was retrieved? Uses the `reference` field
      in eval_dataset.json as ground truth. (llm only)
    """
    llm = get_ragas_llm()
    embeddings = get_ragas_embeddings()
    return [
        Faithfulness(llm=llm),
        # strictness=1, not the default 3: AnswerRelevancy normally asks
        # the LLM to generate 3 candidate questions in ONE call (n=3) to
        # average for a more robust score. Groq's API rejects n>1
        # outright ("'n': number must be at most 1"), so this trades a
        # bit of score robustness for actually being able to run at all
        # against Groq. Revisit if Groq adds n>1 support, or if you
        # switch judge providers.
        AnswerRelevancy(llm=llm, embeddings=embeddings, strictness=1),
        LLMContextPrecisionWithReference(llm=llm),
    ]