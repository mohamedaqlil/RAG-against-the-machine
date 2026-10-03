"""Expose the RAG pipeline through the command-line interface."""

import sys
from pathlib import Path

import fire

from src.evaluation import evaluate as run_evaluate
from src.generation import answer_dataset as run_answer_dataset
from src.generation import generate_answer
from src.indexer import build_index
from src.models import StudentSearchResults
from src.retrieval import load_search_artifacts, search_query
from src.retrieval import search_dataset as run_search_dataset


def search(
    query: str,
    k: int = 5,
    index_path: str | Path = "data/processed/bm25_index.json",
    docmap_path: str | Path = "data/processed/docmap.json",
) -> str:
    """Search for source chunks relevant to a single query."""
    index, docmap = load_search_artifacts(index_path, docmap_path)
    search_result = search_query(query, k, index, docmap)
    result = StudentSearchResults(search_results=[search_result], k=k)
    return result.model_dump_json(indent=2)


def search_dataset(
    dataset_path: str | Path,
    k: int = 5,
    save_directory: str | Path = "data/output",
    index_path: str | Path = "data/processed/bm25_index.json",
    docmap_path: str | Path = "data/processed/docmap.json",
) -> Path:
    """Search all questions in a dataset and save the results."""
    index, docmap = load_search_artifacts(index_path, docmap_path)
    output_path = run_search_dataset(
        dataset_path, k, save_directory, index, docmap
    )
    return output_path


def answer(
    query: str,
    k: int = 5,
    index_path: str | Path = "data/processed/bm25_index.json",
    docmap_path: str | Path = "data/processed/docmap.json",
) -> str:
    """Retrieve context and generate an answer for a single query."""
    index, docmap = load_search_artifacts(index_path, docmap_path)
    result = generate_answer(query, k, index, docmap)
    return result.model_dump_json(indent=2)


def answer_dataset(
    student_search_results_path: str | Path,
    save_directory: str | Path = "data/output"
) -> Path:
    """Generate and save answers for persisted search results."""
    output_path = run_answer_dataset(
        student_search_results_path, save_directory
    )
    return output_path


def evaluate(
    student_search_results_path: str | Path, dataset_path: str | Path
) -> float:
    """Evaluate persisted search results against a reference dataset."""
    recall = run_evaluate(student_search_results_path, dataset_path)
    return recall


commands = {
    "index": build_index,
    "search": search,
    "search_dataset": search_dataset,
    "answer": answer,
    "answer_dataset": answer_dataset,
    "evaluate": evaluate,
}

if __name__ == "__main__":
    try:
        fire.Fire(commands)
    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)
