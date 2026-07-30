"""
Request/response schemas for the FastAPI endpoints.
"""

from pydantic import BaseModel, Field

from config import DEFAULT_TOP_K


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question about the codebase")
    top_k: int = Field(DEFAULT_TOP_K, ge=1, le=20, description="How many chunks to retrieve")


class CitationOut(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    name: str
    code: str = ""
    github_url: str | None = None


class AskResponse(BaseModel):
    question: str
    answer: str
    citations: list[CitationOut]
    retrieved_chunk_count: int


class AgenticAskResponse(BaseModel):
    question: str
    answer: str
    citations: list[CitationOut]
    retrieved_chunk_count: int
    route: str
    sub_questions: list[str] | None = None
    needs_clarification: bool = False