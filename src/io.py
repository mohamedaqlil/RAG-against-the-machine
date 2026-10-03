"""Load and save datasets and RAG pipeline results."""

from pathlib import Path

from pydantic import ValidationError

from src.models import (
    RagDataset,
    StudentSearchResults,
    StudentSearchResultsAndAnswer,
)


def load_dataset(path: str | Path) -> RagDataset:
    """Load and validate a RAG dataset from a JSON file."""
    try:
        json_data = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Dataset file not found: {path}") from exc
    try:
        return RagDataset.model_validate_json(json_data)
    except ValidationError as exc:
        raise ValueError(f"Invalid dataset file: {path}") from exc


def load_results(path: str | Path) -> StudentSearchResults:
    """Load and validate student search results from a JSON file."""
    try:
        json_data = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Search results file not found: {path}") from exc
    try:
        return StudentSearchResults.model_validate_json(json_data)
    except ValidationError as exc:
        raise ValueError(f"Invalid search results file: {path}") from exc


def save_results(
    results: StudentSearchResults | StudentSearchResultsAndAnswer,
    save_directory: str | Path,
    filename: str,
) -> Path:
    """Save RAG pipeline results as JSON and return the output path."""
    directory = Path(save_directory)
    directory.mkdir(parents=True, exist_ok=True)
    output_path = directory / filename
    output_path.write_text(
        results.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return output_path
