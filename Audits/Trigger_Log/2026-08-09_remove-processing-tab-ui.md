# Trigger Log — 2026-08-09 — Remove Processing tab/button from the UI

**Work done:** closed out the `WORKING_LIST.md` "Processing/Analysis
sub-window embedding" item's follow-up question — Owner decided to remove
UI access to the Processing window entirely (both `app.py`'s top-level
tab and Source Builder's admin-actions button) rather than either redesign
it or leave it in place, since its original batching-around-API-cost
rationale no longer applies with the deterministic local parser. The
underlying capability (`_open_processing()` in both files,
`processing_tab.py`/`processing_tab_gui.py`) was deliberately kept intact,
not deleted, per Owner's explicit "not removed in case ever wanted again."

Built via the headless DeepSeek-Coder mechanism in an isolated worktree
(`remove-processing-tab-ui`), `--allowedTools Read,Edit,Bash`. Merged to
`master` as `1c2f03f`, plus a small direct follow-up doc fix (`3347cbb`,
a stale class docstring Coder flagged but correctly left untouched as
outside its specified scope).

**Audit trigger: No — confidence: High, reason:** neither `app.py` nor
`Source Builder/gui.py` is a Frozen Component. Confidence is High rather
than Moderate because of the verification depth: this wasn't just a diff
review, it included a real runtime check (see below), and the change is
inherently low-risk — pure UI-construction removal with the actual
capability provably still intact and callable.

**Verification summary (Advisor's own, not accepted on Coder's
self-report):**
- Read both diffs directly: exactly the specified elements removed
  (`TAB_PROCESSING` constant, `_build_processing_tab()` call and method
  definition, the `processing_button` widget block), exactly the
  specified elements retained (`_open_processing()` in both files,
  `_center_child_over_parent()`, the `import processing_tab_gui`),
  matching the task spec precisely.
- Independently re-ran `tests/test_app_shell.py`: 7/7, including "open
  processing instantiates the existing processing window" (which calls
  `_open_processing()` directly, bypassing the removed UI) still passing
  unchanged.
- Full repo test sweep after applying to the real repo: 59/59 test files
  clean.
- **Real runtime verification, not just diff trust:** instantiated the
  actual `ApplicationShell` class with a real (withdrawn) Tk root and
  inspected the live object — `shell.notebook.tabs()` returns only
  `['Sources']`; `hasattr(source_builder, 'processing_button')` is
  `False`; `hasattr(shell, '_open_processing')` and
  `hasattr(source_builder, '_open_processing')` are both `True`. This
  confirms the actual constructed UI, not just the source code, behaves
  as specified.
- Coder proactively found and correctly reported (without touching, since
  it was outside the task's specified file list) two additional relevant
  test files exercising the retained capability directly
  (`Source Builder/tests/test_source_builder_gui_processing.py` 8/8,
  `test_source_builder_processing_tab.py` 16/16) and one stale docstring
  (fixed separately by Advisor, `3347cbb`).

**Verdict: CLEAN.** Merged to `master` (`1c2f03f`, `3347cbb`), worktree
and branch removed.
