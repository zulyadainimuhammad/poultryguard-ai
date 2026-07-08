# Knowledge Engineering Standards

## Purpose

This document defines the standards every contributor must follow when authoring,
reviewing, or updating documents in the PoultryGuard AI knowledge base. It covers
writing style, Markdown conventions, metadata schema, citation requirements,
terminology, document chunking strategy for RAG, confidence levels, the review
process, and naming conventions.

These standards exist to ensure that every document is:

- factually accurate and traceable to authoritative sources
- consistently structured so the RAG chunker produces high-quality retrieval units
- readable by farmers, extension officers, and domain experts without technical
  background
- maintainable by contributors who are not software engineers

Read this document before authoring any knowledge base content. The companion
schema reference is [`docs/knowledge_base_schema.md`](knowledge_base_schema.md).

---

## 1. Writing Style

### 1.1 Audience

The primary audience is a smallholder poultry farmer in sub-Saharan Africa with
limited formal education. The secondary audience is an agricultural extension
officer who may read documents aloud or summarise them for farmers.

Write for the primary audience at all times. The LLM will adapt the register when
generating a response; the knowledge base itself must be clear and unambiguous at
the source.

### 1.2 Voice and Tone

| Rule | Correct | Incorrect |
|---|---|---|
| Use active voice | "Vaccinate chicks on day 7." | "Chicks should be vaccinated on day 7." |
| Use plain English | "The bird cannot breathe properly." | "The avian subject exhibits respiratory distress." |
| Be direct | "Call a veterinarian immediately." | "It may be advisable to consider contacting a veterinarian." |
| Use second person for instructions | "Separate sick birds from the flock." | "Sick birds should be separated from the flock." |
| Avoid jargon without definition | "Newcastle disease (a viral infection)" | "Newcastle disease (paramyxovirus type 1 serotype)" |

### 1.3 Sentence and Paragraph Length

- Maximum sentence length: 25 words.
- Maximum paragraph length: 4 sentences.
- One idea per paragraph.
- Use bullet lists for three or more parallel items.
- Use numbered lists when order matters (steps, sequences).

### 1.4 Numbers and Units

- Spell out numbers one through nine; use digits for 10 and above.
- Always include units: "5 kg", "37 °C", "2 litres per bird per day".
- Use metric units throughout. Add imperial equivalents in parentheses only when
  the target audience is likely to use them.
- Express percentages as digits: "5% mortality rate", not "five percent".
- Express dates in ISO 8601 format in metadata: `2026-07-01`. In body text, use
  "1 July 2026" or "July 2026".

### 1.5 Safety and Liability Language

Every document that describes disease treatment, drug dosages, or emergency
response must include the following disclaimer in the `## When to Call a
Veterinarian` section (disease documents) or `## Emergency Response` section
(emergency documents):

> **Always consult a licensed veterinarian before administering any drug or
> vaccine. The guidance in this document is for general awareness only and does
> not replace professional veterinary advice.**

Do not invent drug names, dosages, or treatment protocols. If a specific dosage
is not confirmed by a cited source, omit it and direct the farmer to a
veterinarian.

---

## 2. Markdown Conventions

### 2.1 Heading Hierarchy

```
# Document Title          ← H1: exactly one per document, matches `title` field
## Section Name           ← H2: required sections defined in schema
### Subsection Name       ← H3: optional, use sparingly
#### Sub-subsection       ← H4: avoid; restructure content instead
```

Rules:
- Never skip heading levels (e.g., do not jump from H2 to H4).
- H2 headings must exactly match the required section names for the domain (see
  `docs/knowledge_base_schema.md`). Do not paraphrase or reorder them.
- H3 headings are optional and free-form within a section.
- The H1 title must match the `title` field in the YAML front matter exactly.

### 2.2 Lists

Use unordered lists (`-`) for non-sequential items:

```markdown
- Newcastle disease
- Gumboro disease
- Avian Influenza
```

Use ordered lists (`1.`) for sequential steps:

```markdown
1. Isolate the sick bird immediately.
2. Disinfect the housing area.
3. Contact a veterinarian.
```

Do not mix list types within a single list. Do not nest lists more than two
levels deep.

### 2.3 Emphasis

