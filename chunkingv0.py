import os, pathlib, json
from pathlib import Path, PosixPath
import re
from src.models import MinimalSource
import ast
from src.indexer import (
    tokenize_text,
    InvertedIndex,
    BM25Index,
    BM25ContextIndex,
)

RAW_DIR = "data/raw"
PROC_DIR = "data/processed"
USE_STEMMING = True
REMOVE_STOPWORDS = False

raw_dir = Path(RAW_DIR)
proc_dir = Path(PROC_DIR)
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


def pack_lines(text, threshold=2000):
    res = []

    current_start = None
    current_end = None

    start = 0

    for line in text.splitlines():
        line_start = start
        line_end = line_start + len(line)

        if current_start is None:
            # Start the first/current chunk
            current_start = line_start
            current_end = line_end

        elif line_end - current_start <= threshold:
            # Current line still fits.
            # What should current_end become?
            current_end = line_end

        else:
            # Current line doesn't fit.
            # 1. Save the OLD chunk.
            # 2. Start a NEW chunk with this line.
            res.append((current_start, current_end))
            current_start = line_start
            current_end = line_end

        start = line_end + len("\n")

    # What chunk is still waiting here after the loop?
    if current_start is not None:
        res.append((current_start, current_end))

    return res


def chunk_markdown(paths):
    chunks_out = []
    for path in paths:
        if path.suffix == ".md":
            content = path.read_text(encoding="utf-8")
            headers = list(
                re.finditer(r"^#{1,6}\s+.+$", content, re.MULTILINE)
            )

            if not headers:
                chunks_out.append(
                    MinimalSource(
                        file_path=str(path),
                        first_character_index=0,
                        last_character_index=len(content),
                    )
                )

            for i in range(len(headers)):
                if i == len(headers) - 1:
                    start_index = headers[i].start()
                    end_index = len(content)
                    chunk = content[headers[i].start() : len(content)]
                else:
                    start_index = headers[i].start()
                    end_index = headers[i + 1].start()
                    chunk = content[
                        headers[i].start() : headers[i + 1].start()
                    ]

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
                            packed_ranges = pack_lines(c, threshold=2000)

                            for (
                                relative_start,
                                relative_end,
                            ) in packed_ranges:
                                start_index = (
                                    paragraph_start + relative_start
                                )
                                end_index = paragraph_start + relative_end

                                chunks_out.append(
                                    MinimalSource(
                                        file_path=str(path),
                                        first_character_index=start_index,
                                        last_character_index=end_index,
                                    )
                                )

                        else:

                            chunks_out.append(
                                MinimalSource(
                                    file_path=str(path),
                                    first_character_index=start_index,
                                    last_character_index=end_index,
                                )
                            )
                else:
                    chunks_out.append(
                        MinimalSource(
                            file_path=str(path),
                            first_character_index=start_index,
                            last_character_index=end_index,
                        )
                    )
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


def find_nearest_heading(content, chunk_start):
    heading = ""
    headers = list(re.finditer(r"^#{1,6}\s+.+$", content, re.MULTILINE))

    for i, header in enumerate(headers):
        if header.start() <= chunk_start:
            heading = header.group(0)
        else:
            break
    return heading


def pack_paragraphs(paragraphs, threshold=2000):
    res = []

    current_start = None
    current_end = None

    for paragraph_start, paragraph_end in paragraphs:

        if current_start is None:
            # Start the first/current chunk
            current_start = paragraph_start
            current_end = paragraph_end

        elif paragraph_end - current_start <= threshold:
            # Current line still fits.
            # What should current_end become?
            current_end = paragraph_end

        else:
            # Current line doesn't fit.
            # 1. Save the OLD chunk.
            # 2. Start a NEW chunk with this line.
            res.append((current_start, current_end))
            current_start = paragraph_start
            current_end = paragraph_end

    # What chunk is still waiting here after the loop?
    if current_start is not None:
        res.append((current_start, current_end))

    return res


