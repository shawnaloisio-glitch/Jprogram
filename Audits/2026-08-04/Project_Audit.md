# Project Audit — Internal Baseline

**Project:** Japanese Corpus Pipeline (C:\Jprogram)
**Date:** 2026-08-04
**Type:** Internal baseline audit — audit only, no files modified.

This baseline documents the application architecture, the complete data
lifecycle, contracts/schemas, runtime data separation, testing coverage,
configuration, release readiness, and risks before any external review.

---

# 1. Application Architecture

## Main entry points

| Entry point | Path | Purpose | Type |
|---|---|---|---|
| `app.py` | C:\Jprogram\app.py | Application shell (3 tabs: Sources / Processing / Analysis) | Active (primary) |
| `Source Builder\source_builder.py` | C:\Jprogram\Source Builder\source_builder.py | Standalone Source Builder launcher (`gui.main()`) | Active (secondary) |
| `Subtitle Importer\subtitle_importer.py` | C:\Jprogram\Subtitle Importer\subtitle_importer.py | Standalone Subtitle Importer GUI launcher | Developer-only / legacy entry |
| `Production Manager\production_manager.py` | C:\Jprogram\Production Manager\production_manager.py | CLI: `--source/--run/--pipeline/--dry-run` | Active (CLI) |
| Pipeline stage scripts (CLI) | C:\Jprogram\Data Processor\*.py, Subtitle/Transcript Cleaner\*.py | `clean_transcript.py`, `clean_subtitles.py`, `job builder.py`, `request builder.py`, `deepseek_client.py`, `corpus_builder.py` | Active (CLI, invoked by PM) |

## Application shell structure

`ApplicationShell` (app.py) builds a `ttk.Notebook` with three tabs:

- **Sources tab** — embeds `SourceBuilderApp` (the full Source Builder GUI) directly into the tab.
- **Processing tab** — a summary panel with an "Open Processing" button that opens `ProcessingTabWindow`.
- **Analysis tab** — a summary panel with an "Open Analysis" button that opens `AnalysisTabWindow`.

Child windows are centred over the shell via `_center_child_over_parent`.

## Active user-facing components

### Sources (Source Builder)
- **Purpose:** capture, import, and save canonical source files with metadata (collection/standalone identity, source_type, origin), enforce completeness via the Ready State Engine, manage quick presets and recent sources.
- **Main modules:** `Source Builder\gui.py` (GUI), `controller.py` (validation, filenames, canonical save, ReadyStateEngine), `source_package.py` (package build/write/validate), `handoff.py` (registry + cleaning job), `import_material.py` (format conversion), `recent_sources.py`, `quick_presets.py`, `gui_settings.py`, `config_loader.py`, `metadata_editor.py` + `metadata_editor_gui.py`, `diagnostics.py`.
- **Dependencies:** `paths.py`, `project_config.py`, `common.py` (root shared modules); Source Intake artifact writers (`registry.py`, `cleaning_job.py`); Subtitle Importer cleaner (for .srt/.vtt import).
- **Status:** Active, tested.

### Processing (Processing window + pipeline orchestration)
- **Purpose:** list saved source packages with human labels/status, run the pipeline (clean→jobs→requests→api→corpus) sequentially, retry failed sources, export diagnostics.
- **Main modules:** `Source Builder\processing_tab_gui.py` (window), `processing_tab.py` (discovery, status mapping, process orchestration, analysis trigger).
- **Dependencies:** Production Manager API (`status/report/run_stage/pipeline`), pipeline stage scripts via subprocess, `diagnostics.py`.
- **Status:** Active, tested (PM + GUI + orchestration tests; pipeline subprocess launch mocked in tests).

### Analysis (Analysis window + analyzer modules)
- **Purpose:** list corpus-ready sources, run a basic frequency analysis, open the Analysis outputs folder.
- **Main modules:** `Source Builder\analysis_tab_gui.py` (window), `processing_tab.run_analysis` (orchestration), `Analysis\*` modules (`corpus_loader`, `frequency_analyzer`, `distribution_analyzer`, `exposure_analyzer`, `expression_analyzer`, `chunk_analyzer`, `sentence_metrics`, `comparison_analyzer`, `output_writer`).
- **Dependencies:** canonical JSONL corpus (read-only), `output_writer`.
- **Status:** Active, tested (analyzer modules unit-tested; GUI window tested; analysis against a *real* corpus not tested end-to-end).

