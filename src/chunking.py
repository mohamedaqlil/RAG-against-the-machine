import os, pathlib
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
print("Oversized chunks:", res)

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

query = "KV cache manager"

query_tokens = tokenize_text(query)

print("query tokens:", query_tokens)

results = index.search(query_tokens, k=5)

for chunk_id, score in results:
    print("\nSCORE:", score)
    print("CHUNK:", chunk_id)
    print(docmap[chunk_id]["content"][:500])
