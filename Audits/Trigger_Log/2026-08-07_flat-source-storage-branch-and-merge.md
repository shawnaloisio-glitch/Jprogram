# Trigger Log — 2026-08-07 — `flat-source-storage` branch: 4 tasks + merge to `master`

**Backfilled at merge time, not logged individually as each task landed —
same lapse pattern `CLAUDE.md` already documented once before (four tasks
went silently unlogged on 2026-08-05, discovered and backfilled
2026-08-06). Recording all five decisions from this branch now, together,
rather than repeating the gap.**

## Task 1 — De-nest `Sources\collections\`/`standalone\` into a flat root

**Work done:** removed the collection/standalone folder split; every
source keyed by filename only under `Sources\`. Touched `controller.py`,
`gui.py`, `metadata_editor.py`, `recent_sources.py`, `processing_tab.py`,
`source_package.py` (docstrings), plus test files. QC Test Harness path
fixed separately by Advisor directly (path-string edit).

**Audit trigger: No — confidence: Low, reason:** no Frozen Component
touched; contained to Source Builder. Verified via raw `git diff` (12
files, exactly matching the stated file list) and an independent
from-scratch re-run of all 23 Source Builder test files (326/326).

## Task 2 — Standalone SQLite index builder

**Work done:** new `Index\index_builder.py` + tests, a disposable
rebuildable cache over Source Package/config data. CLI-only, unwired to
any pipeline stage.

**Audit trigger: No — confidence: Low, reason:** entirely new, unwired
code; no Frozen Component touched. Verified via raw code read (schema,
parameterized queries, atomic rebuild all confirmed correct) and an
independent re-run (4/4) plus an independent CLI smoke test in an
isolated temp workspace.

## Task 3 — Material Level / Style / Duration backend (no GUI)

**Work done:** Source Package schema v2 (`material_level` required,
`style_id`/`duration_seconds` optional), new Style CRUD vocabulary in
`metadata_editor.py`, a display-name-uniqueness fix applied across all
four vocab validators, `Index\index_builder.py` repointed to a shared
`project_config.MATERIAL_LEVELS` constant. Deliberately GUI-untouched;
`ReadyStateEngine` gained optional plumbing only, no enforcement (would
have broken live saves with no field to fill it from). 14 additional
test files fixed as live-discovered, Owner-approved fallout from the
schema change.

**Audit trigger: No — confidence: Low, reason:** no Frozen Component
touched. Verified via raw diff read of every touched source file
(`project_config.py`, `source_package.py`, `controller.py`,
`metadata_editor.py`, `Index\index_builder.py`) and an independent
re-run of all 25 relevant test files, all green, matching claimed counts
exactly. QC Test Harness's now-required `material_level` arg fixed
separately by Advisor directly (single literal value, no judgment call).

## Task 4 — Fix `tests\test_app_shell.py` (post-merge follow-up)

**Work done:** one test, surfaced only by a full repo-wide suite run
after merging to `master` (it lives outside `Source Builder\tests\`, so
none of Tasks 1–3's scoped test runs ever exercised it). Fixed with the
exact `_inject_material_level()` pattern already established in Task 3's
own `test_source_builder_gui_handoff.py` fix.

**Audit trigger: No — confidence: Low, reason:** single test file,
mirrors an already-verified pattern exactly, no Frozen Component
touched. Verified via raw diff (byte-for-byte match to the established
pattern) and independent re-run (9/9).

## Merge — `flat-source-storage` → `master`

**Action:** `git merge --no-ff flat-source-storage` on `master`
(commit `276a2e7`), followed by Task 4's fix (commit `b4c0c32`).

**Audit trigger: No — confidence: Moderate, reason:** no individual
change in the branch touched a Frozen Component, and each was
independently verified (diff + test re-run) at the time, not accepted on
self-report alone. Raised above Low specifically because this is a merge
into the shared reference branch and changes a real, live-app-visible
contract (physical Sources storage layout; Source Package schema v2)
— not just an internal refactor. Full repo-wide test suite (65 files)
independently re-run twice: once immediately after the merge (64/65,
one real gap found — Task 4 above), and once more after Task 4 landed
(65/65, zero failures). Not pushed to `origin` at the time of this log
entry — that remains Owner's separate, explicit call.
