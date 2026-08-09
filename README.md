# Japanese Corpus Pipeline

## Purpose

The Japanese Corpus Pipeline converts Japanese source material into a structured, canonical JSONL corpus. That corpus is the finished product of this project — Jprogram's scope ends there; it does not itself perform linguistic analysis (see the Pipeline section below for where analysis now lives).

Supported sources include:

- Podcast transcripts
- Anime subtitles
- (Future) Manga text
- (Future) Visual novels
- (Future) Other Japanese text sources

Regardless of the source, every document is converted into the same canonical representation before processing.

The corpus is designed to support downstream questions such as:

- Vocabulary overlap
- Grammar overlap
- Expression overlap
- Frequency analysis
- Comprehensibility (I+1)
- Source comparisons
- Longitudinal learning progression

---

# Pipeline

Current architecture:

```
Raw Source
      │
      ▼
Source Intake (utility + artifact writers implemented)
      │
      ▼
Cleaner
      │
      ▼
Clean Text
      │
      ▼
Job Builder
      │
      ▼
Request Builder
      │
      ▼
DeepSeek Parser
      (deepseek-v4-flash, non-thinking,
       response_format json_object,
       max_tokens, hybrid fixed-position-array
       intermediate format)
      │
      ▼
Response Validator
      │
      ▼
Corpus Builder
      (deterministic normalization,
       span/chunk-text recomputation,
       global positioning, provenance)
      │
      ▼
Canonical Sentence-per-line JSONL Corpus
      │
      ▼
Application Shell (Sources / Processing)
```

Jprogram's own scope ends at the finished canonical JSONL corpus
(2026-08-09 architecture decision). Analysis reads that corpus but is no
longer built or run inside Jprogram — it moved to Language Coach, which
has independently rebuilt it. See `Archive/Analysis/` and
`Archive/ANALYZER_ARCHITECTURE.md` for the retired implementation.

### Source Intake Implementation Status

Source Intake is implemented under the "one program = one task" principle.

Implemented:
- Utility layer: `Source Intake\hashing.py`, `source_id.py`, `schemas.py`.
- Artifact writers: `Source Intake\registry.py` (Source Registry artifact creation), `Source Intake\cleaning_job.py` (Cleaning Job artifact creation), `Source Intake\cleaning_result.py` (Cleaning Result artifact creation).
- Coordinator + duplicate detection: `Source Intake\source_intake.py`, `duplicate_check.py`, `resolver.py`.
- Schema validation, deterministic JSON serialization (UTF-8, `ensure_ascii=False`, `sort_keys=True`), and atomic artifact writes.

Cleaner execution and pipeline orchestration are implemented (Production
Manager runs the stage programs). The Application Shell (`app.py`) provides the
Sources / Processing UI. The Source Package workflow and Handoff
(`Source Builder\source_package.py`, `Source Builder\handoff.py`) create the
intake artifacts from saved sources. See `ARCHITECTURE_CURRENT.md` and
`SOURCE_PACKAGE_HANDOFF.md`.

Architecture: Source creation → Source Package → Handoff → Cleaner → Data Processor → Canonical Corpus. (Downstream analysis is a separate project, Language Coach — see `C:\AI Development Projects\Shared\ECOSYSTEM_OVERVIEW.md`.)

---

# Project Philosophy

The project is intentionally built from small, single-purpose scripts.

Each script should:

- perform one job
- produce one output
- be deterministic whenever possible
- be independently testable
- be restartable whenever practical

No script should attempt to perform multiple unrelated tasks.

---

# Pipeline Rules

## Rule 1

Mechanical scripts may remove formatting and metadata, but they must never modify linguistic content.

Allowed:

- Remove timestamps
- Remove subtitle numbers
- Remove duplicate blank lines
- Trim whitespace
- Normalize line endings
- Remove UTF-8 BOM

Not allowed:

- Merge sentences
- Split sentences
- Correct grammar
- Correct spelling
- Add punctuation
- Remove punctuation
- Infer missing text
- Translate
- Rewrite dialogue

Only the AI parser is permitted to interpret Japanese.

---

## Rule 2

Only one script communicates with an LLM.

All other scripts are deterministic Python programs.

---

## Rule 3

Every processing stage produces a reusable artifact.

Examples:

```
Raw Transcript

↓

Clean Transcript

↓

Jobs

↓

API Responses

↓

Validated Jobs

↓

JSONL Corpus
```

Intermediate files exist to support validation and recovery.

---

## Rule 4

No API work should ever be repeated unnecessarily.

Successful work must survive:

- program crashes
- network failures
- API failures
- computer restarts

The pipeline should always resume from the last successful job whenever possible.

---

## Rule 5

The JSONL corpus is the single source of truth.

Analysis scripts never modify corpus data.

They only read it.

---

# Folder Philosophy

Raw folders contain untouched source material.

Cleaned Archive contains mechanically cleaned text.

Data Processor contains temporary processing artifacts and final JSONL datasets.

Logs contain execution history.

