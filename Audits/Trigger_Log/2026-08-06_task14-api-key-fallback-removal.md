# Trigger Log — 2026-08-06 — TASK 14: Remove api_key.txt fallback + fix processing-tab closure bug

**Work done:** OC's TASK 14 — removed the legacy `api_key.txt` file-fallback
from `Data Processor/deepseek_client.py` (Frozen Component, Transport)
now that `DEEPSEEK_API_KEY` is the one live key-storage mechanism, and
fixed a real closure-capture bug in `Source Builder/processing_tab_gui.py`
found via `ruff` (F821 undefined name) where a deferred Tkinter callback
referenced an exception variable Python had already deleted.

**Audit trigger: Yes — confidence: N/A (automatic).**
`Data Processor/deepseek_client.py` is a Frozen Component per `CLAUDE.md`.

**Disclosure (mandatory every time this trigger fires, per `CLAUDE.md`'s
current Auditor model):** no cross-vendor auditor was used — Claude Code
only. The audit ran as a genuinely fresh subagent with no memory of
Advisor's own evaluation, working directly on the real uncommitted files
(first attempt used filesystem-worktree isolation, which checked out a
stale pre-change copy and was caught and re-run correctly before any
audit conclusion was drawn).

**Verification summary:** raw `git diff`/`git status` confirmed exactly
the 5 named files touched; both test suites independently re-run by
Advisor (26/26, 8/8) and again independently by the fresh subagent
(same counts) — matched exactly both times. Repo-wide grep for the
removed symbols (`API_KEY`, `load_api_key`, `_resolve_api_key`) confirmed
no live code outside the 5 files references them.

**Verdict: CLEAN WITH NOTES — one real bug found, not yet fixed.** OC
itself found and correctly flagged the issue rather than silently
missing it or overstepping its stated boundary: `deepseek_client.py`'s
`run()` still catches `except (FileNotFoundError, ValueError)` around
the key-resolution call, but the simplified `_resolve_api_key()` now
raises `EnvironmentError` (an `OSError`, not a subclass of either caught
type) when the env var is unset. Confirmed independently by both Advisor
(direct repro) and the fresh subagent (live repro against `dsc.run()`):
an unset `DEEPSEEK_API_KEY` crashes `run()` with an unhandled traceback
instead of returning its intended clean failure result. No current test
exercises `run()` with the env var unset, so this gap is real and
untested. **Root cause: Advisor's own Coder-command boundary** ("no
other function in this file changes") was scoped too narrowly for a
change that necessarily affects a caller's exception handling — not an
OC error. Follow-up Coder command drafted to fix `run()`'s except
clause, refresh its now-stale docstring, and add the missing test
coverage.

---

**Follow-up (2026-08-06, same day, continued OC session per the red-box
exception for a tight immediate fix on the same work):** the flagged bug
is fixed. `run()`'s except clause changed from
`except (FileNotFoundError, ValueError)` to `except EnvironmentError`,
matching exactly what `_resolve_api_key()` can raise; docstring refreshed;
new test 15b (`run fails cleanly when env var unset`) added, calling
`run()` itself with the env var unset and confirming a clean `fail()`
return (code 1, failure result written, zero requests processed) with no
unhandled exception. Independently verified: `git diff` read directly,
matches OC's report exactly; 27/27 tests re-run myself, matched; OC again
proved the new test catches the regression by reverting the fix,
confirming failure, and restoring it.

**Audit trigger: Yes (automatic, unchanged) — but the second
fresh-subagent audit pass was deliberately skipped, Owner-confirmed
judgment call, not silently bypassed.** Reasoning: this fix implements
exactly what the prior fresh-subagent audit (this same file, same day)
already independently found and fully specified — not new, unreviewed
Frozen Component logic. Advisor's own direct diff review and independent
test re-run stand in for the second audit pass here. This is a narrow,
one-time exception tied to this specific fix being a direct
implementation of an already-completed audit's own findings — it does
not loosen the automatic-Yes rule for any other change, including
unrelated future changes to this same file.

**Verdict: CLEAN.** Both the API-key-fallback removal and its follow-up
fix are complete, independently verified, and correctly scoped.
