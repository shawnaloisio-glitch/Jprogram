# Japanese Corpus Pipeline
## Project Status and Continuation Document

> ## ⚠️ RETIRED AS CURRENT-STATE (2026-08-12)
>
> **This document is historical.** It grew section-by-section and its
> "Current State" block dates to 2026-08-04 — it is no longer the
> current-state source of truth and should not be read as such.
>
> **The current-state home is `JPROGRAM_SESSION_BOOTSTRAP.md`** (per the
> workspace convention: one authoritative source for current state). Read
> that file for current architecture, phase, and open items.
>
> Everything below this banner is retained as the historical milestone
> record only (git history also preserves it). Do not update this file as
> current state; update the bootstrap instead.

**Project root:** `C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus`  
**Current project name:** Japanese Corpus Pipeline  
**Project version:** 1.0  
**Status:** Active development  
**Last documented stage:** Application Shell / GUI + full pipeline  
**Current state (2026-08-04):** Pipeline, Source Package workflow, Handoff, Application Shell (Sources / Processing / Analysis), and Analysis surface are complete and tested. Runtime data has been reset to a clean state; metadata config has been cleaned. Remaining work: real-data validation, packaging, and external QC review.

> Note: this document has grown historically, section by section. Sections that
> describe earlier milestone statuses (e.g. "parser prompt not written",
> "Corpus Builder not started", "GUI future") reflect the state at the time
> they were written. See the "Current State" section at the top and the status
> table in Section 28 for the current implementation state.

---

# Current State (2026-08-04)

Implemented and tested:

- **Application Shell** (`app.py`) — 3-tab shell: Sources (embedded Source
  Builder), Processing (opens Processing window), Analysis (opens Analysis
  window).
- **Sources** — Source Builder embedded: source capture, Import Material,
  Source Package sidecars, Quick Presets ("Templates"), Recent Sources,
  metadata editor, Ready State Engine.
- **Source Package workflow** — `Source Builder\source_package.py` builds the
  canonical `.source.json` sidecar beside each saved source.
- **Handoff workflow** — `Source Builder\handoff.py` creates the Source
  Registry entry and Cleaning Job from a source package (idempotent via
  sha256).
- **Pipeline complete** — Cleaner → Job Builder → Request Builder → DeepSeek
  Parser → Response Validator → Corpus Builder → canonical JSONL, orchestrated
  by the Production Manager.
- **Processing UI** — list saved sources (human labels), process selected,
  retry failed, run analysis, export diagnostics.
- **Analysis UI** — list corpus-ready sources, run a basic frequency analysis,
  open Analysis outputs.
- **Metadata cleanup** — Config cleaned: collections empty, source_types =
  [podcast_transcript], origins = [user_transcription].
- **Runtime data reset** — Sources / Registry / Cleaning Jobs / Cleaning
  Results / Cleaned Archive / Processing Results / corpus / Analysis outputs /
  Logs / Diagnostics are cleared; the application launches from a clean state.

Regression status (2026-08-04): 722 tests across all suites. 5 documented
failures remain in `test_source_builder_quick_presets.py` and
`test_source_builder_gui_presets.py` because those tests read the live Config
which no longer contains the removed development metadata; they are fixture
issues, not code defects.

Remaining work:

- **Real data validation** — validate the full pipeline (import → save →
  process → analyze) with real source material.
- **Packaging** — launch/installer packaging.
- **External QC review** — the pending Qwen review.

---

# 1. Project Purpose

The Japanese Corpus Pipeline is a local Python pipeline for processing Japanese-language source material into structured corpus data.

The intended general flow is:

```text
Raw Source
    ↓
Cleaning
    ↓
Processing / Jobs
    ↓
Requests
    ↓
DeepSeek API
    ↓
Responses
    ↓
Validation
    ↓
Corpus / JSONL
    ↓
Analysis
```

The project is designed as a series of separate stages with clear responsibilities.

A stage should do one job and communicate with the next stage through files rather than tightly coupling the entire pipeline together.

---

# 2. Current Project Philosophy

The project has grown from a collection of scripts into a structured pipeline.

Important principles:

- Prefer simple, reliable stages.
- Keep responsibilities separated.
- Use shared project configuration rather than duplicating paths and settings.
- Use files as the boundaries between processing stages.
- Make stages restartable.
- Avoid unnecessary API-specific logic in earlier stages.
- Build and test incrementally.
- Do not make architectural changes merely to solve a local problem.
- Follow existing project conventions when adding new scripts.
- Preserve working components rather than repeatedly rewriting them.

The user is not a programmer and should not be expected to infer where code belongs or which constants need to be changed.

When providing code changes, give explicit instructions such as:

> Paste this directly below `[specific existing section]`.

Do not assume the user knows where a block belongs.

---

# 3. Project Structure

The project currently uses this general structure:

