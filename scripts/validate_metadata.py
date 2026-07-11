"""Validate metadata quality for PoultryGuard AI knowledge base documents.

This validator complements ``validate_knowledge_base.py``. The base validator
checks required schema shape; this script checks higher-level metadata quality
rules from ``docs/knowledge_engineering.md``.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from validate_knowledge_base import (
    KNOWLEDGE_BASE_ROOT,
    REQUIRED_METADATA_FIELDS,
    VALID_DOMAINS,
    _collect_documents,
    _parse_front_matter,
)

TAG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_]*$")
TITLE_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)
LANGUAGE_PATTERN = re.compile(r"^[a-z]{2}$")
VALID_CONFIDENCE = frozenset({"high", "medium", "low"})
VALID_SEVERITY = frozenset({"CRITICAL", "WARNING", "INFO"})


@dataclass
class MetadataIssue:
    """A metadata quality issue found in one knowledge base document."""

    path: Path
    message: str


@dataclass
class MetadataValidationResult:
    """Aggregated metadata validation result."""

    issues: list[MetadataIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return True when no metadata quality issues were found."""
        return not self.issues

    def add(self, path: Path, message: str) -> None:
        """Record one metadata validation issue."""
        self.issues.append(MetadataIssue(path=path, message=message))


def _is_empty_value(value: object) -> bool:
    """Return True when a metadata value is missing usable content."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False


def _check_required_fields(
    path: Path,
    meta: dict[str, object],
    result: MetadataValidationResult,
) -> None:
    """Validate that required metadata fields exist and are non-empty."""
    for field_name in REQUIRED_METADATA_FIELDS:
        if field_name not in meta:
            result.add(path, f"Missing required metadata field: '{field_name}'.")
            continue
        if _is_empty_value(meta[field_name]):
            result.add(
                path, f"Required metadata field '{field_name}' must be non-empty."
            )


def _check_title(
    path: Path,
    text: str,
    meta: dict[str, object],
    result: MetadataValidationResult,
) -> None:
    """Validate that title metadata is non-empty and matches the H1 heading."""
    title = meta.get("title")
    if not isinstance(title, str) or not title.strip():
        result.add(path, "Metadata field 'title' must be a non-empty string.")
        return

    headings = TITLE_PATTERN.findall(text)
    if len(headings) != 1:
        result.add(path, "Document must contain exactly one H1 heading.")
        return

    h1 = headings[0].strip()
    if h1 != title.strip():
        result.add(path, f"H1 heading '{h1}' must match metadata title '{title}'.")


def _check_domain_directory(
    path: Path, root: Path, meta: dict[str, object], result: MetadataValidationResult
) -> None:
    """Validate that the domain field matches the document's directory."""
    domain = meta.get("domain")
    if not isinstance(domain, str) or domain not in VALID_DOMAINS:
        return

    try:
        top_level_dir = path.relative_to(root).parts[0]
    except ValueError:
        result.add(path, f"Document is not under knowledge base root '{root}'.")
        return

    if top_level_dir != domain:
        result.add(
            path,
            f"Metadata domain '{domain}' must match directory '{top_level_dir}'.",
        )


def _check_tags(
    path: Path, meta: dict[str, object], result: MetadataValidationResult
) -> None:
    """Validate tag count, naming, and uniqueness."""
    tags = meta.get("tags")
    if not isinstance(tags, list):
        return

    if len(tags) < 3:
        result.add(path, "Metadata field 'tags' must contain at least 3 tags.")

    seen_tags: set[str] = set()
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip():
            result.add(path, "Every tag must be a non-empty string.")
            continue
        if not TAG_PATTERN.match(tag):
            result.add(
                path,
                f"Tag '{tag}' must be lowercase and use underscores, "
                "not spaces or hyphens.",
            )
        if tag in seen_tags:
            result.add(path, f"Duplicate tag '{tag}' found in metadata.")
        seen_tags.add(tag)


def _check_optional_fields(
    path: Path, meta: dict[str, object], result: MetadataValidationResult
) -> None:
    """Validate optional metadata fields used by the quality system."""
    confidence = meta.get("confidence")
    if confidence is not None and confidence not in VALID_CONFIDENCE:
        result.add(
            path,
            "Optional field 'confidence' must be one of: high, medium, low.",
        )

    reviewed = meta.get("reviewed")
    if reviewed is True and confidence == "low":
        result.add(path, "Reviewed documents must not have confidence: low.")

    severity = meta.get("severity")
    domain = meta.get("domain")
    if severity is not None:
        if severity not in VALID_SEVERITY:
            result.add(
                path,
                "Optional field 'severity' must be CRITICAL, WARNING, or INFO.",
            )
        if domain != "emergency":
            result.add(
                path,
                "Optional field 'severity' is only allowed for emergency documents.",
            )

    language = meta.get("language")
    if language is not None and (
        not isinstance(language, str) or not LANGUAGE_PATTERN.match(language)
    ):
        result.add(
            path,
            "Optional field 'language' must be a two-letter ISO 639-1 code.",
        )

    last_updated = meta.get("last_updated")
    if last_updated is not None:
        if not isinstance(last_updated, str):
            result.add(
                path,
                "Optional field 'last_updated' must be an ISO 8601 string.",
            )
        else:
            try:
                date.fromisoformat(last_updated)
            except ValueError:
                result.add(
                    path,
                    "Optional field 'last_updated' must use YYYY-MM-DD format.",
                )

    related_documents = meta.get("related_documents")
    if related_documents is not None:
        if not isinstance(related_documents, list):
            result.add(path, "Optional field 'related_documents' must be a list.")
        else:
            for related in related_documents:
                if not isinstance(related, str) or not related.strip():
                    result.add(
                        path,
                        "Every related document path must be a non-empty string.",
                    )


def validate(root: Path = KNOWLEDGE_BASE_ROOT) -> MetadataValidationResult:
    """Validate metadata quality for all knowledge base documents under *root*."""
    result = MetadataValidationResult()
    seen_titles: dict[str, Path] = {}

    for path in _collect_documents(root):
        text = path.read_text(encoding="utf-8")
        meta = _parse_front_matter(text)
        if meta is None:
            result.add(path, "Missing YAML front matter block.")
            continue

        _check_required_fields(path, meta, result)
        _check_title(path, text, meta, result)
        _check_domain_directory(path, root, meta, result)
        _check_tags(path, meta, result)
        _check_optional_fields(path, meta, result)

        title = meta.get("title")
        if isinstance(title, str) and title.strip():
            title_key = title.strip().lower()
            if title_key in seen_titles:
                first_path = seen_titles[title_key].relative_to(root)
                result.add(
                    path,
                    f"Duplicate document title '{title}' also used in {first_path}.",
                )
            else:
                seen_titles[title_key] = path

    return result


def main() -> None:
    """Run metadata validation and print a report."""
    result = validate()

    if result.passed:
        print("Metadata validation passed - all document metadata is valid.")
        sys.exit(0)

    print(f"Metadata validation FAILED - {len(result.issues)} issue(s) found:\n")
    for issue in result.issues:
        relative = issue.path.relative_to(KNOWLEDGE_BASE_ROOT)
        print(f"  [{relative}] {issue.message}")

    sys.exit(1)


if __name__ == "__main__":
    main()
