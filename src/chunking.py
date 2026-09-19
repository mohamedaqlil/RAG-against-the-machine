import os, pathlib
from pathlib import Path, PosixPath
import re
from src.models import MinimalSource
import ast


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
                        if len(c) > 2000:
                            small_chunks = c.split("\n")
                            for c in small_chunks:
                                start_index = offset
                                end_index = offset + len(c)
                                offset = end_index + len("\n")
                                chunks_out.append(MinimalSource(
                                    file_path=str(path),
                                    first_character_index=start_index,
                                    last_character_index=end_index
                                ))

                        else:
                            start_index = offset
                            end_index = offset + len(c)
                            offset = end_index + len("\n\n")

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
            print(repr(content[382:383]))
    return chunks_out
                    # print(f"OVERSIZED: {path} chunk is {len(chunk)} chars")

        # print(f"chunk length: {len(chunk)}")
        # print(f"chunk {i+1}: {chunk}")
    #     print(content[item.span()[0]: item.span()[1]])
        # print(f"{path.name}: {item.start()} [{item.span()[0]}: {item.span()[1]}]")
        # for c in item.group():
        #     print(c)

def pack_statements(stmts, content, line_offset, lines, threshold=2000):
    sub_chunks = []
    current_texts = []
    current_size = 0

    for stmt in stmts:
        stmt_start = line_offset[stmt.lineno - 1]
        stmt_end = line_offset[stmt.end_lineno - 1] + len(lines[stmt.end_lineno - 1])
        stmt_txt = content[stmt_start:stmt_end]
        stmt_size = len(stmt_txt)
        # stmt_name = getattr(stmt, 'name', 'Unnamed')
        if stmt_size > threshold:
            if hasattr(stmt, "body"):
                if current_texts:
                    sub_chunks.append(current_texts)
                    current_texts = []
                    current_size = 0
                sub_chunks += pack_statements(stmt.body, content, line_offset, lines)
            if hasattr(stmt, "orelse"):
                if current_texts:
                    sub_chunks.append(current_texts)
                    current_texts = []
                    current_size = 0
                sub_chunks += pack_statements(stmt.orelse, content, line_offset, lines)
            if hasattr(stmt, "body") or hasattr(stmt, "orelse"):
                continue

        #   print(f"OVERSIZED {type(stmt).__name__}: {stmt_name} [{stmt.lineno} : {stmt.end_lineno}] in {str(path)}")

        if current_size + stmt_size > threshold and current_texts:
            sub_chunks.append(current_texts)
            current_texts = []
            current_size = 0
        current_texts.append(stmt_txt)
        current_size += stmt_size

    if current_texts:
        sub_chunks.append(current_texts)
    return sub_chunks


def chunk_py(paths):
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
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    start_index = line_offset[node.lineno - 1]
                    end_index = line_offset[node.end_lineno - 1] + len(lines[node.end_lineno - 1])

                    if (end_index - start_index + 1) > 2000:
                        sub_chunks = pack_statements(node.body, content, line_offset, lines)

                        for c in sub_chunks:
                            print("------chunk------")
                            chunk = "\n".join(c)
                            print(chunk)
                        # print(f"OVERSIZED {type(node).__name__}: {node.name} in {str(path)}")
                    chunks_out.append(MinimalSource(
                        file_path=str(path),
                        first_character_index=start_index,
                        last_character_index=end_index
                    ))
                    # for chunk in chunks_out:
                    #     print("---")
                    #     print(content[chunk.first_character_index:chunk.last_character_index])
    return chunks_out


paths = file_discovery(raw_dir)

# chunk_markdown(paths)

paths = [Path('data/raw/vllm-0.10.1/benchmarks/benchmark_serving_structured_output.py')]

chunk_py(paths)

# text = "AAAA\nBBBB\nCCCC"
# print(text.splitlines())

# tree = ast.parse(source)

# for node in ast.walk(tree):
#     if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
#         print(f"{type(node).__name__}: {node.name}, lines {node.lineno}-{node.end_lineno}")