```text
C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus\
│
├── Analysis\
│
├── Cleaned Archive\
│
├── Data Processor\
│   ├── completed\
│   ├── indexes\
│   ├── jobs\
│   ├── jsonl\
│   ├── processing\
│   ├── requests\
│   ├── responses\
│   ├── job builder.py
│   ├── request builder.py
│   └── deepseek_client.py
│
├── Diagnostics\
│
├── Logs\
│   ├── Job Builder\
│   ├── Request Builder\
│   ├── Subtitle Cleaner\
│   └── Transcript Cleaner\
│
├── Prompts\
│   └── parser_prompt.md
│
├── Raw Subtitles\
│
├── Raw Transcripts\
│
├── Requests\
│
├── Subtitle Cleaner\
│
├── Transcript Cleaner\
│
├── common.py
├── paths.py
├── project_config.py
├── project_audit.py
└── PROJECT_STATUS.md
```

Important:

`common.py` and `paths.py` are intentionally located in the project root because they provide functionality used by scripts throughout the project.

Do not move them into `Data Processor`.

---

# 4. Shared Path Configuration

`paths.py` is the central location for project paths.

The project currently defines paths including:

```python
PROJECT_NAME = "Japanese Corpus Pipeline"

PROJECT_ROOT = Path(__file__).resolve().parent

ANALYSIS = PROJECT_ROOT / "Analysis"

CLEANED_ARCHIVE = PROJECT_ROOT / "Cleaned Archive"

DATA_PROCESSOR = PROJECT_ROOT / "Data Processor"

LOGS = PROJECT_ROOT / "Logs"

RAW_SUBTITLES = PROJECT_ROOT / "Raw Subtitles"

RAW_TRANSCRIPTS = PROJECT_ROOT / "Raw Transcripts"

SUBTITLE_CLEANER = PROJECT_ROOT / "Subtitle Cleaner"

TRANSCRIPT_CLEANER = PROJECT_ROOT / "Transcript Cleaner"

COMPLETED = DATA_PROCESSOR / "completed"

INDEXES = DATA_PROCESSOR / "indexes"

JOBS = DATA_PROCESSOR / "jobs"

PROMPTS = PROJECT_ROOT / "Prompts"

REQUESTS = PROJECT_ROOT / "Requests"

JSONL = DATA_PROCESSOR / "jsonl"

PROCESSING = DATA_PROCESSOR / "processing"

RESPONSES = DATA_PROCESSOR / "responses"
```

Log paths include:

```python
LOG_JOB_BUILDER = LOGS / "Job Builder"

LOG_SUBTITLE_CLEANER = LOGS / "Subtitle Cleaner"

LOG_TRANSCRIPT_CLEANER = LOGS / "Transcript Cleaner"

LOG_REQUEST_BUILDER = LOGS / "Request Builder"
```

There are both project-root and Data Processor request-related locations in the current project history.

The working Request Builder currently writes its generated requests to:

```text
C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus\Data Processor\requests
```

Do not casually change this structure. Verify existing code and paths before making architectural changes.

---

# 5. Python Import Convention

Scripts located below the project root, such as scripts in `Data Processor`, explicitly add the project root to Python's import path.

The established pattern is:

```python
import sys
from pathlib import Path

# Allow imports from the project root
sys.path.append(str(Path(__file__).resolve().parent.parent))
```

This is necessary because shared modules such as:

```text
C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus\common.py
C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus\paths.py
C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus\project_config.py
```

are located in the project root.

New Data Processor scripts should follow the existing convention rather than moving shared modules.

---

# 6. Shared Modules

## common.py

`common.py` contains functionality used by multiple scripts throughout the project.

Examples include functions such as:

```python
print_header
print_footer
divider
confirm
ensure_folder
write_log
write_json
```

It belongs in the project root.

## paths.py

`paths.py` is the central project path configuration.

## project_config.py

`project_config.py` contains shared project configuration such as:

```text
PROJECT_VERSION
CLEAN_EXTENSION
CONFIRM_BEFORE_PROCESSING
LOG_DATE_FORMAT
API_MAX_RETRIES
API_RETRY_DELAY
```

Do not duplicate these values inside individual pipeline scripts unless there is a specific reason.

---

# 7. Project Audit

`project_audit.py` was created to verify the project structure and Python modules.

It scans the project and checks structural expectations.

The audit was recently run successfully:

```text
============================================================
Project Audit
============================================================

Status   : HEALTHY
Warnings : 0
Errors   : 0

Report written:
  C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus\Diagnostics\Project_Audit_2026-07-31_09-04-53.txt
```

This is important because substantial manual folder and file creation has occurred during development.

The audit exists specifically to reduce the risk of silently continuing with a typo or missing project component.

The audit should be run after significant structural changes.

---

# 8. Completed Pipeline Components

## Transcript Cleaner

Completed.

Its purpose is to clean raw transcript material and produce cleaned files for subsequent processing.

---

## Subtitle Cleaner

Completed.

Its purpose is to clean subtitle material.

---

## Job Builder

Completed and tested.

The Job Builder:

- scans cleaned files
- identifies files needing processing
- avoids rebuilding files that already have jobs
- reports source character and line counts
- batches source material according to the configured character limit
- writes job JSON files
- writes processing logs

A recent successful run produced:

```text
Clean files found : 2
Already built    : 0
Ready to build   : 2
```

It created one job for each of the two test projects:

