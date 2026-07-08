"""Validate all Markdown documents in the PoultryGuard AI knowledge base.

Checks enforced
---------------
- Required YAML front matter fields present and correctly typed.
- ``domain`` value is one of the declared valid values.
- Required section headings present for the document's domain.
- ``sources`` list is non-empty.
- No duplicate ``title`` values across the knowledge base.
- Filename follows naming conventions (lowercase, underscores, ``.md``).

Exit codes
----------
0  All documents pass validation.
1  One or more validation errors found.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNOWLEDGE_BASE_ROOT = Path(__file__).resolve().parents[1] / "knowledge_base"

VALID_DOMAINS: frozenset[str] = frozenset(
    {
        "diseases",
        "vaccination",
        "climate",
        "biosecurity",
        "feeding",
        "management",
        "market",
        "emergency",
        "faq",
        "hausa",
    }
)

REQUIRED_METADATA_FIELDS: tuple[str, ...] = (
    "title",
    "domain",
    "tags",
    "reviewed",
    "sources",
)

# Sections required per domain.  Keys are domain names; the special key
# ``"_default"`` applies to every domain not listed explicitly.
REQUIRED_SECTIONS: dict[str, tuple[str, ...]] = {
    "_default": ("Overview", "Key Information", "Recommendations", "References"),
    "diseases": (
        "Overview",
        "Symptoms",
        "Treatment and Management",
        "Prevention and Vaccination",
        "When to Call a Veterinarian",
        "References",
    ),
    "emergency": (
        "Overview",
        "Warning Signs",
        "Emergency Response",
        "Do Not",
        "References",
    ),
    "faq": ("Question", "Answer", "References"),
}

# Directories that contain only README files and are not subject to document
# validation (e.g. the references directory holds bibliographies, not KB docs).
SKIP_DIRECTORIES: frozenset[str] = frozenset({"references"})

_FILENAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_]*\.md$")
_FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADING_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ValidationError:
    """A single validation failure for one document."""

    path: Path
    message: str


@dataclass
class ValidationResult:
    """Aggregated result of validating the entire knowledge base."""

    errors: list[ValidationError] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return True when no errors were found."""
        return len(self.errors) == 0

    def add(self, path: Path, message: str) -> None:
        """Record a validation error."""
        self.errors.append(ValidationError(path=path, message=message))


# ---------------------------------------------------------------------------
# YAML front matter parser (stdlib only — no PyYAML dependency)
# ---------------------------------------------------------------------------


def _parse_front_matter(text: str) -> dict[str, object] | None:
    """Extract and parse YAML front matter from a Markdown string.

    Returns a dict of parsed fields, or None if no front matter block is found.
    Only handles the simple scalar and list types used by the KB schema.
    """
    match = _FRONT_MATTER_PATTERN.match(text)
    if not match:
        return None

    raw = match.group(1)
    result: dict[str, object] = {}

    # Parse line by line.  Handles scalars, booleans, and simple inline lists.
    current_key: str | None = None
    current_list: list[str] | None = None

    for line in raw.splitlines():
        # List continuation item
        if line.startswith("  - ") and current_list is not None:
            current_list.append(line[4:].strip().strip('"'))
            continue

        # New key
        if ":" in line and not line.startswith(" "):
            # Flush any in-progress list
            if current_key is not None and current_list is not None:
                result[current_key] = current_list
                current_list = None

            key, _, raw_value = line.partition(":")
            key = key.strip()
            raw_value = raw_value.strip()

            if raw_value == "" or raw_value is None:
                # Value will be on following lines (list)
                current_key = key
                current_list = []
            elif raw_value.startswith("[") and raw_value.endswith("]"):
                # Inline list: [a, b, c]
                inner = raw_value[1:-1]
                items = [
                    item.strip().strip('"') for item in inner.split(",") if item.strip()
                ]
                result[key] = items
                current_key = None
            elif raw_value.lower() == "true":
                result[key] = True
                current_key = None
            elif raw_value.lower() == "false":
                result[key] = False
                current_key = None
            else:
                result[key] = raw_value.strip('"')
                current_key = None

    # Flush trailing list
    if current_key is not None and current_list is not None:
        result[current_key] = current_list

    return result


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_filename(path: Path, result: ValidationResult) -> None:
    """Filename must be lowercase, underscore-separated, ending in .md."""
    if not _FILENAME_PATTERN.match(path.name):
        result.add(
            path,
            f"Filename '{path.name}' must be lowercase, use underscores, "
            "and end with .md (e.g. newcastle_disease.md).",
        )


