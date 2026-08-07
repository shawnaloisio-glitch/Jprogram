# Trigger Log — 2026-08-06 — TASK 18: Source type collapse, GUI layer (Command 3 of 3, final)

**Work done:** OC's TASK 18 — removed the now-redundant user-facing
source_type choice. Both the main-form and preset-editor "Source type:"
comboboxes converted to static, non-interactive labels (`source_type_var`
still set from the real Config vocabulary, never hardcoded, so downstream
save logic is untouched). `SOURCE_TYPE_LABELS` collapsed to the one real
entry. The Metadata Editor's "Source Types" tab removed entirely
(`_build_source_types_tab()` and its notebook registration) — Collections
and Origins tabs untouched, and `metadata_editor.py`'s data-layer
functions (`add_source_type`, etc.) deliberately left alone, only their
GUI exposure removed. `paths.py`'s `SUBTITLE_CLEANER` constant and its
`verify_paths()` entry removed (same shape as TASK 15's
RAW_SUBTITLES/RAW_TRANSCRIPTS cleanup), fixing the one test that had been
failing since Command 1. Repo-wide grep found and fixed 4 test files
whose assertions still expected dropdown interactivity or the removed
tab. Self-caught and removed a newly-dead `source_type_id_map` (only
served the removed dropdown's reverse lookup) after running `ruff` on
its own changes proactively.

**Audit trigger: No — confidence: High, reason:** none of the touched
files (`gui.py`, `metadata_editor_gui.py`, `paths.py`, 4 test files) are
Frozen Components.

**Verification summary:** all four core diffs (`gui.py`,
`metadata_editor_gui.py`, `paths.py`, `test_paths.py`) read directly,
matched OC's report exactly — including confirming the `RAW_SUBTITLES`/
`RAW_TRANSCRIPTS` lines in the `paths.py` diff were TASK 15's earlier
stacked work, not new from this task. Full test suite independently
re-run with a 100s per-file timeout: **63/63 pass, 0 failures, 0
timeouts** — exact match to OC's own final signal.

**Verdict: CLEAN.** This closes the 3-command source_type collapse
project end to end: config/backend (TASK 16) → every downstream
reference and test fixture (TASK 17) → the user-facing UI itself (TASK
18). All three independently verified clean; the one real cross-command
bug (the stale `except` clause from the earlier API-key task, unrelated
to this project) was already caught and fixed separately. Full suite is
green.
