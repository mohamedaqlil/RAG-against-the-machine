from src.models import UnansweredQuestion, RagDataset
from src.retrieval import search_questions
from src.indexer import BM25ContextIndex
import json

INDEX_PATH = "data/test_processed/bm25_index.json"

DOCMAP_PATH = "data/test_processed/docmap.json"

runtime_index = BM25ContextIndex.load(INDEX_PATH)

with open(DOCMAP_PATH, "r", encoding="utf-8") as f:
    runtime_docmap = json.load(f)

question = UnansweredQuestion(
    question="What is the current limitation when using MLP speculators for speculative decoding in vLLM?"
)

dataset = RagDataset(rag_questions=[question])

result = search_questions(
    dataset,
    3,
    runtime_index,
    runtime_docmap,
)

print(result.model_dump_json(indent=2))
