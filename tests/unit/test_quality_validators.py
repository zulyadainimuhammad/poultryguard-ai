# ruff: noqa: E402
"""Unit tests for Sprint 2.2 knowledge base quality validators."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from build_index_preview import build_preview
from validate_links import validate as validate_links
from validate_metadata import validate as validate_metadata
from validate_references import validate as validate_references


def _write(path: Path, content: str) -> Path:
    """Write a fixture document and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _valid_doc(
    *,
    title: str = "Newcastle Disease",
    domain: str = "diseases",
    tags: str = "[newcastle, respiratory, mortality]",
    references: str | None = None,
    body_extra: str = "",
) -> str:
    """Return a valid disease document fixture."""
    source = "FAO. (2021). Newcastle Disease. Food and Agriculture Organization."
    reference_items = references if references is not None else f"- {source}"
    return f"""\
---
title: {title}
domain: {domain}
tags: {tags}
confidence: medium
reviewed: false
last_updated: "2026-07-07"
sources:
  - "{source}"
---

# {title}

## Overview

Newcastle disease is a contagious poultry disease. This overview provides enough
context for a retrieval chunk and names the disease clearly.

## Symptoms

Affected birds may show respiratory signs, neurological signs, and sudden death.
Farmers should watch the flock closely and report fast spread.

## Treatment and Management

There is no specific antiviral treatment. Isolate sick birds, stop movement, and
contact a veterinarian for professional guidance.

## Prevention and Vaccination

Vaccination and biosecurity reduce outbreak risk. Farmers should follow local
veterinary schedules and keep records.

## When to Call a Veterinarian

Call a veterinarian when several birds die suddenly or show twisted neck,
paralysis, or severe breathing problems.

{body_extra}

## References

{reference_items}
"""


class TestMetadataValidation:
    def test_valid_metadata_passes(self, tmp_path: Path) -> None:
        _write(tmp_path / "diseases" / "newcastle_disease.md", _valid_doc())

        result = validate_metadata(tmp_path)

        assert result.passed, [issue.message for issue in result.issues]

    def test_title_must_match_h1(self, tmp_path: Path) -> None:
        doc = _valid_doc(title="Newcastle Disease").replace(
            "# Newcastle Disease", "# Different Disease"
        )
        _write(tmp_path / "diseases" / "newcastle_disease.md", doc)

        result = validate_metadata(tmp_path)

        assert any(
            "must match metadata title" in issue.message for issue in result.issues
        )

    def test_domain_must_match_directory(self, tmp_path: Path) -> None:
        _write(tmp_path / "feeding" / "newcastle_disease.md", _valid_doc())

        result = validate_metadata(tmp_path)

        assert any("must match directory" in issue.message for issue in result.issues)

    def test_tags_require_quality_conventions(self, tmp_path: Path) -> None:
        doc = _valid_doc(tags="[Newcastle, bad-tag]")
        _write(tmp_path / "diseases" / "newcastle_disease.md", doc)

        result = validate_metadata(tmp_path)

        messages = [issue.message for issue in result.issues]
        assert any("at least 3 tags" in message for message in messages)
        assert any("lowercase and use underscores" in message for message in messages)

    def test_duplicate_titles_fail(self, tmp_path: Path) -> None:
        _write(tmp_path / "diseases" / "first.md", _valid_doc())
        _write(tmp_path / "diseases" / "second.md", _valid_doc())

        result = validate_metadata(tmp_path)

        assert any(
            "Duplicate document title" in issue.message for issue in result.issues
        )

    def test_invalid_confidence_and_date_fail(self, tmp_path: Path) -> None:
        doc = _valid_doc().replace("confidence: medium", "confidence: certain")
        doc = doc.replace('last_updated: "2026-07-07"', 'last_updated: "07-07-2026"')
        _write(tmp_path / "diseases" / "newcastle_disease.md", doc)

        result = validate_metadata(tmp_path)

        messages = [issue.message for issue in result.issues]
        assert any("confidence" in message for message in messages)
        assert any("YYYY-MM-DD" in message for message in messages)