```text
Con-Teppei for Beginner 51-100
折り紙でゴミ箱を作ろう Let’s Make a Trash Box with Origami
```

---

# 9. Request Builder

`Data Processor/request builder.py` is completed and working.

Its purpose is to transform job files into API request files.

A successful test produced:

```text
Projects found  : 2
Already built   : 0
Ready to build  : 2
```

It generated:

```text
request_000001.json
```

for:

```text
Con-Teppei for Beginner 51-100
折り紙でゴミ箱を作ろう Let’s Make a Trash Box with Origami
```

The current output location is:

```text
C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus\Data Processor\requests
```

The Request Builder also writes logs to:

```text
C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus\Logs\Request Builder
```

The Request Builder has been polished enough that it is now considered a working pipeline stage.

---

# 10. Parser Prompt

The project has:

```text
C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus\Prompts\parser_prompt.md
```

At the current documented point, this file is only a placeholder containing:

```text
Version: 1.0
```

The actual parser prompt has NOT yet been written.

> Note (2026-08-04): this is a historical statement. The parser prompt was
> subsequently written and frozen; see Section 34.

Do not assume that `parser_prompt.md` contains parser instructions.

Do not design the final parser prompt yet unless specifically requested.

The parser prompt will be designed after the DeepSeek API communication stage has been exercised.

---

# 11. DeepSeek API Design

The next major pipeline component is the DeepSeek Client.

The intended responsibility is deliberately narrow:

```text
requests/
    ↓
DeepSeek Client
    ↓
DeepSeek API
    ↓
responses/
```

The DeepSeek Client should NOT:

- perform corpus analysis
- perform final corpus validation
- merge corpus data
- redesign parser output
- perform unrelated cleaning
- become the entire pipeline

It should primarily handle reliable communication between local request files and the DeepSeek API.

---

# 12. DeepSeek Prompt Caching

DeepSeek's automatic prompt caching was considered during architecture planning.

The relevant design implication is:

The static parser prompt and other repeated instructions should remain identical and appear consistently at the front of requests where appropriate.

We do NOT need to write custom caching code simply to activate DeepSeek's automatic prompt caching.

The exact economics and API behavior should be verified against current DeepSeek documentation when the API client is implemented.

Do not over-engineer a custom caching layer unless a later requirement demonstrates that one is necessary.

---

# 13. DeepSeek Client Current Status

The file already exists:

```text
C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus\Data Processor\deepseek_client.py
```

We began implementing it incrementally.

The current file starts with:

```python
"""
deepseek_client.py

DeepSeek API client for the Japanese Corpus Pipeline.

This module handles communication between the local request
files and the DeepSeek API.

It does not parse, validate, or build corpus data.
"""

import sys
from pathlib import Path

# Allow imports from the project root
sys.path.append(str(Path(__file__).resolve().parent.parent))
```

It then imports shared functions from `common`, paths from `paths`, and configuration from `project_config`.

The client currently contains a request discovery function:

```python
scan_request_projects()
```

Its purpose is to discover project folders containing request JSON files and classify them as:

- all projects
- completed projects
- pending projects

A request analysis function was also added:

```python
analyze_request_projects()
```

A `main()` function was added so the client can be run directly.

---

# 14. Current DeepSeek Client Development Sequence

The DeepSeek Client is intentionally being built in small stages.

The planned order is:

```text
1. Create client skeleton
2. Discover request projects
3. Verify local request structure
4. Read one request
5. Write a dummy response
6. Connect to DeepSeek API
7. Send one real request
8. Save one real response
9. Add error handling
10. Add retries
11. Add logging
12. Add resume capability
```

At the current stopping point, the client is around steps 2–3.

The API has NOT yet been connected.

No API key should be hard-coded into the Python source.

---

# 15. Most Recent Debugging Issue

When `deepseek_client.py` was first run, it failed with:

```text
ModuleNotFoundError: No module named 'common'
```

The cause was that `common.py` is correctly located in the project root while the client is located under `Data Processor`.

The existing `job_builder.py` convention was checked.

The established solution is:

```python
import sys
from pathlib import Path

# Allow imports from the project root
sys.path.append(str(Path(__file__).resolve().parent.parent))
```

This has now been added to `deepseek_client.py`.

The next step is to save and rerun the client.

---

# 16. Current Expected Test

The current request data contains two projects:

```text
Con-Teppei for Beginner 51-100
折り紙でゴミ箱を作ろう Let’s Make a Trash Box with Origami
```

Each currently has one request file.

Therefore the local discovery test should recognize approximately:

```text
Projects found  : 2
Already complete: 0
Pending         : 2
```

The exact output formatting may differ.

The important goal is to verify that the client can see the request files before any API communication is introduced.

---

# 17. API Credentials

No API credentials should be placed directly into source code.

When API communication is implemented, establish a secure configuration mechanism first.

The exact mechanism should be chosen deliberately when we reach that stage.

Do not invent a credential filename or environment-variable convention without checking the existing project configuration.

---

# 18. Error Handling Philosophy

The DeepSeek Client should eventually be able to recover from normal operational problems.

Likely categories include:

- missing request files
- malformed JSON
- missing fields
- network failures
- API errors
- rate limits
- temporary service failures
- interrupted processing
- partially completed projects
- existing response files

