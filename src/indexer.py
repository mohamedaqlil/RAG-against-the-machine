"""Build, persist, and query the lexical BM25 search index."""

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Self

from nltk.stem import PorterStemmer

from src.chunking import (
    chunk_markdown,
    chunk_py,
    file_discovery,
)
from src.internal_types import Source
from src.models import MinimalSource

USE_STEMMING = True


class BM25ContextIndex:
    """Represent a BM25 index over tokenized source chunks."""

    def __init__(self, k1: float = 0.8, b: float = 1.0) -> None:
        """Initialize an empty BM25 index with the given parameters."""
        self.idf: dict[str, float] = {}
        self.inverted_index: dict[str, dict[str, int]] = defaultdict(dict)
        self.doc_lengths: dict[str, int] = defaultdict(int)
        self.avgdl: float = 0.0
        self.k1: float = k1
        self.b: float = b

    def build(
        self, search_corpus: dict[str, list[str]],
        body_corpus: dict[str, list[str]]
    ) -> None:
        """Build the BM25 index from search and body corpora."""
        if search_corpus.keys() != body_corpus.keys():
            raise ValueError(
                "search_corpus and body_corpus must contain"
                "the same document IDs"
            )

        if not body_corpus:
            raise ValueError("body_corpus is empty")

        self.inverted_index = defaultdict(dict)
        self.doc_lengths = defaultdict(int)
        self.idf = bm25_inverse_document_frequency(body_corpus)

        for doc_id, tokens in search_corpus.items():
            counts = term_counts(tokens)
            self.doc_lengths[doc_id] = len(body_corpus[doc_id])
            for token, count in counts.items():
                self.inverted_index[token][doc_id] = count
        self.avgdl = sum(len(tokens) for tokens in body_corpus.values()) / len(
            body_corpus
        )

    def search(
            self, query_tokens: list[str], k: int = 5
    ) -> list[tuple[str, float]]:
        """Rank indexed chunks by BM25 score for the given query tokens."""
        scores: dict[str, float] = defaultdict(float)
        for token in query_tokens:
            for doc_id, frequency in self.inverted_index.get(
                token, {}
            ).items():
                idf = self.idf.get(token, 0.0)
                doc_length = self.doc_lengths[doc_id]
                avgdl = self.avgdl
                length_factor = 1 - self.b + (self.b * (doc_length / avgdl))
                denominator = frequency + (self.k1 * length_factor)
                numerator = frequency * (self.k1 + 1)
                scores[doc_id] += idf * (numerator / denominator)
        sorted_scores = sorted(
            scores.items(), key=lambda item: item[1], reverse=True
        )

        return sorted_scores[:k]

    def save(self, path: str | Path) -> None:
        """Persist the BM25 index as JSON."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "k1": self.k1,
            "b": self.b,
            "avgdl": self.avgdl,
            "idf": self.idf,
            "doc_lengths": dict(self.doc_lengths),
            "inverted_index": dict(self.inverted_index),
        }
        with open(output_path, mode="w", encoding="utf-8") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path: str | Path) -> Self:
        """Load a persisted BM25 index from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        index = cls(k1=data["k1"], b=data["b"])

        # restore:
        index.avgdl = data["avgdl"]
        index.idf = data["idf"]
        index.doc_lengths = data["doc_lengths"]
        index.inverted_index = data["inverted_index"]

        return index


def find_nearest_heading(content: str, chunk_start: int) -> str:
    """Find the nearest Markdown heading preceding a chunk."""
    heading = ""
    headers = list(re.finditer(r"^#{1,6}\s+.+$", content, re.MULTILINE))

    for i, header in enumerate(headers):
        if header.start() <= chunk_start:
            heading = header.group(0)
        else:
            break
    return heading


def group_chunks_by_file(
    docmap: dict[str, Source],
) -> dict[str, list[tuple[str, Source]]]:
    """Group document-map entries by their source file path."""
    chunks_by_file: dict[str, list[tuple[str, Source]]] = defaultdict(list)

    for chunk_id, source in docmap.items():
        chunks_by_file[source["file_path"]].append((chunk_id, source))
    for chunks in chunks_by_file.values():
        chunks.sort(key=lambda item: item[1]["first_character_index"])
    return chunks_by_file