def _check_front_matter(
    path: Path, text: str, result: ValidationResult
) -> dict[str, object] | None:
    """Front matter must be present and contain all required fields."""
    meta = _parse_front_matter(text)
    if meta is None:
        result.add(path, "Missing YAML front matter block (--- ... ---).")
        return None

    for field_name in REQUIRED_METADATA_FIELDS:
        if field_name not in meta:
            result.add(path, f"Missing required metadata field: '{field_name}'.")

    return meta


def _check_domain(
    path: Path, meta: dict[str, object], result: ValidationResult
) -> str | None:
    """domain field must be one of the declared valid values."""
    domain = meta.get("domain")
    if not isinstance(domain, str):
        result.add(path, "Metadata field 'domain' must be a string.")
        return None
    if domain not in VALID_DOMAINS:
        result.add(
            path,
            f"Invalid domain '{domain}'. "
            f"Must be one of: {', '.join(sorted(VALID_DOMAINS))}.",
        )
        return None
    return domain


def _check_sources(
    path: Path, meta: dict[str, object], result: ValidationResult
) -> None:
    """sources must be a non-empty list."""
    sources = meta.get("sources")
    if not isinstance(sources, list) or len(sources) == 0:
        result.add(
            path,
            "Metadata field 'sources' must be a non-empty list. "
            "Add at least one authoritative reference.",
        )


def _check_tags(path: Path, meta: dict[str, object], result: ValidationResult) -> None:
    """tags must be a non-empty list."""
    tags = meta.get("tags")
    if not isinstance(tags, list) or len(tags) == 0:
        result.add(path, "Metadata field 'tags' must be a non-empty list.")


def _check_reviewed_type(
    path: Path, meta: dict[str, object], result: ValidationResult
) -> None:
    """reviewed must be a boolean."""
    reviewed = meta.get("reviewed")
    if not isinstance(reviewed, bool):
        result.add(
            path,
            f"Metadata field 'reviewed' must be a boolean (true or false), "
            f"got: {reviewed!r}.",
        )


def _check_sections(
    path: Path, text: str, domain: str, result: ValidationResult
) -> None:
    """Required section headings must be present for the document's domain."""
    required = REQUIRED_SECTIONS.get(domain, REQUIRED_SECTIONS["_default"])
    found_headings = set(_HEADING_PATTERN.findall(text))
    for section in required:
        if section not in found_headings:
            result.add(
                path,
                f"Missing required section '## {section}' for domain '{domain}'.",
            )


# ---------------------------------------------------------------------------
# Main validation logic
# ---------------------------------------------------------------------------


def _collect_documents(root: Path) -> list[Path]:
    """Return all .md files under root, excluding README.md and skip dirs."""
    docs: list[Path] = []
    for md_file in sorted(root.rglob("*.md")):
        if md_file.name.lower() == "readme.md":
            continue
        # Skip directories that are not subject to document validation
        relative_parts = md_file.relative_to(root).parts
        if relative_parts and relative_parts[0] in SKIP_DIRECTORIES:
            continue
        docs.append(md_file)
    return docs


def validate(root: Path = KNOWLEDGE_BASE_ROOT) -> ValidationResult:
    """Validate all knowledge base documents under *root*.

    Parameters
    ----------
    root:
        Path to the knowledge base root directory.

    Returns
    -------
    ValidationResult
        Contains all errors found.  ``result.passed`` is True when clean.
    """
    result = ValidationResult()
    documents = _collect_documents(root)

    if not documents:
        return result

    seen_titles: dict[str, Path] = {}

    for path in documents:
        text = path.read_text(encoding="utf-8")

        _check_filename(path, result)

        meta = _check_front_matter(path, text, result)
        if meta is None:
            continue  # Cannot proceed without metadata

        _check_tags(path, meta, result)
        _check_reviewed_type(path, meta, result)
        _check_sources(path, meta, result)

        domain = _check_domain(path, meta, result)
        if domain is None:
            continue  # Cannot check sections without a valid domain

        _check_sections(path, text, domain, result)

        # Duplicate title check
        title = meta.get("title")
        if isinstance(title, str):
            title_lower = title.lower()
            if title_lower in seen_titles:
                result.add(
                    path,
                    f"Duplicate title '{title}' — already used in "
                    f"'{seen_titles[title_lower].relative_to(root)}'.",
                )
            else:
                seen_titles[title_lower] = path

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the validator and print a report to stdout."""
    result = validate()

    if result.passed:
        print("Knowledge base validation passed — all documents are valid.")
        sys.exit(0)

    print(f"Knowledge base validation FAILED — {len(result.errors)} error(s) found:\n")
    for error in result.errors:
        relative = error.path.relative_to(KNOWLEDGE_BASE_ROOT)
        print(f"  [{relative}]  {error.message}")

    sys.exit(1)


if __name__ == "__main__":
    main()
