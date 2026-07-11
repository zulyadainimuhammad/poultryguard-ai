"""Build a lightweight preview of future RAG index chunks.

This script does not create embeddings or a FAISS index. It previews the H2
section-level chunks that the future RAG pipeline will index, helping reviewers
spot documents that are too short, too long, or missing useful section structure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from validate_knowledge_base import (
    KNOWLEDGE_BASE_ROOT,
    _collect_documents,
    _parse_front_matter,
)

FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)
H2_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)
WORD_PATTERN = re.compile(r"\b[\w'-]+\b")
MIN_SECTION_WORDS = 80
MAX_SECTION_WORDS = 500


@dataclass(frozen=True)
class PreviewChunk:
    """A section-level chunk that would be indexed later by the RAG pipeline."""

    source: str
    title: str
    domain: str
    section: str
    word_count: int
    char_count: int


@dataclass(frozen=True)
class IndexPreview:
    """Summary of preview chunks and non-fatal quality warnings."""

    document_count: int
    chunk_count: int
    documents_by_domain: dict[str, int]
    chunks_by_domain: dict[str, int]
    average_document_words: float
    average_chunk_words: float
    missing_metadata: dict[str, list[str]]
    duplicate_titles: dict[str, list[str]]
    duplicate_tags: dict[str, list[str]]
    confidence_distribution: dict[str, int]
    warnings: list[str]
    chunks: list[PreviewChunk]


def _remove_front_matter(text: str) -> str:
    """Remove YAML front matter from a Markdown document."""
    return FRONT_MATTER_PATTERN.sub("", text, count=1)


def _word_count(text: str) -> int:
    """Count words in a Markdown section using a lightweight regex."""
    return len(WORD_PATTERN.findall(text))


def _is_missing_metadata_value(value: object) -> bool:
    """Return True when metadata is absent or empty; false booleans are valid."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return not value
    return False


def _split_h2_sections(text: str) -> list[tuple[str, str]]:
    """Split Markdown text into H2 section title and body pairs."""
    matches = list(H2_PATTERN.finditer(text))
    sections: list[tuple[str, str]] = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(1).strip(), text[start:end].strip()))

    return sections


