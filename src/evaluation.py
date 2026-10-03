"""Evaluate retrieval quality using source overlap and recall."""

from pathlib import Path

from src.io import load_dataset, load_results
from src.models import (
    AnsweredQuestion,
    MinimalSearchResults,
    RagDataset,
    StudentSearchResults,
)


def range_iou(
        ref_start: int, ref_end: int, ret_start: int, ret_end: int
) -> float:
    """Calculate intersection over union for two character ranges."""
    intersection_start = max(ref_start, ret_start)
    intersection_end = min(ref_end, ret_end)
    intersection_length = max(0, intersection_end - intersection_start)

    ref_length = ref_end - ref_start
    ret_length = ret_end - ret_start
    union = ref_length + ret_length - intersection_length

    if union == 0:
        return 0.0

    return intersection_length / union


def ranges_overlap(
        ref_start: int, ref_end: int, ret_start: int, ret_end: int
) -> bool:
    """Check whether two character ranges meet the required IoU threshold."""
    return range_iou(ref_start, ref_end, ret_start, ret_end) >= 0.05


def hit_at_k(
    reference_question: AnsweredQuestion, search_result: MinimalSearchResults
) -> bool:
    """
    Check whether retrieved sources.

    contain a correct source for a question.
    """
    for reference_source in reference_question.sources:
        for retrieved_source in search_result.retrieved_sources:
            ref_file = reference_source.file_path
            ref_start = reference_source.first_character_index
            ref_end = reference_source.last_character_index

            ret_file = retrieved_source.file_path
            ret_start = retrieved_source.first_character_index
            ret_end = retrieved_source.last_character_index
            if ret_file == ref_file and ranges_overlap(
                ref_start, ref_end, ret_start, ret_end
            ):
                return True

    return False


def recall_at_k(
    dataset: RagDataset, student_search_results: StudentSearchResults
) -> float:
    """Calculate recall at k over answered questions in a dataset."""
    search_by_id = {
        result.question_id: result
        for result in student_search_results.search_results
    }
    hits = 0
    n = 0

    for question in dataset.rag_questions:
        if not isinstance(question, AnsweredQuestion):
            continue

        n += 1
        search_result = search_by_id.get(question.question_id)

        if search_result is None:
            continue
        if hit_at_k(question, search_result):
            hits += 1
    return hits / n if n != 0 else 0


def evaluate(
    student_search_results_path: str | Path, dataset_path: str | Path
) -> float:
    """Load retrieval results and a dataset, then calculate recall at k."""
    dataset = load_dataset(dataset_path)
    student_results = load_results(student_search_results_path)
    recall = recall_at_k(dataset, student_results)
    return recall


# if __name__ == "__main__":
#     PROJECT_ROOT = os.path.dirname(
#         os.path.dirname(os.path.abspath(__file__))
#     )
#     CODE_PATH = os.path.join(
#         PROJECT_ROOT,
#         "datasets_public",
#         "public",
#         "AnsweredQuestions",
#         "dataset_code_public.json",
#     )
#     DOCS_PATH = os.path.join(
#         PROJECT_ROOT,
#         "datasets_public",
#         "public",
#         "AnsweredQuestions",
#         "dataset_docs_public.json",
#     )

#     with open(CODE_PATH, "r", encoding="utf-8") as f:
#         code_eval = json.load(f)

#     with open(DOCS_PATH, "r", encoding="utf-8") as f:
#         docs_eval = json.load(f)

#     code_questions = code_eval["rag_questions"]
#     docs_questions = docs_eval["rag_questions"]

#     INDEX_PATH = "data/test_processed/bm25_index.json"
#     DOCMAP_PATH = "data/test_processed/docmap.json"

#     runtime_index = BM25ContextIndex.load(INDEX_PATH)

#     with open(DOCMAP_PATH, "r", encoding="utf-8") as f:
#         runtime_docmap = json.load(f)

#     code_recall = recall_at_k(
#         code_questions, runtime_index, runtime_docmap
#     )
#     docs_recall = recall_at_k(
#         docs_questions, runtime_index, runtime_docmap
#     )

#     print(code_recall)
#     print(docs_recall)
