# CURRENT_IMPLEMENTATION_MAP

**Project:** Japanese Corpus Pipeline (C:\Jprogram)
**Date:** 2026-08-04
**Type:** Read-only implementation snapshot — evidence gathered directly from the repository.

---

## 1. Repository Folder Tree

```
C:\Jprogram\
├── app.py                          # Application Shell (primary entry point)
├── common.py                       # shared utilities (project root)
├── paths.py                        # central path configuration
├── project_config.py               # shared configuration (source types, profiles, API)
├── project_audit.py                # developer audit tool
├── PROJECT_STATUS.md / README.md / JPROGRAM_SESSION_BOOTSTRAP.md
├── PARSER_OUTPUT_SPEC.md / SOURCE_TEMPLATE_SPEC.md / ARCHITECTURE_CURRENT.md
├── SOURCE_PACKAGE_HANDOFF.md / ANALYZER_ARCHITECTURE.md
├── api_key.txt                     # !! contains a real API key (release-critical)
├── cleaner common.py               # legacy duplicate of paths.py (not imported)
│
├── Analysis\                       # analyzer modules (read canonical corpus)
│   ├── corpus_loader.py, frequency_analyzer.py, distribution_analyzer.py,
│   │   exposure_analyzer.py, expression_analyzer.py, chunk_analyzer.py,
│   │   sentence_metrics.py, comparison_analyzer.py, output_writer.py
│   └── tests\ (9 suites)
│
├── Audits\2026-08-04\              # current audit set (baseline + handoff)
│   ├── Project_Audit.md, Documentation_Audit.md, Documentation_Reconciliation.md,
│   │   Final_Baseline_Audit.md, Parser_Normalizer_Archaeology.md,
│   │   Validator_Ownership_Audit.md, Canonicalization_Stage_Design_Audit.md,
│   │   Canonicalization_Implementation_Plan.md, REAL_WORLD_VALIDATION_ISSUES.md,
│   │   Session_Handoff_Audit.md
│
├── Cleaned Archive\                # <source_id>.clean.txt (runtime)
├── Cleaning Jobs\                  # <source_id>.cleaning_job.json (runtime)
├── Cleaning Results\               # <source_id>.cleaning_result.json (runtime)
├── Common\cleaning_utils.py        # shared cleaning utilities
├── Config\                         # controlled vocabulary
│   ├── collections.json (2 collections), source_types.json (2 types),
│   │   origins.json (2 origins)  (+ .bak files)
├── Daily Handoff\                  # continuity + dated handoffs
│   ├── PROJECT_CONTEXT.md
│   └── Handoff_2026-08-04\         # dated handoff package (this package)
├── Data Processor\                 # pipeline stage programs (runtime subfolders below)
│   ├── job builder.py, request builder.py, deepseek_client.py,
│   │   parser_normalizer.py, response_validator.py, corpus_builder.py
│   ├── *_result.py                 # per-stage result envelopes
│   ├── corpus_builder_test.py / response_validator_test.py  # dev scripts (external paths)
│   ├── process_file.py             # legacy (not imported)
│   ├── jobs\ requests\ responses\ jsonl\ processing\ completed\ failed\ indexes\
│   │   Job Results\ Request Results\ Corpus Results\    (runtime)
│   └── tests\ (6 suites)
├── Diagnostics\                    # *.json.gz diagnostic bundles (runtime)
├── Intake\                         # subtitle importer dev output (runtime)
├── Integration\tests\              # 1 boundary suite
├── Logs\                           # per-stage log subfolders
├── Processing Results\             # <source_id>.processing_result.json (runtime)
├── Production Manager\
│   ├── production_manager.py       # pipeline orchestrator (CLI + API)
│   ├── README.md / GUI_API.md / API_VERSION.md
│   └── tests\ (7 suites)
├── Prompts\
│   ├── parser_prompt.md            # frozen DeepSeek parser prompt
│   └── corpus_analysis_v1.txt      # 0-byte placeholder
├── Raw Subtitles\ / Raw Transcripts\   # (empty input folders)
├── Source Builder\                 # Sources UI + workflow + orchestration
│   ├── gui.py, source_builder.py, controller.py, source_package.py,
│   │   handoff.py, import_material.py, recent_sources.py, quick_presets.py,
│   │   gui_settings.py, config_loader.py, metadata_editor.py,
│   │   metadata_editor_gui.py, processing_tab.py, processing_tab_gui.py,
│   │   analysis_tab_gui.py, diagnostics.py
│   ├── gui_settings.json / quick_presets.json   # runtime user preferences (stale refs)
│   └── tests\ (20 suites)
├── Source Intake\                  # artifact writers + coordinator
│   ├── schemas.py, registry.py, cleaning_job.py, cleaning_result.py,
│   │   source_id.py, hashing.py, resolver.py, duplicate_check.py, source_intake.py
│   └── tests\ (12 suites)
├── Source Registry\                # <source_id>.json (runtime)
├── Sources\                        # user-created canonical sources
│   ├── collections\<id>\<id>_epNNNN.txt + .source.json
│   └── standalone\<name>.txt + .source.json
├── Subtitle Cleaner\clean_subtitles.py (+ tests)
├── Subtitle Importer\              # cleaner.py (reused), gui.py, subtitle_importer.py (legacy entry)
├── Templates\                      # transcript_template.txt, subtitle_template.txt (frozen)
├── Transcript Cleaner\clean_transcript.py (+ tests)
└── tests\test_app_shell.py         # app shell test
```

---

## 2. Major Modules / Files and Responsibilities