def old_chunk_markdown(paths):
    chunks_out = []
    for path in paths:
        if path.suffix == ".md":
            content = path.read_text(encoding="utf-8")
            headers = list(
                re.finditer(r"^#{1,6}\s+.+$", content, re.MULTILINE)
            )

            if not headers:
                chunks_out.append(
                    MinimalSource(
                        file_path=str(path),
                        first_character_index=0,
                        last_character_index=len(content),
                    )
                )

            for i in range(len(headers)):
                if i == len(headers) - 1:
                    start_index = headers[i].start()
                    end_index = len(content)
                    chunk = content[headers[i].start() : len(content)]
                else:
                    start_index = headers[i].start()
                    end_index = headers[i + 1].start()
                    chunk = content[
                        headers[i].start() : headers[i + 1].start()
                    ]

                if len(chunk) > 2000:
                    paragraph_ranges = []
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
                            if paragraph_ranges:
                                packed_ranges = pack_paragraphs(
                                    paragraph_ranges,
                                    threshold=2000,
                                )

                                for (
                                    packed_start,
                                    packed_end,
                                ) in packed_ranges:
                                    chunks_out.append(
                                        MinimalSource(
                                            file_path=str(path),
                                            first_character_index=packed_start,
                                            last_character_index=packed_end,
                                        )
                                    )

                                paragraph_ranges = []
                            small_chunks = c.split("\n")
                            line_offset = paragraph_start
                            for c in small_chunks:
                                start_index = line_offset
                                end_index = line_offset + len(c)
                                line_offset = end_index + len("\n")
                                if not c:
                                    continue
                                chunks_out.append(
                                    MinimalSource(
                                        file_path=str(path),
                                        first_character_index=start_index,
                                        last_character_index=end_index,
                                    )
                                )
                        else:

                            paragraph_ranges.append(
                                (start_index, end_index)
                            )
                    if paragraph_ranges:
                        packed_ranges = pack_paragraphs(
                            paragraph_ranges,
                            threshold=2000,
                        )

                        for packed_start, packed_end in packed_ranges:
                            chunks_out.append(
                                MinimalSource(
                                    file_path=str(path),
                                    first_character_index=packed_start,
                                    last_character_index=packed_end,
                                )
                            )

                        paragraph_ranges = []
                else:
                    chunks_out.append(
                        MinimalSource(
                            file_path=str(path),
                            first_character_index=start_index,
                            last_character_index=end_index,
                        )
                    )
    return chunks_out


ignored = 0
processed = 0


def pack_statements(
    stmts, content, line_offset, lines, path, threshold=2000
):
    global processed
    global ignored
    sub_chunks = []
    current_texts = []
    current_start = None
    current_end = None

    for stmt in stmts:
        stmt_start = line_offset[stmt.lineno - 1]
        stmt_end = line_offset[stmt.end_lineno - 1] + len(
            lines[stmt.end_lineno - 1]
        )
        stmt_txt = content[stmt_start:stmt_end]
        stmt_size = len(stmt_txt)
        stmt_name = getattr(stmt, "name", "Unnamed")
        if stmt_size > threshold:
            if hasattr(stmt, "body"):
                if current_texts:
                    sub_chunks.append((current_start, current_end))
                    current_texts = []
                sub_chunks += pack_statements(
                    stmt.body,
                    content,
                    line_offset,
                    lines,
                    path,
                    threshold=threshold,
                )
            if hasattr(stmt, "orelse"):
                if current_texts:
                    sub_chunks.append((current_start, current_end))
                    current_texts = []
                sub_chunks += pack_statements(
                    stmt.orelse,
                    content,
                    line_offset,
                    lines,
                    path,
                    threshold=threshold,
                )
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
                if isinstance(
                    node,
                    (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef),
                ):
                    start_index = line_offset[node.lineno - 1]
                    end_index = line_offset[node.end_lineno - 1] + len(
                        lines[node.end_lineno - 1]
                    )

                    if (end_index - start_index) > threshold:
                        sub_chunks = pack_statements(
                            node.body,
                            content,
                            line_offset,
                            lines,
                            path,
                            threshold=threshold,
                        )

                        for start_index, end_index in sub_chunks:
                            chunks_out.append(
                                MinimalSource(
                                    file_path=str(path),
                                    first_character_index=start_index,
                                    last_character_index=end_index,
                                )
                            )
                        # print(f"OVERSIZED {type(node).__name__}: {node.name} in {str(path)}")
                    else:
                        chunks_out.append(
                            MinimalSource(
                                file_path=str(path),
                                first_character_index=start_index,
                                last_character_index=end_index,
                            )
                        )
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
old_chunks = py_chunks + old_chunk_markdown(paths)

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
    docmap[
        f"{chunk.file_path}::{chunk.first_character_index}_{chunk.last_character_index}"
    ]["file_path"] = chunk.file_path
    docmap[
        f"{chunk.file_path}::{chunk.first_character_index}_{chunk.last_character_index}"
    ]["first_character_index"] = chunk.first_character_index
    docmap[
        f"{chunk.file_path}::{chunk.first_character_index}_{chunk.last_character_index}"
    ]["last_character_index"] = chunk.last_character_index
    docmap[
        f"{chunk.file_path}::{chunk.first_character_index}_{chunk.last_character_index}"
    ]["content"] = open(chunk.file_path, "r", encoding="utf-8").read()[
        chunk.first_character_index : chunk.last_character_index
    ]

corpus = {}