def build_preview(root: Path = KNOWLEDGE_BASE_ROOT) -> IndexPreview:
    """Build a section-level index preview for knowledge base documents."""
    chunks: list[PreviewChunk] = []
    warnings: list[str] = []
    documents = _collect_documents(root)
    documents_by_domain: dict[str, int] = {}
    document_word_counts: list[int] = []
    missing_metadata: dict[str, list[str]] = {}
    duplicate_tags: dict[str, list[str]] = {}
    confidence_distribution: dict[str, int] = {}
    titles_by_name: dict[str, list[str]] = {}

    for path in documents:
        text = path.read_text(encoding="utf-8")
        meta = _parse_front_matter(text) or {}
        title = str(meta.get("title", path.stem.replace("_", " ").title()))
        domain = str(meta.get("domain", path.parent.name))
        source = path.relative_to(root).as_posix()
        documents_by_domain[domain] = documents_by_domain.get(domain, 0) + 1
        titles_by_name.setdefault(title.lower(), []).append(source)

        required_fields = ("title", "domain", "tags", "reviewed", "sources")
        missing = [
            field
            for field in required_fields
            if field not in meta or _is_missing_metadata_value(meta[field])
        ]
        if missing:
            missing_metadata[source] = missing

        tags = meta.get("tags")
        if isinstance(tags, list):
            seen_tags: set[str] = set()
            duplicates: list[str] = []
            for tag in tags:
                tag_text = str(tag)
                if tag_text in seen_tags and tag_text not in duplicates:
                    duplicates.append(tag_text)
                seen_tags.add(tag_text)
            if duplicates:
                duplicate_tags[source] = duplicates

        confidence = meta.get("confidence", "missing")
        confidence_key = str(confidence)
        confidence_distribution[confidence_key] = (
            confidence_distribution.get(confidence_key, 0) + 1
        )

        markdown_body = _remove_front_matter(text)
        document_word_counts.append(_word_count(markdown_body))
        sections = _split_h2_sections(markdown_body)

        if not sections:
            warnings.append(f"{path.relative_to(root)}: no H2 sections found.")
            continue

        for section, body in sections:
            count = _word_count(body)
            chunks.append(
                PreviewChunk(
                    source=source,
                    title=title,
                    domain=domain,
                    section=section,
                    word_count=count,
                    char_count=len(body),
                )
            )

            if section != "References" and count < MIN_SECTION_WORDS:
                warnings.append(
                    f"{source} -> {section}: {count} words; target is at least "
                    f"{MIN_SECTION_WORDS} for retrieval context."
                )
            if count > MAX_SECTION_WORDS:
                warnings.append(
                    f"{source} -> {section}: {count} words; consider splitting "
                    f"before indexing."
                )

    chunks_by_domain: dict[str, int] = {}
    for chunk in chunks:
        chunks_by_domain[chunk.domain] = chunks_by_domain.get(chunk.domain, 0) + 1

    duplicate_titles = {
        title: paths for title, paths in titles_by_name.items() if len(paths) > 1
    }
    chunk_word_counts = [chunk.word_count for chunk in chunks]

    return IndexPreview(
        document_count=len(documents),
        chunk_count=len(chunks),
        documents_by_domain=dict(sorted(documents_by_domain.items())),
        chunks_by_domain=dict(sorted(chunks_by_domain.items())),
        average_document_words=round(
            sum(document_word_counts) / len(document_word_counts), 2
        )
        if document_word_counts
        else 0.0,
        average_chunk_words=round(sum(chunk_word_counts) / len(chunk_word_counts), 2)
        if chunk_word_counts
        else 0.0,
        missing_metadata=missing_metadata,
        duplicate_titles=duplicate_titles,
        duplicate_tags=duplicate_tags,
        confidence_distribution=dict(sorted(confidence_distribution.items())),
        warnings=warnings,
        chunks=chunks,
    )


def _print_text_report(preview: IndexPreview) -> None:
    """Print a human-readable preview report."""
    print("Knowledge base index preview")
    print(f"Documents: {preview.document_count}")
    print(f"Preview chunks: {preview.chunk_count}")
    print(f"Average document length: {preview.average_document_words} words")
    print(f"Average chunk size estimate: {preview.average_chunk_words} words")
    print("Documents by category:")
    for domain, count in preview.documents_by_domain.items():
        print(f"  - {domain}: {count}")
    print("Chunks by category:")
    for domain, count in preview.chunks_by_domain.items():
        print(f"  - {domain}: {count}")
    print("Confidence distribution:")
    for confidence, count in preview.confidence_distribution.items():
        print(f"  - {confidence}: {count}")

    if preview.missing_metadata:
        print("\nMissing metadata:")
        for source, fields in preview.missing_metadata.items():
            print(f"  - {source}: {', '.join(fields)}")

    if preview.duplicate_titles:
        print("\nDuplicate titles:")
        for title, sources in preview.duplicate_titles.items():
            print(f"  - {title}: {', '.join(sources)}")

    if preview.duplicate_tags:
        print("\nDuplicate tags:")
        for source, tags in preview.duplicate_tags.items():
            print(f"  - {source}: {', '.join(tags)}")

    if preview.warnings:
        print("\nWarnings:")
        for warning in preview.warnings:
            print(f"  - {warning}")


def main() -> None:
    """Build and print a knowledge base index preview."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the preview as JSON instead of a text report.",
    )
    args = parser.parse_args()

    preview = build_preview()
    if args.json:
        print(json.dumps(asdict(preview), indent=2))
    else:
        _print_text_report(preview)

    if preview.document_count == 0 or preview.chunk_count == 0:
        print("Index preview failed - no indexable knowledge base chunks found.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
