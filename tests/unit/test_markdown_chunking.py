"""Unit tests for the Sprint 3.1 Markdown chunking engine."""

from __future__ import annotations

from rag.chunking.chunker import MarkdownChunker
from rag.chunking.markdown_parser import parse_markdown
from rag.chunking.metadata import ChunkingConfig


def _sample_markdown() -> str:
    """Return a representative Markdown fixture with front matter and headings."""
    return """\
---
title: Chunking Sample
domain: biosecurity
tags: [biosecurity, chunking, parser]
reviewed: false
sources:
  - "FAO. (2021). Sample Source. Food and Agriculture Organization."
---

# Chunking Sample

Intro paragraph before the first H2 section.

## Overview

Overview text for the first section.

```python
## not_a_heading_inside_code
```

### Detail

Extra details under the overview section.

## Recommendations

Recommendations text for the second section.
"""


def test_parser_preserves_front_matter_and_extracts_headings() -> None:
    parsed = parse_markdown(
        "knowledge_base/biosecurity/chunking_sample.md",
        _sample_markdown(),
    )

    assert parsed.metadata.title == "Chunking Sample"
    assert parsed.metadata.domain == "biosecurity"
    assert parsed.metadata.tags == ("biosecurity", "chunking", "parser")
    assert "title: Chunking Sample" in parsed.metadata.raw_front_matter

    heading_titles = [heading.title for heading in parsed.headings]
    assert "Chunking Sample" in heading_titles
    assert "Overview" in heading_titles
    assert "Recommendations" in heading_titles
    assert "not_a_heading_inside_code" not in heading_titles

    assert [section.heading for section in parsed.h2_sections] == [
        "Overview",
        "Recommendations",
    ]


def test_chunker_uses_h2_boundaries_for_primary_chunks() -> None:
    chunker = MarkdownChunker(ChunkingConfig(chunk_size=200, chunk_overlap=20))

    chunks = chunker.chunk_text(
        "knowledge_base/biosecurity/chunking_sample.md",
        _sample_markdown(),
    )

    assert len(chunks) == 2
    assert [chunk.section for chunk in chunks] == ["Overview", "Recommendations"]


def test_chunker_splits_long_sections_with_overlap() -> None:
    words = " ".join(f"word{i}" for i in range(1, 41))
    markdown = f"""\
---
title: Overlap Test
domain: feeding
tags: [feeding, overlap, chunk]
reviewed: false
sources:
  - "FAO. (2021). Overlap Test. Food and Agriculture Organization."
---

# Overlap Test

## Key Information

{words}
"""
    chunker = MarkdownChunker(ChunkingConfig(chunk_size=12, chunk_overlap=4))
    chunks = chunker.chunk_text("knowledge_base/feeding/overlap_test.md", markdown)

    assert len(chunks) == 5

    first_body = chunks[0].text.split("\n\n", maxsplit=1)[1].split()
    second_body = chunks[1].text.split("\n\n", maxsplit=1)[1].split()
    assert first_body[-4:] == second_body[:4]


def test_chunker_preserves_source_metadata_and_ids_are_deterministic() -> None:
    source = "knowledge_base/biosecurity/chunking_sample.md"
    chunker = MarkdownChunker(ChunkingConfig(chunk_size=40, chunk_overlap=10))

    first_run = chunker.chunk_text(source, _sample_markdown())
    second_run = chunker.chunk_text(source, _sample_markdown())

    assert [chunk.id for chunk in first_run] == [chunk.id for chunk in second_run]
    assert first_run[0].metadata["source"] == source
    assert first_run[0].metadata["domain"] == "biosecurity"
    assert first_run[0].metadata["title"] == "Chunking Sample"
    assert first_run[0].metadata["tags"] == ["biosecurity", "chunking", "parser"]


def test_chunker_falls_back_when_document_has_no_h2_headings() -> None:
    markdown = """\
---
title: No H2
domain: management
tags: [management, parser, fallback]
reviewed: false
sources:
  - "FAO. (2022). No H2 Test. Food and Agriculture Organization."
---

# No H2

This document intentionally has no second-level headings.
"""
    chunker = MarkdownChunker(ChunkingConfig(chunk_size=50, chunk_overlap=10))

    chunks = chunker.chunk_text("knowledge_base/management/no_h2.md", markdown)

    assert len(chunks) == 1
    assert chunks[0].section == "No H2"