for chunk_id, source in docmap.items():
    tokens = tokenize_text(
        source["content"],
        use_stemming=USE_STEMMING,
        remove_stopwords=REMOVE_STOPWORDS,
    )

    if tokens:
        corpus[chunk_id] = tokens


old_docmap: dict = defaultdict(dict)

for chunk in old_chunks:
    old_docmap[
        f"{chunk.file_path}::{chunk.first_character_index}_{chunk.last_character_index}"
    ]["file_path"] = chunk.file_path
    old_docmap[
        f"{chunk.file_path}::{chunk.first_character_index}_{chunk.last_character_index}"
    ]["first_character_index"] = chunk.first_character_index
    old_docmap[
        f"{chunk.file_path}::{chunk.first_character_index}_{chunk.last_character_index}"
    ]["last_character_index"] = chunk.last_character_index
    old_docmap[
        f"{chunk.file_path}::{chunk.first_character_index}_{chunk.last_character_index}"
    ]["content"] = open(chunk.file_path, "r", encoding="utf-8").read()[
        chunk.first_character_index : chunk.last_character_index
    ]

old_corpus = {}
heading_corpus = {}

for chunk_id, source in old_docmap.items():
    text_for_indexing = source["content"]

    if source["file_path"].endswith(".md"):
        full_content = open(
            source["file_path"], "r", encoding="utf-8"
        ).read()
        heading = find_nearest_heading(
            full_content, source["first_character_index"]
        )
        if heading and source["content"].strip() != heading.strip():
            text_for_indexing = heading + text_for_indexing
    tokens = tokenize_text(
        text_for_indexing,
        use_stemming=USE_STEMMING,
        remove_stopwords=REMOVE_STOPWORDS,
    )

    if tokens:
        heading_corpus[chunk_id] = tokens

    tokens = tokenize_text(
        source["content"],
        use_stemming=USE_STEMMING,
        remove_stopwords=REMOVE_STOPWORDS,
    )

    if tokens:
        old_corpus[chunk_id] = tokens

dedup_heading_corpus = {}
for chunk_id, source in old_docmap.items():

    chunk_tokens = tokenize_text(
        source["content"],
        use_stemming=USE_STEMMING,
        remove_stopwords=REMOVE_STOPWORDS,
    )
    tokens = chunk_tokens

    if source["file_path"].endswith(".md"):
        full_content = open(
            source["file_path"], "r", encoding="utf-8"
        ).read()
        heading = find_nearest_heading(
            full_content, source["first_character_index"]
        )

        if heading and source["content"].strip() != heading.strip():

            heading_tokens = tokenize_text(
                heading,
                use_stemming=USE_STEMMING,
                remove_stopwords=REMOVE_STOPWORDS,
            )

            new_heading_tokens = [
                token
                for token in heading_tokens
                if token not in chunk_tokens
            ]

            tokens = new_heading_tokens + tokens

    if tokens:
        dedup_heading_corpus[chunk_id] = tokens

# structured_id = (
#     "data/raw/vllm-0.10.1/docs/features/"
#     "structured_outputs.md::5461_5535"
# )

# mlp_id = (
#     "data/raw/vllm-0.10.1/docs/features/"
#     "spec_decode.md::5027_5352"
# )

# for name, chunk_id in [
#     ("STRUCTURED", structured_id),
#     ("MLP", mlp_id),
# ]:
#     print("\n---", name, "---")
#     print("OLD:")
#     print(old_corpus[chunk_id])

#     print("\nDEDUP HEADING:")
#     print(dedup_heading_corpus[chunk_id])

#     added = (
#         dedup_heading_corpus[chunk_id][
#             :len(dedup_heading_corpus[chunk_id]) - len(old_corpus[chunk_id])
#         ]
#     )

#     print("\nADDED:")
#     print(added)

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

# index = BM25Index()
# index.build(corpus)

# old_index = BM25Index()
# old_index.build(old_corpus)

# print("IDF terms:", len(index.idf))
# print("Indexed terms:", len(index.inverted_index))
# print("Document norms:", len(index.document_norms))
# print()
# print()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE_PATH = os.path.join(
    PROJECT_ROOT,
    "datasets_public",
    "public",
    "AnsweredQuestions",
    "dataset_code_public.json",
)
DOCS_PATH = os.path.join(
    PROJECT_ROOT,
    "datasets_public",
    "public",
    "AnsweredQuestions",
    "dataset_docs_public.json",
)

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


from src.evaluation import ranges_overlap, range_iou


