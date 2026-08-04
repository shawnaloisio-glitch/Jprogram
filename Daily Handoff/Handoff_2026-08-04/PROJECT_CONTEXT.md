# PROJECT_CONTEXT

**Japanese Corpus Pipeline (C:\Jprogram)**
AI continuity document for future sessions. Read this first, then
`PROJECT_STATUS.md`, then the latest audit set.

---

## 1. Project Purpose

**What Jprogram is:** a local, staged, AI-assisted language processing
pipeline. It ingests Japanese source material (podcasts, subtitles, future
manga/novels/web text), cleans it, parses it with the DeepSeek API, and produces
a canonical sentence-per-line JSONL corpus that deterministic analyzers read to
compute frequency, distribution, exposure, and other measurements.

**Goal:** build a *reusable* AI-assisted language processing platform — not a
one-off script collection. Each stage is a single-purpose program with a defined
artifact contract, so new source types are added by writing a new cleaner plus a
config entry, never by rewriting the pipeline.

**Multi-language portability:** the architecture is language-agnostic. The only
language-specific default is the project-level `ja` in
`project_config.py`/`controller.py` — an intentional setting, not a design
constraint. No Japanese-specific logic is embedded in the core architecture.

**User data vs product defaults:** strictly separated. `Config\*.json` holds
controlled vocabulary (collections, source_types, origins) and ships clean;
user-created data (sources, registry entries, cleaning jobs, results, corpus
outputs, analysis outputs, diagnostics, logs) lives in separate runtime folders
and can be removed without affecting the application. User metadata must never
leak into portable/shipped builds.

---

## 2. Current Development Phase

The project has moved from **architecture development** into
**real-world validation**. The full application is built and unit-tested; the
remaining work is validating the pipeline with real source material end-to-end
(import → save → process → corpus → analysis), then packaging and external QC.

**Implementation state (complete and tested):**
- Application Shell (3 tabs) — complete.
- Source Builder (capture, import, source package, presets, recent sources,
  metadata editor, Ready State Engine) — complete.
- Processing pipeline (clean → jobs → requests → api → corpus via Production
  Manager) — complete.
- Parser Output Canonicalizer — complete (`Data Processor\parser_normalizer.py`).
- Analysis framework (nine analyzer modules) — complete.
- Regression: **740 tests — 735 passing / 5 failing.** The 5 failures are
  documented live-Config fixture issues (tests reference removed development
  metadata); they are fixture problems, not code defects.

**Entry points:** `python app.py` (primary), `Source Builder\source_builder.py`
(standalone), Production Manager CLI, stage scripts.

---

## 3. Current Architecture Overview

The application layer is a 3-tab shell (`app.py`) with embedded Source Builder
(Sources tab) and child Processing / Analysis windows, orchestration via the
Production Manager, and a set of single-purpose pipeline stage programs:

```
User (app.py shell)
   |  Sources: capture/import/save + Source Package (.source.json)
   v
Handoff (registry + cleaning job) -> Cleaner -> Cleaned Archive
   v
Production Manager pipeline: clean -> jobs -> requests -> api -> corpus
   v
Canonical JSONL Corpus (Data Processor\jsonl)  [single source of truth]
   v
Analysis (Analysis\ analyzers, read-only) -> Analysis\outputs
```

**Key modules:** `app.py`, `Source Builder\` (gui, controller, source_package,
handoff, processing_tab, analysis_tab_gui, metadata_editor, config_loader),
`Production Manager\production_manager.py`, `Data Processor\` (job builder,
request builder, deepseek_client, parser_normalizer, response_validator,
corpus_builder), `Analysis\`, `Source Intake\`, cleaners, `Config\`.

**Runtime data separation:** code is separate from data; sources/registry/
results/corpus/outputs/logs/diagnostics are all removable without affecting the
application (clean-install-equivalent launch verified).

---

## 4. Authoritative Data Pipeline Flow

Implemented and verified:

```
Clean Source
    |
    v