- Use `**bold**` for critical warnings, key terms on first use, and action items.
- Use `*italic*` for scientific names (e.g., *Marek's disease virus*) and
  non-English terms.
- Do not use bold or italic for decoration.
- Do not use ALL CAPS for emphasis.

### 2.4 Tables

Use tables for structured comparisons, schedules, and reference data:

```markdown
| Age (days) | Vaccine | Route |
|---|---|---|
| 7 | Newcastle (La Sota) | Eye drop |
| 14 | Gumboro (IBD) | Drinking water |
```

- Every table must have a header row.
- Align columns with `|---|` (left-aligned is the default and preferred).
- Do not use tables for content that reads naturally as prose.

### 2.5 Code Blocks

Do not use code blocks in knowledge base documents. Code blocks are reserved for
technical documentation under `docs/`.

### 2.6 Links

Do not include external hyperlinks in knowledge base documents. The system
operates offline; links will not resolve at runtime. Cite sources in the
`## References` section using plain text bibliographic format instead.

Internal cross-references between knowledge base documents are permitted using
relative Markdown links:

```markdown
See also: [Vaccination Schedule for Broilers](../vaccination/vaccination_schedule_broilers.md)
```

### 2.7 Images

Do not embed images in knowledge base documents in the MVP. The RAG pipeline
processes text only. Images may be added to `assets/` for the UI layer in a
later sprint.

### 2.8 Blank Lines

- One blank line between paragraphs.
- One blank line before and after every heading.
- One blank line before and after every list.
- One blank line before and after every table.
- No trailing whitespace on any line.

---

## 3. Metadata Schema

The YAML front matter block is the machine-readable identity of every document.
It must appear at the very top of the file, before any Markdown content.

### 3.1 Required Fields

| Field | Type | Constraints | Example |
|---|---|---|---|
| `title` | string | Unique across the entire knowledge base; matches H1 exactly | `Newcastle Disease` |
| `domain` | string | One of the ten valid domain values | `diseases` |
| `tags` | list of strings | Minimum 3 tags; lowercase; no spaces (use underscores) | `[newcastle, paramyxovirus, respiratory]` |
| `reviewed` | boolean | `false` until a domain expert has approved the content | `false` |
| `sources` | list of strings | Minimum 1; full bibliographic citation string | `["FAO. (2021). Newcastle Disease."]` |

### 3.2 Optional Fields

| Field | Type | Constraints | Example |
|---|---|---|---|
| `confidence` | string | One of: `high`, `medium`, `low` | `high` |
| `severity` | string | `emergency` domain only: `CRITICAL`, `WARNING`, `INFO` | `CRITICAL` |
| `language` | string | ISO 639-1 code; omit for English | `ha` |
| `last_updated` | string | ISO 8601 date | `2026-07-01` |
| `related_documents` | list of strings | Relative paths to related KB documents | `["../vaccination/vaccination_schedule_broilers.md"]` |

### 3.3 Tag Conventions

Tags are used by the RAG retrieval system to support domain-scoped search and
by the Emergency Advisory Module for keyword matching.

- Use lowercase only: `newcastle`, not `Newcastle`.
- Use underscores for multi-word tags: `avian_influenza`, not `avian influenza`.
- Include the disease or topic name, the causative agent where known, and the
  primary clinical signs.
- Include the production type where relevant: `broiler`, `layer`, `chick`.
- Minimum 3 tags per document; aim for 5–8.

Example tag set for a Newcastle disease document:

```yaml
tags: [newcastle, paramyxovirus, respiratory, neurological, torticollis, mortality, broiler, layer]
```

---

## 4. Citation Requirements

### 4.1 Mandatory Sourcing

Every factual claim in a knowledge base document must be traceable to at least
one source listed in the `sources` front matter field. This includes:

- Disease names, causative agents, and transmission routes
- Vaccination schedules and dosages
- Mortality rates and morbidity statistics
- Drug names and treatment protocols
- Climate thresholds (temperature, humidity, ventilation rates)
- Nutritional requirements and feed compositions
- Market prices and economic data

### 4.2 Acceptable Sources

Sources are ranked by authority. Use the highest-authority source available.

| Tier | Source Type | Examples |
|---|---|---|
| 1 | International veterinary authority | OIE/WOAH Technical Disease Cards, FAO Animal Health publications |
| 2 | Peer-reviewed journal articles | Poultry Science, Avian Diseases, Preventive Veterinary Medicine |
| 3 | National veterinary authority | NAFDAC (Nigeria), DVS (Kenya), DAFF (South Africa) guidelines |
| 4 | University extension services | University of Ibadan, Egerton University, ILRI publications |
| 5 | Reputable NGO publications | ACIAR, CABI, Heifer International technical guides |

### 4.3 Unacceptable Sources

The following source types must never be cited:

- Wikipedia or any wiki-style collaborative site
- Undated web pages without institutional authorship
- Social media posts, blogs, or forums
- Commercial product marketing materials
- AI-generated content

### 4.4 Citation Format

Use APA 7th edition format for all citations in the `sources` field and the
`## References` section.

**Journal article:**
```
Author, A. A., & Author, B. B. (Year). Title of article. Journal Name, volume(issue), pages. https://doi.org/xxxxx
```

**Book or report:**
```
Organisation Name. (Year). Title of publication. Publisher.
```

**Technical card or fact sheet:**
```
OIE/WOAH. (Year). [Disease Name] — Technical Disease Card. World Organisation for Animal Health.
```

**Government guideline:**
```
Ministry/Department Name. (Year). Title of guideline. Government of [Country].
```

### 4.5 In-text Attribution

Do not use in-text citation markers (e.g., `[1]`, `(FAO, 2021)`) in the body of
knowledge base documents. The `## References` section at the end of each document
lists all sources. The RAG prompt builder surfaces source metadata to the LLM
separately.

---

## 5. Terminology Standards

### 5.1 Preferred Terms

Use the following standardised terms consistently across all documents. Do not
use synonyms or regional variants unless they are introduced as alternatives in
parentheses on first use.

| Preferred Term | Do Not Use | Notes |
|---|---|---|
| Newcastle disease | ND, pseudo-fowl pest, Ranikhet disease | Introduce alternatives on first use only |
| Avian Influenza | bird flu, AI | "Highly Pathogenic Avian Influenza (HPAI)" for H5N1/H5N8 strains |
| Gumboro disease | Infectious Bursal Disease, IBD | Use "Gumboro disease (IBD)" on first use |
| Marek's disease | MD | Use full name throughout |
| Coccidiosis | cocci | Use full name throughout |
| Fowl Pox | fowlpox, chicken pox | "Fowl Pox" (two words, capitalised) |
| broiler | meat bird, table bird | Use "broiler" consistently |
| layer | laying hen, egg bird | Use "layer" consistently |
| chick | day-old chick, DOC | "chick" for birds under 4 weeks; "DOC" only in vaccination schedules |
| flock | birds, chickens, poultry | "flock" for the group; "bird" for an individual |
| mortality rate | death rate, loss rate | Express as a percentage: "5% mortality rate" |
| morbidity rate | sickness rate | Express as a percentage |
| veterinarian | vet, animal doctor | Use "veterinarian" in formal text; "vet" acceptable in FAQ domain |
| biosecurity | bio-security, bio security | One word, no hyphen |
| disinfectant | disinfector, sanitiser | "disinfectant" for chemical agents; "sanitiser" only for human hand hygiene |

### 5.2 Scientific Names

Write scientific names in italics on first use in each document, followed by the
common name in parentheses:

```markdown
*Paramyxovirus avium* (Newcastle disease virus)
*Marek's disease virus* (MDV)
*Eimeria* spp. (coccidiosis)
```

Subsequent references in the same document may use the common name alone.

### 5.3 Units and Measurements

| Quantity | Unit | Example |
|---|---|---|
| Temperature | °C | "38 °C" |
| Weight | kg or g | "2.5 kg live weight" |
| Volume | litres or mL | "2 litres per bird per day" |
| Area | m² | "0.1 m² per bird" |
| Concentration | % or mg/kg | "0.5% solution" |
| Age | days or weeks | "day 7", "week 3" |
| Mortality | % | "10% mortality rate" |

### 5.4 Drug and Vaccine Names

- Use the International Nonproprietary Name (INN) for drugs, not brand names.
- Use the full vaccine strain name on first use: "Newcastle disease vaccine
  (La Sota strain)".
- Never recommend a specific commercial brand.
- Never specify a dosage unless it is confirmed by a Tier 1 or Tier 2 source and
  the source is cited.

---

## 6. Document Chunking Strategy for RAG

This section defines how knowledge base documents should be structured to produce
high-quality retrieval chunks. The RAG chunker (`rag/chunking/markdown_chunker.py`)
splits documents on H2 heading boundaries first, then applies sliding-window
splitting for sections that exceed the token budget.

### 6.1 Chunk Boundaries

The chunker treats each H2 section as a natural chunk boundary. This means:

- **Each H2 section should be self-contained.** A farmer should be able to read
  one section and understand it without reading the others.
- **Avoid forward references within a section.** Do not write "as described in
  the Symptoms section above" — repeat the key fact instead.
- **Keep each H2 section between 100 and 400 words.** Sections shorter than 100
  words may not contain enough context for retrieval. Sections longer than 400
  words will be split mid-content by the sliding-window algorithm, which may
  break semantic coherence.

### 6.2 Section Word Count Targets

| Section | Target Word Count | Notes |
|---|---|---|
| `## Overview` | 80–150 words | Introduce the topic; include the most important retrieval keywords |
| `## Symptoms` | 150–300 words | List all observable signs; use bullet points |
| `## Treatment and Management` | 150–300 words | Step-by-step actions; include veterinarian disclaimer |
| `## Prevention and Vaccination` | 150–250 words | Vaccine names, schedule references, biosecurity links |
| `## When to Call a Veterinarian` | 80–150 words | Specific escalation criteria only |
| `## Key Information` | 150–300 words | Core facts for non-disease domains |
| `## Recommendations` | 100–250 words | Numbered steps; practical and actionable |
| `## References` | No limit | One citation per line; not indexed for retrieval |

### 6.3 Keyword Density

The embedding model (`all-MiniLM-L6-v2`) produces better retrieval when the
most important terms appear in the first 50 words of each section. Write the
`## Overview` section so that the disease name, causative agent, and primary
clinical signs all appear in the first two sentences.

Example of a well-structured Overview opening:

> Newcastle disease is a highly contagious viral infection of poultry caused by
> *Paramyxovirus avium*. It affects chickens, turkeys, and other birds, causing
> respiratory distress, neurological signs, and sudden death. Outbreaks can kill
> an entire flock within days.

### 6.4 Avoid Retrieval Anti-patterns

| Anti-pattern | Problem | Fix |
|---|---|---|
| Very short sections (< 80 words) | Insufficient context for embedding | Merge with adjacent section or expand content |
| Very long sections (> 500 words) | Sliding-window split breaks semantic units | Split into H3 subsections or separate documents |
| Pronoun-heavy text ("it", "they", "this") | Chunks lose referential context when split | Repeat the subject noun in each paragraph |
| Tables without prose context | Table rows embed poorly in isolation | Precede every table with a one-sentence introduction |
| Numbered lists without a lead sentence | List items lose context when chunked | Always introduce a list with a sentence |

---

## 7. Confidence Levels

The optional `confidence` metadata field records the author's assessment of the
factual reliability of the document's content. It is used by the evaluation
framework to weight answer quality scores and by reviewers to prioritise review
effort.

### 7.1 Confidence Values

| Value | Meaning | When to Use |
|---|---|---|
| `high` | All claims are supported by Tier 1 or Tier 2 sources; content has been reviewed by a domain expert | After expert review and source verification |
| `medium` | Most claims are supported by Tier 3 or Tier 4 sources; content is plausible but not fully verified | Initial drafts with good sourcing |
| `low` | Some claims are unsourced or based on Tier 5 sources; content requires expert review before use | First drafts, placeholder content |

### 7.2 Default Confidence

Omit the `confidence` field when the document has not yet been assessed. The
validator does not require it. The evaluation framework treats missing confidence
as `low`.

### 7.3 Confidence and the `reviewed` Flag

The `reviewed` field and `confidence` field are independent:

- `reviewed: true` means a domain expert has read and approved the document.
- `confidence: high` means the author assessed the sourcing as strong.

A document can have `confidence: high` and `reviewed: false` (well-sourced but
not yet reviewed). It should not have `confidence: low` and `reviewed: true`
(a reviewer should not approve low-confidence content without improving it).

---

## 8. Review Process

### 8.1 Authoring Stage

1. Author creates the document on a feature branch (`feature/knowledge-base`).
2. Author runs `python scripts/validate_knowledge_base.py` locally.
3. Author fixes all validator errors before opening a pull request.
4. Author sets `reviewed: false` and `confidence: medium` or `low`.

### 8.2 Pull Request Stage

1. Author opens a pull request from `feature/knowledge-base` to `main`.
2. CI runs the validator automatically. The PR is blocked if validation fails.
3. A second contributor performs a content review using the checklist below.
4. The reviewer checks out the branch and reads the document in full.

### 8.3 Content Review Checklist

The reviewer must confirm all of the following before approving:

- [ ] All factual claims are supported by a cited source.
- [ ] No drug dosages or treatment protocols are present without a Tier 1 or
      Tier 2 citation.
- [ ] The veterinarian disclaimer is present in all required sections.
- [ ] All required sections are present and contain substantive content
      (not placeholder text).
- [ ] Section word counts are within the targets defined in Section 6.2.
- [ ] Writing style follows Section 1 (active voice, plain English, short
      sentences).
- [ ] Terminology follows Section 5 (preferred terms used consistently).
- [ ] No external hyperlinks are present in the document body.
- [ ] The `title` field matches the H1 heading exactly.
- [ ] Tags are lowercase, use underscores, and number at least 3.
- [ ] The `sources` field lists all sources cited in `## References`.

### 8.4 Approval Stage

1. Reviewer approves the pull request.
2. Author updates `reviewed: true` in the front matter.
3. Author updates `confidence` to `high` if all sources are Tier 1 or Tier 2.
4. PR is merged to `main`.
5. The FAISS index is rebuilt via `python scripts/build_index.py`.

### 8.5 Update Process

When a document requires factual updates:

1. Create a new branch: `fix/knowledge-base-<document-name>`.
2. Make changes and update `last_updated` in the front matter.
3. Reset `reviewed: false` until the update has been reviewed.
4. Follow the same PR and review process as a new document.

---

## 9. Naming Conventions

### 9.1 File Names

| Rule | Correct | Incorrect |
|---|---|---|
| Lowercase only | `newcastle_disease.md` | `Newcastle_Disease.md` |
| Underscores, not hyphens | `heat_stress_management.md` | `heat-stress-management.md` |
| `.md` extension | `broiler_nutrition.md` | `broiler_nutrition.txt` |
| No spaces | `flock_records.md` | `flock records.md` |
| Descriptive and specific | `vaccination_schedule_broilers.md` | `schedule1.md` |
| No version numbers in filename | `newcastle_disease.md` | `newcastle_disease_v2.md` |
| Maximum 40 characters | `infectious_bronchitis.md` (22 chars) | `infectious_bronchitis_disease_overview_and_management.md` |

### 9.2 Directory Names

Directories follow the same lowercase-underscore convention as files. The ten
valid domain directories are fixed and must not be renamed:

```
diseases/  vaccination/  climate/  biosecurity/  feeding/
management/  market/  emergency/  faq/  hausa/
```

Do not create subdirectories within domain directories. All documents for a
domain live at the top level of that domain's directory.

### 9.3 Title Conventions

The `title` field and the H1 heading must be identical. Titles follow title case:

| Rule | Correct | Incorrect |
|---|---|---|
| Title case | `Newcastle Disease` | `newcastle disease` |
| No trailing punctuation | `Broiler Nutrition` | `Broiler Nutrition.` |
| Specific, not generic | `Vaccination Schedule for Broilers` | `Vaccination` |
| No version numbers | `Heat Stress Management` | `Heat Stress Management v1` |
| Match filename semantics | File: `heat_stress_management.md` → Title: `Heat Stress Management` | File: `heat_stress.md` → Title: `Managing Heat Stress in Poultry Houses` |

### 9.4 Tag Naming

| Rule | Correct | Incorrect |
|---|---|---|
| Lowercase | `newcastle` | `Newcastle` |
| Underscores for multi-word | `avian_influenza` | `avian-influenza`, `avian influenza` |
| Specific | `respiratory_disease` | `disease` |
| No duplicates within a document | `[newcastle, respiratory]` | `[newcastle, newcastle, respiratory]` |

---

## 10. Document Inventory Targets

The following table defines the minimum document count per domain for Sprint 2.
These targets ensure sufficient knowledge base coverage for the RAG evaluation
in Sprint 3.

| Domain | Minimum Documents | Priority Documents |
|---|---|---|
| `diseases` | 8 | Newcastle disease, Avian Influenza, Gumboro disease, Marek's disease, Coccidiosis, Fowl Pox, Fowl Typhoid, Infectious Bronchitis |
| `vaccination` | 4 | Broiler schedule, Layer schedule, Vaccine storage, Vaccine administration |
| `climate` | 3 | Housing ventilation, Heat stress management, Cold stress management |
| `biosecurity` | 3 | Farm biosecurity checklist, Visitor protocols, Disinfection guide |
| `feeding` | 4 | Broiler nutrition, Layer nutrition, Feed storage, Water quality |
| `management` | 3 | Flock records, Mortality tracking, Production records |
| `market` | 2 | Market pricing guidance, Cost management |
| `emergency` | 3 | Newcastle disease emergency, Avian Influenza emergency, Mass mortality emergency |
| `faq` | 5 | Common farmer questions across all domains |
| **Total** | **35** | |

---

## References

- [FAO Animal Production and Health](https://www.fao.org/animal-production-health/en/)
- [OIE/WOAH Technical Disease Cards](https://www.woah.org/en/what-we-do/animal-health-and-welfare/animal-diseases/)
- [APA 7th Edition Citation Guide](https://apastyle.apa.org/style-grammar-guidelines/references)
- [Plain Language Guidelines — plainlanguage.gov](https://www.plainlanguage.gov/guidelines/)
- See also: [`docs/knowledge_base_schema.md`](knowledge_base_schema.md),
  [`knowledge_base/README.md`](../knowledge_base/README.md),
  [`docs/architecture/rag_design.md`](architecture/rag_design.md)
