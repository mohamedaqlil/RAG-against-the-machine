"""Semantic vector index for repository chunks."""

from collections import defaultdict
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from src.internal_types import Source


class SemanticIndex:
    """Store normalized semantic embeddings and their chunk identifiers."""

    def __init__(self, model_name: str) -> None:
        """Initialize an empty semantic index."""
        self.model_name = model_name
        self.chunk_ids: list[str] = []
        self.embeddings = np.empty((0, 0), dtype=np.float32)

    def build(
        self,
        docmap: dict[str, Source],
        model: SentenceTransformer,
    ) -> None:
        self.chunk_ids = list(docmap.keys())

        texts = [
            docmap[chunk_id]["content"]
            for chunk_id in self.chunk_ids
        ]

        self.embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        if len(self.chunk_ids) != self.embeddings.shape[0]:
            raise ValueError("Chunk IDs and embeddings are out of sync")

    def search(
            self, query: str, model: SentenceTransformer, k: int = 5,
    ) -> list[tuple[str, float]]:
        query_embedding = model.encode(
            query,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        scores = self.embeddings @ query_embedding
        sorted_ids = np.argsort(scores, descending=True)
        sorted_scores = []
        for i in sorted_ids[:k]:
            sorted_scores.append((self.chunk_ids[i], scores[i]))

        return sorted_scores

    def save(self, embeddings_path, metadata_path):
        embeddings_path = Path(embeddings_path)
        embeddings_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(embeddings_path, self.embeddings)

        metadata_path = Path(metadata_path)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "model_name": self.model_name,
            "chunk_ids": self.chunk_ids
        }
        with open(metadata_path, mode="w", encoding="utf-8") as f:
            json.dump(metadata, f)

    @classmethod
    def load(cls, embeddings_path, metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        index = cls(metadata["model_name"])

        # restore:
        index.chunk_ids = metadata["chunk_ids"]
        index.embeddings = np.load(embeddings_path)
        if len(index.chunk_ids) != index.embeddings.shape[0]:
            raise ValueError("Chunk IDs and embeddings are out of sync")

        return index

if __name__ == "__main__":
    import json
    index = SemanticIndex("all-MiniLM-L6-v2")

    # DOCMAP_PATH = "data/test_processed/docmap.json"

    # with open(DOCMAP_PATH, "r", encoding="utf-8") as f:
    #     docmap = json.load(f)

    model = SentenceTransformer("all-MiniLM-L6-v2")

    # index.build(docmap, model)

    # print("original index scores:", index.search("what is vllm?", model))
    # print("original chunk count:", len(index.chunk_ids))
    # print("original embedding shape", index.embeddings.shape)
    # print("original model name", index.model_name)

    # index.save("save_embeddings.npy", "metadata_test.json")
    loaded_index = SemanticIndex.load("save_embeddings.npy", "metadata_test.json")

    print("loaded index scores:", loaded_index.search("what is vllm?", model))
    print("loaded chunk count:", len(loaded_index.chunk_ids))
    print("loaded embedding shape", loaded_index.embeddings.shape)
    print("loaded model name", loaded_index.model_name)
    # print(index.embeddings.dtype)
    # print(np.linalg.norm(index.embeddings[0]))