def hit_at_k(question, index, docmap, k=5):
    reference = question["sources"][0]

    ref_file = reference["file_path"]
    ref_start = reference["first_character_index"]
    ref_end = reference["last_character_index"]
    best_iou = 0.0
    best_source = None

    query_tokens = tokenize_text(
        question["question"],
        use_stemming=USE_STEMMING,
        remove_stopwords=REMOVE_STOPWORDS,
    )
    results = index.search(query_tokens, k=k)
    for chunk_id, score in results:
        source = docmap[chunk_id]

        if source["file_path"] == ref_file:
            iou = range_iou(
                ref_start,
                ref_end,
                source["first_character_index"],
                source["last_character_index"],
            )
            if iou > best_iou:
                best_iou = iou
                best_source = source
            if ranges_overlap(
                ref_start,
                ref_end,
                source["first_character_index"],
                source["last_character_index"],
            ):
                return True
    if 0 < best_iou < 0.05:
        print(f"reference: {ref_start}-{ref_end}")
        print(
            f"best retrieved: "
            f"{best_source['first_character_index']}-"
            f"{best_source['last_character_index']}"
        )
        print(f"file: {best_source['file_path']}")
        print(question["question"])
        print("best IoU:", best_iou)
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


# k1_values = [0.4, 0.6, 0.8, 1.0]
# b_values = [1.0]

# for k1 in k1_values:
#     for b in b_values:
#         index = BM25Index(k1=k1, b=b)
#         index.build(corpus)
#         code_recall = recall_at_k(code_questions, index, docmap)
#         docs_recall = recall_at_k(docs_questions, index, docmap)
#         print(f"{k1} | {b} | {code_recall} | {docs_recall}")

# code_recall = recall_at_k(code_questions, index, docmap)
# docs_recall = recall_at_k(docs_questions, index, docmap)

# print("-----------------NEW-----------------------------")
# print("code recall", code_recall)
# print("docs recall", docs_recall)
# heading_index = BM25Index(k1=0.8, b=1.0)
# heading_index.build(heading_corpus)
# dedup_heading_index = BM25Index(k1=0.8, b=1.0)
# dedup_heading_index.build(dedup_heading_corpus)
# print("BASELINE")
# print("code:", recall_at_k(code_questions, old_index, old_docmap))
# print("docs:", recall_at_k(docs_questions, old_index, old_docmap))
# context_index = BM25ContextIndex(k1=0.8, b=1.0)
# context_search_corpus = {
#     doc_id: tokens
#     for doc_id, tokens in dedup_heading_corpus.items()
#     if doc_id in old_corpus
# }

# context_index.build(
#     context_search_corpus,
#     old_corpus
# )
# print("\nCONTEXT INDEX")
# print("code:", recall_at_k(code_questions, context_index, old_docmap))
# print("docs:", recall_at_k(docs_questions, context_index, old_docmap))
# print("\nFULL HEADING")
# print("code:", recall_at_k(code_questions, heading_index, old_docmap))
# print("docs:", recall_at_k(docs_questions, heading_index, old_docmap))

# print("\nDEDUP HEADING")
# print("code:", recall_at_k(code_questions, dedup_heading_index, old_docmap))
# print("docs:", recall_at_k(docs_questions, dedup_heading_index, old_docmap))


# for question in docs_questions:
#     old_hit = hit_at_k(question, old_index, old_docmap, k=5)
#     context_hit = hit_at_k(question, context_index, old_docmap, k=5)

#     if old_hit != context_hit:
#         print("OLD:", old_hit, "CONTEXT:", context_hit)
#         print(question["question"])
#         print()


# path = "data/raw/vllm-0.10.1/docs/features/spec_decode.md"

# content = open(path, "r", encoding="utf-8").read()

# start = 5027
# end = 5352

# print(content[start - 1000:end + 300])
# for chunk_id, source in old_docmap.items():
#     if source["file_path"].endswith("spec_decode.md"):
#         start = source["first_character_index"]

#         if 3500 <= start <= 5500:
#             print(
#                 source["first_character_index"],
#                 source["last_character_index"],
#                 repr(source["content"][:150])
#             )

# source = old_docmap[
#     "data/raw/vllm-0.10.1/docs/features/spec_decode.md::5027_5352"
# ]

# normal_tokens = tokenize_text(
#     source["content"],
#     use_stemming=USE_STEMMING,
#     remove_stopwords=REMOVE_STOPWORDS
# )

# with_heading_tokens = tokenize_text(
#     "## Speculating using MLP speculators\n" + source["content"],
#     use_stemming=USE_STEMMING,
#     remove_stopwords=REMOVE_STOPWORDS
# )

# question_text = (
#     "What is the current limitation when using MLP speculators "
#     "for speculative decoding in vLLM?"
# )

# query_tokens = tokenize_text(
#     question_text,
#     use_stemming=USE_STEMMING,
#     remove_stopwords=REMOVE_STOPWORDS
# )

# import copy

# test_corpus = copy.deepcopy(old_corpus)
# chunk_id = "data/raw/vllm-0.10.1/docs/features/spec_decode.md::5027_5352"

