import os, pathlib, json
from pathlib import Path, PosixPath
import re
from src.models import MinimalSource
import ast
from src.indexer import tokenize_text, InvertedIndex


RAW_DIR = "data/raw"

raw_dir = Path(RAW_DIR)
IGNORED_DIRS = {"__pycache__", ".git", ".venv", ".mypy_cache"}

def file_discovery(raw_dir):
    paths = []
    for path in raw_dir.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix in {".py", ".md"}:
            paths.append(path)
    return paths

def chunk_markdown(paths):
    chunks_out = []
    for path in paths:
        if path.suffix == ".md":
            content = path.read_text(encoding="utf-8")
            headers = list(re.finditer(r"^#{1,6}\s+.+$", content, re.MULTILINE))


            if not headers:
                chunks_out.append(MinimalSource(
                    file_path=str(path),
                    first_character_index=0,
                    last_character_index=len(content)
                ))

            for i in range(len(headers)):
                if i == len(headers) - 1:
                    start_index = headers[i].start()
                    end_index = len(content)
                    chunk = content[headers[i].start(): len(content)]
                else:
                    start_index = headers[i].start()
                    end_index = headers[i+1].start()
                    chunk = content[headers[i].start(): headers[i+1].start()]

                if len(chunk) > 2000:
                    chunks = chunk.split("\n\n")
                    offset = headers[i].start()
                    for c in chunks:
                        start_index = offset
                        paragraph_start = offset
                        end_index = offset + len(c)
                        offset = end_index + len("\n\n")
                        if not c:
                            continue
                        if len(c) > 2000:
                            small_chunks = c.split("\n")
                            line_offset = paragraph_start
                            for c in small_chunks:
                                start_index = line_offset
                                end_index = line_offset + len(c)
                                line_offset = end_index + len("\n")
                                if not c:
                                    continue
                                chunks_out.append(MinimalSource(
                                    file_path=str(path),
                                    first_character_index=start_index,
                                    last_character_index=end_index
                                ))

                        else:

                            chunks_out.append(MinimalSource(
                                file_path=str(path),
                                first_character_index=start_index,
                                last_character_index=end_index
                            ))
                else:
                    chunks_out.append(MinimalSource(
                        file_path=str(path),
                        first_character_index=start_index,
                        last_character_index=end_index
                    ))
            # for chunk in chunks_out[:5]:  # just check the first few
            #     print("---")
            #     print(content[chunk.first_character_index:chunk.last_character_index])
            # print(repr(content[382:383]))
    return chunks_out
                    # print(f"OVERSIZED: {path} chunk is {len(chunk)} chars")

        # print(f"chunk length: {len(chunk)}")
        # print(f"chunk {i+1}: {chunk}")
    #     print(content[item.span()[0]: item.span()[1]])
        # print(f"{path.name}: {item.start()} [{item.span()[0]}: {item.span()[1]}]")
        # for c in item.group():
        #     print(c)
ignored = 0
processed = 0
def pack_statements(stmts, content, line_offset, lines, path, threshold=2000):
    global processed
    global ignored
    sub_chunks = []
    current_texts = []
    current_start = None
    current_end = None

    for stmt in stmts:
        stmt_start = line_offset[stmt.lineno - 1]
        stmt_end = line_offset[stmt.end_lineno - 1] + len(lines[stmt.end_lineno - 1])
        stmt_txt = content[stmt_start:stmt_end]
        stmt_size = len(stmt_txt)
        stmt_name = getattr(stmt, 'name', 'Unnamed')
        if stmt_size > threshold:
            if hasattr(stmt, "body"):
                if current_texts:
                    sub_chunks.append((current_start, current_end))
                    current_texts = []
                sub_chunks += pack_statements(stmt.body, content, line_offset, lines, path, threshold=threshold)
            if hasattr(stmt, "orelse"):
                if current_texts:
                    sub_chunks.append((current_start, current_end))
                    current_texts = []
                sub_chunks += pack_statements(stmt.orelse, content, line_offset, lines, path, threshold=threshold)
            if hasattr(stmt, "body") or hasattr(stmt, "orelse"):
                processed += 1
                continue
            else:
                # print(f"OVERSIZED {type(stmt).__name__}: {stmt_name} [{stmt.lineno} : {stmt.end_lineno}] path:{path}")
                ignored += 1
                processed += 1
                continue

        if current_texts and (stmt_end - current_start) > threshold:
            sub_chunks.append((current_start, current_end))
            current_texts = []
        if not current_texts:
            current_start = stmt_start

        current_end = stmt_end
        current_texts.append(stmt_txt)
        processed += 1

    if current_texts:
        sub_chunks.append((current_start, current_end))
    return sub_chunks


