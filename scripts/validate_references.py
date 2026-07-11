"""Validate references and source quality in knowledge base documents."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from validate_knowledge_base import (
    KNOWLEDGE_BASE_ROOT,
    _collect_documents,
    _parse_front_matter,
)

REFERENCE_SECTION_PATTERN = re.compile(
    r"^## References\s*\n(?P<body>.*?)(?=^##\s+|\Z)", re.DOTALL | re.MULTILINE
)
REFERENCE_ITEM_PATTERN = re.compile(r"^\s*[-*]\s+(.+?)\s*$", re.MULTILINE)
YEAR_PATTERN = re.compile(r"\((?:19|20)\d{2}\)")
PLAIN_YEAR_PATTERN = re.compile(r"(?:19|20)\d{2}")
OFFICIAL_MANUAL_PATTERNS = (
    "manual",
    "technical disease card",
    "world organisation for animal health",
    "woah",
    "oie",
    "fao",
    "merck veterinary manual",
    "diseases of poultry",
)
UNACCEPTABLE_SOURCE_PATTERNS = (
    "wikipedia",
    "facebook",
    "twitter.com",
    "x.com/",
    "instagram",
    "tiktok",
    "reddit",
    "blogspot",
    "medium.com",
    "quora",
    "forum",
    "chatgpt",
    "ai-generated",
)


@dataclass
class ReferenceIssue:
    """A reference validation issue found in one document."""

    path: Path
    message: str


@dataclass
class ReferenceValidationResult:
    """Aggregated reference validation result."""

    issues: list[ReferenceIssue] = field(default_factory=list)
    warnings: list[ReferenceIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return True when no reference issues were found."""
        return not self.issues

    def add(self, path: Path, message: str) -> None:
        """Record one reference validation issue."""
        self.issues.append(ReferenceIssue(path=path, message=message))

    def warn(self, path: Path, message: str) -> None:
        """Record one non-fatal reference validation warning."""
        warning = ReferenceIssue(path=path, message=message)
        if warning not in self.warnings:
            self.warnings.append(warning)


def _normalise_reference(value: str) -> str:
    """Return a loose comparable form for source/reference matching."""
    lowered = value.lower().strip().strip('"').strip("'")
    return re.sub(r"\s+", " ", lowered).rstrip(".")


def _extract_reference_items(text: str) -> list[str]:
    """Extract bullet items from the References section."""
    match = REFERENCE_SECTION_PATTERN.search(text)
    if not match:
        return []
    return [
        item.strip() for item in REFERENCE_ITEM_PATTERN.findall(match.group("body"))
    ]


def _reference_year(reference: str) -> int | None:
    """Extract the first publication year found in a reference string."""
    match = PLAIN_YEAR_PATTERN.search(reference)
    if not match:
        return None
    return int(match.group(0))


def _is_official_manual(reference: str) -> bool:
    """Return True when an old reference is an accepted official/manual source."""
    lowered = reference.lower()
    return any(pattern in lowered for pattern in OFFICIAL_MANUAL_PATTERNS)


def _has_author_or_organisation(reference: str) -> bool:
    """Check that a reference starts with an author or organisation token."""
    prefix = reference.split("(", 1)[0].strip()
    return bool(prefix) and any(char.isalpha() for char in prefix)


def _has_title(reference: str) -> bool:
    """Check that a reference appears to contain a title after its year."""
    after_year = re.split(r"\((?:19|20)\d{2}\)\.?", reference, maxsplit=1)
    if len(after_year) < 2:
        return False
    title = after_year[1].strip()
    return bool(title) and any(char.isalpha() for char in title)