Data and logs remain separate.

---

# Processing Philosophy

The processor does not know whether text originated from:

- a podcast
- subtitles
- manga
- visual novels

Once cleaned, all sources become clean Japanese text.

From that point onward, every source follows the same processing pipeline.

---

# Design Goals

Priority order:

1. Data integrity
2. Recoverability
3. Deterministic processing
4. Low API cost
5. Ease of maintenance
6. Ease of extension

The architecture should allow new source types to be added by writing a new cleaner rather than modifying the processing pipeline.

---

# Corpus Parser Data-Preservation Architecture

## Approved Decision

The processor preserves raw linguistic evidence.

The analyzer performs statistical analysis and higher-level corpus analysis.

The processor must NOT calculate frequency, dispersion, clustering, inter-occurrence distance, or other statistics. It must preserve enough evidence that future Python analyzers can calculate those measurements without rerunning DeepSeek.

## Approved Corpus Evidence Layers

### 1. Sentence Level (Critical)

Preserve the complete original Japanese sentence.

Each sentence must have stable source/position information.

Required for:
- future Anki sentence extraction
- retrieving the original context for any word/chunk/expression
- future analysis of occurrences in context
- preserving the original linguistic evidence

### 2. Word Level

Preserve the full surface word/form as actually encountered.

Example: 食べました

The exact encountered form must remain available.

Required for:
- surface-form frequency
- exact occurrence retrieval
- positional analysis
- future analysis that depends on what was actually encountered

### 3. Lexical Form

Every word occurrence must preserve BOTH:

- surface: the exact Japanese form encountered in the source
- lexical: the dictionary/base form corresponding to that occurrence

Conceptual examples:
- 食べました → 食べる
- 食べない → 食べる
- 食べて → 食べる
- 行きました → 行く
- 行って → 行く
- 思います → 思う

The surface form must never be replaced by the lexical form.

"lexical" is defined as the dictionary/base form of the occurrence. If a reliable dictionary/base form cannot be determined, lexical may be null rather than inventing one.

Do NOT add POS tagging, grammar explanations, readings, translations, or other linguistic annotations to support lexical normalization.

Required for:
- dictionary-level counting
- deterministic grouping of inflected occurrences
- lexical-item frequency
- distinguishing actual encountered forms from their lexical identity

### 4. Meaningful Grammar Chunks

Preserve meaningful grammatical chunks.

These reflect meaningful phrase-level grammatical units rather than a full word-by-word grammatical analysis.

This is NOT the same as detailed learner-oriented chunking/decoding.

Example of a corpus-useful unit: 行くことにしました

The detailed learner-oriented sentence breakdown can always be generated later from the original Japanese sentence.

### 5. Expressions

Preserve meaningful multi-word expressions/patterns.

Expressions are a separate evidence layer from meaningful grammar chunks, because Japanese meaning is frequently carried by recurring multi-word units.

An expression should represent the LONGEST COMPLETE MEANINGFUL EXPRESSION identified in the sentence.

When expression candidates overlap because a shorter expression is contained inside a longer expression, preserve ONLY the longest complete expression. Do NOT preserve the shorter nested expression as a separate expression occurrence.

Example: if なぜかというと is identified as one complete expression, do not additionally record という as an expression occurrence inside it. The nested sequence may have a different meaning or function when encountered independently; inside the longer expression it is part of that complete expression.

Separate expressions that do not overlap remain independent.

Every expression occurrence must preserve:
- its exact encountered surface
- its word span within the sentence
- an expression index within the sentence
- its normalized/grouping pattern, if that field remains part of the approved schema

Conceptual pattern examples include:
- ～と思います
- ～ということ
- なぜかというと
- ～ことにする

The parser identifies the expression as encountered/used. It does not provide a grammar lesson. It does not calculate expression frequency, recurrence, dispersion, or other statistics.

### 6. Links Between Levels

The output must preserve sufficient IDs, positions, or equivalent relationships to connect every occurrence back to:

source → sentence → word occurrence → lexical form → grammar chunk → expression

Implementation details of the IDs/schema are designed later. The information relationship must be preserved.

If an analyzer discovers "X occurred 37 times", it must be able to retrieve the 37 actual Japanese sentence contexts and know where they occurred in the source.

Grammar chunks and expressions must be traceable back to their source sentences.

## Occurrence Evidence vs Grouping Labels

The corpus must distinguish two kinds of information:

WHAT OCCURRED:
- exact sentence
- exact surface word
- exact expression surface
- word/chunk/expression positions

WHAT IT REPRESENTS FOR GROUPING:
- dictionary/base lexical form
- expression pattern, if retained

The analyzer will later use these fields to calculate frequency, recurrence, dispersion, average distance between occurrences, clumping vs spreading, and other corpus measurements.

Do not perform those analyses in the parser.

## What the Processor Must NOT Produce

The parser is NOT required to generate:

