"""Markdown chunker for the PoultryGuard AI RAG pipeline.

Chunking is heading-aware and primarily based on H2 section boundaries. Sections
larger than the configured size are split with fixed overlap to reduce context
loss at chunk boundaries.
"""

from __future__ import annotations

from pathlib import Path

from rag.chunking.markdown_parser import parse_markdown, parse_markdown_path
from rag.chunking.metadata import (
    ChunkingConfig,
    MarkdownChunk,
    ParsedMarkdownDocument,
    generate_chunk_id,
)


class MarkdownChunker:
    """Convert Markdown documents into retrieval-ready chunks with metadata."""

    def __init__(self, config: ChunkingConfig | None = None) -> None:
        """Create a chunker with optional custom configuration."""
        self.config = config or ChunkingConfig()

    def chunk_text(self, source: str, text: str) -> list[MarkdownChunk]:
        """Chunk a Markdown document string."""
        document = parse_markdown(source, text)
        return self._chunk_document(document)

    def chunk_path(self, path: Path) -> list[MarkdownChunk]:
        """Chunk a Markdown document loaded from a file path."""
        document = parse_markdown_path(path)
        return self._chunk_document(document)

    def _chunk_document(self, document: ParsedMarkdownDocument) -> list[MarkdownChunk]:
        """Chunk parsed sections, then split oversized sections with overlap."""
        chunks: list[MarkdownChunk] = []
        chunk_index = 0

        for section_index, section in enumerate(document.h2_sections):
            if not section.content.strip():
                continue

            windows = self._window_text(section.content)
            for window_index, window_text in enumerate(windows):
                chunk_text = self._build_chunk_text(section.heading, window_text)
                chunk_id = generate_chunk_id(
                    source=document.metadata.source,
                    section=section.heading,
                    section_index=section_index,
                    window_index=window_index,
                    text=window_text,
                )
                metadata = dict(document.metadata.front_matter)
                metadata.update(
                    {
                        "source": document.metadata.source,
                        "section": section.heading,
                        "domain": document.metadata.domain,
                        "title": document.metadata.title,
                        "tags": list(document.metadata.tags),
                    }
                )

                chunks.append(
                    MarkdownChunk(
                        id=chunk_id,
                        text=chunk_text,
                        source=document.metadata.source,
                        section=section.heading,
                        domain=document.metadata.domain,
                        chunk_index=chunk_index,
                        section_index=section_index,
                        word_count=_word_count(window_text),
                        char_count=len(window_text),
                        metadata=metadata,
                    )
                )
                chunk_index += 1

        return chunks

    def _window_text(self, text: str) -> list[str]:
        """Split text into fixed-size windows with configurable overlap."""
        words = text.split()
        if not words:
            return []

        if len(words) <= self.config.chunk_size:
            return [" ".join(words)]

        windows: list[str] = []
        step = self.config.chunk_size - self.config.chunk_overlap
        start = 0
        while start < len(words):
            end = min(start + self.config.chunk_size, len(words))
            windows.append(" ".join(words[start:end]))
            if end >= len(words):
                break
            start += step

        return windows

    def _build_chunk_text(self, section_heading: str, body: str) -> str:
        """Build final chunk text, optionally including its H2 section heading."""
        if self.config.include_section_heading:
            return f"## {section_heading}\n\n{body}".strip()
        return body.strip()


def _word_count(text: str) -> int:
    """Return a simple whitespace-based word count."""
    return len(text.split())
