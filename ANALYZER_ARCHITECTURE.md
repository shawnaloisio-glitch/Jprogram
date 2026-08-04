# Analyzer Architecture

**Status:** APPROVED / FROZEN DESIGN (architecture decisions; no code yet)
**Document basis:** Analyzer design principles (handover §15) + approved decisions
**Contract boundary:** Canonical Corpus → Analyzer Utilities → Structured Data Outputs → Lesson Coach / Human Interpretation

This document freezes the Analyzer architecture. It is a design specification, not an implementation. Analyzer code, folders, and skeleton files are intentionally not created by this document.

---

## 1. Purpose

The Analyzer is a **deterministic corpus transformation layer**.

It produces **structured evidence datasets** from the canonical sentence-per-line JSONL corpus.

It does **not**:
- interpret
- recommend
- summarize
- classify
- use LLM calls

Analyzer outputs are data products consumed by later interpretation layers (Lesson Coach / human interpretation).

---

## 2. Folder

Use the existing **Analysis** convention. Do **not** introduce a new Analyzer folder.

Approved structure:

```
C:\Jprogram\Analysis\
├── analyzer modules
└── outputs\
```

- `analyzer modules` — the Analyzer Python modules (see Section 3).
- `outputs\` — derived structured data products written by the Analyzer.

Reason for the root-level `Analysis\` location:
- **Analysis is a consumer of canonical corpus data.** It reads from the canonical corpus and never feeds back into it.
- **It is not part of the corpus-building pipeline.** It is downstream of the Builder and is not a production stage.
- **The existing `paths.ANALYSIS` convention must be preserved** (`ANALYSIS = PROJECT_ROOT / "Analysis"`), rather than introducing a new or nested folder.

---

## 3. Modules

| Module | Responsibility |
|---|---|
| `corpus_loader.py` | Deterministic canonical JSONL reader (preserves canonical record order; sorted, deterministic file discovery). |
| `frequency_analyzer.py` | Occurrence counts; sentence / source / section coverage. |
| `distribution_analyzer.py` | Occurrence spacing metrics (see Section 4). |
| `exposure_analyzer.py` | First appearance; recurrence; exposure spacing; coverage. |
| `expression_analyzer.py` | Parser expression frequency and distribution. |
| `chunk_analyzer.py` | Parser chunk frequency and distribution. Grammar-pattern analysis is represented here (chunks are the canonical grammar layer). |
| `sentence_metrics.py` | Sentence-level statistics. |
| `comparison_analyzer.py` | Cross-source comparisons. |
| `output_writer.py` | Deterministic derived-data writer (see Section 7). |

Design rules (from the Analyzer design principles):
- One script per job/function.
- Each utility reads canonical JSONL (via `corpus_loader`), performs deterministic calculations, writes structured output (via `output_writer`), and has independent tests.
- No utility contains recommendation, interpretation, or classification logic.

---

## 4. Distribution Metrics

All metrics are mechanical measurements only.

- **Primary metric: corpus word-index distance.**
  Distance between occurrences measured in a global canonical word index. The global word index is the word's ordinal position in the corpus's canonical word sequence, derived deterministically by ordering all word occurrences by (sentence_id ascending, word index ascending). The distance between two occurrences is the difference in their global word indices.
- **Secondary metric: character distance.**
  Measured using the canonical recomputed character spans. Within a sentence, the distance is the number of characters between the end of the first occurrence's surface and the start of the next occurrence's surface. Across sentences it is accumulated deterministically using canonical sentence text lengths.
- **Context metric: sentence distance.**
  The difference in canonical `sentence_id`. Sentence distance is context, not the primary measurement.

All metrics are deterministic functions of the canonical corpus evidence (IDs, word indices, recomputed character spans, sentence positions).

---

## 5. Grammar Boundary

There is **no grammar parser**.

The Analyzer does **not** perform:
- particle analysis
- conjugation analysis
- verb-form analysis
- grammar classification

It uses the existing parser evidence only:
- `chunks` (the meaningful grammatical chunk layer)
- `expressions` (the expression layer)

It analyzes these layers mechanically:
- frequency
- recurrence
- distribution

---

## 6. Exposure Boundary

Exposure analysis measures:
- when an item first appears
- number of encounters (recurrence)
- spacing between encounters
- distribution across source material

It does **not** determine:
- learned status
- difficulty
- importance
- I+1 status

Those determinations belong to the interpretation layer, never to the Analyzer.

---

## 7. Output Principles

Analyzer outputs must be:
- **deterministic** — identical input produces identical output, byte-for-byte
- **traceable to canonical IDs** — every derived value references the canonical sentence/word/chunk/expression IDs
- **UTF-8** encoded
- **reproducible** across repeated runs
- **suitable for later AI interpretation** — clean, structured data products

Outputs contain **no recommendations or conclusions**.

---

## 8. Analyzer Independence Principle

**FROZEN DESIGN PRINCIPLE.**

Each analyzer is an independent deterministic view of the canonical corpus.

Rules:
- Every analyzer reads canonical JSONL directly.
- Analyzer outputs are evidence datasets, not inputs for other analyzers.
- No analyzer may depend on another analyzer's generated output files.
- The Comparison Analyzer must also read canonical corpus data directly.
- Analyzer modules may share common utility code only where it does not create a data dependency between analysis products.

Reason:
Analyzer independence prevents cascading errors and hidden coupling.

Benefits:
1. A change or bug in one analyzer cannot silently affect unrelated analyzers.
2. Each analyzer can be independently tested and verified.
3. Analyzer algorithms can evolve independently.
4. The canonical corpus remains the single source of truth.
5. AI interpretation receives multiple independent evidence views rather than a chain of derived assumptions.

Architecture:

```
Canonical Corpus
        |
        +--> Frequency Analyzer
        |
        +--> Distribution Analyzer
        |
        +--> Exposure Analyzer
        |
        +--> Expression Analyzer
        |
        +--> Chunk Analyzer
        |
        +--> Sentence Metrics
        |
        +--> Comparison Analyzer
```

All outputs are independent derived views.

---

*End of Analyzer architecture freeze document.*
