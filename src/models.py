"""Define Pydantic models exchanged between RAG pipeline stages."""

import uuid
from typing import List

from pydantic import BaseModel, Field


class MinimalSource(BaseModel):
    """Represent a source location using a file path and character offsets."""

    file_path: str
    first_character_index: int
    last_character_index: int


class UnansweredQuestion(BaseModel):
    """Represent a question that has not yet been answered."""

    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str


class AnsweredQuestion(UnansweredQuestion):
    """
    Represent a question.

    with its generated answer and supporting sources.
    """

    sources: List[MinimalSource]
    answer: str


class RagDataset(BaseModel):
    """Represent a dataset of answered and unanswered RAG questions."""

    rag_questions: List[AnsweredQuestion | UnansweredQuestion]


class MinimalSearchResults(BaseModel):
    """Represent retrieved sources for a single question."""

    question_id: str
    question: str
    retrieved_sources: List[MinimalSource]


class MinimalAnswer(MinimalSearchResults):
    """Represent search results augmented with a generated answer."""

    answer: str


class StudentSearchResults(BaseModel):
    """Represent retrieval results for a collection of questions."""

    search_results: List[MinimalSearchResults]
    k: int


class StudentSearchResultsAndAnswer(BaseModel):
    """Represent retrieval results with generated answers."""

    search_results: List[MinimalAnswer]
    k: int
