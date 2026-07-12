"""Metadata models for Markdown parsing and chunk generation.

These dataclasses define the contract between the parser and chunker modules.
They keep source-document metadata attached to every generated chunk so the
retrieval layer can preserve traceability to original knowledge base files.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkingConfig:
    """Configuration for fixed-size chunking with overlap.

    Values are word-count based to avoid tokenizer dependencies in the MVP.
    """

    chunk_size: int = 512
    chunk_overlap: int = 64
    include_section_heading: bool = True

    def __post_init__(self) -> None:
        """Validate chunk-size and overlap constraints."""
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero.")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative.")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size.")


@dataclass(frozen=True)
class MarkdownHeading:
    """A parsed ATX heading from a Markdown body."""

    level: int
    title: str
    line_number: int


@dataclass(frozen=True)
class MarkdownSection:
    """A logical section extracted from a document, primarily at H2 boundaries."""

    heading: str
    level: int
    content: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class DocumentMetadata:
    """Structured metadata extracted from YAML front matter and file context."""

    source: str
    title: str
    domain: str
    tags: tuple[str, ...]
    front_matter: dict[str, object]
    raw_front_matter: str


@dataclass(frozen=True)
class ParsedMarkdownDocument:
    """A Markdown document parsed into metadata, headings, and H2 sections."""

    metadata: DocumentMetadata
    body: str
    headings: tuple[MarkdownHeading, ...]
    h2_sections: tuple[MarkdownSection, ...]


@dataclass(frozen=True)
class MarkdownChunk:
    """A retrieval-ready chunk with source metadata and deterministic ID."""

    id: str
    text: str
    source: str
    section: str
    domain: str
    chunk_index: int
    section_index: int
    word_count: int
    char_count: int
    metadata: dict[str, object]


def generate_chunk_id(
    *,
    source: str,
    section: str,
    section_index: int,
    window_index: int,
    text: str,
) -> str:
    """Generate a deterministic chunk ID from stable chunk attributes."""
    payload = {
        "source": source,
        "section": section,
        "section_index": section_index,
        "window_index": window_index,
        "text": " ".join(text.split()),
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"chunk_{digest[:16]}"
