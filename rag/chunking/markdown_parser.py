"""Heading-aware Markdown parser for RAG chunking.

The parser preserves YAML front matter, extracts ATX headings, and builds section
objects primarily from H2 boundaries. Headings inside fenced code blocks are
ignored so structural parsing remains stable and deterministic.
"""

from __future__ import annotations

import re
from pathlib import Path

from rag.chunking.metadata import (
    DocumentMetadata,
    MarkdownHeading,
    MarkdownSection,
    ParsedMarkdownDocument,
)

_FRONT_MATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
_HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")


def parse_markdown(source: str, text: str) -> ParsedMarkdownDocument:
    """Parse Markdown text into metadata, headings, and H2 sections."""
    raw_front_matter, front_matter, body = _extract_front_matter(text)
    headings = tuple(_extract_headings(body))
    sections = tuple(_extract_h2_sections(body, headings))

    first_h1 = next((heading.title for heading in headings if heading.level == 1), None)
    source_path = Path(source)
    title = str(front_matter.get("title") or first_h1 or _title_from_stem(source_path))
    domain = str(front_matter.get("domain") or source_path.parent.name)
    tags_raw = front_matter.get("tags", [])
    tags = tuple(str(tag) for tag in tags_raw) if isinstance(tags_raw, list) else ()

    metadata = DocumentMetadata(
        source=source,
        title=title,
        domain=domain,
        tags=tags,
        front_matter=front_matter,
        raw_front_matter=raw_front_matter,
    )
    return ParsedMarkdownDocument(
        metadata=metadata,
        body=body,
        headings=headings,
        h2_sections=sections,
    )


def parse_markdown_path(path: Path) -> ParsedMarkdownDocument:
    """Read and parse a Markdown file from disk."""
    text = path.read_text(encoding="utf-8")
    return parse_markdown(path.as_posix(), text)


def _extract_front_matter(text: str) -> tuple[str, dict[str, object], str]:
    """Return raw front matter, parsed metadata, and body without front matter."""
    match = _FRONT_MATTER_PATTERN.match(text)
    if not match:
        return "", {}, text

    raw_front_matter = match.group(0).strip()
    parsed = _parse_front_matter_block(match.group(1))
    body = text[match.end() :]
    return raw_front_matter, parsed, body


def _parse_front_matter_block(raw: str) -> dict[str, object]:
    """Parse simple YAML front matter values used by this project schema."""
    result: dict[str, object] = {}
    current_key: str | None = None
    current_list: list[str] | None = None

    for line in raw.splitlines():
        if line.startswith("  - ") and current_list is not None:
            current_list.append(line[4:].strip().strip('"'))
            continue

        if ":" not in line or line.startswith(" "):
            continue

        if current_key is not None and current_list is not None:
            result[current_key] = current_list
            current_key = None
            current_list = None

        key, _, raw_value = line.partition(":")
        key = key.strip()
        value = raw_value.strip()

        if value == "":
            current_key = key
            current_list = []
            continue

        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1]
            result[key] = [
                item.strip().strip('"') for item in inner.split(",") if item.strip()
            ]
            continue

        if value.lower() == "true":
            result[key] = True
            continue

        if value.lower() == "false":
            result[key] = False
            continue

        result[key] = value.strip('"')

    if current_key is not None and current_list is not None:
        result[current_key] = current_list

    return result


def _extract_headings(markdown_body: str) -> list[MarkdownHeading]:
    """Extract ATX headings while ignoring headings in fenced code blocks."""
    headings: list[MarkdownHeading] = []
    in_fence = False
    fence_char = ""
    lines = markdown_body.splitlines()

    for line_number, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        if _is_fence_delimiter(stripped):
            marker = stripped[0]
            if not in_fence:
                in_fence = True
                fence_char = marker
            elif marker == fence_char:
                in_fence = False
            continue

        if in_fence:
            continue

        match = _HEADING_PATTERN.match(line)
        if not match:
            continue

        level = len(match.group(1))
        title = match.group(2).strip()
        headings.append(
            MarkdownHeading(level=level, title=title, line_number=line_number)
        )

    return headings


def _extract_h2_sections(
    markdown_body: str, headings: tuple[MarkdownHeading, ...]
) -> list[MarkdownSection]:
    """Split a document into sections using H2 boundaries as primary chunk units."""
    lines = markdown_body.splitlines()
    h2_headings = [heading for heading in headings if heading.level == 2]

    if not h2_headings:
        heading = next((item.title for item in headings if item.level == 1), "Document")
        content = markdown_body.strip()
        if not content:
            return []
        return [
            MarkdownSection(
                heading=heading,
                level=2,
                content=content,
                start_line=1,
                end_line=len(lines),
            )
        ]

    sections: list[MarkdownSection] = []
    preface = "\n".join(lines[: h2_headings[0].line_number - 1]).strip()

    for index, heading in enumerate(h2_headings):
        start_line = heading.line_number + 1
        end_line = (
            h2_headings[index + 1].line_number - 1
            if index + 1 < len(h2_headings)
            else len(lines)
        )
        section_text = "\n".join(lines[start_line - 1 : end_line]).strip()

        if index == 0 and preface:
            section_text = (
                f"{preface}\n\n{section_text}".strip() if section_text else preface
            )

        sections.append(
            MarkdownSection(
                heading=heading.title,
                level=2,
                content=section_text,
                start_line=start_line,
                end_line=end_line,
            )
        )

    return sections


def _is_fence_delimiter(stripped_line: str) -> bool:
    """Return True for Markdown fenced-code delimiters using ``` or ~~~."""
    if len(stripped_line) < 3:
        return False
    marker = stripped_line[0]
    if marker not in {"`", "~"}:
        return False
    return stripped_line.startswith(marker * 3)


def _title_from_stem(path: Path) -> str:
    """Build a fallback title from a filename stem."""
    return path.stem.replace("_", " ").strip().title()
