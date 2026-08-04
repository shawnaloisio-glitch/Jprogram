# Real-World Validation Issue Register

**Project:** Japanese Corpus Pipeline (C:\Jprogram)
**Date:** 2026-08-04
**Type:** Planning artifact only — no fixes, no redesign, no code changes.

This register documents issues observed during real-world validation and
real-data testing. Each issue is classified, described (observed vs expected),
and given a priority, dependencies, and a recommended investigation order.

**Priority scale:** P0 (blocks real-data use / data loss) · P1 (high, frequent
or serious) · P2 (medium, workaround exists) · P3 (low / future).

---

## 1. Import Filesystem

- **Classification:** UX issue / Architecture issue
- **Observed behavior:** Import Material opens a file dialog and converts a
  single selection of files (via `import_material.convert_files`), but there is
  no folder-based bulk import, no recursive discovery of a project folder, and
  no notion of "import everything under this directory into its collection".
  File inputs are passed one dialog selection at a time.
- **Expected behavior:** A user can point at a folder tree (e.g. a raw
  collection folder) and have its files discovered, classified by format
  (transcript / subtitle / plain text), and converted into canonical sources —
  or at minimum get clear feedback that bulk/folder import is not supported.
- **Affected modules:** `Source Builder\import_material.py`,
  `Source Builder\gui.py` (`_import_material`/`_do_import`).
- **Priority:** P1
- **Dependencies:** Item 2 (folder hierarchy) — import should map files into
  collection folders; Item 10 (subtitle workflow) for subtitle routing.
- **Recommended investigation order:** after Items 2 and 10, before Item 3.

---

## 2. Collection Folder Hierarchy

- **Classification:** Architecture issue / Metadata issue
- **Observed behavior:** Canonical sources live at
  `Sources\collections\<collection_id>\<collection_id>_epNNNN.txt`, and
  standalone at `Sources\standalone\<source_name>.txt`
  (`controller.collection_dir` / `source_path`, `generate_filename` uses a
  single 4-digit episode field). Real data showed `ci_transcript_ep0001`…
  `ep0005` created by hand/save. There is no season, volume, or
  multi-level grouping, and collection_id is the only folder dimension.
- **Expected behavior:** The folder hierarchy should model the real data
  structure (collection → optional season/volume → episode) so large real
  corpora do not collapse into flat `epNNNN` filenames that collide or mislead.
- **Affected modules:** `Source Builder\controller.py` (path/filename
  generation), `source_package.py` (canonical_path), `processing_tab.py`
  (discovery via `rglob`).
- **Priority:** P2
- **Dependencies:** Item 1 (import must produce the hierarchy); Item 3
  (non-episode content must fit the model).
- **Recommended investigation order:** after Item 1, before Item 3.

---

## 3. Non-Episode Content Model

- **Classification:** Architecture issue / Future capability
- **Observed behavior:** Collection-mode identity always requires an episode
  number (`episode: 04d` filename; `validate_collection_fields` requires a
  non-negative integer). Real content that is not episode-based (single
  articles, essays, one-off videos, chapters without numbers) must either
  become a standalone source or be forced into an arbitrary episode number.
- **Expected behavior:** A way to represent non-episode content within a
  collection (e.g. a content key/date/chapter field) without inventing episode
  numbers, or an explicit documented decision that such content is
  standalone-only.
- **Affected modules:** `Source Builder\controller.py` (validation/filenames),
  `source_package.py`, `processing_tab.human_label`.
- **Priority:** P2
- **Dependencies:** Item 2 (hierarchy) and Item 8 (source-type sync).
- **Recommended investigation order:** after Item 2.

---

## 4. Processing Cancel

- **Classification:** UX issue / Architecture issue
- **Observed behavior:** `ProcessingTabWindow._run_sources` starts a daemon
  worker thread that runs `processing_tab.process_sources` (sequential PM
  pipeline) with no cancel/stop/abort control. Closing the window
  (`self.window.destroy`) or clicking buttons is guarded by `_busy`, but there
  is no way to cancel an in-flight multi-source run; the worker keeps running
  until it finishes (only `Close` destroys the window; the daemon thread cannot
  be stopped).
- **Expected behavior:** A "Cancel" action that stops the current sequential
  run (stop launching further stages/sources and report partial results)
  without corrupting artifacts, and clear busy-state UX.
- **Affected modules:** `Source Builder\processing_tab_gui.py`,
  `Source Builder\processing_tab.py` (`process_sources`), `Production
  Manager\production_manager.py` (`pipeline`, `launch_stage`).
- **Priority:** P1
- **Dependencies:** none; but a cancel design must respect PM's artifact-only
  resume behavior (PM README recovery workflow).
