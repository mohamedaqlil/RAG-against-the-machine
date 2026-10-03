"""Build and format retrieved context for answer generation."""

from src.internal_types import Source
from src.models import MinimalSource


def build_context(
    results: list[tuple[str, float]], docmap: dict[str, Source]
) -> list[Source]:
    """Attach runtime content and retrieval metadata to search results."""
    sources = []

    for chunk_id, score in results:
        source = docmap[chunk_id]
        context = source.copy()
        context["chunk_id"] = chunk_id
        context["score"] = score
        sources.append(context)

    return sources


def format_context(sources: list[Source]) -> str:
    """Format retrieved source chunks as context for the language model."""
    result = ""
    for i, source in enumerate(sources, start=1):
        result += f"[SOURCE {i}]\n"
        result += f'File: {source["file_path"]}\n'
        result += (
            f'Range: {source["first_character_index"]}-'
            f'{source["last_character_index"]}\n'
        )
        result += "Content:\n"
        result += f'{source["content"]}\n'
        result += "\n\n"
    return result


def build_messages(question: str, context_text: str) -> list[dict[str, str]]:
    """Build chat messages containing the question and retrieved context."""
    prompt = "You are a RAG agent for vLLM repository.\n"
    prompt += (
        "Your task is to provide a natural-language answer "
        "to the user's query based only on the provided sources "
        "retrieved during search.\n"
    )
    prompt += (
        "Provide a comprehensive answer that addresses "
        "the user's query.\n"
    )
    prompt += (
        "If the sources do not contain enough information to answer, "
        "say that the provided sources do not contain enough information.\n"
    )
    prompt += (
        "Cite the source number(s) used in the answer, "
        "such as [SOURCE 3]."
    )
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": f"Sources:\n{context_text}\n\nQuestion: {question}",
        },
    ]
    return messages


def to_minimal_sources(sources: list[Source]) -> list[MinimalSource]:
    """Convert internal source data to minimal source references."""
    minimal_sources: list[MinimalSource] = []

    for source in sources:
        minimal_sources.append(
            MinimalSource(
                file_path=source["file_path"],
                first_character_index=source["first_character_index"],
                last_character_index=source["last_character_index"],
            )
        )

    return minimal_sources