def build_search_corpus(docmap: dict[str, Source]) -> dict[str, list[str]]:
    """Build the tokenized corpus used for BM25 retrieval."""
    corpus: dict[str, list[str]] = {}
    chunks_by_file = group_chunks_by_file(docmap)

    for file_path, chunks in chunks_by_file.items():

        if file_path.endswith(".py"):
            for chunk_id, source in chunks:
                content = source["content"]
                chunk_tokens = tokenize_text(
                    content,
                    use_stemming=USE_STEMMING,
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
                            full_content,
                            source["first_character_index"],
                        )
                        heading_tokens = tokenize_text(
                            heading,
                            use_stemming=USE_STEMMING,
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


def build_docmap(chunks: list[MinimalSource]) -> dict[str, Source]:
    """Build a document map containing source metadata and chunk content."""
    docmap: dict[str, Source] = {}
    for chunk in chunks:
        content = Path(chunk.file_path).read_text(encoding="utf-8")
        chunk_id = (
            f"{chunk.file_path}::"
            f"{chunk.first_character_index}_{chunk.last_character_index}"
        )
        docmap[chunk_id] = {
            "file_path": chunk.file_path,
            "first_character_index": chunk.first_character_index,
            "last_character_index": chunk.last_character_index,
            "content": content[
                chunk.first_character_index: chunk.last_character_index
            ],
        }
    return docmap


def build_body_corpus(docmap: dict[str, Source]) -> dict[str, list[str]]:
    """Build the tokenized body corpus used for BM25 statistics."""
    return {
        chunk_id: tokens
        for chunk_id, source in docmap.items()
        if (
            tokens := tokenize_text(
                source["content"],
                use_stemming=USE_STEMMING,
            )
        )
    }


def save_docmap(docmap: dict[str, Source], path: str | Path) -> Path:
    """Persist the document map as JSON and return its output path."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    json_data = json.dumps(docmap, indent=2)
    output_path.write_text(json_data, encoding="utf-8")
    return output_path


def build_index(
    raw_directory: str | Path = "data/raw",
    processed_directory: str | Path = "data/processed",
    max_chunk_size: int = 2000,
) -> tuple[Path, Path]:
    """Build and persist the BM25 index and document map."""
    raw_directory = Path(raw_directory)
    processed_directory = Path(processed_directory)
    if max_chunk_size <= 0:
        raise ValueError("max_chunk_size must be greater than 0")

    paths = file_discovery(raw_directory)

    if not paths:
        raise ValueError(
            f"No supported source files found in: {raw_directory}"
        )

    py_chunks = chunk_py(paths, threshold=max_chunk_size)
    markdown_chunks = chunk_markdown(paths, threshold=max_chunk_size)

    chunks = py_chunks + markdown_chunks

    docmap = build_docmap(chunks)

    body_corpus = build_body_corpus(docmap)
    search_corpus = build_search_corpus(docmap)

    index = BM25ContextIndex(k1=0.8, b=1.0)
    index.build(search_corpus, body_corpus)
    index_path = processed_directory / "bm25_index.json"
    docmap_path = processed_directory / "docmap.json"
    index.save(index_path)
    save_docmap(docmap, docmap_path)

    return index_path, docmap_path


def tokenize_text(
    text: str, use_stemming: bool = True
) -> list[str]:
    """Tokenize text with optional stopword removal and stemming."""
    pattern = r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)|\d+"
    tokens = re.findall(pattern, text)
    valid_tokens = []
    for token in tokens:
        if token:
            valid_tokens.append(token.lower())
    if use_stemming:
        stemmer = PorterStemmer()
        stemmed_words = []
        for word in valid_tokens:
            stemmed_words.append(stemmer.stem(word))
        valid_tokens = stemmed_words

    return valid_tokens


def term_counts(text_tokens: list[str]) -> dict[str, int]:
    """Count occurrences of each term in a tokenized document."""
    term_counter: dict[str, int] = defaultdict(int)
    for token in text_tokens:
        term_counter[token] += 1
    return dict(term_counter)


def document_frequency(corpus: dict[str, list[str]]) -> dict[str, int]:
    """Count the number of documents containing each term."""
    df: dict[str, int] = defaultdict(int)
    for text_tokens in corpus.values():
        for token in set(text_tokens):
            df[token] += 1
    return dict(df)


def bm25_inverse_document_frequency(
        corpus: dict[str, list[str]]
) -> dict[str, float]:
    """Calculate BM25 inverse document frequency for each corpus term."""
    idf: dict[str, float] = defaultdict(float)
    df = document_frequency(corpus)
    nb_docs = len(corpus)
    for term, document_count in df.items():
        idf[term] = math.log(
            1 + ((nb_docs - document_count + 0.5) / (document_count + 0.5))
        )
    return dict(idf)
