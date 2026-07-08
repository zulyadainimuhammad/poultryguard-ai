# ruff: noqa: E402
"""Unit tests for scripts/validate_knowledge_base.py.

Each test exercises one specific validation rule in isolation using a
temporary directory so the real knowledge base is never touched.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from validate_knowledge_base import _parse_front_matter, validate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, filename: str, content: str) -> Path:
    """Write *content* to *tmp_path/filename* and return the path."""
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return p


def _valid_disease_doc(title: str = "Test Disease") -> str:
    """Return a fully valid disease-domain document."""
    return f"""\
---
title: {title}
domain: diseases
tags: [test, disease]
reviewed: false
sources:
  - "FAO. (2021). Test Source."
---

# {title}

## Overview

Overview text.

## Symptoms

Symptom text.

## Treatment and Management

Treatment text.

## Prevention and Vaccination

Prevention text.

## When to Call a Veterinarian

Vet escalation text.

## References

- FAO. (2021). Test Source.
"""


def _valid_default_doc(title: str = "Test Topic", domain: str = "feeding") -> str:
    """Return a fully valid default-domain document."""
    return f"""\
---
title: {title}
domain: {domain}
tags: [test]
reviewed: false
sources:
  - "FAO. (2021). Test Source."
---

# {title}

## Overview

Overview text.

## Key Information

Key info text.

## Recommendations

Recommendations text.

## References

- FAO. (2021). Test Source.
"""


def _valid_emergency_doc(title: str = "Test Emergency") -> str:
    return f"""\
---
title: {title}
domain: emergency
tags: [emergency, test]
reviewed: false
sources:
  - "OIE. (2021). Test Source."
severity: CRITICAL
---

# {title}

## Overview

Overview text.

## Warning Signs

Warning signs text.

## Emergency Response

Response text.

## Do Not

Do not text.

## References

- OIE. (2021). Test Source.
"""


def _valid_faq_doc(title: str = "Test FAQ") -> str:
    return f"""\
---
title: {title}
domain: faq
tags: [faq, test]
reviewed: false
sources:
  - "Extension Service. (2021). Test."
---

# {title}

## Question

What is the question?

## Answer

This is the answer.

## References

