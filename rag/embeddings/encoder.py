
"""Local text embedding utilities for the PoultryGuard AI RAG pipeline."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sentence_transformers import SentenceTransformer

from rag.chunking.metadata import MarkdownChunk


@dataclass(frozen=True)
class EmbeddingBatch:
    """Embeddings and traceable metadata for a batch of chunks."""

    chunk_ids: tuple[str, ...]
    vectors: np.ndarray
    metadata: tuple[dict[str, object], ...]


class SentenceTransformerEncoder:
    """Generate local semantic embeddings for Markdown chunks."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        batch_size: int = 16,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name cannot be empty.")
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero.")

        self.model_name = model_name
        self.batch_size = batch_size
        self._model: SentenceTransformer | None = None

    def _load_model(self) -> SentenceTransformer:
        """Load the embedding model from the local cache only."""
        if self._model is None:
            self._model = SentenceTransformer(
                self.model_name,
                local_files_only=True,
            )
        return self._model

    def encode_chunks(
        self, chunks: list[MarkdownChunk]
    ) -> EmbeddingBatch:
        """Embed chunks and preserve their IDs and source metadata."""
        if not chunks:
            raise ValueError("chunks cannot be empty.")

        for chunk in chunks:
            if not chunk.text.strip():
                raise ValueError(f"Chunk {chunk.id!r} has empty text.")

        model = self._load_model()
        vectors = model.encode(
            [chunk.text for chunk in chunks],
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        vectors = np.asarray(vectors, dtype=np.float32)

        if vectors.ndim != 2 or vectors.shape[0] != len(chunks):
            raise ValueError("The model returned an unexpected embedding shape.")

        if not np.isfinite(vectors).all():
            raise ValueError("Embeddings contain non-finite values.")

        return EmbeddingBatch(
            chunk_ids=tuple(chunk.id for chunk in chunks),
            vectors=vectors,
            metadata=tuple(dict(chunk.metadata) for chunk in chunks),
        )