# test_corpus[chunk_id] = with_heading_tokens
# test_index = BM25Index(k1=0.8, b=1.0)
# test_index.build(test_corpus)
# results = test_index.search(query_tokens, k=10)

# for rank, (doc_id, score) in enumerate(results, start=1):
#     if doc_id == chunk_id:
#         print("Relevant rank:", rank)
#         print("Score:", score)

# print("QUERY TOKENS:")
# print(query_tokens)

# results = old_index.search(query_tokens, k=10)

# for rank, (chunk_id, score) in enumerate(results, start=1):
#     source = old_docmap[chunk_id]

#     print("\n" + "=" * 80)
#     print("RANK:", rank)
#     print("SCORE:", score)
#     print("CHUNK:", chunk_id)
#     print("LENGTH:", len(source["content"]))
#     print(source["content"][:1000])


# question = code_questions[0]
def reference_is_covered(question, docmap):
    reference = question["sources"][0]

    ref_file = reference["file_path"]
    ref_start = reference["first_character_index"]
    ref_end = reference["last_character_index"]

    for source in docmap.values():
        if source["file_path"] == ref_file:
            if ranges_overlap(
                ref_start,
                ref_end,
                source["first_character_index"],
                source["last_character_index"],
            ):
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


# for question in code_questions:
#     if (not hit_at_k(question, index, docmap, k=5)
#         and reference_is_covered(question, docmap)):
#         break

# print("Question:", question["question"])

# reference = question["sources"][0]

# ref_file = reference["file_path"]
# ref_start = reference["first_character_index"]
# ref_end = reference["last_character_index"]
# query_tokens = tokenize_text(
#                 question["question"],
#                 use_stemming=USE_STEMMING,
#                 remove_stopwords=REMOVE_STOPWORDS
#             )
# results = index.search(query_tokens, k=1000)
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

# print("Query tokens:")
# print(query_tokens)

# from src.indexer import tf_idf, vector_magnitude, dot_product, cosine_similarity


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
    query_tokens = tokenize_text(
        question["question"],
        use_stemming=USE_STEMMING,
        remove_stopwords=REMOVE_STOPWORDS,
    )
    results = index.search(query_tokens, k=k)
    for rank, (chunk_id, score) in enumerate(results, start=1):
        source = docmap[chunk_id]

        if source["file_path"] == ref_file:
            if ranges_overlap(
                ref_start,
                ref_end,
                source["first_character_index"],
                source["last_character_index"],
            ):
                return rank
    return None


# targets = {
#     "What is the current limitation when using MLP speculators for speculative decoding in vLLM?",
#     "Where can I find a complete example of structured outputs in vLLM online serving?"
# }

# for question in docs_questions:
#     if question["question"] in targets:
#         print(question["question"])
#         print("baseline:", relevant_rank(question, old_index, old_docmap))
#         print("context:", relevant_rank(question, context_index, old_docmap))
#         print()

# question_text = (
#     "Where can I find a complete example of structured outputs "
#     "in vLLM online serving?"
# )

# for question in docs_questions:
#     if question["question"] == question_text:
#         q = question
#         break

# query_tokens = tokenize_text(
#     q["question"],
#     use_stemming=USE_STEMMING,
#     remove_stopwords=REMOVE_STOPWORDS
# )

# for name, index in [
#     ("BASELINE", old_index),
#     ("CONTEXT_BASELINE_IDF", context_index),
# ]:
#     print("\n---", name, "---")

#     for rank, (doc_id, score) in enumerate(
#         index.search(query_tokens, k=7),
#         start=1
#     ):
#         print(rank, round(score, 3), doc_id)

# competitor_id = (
#     "data/raw/vllm-0.10.1/docs/features/"
#     "structured_outputs.md::343_540"
# )

# source = old_docmap[competitor_id]

# full_content = open(
#     source["file_path"],
#     "r",
#     encoding="utf-8"
# ).read()

# heading = find_nearest_heading(
#     full_content,
#     source["first_character_index"]
# )

# print("HEADING:")
# print(repr(heading))

# print("\nCONTENT:")
# print(repr(source["content"]))

# print("\nBODY TOKENS:")
# print(old_corpus[competitor_id])

# print("\nSEARCH TOKENS:")
# print(context_search_corpus[competitor_id])

# added = [
#     token
#     for token in context_search_corpus[competitor_id]
#     if token not in old_corpus[competitor_id]
# ]

# print("\nADDED:")
# print(added)

# print("OLD RANK:")
# print(relevant_rank(q, old_index, old_docmap))

# print("HEADING RANK:")
# print(relevant_rank(q, heading_index, old_docmap))

# query_tokens = tokenize_text(
#     q["question"],
#     use_stemming=USE_STEMMING,
#     remove_stopwords=REMOVE_STOPWORDS
# )

