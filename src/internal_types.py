"""Define internal runtime types used across the RAG pipeline."""

from typing import NotRequired, TypedDict


class Source(TypedDict):
    """Represent an internal source chunk with its text and metadata."""

    file_path: str
    first_character_index: int
    last_character_index: int
    content: str
    chunk_id: NotRequired[str]
    score: NotRequired[float]
