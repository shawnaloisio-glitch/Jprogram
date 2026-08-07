# Trigger Log — 2026-08-06 — TASK 20: Move origins to the workspace (like collections)

**Work done:** OC's TASK 20 — `origin` no longer drives any pipeline
routing (confirmed earlier this session: absent from Source Intake's
resolver/schemas and every Data Processor stage), so it moved to live
in the workspace exactly like `collections` — no shipped defaults, no
seeding, empty until the user adds their first entry. Added
`paths.ORIGINS_CONFIG`; gave `metadata_editor.py` and `config_loader.py`
the same origins-special-case path resolution collections already has;
fixed `config_loader.py`'s missing-file behavior specifically for
origins (was raising `ConfigError`, now returns `[]`, matching
`metadata_editor.py`'s already-correct behavior); deleted the shipped
`Config/origins.json` entirely, which removed a real personal entry
(`cijsub`/"CiJapanese Subs") that had been baked into product config.
11 test files updated to sandbox the new workspace path; two new tests
added covering the missing-file-loads-empty behavior directly.

**Audit trigger: No — confidence: High, reason:** none of the touched
files (`paths.py`, `config_loader.py`, `metadata_editor.py`, 11 test
files) are Frozen Components.

**Verification summary:** all three core production diffs read
directly, matched OC's report exactly. Deletion of `Config/origins.json`
independently confirmed. Full test suite independently re-run: **63/63
pass, 0 failures, 0 timeouts** — exact match to OC's own result.
`gui.py`'s appearance in `git status` during this task is unrelated
pre-existing uncommitted work from TASK 19, confirmed via the session
transcript showing zero edits to that file this task.

**Verdict: CLEAN.**