Parser                     (DeepSeek, deepseek-v4-flash, non-thinking,
    |                      hybrid fixed-position-array format)
    v
Parser Output Canonicalizer  (parser_normalizer.py)
    |   replace sentence text / recompute spans / recompute chunk text /
    |   verify reconstruction
    v
Response Validator        (response_validator.py)
    |
    v
Corpus Builder            (corpus_builder.py)
    |   assign IDs / provenance / sections
    v
Corpus JSONL              (sentence-per-line canonical corpus)
    |
    v
Analysis                  (Analysis\ analyzers — read-only)
```

The Parser Output Canonicalizer runs **before** the Response Validator, so the
validator gates canonical records whose sentence text comes from the clean
source.

---

## 5. Stage Ownership

| Stage | Owns | Must NOT |
|---|---|---|
| **Parser** | Creates the structured interpretation (sentences, words, chunks, expressions) from the source and preserves all original evidence. | Compute statistics; invent global IDs/offsets; normalize away source text. |
| **Parser Output Canonicalizer** | Restores clean-source authority: replaces parser sentence `text` with the canonical clean-source sentence, recalculates character spans and chunk text, verifies reconstruction. Prepares parser output for validation. | Interpret, guess, or silently repair; compute statistics. |
| **Response Validator** | Checks the integrity of the *canonical* output (structure, indices, spans, word-surface partition against canonical text). A gate: it never corrects. | Repair or rewrite output; own sentence-text authority. |
| **Corpus Builder** | Creates the final canonical corpus records and metadata: global IDs, sections, provenance, and the final JSONL write. | Canonicalize sentence text (moved out); compute statistics. |
| **Analysis** | Computes all statistics (frequency, distribution, exposure, etc.) from the canonical corpus. | Modify corpus data; feed back into the corpus. |

---

## 6. Major Architectural Decisions and Rationale

- **Clean source is the sentence authority.** The LLM is demonstrably
  unreliable at exact text reproduction (it dropped characters, split/merged
  units, and changed punctuation in benchmarks). The cleaned source is the only
  verifiable record of what was actually consumed, so it owns sentence text;
  parser output is treated as evidence to be checked against it.
- **Canonicalization was moved out of the Corpus Builder.** The builder's
  sentence-restoration logic was unreachable because the validator's fatal
  word-surface partition check ran first and rejected real parser output that
  omitted sentence-final punctuation. The deterministic canonicalization
  (restore text, recompute spans/chunks, verify reconstruction) now lives in a
  dedicated **Parser Output Canonicalizer** that runs *before* validation, so
  the validator validates canonical records. The builder keeps only
  IDs/sections/provenance. This preserved "one responsibility per stage"
  instead of patching the validator or relaxing the gate.
- **Canonical sentence restoration addresses parser spacing problems.**
  Benchmark responses split single units (e.g. ことが → こと が) and drifted from
  source whitespace. Rather than trusting the parser's spans or text, the
  canonicalizer deterministically restores the clean-source sentence and
  recomputes all positions from the authoritative ordered word surfaces, with a
  strict reconstruction gate (no silent repair).
- **Metadata cleanup was performed.** Development-era collections, source
  types, and origins (including "Teppei"-related values) had accumulated in
  `Config\` and runtime files. They were removed to enforce "user metadata must
  not become shipped defaults" and to give the application a clean-install
  baseline. A few stale runtime references remain and are tracked as Item 7.
- **Validator vs builder split.** The validator is a deterministic gate that
  detects errors and never repairs; the builder deterministically recomputes
  what the LLM is bad at (spans, chunk text, global positions).
- **One program = one task.** Programs communicate through defined artifacts
  and never modify another program's owned files.

---

## 7. Current Known Issues

Full register: `Audits\2026-08-04\REAL_WORLD_VALIDATION_ISSUES.md`.

- **P0 — Collection/source-type synchronization (Item 8):** collections can
  carry a default source type with no processing profile, blocking handoff.
  `cij_transcript` currently exists in Config with no processing profile.
- **P1 — Processing cancellation (Item 4):** no cancel control for in-flight
  multi-source runs.
- **P1 — Subtitle import workflow (Item 10):** two overlapping subtitle paths;
  subtitle profile not exposed in Config.
- **P1 — Import filesystem (Item 1):** no folder/bulk import.
- **P1 — Teppei metadata cleanup (Item 7):** stale runtime references to
  removed vocabulary remain in `gui_settings.json` / `quick_presets.json`.
- **P2 — Collection folder hierarchy (2), non-episode content model (3),
  duplicate analysis workflow (5), embedded tab workflow (6), template editor
  validation (9).**
- **Real-data loop not yet re-verified:** the one existing real response
  (pre-fix) failed at corpus build; the fixed canonicalizer pipeline has not
  been re-run against it.
- **Frozen contract narratives not reconciled** with the canonicalization
  stage (PARSER_OUTPUT_SPEC §3/§14, parser_prompt.md, README, PROJECT_STATUS).
- **API-key hygiene:** `api_key.txt` contains a real key; must be
  removed/rotated and moved to a non-committed mechanism before external review.

---

## 8. Rules for Future AI Sessions

1. **Read this document first** (stable engineering context).
2. **Then read `PROJECT_STATUS.md`** (milestone history and status table).
3. **Then read the latest audit set** under `Audits\<date>\` (current
   regression, known issues, real-world validation register).
4. **Review before recommending changes** — establish current state and the
   correct owner before proposing anything.
5. **Do not modify files without explicit approval.** Audit first, modify
   second. For each proposed change state: Problem → Current owner → Correct
   owner → Proposed change → Regression risk, then wait for approval.
6. **Separate observations, evidence, and recommendations** in every response.
7. Preserve frozen contracts (parser prompt, PARSER_OUTPUT_SPEC, source
   template spec, PM API, artifact schemas) unless a change is explicitly
   approved.
8. Do not create temporary patches that bypass architectural problems; prefer
   correct ownership over minimum line changes.

---

## 9. Documentation Authority Hierarchy

| Level | Document(s) | Role |
|---|---|---|
| **1 — Contract (frozen, highest)** | `PARSER_OUTPUT_SPEC.md`, `Prompts\parser_prompt.md`, `SOURCE_TEMPLATE_SPEC.md`, `Production Manager\GUI_API.md`, `API_VERSION.md`, `Source Intake\schemas.py` | Define behavior that must not change without explicit approval. |
| **2 — Current architecture** | `ARCHITECTURE_CURRENT.md`, `SOURCE_PACKAGE_HANDOFF.md` | Describe the implemented application and workflows as they are now. |
| **3 — Project memory / continuity** | `PROJECT_CONTEXT.md` (this file), `JPROGRAM_SESSION_BOOTSTRAP.md` | Stable engineering context for fresh AI sessions. |
| **4 — Status / history** | `PROJECT_STATUS.md`, `README.md` | Milestone-by-milestone status; some historical sections are dated and annotated. |
| **5 — Audit records (evidence)** | `Audits\<date>\` (`Project_Audit`, `Documentation_Audit`, `Final_Baseline_Audit`, `Session_Handoff_Audit`, `REAL_WORLD_VALIDATION_ISSUES`, etc.) | Point-in-time findings; the latest date is the current baseline. |
| **6 — Historical / frozen snapshots** | `Daily Handoff\V1_FREEZE_2026-08-02\`, older `Daily Handoff\*` design docs | Dated snapshots and superseded designs; not current. |

Conflict rule: a frozen contract (level 1) wins over narrative documents; the
latest audit (level 5) is the current evidence baseline; historical status
sections in level 4 are superseded by level 2–3 documents.

---

*End of project context.* STOPPED.
