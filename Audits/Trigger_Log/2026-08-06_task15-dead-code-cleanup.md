# Trigger Log — 2026-08-06 — TASK 15: Dead-code cleanup (production_manager.py, paths.py, test_job_builder.py); gui.py part blocked

**Work done:** OC's TASK 15 — three unrelated dead-code cleanups, none
touching Frozen Components. Part 1: removed an unreachable duplicate
`elif` branch in `production_manager.py`'s `state_for()`. Part 3:
removed the orphaned `RAW_SUBTITLES`/`RAW_TRANSCRIPTS` path constants
from `paths.py` (confirmed dead — leftover from a retired folder-scan
acquisition design). Part 4: removed the now-impossible "no Raw folder
write" boundary check from `test_job_builder.py` that Part 3 would have
broken. **Part 2 (removing two dead methods from `gui.py`) was correctly
BLOCKED** — OC's own repo-wide grep (required by the command) found the
methods are directly called from
`Source Builder/tests/test_source_builder_gui_label_combos.py`, a file
outside the task's boundary. OC did not remove them and did not touch
the out-of-boundary test file; it reported the contradiction and asked
how to proceed rather than guessing.

**Audit trigger: No — confidence: High, reason:** none of the three
files actually modified (`production_manager.py`, `paths.py`,
`test_job_builder.py`) are Frozen Components. `gui.py` was not modified.

**Verification summary:** all three touched-file diffs read directly
and matched OC's report exactly. All three affected test suites
independently re-run and matched claimed counts exactly:
`test_job_builder.py` 18/18, `test_production_manager.py` 15/15,
`test_source_builder_gui_label_combos.py` 9/9 (this last one confirms
Part 2 being blocked didn't break anything — the test still exercises
the dead methods successfully since they weren't removed).

**Part 2 follow-up investigated by Advisor, not OC:** read
`_wire_label_combo` and both "dead" methods directly. Finding: the
concern is smaller than it first appeared — both the live
`<<ComboboxSelected>>` binding and the two unbound methods ultimately
call the same static helper, `_apply_label_to_id()`. The test calling
the dead methods directly isn't exercising divergent/stale logic, it's
exercising the real shared translation logic through an unused entry
point. The only genuinely untested seam is whether the live event
binding itself correctly triggers that logic — low risk, matches TASK
12's original "harmless dead methods, no functional impact" finding.

**Verdict: CLEAN.** Owner decision (2026-08-06): not worth a follow-up
command for Part 2 given the low risk and the deterministic-parser
work ahead — left exactly as already queued on `WORKING_LIST.md`
("next task that touches `gui.py`"), not escalated to its own task.