However, these should be implemented incrementally.

Do not build all error handling before successfully sending and saving one real API request.

---

# 19. Response Architecture

The eventual response flow should be:

```text
Request JSON
    ↓
DeepSeek Client
    ↓
API
    ↓
Raw API response
    ↓
Saved response JSON
```

The response stage should preserve enough metadata to allow later debugging and analysis.

The exact response schema has not yet been finalized.

Do not prematurely design the final corpus schema.

---

# 20. Future Pipeline Stages

After the DeepSeek Client, the planned stages are approximately:

```text
DeepSeek Client
        ↓
Response Validator
        ↓
Corpus Builder
        ↓
Corpus Analytics
```

These stages have not yet been implemented.

Their exact designs should be based on the actual DeepSeek output rather than being guessed in advance.

---

# 21. Current Test Data

The current test projects include:

```text
Con-Teppei for Beginner 51-100
```

with approximately:

```text
1,840 characters
120 lines
```

and:

```text
折り紙でゴミ箱を作ろう Let’s Make a Trash Box with Origami
```

with approximately:

```text
1,242 characters
211 lines
```

Both currently produce one job and one request because each is well below the current 10,000-character batch limit.

---

# 22. Important Naming Note

The physical project directory is still named `Jprogram` (moved 2026-08-06 to
live alongside sibling projects; its own directory name is unchanged):

```text
C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus
```

The project has NOT been physically renamed to:

```text
Japanese Corpus Pipeline
```

The logical project name inside the configuration is:

```text
Japanese Corpus Pipeline
```

Do not rename the physical directory unless explicitly requested.

---

# 23. Development Workflow

The user prefers incremental development.

For each new section:

1. Explain what the section does.
2. Tell the user exactly where to paste it.
3. Give a complete paste-ready code block.
4. Have the user save.
5. Run the script.
6. Review the output.
7. Only then proceed.

Do not assume programming knowledge.

If an error occurs:

1. Read the exact error.
2. Check the existing project conventions.
3. Prefer the established architecture over a one-off workaround.
4. Give explicit instructions for the smallest necessary change.
5. Retest before continuing.

---

# 24. Do Not Make These Changes Casually

Do not:

- move `common.py`
- move `paths.py`
- rename the physical `Jprogram` folder
- redesign the entire pipeline
- replace working scripts unnecessarily
- hard-code API credentials
- build a custom caching system without a demonstrated need
- write the final parser prompt before the API stage has been exercised
- assume a placeholder file contains content that has not been written
- introduce a new folder when an existing project convention already handles the requirement

---

# 25. GUI

A GUI was discussed as a possible future enhancement.

It is considered feasible, but it is NOT currently part of the implementation plan.

The priority is:

```text
Finish reliable pipeline first.
GUI later.
```

Do not divert development into GUI work at this stage.

---

# 26. Current Exact Stopping Point

The project is currently paused immediately before the next test of:

```text
C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus\Data Processor\deepseek_client.py
```

The latest change was adding the established project-root import mechanism:

```python
import sys
from pathlib import Path

# Allow imports from the project root
sys.path.append(str(Path(__file__).resolve().parent.parent))
```

The next action is:

```text
Save deepseek_client.py
Run it
Review the output
```

No DeepSeek API call should happen yet.

---

# 27. Continuation Instruction for ChatGPT

If this document is provided to a future ChatGPT session, the assistant should:

1. Treat this document as the current project status.
2. Do not assume unfinished components are complete.
3. Do not redesign completed stages without a demonstrated reason.
4. Continue from the exact stopping point in Section 26.
5. Ask for the output of the current `deepseek_client.py` test if it has not yet been run.
6. Continue the DeepSeek Client incrementally.
7. Preserve the existing project architecture and conventions.
8. Remember that the user is deferring most implementation decisions to the assistant, unless a decision genuinely requires user input.
9. Give explicit paste locations and paste-ready blocks.
10. Keep the project focused on a reliable Japanese corpus processing pipeline.

---

# 28. Project Status Summary

| Component | Status |
|---|---|
| Project architecture | Complete |
| Shared paths | Complete |
| Shared configuration | Complete |
| Common utilities | Complete |
| Project Audit | Complete |
| Transcript Cleaner | Complete |
| Subtitle Cleaner | Complete |
| Job Builder | Complete |
| Request Builder | Complete |
| Parser Output Specification | Complete (frozen) |
| Parser prompt | Complete (frozen) |
| DeepSeek Client | Complete |
| API configuration / testing | Complete (controlled benchmarks) |
| Response Validator | Complete (20/20 tests) |
| Corpus Builder | Complete |
| Source Intake | Complete (utilities + artifact writers + coordinator) |
| Source Package | Complete |
| Handoff | Complete |
| Analysis (analyzer modules) | Complete |
| Application Shell | Complete |
| Sources UI (Source Builder) | Complete |
| Processing UI | Complete |
| Analysis UI | Complete |
| Metadata cleanup | Complete (Config cleaned) |
| Runtime data reset | Complete (clean working state) |
| Regression | 722 tests; 5 documented live-Config fixture failures |
| Real-data validation | Remaining |
| Packaging | Remaining |
| External QC review | Remaining |