- **Recommended investigation order:** high — independently valuable for
  real-data use.

---

## 5. Duplicate Analysis Workflow

- **Classification:** UX issue / Bug (minor)
- **Observed behavior:** `processing_tab.run_analysis` writes
  `Analysis\outputs\<source_id>.frequency.json` unconditionally
  (`output_path.open("w")`) — re-running analysis for the same source
  overwrites the prior report with no duplicate/overwrite confirmation and no
  indication that a report already exists. Analysis can also be triggered from
  both the Processing window and the Analysis window for the same source,
  producing the same overwrite without coordination.
- **Expected behavior:** Either a "report already exists — overwrite?" prompt,
  timestamped output files, or an explicit idempotent "refresh analysis"
  behavior with clear feedback; and consistent triggering from both surfaces.
- **Affected modules:** `Source Builder\processing_tab.py` (`run_analysis`),
  `Source Builder\processing_tab_gui.py`, `Source Builder\analysis_tab_gui.py`.
- **Priority:** P2
- **Dependencies:** none.
- **Recommended investigation order:** medium.

---

## 6. Embedded Tab Workflow

- **Classification:** Architecture issue / UX issue
- **Observed behavior:** `app.py` embeds `SourceBuilderApp` directly inside the
  Sources tab (line 81), while Processing and Analysis are *separate Toplevel
  windows* opened from summary tabs (lines 119–127). The Sources tab has its
  own administrative "Processing" button, and the Processing/Analysis windows
  are transient children. There is no single consistent navigation model (tab
  vs window), and the embedded Source Builder reuses the shell root's style
  (background tint applied globally).
- **Expected behavior:** A consistent navigation model — either Processing and
  Analysis also become embedded tabs, or the Sources tab's "Processing" button
  is reconciled with the Processing tab — so users do not have two different
  ways to reach the same workflow.
- **Affected modules:** `app.py`, `Source Builder\gui.py` (`_open_processing`),
  `Source Builder\processing_tab_gui.py`, `Source Builder\analysis_tab_gui.py`.
- **Priority:** P2
- **Dependencies:** Item 4 (cancel) and Item 5 (duplicate analysis) both touch
  the windows that would be reorganized.
- **Recommended investigation order:** after Items 4 and 5.

---

## 7. Teppei Metadata Dependency Audit

- **Classification:** Metadata issue
- **Observed behavior:** `Source Builder\gui_settings.json` still holds
  `origin: "con_teppei_podcast"` (an origin removed from `Config\origins.json`)
  and `Source Builder\quick_presets.json` previously referenced
  `teppei_beginner`/`con_teppei_podcast`; the current preset references
  `cijapanese` with `source_type: podcast_transcript` while that collection's
  default source type is `cij_transcript`. Out-of-vocabulary values are
  silently ignored by `_restore_persisted_metadata` / `preset_population`, so
  stale metadata lingers without surfacing. The name "Teppei" appears in
  comments and the earlier dev dataset only; no live Config value depends on it
  now, but the runtime files are not clean.
- **Expected behavior:** Runtime metadata files contain only valid, current
  vocabulary; stale references are either cleaned or visibly surfaced, and a
  preset's stored source_type should reconcile with the collection's declared
  default (see Item 8).
- **Affected modules:** `Source Builder\gui_settings.py`,
  `Source Builder\quick_presets.py`, `Source Builder\gui.py`
  (`_restore_persisted_metadata`, `_on_preset_click`), `Config\*.json`.
- **Priority:** P1
- **Dependencies:** Item 8 (collection/source-type sync).
- **Recommended investigation order:** high — cheap, prevents stale-data
  confusion during real use.

---

## 8. Collection / Source Type Synchronization

- **Classification:** Metadata issue / Architecture issue
- **Observed behavior:** `metadata_editor.validate_collection` checks that a
  collection's `default_source_type` is a *known source type* (in
  `source_types.json`) but does **not** require that it be a *processable*
  source type (has a `PROCESSING_PROFILE`). Real data created collections with
  `source_type: cij_transcript`, which has **no processing profile**
  (`cleaning_profile_for("cij_transcript")` → None), producing the documented
  real-data failure (handoff rejected). The GUI's processable-only dropdown
  filter (from the earlier fix) prevents *new* unprocessable selections, but an
  existing collection/preset can still carry an unprocessable default, and the
  metadata editor itself does not warn.
- **Expected behavior:** A collection's default source type should be validated
  as processable (or clearly flagged as not-yet-processable) at edit/save time,
  and collection → default source type should stay in sync with the processable
  vocabulary and with presets that reference the collection.
