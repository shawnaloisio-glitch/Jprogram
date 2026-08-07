# Trigger Log — 2026-08-06 — TASK 16: Collapse source_type to clean_text (config/backend layer, Command 1 of 3)

**Work done:** OC's TASK 16 — collapsed `source_type` to a single
`"clean_text"` value at the config/backend layer. Renamed
`Config/source_types.json`'s entry; collapsed `project_config.py`'s
`SOURCE_TYPES`, `CLEANING_PROFILES`, `PROCESSING_PROFILES`,
`CLEANER_VERSIONS`, `SOURCE_TYPE_RAW_DIR`, and `CLEANING_TRANSFORMS` to
drop `anime_subtitle`/`subtitle_standard_v1` and rename
`podcast_transcript` → `clean_text`; deleted the now-genuinely-dead
`Subtitle Cleaner/` directory (confirmed superseded by the separate,
independent `Subtitle Importer/cleaner.py`, which never called it);
updated the two Source Intake test files most tightly coupled to this
config. This is Command 1 of a deliberately sequenced 3-command project
(config/backend → repo-wide test-fixture rename → GUI layer) — the
resulting test breakage across the rest of the suite is expected, not a
defect in this task.

**Audit trigger: No — confidence: High, reason:** none of the 4 touched
files (`Config/source_types.json`, `project_config.py`,
`test_project_config.py`, `test_resolver.py`) plus the deleted
`Subtitle Cleaner/` directory are Frozen Components per `CLAUDE.md`.

**Verification summary:** `project_config.py`/`source_types.json` diffs
read directly, matched OC's report exactly. `test_project_config.py`
23/23 and `test_resolver.py` 14/14 independently re-run, matched. OC
correctly expanded Part 2/4 to two additional real-config-dependent
spots in the *same* files (`SOURCE_TYPES`/`CLEANING_PROFILES`
frozensets; 3 more tests in `test_project_config.py`) rather than
leaving them stale — disclosed explicitly, not silent scope creep, and
confirmed via diff to be exactly what was needed. Did not touch anything
outside its 5-item boundary despite finding and explicitly listing a
long tail of real breakage elsewhere.

**Full-suite check (Advisor, beyond what OC was asked to verify):** ran
every `test_*.py` with a per-file timeout. Result: 40 pass, 22 fail, 1
timeout (`test_source_builder_gui_metadata_editor.py` hangs rather than
failing cleanly — flagged distinctly for whoever picks up the GUI
command, since a hang can indicate something worse than a clean
assertion failure). All 22 failures are consistent with OC's own
findings list (stale `podcast_transcript`/`anime_subtitle` fixture data,
imports of the deleted `clean_subtitles` module) — expected mid-sequence
state, not new information.

**Verdict: CLEAN.** Scoped correctly, verified correctly, and the
resulting breakage is fully accounted for by OC's own disclosed
findings — nothing surprised this check.
