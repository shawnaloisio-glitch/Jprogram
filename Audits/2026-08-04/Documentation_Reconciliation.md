# Documentation Reconciliation Audit

**Project:** Japanese Corpus Pipeline (C:\Jprogram)
**Date:** 2026-08-04
**Basis:** Audits\2026-08-04\Documentation_Audit.md, Audits\2026-08-04\Project_Audit.md, and direct verification of the implementation.
**Type:** Audit only — no files modified.

This document compares documentation claims against the actual implementation
state and identifies what must be updated before an external (Qwen) review.

---

# 1. Accurate Documentation

Documentation that matches the implementation:

| Document | Claim verified against implementation | Verdict |
|---|---|---|
| `Prompts\parser_prompt.md` | Frozen DeepSeek parser prompt | Accurate — file is non-empty (11,492 bytes) and is the active parser prompt. |
| `PARSER_OUTPUT_SPEC.md` | Frozen parser output field specification (positional arrays, sentence/word/chunk/expression rules, job-local positions) | Accurate — matches `response_validator.py` and `corpus_builder.py` behavior. |
| `SOURCE_TEMPLATE_SPEC.md` | Frozen V1.0 source template; 15 four-digit episode blocks; SOURCE header fields | Accurate — matches `Templates\transcript_template.txt` and `subtitle_template.txt` (verified headers + EPISODE markers). |
| `Production Manager\README.md` | PM is a thin observer/launcher; ownership boundaries; state machine; CLI flags | Accurate — matches `production_manager.py` (`state_for`, `launch_stage`, `pipeline`, CLI argparse). |
| `Production Manager\GUI_API.md` | Frozen public API: `status`, `report`, `dry_run`, `run_stage`, `pipeline` | Accurate — all five functions exist with the documented signatures (verified lines 788/816/828/852/867). |
| `Production Manager\API_VERSION.md` | API frozen at 1.0 | Accurate. |
| `Source Intake\schemas.py` (self-docstring) | Registry / Cleaning Job / Cleaning Result schemas | Accurate — matches the three `ARTIFACT_SCHEMAS` entries and the writers. |
| `Logs\README.md` (purpose + philosophy sections) | Logs record execution; logs are not corpus data; permanent vs temporary files | Accurate (philosophy). |
| `Source Builder\source_package.py` (docstring) | Source Package sidecar beside canonical file; fields; atomic writes | Accurate. |
| `Source Builder\handoff.py` (docstring) | Handoff creates Registry entry + Cleaning Job; idempotent via sha256 | Accurate. |
| `README.md` evidence-preservation architecture (sentence/word/lexical/chunk/expression layers, parser-never-analyzes) | Matches corpus_builder / validator / analyzer responsibilities | Accurate (narrative). |

---

# 2. Documentation Drift

| # | Document / file | Current statement | Actual implementation | Required update |
|---|---|---|---|---|
| 1 | `README.md` (lines ~77–89, 74) | "Source Intake — utility + artifact writers implemented"; "Not yet implemented: source_intake.py coordinator, duplicate_check.py, cleaner execution, pipeline orchestration"; "(planned) UI" | Source Intake is complete (incl. coordinator + duplicate_check); cleaners and pipeline orchestration exist; the UI (app shell, Sources/Processing/Analysis) is implemented | Refresh implementation-status section; remove "(planned) UI"; state the GUI/PM path and that intake coordinator is bypassed by handoff. |
| 2 | `PROJECT_STATUS.md` (Sections 10, 24 vs 28, 34) | "parser prompt has NOT yet been written" and "must not be created yet" vs "Parser prompt — Complete (frozen)" | parser_prompt.md exists and is frozen | Resolve internal contradiction; state parser prompt is complete. |
| 3 | `PROJECT_STATUS.md` (Section 28) | "Corpus Builder — Not started (next stage)"; "Corpus Analytics — Not started"; "GUI — Future possibility" | Corpus Builder is implemented and tested; Analysis modules are implemented and tested; GUI exists | Update status table. |
| 4 | `PROJECT_STATUS.md` (Sections 13–16, 26–27) | DeepSeek Client "at steps 2–3", "API NOT yet connected", stopping point = "next test of deepseek_client.py" | deepseek_client.py is complete with full API/retry/logging/resume | Update to current status. |
| 5 | `PROJECT_STATUS.md` (Section 3 project structure) | Structure tree omits Source Builder, Source Package, Handoff, app.py, Production Manager GUI API | Project structure has grown | Refresh structure tree. |
| 6 | `JPROGRAM_SESSION_BOOTSTRAP.md` (Sections 6, 10) | "Source Intake Phase 3 (coordinator, duplicate_check) not implemented; awaiting Phase 3" | source_intake.py and duplicate_check.py exist; Source Intake complete | Update status. |
| 7 | `ANALYZER_ARCHITECTURE.md` (header) | "no code yet" | All nine analyzer modules exist and are tested | Update status line to "implemented". |
| 8 | `Daily Handoff\GUI_ARCHITECTURE.md` | GUI is "thin presentation layer" with "drag & drop" of raw files, "folder browsing", displays pipeline state per source | The implemented GUI is a tabbed shell embedding the Source Builder; Processing/Analysis windows; **no drag & drop and no artifact browsing** (verified: no dnd handlers) | Correct the GUI description; describe the actual shell + windows. |
| 9 | `Daily Handoff\SOURCE_METADATA_SPEC.md` (config examples) | source_types example: [podcast_transcript, subtitle, article, manga_text, book_text]; origins example: [con_teppei_podcast, nhk_news, anime_broadcast, user_transcription] | Cleaned Config: source_types=[podcast_transcript]; origins=[user_transcription]; collections=[] | Update examples to current cleaned vocab. |
| 10 | `Daily Handoff\SOURCE_BUILDER_SPEC.md` / `SOURCE_BUILDER_GUI_DESIGN.md` / `SOURCE_BUILDER_GUI_IMPLEMENTATION_PLAN.md` / `SOURCE_BUILDER_IMPLEMENTATION_SPEC.md` | Button/panel names: "Create Next Source", "Workflow Panel", "Edit Metadata..." admin group | Current UI: "Add Another", panel titled "Status", admin group includes Open Folder / Edit Metadata... / Processing; "Send to Processing" removed | Update UI term references. |
| 11 | `Logs\README.md` (folder listing) | Subfolders: Cleaner/, Job Builder/, Processor/, Merger/, Analysis/ | Actual subfolders: Analysis, Cleaning, Corpus Builder, DeepSeek Client, Job Builder, Job Creation, Merging, Processing, Production Manager, Request Builder, Source Intake, Subtitle Cleaner, Transcript Cleaner | Correct folder listing. |
| 12 | `README.md` / `PROJECT_STATUS.md` source-type coverage | "Supported sources include podcast transcripts, anime subtitles" | Config exposes only `podcast_transcript`; `anime_subtitle` exists in pipeline profiles but is not in the cleaned Config | Align supported-source claims with the cleaned config. |
| 13 | `Daily Handoff\V1_FREEZE_2026-08-02\05_TOMORROW.md` | "Begin GUI" (dated 2026-08-03) | GUI is already implemented | Historical snapshot; do not treat as current plan. |