- **Affected modules:** `Source Builder\metadata_editor.py`
  (`validate_collection`, `add_collection`, `delete_source_type`),
  `Source Builder\config_loader.py` (`default_source_type_for_collection`),
  `Source Builder\quick_presets.py`, `Config\source_types.json`.
- **Priority:** P0
- **Dependencies:** none upstream; blocks real-data collection creation that
  should be processable.
- **Recommended investigation order:** first — this is the direct cause of the
  real-data processing failure.

---

## 9. Template Editor Validation Limitations

- **Classification:** UX issue / Future capability
- **Observed behavior:** The preset editor (`gui._save_preset_from_editor`)
  validates slot/identity and relies on `quick_presets.save_slot`
  (`_normalize_preset`), and `metadata_editor.validate_*` checks ids/display
  names/uniqueness and preset/reference collisions on delete. But it does not
  validate that a preset's `source_type` is processable, nor cross-validate a
  collection preset's source_type against the collection's declared default.
  The source template files themselves (`Templates\*.txt`) are validated only
  by the frozen `SOURCE_TEMPLATE_SPEC` consistency test
  (`Templates\tests\test_source_template.py`), not by the editor.
- **Expected behavior:** Template/preset edits surface validation feedback for
  processability and collection-default consistency, and template file edits
  are validated against the frozen spec before use.
- **Affected modules:** `Source Builder\gui.py` (preset editor),
  `Source Builder\quick_presets.py`, `Source Builder\metadata_editor.py`,
  `Templates\tests\test_source_template.py`.
- **Priority:** P2
- **Dependencies:** Item 8 (processable-source-type validation is the same
  rule the editor should reuse).
- **Recommended investigation order:** after Item 8.

---

## 10. Subtitle Import Workflow

- **Classification:** Architecture issue / Future capability
- **Observed behavior:** Import Material handles subtitle files by reusing the
  Subtitle Importer cleaner (`import_material.convert_file` → `cleaner.clean_file`
  for .srt/.vtt), converting them to dialogue text lines. Separately, there is a
  standalone `Subtitle Importer\gui.py` / `subtitle_importer.py` entry point that
  writes clean text to `Intake\<stem>.txt` — a *different* destination than the
  Source Builder's canonical `Sources\` store. Two overlapping subtitle
  workflows exist with different outputs and no unified routing or
  collection/source-type mapping for subtitles (the pipeline's subtitle profile
  is `anime_subtitle`/`subtitle_standard_v1`, which is not exposed in the
  cleaned Config source types).
- **Expected behavior:** A single subtitle path: subtitles imported through the
  app are converted, routed to a canonical source (with the correct processable
  source type / cleaning profile), and the standalone Subtitle Importer either
  becomes that path or is retired/documented as dev-only.
- **Affected modules:** `Source Builder\import_material.py`,
  `Subtitle Importer\cleaner.py`, `Subtitle Importer\gui.py`,
  `Subtitle Importer\subtitle_importer.py`, `Config\source_types.json`,
  `project_config.py` (PROCESSING_PROFILES: anime_subtitle).
- **Priority:** P1
- **Dependencies:** Item 1 (import filesystem), Item 8 (source-type sync).
- **Recommended investigation order:** after Items 1 and 8.

---

## Summary Table

| # | Issue | Classification | Priority |
|---|---|---|---|
| 1 | Import filesystem | UX / Architecture | P1 |
| 2 | Collection folder hierarchy | Architecture / Metadata | P2 |
| 3 | Non-episode content model | Architecture / Future | P2 |
| 4 | Processing cancel | UX / Architecture | P1 |
| 5 | Duplicate analysis workflow | UX / Bug (minor) | P2 |
| 6 | Embedded tab workflow | Architecture / UX | P2 |
| 7 | Teppei metadata dependency audit | Metadata | P1 |
| 8 | Collection/source type synchronization | Metadata / Architecture | **P0** |
| 9 | Template editor validation limitations | UX / Future | P2 |
| 10 | Subtitle import workflow | Architecture / Future | P1 |

## Recommended Investigation Order

1. **Item 8** — P0, direct cause of the real-data processing failure.
2. **Item 7** — cheap cleanup of stale runtime metadata, feeds Item 8.
3. **Item 4** — cancel control for real multi-source runs.
4. **Item 10** — subtitle routing (depends on Item 8's source-type rule).
5. **Item 1** — import filesystem (depends on Items 8/10).
6. **Item 2** — collection hierarchy (depends on Item 1).
7. **Item 3** — non-episode content (depends on Item 2).
8. **Item 5** — duplicate analysis (independent).
9. **Item 6** — embedded tab workflow (depends on 4/5).
10. **Item 9** — template editor validation (depends on Item 8).

---

*End of real-world validation issue register.* STOPPED.