def chunk_py(paths, threshold=2000):
    global processed
    global ignored
    chunks_out = []
    for path in paths:
        if path.suffix == ".py":
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            lines = content.split("\n")
            line_offset = [0]
            for line in lines[:-1]:
                next_offset = line_offset[-1] + len(line) + 1
                line_offset.append(next_offset)

            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                    start_index = line_offset[node.lineno - 1]
                    end_index = line_offset[node.end_lineno - 1] + len(lines[node.end_lineno - 1])

                    if (end_index - start_index) > threshold:
                        sub_chunks = pack_statements(node.body, content, line_offset, lines, path, threshold=threshold)

                        for start_index, end_index in sub_chunks:
                            chunks_out.append(MinimalSource(
                                file_path=str(path),
                                first_character_index=start_index,
                                last_character_index=end_index
                            ))
                        # print(f"OVERSIZED {type(node).__name__}: {node.name} in {str(path)}")
                    else:
                        chunks_out.append(MinimalSource(
                            file_path=str(path),
                            first_character_index=start_index,
                            last_character_index=end_index
                        ))
                    # for chunk in chunks_out:
                    #     print("---")
                    #     print(content[chunk.first_character_index:chunk.last_character_index])
        # print(f"{ignored} oversized leaves out of {processed} statements")
    return chunks_out


paths = file_discovery(raw_dir)

# chunk_markdown(paths)

# paths = [Path('data/raw/vllm-0.10.1/benchmarks/benchmark_serving_structured_output.py')]

py_chunks = chunk_py(paths)
m_chunks = chunk_markdown(paths)
chunks = py_chunks + m_chunks

# print("Python chunk count:", len(py_chunks))
# print("Markdown chunk count:", len(m_chunks))

oversized = []

# for source in chunks:
#     if source.last_character_index - source.first_character_index > 2000:
#         oversized.append(f"{source.file_path}[{source.first_character_index}:{source.last_character_index}]")

res = "\n".join(oversized) or "nothing"
# print("Oversized chunks:", res)

from collections import defaultdict

docmap: dict = defaultdict(dict)

for chunk in chunks:
    docmap[f"{chunk.file_path}::{chunk.first_character_index}_{chunk.last_character_index}"]["file_path"] = chunk.file_path
    docmap[f"{chunk.file_path}::{chunk.first_character_index}_{chunk.last_character_index}"]["first_character_index"] = chunk.first_character_index
    docmap[f"{chunk.file_path}::{chunk.first_character_index}_{chunk.last_character_index}"]["last_character_index"] = chunk.last_character_index
    docmap[f"{chunk.file_path}::{chunk.first_character_index}_{chunk.last_character_index}"]["content"] = open(chunk.file_path, "r", encoding="utf-8").read()[chunk.first_character_index:chunk.last_character_index]

corpus = {}

for chunk_id, source in docmap.items():
    tokens = tokenize_text(source["content"])

    if tokens:
        corpus[chunk_id] = tokens
# for k, v in three_entries.items():
#     print("--------------------------------------------")
#     print(k)
#     print(v[:10])
# print(docmap[f"{chunks[0].file_path}::{chunks[0].first_character_index}_{chunks[0].last_character_index}"])

# print("docmap entries:", len(docmap))
# print("real corpus entries:", len(corpus))

# empty_tokenized_chunks = [
#     chunk_id
#     for chunk_id, tokens in corpus.items()
#     if not tokens
# ]

# print("empty tokenized chunks:", len(empty_tokenized_chunks))