# for name, index in [
#     ("OLD", old_index),
#     ("HEADING", heading_index)
# ]:
#     print("\n---", name, "---")

#     results = index.search(query_tokens, k=10)

#     for rank, (chunk_id, score) in enumerate(results, start=1):
#         print(rank, score, chunk_id)
#         print(old_docmap[chunk_id]["content"][:300])
#         print()

# quark_question = None

# for question in docs_questions:
#     if "Quark quantized model" in question["question"]:

#         quark_question = question

#         break

# for b in [0.0, 0.25, 0.5, 0.75, 1.0]:

#     index = BM25Index(k1=0.8, b=b)
#     index.build(corpus)

#     rank = relevant_rank(quark_question, index, docmap, k=1000)

#     print(f"{b} | {rank}")

# covered_miss_ranks = []


# for question in docs_questions:
#     if (
#         not hit_at_k(question, index, docmap, k=5)
#         and reference_is_covered(question, docmap)
#     ):
#         rank = relevant_rank(question, index, docmap, k=1000)
#         covered_miss_ranks.append(rank)
#         if not rank:
#             continue
#         if 6 <= rank <= 10:
#             reference = question["sources"][0]
#             ref_file = reference["file_path"]
#             ref_start = reference["first_character_index"]
#             ref_end = reference["last_character_index"]
#             print("Q:", question["question"])
#             print("Relevant rank:", rank)
#             query_tokens = tokenize_text(
#                 question["question"],
#                 use_stemming=USE_STEMMING,
#                 remove_stopwords=REMOVE_STOPWORDS
#             )
#             results = index.search(query_tokens, k=10)
#             for i, (chunk_id, score) in enumerate(results, start=1):
#                 source = docmap[chunk_id]

#                 if source["file_path"] == ref_file:
#                     if ranges_overlap(ref_start, ref_end, source["first_character_index"], source["last_character_index"]):
#                         print("Relevant result:")
#                         print(f"{docmap[chunk_id]["content"]}")
#                         print(" rank:", i)
#                         print(" score:", score)
#                         print(" chunk:", chunk_id)

#             print("Top 5:")
#             for i, (chunk_id, score) in enumerate(results[:5], start=1):
#                 if i == 1:
#                     print(f"{docmap[chunk_id]["content"]}")
#                 print(i, score, chunk_id)

# buckets = {
#     "6-10": 0,
#     "11-20": 0,
#     "21-50": 0,
#     "51-100": 0,
#     "101-1000": 0,
#     "None": 0,
# }

# for rank in covered_miss_ranks:
#     if rank is None:
#         buckets["None"] += 1
#     elif rank <= 10:
#         buckets["6-10"] += 1
#     elif rank <= 20:
#         buckets["11-20"] += 1
#     elif rank <= 50:
#         buckets["21-50"] += 1
#     elif rank <= 100:
#         buckets["51-100"] += 1
#     elif rank <= 1000:
#         buckets["101-1000"] += 1

# print(buckets)

# print("Total:", sum(buckets.values()))

# for chunk_id, source in docmap.items():
#     if source["file_path"].endswith("supported_models.md"):
#         if 12000 <= source["first_character_index"] <= 15000:
#             print(
#                 source["first_character_index"],
#                 source["last_character_index"],
#                 repr(source["content"][:100])
#             )


# path = (
#     "data/raw/vllm-0.10.1/docs/features/"
#     "structured_outputs.md"
# )

# path = (
#     "data/raw/vllm-0.10.1/docs/features/"
#     "spec_decode.md"
# )

# for chunk_id, source in old_docmap.items():
#     if source["file_path"] != path:
#         continue

#     if 3900 <= source["first_character_index"] <= 5400:
#         print(
#             source["first_character_index"],
#             source["last_character_index"],
#             repr(source["content"][:200])
#         )

# spec_chunks = [
#     (chunk_id, source)
#     for chunk_id, source in old_docmap.items()
#     if source["file_path"].endswith("spec_decode.md")
# ]

# spec_chunks.sort(
#     key=lambda item: item[1]["first_character_index"]
# )
# selective_heading_corpus = {}

# markdown_files = {
#     source["file_path"]
#     for source in old_docmap.values()
#     if source["file_path"].endswith(".md")
# }

# for file_path in markdown_files:
#     file_chunks = [(chunk_id, source) for chunk_id, source in old_docmap.items() if source["file_path"] == file_path]
#     file_chunks.sort(key=lambda item: item[1]["first_character_index"])
#     full_content = open(file_path, "r", encoding="utf-8").read()
#     seen_content = False
#     for chunk_id, source in file_chunks:
#         content = source["content"]
#         chunk_tokens = tokenize_text(source["content"], use_stemming=USE_STEMMING, remove_stopwords=REMOVE_STOPWORDS)
#         headers = list(re.finditer(r"^#{1,6}\s+.+$", content, re.MULTILINE))