class TestReferenceValidation:
    def test_valid_references_pass(self, tmp_path: Path) -> None:
        _write(tmp_path / "diseases" / "newcastle_disease.md", _valid_doc())

        result = validate_references(tmp_path)

        assert result.passed, [issue.message for issue in result.issues]

    def test_metadata_source_must_appear_in_references_section(
        self, tmp_path: Path
    ) -> None:
        doc = _valid_doc(references="- WOAH. (2021). Different Source.")
        _write(tmp_path / "diseases" / "newcastle_disease.md", doc)

        result = validate_references(tmp_path)

        assert any(
            "missing from the References section" in issue.message
            for issue in result.issues
        )

    def test_unacceptable_source_fails(self, tmp_path: Path) -> None:
        doc = _valid_doc().replace(
            "FAO. (2021). Newcastle Disease. Food and Agriculture Organization.",
            "Wikipedia. (2021). Newcastle Disease.",
        )
        _write(tmp_path / "diseases" / "newcastle_disease.md", doc)

        result = validate_references(tmp_path)

        assert any("Unacceptable" in issue.message for issue in result.issues)

    def test_duplicate_references_fail(self, tmp_path: Path) -> None:
        source = "FAO. (2021). Newcastle Disease. Food and Agriculture Organization."
        doc = _valid_doc(references=f"- {source}\n- {source}")
        _write(tmp_path / "diseases" / "newcastle_disease.md", doc)

        result = validate_references(tmp_path)

        assert any(
            "duplicate references" in issue.message.lower() for issue in result.issues
        )

    def test_old_non_manual_reference_warns(self, tmp_path: Path) -> None:
        old_source = "Smith, A. (2001). Small Farm Poultry Notes. Local Press."
        doc = _valid_doc().replace(
            "FAO. (2021). Newcastle Disease. Food and Agriculture Organization.",
            old_source,
        )
        _write(tmp_path / "diseases" / "newcastle_disease.md", doc)

        result = validate_references(tmp_path)

        assert result.passed
        assert any(
            "older than 10 years" in warning.message for warning in result.warnings
        )


class TestLinkValidation:
    def test_internal_relative_link_passes(self, tmp_path: Path) -> None:
        _write(tmp_path / "vaccination" / "schedule.md", "# Schedule\n")
        doc = _valid_doc(
            body_extra="See [Vaccination Schedule](../vaccination/schedule.md)."
        )
        _write(tmp_path / "diseases" / "newcastle_disease.md", doc)

        result = validate_links(tmp_path)

        assert result.passed, [issue.message for issue in result.issues]

    def test_external_link_fails(self, tmp_path: Path) -> None:
        doc = _valid_doc(body_extra="See [external](https://example.com).")
        _write(tmp_path / "diseases" / "newcastle_disease.md", doc)

        result = validate_links(tmp_path)

        assert any(
            "External links are not allowed" in issue.message for issue in result.issues
        )

    def test_missing_internal_link_target_fails(self, tmp_path: Path) -> None:
        doc = _valid_doc(body_extra="See [missing](../vaccination/missing.md).")
        _write(tmp_path / "diseases" / "newcastle_disease.md", doc)

        result = validate_links(tmp_path)

        assert any("does not exist" in issue.message for issue in result.issues)

    def test_broken_anchor_fails(self, tmp_path: Path) -> None:
        _write(tmp_path / "vaccination" / "schedule.md", "# Schedule\n\n## Overview\n")
        doc = _valid_doc(
            body_extra="See [Vaccination Schedule](../vaccination/schedule.md#missing)."
        )
        _write(tmp_path / "diseases" / "newcastle_disease.md", doc)

        result = validate_links(tmp_path)

        assert any("anchor does not exist" in issue.message for issue in result.issues)

    def test_readme_links_are_validated(self, tmp_path: Path) -> None:
        _write(tmp_path / "README.md", "[Missing](missing.md)\n")

        result = validate_links(tmp_path)

        assert any("does not exist" in issue.message for issue in result.issues)


class TestIndexPreview:
    def test_build_preview_counts_documents_and_chunks(self, tmp_path: Path) -> None:
        _write(tmp_path / "diseases" / "newcastle_disease.md", _valid_doc())

        preview = build_preview(tmp_path)

        assert preview.document_count == 1
        assert preview.chunk_count == 6
        assert preview.documents_by_domain == {"diseases": 1}
        assert preview.chunks_by_domain == {"diseases": 6}
        assert preview.average_document_words > 0
        assert preview.average_chunk_words > 0
        assert preview.confidence_distribution == {"medium": 1}

    def test_build_preview_warns_for_short_sections(self, tmp_path: Path) -> None:
        _write(tmp_path / "diseases" / "newcastle_disease.md", _valid_doc())

        preview = build_preview(tmp_path)

        assert any("target is at least" in warning for warning in preview.warnings)

    def test_build_preview_reports_duplicate_tags(self, tmp_path: Path) -> None:
        doc = _valid_doc(tags="[newcastle, newcastle, respiratory]")
        _write(tmp_path / "diseases" / "newcastle_disease.md", doc)

        preview = build_preview(tmp_path)

        assert preview.duplicate_tags == {
            "diseases/newcastle_disease.md": ["newcastle"]
        }