---

## Current Priority

**Validate the complete pipeline with real source material end-to-end (import
→ save → process → corpus → analysis), then packaging and external QC review.
**

---

# 29. Approved Corpus-Parser Data-Preservation Architecture

## Status

APPROVED ARCHITECTURAL DECISION.

## Core Principle

The processor preserves raw linguistic evidence.

The analyzer performs statistical analysis and higher-level corpus analysis.

The processor must NOT calculate frequency, dispersion, clustering, inter-occurrence distance, or other statistics. It must preserve enough evidence that future Python analyzers can calculate those measurements without rerunning DeepSeek.

## Approved Evidence Layers

The parser output must preserve:

1. **Sentence Level (critical):** the complete original Japanese sentence with stable source/position information. Required for Anki sentence extraction, context retrieval, occurrence-in-context analysis, and preserving the original linguistic evidence.
2. **Word Level:** the full surface word/form as actually encountered (e.g., 食べました). Required for surface-form frequency, exact occurrence retrieval, and positional analysis.
3. **Lexical Form:** a normalized lexical form where appropriate (e.g., 食べました → 食べる). Preserve BOTH the surface form and the lexical form. Do not replace one with the other. Required for dictionary-level counting and grouping inflected forms.
4. **Meaningful Grammar Chunks:** meaningful phrase-level grammatical units (e.g., 行くことにしました). This is NOT the detailed learner-oriented LingQ-style chunking/decoding. Learner-oriented breakdowns can be generated later from the original sentence.
5. **Expressions:** meaningful multi-word expressions/patterns (e.g., ～と思います, ～ということ, なぜかというと, ～ことにする). Identify the expression as encountered/used; do not provide a grammar lesson.
6. **Links Between Levels:** sufficient IDs, positions, or equivalent relationships so every occurrence connects back through source → sentence → word occurrence → lexical form → grammar chunk → expression. Implementation details of the IDs/schema are designed later, but the information relationship must be preserved.

## What the Parser Must NOT Produce

The parser is NOT required to generate: English translations, Japanese readings, furigana, POS labels, grammar explanations, learner-oriented micro-chunking, frequency statistics, dispersion statistics, clustering statistics, average distance between occurrences, lesson reports, corpus analysis, or other statistical aggregation. These belong to later deterministic analysis/reporting stages.

## Rationale

This is an immersion-oriented corpus, not an explicit grammar-study corpus. The purpose is to preserve what Shawn actually encounters in Japanese and allow later analysis of exposure, recurrence, vocabulary, chunks, and expressions. Translations and readings would add API output/cost without being necessary for the planned analyses. POS tagging is intentionally omitted because it encourages a traditional grammatical analysis that is not required for the immersion-oriented use case.

## Analytical Consequence

The parser must preserve enough positional information for future analyzers to calculate: word frequency, lexical-form frequency, frequency by source, frequency by lesson/episode, recurrence across sources, sentence frequency, expression frequency, grammar-chunk frequency, distance between occurrences, average/median inter-occurrence distance, clustering vs dispersion, exposure distribution, vocabulary growth, source comparisons, and any future statistical measurement. These measurements MUST NOT be calculated by the processor.

## Architectural Boundary

DeepSeek parser: Japanese source → interprets it → preserves sentence/word/lexical-form/grammar-chunk/expression evidence → records relationships and positions → saves corpus data.

Analyzer: saved corpus data → calculates statistics → performs comparisons → generates reports.

The parser must not become the analyzer or the lesson-report generator. The detailed learner-oriented sentence report can be generated later from the preserved original sentence.

---

# 30. Future Parser Requirements

The following parser requirements follow from the approved decisions in Section 29. They are future requirements and are not yet implemented:

- The final parser prompt and corpus schema must be designed to preserve the six evidence layers in Section 29.
- The schema must allow analyzers to retrieve the actual Japanese sentence contexts for any reported occurrence count.
- Grammar chunks and expressions must be traceable back to their source sentences.
- Every word occurrence must preserve both the surface form and its dictionary/base lexical form (see Section 31).
- Expressions must preserve the longest complete expression only; shorter nested expressions are not recorded separately (see Section 31).
- The parser must not emit translations, readings, furigana, POS labels, grammar explanations, statistics, or lesson reports.
- The parser must not perform statistical aggregation of any kind.

Note on consistency with earlier sections: Sections 19 and 20 (response architecture and future pipeline stages) remain in force — the schema implementation details are still to be designed, and the evidence layers are now approved requirements that will guide that design. Section 10 and Section 24 remain in force — the parser prompt must still not be created until the DeepSeek API stage has been exercised.

---

# 31. Approved Decisions: Lexical Form and Expression Rules

## Status

APPROVED ARCHITECTURAL DECISION. Refines Sections 29 and 30.

## Lexical Form

Every word occurrence must preserve both:

- surface: the exact Japanese form encountered in the source
- lexical: the dictionary/base form corresponding to that occurrence

