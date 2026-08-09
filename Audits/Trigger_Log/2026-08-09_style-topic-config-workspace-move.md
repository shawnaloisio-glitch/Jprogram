# Trigger Log — 2026-08-09 — Move Style/Topic config to the Workspace

**Work done:** fixed a real architectural gap discovered while scoping the
batch-import metadata entry task (item #3 of the WORKING_LIST.md priority
list). `Config/styles.json`/`Config/topics.json` lived under `PROJECT_ROOT`
(inside the git repo) and were tracked/committed — but they were never
real shipped defaults, just empty placeholder files (`{"styles": []}`)
that existed solely to stop `load_json()` raising `ConfigError` on a
missing file. This meant a user's real Style/Topic entries (user-managed,
open-ended vocabulary, same category as Collections/Creators) would get
committed as product data into the repo, violating the standing "zero
user-specific data in product" principle
([[project_no_user_specific_data_in_product]]). Collections/Creators
already solved this correctly: they live under `WORKSPACE_ROOT`, outside
the repo, with graceful missing-file handling (empty list, not an error).

Fix copies that exact existing pattern for styles/topics — no new design,
a direct mirror:
- `paths.py`: new `STYLES_CONFIG`/`TOPICS_CONFIG` constants
  (`WORKSPACE_ROOT / "Config" / ...`), next to `COLLECTIONS_CONFIG`/
  `CREATORS_CONFIG`.
- `Source Builder/config_loader.py`: new `_load_styles_raw()`/
  `_load_topics_raw()` helpers mirroring `_load_creators_raw()` exactly;
  `load_styles()`/`load_topics()`/`load_styles_full()`/`load_topics_full()`
  now use them (missing file → `[]`, not an exception).
- `Source Builder/metadata_editor.py`: `_config_path()`/`_sibling_path()`
  gained `"styles"`/`"topics"` special cases, mirroring the existing
  `"collections"`/`"creators"` cases.
- Old `Config/styles.json`/`Config/topics.json` (and their gitignored
  `.bak` files) deleted from the repo — no longer needed.
- 10 test files updated to redirect the new path constants in their
  sandbox setup, each following its own pre-existing
  save/set/restore pattern for `COLLECTIONS_CONFIG`/`CREATORS_CONFIG`.

**Real secondary bug this uncovered and fixed as part of the same change:**
a genuinely fresh install with no `styles.json`/`topics.json` at all would
previously crash with `ConfigError` on load, unlike Collections/Creators
which already handled a missing file gracefully. Now consistent.

Built via the headless DeepSeek-Coder mechanism in an isolated worktree
(`fix-style-topic-config-location`), merged to `master` as `f3eb452`.

**Process note, not about the fix itself:** the first launch attempt of
this task failed outright with a bash quoting error (`unexpected EOF
while looking for matching` a single quote) before any Coder work
happened — the inline `-p` prompt string was too large/quote-heavy for
safe inline shell embedding. Fixed by writing the prompt to a file first
and using `claude -p "$(cat promptfile)"` instead, which succeeded
cleanly on retry. Worth remembering for any future Coder task with a
long, quote-heavy prompt: write it to a file rather than inlining it.

**Audit trigger: No — confidence: Moderate, reason:** no Frozen Component
touched (`paths.py`, `config_loader.py`, `metadata_editor.py`, and their
tests are all outside the Frozen list). Confidence is Moderate rather
than High because this is a real behavior change to config-loading logic
across 3 modules and 10 tests (larger surface than a typical "No, High
confidence" doc/config edit) — but the change itself is low-judgment,
since it's a verified line-for-line mirror of an already-proven pattern
(Collections/Creators), not new design.

**Verification summary (Advisor's own, not accepted on Coder's
self-report — though this time Coder had real Bash access and no
permission denials occurred, unlike the two prior tasks this session):**
- Read every diff directly: `paths.py`, `config_loader.py`,
  `metadata_editor.py` all match the specified mirror-pattern exactly,
  including docstring updates beyond the literal minimum asked (a
  reasonable, in-scope addition, not scope creep).
- `git diff --stat`: exactly the 15 files specified (3 source files, 10
  test files, 2 deletions) — no scope creep.
- Full repo test sweep independently re-run after applying the change to
  the real repo: **59/59 test files passing** (matches Coder's own
  claimed 224/224 individual test count across the 11 files it listed,
  and this time the claim is credible since Bash access was genuinely
  granted and used — confirmed via the raw JSON's empty
  `permission_denials` array).
- `import app` (module-level, not full GUI launch): clean, no startup
  error from the `paths.py` changes.
- Re-ran the actual Style/Topic vocab creation (the same `add_style`/
  `add_topic` calls attempted before this fix) and confirmed directly on
  disk: `styles.json`/`topics.json` now write to
  `Jprogram Workspace/Config/`, not `Jprogram/Config/`; `git status` on
  `Config/` shows only the intended deletions, nothing new appearing to
  be accidentally tracked.

**Verdict: CLEAN.** Merged to `master` (`f3eb452`), worktree and branch
removed.
