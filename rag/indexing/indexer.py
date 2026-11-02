"""Build and persist a local FAISS index for PoultryGuard AI."""

from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

from rag.chunking.chunker import MarkdownChunker
from rag.embeddings import SentenceTransformerEncoder


class KnowledgeBaseIndexer:
    """Chunk Markdown documents, embed them, and build a FAISS index."""

    def __init__(
        self,
        knowledge_base_dir: str | Path = "knowledge_base",
        index_dir: str | Path = "vector_store",
        encoder: SentenceTransformerEncoder | None = None,
    ) -> None:
        self.knowledge_base_dir = Path(knowledge_base_dir)
        self.index_dir = Path(index_dir)
        self.chunker = MarkdownChunker()
        self.encoder = encoder or SentenceTransformerEncoder()

    def build(self) -> dict[str, int | str]:
        """Build an index and save it with metadata and chunk IDs."""
        if not self.knowledge_base_dir.is_dir():
            raise FileNotFoundError(
                f"Knowledge-base directory not found: {self.knowledge_base_dir}"
            )

        documents = sorted(self.knowledge_base_dir.rglob("*.md"))
        documents = [path for path in documents if path.name.lower() != "readme.md"]

        if not documents:
            raise ValueError(
                f"No Markdown documents found in {self.knowledge_base_dir}"
            )

        chunks = []
        for document in documents:
            chunks.extend(self.chunker.chunk_path(document))

        if not chunks:
            raise ValueError("No chunks were generated from the knowledge base.")

        batch = self.encoder.encode_chunks(chunks)
        vectors = np.ascontiguousarray(batch.vectors, dtype=np.float32)

        # Embeddings are normalised, so inner product gives cosine similarity.
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)

        self.index_dir.mkdir(parents=True, exist_ok=True)

        index_path = self.index_dir / "poultryguard.faiss"
        metadata_path = self.index_dir / "metadata.json"

        faiss.write_index(index, str(index_path))

        records = [
            {
                "chunk_id": chunk.id,
                "text": chunk.text,
                "source": chunk.source,
                "section": chunk.section,
                "domain": chunk.domain,
                "chunk_index": chunk.chunk_index,
                "section_index": chunk.section_index,
                "word_count": chunk.word_count,
                "char_count": chunk.char_count,
                "metadata": dict(chunk.metadata),
            }
            for chunk in chunks
        ]

        metadata_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return {
            "documents": len(documents),
            "chunks": len(chunks),
            "dimensions": vectors.shape[1],
            "index_path": str(index_path),
            "metadata_path": str(metadata_path),
        }