Examples:
- 食べました → 食べる
- 食べない → 食べる
- 食べて → 食べる
- 行きました → 行く
- 行って → 行く
- 思います → 思う

The surface form must never be replaced by the lexical form.

The purpose of the lexical field is to allow the future analyzer to group inflected occurrences deterministically and calculate lexical-item frequency.

Use "dictionary/base form" as the conceptual definition of lexical.

If a reliable dictionary/base form cannot be determined, lexical may be null rather than inventing one.

Do NOT add POS tagging, grammar explanations, readings, translations, or other linguistic annotations to support lexical normalization.

## Expressions

Expressions are a separate evidence layer from meaningful grammar chunks.

An expression should represent the LONGEST COMPLETE MEANINGFUL EXPRESSION identified in the sentence.

When expression candidates overlap because a shorter expression is contained inside a longer expression, preserve ONLY the longest complete expression. Do NOT preserve the shorter nested expression as a separate expression occurrence.

Example: if なぜかというと is identified as one complete expression, do not additionally record という as an expression occurrence inside it. The nested sequence may have a different meaning or function when encountered independently, whereas inside the longer expression it is part of that complete expression.

Separate expressions that do not overlap should remain independent.

Every expression occurrence must preserve:

- its exact encountered surface
- its word span within the sentence
- an expression index within the sentence
- its normalized/grouping pattern only if that field remains part of the approved schema

The parser should preserve the evidence needed for later analysis but should NOT calculate expression frequency, recurrence, dispersion, or any other statistics. Those remain the analyzer's responsibility.

## Architectural Principle

Keep the distinction between:

WHAT OCCURRED:
- exact sentence
- exact surface word
- exact expression surface
- word/chunk/expression positions

WHAT IT REPRESENTS FOR GROUPING:
- dictionary/base lexical form
- expression pattern, if retained

The analyzer will later use these fields to calculate frequency, recurrence, dispersion, average distance between occurrences, clumping vs. spreading, and other corpus measurements.

Do not perform those analyses in the parser.

---

# 32. Parser Design Decisions (TASK 13)

These decisions were settled before the parser contract was frozen.

- **Word segmentation policy:** whitespace-delimited sources keep their existing whitespace-delimited word units verbatim (no merging or re-segmentation); non-whitespace-delimited Japanese uses pragmatic reader-perceived word units; inflected forms stay intact (食べました is never decomposed into 食べ/まし/た); functional elements may be separate units; no POS.
- **Character spans:** per-word `char_start`/`char_end` are sentence-relative; invariant `text[char_start:char_end] == surface`. The parser does not emit sentence-level or source-global character offsets.
- **Grammar chunks:** flat, non-overlapping partition of the sentence; every word belongs to at most one chunk; chunk text corresponds to its word span; chunks are NOT learner/LingQ micro-chunks.
- **Expressions:** longest-complete-expression rule; nested shorter expressions are not separately recorded; independent non-overlapping expressions may both be recorded; `pattern` is an advisory grouping aid.
- **Section/episode handling:** deterministic Corpus Builder work; the parser must not emit header marker lines (e.g., `===== Episode 51 =====`) as sentences; no LLM global section metadata is trusted.
- **Source type / provenance:** source type and provenance (source, source file, job number, model, prompt version, clean artifact) belong to the corpus metadata; lightweight and deterministic.
- **Global positioning:** the parser reports only job-local positions; the Corpus Builder assigns source-global ordering and IDs. The LLM never invents global IDs.
- **Canonical JSONL:** one sentence = one JSONL record, all evidence nested inside; analyzers compute all statistics later.
- **Validator vs builder:** the Response Validator detects errors; the Corpus Builder deterministically normalizes and recomputes.
- **Integrity reconstruction:** the builder verifies that reconstructed sentence text reproduces the clean source text (with section markers removed and permitted whitespace normalization).

# 33. Parser Output Specification (TASK 14)

`C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus\PARSER_OUTPUT_SPEC.md` was created and is the frozen contract between the DeepSeek Parser, the Response Validator, the Corpus Builder, and the Analyzer.

- Exactly one valid JSON object per job: `source_name`, `job_number`, `sentences`.
- Sentence: `sentence_index` (job-local, 0-based), `text`, `words`, `chunks`, `expressions`.
- All indices 0-based; all spans half-open (start inclusive, end exclusive), matching Python slicing.
- Word: `[index, surface, lexical, char_start, char_end]`.
- Chunk: `[index, text, start_word, end_word]`.
- Expression: `[index, surface, start_word, end_word, pattern]`.
- Surface and lexical are both preserved; lexical is null rather than invented.
- Parser/builder/analyzer separation is explicit in the specification.

# 34. Parser Prompt (TASK 15)

`C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus\Prompts\parser_prompt.md` was created (replacing the placeholder) and is frozen.

- Instructs DeepSeek to transform each ~10,000-character job into exactly the PARSER_OUTPUT_SPEC JSON structure.
- Output contract: exactly one valid JSON object; no Markdown fences, prose, comments, multiple objects, or JSONL.
- Includes sentence preservation, word/lexical rules, segmentation rules, the character-span invariant, chunk rules, the longest-expression rule, and the full "must not produce" list.
- **Remaining open issue (known):** the request's user message does not currently pass `source_name`/`job_number` to the model, so the parser echoes placeholder values (observed as `"unknown"` / `0`). The request metadata remains authoritative; this is resolved when the Request Builder supplies identification.