- English translations
- Japanese readings
- furigana
- POS labels
- grammar explanations
- learner-oriented micro-chunking
- frequency statistics
- dispersion statistics
- clustering statistics
- average distance between occurrences
- lesson reports
- corpus analysis
- other statistical aggregation

These belong to later deterministic analysis/reporting stages.

## Rationale for Omitting Translations / Readings / POS

This is an immersion-oriented corpus, not an explicit grammar-study corpus.

The purpose is to preserve what Shawn actually encounters in Japanese and allow later analysis of exposure, recurrence, vocabulary, chunks, and expressions.

Translations and readings would add API output/cost without being necessary for the planned analyses.

POS tagging is intentionally omitted because it encourages a traditional grammatical analysis that is not required for the immersion-oriented use case.

## Analytical Consequence

The parser must preserve enough positional information to allow future analyzers to calculate:

- word frequency
- lexical-form frequency
- frequency by source
- frequency by lesson/episode
- recurrence across sources
- sentence frequency
- expression frequency
- grammar-chunk frequency
- distance between occurrences
- average/median inter-occurrence distance
- clustering vs dispersion
- exposure distribution
- vocabulary growth
- source comparisons
- any future statistical measurement

These measurements MUST NOT be calculated by the processor.

## Architectural Boundary

The DeepSeek parser:

Japanese source → interprets it → preserves sentence/word/lexical-form/grammar-chunk/expression evidence → records relationships and positions → saves corpus data

The analyzer:

saved corpus data → calculates statistics → performs comparisons → generates reports

The parser must not become the analyzer.

The parser must not become the lesson-report generator.

The detailed learner-oriented sentence report can be generated later from the preserved original sentence.

## Core Principle: "Garbage In, Garbage Out"

The parser's job is to preserve original evidence while adding structured supplemental information. It must not replace source evidence with interpretations.

- Surface/text remain authoritative occurrence evidence.
- Lexical forms and expression patterns represent grouping, not evidence.
- The validator detects errors; deterministic builder logic should recompute information the LLM is demonstrably bad at calculating (character offsets, chunk text, global positions).

## Validator and Builder Division

The Response Validator is a deterministic gate: it validates structure and evidence preservation and reports problems, but it never repairs output.

The Corpus Builder is the deterministic stage that turns validated evidence into the canonical corpus: it normalizes records, recomputes character spans and chunk text from the authoritative ordered surfaces, assigns source-global ordering/IDs, performs section assignment and the source-reconstruction integrity check, and stamps provenance.

## Source Integrity Principle

Every imported source receives:
- a stable human-readable source_id
- a SHA-256 hash fingerprint of the original source file
- metadata describing source type and processing requirements
- lineage information connecting derived artifacts back to the original source

Design rules:

1. **Hashes are audit identifiers, not primary IDs.**
   - source_id remains human-readable and organizational.
   - SHA-256 is used to detect duplicates, corruption, and changes.

2. **Source files are treated as immutable inputs.**
   - Cleaning creates derived artifacts.
   - Parsing creates derived artifacts.
   - Corpus JSONL is rebuildable from earlier stages.

3. **Each processing stage should preserve traceability:**

   ```
   Raw Source
       |
       v
   Cleaner + cleaner version
       |
       v
   Parser + parser version
       |
       v
   Validator
       |
       v
   Canonical Corpus
   ```

4. **Metadata should eventually include:**
   - original filename
   - source type
   - format
   - language
   - SHA-256 hash
   - cleaner version
   - parser version
   - validator version
   - derived artifact hashes

5. **This system is designed for rebuildability:**
   - The source file remains the source of truth.
   - Cleaned files and corpus files are derived products.
   - Future database/index systems are derived views, not replacements for provenance.

---

# Planned Analytical Use Cases

Recorded as planned directions, not yet implementation requirements:

- finding vocabulary/expression/grammar leeches in corpus context
- retrieving example sentences by word, expression, or grammar level
- generating Anki cards and reading lists from corpus evidence
- using consumed-source/reference history to estimate exposure
- generating tests/quizzes based on actual corpus exposure
- eventually comparing exposure against recognition/knowledge

---

# Long-Term Goal

Create a high-quality Japanese corpus that supports evidence-based analysis of:

- vocabulary acquisition
- grammar acquisition
- expression frequency
- source overlap
- learner progression
- comprehensibility metrics

while minimizing API cost and maximizing reproducibility.
---

# AI-Assisted Development

This project is built with AI assistance under an Owner/Advisor/Coder/Auditor protocol. Two files carry standing operating instructions and are auto-loaded by their respective tools — they are not duplicated here:

- `CLAUDE.md` — Advisor and Auditor instructions (Claude Code). Auditor is filled by a fresh Claude Code session/subagent, not a separate vendor — see that file for why.
- `AGENTS.md` — Coder instructions (OpenCode)

(`QWEN.md`, the original cross-vendor Auditor design, is retired — see `Archive/QWEN.md`.)

Current project state, architecture, and next planned work live in `JPROGRAM_SESSION_BOOTSTRAP.md`, refreshed each session.