| Module | Responsibility |
|---|---|
| `app.py` | Application shell — 3 tabs (Sources / Processing / Analysis). Primary entry point. |
| `paths.py` | Central path configuration (all project folder constants). |
| `project_config.py` | Shared configuration: `SOURCE_TYPES`, `PROCESSING_PROFILES`, `CLEANER_VERSIONS`, `DEFAULT_LANGUAGE=ja`, API settings (`MODEL_NAME`, `API_THINKING_TYPE`, `API_MAX_TOKENS`). |
| `common.py` | Shared utilities (headers, logs, JSON writes, atomic writes). |
| `Source Builder\controller.py` | Source capture: validation, canonical filenames, atomic save, Ready State Engine. |
| `Source Builder\source_package.py` | Source Package sidecar (`.source.json`) build/write/validate. |
| `Source Builder\handoff.py` | Handoff → Registry entry + Cleaning Job (via Source Intake writers, idempotent by sha256). |
| `Source Builder\import_material.py` | Import Material format conversion (transcript/subtitle/ebook/ocr/plain text). |
| `Source Builder\processing_tab.py` | Processing orchestration: package discovery, status mapping, process/retry/analysis. |
| `Source Builder\processing_tab_gui.py` / `analysis_tab_gui.py` | Processing and Analysis windows. |
| `Source Builder\metadata_editor.py` / `config_loader.py` | Collection/source-type/origin editing and config loading. |
| `Source Builder\diagnostics.py` | Diagnostic bundle export (gzipped JSON). |
| `Production Manager\production_manager.py` | Pipeline orchestrator: `status/report/dry_run/run_stage/pipeline`; launches stage programs as subprocesses. |
| `Data Processor\job builder.py` | Clean text → job files. |
| `Data Processor\request builder.py` | Jobs → DeepSeek request files (prepends SOURCE METADATA block). |
| `Data Processor\deepseek_client.py` | DeepSeek API transport (non-thinking, json_object, max_tokens). |
| `Data Processor\parser_normalizer.py` | **Parser Output Canonicalizer** — restores clean-source sentence text, recomputes spans/chunk text, verifies reconstruction. Runs before validation. |
| `Data Processor\response_validator.py` | Deterministic validation gate on canonical records (punctuation-normalized partition check). |
| `Data Processor\corpus_builder.py` | Corpus Builder — canonicalize → validate → build; assigns global IDs, sections, provenance; writes JSONL. |
| `Analysis\*.py` | Analyzers: frequency, distribution, exposure, expression, chunk, sentence metrics, comparison, output writer. |
| `Source Intake\*.py` | Artifact schemas + writers (registry, cleaning_job, cleaning_result) + coordinator (`source_intake.py`, `duplicate_check.py` — not invoked by GUI path). |
| `Subtitle Cleaner\clean_subtitles.py`, `Transcript Cleaner\clean_transcript.py` | Cleaning content programs. |
| `Subtitle Importer\cleaner.py` | Subtitle file conversion (reused by Import Material for .srt/.vtt). |

---

## 3. Application Entry Points

| Entry point | Path | Type |
|---|---|---|
| `python app.py` | `C:\Jprogram\app.py` | Primary — Application Shell (3 tabs) |
| `python "Source Builder\source_builder.py"` | `C:\Jprogram\Source Builder\source_builder.py` | Secondary — standalone Source Builder |
| Production Manager CLI | `Production Manager\production_manager.py --source/--run/--pipeline/--dry-run` | CLI orchestrator |
| Stage scripts (CLI) | `Data Processor\*.py`, cleaners | Invoked by PM via subprocess |
| `python "Subtitle Importer\subtitle_importer.py"` | `C:\Jprogram\Subtitle Importer\subtitle_importer.py` | Developer-only / legacy standalone |

---

## 4. Current Pipeline Components

```
Clean Source
    → Parser (deepseek_client.py → DeepSeek API, deepseek-v4-flash)
    → Parser Output Canonicalizer (parser_normalizer.py)
    → Response Validator (response_validator.py)
    → Corpus Builder (corpus_builder.py)
    → Canonical JSONL (Data Processor\jsonl\<source_id>.jsonl)
    → Analysis (Analysis\*)
```

PM stage sequence: `clean → jobs → requests → api → corpus` (5 stages, artifact-resume based).
The Parser Output Canonicalizer runs **inside** corpus_builder's per-job flow
(before validation) — it is not a separate PM stage/subprocess.

---

## 5. Test Locations

Test command: `python <each test file>` (self-contained scripts with a
`TESTS` list + main runner). No pytest/unittest framework is used.

| Location | Suites | File count |
|---|---|---|
| `tests\` (root) | app shell | 1 |
| `Analysis\tests\` | 9 analyzer suites | 9 |
| `Common\tests\` | cleaning utils | 1 |
| `Data Processor\tests\` | corpus builder, deepseek client, job builder, parser contract, parser normalizer, request builder | 6 |
| `Integration\tests\` | intake/cleaner boundary | 1 |
| `Production Manager\tests\` | core, api, api docs, controls, integration, launcher, pipeline | 7 |
| `Source Builder\tests\` | controller, gui (10), handoff, import, metadata editor, processing tab, presets, ready state, recent, source package | 20 |
| `Source Intake\tests\` | cleaning job, cleaning result, duplicate check, hashing, paths, project config, registry, resolver, schemas, source id, source intake | 11 (+test_project_config) |
| `Subtitle Cleaner\tests\` | clean subtitles | 1 |
| `Subtitle Importer\tests\` | cleaner | 1 |
| `Templates\tests\` | source template consistency | 1 |
| `Transcript Cleaner\tests\` | clean transcript | 1 |

Dev-only (outside `tests\`, not part of the regression run):
`Data Processor\corpus_builder_test.py` and `response_validator_test.py`
(hardcode external benchmark path `C:\Users\Shawn\AppData\Local\Temp\opencode\parser_bench`).

---

*End of current implementation map.* STOPPED.