#         if headers:
#             tokens = chunk_tokens
#             seen_content = False
#         else:
#             if not seen_content:
#                 tokens = chunk_tokens
#                 seen_content = True
#             else:
#                 heading = find_nearest_heading(full_content, source["first_character_index"])
#                 heading_tokens = tokenize_text(heading, use_stemming=USE_STEMMING, remove_stopwords=REMOVE_STOPWORDS)
#                 new_heading_tokens = [token for token in heading_tokens if token not in chunk_tokens]
#                 tokens = new_heading_tokens + chunk_tokens

#         if tokens:
#             selective_heading_corpus[chunk_id] = tokens

# selective_search_corpus = dict(old_corpus)
# for chunk_id, tokens in selective_heading_corpus.items():
#     if chunk_id in old_corpus:
#         selective_search_corpus[chunk_id] = tokens

# print(len(old_corpus))
# print(len(selective_search_corpus))
# print(set(old_corpus) == set(selective_search_corpus))

# selective_index = BM25ContextIndex(
#     k1=0.8,
#     b=1.0
# )

# selective_index.build(
#     selective_search_corpus,
#     old_corpus
# )

# print("BASELINE")
# print("code:", recall_at_k(code_questions, old_index, old_docmap, k=5))
# print("docs:", recall_at_k(docs_questions, old_index, old_docmap, k=5))

# print("\nSELECTIVE")
# print("code:", recall_at_k(code_questions, selective_index, old_docmap, k=5))
# print("docs:", recall_at_k(docs_questions, selective_index, old_docmap, k=5))

# for question in docs_questions:
#     if question["question"] in targets:
#         print(question["question"])
#         print("baseline:", relevant_rank(question, old_index, old_docmap))
#         print("selective:", relevant_rank(question, selective_index, old_docmap))
#         print()


# for question in docs_questions:
#     old_hit = hit_at_k(
#         question,
#         old_index,
#         old_docmap,
#         k=5
#     )

#     selective_hit = hit_at_k(
#         question,
#         selective_index,
#         old_docmap,
#         k=5
#     )

#     if old_hit != selective_hit:
#         print("OLD:", old_hit, "SELECTIVE:", selective_hit)
#         print(question["question"])
#         print()


# chunks_by_file = group_chunks_by_file(old_docmap)

# spec_chunks = chunks_by_file[
#     "data/raw/vllm-0.10.1/docs/features/spec_decode.md"
# ]

# for chunk_id, source in spec_chunks:
#     start = source["first_character_index"]

#     if 3940 <= start <= 4000:
#         print("\n\n")
#         print(start, source["last_character_index"])

# extra_ids = set(final_corpus) - set(old_corpus)

# print("extra:", len(extra_ids))

# for chunk_id in list(extra_ids)[:10]:
#     source = old_docmap[chunk_id]

#     body_tokens = tokenize_text(
#         source["content"],
#         use_stemming=USE_STEMMING,
#         remove_stopwords=REMOVE_STOPWORDS
#     )

#     print(
#         chunk_id,
#         "body_tokens =", body_tokens,
#         "content =", repr(source["content"][:80])
#     )

# print("old:", len(old_corpus))
# print("final:", len(final_corpus))
# print("same IDs:", set(old_corpus) == set(final_corpus))

# different = []

# for chunk_id in final_corpus:
#     if final_corpus[chunk_id] != selective_search_corpus[chunk_id]:
#         different.append(chunk_id)

# print("different chunks:", len(different))


def group_chunks_by_file(docmap):
    chunks_by_file = defaultdict(list)

    for chunk_id, source in docmap.items():
        chunks_by_file[source["file_path"]].append((chunk_id, source))
    for chunks in chunks_by_file.values():
        chunks.sort(key=lambda item: item[1]["first_character_index"])
    return chunks_by_file