all_python_files = {str(path) for path in paths if path.suffix == ".py"}
chunked_python_files = {chunk.file_path for chunk in py_chunks}

missing_python_files = all_python_files - chunked_python_files

# print(f"Missing python files: {[path for path in missing_python_files][:10]}")

# print(f"Missing python files: {[f"content for {path}: {open(path, "r").read()}" for path in missing_python_files][:10]}")

# all_markdown_files = {str(path) for path in paths if path.suffix == ".md"}
# chunked_markdown_files = {chunk.file_path for chunk in m_chunks}

# missing_markdown_files = all_markdown_files - chunked_markdown_files

# print(f"Missing Markdown files: {[f"content_length for {path}: {len((open(path, "r")).read())}" for path in missing_markdown_files]}")


index = InvertedIndex()
index.build(corpus)

print("IDF terms:", len(index.idf))
print("Indexed terms:", len(index.inverted_index))
print("Document norms:", len(index.document_norms))
print()
print()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE_PATH = os.path.join(PROJECT_ROOT, "datasets_public", "public", "AnsweredQuestions", "dataset_code_public.json")
DOCS_PATH = os.path.join(PROJECT_ROOT, "datasets_public", "public", "AnsweredQuestions", "dataset_docs_public.json")

with open(CODE_PATH, "r", encoding="utf-8") as f:
    code_eval = json.load(f)

with open(DOCS_PATH, "r", encoding="utf-8") as f:
    docs_eval = json.load(f)

code_questions = code_eval["rag_questions"]
docs_questions = docs_eval["rag_questions"]

# for name, questions in [
#     ("code", code_questions),
#     ("docs", docs_questions)
# ]:
#     counts = {}

#     for question in questions:
#         n = len(question["sources"])
#         counts[n] = counts.get(n, 0) + 1

#     print(name, counts)


from src.evaluation import ranges_overlap


def hit_at_k(question, index, docmap, k=5):
    reference = question["sources"][0]

    ref_file = reference["file_path"]
    ref_start = reference["first_character_index"]
    ref_end = reference["last_character_index"]

    query_tokens = tokenize_text(question["question"])
    results = index.search(query_tokens, k=k)
    for chunk_id, score in results:
        source = docmap[chunk_id]

        if source["file_path"] == ref_file:
            if ranges_overlap(ref_start, ref_end, source["first_character_index"], source["last_character_index"]):
                return True
    return False

# print("Question:", question["question"])
# print("Hit@5:", hit)

# print(query_tokens)
# print(results)

# for chunk_id, score in results:
#     source = docmap[chunk_id]
#     print(
#         score,
#         source["file_path"],
#         source["first_character_index"],
#         source["last_character_index"]
#     )
#     print()

def recall_at_k(questions, index, docmap, k=5):
    hits = 0

    for question in questions:
        if hit_at_k(question, index, docmap, k=k):
            hits += 1

    return hits / len(questions)

code_recall = recall_at_k(code_questions, index, docmap, k=5)
docs_recall = recall_at_k(docs_questions, index, docmap, k=5)

# print(code_recall)
# print(docs_recall)

# question = code_questions[0]
def reference_is_covered(question, docmap):
    reference = question["sources"][0]

    ref_file = reference["file_path"]
    ref_start = reference["first_character_index"]
    ref_end = reference["last_character_index"]

    for source in docmap.values():
        if source["file_path"] == ref_file:
            if ranges_overlap(ref_start, ref_end, source["first_character_index"], source["last_character_index"]):
                return True
                # print(source["first_character_index"])
                # print(source["last_character_index"])
                # print(source["content"])
    return False

hits = 0
covered_misses = 0
uncovered_misses = 0

# for question in docs_questions:
#     if hit_at_k(question, index, docmap, k=100):
#         hits += 1
#     elif reference_is_covered(question, docmap):
#         covered_misses += 1
#     else:
#         uncovered_misses += 1


# print("Hits:", hits)
# print("Covered misses:", covered_misses)
# print("Uncovered misses:", uncovered_misses)
# print("Total:", hits + covered_misses + uncovered_misses)


for question in code_questions:
    if (not hit_at_k(question, index, docmap, k=5)
        and reference_is_covered(question, docmap)):
        break

