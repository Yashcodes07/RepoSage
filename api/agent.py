"""
Phase 6: agentic layer on top of Phase 3-5's RAG pipeline.

    question -> router (simple | multi_hop | clarify)
             -> [simple]     retrieve once -> synthesize
             -> [multi_hop]  decompose -> retrieve per sub-question -> synthesize across all
             -> [clarify]    ask a clarifying question instead of guessing

This sits ON TOP of rag_pipeline.py's retrieve_chunks() — it doesn't
duplicate retrieval logic, just orchestrates it differently depending
on question type. A single-hop question like "where is auth handled"
still goes through the same hybrid retrieval + fusion + optional
rerank as before; this only adds value for questions that genuinely
span multiple parts of the codebase (e.g. "how does the retry loop
interact with the schema explorer").
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from config import GROQ_MODEL
from llm import get_client, generate_answer
from rag_pipeline import retrieve_chunks, build_context, Citation, RagAnswer

ROUTES = ("simple", "multi_hop", "clarify")

ROUTER_SYSTEM_PROMPT = """You classify questions about a codebase into exactly one category:

- simple: asks about ONE specific function, file, or concept \
(e.g. "where is auth handled", "what does run_nl_query do")
- multi_hop: asks how MULTIPLE parts of the code relate, interact, or compare \
(e.g. "how does the retry loop interact with the schema explorer", \
"what's the difference between X and Y", "walk me through the flow from A to B")
- clarify: too vague to search for without more detail \
(e.g. "how does it work", "explain the code", "what does this do")

Respond with exactly one word: simple, multi_hop, or clarify. Nothing else."""

DECOMPOSE_SYSTEM_PROMPT = """Break the user's question about a codebase into 2-4 focused, \
standalone sub-questions that, answered together, would answer the original question. \
Each sub-question should be independently searchable in a codebase.

Respond with ONLY a JSON array of strings, nothing else. Example:
["Where is X implemented?", "How does Y call into X?"]"""

CLARIFY_SYSTEM_PROMPT = """The user's question about a codebase is too vague to search for \
directly. Write one short, specific clarifying question that would help narrow it down — \
e.g. ask which feature, file, or behavior they mean. Keep it to one sentence."""


class AgentState(TypedDict):
    question: str
    route: str
    sub_questions: list[str]
    chunks: list  # retrieved chunk objects (FusedResult or RerankedResult)
    answer: str
    needs_clarification: bool


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """Small, direct Groq call for router/decompose/clarify steps — these
    don't need the full cited-answer machinery in llm.py's generate_answer,
    just a short classification/generation call."""
    client = get_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=256,
    )
    return response.choices[0].message.content.strip()


def route_question(state: AgentState) -> dict:
    raw = _call_llm(ROUTER_SYSTEM_PROMPT, state["question"]).lower().strip()
    # Normalize — a model might say "simple." or "Route: simple" etc.
    # Fall back to "simple" (the safe default, same as pre-Phase-6
    # behavior) if the response doesn't clearly match one of the routes.
    route = next((r for r in ROUTES if r in raw), "simple")
    return {"route": route}


def _decide_route(state: AgentState) -> str:
    return state["route"]


def retrieve_simple(state: AgentState) -> dict:
    chunks = retrieve_chunks(state["question"])
    return {"chunks": chunks}


def decompose_question(state: AgentState) -> dict:
    raw = _call_llm(DECOMPOSE_SYSTEM_PROMPT, state["question"])
    sub_questions = _parse_sub_questions(raw, fallback=state["question"])
    return {"sub_questions": sub_questions}


def _parse_sub_questions(raw: str, fallback: str) -> list[str]:
    """
    Robust-ish JSON parsing: strips markdown code fences if present,
    falls back to treating the original question as a single
    "sub-question" if the model didn't return valid JSON — degrades
    gracefully instead of crashing the whole graph on a malformed
    response.
    """
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list) and all(isinstance(q, str) for q in parsed) and parsed:
            return parsed[:4]  # cap at 4 sub-questions even if the model returns more
    except (json.JSONDecodeError, TypeError):
        pass
    return [fallback]


def retrieve_multi_hop(state: AgentState) -> dict:
    """
    Retrieves for each sub-question independently, then merges results,
    deduplicating chunks that multiple sub-questions happened to both
    retrieve (common when sub-questions are related) so the synthesis
    step doesn't see the same chunk twice.
    """
    seen_ids = set()
    merged_chunks = []
    for sub_q in state["sub_questions"]:
        for chunk in retrieve_chunks(sub_q):
            if chunk.id not in seen_ids:
                seen_ids.add(chunk.id)
                merged_chunks.append(chunk)
    return {"chunks": merged_chunks}


def synthesize_answer(state: AgentState) -> dict:
    context = build_context(state["chunks"])
    answer = generate_answer(state["question"], context)
    return {"answer": answer}


def ask_clarification(state: AgentState) -> dict:
    question = _call_llm(CLARIFY_SYSTEM_PROMPT, state["question"])
    return {"answer": question, "needs_clarification": True, "chunks": []}


def build_agent_graph():
    graph = StateGraph(AgentState)

    graph.add_node("route_question", route_question)
    graph.add_node("retrieve_simple", retrieve_simple)
    graph.add_node("decompose_question", decompose_question)
    graph.add_node("retrieve_multi_hop", retrieve_multi_hop)
    graph.add_node("synthesize_answer", synthesize_answer)
    graph.add_node("ask_clarification", ask_clarification)

    graph.add_edge(START, "route_question")
    graph.add_conditional_edges(
        "route_question",
        _decide_route,
        {
            "simple": "retrieve_simple",
            "multi_hop": "decompose_question",
            "clarify": "ask_clarification",
        },
    )
    graph.add_edge("retrieve_simple", "synthesize_answer")
    graph.add_edge("decompose_question", "retrieve_multi_hop")
    graph.add_edge("retrieve_multi_hop", "synthesize_answer")
    graph.add_edge("synthesize_answer", END)
    graph.add_edge("ask_clarification", END)

    return graph.compile()


_agent_app = None


def get_agent():
    global _agent_app
    if _agent_app is None:
        _agent_app = build_agent_graph()
    return _agent_app


@dataclass
class AgenticAnswer(RagAnswer):
    route: str = ""
    sub_questions: list[str] | None = None
    needs_clarification: bool = False


def run_agentic_query(question: str) -> AgenticAnswer:
    app = get_agent()
    result = app.invoke({
        "question": question,
        "route": "",
        "sub_questions": [],
        "chunks": [],
        "answer": "",
        "needs_clarification": False,
    })

    chunks = result.get("chunks", [])
    citations = [
        Citation(file_path=c.file_path, start_line=c.start_line, end_line=c.end_line,
                  name=c.name, code=c.code)
        for c in chunks
    ]

    return AgenticAnswer(
        answer=result["answer"],
        citations=citations,
        retrieved_chunk_count=len(chunks),
        route=result["route"],
        sub_questions=result.get("sub_questions") or None,
        needs_clarification=result.get("needs_clarification", False),
    )