def build_search_corpus(docmap):
    corpus = {}
    chunks_by_file = group_chunks_by_file(docmap)

    for file_path, chunks in chunks_by_file.items():

        if file_path.endswith(".py"):
            for chunk_id, source in chunks:
                content = source["content"]
                chunk_tokens = tokenize_text(
                    content,
                    use_stemming=USE_STEMMING,
                    remove_stopwords=REMOVE_STOPWORDS,
                )
                if chunk_tokens:
                    corpus[chunk_id] = chunk_tokens

        elif file_path.endswith(".md"):
            seen_content = False
            with open(file_path, "r", encoding="utf-8") as f:
                full_content = f.read()
            for chunk_id, source in chunks:
                content = source["content"]
                chunk_tokens = tokenize_text(
                    content,
                    use_stemming=USE_STEMMING,
                    remove_stopwords=REMOVE_STOPWORDS,
                )
                if not chunk_tokens:
                    continue
                headers = list(
                    re.finditer(r"^#{1,6}\s+.+$", content, re.MULTILINE)
                )

                if headers:
                    tokens = chunk_tokens
                    seen_content = False
                else:
                    if not seen_content:
                        tokens = chunk_tokens
                        seen_content = True
                    else:
                        heading = find_nearest_heading(
                            full_content, source["first_character_index"]
                        )
                        heading_tokens = tokenize_text(
                            heading,
                            use_stemming=USE_STEMMING,
                            remove_stopwords=REMOVE_STOPWORDS,
                        )
                        new_heading_tokens = [
                            token
                            for token in heading_tokens
                            if token not in chunk_tokens
                        ]
                        tokens = new_heading_tokens + chunk_tokens

                if tokens:
                    corpus[chunk_id] = tokens

    return corpus


body_corpus = {
    chunk_id: tokens
    for chunk_id, source in old_docmap.items()
    if (
        tokens := tokenize_text(
            source["content"],
            use_stemming=USE_STEMMING,
            remove_stopwords=REMOVE_STOPWORDS,
        )
    )
}

INDEX_DIR = os.path.join(PROJECT_ROOT, PROC_DIR)
DOCMAP_PATH_STR = os.path.join(INDEX_DIR, "docmap.json")
os.makedirs(INDEX_DIR, exist_ok=True)

with open(DOCMAP_PATH_STR, "w", encoding="utf-8") as f:
    json.dump(old_docmap, f)

# with open(DOCMAP_PATH_STR, "r", encoding="utf-8") as f:
#     loaded_docmap = json.load(f)

# print(len(old_docmap))
# print(len(loaded_docmap))
# print(old_docmap == loaded_docmap)

search_corpus = build_search_corpus(old_docmap)

final_index = BM25ContextIndex(k1=0.8, b=1.0)
final_index.build(search_corpus, body_corpus)

INDEX_DIR = os.path.join(PROJECT_ROOT, PROC_DIR)
INDEX_PATH_STR = os.path.join(INDEX_DIR, "bm25_index.json")
os.makedirs(INDEX_DIR, exist_ok=True)
final_index.save(INDEX_PATH_STR)

# print("exists:", os.path.exists(INDEX_PATH_STR))
# print("size:", os.path.getsize(INDEX_PATH_STR))
# with open(INDEX_PATH_STR, "r", encoding="utf-8") as f:
#     data = json.load(f)

# print(data.keys())
# print(data["k1"])
# print(data["b"])
# print(data["avgdl"])
# print(len(data["idf"]))
# print(len(data["doc_lengths"]))
# print(len(data["inverted_index"]))
# print(len(body_corpus))
# print(len(search_corpus))
# print(body_corpus.keys() == search_corpus.keys())
# print()

print("code:", recall_at_k(code_questions, final_index, old_docmap, k=5))
print("docs:", recall_at_k(docs_questions, final_index, old_docmap, k=5))

runtime_index = BM25ContextIndex.load(INDEX_PATH_STR)

with open(DOCMAP_PATH_STR, "r", encoding="utf-8") as f:
    runtime_docmap = json.load(f)

query = "What is the current limitation when using MLP speculators for speculative decoding in vLLM?"

query_tokens = tokenize_text(
    query, use_stemming=USE_STEMMING, remove_stopwords=REMOVE_STOPWORDS
)

from src.augmentation import build_context, format_context, build_messages

results = runtime_index.search(query_tokens, k=5)

sources = build_context(results, runtime_docmap)

# for source in sources:
#     print(source.keys())

context_text = format_context(sources)
# print(context_text)


# for chunk_id, score in results:
#     source = runtime_docmap[chunk_id]

#     print("\nSCORE:", score)
#     print("FILE:", source["file_path"])
#     print(
#         "RANGE:",
#         source["first_character_index"],
#         source["last_character_index"]
#     )
#     print("CONTENT:")
#     print(source["content"])
# print(loaded_index.k1)
# print(loaded_index.b)
# print(loaded_index.avgdl)
# print(len(loaded_index.idf))
# print(len(loaded_index.doc_lengths))
# print(len(loaded_index.inverted_index))

messages = build_messages(query, context_text)

# query_tokens = tokenize_text(
#     query,
#     use_stemming=USE_STEMMING,
#     remove_stopwords=REMOVE_STOPWORDS
# )

# original_results = final_index.search(query_tokens, k=5)
# loaded_results = loaded_index.search(query_tokens, k=5)

# print("same results:", original_results == loaded_results)

# print("\nOriginal:")
# for result in original_results:
#     print(result)

# print("\nLoaded:")
# for result in loaded_results:
#     print(result)