print("Question:", question["question"])

reference = question["sources"][0]

ref_file = reference["file_path"]
ref_start = reference["first_character_index"]
ref_end = reference["last_character_index"]
query_tokens = tokenize_text(question["question"])
results = index.search(query_tokens, k=1000)
# for rank, (chunk_id, score) in enumerate(results, start=1):
#     source = docmap[chunk_id]

#     if source["file_path"] == ref_file:
#         if ranges_overlap(ref_start, ref_end, source["first_character_index"], source["last_character_index"]):
#             print("Relevant rank:", rank)

#             print("Score:", score)

#             print(

#                 "Range:",

#                 source["first_character_index"],

#                 source["last_character_index"],

#             )

#             print("Content:")

#             print(source["content"])
#             break

print("Query tokens:")
print(query_tokens)

from src.indexer import tf_idf, vector_magnitude, dot_product, cosine_similarity


# for chunk_id, source in docmap.items():
#     if (
#         source["file_path"] == ref_file
#         and ranges_overlap(
#             ref_start,
#             ref_end,
#             source["first_character_index"],
#             source["last_character_index"],
#         )
#     ):
#         chunk_tokens = tokenize_text(source["content"])

#         doc_vector = tf_idf(chunk_tokens, index.idf)
#         query_vector = tf_idf(query_tokens, index.idf)

#         print("Query magnitude:", vector_magnitude(query_vector))
#         print("Document magnitude:", vector_magnitude(doc_vector))
#         print("Dot product:", dot_product(query_vector, doc_vector))
#         print("Cosine:", cosine_similarity(query_vector, doc_vector))

#         print("Chunk token count:", len(chunk_tokens))
#         print("Unique chunk tokens:", len(set(chunk_tokens)))

#         # print("\nShared tokens:")
#         # print(set(query_tokens) & set(chunk_tokens))
#         break

# query_vector = tf_idf(query_tokens, index.idf)

# top_chunk_id, top_score = results[0]

# top_source = docmap[top_chunk_id]
# top_tokens = corpus[top_chunk_id]

# top_vector = tf_idf(top_tokens, index.idf)

# print("Top result:", top_chunk_id)
# print("Score:", top_score)

# print("Document magnitude:", vector_magnitude(top_vector))
# print("Dot product:", dot_product(query_vector, top_vector))

# print("Chunk token count:", len(top_tokens))
# print("Unique chunk tokens:", len(set(top_tokens)))

# print(
#     "Shared tokens:",
#     set(query_tokens) & set(top_tokens)
# )

# print("\nContent:")
# print(top_source["content"])


def relevant_rank(question, index, docmap, k=1000):
    reference = question["sources"][0]
    ref_file = reference["file_path"]
    ref_start = reference["first_character_index"]
    ref_end = reference["last_character_index"]
    query_tokens = tokenize_text(question["question"])
    results = index.search(query_tokens, k=k)
    for rank, (chunk_id, score) in enumerate(results, start=1):
        source = docmap[chunk_id]

        if source["file_path"] == ref_file:
            if ranges_overlap(ref_start, ref_end, source["first_character_index"], source["last_character_index"]):
                return rank
    return None

covered_miss_ranks = []

for question in docs_questions:
    if (
        not hit_at_k(question, index, docmap, k=5)
        and reference_is_covered(question, docmap)
    ):
        rank = relevant_rank(question, index, docmap, k=1000)
        covered_miss_ranks.append(rank)

buckets = {
    "6-10": 0,
    "11-20": 0,
    "21-50": 0,
    "51-100": 0,
    "101-1000": 0,
    "None": 0,
}

for rank in covered_miss_ranks:
    if rank is None:
        buckets["None"] += 1
    elif rank <= 10:
        buckets["6-10"] += 1
    elif rank <= 20:
        buckets["11-20"] += 1
    elif rank <= 50:
        buckets["21-50"] += 1
    elif rank <= 100:
        buckets["51-100"] += 1
    elif rank <= 1000:
        buckets["101-1000"] += 1

print(buckets)

print("Total:", sum(buckets.values()))
