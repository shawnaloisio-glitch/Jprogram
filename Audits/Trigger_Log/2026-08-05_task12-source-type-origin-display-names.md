# Trigger Log — 2026-08-05 — TASK 12: Source type / Origin display names

**Backfilled 2026-08-06** — this entry was missed at the time; written
retroactively from `Audits/OC_Reliability_Log.md`'s existing TASK 12
record and raw verification, not from memory.

**Work done:** OC's TASK 12 — main-form Source type/Origin dropdowns now
show friendly `display_name` labels while `source_type_var`/`origin_var`
continue holding raw ids byte-identical to before (a dozen downstream
save/preset/settings sites depend on this). Mid-task, OC self-diagnosed
and fixed a genuinely subtle stale-closure bug (label maps captured by
reference, would go stale on a metadata reload) unprompted, adding a
dedicated regression test. Files: `gui.py`, `config_loader.py`, 3 test
files. Full detail in `Audits/OC_Reliability_Log.md`'s TASK 12 entry.

**Audit trigger: No — confidence: High, reason:** touches only the 5
in-scope Source Builder files — none are Frozen Components per
`CLAUDE.md`. The self-caught stale-closure bug was fixed and covered by
a new test before this evaluation, so it isn't residual risk.

**Verification summary:** raw OC transcript pulled via `--since` (task
ran in a session reused across TASK 10/11/12); full `git diff` for
`gui.py`/`config_loader.py` read directly to confirm the id/label
invariant in code; independently re-ran `test_config_loader.py` (12/12),
`test_source_builder_gui_label_combos.py` (9/9), and
`test_source_builder_gui_metadata_editor.py` (25/25) — all matched. The
anti-corruption guard test (saved source persists raw ids, never
labels) passes.

**Verdict: CLEAN WITH NOTES.** One cosmetic-only finding: two dead
methods left in `gui.py` (`_on_source_type_selected`/
`_on_origin_selected`), unflagged by OC, no functional impact — queued
into the next task that touches `gui.py`, not a standalone fix. See
`Audits/OC_Reliability_Log.md` TASK 12 for full detail.