# 35. Parser Format Efficiency Review and Benchmarks (TASKS 16–17)

- A design review compared named nested JSON, hybrid fixed-position arrays, flat JSONL records, and other formats across token cost, model reliability, validation, Python processing, and storage.
- **Hybrid fixed-position-array format** (named sentence objects; word/chunk/expression records as fixed-position arrays) was identified as substantially more token-efficient (~25% of output tokens) with manageable, validator-detectable reliability.
- The canonical corpus remains named sentence-per-line JSONL. Parquet/Arrow was deferred as a possible future derived analytics artifact.
- Controlled benchmark (Task 17, same 1,242-char job):
  - Named format (Test A): `finish_reason=length`, 65,536 completion tokens (44,925 reasoning), truncated, invalid JSON — could not complete the job.
  - Hybrid format (Test B): completed with valid JSON, 35,384 completion tokens (28,053 reasoning) — but dropped one sentence (`できました。`), demonstrating both reasoning overhead and evidence loss.
  - Hybrid repeat (Test C): 65,536 completion tokens, ALL reasoning, zero content.
- Conclusion at that point: completion/reasoning failure was identified as SEPARATE from schema reliability; the hybrid is cheaper and structurally sound when it completes, but the reasoning model was the bottleneck.

# 36. DeepSeek V4-Flash API Capability Findings (TASKS 18–19)

Based on official DeepSeek API documentation and controlled testing:

- **Thinking mode:** `deepseek-v4-flash` supports both non-thinking and thinking modes; thinking is the default with effort `high`.
- **Reasoning can be disabled:** `thinking: {"type": "disabled"}` requests a direct response (no `reasoning_content`, no reasoning tokens).
- **Low reasoning effort proved unreliable:** `reasoning_effort: "low"` did not prevent reasoning blowouts (65,536 reasoning tokens, zero content in the test).
- **Explicit `max_tokens` required:** non-thinking mode defaulted to an 8,192-token output cap (truncation at `finish_reason=length`); the API maximum is 384K, so `max_tokens` must be set explicitly.
- **`response_format: {"type": "json_object"}`** retained (guarantees valid JSON on completion; does not prevent budget truncation).
- **Prompt/context caching confirmed:** caching is automatic and on by default; the static parser prompt is a cache-hit prefix (2,816 of 2,820 prompt tokens cached from the second call onward). Input caching does NOT reduce output or reasoning-token cost.
- **Production direction became non-thinking mode.**
- **Relevant project changes (Task 19):** `project_config.py` added `API_THINKING_TYPE`, `API_REASONING_EFFORT`, `API_JSON_RESPONSE`; `deepseek_client.py` `build_request_body()` now exposes `thinking`, `reasoning_effort`, and `json_response` overrides (defaults preserve prior behavior).

# 37. Final Controlled Parser Benchmark (TASK 20)

Configuration (all three calls identical): `deepseek-v4-flash`, `thinking` disabled, `response_format` json_object, `max_tokens=32768`, hybrid format, same 1,242-char job.

Results:
- 3/3 `finish_reason=stop`; 3/3 valid JSON; 0 reasoning tokens.
- Completion tokens: 16,229 / 17,154 / 16,277.
- Evidence reconstruction succeeded 3/3 (whitespace-normalized sentence concatenation equals the clean job text).
- Word surfaces partitioned sentences correctly 3/3 (106/106 sentences; 0 dropped, 0 mis-split).
- **Recurring CJK character-offset errors identified:** 34–78 char-span mismatches per response (6.6%–15.2% of words); all validator-detectable. Ordered word surfaces remain authoritative because they exactly partition each sentence.
- **Decision:** deterministic recomputation of character spans (and chunk text) is delegated to the Corpus Builder.
- **The hybrid + non-thinking parser architecture was frozen.**

# 38. Response Validator (TASK 21)

- `Data Processor\response_validator.py` replaced the stale placeholder with the real deterministic validator.
- `Data Processor\response_validator_test.py` was created; **20/20 tests pass**.
- Validator responsibilities: top-level, sentence, word, chunk, and expression validation; the word-surface partition test; source-identity comparison against request metadata; machine-readable result (`valid`, `errors`, `warnings`, `summary`).
- **Fatal vs non-fatal distinction:** character-span mismatches are reported as non-fatal (the Corpus Builder recomputes them from the authoritative surfaces); everything else (structure, indices, word-surface partition mismatch, chunk/expression problems) is fatal. The word-surface partition mismatch is fatal evidence corruption.
- Real benchmark response demonstration: 78 span errors detected while evidence integrity (word-surface partition) was preserved.
- **No silent repair:** the validator is a gate; it never corrects, rewrites, reconstructs, or reorders output.
- Corpus Builder remains unimplemented (next stage).

# 39. Current Architectural Pipeline, Core Principle, and Planned Analytical Use Cases

## Current Architectural Pipeline

