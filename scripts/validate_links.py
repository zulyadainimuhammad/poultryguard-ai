"""Validate offline-safe Markdown links in the knowledge base."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

from validate_knowledge_base import KNOWLEDGE_BASE_ROOT

MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[[^\]]*]\(([^)]+)\)")
EXTERNAL_TARGET_PATTERN = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)


@dataclass
class LinkIssue:
    """A link validation issue found in one Markdown document."""

    path: Path
    message: str


@dataclass
class LinkValidationResult:
    """Aggregated link validation result."""

    issues: list[LinkIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return True when no link issues were found."""
        return not self.issues

    def add(self, path: Path, message: str) -> None:
        """Record one link validation issue."""
        self.issues.append(LinkIssue(path=path, message=message))


def _collect_markdown_files(root: Path) -> list[Path]:
    """Return all Markdown files under *root* for link validation."""
    return sorted(root.rglob("*.md"))


def _strip_fragment_and_query(target: str) -> str:
    """Remove URL fragment and query portions from a link target."""
    return target.split("#", 1)[0].split("?", 1)[0]


def _extract_fragment(target: str) -> str | None:
    """Extract a Markdown link fragment, if one exists."""
    if "#" not in target:
        return None
    return target.split("#", 1)[1].split("?", 1)[0]


def _slugify_heading(heading: str) -> str:
    """Return GitHub-style slug for a Markdown heading."""
    lowered = heading.strip().lower()
    lowered = re.sub(r"[^\w\s-]", "", lowered)
    lowered = re.sub(r"\s+", "-", lowered)
    return lowered.strip("-")


def _document_anchors(path: Path) -> set[str]:
    """Return possible Markdown heading anchors for a document."""
    text = path.read_text(encoding="utf-8")
    anchors: set[str] = set()
    for _, heading in HEADING_PATTERN.findall(text):
        anchors.add(_slugify_heading(heading))
    return anchors


def _is_external(target: str) -> bool:
    """Return True when *target* is an external URL or email link."""
    return bool(EXTERNAL_TARGET_PATTERN.match(target)) or target.lower().startswith(
        "mailto:"
    )


def _validate_target(
    path: Path,
    root: Path,
    target: str,
    result: LinkValidationResult,
) -> None:
    """Validate one Markdown link target."""
    cleaned = target.strip().strip("<>").strip()
    if not cleaned:
        result.add(path, "Markdown link target must not be empty.")
        return

    if _is_external(cleaned):
        result.add(
            path,
            f"External links are not allowed in knowledge base files: {cleaned}",
        )
        return

    local_part = _strip_fragment_and_query(cleaned)
    fragment = _extract_fragment(cleaned)
    candidate = (
        path if not local_part else (path.parent / unquote(local_part)).resolve()
    )
    repo_root = root.resolve().parent
    if not str(candidate).startswith(str(repo_root)):
        result.add(path, f"Relative link escapes repository root: {cleaned}")
        return
    if not candidate.exists():
        result.add(path, f"Internal Markdown link target does not exist: {cleaned}")
        return

    if fragment:
        anchors = _document_anchors(candidate)
        if unquote(fragment).lower() not in anchors:
            result.add(path, f"Markdown anchor does not exist: {cleaned}")


def validate(root: Path = KNOWLEDGE_BASE_ROOT) -> LinkValidationResult:
    """Validate Markdown links for all knowledge base Markdown files."""
    result = LinkValidationResult()

    for path in _collect_markdown_files(root):
        text = path.read_text(encoding="utf-8")

        for image_target in MARKDOWN_IMAGE_PATTERN.findall(text):
            result.add(
                path,
                f"Images are not allowed in MVP knowledge base files: {image_target}",
            )

        for link_target in MARKDOWN_LINK_PATTERN.findall(text):
            _validate_target(path, root, link_target, result)

    return result


def main() -> None:
    """Run link validation and print a report."""
    result = validate()

    if result.passed:
        print("Link validation passed - internal Markdown links are valid.")
        sys.exit(0)

    print(f"Link validation FAILED - {len(result.issues)} issue(s) found:\n")
    for issue in result.issues:
        relative = issue.path.relative_to(KNOWLEDGE_BASE_ROOT)
        print(f"  [{relative}] {issue.message}")

    sys.exit(1)


if __name__ == "__main__":
    main()