- Extension Service. (2021). Test.
"""


# ---------------------------------------------------------------------------
# _parse_front_matter
# ---------------------------------------------------------------------------


class TestParseFrontMatter:
    def test_returns_none_when_no_front_matter(self) -> None:
        assert _parse_front_matter("# Just a heading\n\nSome text.") is None

    def test_parses_scalar_fields(self) -> None:
        text = "---\ntitle: My Title\nreviewed: false\n---\n"
        meta = _parse_front_matter(text)
        assert meta is not None
        assert meta["title"] == "My Title"
        assert meta["reviewed"] is False

    def test_parses_inline_list(self) -> None:
        text = "---\ntags: [a, b, c]\n---\n"
        meta = _parse_front_matter(text)
        assert meta is not None
        assert meta["tags"] == ["a", "b", "c"]

    def test_parses_block_list(self) -> None:
        text = "---\nsources:\n  - First source\n  - Second source\n---\n"
        meta = _parse_front_matter(text)
        assert meta is not None
        assert meta["sources"] == ["First source", "Second source"]

    def test_parses_boolean_true(self) -> None:
        text = "---\nreviewed: true\n---\n"
        meta = _parse_front_matter(text)
        assert meta is not None
        assert meta["reviewed"] is True


# ---------------------------------------------------------------------------
# Filename validation
# ---------------------------------------------------------------------------


class TestFilenameValidation:
    def test_valid_filename_passes(self, tmp_path: Path) -> None:
        _write(tmp_path, "valid_name.md", _valid_disease_doc())
        result = validate(tmp_path)
        filename_errors = [e for e in result.errors if "Filename" in e.message]
        assert not filename_errors

    def test_uppercase_filename_fails(self, tmp_path: Path) -> None:
        _write(tmp_path, "Invalid_Name.md", _valid_disease_doc())
        result = validate(tmp_path)
        assert any("Filename" in e.message for e in result.errors)

    def test_hyphenated_filename_fails(self, tmp_path: Path) -> None:
        _write(tmp_path, "invalid-name.md", _valid_disease_doc())
        result = validate(tmp_path)
        assert any("Filename" in e.message for e in result.errors)

    def test_readme_is_skipped(self, tmp_path: Path) -> None:
        _write(tmp_path, "README.md", "# README\n\nNot a KB doc.")
        result = validate(tmp_path)
        assert result.passed


# ---------------------------------------------------------------------------
# Front matter validation
# ---------------------------------------------------------------------------


class TestFrontMatterValidation:
    def test_missing_front_matter_fails(self, tmp_path: Path) -> None:
        _write(tmp_path, "no_front_matter.md", "# Title\n\nNo front matter here.")
        result = validate(tmp_path)
        assert any("front matter" in e.message for e in result.errors)

    def test_missing_title_fails(self, tmp_path: Path) -> None:
        doc = _valid_disease_doc().replace("title: Test Disease\n", "")
        _write(tmp_path, "missing_title.md", doc)
        result = validate(tmp_path)
        assert any("'title'" in e.message for e in result.errors)

    def test_missing_domain_fails(self, tmp_path: Path) -> None:
        doc = _valid_disease_doc().replace("domain: diseases\n", "")
        _write(tmp_path, "missing_domain.md", doc)
        result = validate(tmp_path)
        assert any("'domain'" in e.message for e in result.errors)

    def test_missing_tags_fails(self, tmp_path: Path) -> None:
        doc = _valid_disease_doc().replace("tags: [test, disease]\n", "")
        _write(tmp_path, "missing_tags.md", doc)
        result = validate(tmp_path)
        assert any("'tags'" in e.message for e in result.errors)

    def test_missing_reviewed_fails(self, tmp_path: Path) -> None:
        doc = _valid_disease_doc().replace("reviewed: false\n", "")
        _write(tmp_path, "missing_reviewed.md", doc)
        result = validate(tmp_path)
        assert any("'reviewed'" in e.message for e in result.errors)

    def test_missing_sources_fails(self, tmp_path: Path) -> None:
        doc = _valid_disease_doc().replace(
            'sources:\n  - "FAO. (2021). Test Source."\n', ""
        )
        _write(tmp_path, "missing_sources.md", doc)
        result = validate(tmp_path)
        assert any("'sources'" in e.message for e in result.errors)


# ---------------------------------------------------------------------------
# Domain validation
# ---------------------------------------------------------------------------


class TestDomainValidation:
    def test_invalid_domain_fails(self, tmp_path: Path) -> None:
        doc = _valid_disease_doc().replace("domain: diseases", "domain: invalid_domain")
        _write(tmp_path, "bad_domain.md", doc)
        result = validate(tmp_path)
        assert any("Invalid domain" in e.message for e in result.errors)

    def test_all_valid_domains_pass(self, tmp_path: Path) -> None:
        domains_to_test = [
            ("diseases", _valid_disease_doc("D1")),
            ("feeding", _valid_default_doc("D2", "feeding")),
            ("vaccination", _valid_default_doc("D3", "vaccination")),
            ("climate", _valid_default_doc("D4", "climate")),
            ("biosecurity", _valid_default_doc("D5", "biosecurity")),
            ("management", _valid_default_doc("D6", "management")),
            ("market", _valid_default_doc("D7", "market")),
            ("emergency", _valid_emergency_doc("D8")),
            ("faq", _valid_faq_doc("D9")),
        ]
        for domain, content in domains_to_test:
            _write(tmp_path, f"{domain}_doc.md", content)
        result = validate(tmp_path)
        domain_errors = [e for e in result.errors if "Invalid domain" in e.message]
        assert not domain_errors


# ---------------------------------------------------------------------------
# Sources validation
# ---------------------------------------------------------------------------


class TestSourcesValidation:
    def test_empty_sources_list_fails(self, tmp_path: Path) -> None:
        doc = _valid_disease_doc().replace(
            'sources:\n  - "FAO. (2021). Test Source."\n', "sources: []\n"
        )
        _write(tmp_path, "empty_sources.md", doc)
        result = validate(tmp_path)
        assert any("sources" in e.message.lower() for e in result.errors)


# ---------------------------------------------------------------------------
# Section heading validation
# ---------------------------------------------------------------------------


class TestSectionValidation:
    def test_disease_missing_symptoms_fails(self, tmp_path: Path) -> None:
        doc = _valid_disease_doc().replace("## Symptoms\n\nSymptom text.\n\n", "")
        _write(tmp_path, "missing_symptoms.md", doc)
        result = validate(tmp_path)
        assert any("Symptoms" in e.message for e in result.errors)

    def test_disease_missing_vet_section_fails(self, tmp_path: Path) -> None:
        doc = _valid_disease_doc().replace(
            "## When to Call a Veterinarian\n\nVet escalation text.\n\n", ""
        )
        _write(tmp_path, "missing_vet.md", doc)
        result = validate(tmp_path)
        assert any("When to Call a Veterinarian" in e.message for e in result.errors)

    def test_emergency_missing_response_section_fails(self, tmp_path: Path) -> None:
        doc = _valid_emergency_doc().replace(
            "## Emergency Response\n\nResponse text.\n\n", ""
        )
        _write(tmp_path, "missing_response.md", doc)
        result = validate(tmp_path)
        assert any("Emergency Response" in e.message for e in result.errors)

    def test_faq_missing_answer_fails(self, tmp_path: Path) -> None:
        doc = _valid_faq_doc().replace("## Answer\n\nThis is the answer.\n\n", "")
        _write(tmp_path, "missing_answer.md", doc)
        result = validate(tmp_path)
        assert any("Answer" in e.message for e in result.errors)

    def test_default_domain_missing_key_information_fails(self, tmp_path: Path) -> None:
        doc = _valid_default_doc().replace(
            "## Key Information\n\nKey info text.\n\n", ""
        )
        _write(tmp_path, "missing_key_info.md", doc)
        result = validate(tmp_path)
        assert any("Key Information" in e.message for e in result.errors)


# ---------------------------------------------------------------------------
# Duplicate title validation
# ---------------------------------------------------------------------------


class TestDuplicateTitleValidation:
    def test_duplicate_titles_fail(self, tmp_path: Path) -> None:
        _write(tmp_path, "doc_one.md", _valid_disease_doc("Same Title"))
        _write(tmp_path, "doc_two.md", _valid_disease_doc("Same Title"))
        result = validate(tmp_path)
        assert any("Duplicate title" in e.message for e in result.errors)

    def test_unique_titles_pass(self, tmp_path: Path) -> None:
        _write(tmp_path, "doc_one.md", _valid_disease_doc("Title One"))
        _write(tmp_path, "doc_two.md", _valid_disease_doc("Title Two"))
        result = validate(tmp_path)
        dup_errors = [e for e in result.errors if "Duplicate title" in e.message]
        assert not dup_errors


# ---------------------------------------------------------------------------
# Empty knowledge base
# ---------------------------------------------------------------------------


class TestEmptyKnowledgeBase:
    def test_empty_directory_passes(self, tmp_path: Path) -> None:
        result = validate(tmp_path)
        assert result.passed

    def test_only_readme_passes(self, tmp_path: Path) -> None:
        _write(tmp_path, "README.md", "# KB README\n")
        result = validate(tmp_path)
        assert result.passed


# ---------------------------------------------------------------------------
# Full valid document passes
# ---------------------------------------------------------------------------


class TestFullValidDocument:
    def test_valid_disease_document_passes(self, tmp_path: Path) -> None:
        _write(tmp_path, "valid_disease.md", _valid_disease_doc())
        result = validate(tmp_path)
        assert result.passed, [e.message for e in result.errors]

    def test_valid_emergency_document_passes(self, tmp_path: Path) -> None:
        _write(tmp_path, "valid_emergency.md", _valid_emergency_doc())
        result = validate(tmp_path)
        assert result.passed, [e.message for e in result.errors]

    def test_valid_faq_document_passes(self, tmp_path: Path) -> None:
        _write(tmp_path, "valid_faq.md", _valid_faq_doc())
        result = validate(tmp_path)
        assert result.passed, [e.message for e in result.errors]

    def test_valid_default_domain_passes(self, tmp_path: Path) -> None:
        _write(tmp_path, "valid_feeding.md", _valid_default_doc())
        result = validate(tmp_path)
        assert result.passed, [e.message for e in result.errors]