## Active / legacy / developer-only classification

| Category | Items |
|---|---|
| **Active code** | app.py; Source Builder modules (all); Production Manager; Data Processor stage scripts (corpus_builder, deepseek_client, job builder, request builder, response_validator); Subtitle/Transcript Cleaner; Source Intake modules; Analysis modules; Common; root shared modules (paths.py, project_config.py, common.py). |
| **Legacy / obsolete** | `Data Processor\process_file.py` (stale copy of old clean_transcript.py; not imported by any active code, referenced only in tests as a "forbidden import"); `cleaner common.py` (root, an outdated duplicate of paths.py; imported by nothing); `Data Processor\corpus_builder_test.py` and `response_validator_test.py` (ad-hoc dev scripts outside `tests\`, hardcode external benchmark paths `C:\Users\Shawn\AppData\Local\Temp\opencode\parser_bench`); `Source Intake\source_intake.py` + `duplicate_check.py` (complete but not invoked by the GUI/PM path — the GUI handoff uses registry/cleaning_job writers directly). |
| **Developer-only entry points** | `Subtitle Importer\subtitle_importer.py` / `gui.py` (standalone GUI not wired into app.py; the cleaner is reused via import_material, the GUI launcher is separate); `project_audit.py` (developer audit tool); Production Manager CLI. |

---

# 2. Complete Data Lifecycle Audit

User workflow: Input material → Source creation/import → Source Package → Handoff → Registry → Cleaning → Job creation → Request creation → API processing → Validation → Corpus creation → Analysis.

| Stage | Responsible module | Input | Output | Contract / artifact | Error handling | User visibility |
|---|---|---|---|---|---|---|
| **Input material** | (user) / Import Material | Raw transcripts / subtitle files | Normalized text lines | Import formats: podcast_transcript, subtitle, ebook, ocr, plain_text | ImportError on unknown format / empty / read failure | Sources → Import Material |
| **Source creation** | `controller.py` (`create_collection_source` / `create_standalone_source`) | metadata + source text | Canonical `.txt` in `Sources\collections\<id>\` or `Sources\standalone\` | Canonical filename `{collection_id}_epNNNN.txt` / `{source_name}.txt`; atomic write | Validation errors returned; SourceBuilderError | Sources form → Save |
| **Source Package** | `source_package.py` (`build_package`/`write_package`) | canonical file | Sidecar `<stem>.source.json` | `artifact_type=source_package`, `schema_version=1`, fields incl. source_id, source_type, origin, language, canonical_path, sha256, cleaning_profile, cleaner_version | SourcePackageError on missing file / missing identity / invalid | Implicit (sidecar written on save); schema in package |
| **Handoff** | `handoff.py` (`handoff`/`handoff_for_package_path`) | source package | Source Registry entry + Cleaning Job artifact | Registry schema + Cleaning Job schema (Source Intake `schemas.py`) | HandoffError; idempotent via sha256 | Not surfaced (automatic; previously a button, now invoked by Processing) |
| **Registry** | `Source Intake\registry.py` (`build_entry`/`write_registry`) | package fields | `Source Registry\<source_id>.json` | Registry schema v1; atomic write; UTF-8, ensure_ascii=False, sort_keys | RegistryError | Not surfaced |
| **Cleaning** | `Subtitle Cleaner\clean_subtitles.py` / `Transcript Cleaner\clean_transcript.py` (dispatched by PM `_cleaner_script`) | Cleaning Job → raw source | `Cleaned Archive\<source_id>.clean.txt` + Cleaning Result | Cleaning Result schema v1; clean artifact extension `.clean.txt` | Cleaner errors → Cleaning Result success=false; PM reports failure | Processing status "Failed while preparing the source" |
| **Job creation** | `Data Processor\job builder.py` | clean text | `jobs\<source_id>\` job files + Job Result | Job Result artifact (job_builder_result) | PM validates result artifact | Not surfaced (status map) |
| **Request creation** | `Data Processor\request builder.py` | jobs | `requests\<source_id>\request_*.json` + Request Result | Request Result artifact; `user_content()` prepends SOURCE METADATA section | PM validates result | Not surfaced |
| **API processing** | `Data Processor\deepseek_client.py` | requests | `responses\<source_id>\` raw responses + Processing Result | Processing Result artifact; parser deepseek-v4-flash, non-thinking, json_object, max_tokens=32768, hybrid fixed-position-array | Retry/timeout; PM reports API failure | Status "Failed during AI processing" |
| **Validation** | `Data Processor\response_validator.py` | responses | Validation verdict (valid/errors/warnings) | PARSER_OUTPUT_SPEC.md frozen contract | Fatal vs non-fatal distinction | Not surfaced |
| **Corpus creation** | `Data Processor\corpus_builder.py` | validated responses + request metadata | `jsonl\<source_id>.jsonl` (canonical sentence-per-line JSONL) + Corpus Result | Canonical JSONL format; deterministic normalization, span recompute, global IDs, provenance, reconstruction check | Corpus Result success=false on failure; PM reports | Status "corpus_available" / "Failed while producing the final output" |
| **Analysis** | `processing_tab.run_analysis` + `Analysis\frequency_analyzer`/`corpus_loader` | canonical JSONL | `Analysis\outputs\*.frequency.json` | Derived data product (read-only consumer) | ProcessingTabError "No corpus available" / "Analysis failed" | Analysis window; "Analysis complete: <path>" |

### Lifecycle observations
- The GUI/PM path never invokes `Source Intake\source_intake.py` (the coordinator) or `duplicate_check.py`; Handoff reuses the artifact writers directly. This is additive orchestration, not a contract change.
- The full pipeline (real subprocess + real API) is **not** exercised by the automated test suite; it is covered by dev scripts (`corpus_builder_test.py`, `response_validator_test.py`) that depend on external benchmark data, and by the PM integration/launcher tests that create synthetic stage scripts.

---

# 3. Contract and Schema Review

| Contract / schema | Definition location | Classification |
|---|---|---|
| Parser output spec (DeepSeek → validator → builder → analyzer) | `PARSER_OUTPUT_SPEC.md` | **Active contract** (frozen) |
| Parser prompt | `Prompts\parser_prompt.md` | **Active contract** (frozen) |
| Source template (transcript/subtitle) | `SOURCE_TEMPLATE_SPEC.md`, `Templates\*.txt` | **Active contract** (frozen) |
| Registry schema | `Source Intake\schemas.py` (ARTIFACT_SCHEMAS["registry"]) | **Active contract** (frozen) |
| Cleaning Job schema | `Source Intake\schemas.py` (ARTIFACT_SCHEMAS["cleaning_job"]) | **Active contract** (frozen) |
| Cleaning Result schema | `Source Intake\schemas.py` (ARTIFACT_SCHEMAS["cleaning_result"]) | **Active contract** (frozen) |
| Source Package schema | `Source Builder\source_package.py` (validate_package / ARTIFACT_TYPE=source_package, SCHEMA_VERSION=1) | **Active contract** (GUI-side; frozen by task lock) |
| Job Result / Request Result / Processing Result / Corpus Result | `Data Processor\job_builder_result.py`, `request_builder_result.py`, `processing_result.py`, `corpus_builder_result.py` | **Internal implementation detail** (result envelopes consumed by PM) |
| Canonical JSONL corpus output | `Data Processor\corpus_builder.py` (jsonl_writer, canonical record) | **Active contract** (corpus consumers read it) |
| Analysis outputs | `Analysis\output_writer.py` + analyzer modules | **Internal implementation detail** (derived data products) |
| Production Manager public API | `Production Manager\GUI_API.md`, `API_VERSION.md` | **Active contract** (frozen V1.0) |
| Source Intake coordinator / duplicate_check | `Source Intake\source_intake.py`, `duplicate_check.py` | **Historical/unused in current GUI path** (complete but not invoked by the app) |

### Undocumented assumptions observed
- The Source Package schema is validated only by `source_package.validate_package` and is **not** part of Source Intake's `ARTIFACT_SCHEMAS` (no shared schema registry entry for it).
- `user_content()` in the Request Builder prepends a `SOURCE METADATA` block; `corpus_builder.job_text_from_user_content` strips it for reconstruction. This coupling is not documented in a spec file.
- Cleaning Profile / cleaner version mapping lives in `project_config.py` (PROCESSING_PROFILES / CLEANER_VERSIONS); only `podcast_transcript` and `anime_subtitle` have profiles, but `anime_subtitle` is not present in `Config\source_types.json` (only `podcast_transcript` is).
- The canonical corpus "single source of truth" contract (README Rule 5 / corpus_builder) is followed by the analyzer consumers.
- Handoff idempotency relies on sha256 comparison of existing artifacts (documented in code, not in a spec).

---

# 4. Runtime Data Separation

| Category | Locations | Notes |
|---|---|---|
| Application code | `app.py`, `Source Builder\*.py`, `Production Manager\*.py`, `Data Processor\*.py`, `Analysis\*.py`, `Source Intake\*.py`, `Subtitle Cleaner\*.py`, `Transcript Cleaner\*.py`, `Subtitle Importer\*.py`, `Common\*.py`, root `common.py`/`paths.py`/`project_config.py` | Code is separate from data. |
| Configuration | `Config\collections.json`, `Config\source_types.json`, `Config\origins.json` | Controlled vocabulary (clean: empty collections; source_types=[podcast_transcript]; origins=[user_transcription]). |
| User-created data | `Sources\` (collections/standalone) | Empty after reset. |
| Generated runtime artifacts | `Source Registry\`, `Cleaning Jobs\`, `Cleaning Results\`, `Cleaned Archive\`, `Processing Results\`, `Data Processor\` runtime subfolders (jobs/jsonl/requests/responses/processing/completed/failed/indexes/Corpus Results/Job Results/Request Results), `Analysis\outputs\` | Empty after reset. |
| Diagnostics | `Diagnostics\` | Empty. |
| Logs | `Logs\` (13 subfolders + README) | Only README present. |
| Tests | All `tests\` folders + dev scripts in package roots | Separate from runtime. |
| Developer tools | `project_audit.py`, `Data Processor\corpus_builder_test.py`, `response_validator_test.py`, `Source Builder\source_builder.py` (standalone), `Subtitle Importer\subtitle_importer.py` | Developer-only entry points. |

**Can user data be removed without affecting the application?**
Yes. Sources/Registry/Jobs/Results/outputs/Logs/Diagnostics are all empty or generated on demand (`mkdir(parents=True, exist_ok=True)`); no code path requires user data to exist at startup. Removing them returns to the current clean state.

**Can the application start from a clean install state?**
Yes. Verified earlier: the app launches with `config_error=None`, all three tabs open, empty collections load, dropdowns populate, save creates a valid package, import works. `verify_paths()` is not auto-invoked at import.

**Are any Japanese-specific / user-specific artifacts still embedded?**
- `Config\source_types.json` / `origins.json` are clean; `collections.json` is empty.
- **Stale user references remain in runtime files:** `Source Builder\gui_settings.json` holds `origin: "con_teppei_podcast"` (removed from Config) and `Source Builder\quick_presets.json` holds a preset referencing `teppei_beginner` / `con_teppei_podcast` (removed from Config). The code safely ignores out-of-vocabulary values, but the stale data is still on disk.
- **`api_key.txt` still exists** containing a real `sk-...` key (35 chars) — a release-critical secret.
- Project language is `ja` (project-level), stored in `project_config.py` (`DEFAULT_LANGUAGE`) and `controller.py` (`PROJECT_LANGUAGE`) — expected, not an artifact.

---

# 5. Testing Coverage Review

## Current regression count

- **722 tests passing across all proper suites** (Source Builder + shell 274, Data Processor 95, PM 77, Analysis 78, Source Intake 106, Subtitle Importer 16, Subtitle Cleaner 15, Transcript Cleaner 17, Common 26, Integration 10, Templates 8).
- Note: two suite runs show 5 failures that are **expected and documented** (metadata cleanup removed the live-Config test fixtures): `test_source_builder_quick_presets.py` (1) and `test_source_builder_gui_presets.py` (4) depend on removed `teppei_beginner`/`article`/`nhk_news`/`con_teppei_podcast` entries. The remaining 717 pass when those two are excluded; the failures are fixture-vs-config issues, not code defects.

## Well-tested areas
- Source Builder controller, ready-state engine, source package, handoff (module level), metadata editor, quick presets (pure), settings, import material, recent sources, GUI windows (load file, processing, analysis, presets, handoff, import), app shell.
- Source Intake artifact writers + schemas + resolver + source_id + hashing (106).
- Production Manager (state machine, API, docs, controls, launcher, pipeline, integration — 77).
- Data Processor stage logic (job builder, request builder, deepseek client, corpus builder, parser contract — 95) via synthetic fixtures.
- Analysis analyzer modules (9 suites, 78) via synthetic fixtures.
- Cleaners (transcript/subtitle), Subtitle Importer cleaner, Common utils, Integration boundary, Templates consistency.

## Weakly tested areas
- **Real data processing:** the automated suite does not run the real pipeline with real source files; stage execution is mocked (PM `pipeline` patched in `test_source_builder_processing_tab.py`). Real-data coverage lives only in dev scripts (`corpus_builder_test.py`, `response_validator_test.py`) that require external benchmark data (`C:\Users\Shawn\AppData\Local\Temp\opencode\parser_bench`).
- **Multiple source types:** only `podcast_transcript` is configured as a source type in the cleaned Config; `anime_subtitle` exists in the pipeline profiles but is not selectable in the GUI config. No test covers a full flow for a subtitle source through the GUI.
- **Analysis using real corpus data:** Analysis modules are tested with synthetic JSONL fixtures; there is no automated test that runs the full pipeline and then analyzes a real corpus output.
- **Fresh installation workflow:** no automated test covers "clean install → import material → save → process → analyze" as one unbroken flow (the app-shell test covers save→package, but not the full pipeline/analysis chain).
- **Cleaning result artifact through the cleaner:** cleaner unit tests exercise cleaning logic; the Cleaning Result artifact writing is tested at the Source Intake writer level but not through a full cleaner run.

## Untested workflows
- End-to-end pipeline execution against a live DeepSeek API (by design; API is not exercised in CI).
- Fresh-install import → process → analyze as a single integration flow.
- GUI-driven processing of a real subtitle source.

---

# 6. Configuration Review

| Config file | Current values | Classification |
|---|---|---|
| `Config\collections.json` | `[]` (empty) | Required default structure; no user data. |
| `Config\source_types.json` | `["podcast_transcript"]` | Required default (only pipeline-backed type). |
| `Config\origins.json` | `["user_transcription"]` | Generic default origin. |
| `project_config.py` | SOURCE_TYPES={anime_subtitle, podcast_transcript}; PROCESSING_PROFILES; CLEANER_VERSIONS; DEFAULT_LANGUAGE=ja; PROJECT_VERSION=1.0; API settings | Required defaults (language-specific: `ja`). |

- **Required defaults:** `podcast_transcript` source type; `user_transcription` origin; project language `ja`.
- **User-created values:** none in Config (all test collections/origins/source types were removed).
- **Language-specific values:** `DEFAULT_LANGUAGE = "ja"` (project_config) and `PROJECT_LANGUAGE = "ja"` (controller) — intentional project-level setting.
- **Development leftovers:**
  - `Config` is clean (no `.bak`).
  - Stale user references remain in **runtime files** `Source Builder\gui_settings.json` (`con_teppei_podcast`) and `Source Builder\quick_presets.json` (`teppei_beginner` preset) — leftover from dev, safe-but-stale.
  - `prompt` placeholder `Prompts\corpus_analysis_v1.txt` is 0 bytes.
  - `Daily Handoff\distribution of roles.txt` is 0 bytes.

---

# 7. Release Readiness Assessment

## READY (no work required)
- Core pipeline stage logic (clean/jobs/requests/api/corpus) implemented and unit-tested.
- Frozen contracts (parser output spec, parser prompt, source template, PM API, schemas).
- Application shell + Sources/Processing/Analysis surfaces implemented.
- Runtime data reset to a clean state; Config cleaned.
- Regression suite structure in place (722 total).

## BEFORE RELEASE (should be addressed)
- **API key handling:** `api_key.txt` contains a real secret; must be removed/rotated and loaded via a non-committed mechanism (env var) before any release or external review.
- **Stale runtime user data:** `Source Builder\gui_settings.json` and `Source Builder\quick_presets.json` reference removed vocab (`con_teppei_podcast`, `teppei_beginner`); should be reset to neutral defaults.
- **Live-Config test dependency:** 5 test failures from `test_source_builder_quick_presets.py` / `test_source_builder_gui_presets.py` depend on removed Config entries; fixtures need neutral/sandboxed Config (already flagged in the metadata cleanup).
- **Real-data end-to-end validation:** no automated test runs the full real pipeline (subprocess + real corpus) to a corpus and through analysis; needed before claiming production readiness.
- **Documentation drift:** PROJECT_STATUS.md / SESSION_BOOTSTRAP.md / README describe earlier milestones (parser prompt "not written", Corpus Builder "not started", GUI "future") that are now complete (documented in the Documentation Audit).
- **Stale/legacy files in tree:** `cleaner common.py`, `Data Processor\process_file.py`, dev-only `corpus_builder_test.py`/`response_validator_test.py` with hardcoded external paths, `Subtitle Importer` standalone GUI (not wired), and the frozen code duplicates under `Daily Handoff\V1_FREEZE...\Reference Files\`.

## FUTURE (improvements, not blockers)
- Add `anime_subtitle` to `Config\source_types.json` if subtitle sources are to be selectable in the GUI.
- Standalone `source_intake.py` coordinator integration into the GUI path (currently bypassed).
- Packaging / installer / launch scripts.
- Multi-language support (currently hardcoded `ja`).
- Test coverage for fresh-install-to-analysis and multiple source types.

---

# 8. Risk Register

| # | Risk | Impact | Likelihood | Recommendation (identify only) |
|---|---|---|---|---|
| 1 | **API key exposure** — `api_key.txt` contains a real `sk-` key in the tree. | High (credential leak, cost/fraud) | High (present now) | Remove/rotate; move to env var; exclude from any release. |
| 2 | **Hidden dependency on external benchmark data** — `corpus_builder_test.py`/`response_validator_test.py` hardcode `C:\Users\Shawn\AppData\Local\Temp\opencode\parser_bench`. | Medium (dev tests fail on another machine) | High | Do not rely on them for release validation. |
| 3 | **Live-Config test coupling** — presets/quick-presets tests read real `Config\`. | Medium (flaky across environments) | High | Fixtures should sandbox CONFIG_DIR. |
| 4 | **Documentation drift** — status/bootstrap/README describe outdated milestones. | Medium (misleading external review) | High | Refresh current-state docs before review. |
| 5 | **Legacy/duplicate code in tree** — `cleaner common.py`, `process_file.py`, frozen `.py` duplicates under V1_FREEZE, dev scripts. | Low (confusion, drift risk) | High | Separate/archive dev artifacts. |
| 6 | **Real pipeline not tested end-to-end** — API/subprocess path only mocked in automated tests. | High (production failure risk) | Medium | Add an integration test with a real (or stubbed network) corpus run. |
| 7 | **No packaging/launcher** — user launches via `python app.py`. | Medium (portability) | Medium | Add packaging/launch script before distribution. |
| 8 | **Portability** — absolute path assumptions (`C:\Jprogram`, temp benchmark path), Windows-specific `os.startfile`. | Medium (non-Windows / other paths) | Medium | Paths are centralized in `paths.py`, but hardcoded strings exist in dev scripts. |
| 9 | **Scaling** — Processing runs sources sequentially; single-threaded GUI; per-source subprocess launch. | Low-Medium (throughput) | Low | Acceptable for batch use; revisit for large corpora. |
| 10 | **Undocumented coupling** — Request Builder `user_content()` ↔ Corpus Builder `job_text_from_user_content`; Source Package schema outside shared `ARTIFACT_SCHEMAS`. | Medium (contract drift) | Low-Medium | Document contract boundaries. |

---

# 9. Executive Summary

**Current project state:** **Stable** — the pipeline, frozen contracts, and application surfaces are implemented and unit-tested (722 tests across all suites), and the runtime has been reset to a clean, app-launching state. It is stable for development and review purposes.

**Recommended next steps (before Qwen review):**
- Remove/rotate the real API key in `api_key.txt` and move loading to a non-committed mechanism.
- Reset `Source Builder\gui_settings.json` and `Source Builder\quick_presets.json` to neutral defaults (no removed vocab references).
- Sandbox the two live-Config test suites so the full regression is green (717→722).
- Resolve the 5 documented test failures tied to the metadata cleanup.
- Refresh the current-state documentation (README status lines, PROJECT_STATUS.md, JPROGRAM_SESSION_BOOTSTRAP.md) to match the completed application layer.
- Add an end-to-end real-data validation run (pipeline → corpus → analysis) before declaring production readiness.

No implementation was performed in this audit. STOPPED.
