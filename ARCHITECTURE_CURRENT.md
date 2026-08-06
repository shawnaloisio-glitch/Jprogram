# ARCHITECTURE_CURRENT

**Japanese Corpus Pipeline — Current Architecture**

Date: 2026-08-04
Status: Current-state reference (matches the implemented application)

This document describes the implemented architecture as of the current
milestone: pipeline, Source Package, Handoff, Application Shell
(Sources / Processing / Analysis), and Analysis surface are complete and
tested. Runtime data is reset and metadata config is cleaned.

---

## 1. Application Structure

```
C:\AI Development Projects\Jprogram\
│
├── app.py                          # Application Shell (primary entry point)
│
├── Source Builder\                 # Sources UI + workflow + orchestration
│   ├── gui.py                      # Source Builder GUI (embedded in Sources tab)
│   ├── source_builder.py           # Standalone Source Builder launcher
│   ├── controller.py               # Validation, filenames, ReadyStateEngine
│   ├── source_package.py           # Source Package (sidecar .source.json)
│   ├── handoff.py                  # Registry + Cleaning Job creation
│   ├── import_material.py          # Import Material format conversion
│   ├── recent_sources.py           # Recent Sources list (max 10)
│   ├── quick_presets.py            # Quick Presets ("Templates")
│   ├── gui_settings.py             # Persisted GUI settings
│   ├── config_loader.py            # Config\ vocabulary loader
│   ├── metadata_editor.py / _gui   # Edit Collections / Source Types / Origins
│   ├── processing_tab.py           # Processing orchestration (discovery, PM)
│   ├── processing_tab_gui.py       # Processing window
│   ├── analysis_tab_gui.py         # Analysis window
│   └── diagnostics.py              # Diagnostics bundle ("Export Diagnostics")
│
├── Production Manager\
│   ├── production_manager.py       # Pipeline orchestrator (CLI + API)
│   ├── README.md / GUI_API.md / API_VERSION.md
│
├── Data Processor\                 # Pipeline stage programs
│   ├── job builder.py              # clean text → jobs
│   ├── request builder.py          # jobs → DeepSeek requests
│   ├── deepseek_client.py          # DeepSeek API transport
│   ├── response_validator.py       # deterministic validation gate
│   ├── corpus_builder.py           # validated responses → canonical JSONL
│   ├── *result.py                  # per-stage result envelopes
│   └── (runtime: jobs/ requests/ responses/ jsonl/ processing/ etc.)
│
├── Subtitle Cleaner\               # clean_subtitles.py
├── Transcript Cleaner\             # clean_transcript.py
├── Subtitle Importer\              # cleaner.py (reused by Import Material)
├── Source Intake\                  # artifact writers + coordinator
│   ├── schemas.py                  # frozen artifact schemas
│   ├── registry.py / cleaning_job.py / cleaning_result.py
│   ├── source_id.py / hashing.py / resolver.py / duplicate_check.py
│   └── source_intake.py            # coordinator (complete, not GUI-invoked)
├── Analysis\                       # analyzer modules (read canonical corpus)
├── Common\cleaning_utils.py
├── Config\                         # controlled vocabulary (collections.json,
│                                   # source_types.json, origins.json)
├── Prompts\parser_prompt.md        # frozen parser prompt
├── Templates\                      # frozen source templates
└── root shared modules: paths.py, project_config.py, common.py
```

---

## 2. User Workflow

1. **Launch** `app.py` → the Application Shell opens with three tabs.
2. **Sources tab** — the Source Builder is embedded:
   - Select identity: Collection or Standalone.
   - Fill metadata (collection + episode, or source name), source type, origin.
   - **Import Material**: convert a raw file (podcast transcript, subtitle,
     ebook, OCR, plain text) into the text area.
   - Review the text; the Ready State Engine shows the workflow state
     (INCOMPLETE / READY / SAVED / ERROR).
   - **Save Source** writes the canonical `.txt` plus a `.source.json` sidecar
     (Source Package).
   - Quick Presets ("Templates") and Recent Sources speed up repeated entry.
   - Administrative actions: Open Folder, Edit Metadata..., Processing.
3. **Processing tab / window**:
   - Lists saved source packages with human labels and pipeline status.
   - **Process Selected** runs the pipeline sequentially (handoff first if
     needed, then clean → jobs → requests → api → corpus).
   - **Retry Failed** re-runs failed sources.
   - **Run Analysis** runs a basic frequency analysis on corpus-ready sources.
   - **Export Diagnostics** writes a compressed diagnostic bundle.