def _check_reference_quality(
    path: Path,
    reference: str,
    result: ReferenceValidationResult,
) -> None:
    """Validate author/organisation, title, year, and age quality."""
    if not _has_author_or_organisation(reference):
        result.add(
            path, f"Reference must include an author or organisation: {reference}"
        )

    year = _reference_year(reference)
    if year is None:
        result.warn(path, f"Reference has no publication year to verify: {reference}")
    elif not _has_title(reference):
        result.add(path, f"Reference must include a title after the year: {reference}")
    elif date.today().year - year > 10 and not _is_official_manual(reference):
        result.warn(
            path,
            f"Reference is older than 10 years and is not clearly an official "
            f"veterinary manual/source: {reference}",
        )


def _check_sources_field(
    path: Path, meta: dict[str, object], result: ReferenceValidationResult
) -> list[str]:
    """Validate and return source strings from metadata."""
    sources = meta.get("sources")
    if not isinstance(sources, list) or not sources:
        result.add(path, "Metadata field 'sources' must be a non-empty list.")
        return []

    clean_sources: list[str] = []
    seen_sources: set[str] = set()
    for source in sources:
        if not isinstance(source, str) or not source.strip():
            result.add(path, "Every source must be a non-empty string.")
            continue

        normalised = _normalise_reference(source)
        if normalised in seen_sources:
            result.add(path, f"Duplicate metadata source found: {source}")
        seen_sources.add(normalised)
        clean_sources.append(source)

        lowered = source.lower()
        if any(pattern in lowered for pattern in UNACCEPTABLE_SOURCE_PATTERNS):
            result.add(path, f"Unacceptable source type found: {source}")

        _check_reference_quality(path, source, result)

    return clean_sources


def _check_references_section(
    path: Path,
    sources: list[str],
    reference_items: list[str],
    result: ReferenceValidationResult,
) -> None:
    """Validate that metadata sources and References bullets agree."""
    if not reference_items:
        result.add(path, "References section must contain at least one bullet item.")
        return

    normalised_items = {_normalise_reference(item) for item in reference_items}
    if len(normalised_items) != len(reference_items):
        result.add(path, "References section contains duplicate references.")

    for item in reference_items:
        lowered = item.lower()
        if any(pattern in lowered for pattern in UNACCEPTABLE_SOURCE_PATTERNS):
            result.add(path, f"Unacceptable reference item found: {item}")
        _check_reference_quality(path, item, result)

    for source in sources:
        if _normalise_reference(source) not in normalised_items:
            result.add(
                path,
                f"Metadata source is missing from the References section: {source}",
            )


def validate(root: Path = KNOWLEDGE_BASE_ROOT) -> ReferenceValidationResult:
    """Validate references for all knowledge base documents under *root*."""
    result = ReferenceValidationResult()

    for path in _collect_documents(root):
        text = path.read_text(encoding="utf-8")
        meta = _parse_front_matter(text)
        if meta is None:
            result.add(path, "Missing YAML front matter block.")
            continue

        sources = _check_sources_field(path, meta, result)
        references = _extract_reference_items(text)
        _check_references_section(path, sources, references, result)

    return result


def main() -> None:
    """Run reference validation and print a report."""
    result = validate()

    if result.passed:
        print("Reference validation passed.")
        if result.warnings:
            print(f"Reference validation warnings - {len(result.warnings)} warning(s):")
            for warning in result.warnings:
                relative = warning.path.relative_to(KNOWLEDGE_BASE_ROOT)
                print(f"  [{relative}] {warning.message}")
        sys.exit(0)

    print(f"Reference validation FAILED - {len(result.issues)} issue(s) found:\n")
    for issue in result.issues:
        relative = issue.path.relative_to(KNOWLEDGE_BASE_ROOT)
        print(f"  [{relative}] {issue.message}")

    if result.warnings:
        print(f"\nWarnings - {len(result.warnings)} warning(s):")
        for warning in result.warnings:
            relative = warning.path.relative_to(KNOWLEDGE_BASE_ROOT)
            print(f"  [{relative}] {warning.message}")

    sys.exit(1)


if __name__ == "__main__":
    main()
