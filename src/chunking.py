"""Discover and chunk Python and Markdown source files."""

import ast
import re
from pathlib import Path

from src.models import MinimalSource

IGNORED_DIRS = {"__pycache__", ".git", ".venv", ".mypy_cache"}


def file_discovery(raw_dir: Path) -> list[Path]:
    """Discover supported source files while skipping ignored directories."""
    paths = []
    for path in raw_dir.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix in {".py", ".md"}:
            paths.append(path)
    return paths


def pack_paragraphs(
    paragraphs: list[tuple[int, int]], threshold: int = 2000
) -> list[tuple[int, int]]:
    """Pack adjacent paragraph ranges into chunks within the size threshold."""
    res: list[tuple[int, int]] = []
    current_start: int | None = None
    current_end: int | None = None

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
            if current_end is not None:
                res.append((current_start, current_end))
            current_start = paragraph_start
            current_end = paragraph_end

    # What chunk is still waiting here after the loop?
    if current_start is not None and current_end is not None:
        res.append((current_start, current_end))

    return res


def chunk_markdown(
        paths: list[Path],
        threshold: int = 2000,
) -> list[MinimalSource]:
    """Chunk Markdown files using headings and paragraph boundaries."""
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
                    chunk = content[headers[i].start(): len(content)]
                else:
                    start_index = headers[i].start()
                    end_index = headers[i + 1].start()
                    chunk = content[headers[i].start(): headers[i + 1].start()]

                if len(chunk) > threshold:
                    paragraph_ranges: list[tuple[int, int]] = []
                    chunks = chunk.split("\n\n")
                    offset = headers[i].start()
                    for c in chunks:
                        start_index = offset
                        paragraph_start = offset
                        end_index = offset + len(c)
                        offset = end_index + len("\n\n")
                        if not c:
                            continue
                        if len(c) > threshold:
                            if paragraph_ranges:
                                packed_ranges = pack_paragraphs(
                                    paragraph_ranges,
                                    threshold=threshold,
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

                            paragraph_ranges.append((start_index, end_index))
                    if paragraph_ranges:
                        packed_ranges = pack_paragraphs(
                            paragraph_ranges,
                            threshold=threshold,
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


def pack_statements(
    stmts: list[ast.stmt],
    content: str,
    line_offset: list[int],
    lines: list[str],
    path: Path,
    threshold: int = 2000,
) -> list[tuple[int, int]]:
    """Pack Python statement ranges into chunks within the size threshold."""
    sub_chunks: list[tuple[int, int]] = []
    current_texts: list[str] = []
    current_start: int | None = None
    current_end: int | None = None

    for stmt in stmts:
        if stmt.end_lineno is None:
            continue

        stmt_start = line_offset[stmt.lineno - 1]
        stmt_end = line_offset[stmt.end_lineno - 1] + len(
            lines[stmt.end_lineno - 1]
        )
        stmt_txt = content[stmt_start:stmt_end]
        stmt_size = len(stmt_txt)
        if stmt_size > threshold:
            if hasattr(stmt, "body"):
                if (
                    current_texts
                    and current_start is not None
                    and current_end is not None
                ):
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
                if (
                    current_texts
                    and current_start is not None
                    and current_end is not None
                ):
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
                continue
            else:
                continue

        if (
            current_texts
            and current_start is not None
            and current_end is not None
            and (stmt_end - current_start) > threshold
        ):
            sub_chunks.append((current_start, current_end))
            current_texts = []
        if not current_texts:
            current_start = stmt_start

        current_end = stmt_end
        current_texts.append(stmt_txt)

    if current_texts and current_start is not None and current_end is not None:
        sub_chunks.append((current_start, current_end))
    return sub_chunks


def chunk_py(paths: list[Path], threshold: int = 2000) -> list[MinimalSource]:
    """Chunk Python files using top-level AST definitions and statements."""
    chunks_out: list[MinimalSource] = []
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
                    (
                        ast.FunctionDef,
                        ast.ClassDef,
                        ast.AsyncFunctionDef,
                    ),
                ):
                    if node.end_lineno is None:
                        continue

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
                    else:
                        chunks_out.append(
                            MinimalSource(
                                file_path=str(path),
                                first_character_index=start_index,
                                last_character_index=end_index,
                            )
                        )
    return chunks_out
