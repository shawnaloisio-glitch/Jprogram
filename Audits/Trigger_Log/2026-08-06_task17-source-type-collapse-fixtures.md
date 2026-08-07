# Trigger Log — 2026-08-06 — TASK 17: Source type collapse, downstream references (Command 2 of 3)

**Work done:** OC's TASK 17 — fixed every downstream reference Command 1
deliberately left broken. Two real production-code fixes: `source_intake.py`'s
`_EXTENSIONS_BY_TYPE` (was about to `KeyError` on any `clean_text` source)
and `production_manager.py`'s dead `clean_subtitles` cleaner-path mapping
(matching the TASK 15 precedent for removing a dead branch). One test file
(`Integration/tests/test_intake_cleaner_boundary.py`) had its broken
`clean_subtitles` import removed and its subtitle-specific tests
converted/removed. Then a repo-wide fixture rename: 37 test files plus
2 templates, the template test, and the QC harness, all renamed
`podcast_transcript`/`anime_subtitle` → `clean_text` as fixture data.
Diagnosed and fixed a real hang in
`test_source_builder_gui_metadata_editor.py` (a `wait_window` blocked
forever because a "Default Source Type" combo came up empty once
`podcast_transcript` stopped being processable — fixed by the same
rename, confirmed root-caused, not papered over).

**Audit trigger: No — confidence: High, reason:** none of the touched
files (`source_intake.py`, `production_manager.py`, all test/template
files) are Frozen Components.

**Verification summary:** both production-code diffs read directly,
matched exactly (including confirming the `os`/`SUBTITLE_CLEANER` import
removals and the `state_for` dead-branch line were TASK 15's pre-existing
uncommitted changes, not new from this task). `gui.py` confirmed
untouched — the one remaining `podcast_transcript` reference there
(`SOURCE_TYPE_LABELS`) was correctly left for the next command. Full test
suite independently re-run with a 90s per-file timeout: **62/63 pass,
0 timeouts** — exact match to OC's own reported result. The one failure
(`test_paths.py`) independently confirmed to be a genuine Command 1
consequence (`paths.py`'s `verify_paths()` still requires the deleted
`Subtitle Cleaner` directory), not something this task introduced.

**Advisor process note, for the record:** my first two verification
passes (15s and 30s per-file timeouts) both incorrectly flagged
`test_source_builder_gui_metadata_editor.py` as still hanging. Direct
investigation showed it isn't hung — it's genuinely slow (many real
Tkinter dialog-opening tests), completing cleanly in under 60s. The
timeout was too tight, not OC's fix wrong. Corrected before drawing a
conclusion, not after.

**Verdict: CLEAN.** Command 2 of 3 complete, independently verified, one
correctly-attributed pre-existing failure carried forward (not this
task's to fix — its own boundary explicitly excluded `paths.py`).
