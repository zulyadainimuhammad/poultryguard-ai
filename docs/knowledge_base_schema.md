# Knowledge Base Schema

## Purpose

This document defines the mandatory schema for all Markdown documents in the PoultryGuard AI knowledge base. Every document must conform to this schema before it is accepted into the repository. The `scripts/validate_knowledge_base.py` validator enforces this schema automatically in CI.

---

## Background

A consistent schema across all knowledge base documents is essential for:

1. **Retrieval quality** — the RAG chunker relies on predictable heading structure to produce semantically coherent chunks.
2. **Metadata integrity** — the FAISS index stores domain, source, and section metadata per chunk; missing or invalid metadata degrades retrieval.
3. **Factual accountability** — every document must cite sources so claims can be verified by domain experts and ADTC reviewers.
4. **Validator automation** — CI enforces schema compliance on every pull request, preventing malformed documents from entering the index.

---

## YAML Front Matter

Every knowledge base document must begin with a YAML front matter block delimited by `---`.

### Required Fields

| Field | Type | Description | Example |
|---|---|---|---|
| `title` | string | Human-readable document title, unique across the knowledge base | `Newcastle Disease` |
| `domain` | string | Knowledge base domain (see valid values below) | `diseases` |
| `tags` | list of strings | Searchable keywords relevant to the document | `[newcastle, paramyxovirus, respiratory]` |
| `reviewed` | boolean | Whether the document has been reviewed by a domain expert | `false` |
| `sources` | list of strings | Bibliographic references supporting the document's claims | `["FAO, 2021"]` |

### Optional Fields

| Field | Type | Description | Example |
|---|---|---|---|
| `language` | string | ISO 639-1 language code; omit for English | `ha` |
| `severity` | string | For `emergency` domain only: `CRITICAL`, `WARNING`, or `INFO` | `CRITICAL` |
| `last_updated` | string | ISO 8601 date of last content update | `2026-07-01` |

### Example Front Matter

```yaml
---
title: Newcastle Disease
domain: diseases
tags: [newcastle, paramyxovirus, respiratory, neurological, torticollis]
reviewed: false
sources:
  - "FAO. (2021). Newcastle Disease. Animal Production and Health Division."
  - "OIE. (2021). Newcastle Disease — Technical Disease Card."
---
```

---

## Valid Domain Values

The `domain` field must be one of the following values exactly:

| Value | Directory | Description |
|---|---|---|
| `diseases` | `knowledge_base/diseases/` | Poultry disease identification and management |
| `vaccination` | `knowledge_base/vaccination/` | Vaccination schedules and administration |
| `climate` | `knowledge_base/climate/` | Housing, ventilation, and climate management |
| `biosecurity` | `knowledge_base/biosecurity/` | Farm biosecurity protocols and checklists |
| `feeding` | `knowledge_base/feeding/` | Nutrition, feed management, and water quality |
| `management` | `knowledge_base/management/` | Flock records and farm operations |
| `market` | `knowledge_base/market/` | Market pricing and economic guidance |
| `emergency` | `knowledge_base/emergency/` | Critical disease alerts for the Emergency Advisory Module |
| `faq` | `knowledge_base/faq/` | Frequently asked questions |
| `hausa` | `knowledge_base/hausa/` | Hausa-language documents |

---

## Required Sections

Every document must contain the following Markdown headings (H2 level, `##`). The exact heading text must match.

### Standard Documents (all domains except `emergency` and `faq`)

| Heading | Purpose |
|---|---|
| `## Overview` | Brief description of the topic |
| `## Key Information` | Core factual content for retrieval |
| `## Recommendations` | Practical guidance for farmers |
| `## References` | Bibliographic sources |

### Disease Domain (`domain: diseases`)

Disease documents must include these additional sections:

| Heading | Purpose |
|---|---|
| `## Symptoms` | Clinical signs and observable indicators |
| `## Treatment and Management` | Response actions and treatment options |
| `## Prevention and Vaccination` | Preventive measures and vaccine guidance |
| `## When to Call a Veterinarian` | Escalation criteria |

### Emergency Domain (`domain: emergency`)

| Heading | Purpose |
|---|---|
| `## Overview` | Brief description of the emergency condition |
| `## Warning Signs` | Symptoms that trigger this emergency alert |
| `## Emergency Response` | Immediate actions the farmer must take |
| `## Do Not` | Actions to avoid during the emergency |
| `## References` | Bibliographic sources |

### FAQ Domain (`domain: faq`)

| Heading | Purpose |
|---|---|
| `## Question` | The farmer question being answered |
| `## Answer` | The direct answer |
| `## References` | Bibliographic sources |

---

## Filename Conventions

| Rule | Example |
|---|---|
| Lowercase only | `newcastle_disease.md` ✅ `Newcastle_Disease.md` ❌ |
| Words separated by underscores | `heat_stress_management.md` ✅ `heat-stress-management.md` ❌ |
| `.md` extension only | `newcastle_disease.md` ✅ `newcastle_disease.txt` ❌ |
| No spaces | `newcastle_disease.md` ✅ `newcastle disease.md` ❌ |
| Descriptive, not generic | `broiler_nutrition.md` ✅ `document1.md` ❌ |

---

## Sources Requirement

The `sources` field must not be empty. Every document must cite at least one authoritative source. Acceptable source formats:

- FAO publications
- OIE/WOAH technical cards
- Peer-reviewed journal articles (APA or Vancouver format)
- National veterinary authority guidelines
- University extension service publications

Unacceptable sources:
- Wikipedia
- Undated web pages without institutional authorship
- Social media

---

## Complete Document Template

Copy this template when creating a new knowledge base document:

```markdown
---
title: <Document Title>
domain: <domain_value>
tags: [tag1, tag2, tag3]
reviewed: false
sources:
  - "<Author. (Year). Title. Publisher.>"
---

# <Document Title>

## Overview

<Brief description of the topic — 2 to 4 sentences.>

## Key Information

<Core factual content. Use bullet points or short paragraphs.>

## Recommendations

<Practical guidance for farmers. Use numbered steps where order matters.>

## References

- <Author. (Year). Title. Publisher.>
```

For disease documents, add after `## Overview`:

```markdown
## Symptoms

<Clinical signs and observable indicators.>

## Treatment and Management

<Response actions. Always note that a veterinarian should be consulted.>

## Prevention and Vaccination

<Preventive measures and vaccine schedule references.>

## When to Call a Veterinarian

<Specific escalation criteria — e.g., mortality rate, flock-wide spread.>
```

---

## Validator

The `scripts/validate_knowledge_base.py` script enforces this schema. Run it locally before committing:

```bash
python scripts/validate_knowledge_base.py
```

It checks:
- Required YAML front matter fields present and correctly typed
- `domain` value is one of the valid values
- Required section headings present for the document's domain
- `sources` list is non-empty
- No duplicate `title` values across the knowledge base
- Filename follows naming conventions (lowercase, underscores, `.md`)

CI runs this validator automatically on every pull request.

---

## References

- [Keep a Changelog](https://keepachangelog.com) — inspiration for structured, consistent documentation
- [FAO Animal Production and Health](https://www.fao.org/animal-production-health/en/)
- [OIE/WOAH Technical Disease Cards](https://www.woah.org/en/what-we-do/animal-health-and-welfare/animal-diseases/)
- See also: `knowledge_base/README.md`, `scripts/validate_knowledge_base.py`
