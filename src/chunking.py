import os, pathlib
from pathlib import Path
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


def chunk_py(paths):
    chunks_out = []
    for path in paths[:3]:
        if path.suffix == ".py":
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            print(ast.dump(tree, indent=4))

            # for node in tree.body:
            #     if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            #         pass
            #     print(node)
                # if len(c) > 2000:
                #     small_chunks = c.split("\n")
                #     for c in small_chunks:
                #         start_index = offset
                #         end_index = offset + len(c)
                #         offset = end_index + len("\n")
                #         chunks_out.append(MinimalSource(
                #             file_path=str(path),
                #             first_character_index=start_index,
                #             last_character_index=end_index
                #         ))

                # else:
                #     start_index = offset
                #     end_index = offset + len(c)
                #     offset = end_index + len("\n\n")

                #     chunks_out.append(MinimalSource(
                #         file_path=str(path),
                #         first_character_index=start_index,
                #         last_character_index=end_index
                #     ))
            # for node in tree.body:
            #     if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            #         print(f"{type(node).__name__}: {node.name}")
    return chunks_out


paths = file_discovery(raw_dir)

# chunk_markdown(paths)

chunk_py(paths)

# text = "AAAA\nBBBB\nCCCC"
# print(text.splitlines())

# tree = ast.parse(source)

# for node in ast.walk(tree):
#     if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
#         print(f"{type(node).__name__}: {node.name}, lines {node.lineno}-{node.end_lineno}")
