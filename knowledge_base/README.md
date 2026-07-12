# Knowledge Base

The PoultryGuard AI knowledge base is a curated collection of Markdown documents
covering all domains relevant to African poultry farming. It is the primary data
source for the RAG pipeline and the Rule-Based Emergency Advisory Module.

---

## Standards

Before authoring or reviewing any document, read:

| Document | Purpose |
|---|---|
| [`docs/knowledge_engineering.md`](../docs/knowledge_engineering.md) | Writing style, Markdown conventions, citation requirements, terminology, chunking strategy, confidence levels, review process, naming conventions |
| [`docs/knowledge_base_schema.md`](../docs/knowledge_base_schema.md) | Required metadata fields, valid domain values, required section headings per domain, document templates |

These two documents are the authoritative standards for all knowledge base
content. The CI validator enforces the schema automatically; the engineering
standards require human judgement during review.

---

## Structure

```
knowledge_base/
├── diseases/        # Disease identification, symptoms, treatment, prevention
├── vaccination/     # Vaccination schedules and administration guidance
├── climate/         # Housing, ventilation, heat and cold stress management
├── biosecurity/     # Farm biosecurity protocols and checklists
├── feeding/         # Nutrition, feed management, water quality
├── management/      # Flock records and farm operations
├── market/          # Market pricing and economic guidance
├── emergency/       # Critical disease alerts (Emergency Advisory Module)
├── faq/             # Frequently asked questions
├── hausa/           # Hausa-language documents (Sprint 6)
└── references/      # Bibliographic source lists
```

---

## Domains

| Domain | Directory | Description | Sprint |
|---|---|---|---|
| `diseases` | `diseases/` | Poultry disease identification and management | Sprint 2 |
| `vaccination` | `vaccination/` | Vaccination schedules and administration | Sprint 2 |
| `climate` | `climate/` | Housing, ventilation, climate management | Sprint 2 |
| `biosecurity` | `biosecurity/` | Farm biosecurity protocols | Sprint 2 |
| `feeding` | `feeding/` | Nutrition and feed management | Sprint 2 |
| `management` | `management/` | Flock records and farm operations | Sprint 2 |
| `market` | `market/` | Market pricing and economic guidance | Sprint 2 |
| `emergency` | `emergency/` | Critical alerts for Emergency Advisory Module | Sprint 2 |
| `faq` | `faq/` | Frequently asked questions | Sprint 2 |
| `hausa` | `hausa/` | Hausa-language documents | Sprint 6 |

---

## Climate Documents (Sprint 2)

The following climate documents are now available under `knowledge_base/climate/`:

- `housing_ventilation.md` — ventilation control, airflow risks, monitoring, and emergency warning signs
- `heat_stress.md` — heat stress causes, prevention, monitoring, and farmer emergency actions
- `cold_stress.md` — cold stress causes, brooding controls, monitoring, and emergency warning signs

---

## Biosecurity Documents (Sprint 2)

The following biosecurity documents are now available under `knowledge_base/biosecurity/`:

- `farm_biosecurity_checklist.md` — farm entry controls, SOPs, implementation workflow, and emergency response actions
- `visitor_control.md` — visitor access management, compliance monitoring, and outbreak-risk response steps
- `cleaning_and_disinfection.md` — sanitation SOPs, implementation sequence, checklist controls, and emergency correction steps

---

## Feeding Documents (Sprint 2.5)

The following feeding documents are now available under `knowledge_base/feeding/`:

- `broiler_nutrition.md` — broiler feed phase planning, monitoring, emergency signs, and practical feeding control
- `layer_nutrition.md` — layer nutrient priorities, production-stage feeding, monitoring, and corrective actions
- `feed_storage.md` — feed storage hygiene, contamination prevention, and practical quality checks
- `water_quality.md` — drinking-water quality management, monitoring, and emergency response indicators

---

## Adding a Document

1. Read [`docs/knowledge_engineering.md`](../docs/knowledge_engineering.md) in full.
2. Choose the correct domain directory.
3. Copy the template from [`docs/knowledge_base_schema.md`](../docs/knowledge_base_schema.md).
4. Name the file using lowercase and underscores: `example_topic.md`.
5. Fill in all required front matter fields (`title`, `domain`, `tags`, `reviewed`, `sources`).
6. Write all required sections for the domain (see schema document).
7. Keep each H2 section between 100 and 400 words (see chunking strategy in engineering standards).
8. Add at least one Tier 1 or Tier 2 source to `sources` (see citation requirements).
9. Run the validator: `python scripts/validate_knowledge_base.py`
10. Commit on `feature/knowledge-base` and open a pull request.
11. Complete the content review checklist before requesting approval.

---

## Validation

The knowledge base is validated automatically in CI. To run locally:

```bash
python scripts/validate_knowledge_base.py
```

The validator checks:

- Required metadata fields present and correctly typed
- Valid `domain` value
- Required section headings for the document's domain
- Non-empty `sources` list
- No duplicate `title` values across the knowledge base
- Filename naming conventions (lowercase, underscores, `.md`)

---

## Content Status

| Domain | Documents | Reviewed | Sprint Target |
|---|---|---|---|
| diseases | 10 | 0 | Sprint 2 |
| vaccination | 5 | 0 | Sprint 2 |
| climate | 3 | 0 | Sprint 2 |
| biosecurity | 3 | 0 | Sprint 2 |
| feeding | 4 | 0 | Sprint 2 |
| management | 3 | 0 | Sprint 2 |
| market | 0 | 0 | Sprint 2 |
| emergency | 3 | 0 | Sprint 2 |
| faq | 5 | 0 | Sprint 2 |
| hausa | 0 | 0 | Sprint 6 |

---

## Document Inventory Targets (Sprint 2)

| Domain | Minimum | Priority Documents |
|---|---|---|
| diseases | 8 | Newcastle disease, Avian Influenza, Gumboro disease, Marek's disease, Coccidiosis, Fowl Pox, Fowl Typhoid, Infectious Bronchitis |
| vaccination | 4 | Broiler schedule, Layer schedule, Vaccine storage, Vaccine administration |
| climate | 3 | Housing ventilation, Heat stress management, Cold stress management |
| biosecurity | 3 | Farm biosecurity checklist, Visitor protocols, Disinfection guide |
| feeding | 4 | Broiler nutrition, Layer nutrition, Feed storage, Water quality |
| management | 3 | Flock records, Mortality tracking, Production records |
| market | 2 | Market pricing guidance, Cost management |
| emergency | 3 | Newcastle disease emergency, Avian Influenza emergency, Mass mortality emergency |
| faq | 5 | Common farmer questions across all domains |
| **Total** | **35** | |

---

## References

- Engineering standards: [`docs/knowledge_engineering.md`](../docs/knowledge_engineering.md)
- Schema: [`docs/knowledge_base_schema.md`](../docs/knowledge_base_schema.md)
- Validator: [`scripts/validate_knowledge_base.py`](../scripts/validate_knowledge_base.py)
- RAG design: [`docs/architecture/rag_design.md`](../docs/architecture/rag_design.md)
