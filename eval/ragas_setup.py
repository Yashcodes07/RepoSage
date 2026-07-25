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

from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import Faithfulness, AnswerRelevancy, LLMContextPrecisionWithReference
from langchain_core.embeddings import Embeddings
from chromadb.utils import embedding_functions

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "api"))
sys.path.insert(0, str(_PROJECT_ROOT / "indexing"))

from config import GROQ_API_KEY, GROQ_MODEL  # noqa: E402  (from api/config.py)

GROQ_OPENAI_COMPATIBLE_BASE_URL = "https://api.groq.com/openai/v1"


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
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env in api/ "
            "and add your key (this eval harness reuses api/'s config)."
        )
    client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url=GROQ_OPENAI_COMPATIBLE_BASE_URL)
    return llm_factory(GROQ_MODEL, client=client)


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
        AnswerRelevancy(llm=llm, embeddings=embeddings),
        LLMContextPrecisionWithReference(llm=llm),
    ]