```text
RAW SOURCE
  → CLEAN SOURCE
  → REQUEST BUILDER
  → DEEPSEEK PARSER
       (deepseek-v4-flash, non-thinking, response_format json_object,
        max_tokens >= 32768, hybrid fixed-position-array intermediate format)
  → RESPONSE VALIDATOR
  → CORPUS BUILDER
       (deterministic normalization, character-span/chunk-text recomputation,
        global positioning and IDs, section assignment, provenance,
        source-reconstruction integrity check)
  → CANONICAL SENTENCE-PER-LINE JSONL CORPUS
  → ANALYSIS / REPORTS
  → Application Shell / GUI (Sources, Processing, Analysis)
```

## Core Principle: "Garbage In, Garbage Out"

The parser's job is to preserve original evidence while adding structured supplemental information. It must not replace source evidence with interpretations.

- Surface/text remain authoritative occurrence evidence.
- Lexical forms and expression patterns represent grouping, not evidence.
- The validator detects errors; deterministic builder logic should recompute information the LLM is demonstrably bad at calculating (character offsets, chunk text, global positions).

## Planned Analytical Use Cases

Recorded as planned directions, not implementation requirements:

- Finding vocabulary/expression/grammar leeches in corpus context.
- Retrieving example sentences by word, expression, or grammar level.
- Generating Anki cards and reading lists from corpus evidence.
- Using consumed-source/reference history to estimate exposure.
- Generating tests/quizzes based on actual corpus exposure.
- Eventually comparing exposure against recognition/knowledge.
---

# 40. Approved Decision: Source Integrity Principle

## Status

APPROVED ARCHITECTURAL DECISION.

## Principle

Every imported source receives:
- a stable human-readable source_id
- a SHA-256 hash fingerprint of the original source file
- metadata describing source type and processing requirements
- lineage information connecting derived artifacts back to the original source

## Design Rules

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

# 41. Approved Decision: Source Intake Data Contract

## Status

APPROVED ARCHITECTURAL DECISION. Specifies the Source Intake architecture and data contracts. No implementation yet.

## Responsibility Boundary

- **Source Intake Manager:** registers incoming files, creates source_id, calculates SHA-256, stores registry metadata, selects cleaning_profile, and routes to the correct cleaner.
- **Cleaners:** only clean content. They do not create source identity, manage hashes, or manage registry metadata.

## Naming Convention

`{type}_{slug}_{sequence}` (e.g., sub_sousou-no-frieren_ep001, pod_conteppei_ep051, manga_one-piece_ch012). The original filename is preserved only in the registry and never used as identity.

## Registry Schema

One JSON file per source at `Source Registry\<source_id>.json` (UTF-8, ensure_ascii=False, stable key ordering).

Required fields:
- Identity: source_id, original_filename, sha256
- Classification: source_type, format, language
- Processing: cleaning_profile, cleaner_version, intake_timestamp, cleaned_at
- Lineage: cleaned_artifact, parser_version, validator_version, canonical_corpus
- lifecycle_status: registered, cleaning, cleaned, processing, parsed, validated, corpus_created, complete, and failure states (failed_*)

## Cleaner Contract

Input: source_id, raw_path, cleaning_profile, output_path.
Output: cleaned artifact path, cleaning result, updated registry fields (the manager writes the registry, never the cleaner).

## Processing Profile Model

`source_type` is separate from `cleaning_profile` (e.g., source_type=anime_subtitle, cleaning_profile=subtitle_standard_v1). A configuration mapping (source_type -> default cleaning_profile -> cleaner) resolves routing. Future profiles are configuration entries plus new cleaner scripts; Source Intake logic is unchanged.

## Migration Impact

Future changes (when implemented): paths.py (SOURCE_REGISTRY constant), project_config.py (source types, cleaning profiles, cleaner versions, profile mapping, extensions), cleaners (adopt the intake contract; fix the hardcoded cleaning log path), and optionally job builder (registry linkage).

## Frozen Components

Parser, validator, builder, canonical JSONL, analyzers, and the DeepSeek client transport remain frozen.

---

# 42. Approved Decision: Source Intake Phase 2 Artifact Layer Complete

## Status

APPROVED ARCHITECTURAL DECISION. Source Intake Phases 1–2 are implemented and tested.

## Completed Files

- Source Intake\hashing.py (utility)
- Source Intake\source_id.py (utility)
- Source Intake\schemas.py (utility)
- Source Intake\registry.py (Source Registry artifact writer)
- Source Intake\cleaning_job.py (Cleaning Job artifact writer)
- tests for all modules

## Architecture Confirmation (Artifact Ownership)

- Source Intake owns Source Registry creation.
- Source Intake owns Cleaning Job creation.
- The Cleaner will own Cleaning Result creation.
- Future managers only orchestrate.

## Implementation Status

Completed:
- artifact builders
- schema validation integration
- deterministic JSON output
- atomic writes

Remaining:
- coordinator layer (source_intake.py)
- duplicate detection (duplicate_check.py)
- configuration integration
- cleaner migration

## Protected Boundaries (Unchanged)

Parser, validator, builder, canonical JSONL, analyzers, and the DeepSeek transport.