4. **Analysis window**:
   - Lists sources with a completed corpus.
   - **Run Analysis** writes `Analysis\outputs\*.frequency.json`.
   - **Open Reports** opens the Analysis outputs folder.

---

## 3. Data Lifecycle

```
Input material
   ↓ (Import Material / paste)
Source creation (controller.py)            → Sources\<type>\<id>_epNNNN.txt
   ↓ (sidecar)
Source Package (source_package.py)          → <canonical>.source.json
   ↓ (handoff)
Registry (Source Intake registry writer)    → Source Registry\<source_id>.json
Cleaning Job (Source Intake cleaning_job)   → Cleaning Jobs\<source_id>.cleaning_job.json
   ↓ (cleaner)
Cleaned Archive + Cleaning Result           → Cleaned Archive\*.clean.txt
                                              Cleaning Results\*.cleaning_result.json
   ↓ (job builder)
Jobs + Job Result                           → Data Processor\jobs\, Job Results\
   ↓ (request builder)
Requests + Request Result                   → Data Processor\requests\, Request Results\
   ↓ (deepseek_client)
Responses + Processing Result               → Data Processor\responses\, Processing Results\
   ↓ (response_validator)
Validation verdict                          (PARSER_OUTPUT_SPEC.md contract)
   ↓ (corpus_builder)
Canonical JSONL + Corpus Result             → Data Processor\jsonl\<source_id>.jsonl
   ↓ (analysis)
Analysis outputs                            → Analysis\outputs\*.frequency.json
```

---

## 4. Module Ownership

| Responsibility | Owner |
|---|---|
| Source capture / validation / filenames | `Source Builder\controller.py` |
| Source Package artifact | `Source Builder\source_package.py` |
| Registry + Cleaning Job creation (GUI path) | `Source Builder\handoff.py` (via Source Intake writers) |
| Source Registry / Cleaning Job / Cleaning Result writers + schemas | `Source Intake\` |
| Cleaning content | `Subtitle Cleaner\`, `Transcript Cleaner\` |
| Subtitle file conversion | `Subtitle Importer\cleaner.py` (reused by Import Material) |
| Jobs / Requests / API transport / Validation / Corpus | `Data Processor\` stage programs |
| Pipeline orchestration + status | `Production Manager\production_manager.py` |
| Analyzer modules (read canonical corpus) | `Analysis\` |
| GUI orchestration (discovery, process, analyze) | `Source Builder\processing_tab.py` |
| Diagnostics bundle | `Source Builder\diagnostics.py` |
| Controlled vocabulary | `Config\*.json` |
| Project paths / settings | `paths.py`, `project_config.py` |

Ownership rules: every pipeline artifact is written exclusively by its owning
stage program; the Production Manager only observes/launches; the GUI consumes
state through the Production Manager API and reads source packages directly for
discovery/display.

---

## 5. Contracts

| Contract | Location |
|---|---|
| Parser output field specification | `PARSER_OUTPUT_SPEC.md` (frozen) |
| Parser prompt | `Prompts\parser_prompt.md` (frozen) |
| Source template | `SOURCE_TEMPLATE_SPEC.md`, `Templates\*.txt` (frozen) |
| Registry / Cleaning Job / Cleaning Result schemas | `Source Intake\schemas.py` (frozen) |
| Source Package | `Source Builder\source_package.py` (`SOURCE_PACKAGE_HANDOFF.md`) |
| Canonical JSONL corpus | `Data Processor\corpus_builder.py` |
| Production Manager API | `Production Manager\GUI_API.md`, `API_VERSION.md` (frozen V1.0) |

---

## 6. Runtime Data Separation

| Category | Folders | State (2026-08-04) |
|---|---|---|
| Application code | `app.py`, `Source Builder\`, `Production Manager\`, `Data Processor\`, `Analysis\`, `Source Intake\`, cleaners, `Common\`, root shared modules | Present |
| Configuration | `Config\` (collections, source_types, origins) | Clean: collections empty; source_types=[podcast_transcript]; origins=[user_transcription] |
| User-created data | `Sources\` (collections/standalone) | Empty |
| Generated runtime artifacts | `Source Registry\`, `Cleaning Jobs\`, `Cleaning Results\`, `Cleaned Archive\`, `Processing Results\`, `Data Processor\` runtime subfolders, `Analysis\outputs\` | Empty |
| Diagnostics | `Diagnostics\` | Empty |
| Logs | `Logs\` (13 subfolders + README) | Only README |
| Tests | all `tests\` folders + dev scripts | Present |
| Developer tools | `project_audit.py`, dev-only `*_test.py` scripts, standalone launchers | Present |

The application launches from a clean state; user data can be removed without
affecting the application.
