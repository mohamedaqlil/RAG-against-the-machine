"""Generate grounded answers from retrieved source context."""

from pathlib import Path
from typing import Any, cast

from tqdm import tqdm
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BatchEncoding,
    PreTrainedModel,
    PreTrainedTokenizerBase,
)

from src.augmentation import build_messages, format_context
from src.indexer import BM25ContextIndex
from src.internal_types import Source
from src.io import (
    load_results,
    save_results,
)
from src.models import (
    MinimalAnswer,
    MinimalSearchResults,
    MinimalSource,
    StudentSearchResults,
    StudentSearchResultsAndAnswer,
)
from src.retrieval import search_query

MODEL_NAME = "Qwen/Qwen3-0.6B"
MAX_NEW_TOKENS = 200


def load_model() -> tuple[PreTrainedTokenizerBase, PreTrainedModel]:
    """Load the tokenizer and language model used for answer generation."""
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

    return tokenizer, model


def generate(
    messages: list[dict[str, str]],
    tokenizer: PreTrainedTokenizerBase,
    model: PreTrainedModel,
) -> str:
    """Generate an answer from prepared chat messages."""
    inputs = cast(
        BatchEncoding,
        tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            enable_thinking=False,
        ),
    )
    context_limit = model.config.max_position_embeddings
    input_length = inputs["input_ids"].shape[1]

    if input_length + MAX_NEW_TOKENS > context_limit:
        raise ValueError(
            f"Prompt exceeds model context limit: "
            f"{input_length} input tokens + "
            f"{MAX_NEW_TOKENS} generation tokens > "
            f"{context_limit}"
        )
    generation_model = cast(Any, model)
    outputs = generation_model.generate(
        **inputs,
        max_new_tokens=MAX_NEW_TOKENS,
    )

    decoded = cast(
        str,
        tokenizer.decode(
            outputs[0][input_length:],
            skip_special_tokens=True,
        ),
    )
    return decoded.strip()


def generate_answer(
    query: str, k: int, index: BM25ContextIndex, docmap: dict[str, Source]
) -> StudentSearchResultsAndAnswer:
    """Retrieve context and generate an answer for a single query."""
    search_result = search_query(query, k, index, docmap)
    tokenizer, model = load_model()

    minimal_answer = to_answered_result(search_result, tokenizer, model)

    final_result = StudentSearchResultsAndAnswer(
        search_results=[minimal_answer], k=k
    )
    return final_result


def load_source_content(source: MinimalSource) -> str:
    """Load the exact source text referenced by a minimal source."""
    file_path = Path(source.file_path)
    try:
        content = file_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(
            f"Source file not found: {source.file_path}"
        ) from exc
    return content[source.first_character_index: source.last_character_index]


def enrich_sources(minimal_sources: list[MinimalSource]) -> list[Source]:
    """Add source text content to minimal source references."""
    sources: list[Source] = []
    for source in minimal_sources:
        sources.append(
            {
                "file_path": source.file_path,
                "first_character_index": source.first_character_index,
                "last_character_index": source.last_character_index,
                "content": load_source_content(source),
            }
        )

    return sources


def generate_answer_text(
    search_result: MinimalSearchResults,
    tokenizer: PreTrainedTokenizerBase,
    model: PreTrainedModel,
) -> str:
    """Generate answer text from retrieved sources for one question."""
    sources = enrich_sources(search_result.retrieved_sources)
    fitted_sources = fit_sources_to_budget(
        search_result.question, sources, tokenizer, model
    )
    context_text = format_context(fitted_sources)
    messages = build_messages(search_result.question, context_text)
    return generate(messages, tokenizer, model)


def fit_sources_to_budget(
    question: str,
    sources: list[Source],
    tokenizer: PreTrainedTokenizerBase,
    model: PreTrainedModel,
) -> list[Source]:
    """Select ranked source chunks that fit within the model token budget."""
    fitted_sources: list[Source] = []
    for source in sources:
        candidate_sources = fitted_sources + [source]
        context_text = format_context(candidate_sources)
        messages = build_messages(question, context_text)
        inputs = cast(
            BatchEncoding,
            tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
                enable_thinking=False,
            ),
        )
        context_limit = model.config.max_position_embeddings
        input_length = inputs["input_ids"].shape[1]

        if input_length + MAX_NEW_TOKENS > context_limit:
            break
        fitted_sources = candidate_sources
    return fitted_sources


def to_answered_result(
    search_result: MinimalSearchResults,
    tokenizer: PreTrainedTokenizerBase,
    model: PreTrainedModel,
) -> MinimalAnswer:
    """Convert retrieval results into results containing a generated answer."""
    answer = generate_answer_text(search_result, tokenizer, model)
    return MinimalAnswer(
        question_id=search_result.question_id,
        question=search_result.question,
        retrieved_sources=search_result.retrieved_sources,
        answer=answer,
    )


def answer_search_results(
    student_search_results: StudentSearchResults,
    tokenizer: PreTrainedTokenizerBase,
    model: PreTrainedModel,
) -> StudentSearchResultsAndAnswer:
    """Generate answers for all retrieval results in a batch."""
    answered_results: list[MinimalAnswer] = []
    for search_result in tqdm(
        student_search_results.search_results, desc="Generating answers"
    ):
        answered_results.append(
            to_answered_result(search_result, tokenizer, model)
        )
    return StudentSearchResultsAndAnswer(
        search_results=answered_results, k=student_search_results.k
    )


def answer_dataset(path: str | Path, save_directory: str | Path) -> Path:
    """Load retrieval results, generate answers, and save them as JSON."""
    student_search_results = load_results(path)
    tokenizer, model = load_model()
    search_results = answer_search_results(
        student_search_results, tokenizer, model
    )
    output_path = save_results(
        search_results, save_directory, "search_results_and_answers.json"
    )
    return output_path


# if __name__ == "__main__":
#     from src.indexer import BM25ContextIndex
#     import json

#     INDEX_PATH = "data/processed/bm25_index.json"
#     DOCMAP_PATH = "data/processed/docmap.json"
#     index = BM25ContextIndex.load(INDEX_PATH)

#     with open(DOCMAP_PATH, "r", encoding="utf-8") as f:
#         docmap = json.load(f)

#     output = answer_dataset(
#         "data/output/search_results.json",
#         "data/output",
#     )

#     print(output)

#     answers = StudentSearchResultsAndAnswer.model_validate_json(
#         output.read_text(encoding="utf-8")
#     )

#     print(answers)
