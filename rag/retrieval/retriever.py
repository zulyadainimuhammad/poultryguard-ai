"""Semantic retrieval from the local PoultryGuard AI knowledge base."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from rag.embeddings import SentenceTransformerEncoder


class KnowledgeBaseRetriever:
    """Retrieve relevant knowledge chunks using a local FAISS index."""

    def __init__(
        self,
        index_path: str | Path = "vector_store/poultryguard.faiss",
        metadata_path: str | Path = "vector_store/metadata.json",
        encoder: SentenceTransformerEncoder | None = None,
    ) -> None:
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        self.encoder = encoder or SentenceTransformerEncoder()
        self._index: Any = None
        self._records: list[dict[str, Any]] | None = None

    def _load(self) -> None:
        """Load the index and metadata once, when first needed."""
        if not self.index_path.is_file():
            raise FileNotFoundError(
                f"FAISS index not found: {self.index_path}. "
                "Build the knowledge-base index first."
            )

        if not self.metadata_path.is_file():
            raise FileNotFoundError(f"Metadata file not found: {self.metadata_path}.")

        if self._index is None:
            self._index = faiss.read_index(str(self.index_path))

        if self._records is None:
            self._records = json.loads(self.metadata_path.read_text(encoding="utf-8"))

        if self._index.ntotal != len(self._records):
            raise ValueError(
                "Index/metadata mismatch: "
                f"{self._index.ntotal} vectors but "
                f"{len(self._records)} metadata records."
            )

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Return the most similar chunks for a non-empty query."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        self._load()

        assert self._index is not None
        assert self._records is not None

        query_vectors = self.encoder._load_model().encode(
            [query.strip()],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        query_vector = np.ascontiguousarray(query_vectors, dtype=np.float32)

        if query_vector.shape[1] != self._index.d:
            raise ValueError(
                f"Query embedding dimension {query_vector.shape[1]} "
                f"does not match index dimension {self._index.d}."
            )

        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(query_vector, k)

        results: list[dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0], strict=True):
            if idx < 0:
                continue

            record = dict(self._records[int(idx)])
            record["score"] = float(score)
            results.append(record)

        return results