---

# 3. Missing Documentation

Implemented features with no (or no current) documentation:

| Feature | Implementation | Documentation status |
|---|---|---|
| **Application Shell** | `app.py` — 3-tab notebook embedding Source Builder; Processing/Analysis open child windows | No current doc; only a dated V1-freeze file index mentions it. |
| **Source Package** | `Source Builder\source_package.py` (build/write/validate; sidecar `.source.json`) | No spec doc (only module docstring). |
| **Handoff** | `Source Builder\handoff.py` (registry + cleaning job; idempotent) | No spec doc (only module docstring). |
| **Import Material** | `Source Builder\import_material.py` + `_import_material` dialog (5 formats incl. subtitle reuse of Subtitle Importer cleaner) | No doc. |
| **Recent Sources** | `Source Builder\recent_sources.py` (max 10, human labels) + GUI list | No doc. |
| **Quick Presets / Templates GUI** | `Source Builder\quick_presets.py` + preset editor (renamed "Templates") | Only the source-template file format is documented; the GUI presets feature is not. |
| **Processing UI** | `Source Builder\processing_tab_gui.py` + `processing_tab.py` (selection, batch process, retry, run analysis, Export Diagnostics) | No GUI doc (pipeline side is covered by PM README / GUI_API). |
| **Analysis UI** | `Source Builder\analysis_tab_gui.py` (list corpora, Run Analysis, Open Reports) | No GUI doc. |
| **Diagnostics** | `Source Builder\diagnostics.py` (gzipped bundle: identity, report, artifacts, logs, environment) | No doc (module docstring only). |
| **Configuration cleanup state** | Cleaned Config: empty collections, source_types=[podcast_transcript], origins=[user_transcription] | No doc of the current cleaned state. |
| **Testing state** | 722 tests across suites; 5 live-Config fixture failures; PM/Analysis/DP suites | No test documentation/README describing the suite layout or how to run it. |
| **Pipeline stage scripts (current)** | `job builder.py`, `request builder.py`, `deepseek_client.py`, `corpus_builder.py`, cleaners — current behavior | Covered partially by older PROJECT_STATUS sections; no current per-stage guide. |
| **Source Intake coordinator** | `source_intake.py`, `duplicate_check.py` (complete, unused in GUI path) | No current doc; bootstrap says Phase 3 not implemented. |

---

# 4. Architecture Corrections

Places where documentation describes pathways/ownership/contracts that do not match the implementation:

| # | Document claim | Actual | Correction type |
|---|---|---|---|
| 1 | GUI_ARCHITECTURE.md: GUI does "drag & drop", "folder browsing", displays per-source pipeline state | Implemented GUI: tabbed shell + Source Builder + Processing/Analysis windows; **no drag & drop, no artifact browsing** | **Unused/historical pathway** described as current |
| 2 | GUI_ARCHITECTURE.md / PM README: "GUI reads state through the API, never by opening pipeline artifacts" | Partially true: `processing_tab.py` calls PM API (`state_for`/`pipeline`), but `discover_packages()` reads Source Packages directly from disk, and `_display_name_for_collection` reads Config directly | **Incorrect module ownership** (GUI-side code reads packages/config directly, not only through PM API) |
| 3 | PROJECT_STATUS.md / bootstrap: "Source Intake owns Source Registry + Cleaning Job creation; future managers orchestrate" | Current GUI path: `handoff.py` (Source Builder module) creates Registry + Cleaning Job via the Source Intake writers; `source_intake.py` coordinator is not invoked | **Outdated ownership/contract** description |
| 4 | README/PROJECT_STATUS: "DeepSeek transport frozen"; "Parser, validator, builder, canonical JSONL, analyzers frozen" | Accurate, but PROJECT_STATUS status table contradicts itself (Builder "not started" vs complete) | **Outdated contract status** |
| 5 | README: "(planned) UI" | UI implemented | **Outdated workflow/roadmap** |
| 6 | V1_FREEZE\02_ARCHITECTURE.md: "GUI (future — not yet built)" | GUI exists | **Historical snapshot** (frozen; not current) |
| 7 | SOURCE_METADATA_SPEC.md: controlled vocabulary examples include removed values | Config cleaned | **Outdated contract examples** |

---

# 5. Required Documentation Updates Before Qwen Review

## HIGH — must update before external review

| # | Update |
|---|---|
| H1 | Refresh `README.md` implementation-status section: Source Intake complete, cleaners + pipeline orchestration implemented, GUI exists (remove "(planned) UI"). |
| H2 | Refresh `PROJECT_STATUS.md` status table + DeepSeek/parser/Corpus Builder sections to current state; remove internal contradictions. |
| H3 | Refresh `JPROGRAM_SESSION_BOOTSTRAP.md`: Source Intake complete; add current entry points (app.py, Processing, Analysis). |
| H4 | Add a current **Application Shell / Sources / Processing / Analysis** documentation (or a single current-state README section) — the most visible gap. |
| H5 | Document the **Source Package** and **Handoff** contracts (fields, sidecar, idempotency) — they are core active contracts with no spec. |
| H6 | Document **API key handling** requirement (key must not be in tree; env-var loading) — release-critical. |

## MEDIUM — should update

| # | Update |
|---|---|
| M1 | Correct `Daily Handoff\GUI_ARCHITECTURE.md` (remove drag & drop / artifact-browsing claims; describe actual shell + windows; correct the "reads only via API" ownership claim). |
| M2 | Update `SOURCE_METADATA_SPEC.md` config examples to the cleaned vocab. |
| M3 | Update Source Builder spec/design docs UI terms ("Create Next"→"Add Another", "Workflow Panel"→"Status", "Quick Presets"→"Templates", remove "Send to Processing"). |
| M4 | Correct `Logs\README.md` folder listing. |
| M5 | Document **Import Material** (formats, subtitle reuse) and **Recent Sources** behavior. |
| M6 | Document **Diagnostics** bundle contents/usage. |
| M7 | Document the **current Config state** and the project-language (`ja`) assumption. |

## LOW — future improvement

| # | Update |
|---|---|
| L1 | Document the testing suite layout and how to run it (no test README exists). |
| L2 | Document the Source Intake coordinator + duplicate_check (currently unused in the GUI path) and whether it should replace handoff's direct writer calls. |
| L3 | Document packaging / launch instructions. |
| L4 | Reconcile the V1_FREEZE frozen snapshots as historical (add a note they are dated snapshots, not current). |
| L5 | Add a per-stage pipeline guide reflecting the current stage scripts. |

---

# 6. Final Recommendation

**Is the project documentation accurate enough for Qwen review?**
**NO.**

**Why:**
- The frozen **contracts** (parser prompt, parser output spec, source template, PM API, artifact schemas) are accurate and match the implementation — these provide a solid technical core.
- However, the **current-state documentation is materially wrong**: `README.md`, `PROJECT_STATUS.md`, and `JPROGRAM_SESSION_BOOTSTRAP.md` describe Source Intake as partially implemented, the parser prompt as unwritten, the Corpus Builder as not started, and the GUI as "future" — all of which are implemented and tested. An external reviewer relying on these documents would form a substantially incorrect picture.
- Several architecture claims are outdated or inaccurate: the GUI architecture document describes drag & drop / artifact browsing that does not exist and states the GUI reads state only via the PM API (the implementation reads packages/config directly in places); the Source Intake ownership description does not match the handoff-driven path.
- The largest implemented feature group — the Application Shell, Source Builder GUI, Source Package, Handoff, Import Material, Recent Sources, Processing UI, Analysis UI, and Diagnostics — has **no current documentation** at all.
- The 5 live-Config test failures and the still-present `api_key.txt` are implementation-state issues that must be resolved and documented before review.

**Recommendation (identification only):** address the HIGH items (H1–H6) — especially refreshing the three root status documents and adding current docs for the shell and the Source Package/Handoff contracts — before an external review. The frozen pipeline contracts themselves are trustworthy; the project-level "current state" documentation is not.

---

*End of documentation reconciliation audit.* STOPPED.
