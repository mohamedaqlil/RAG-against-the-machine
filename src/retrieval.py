"""Retrieve relevant source chunks for individual questions and datasets."""

import json
from pathlib import Path

from tqdm import tqdm

from src.augmentation import build_context, to_minimal_sources
from src.indexer import USE_STEMMING, BM25ContextIndex, tokenize_text
from src.internal_types import Source
from src.io import (
    load_dataset,
    save_results,
)
from src.models import (
    MinimalSearchResults,
    RagDataset,
    StudentSearchResults,
    UnansweredQuestion,
)


def search_query(
    query: str, k: int, index: BM25ContextIndex, docmap: dict[str, Source]
) -> MinimalSearchResults:
    """Search for source chunks relevant to a query."""
    question = UnansweredQuestion(question=query)
    return search_question(question, k, index, docmap)


def search_question(
    question: UnansweredQuestion,
    k: int,
    index: BM25ContextIndex,
    docmap: dict[str, Source],
) -> MinimalSearchResults:
    """Retrieve relevant source chunks for a question."""
    if k < 0:
        raise ValueError("k must be greater than or equal to 0")

    if not question.question.strip():
        raise ValueError("Query must not be empty")

    query_tokens = tokenize_text(
        question.question,
        use_stemming=USE_STEMMING,
    )
    results = index.search(query_tokens, k=k)

    sources = build_context(results, docmap)

    minimal_sources = to_minimal_sources(sources)
    return MinimalSearchResults(
        question_id=question.question_id,
        question=question.question,
        retrieved_sources=minimal_sources,
    )


def search_questions(
    dataset: RagDataset,
    k: int,
    index: BM25ContextIndex,
    docmap: dict[str, Source]
) -> StudentSearchResults:
    """Retrieve relevant source chunks for all questions in a dataset."""
    search_results: list[MinimalSearchResults] = []
    for question in tqdm(dataset.rag_questions, desc="Searching"):
        search_results.append(search_question(question, k, index, docmap))
    return StudentSearchResults(search_results=search_results, k=k)


def search_dataset(
    path: str | Path,
    k: int,
    save_directory: str | Path,
    index: BM25ContextIndex,
    docmap: dict[str, Source],
) -> Path:
    """Search a dataset and save the retrieval results as JSON."""
    dataset = load_dataset(path)
    search_results = search_questions(dataset, k, index, docmap)
    output_path = save_results(
        search_results, save_directory, "search_results.json"
    )
    return output_path


def load_search_artifacts(
    index_path: str | Path, docmap_path: str | Path
) -> tuple[BM25ContextIndex, dict[str, Source]]:
    """Load the persisted BM25 index and document map."""
    try:
        index = BM25ContextIndex.load(index_path)
    except FileNotFoundError as exc:
        raise ValueError(f"Index file not found: {index_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid index file: {index_path}") from exc
    try:
        json_data = Path(docmap_path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Docmap file not found: {docmap_path}") from exc
    try:
        docmap = json.loads(json_data)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid docmap file: {docmap_path}") from exc
    return index, docmap


# if __name__ == "__main__":
#     from src.indexer import BM25ContextIndex
#     import json

#     INDEX_PATH = "data/test_processed/bm25_index.json"

#     DOCMAP_PATH = "data/test_processed/docmap.json"

#     runtime_index = BM25ContextIndex.load(INDEX_PATH)

#     with open(DOCMAP_PATH, "r", encoding="utf-8") as f:
#         runtime_docmap = json.load(f)

#     # dataset = load_dataset(path)
#     # search_questions(dataset, k, index, docmap)
#     # output = search_dataset(
#     #     "test_search_dataset.json",
#     #     3,
#     #     "data/output",
#     #     runtime_index,
#     #     runtime_docmap,
#     # )

#     # print(output)
#     # print(StudentSearchResults.model_validate_json(
#     #     output.read_text(encoding="utf-8")
#     # ))
