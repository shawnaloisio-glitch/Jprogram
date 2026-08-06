# Jprogram Session Bootstrap

Companion to `CLAUDE.md`. `CLAUDE.md` is auto-loaded and holds Advisor's standing behavior rules (role, permission mode, evidence hierarchy, report format, Frozen Components trigger list) — read it first if you haven't already. This file holds current project state: what's built, what's next, what to know before touching anything. Unlike `CLAUDE.md`, this file is expected to go stale between sessions and gets refreshed as part of each handoff.

**Note:** the status content below is carried over from the prior version of this doc and has not been independently re-verified as of this rewrite — a project audit is planned as a near-term task specifically to confirm or correct it (see Jprogram design spec, §8, task 9).

**Small, concrete pending items** (things to check/decide/fix that aren't major scope) go in `WORKING_LIST.md`, not here — keeps this file about architecture/state/major tasks only.

---

## 1. Project Purpose

- A **Japanese language corpus project**.
- **Goal:** create reliable corpus data from Japanese media sources (podcasts, anime subtitles; future manga, novels, web articles).
- **Pipeline purpose:**
  ```
  Raw source → cleaned data → parsed structured data → validated corpus → analysis
  ```
- The project builds an immersion-oriented corpus that preserves raw linguistic evidence so later analyzers can compute frequency, distribution, exposure, and other measurements deterministically.

---

## 2. Current Architecture

```
User (via Application Shell)
   ↓
Sources tab — Source Builder (capture / import / save)
   ↓
Source Package (sidecar .source.json)
   ↓
Handoff (Registry entry + Cleaning Job)          [Source Intake writers]
   ↓
Cleaner             (Transcript Cleaner / Subtitle Cleaner; future cleaners plug in)
   ↓
Data Processor
    Job Builder     (clean text → jobs)
    Request Builder (jobs → DeepSeek requests)
    Parser          (DeepSeek, non-thinking + hybrid format)
    Validator       (deterministic gate)
    Corpus Builder  (deterministic → canonical corpus)
   ↓
Canonical JSONL Corpus   (sentence-per-line, the single source of truth)
   ↓
Analysis            (deterministic analyzer utilities → evidence datasets → future interpretation)
```

Entry points today:

- **`app.py`** — the application shell (Sources / Processing / Analysis tabs). This is the primary entry point.
- **`Source Builder\source_builder.py`** — standalone Source Builder launcher.
- **Production Manager CLI** — `python "Production Manager\production_manager.py" --source/--run/--pipeline/--dry-run`. (Note: "Production Manager" here is the software component that launches pipeline-stage subprocesses — not the Advisor/OC workflow role discussed in the design spec, which uses the term "Advisor" instead to avoid this exact collision.)
- Pipeline stage scripts: `job builder.py`, `request builder.py`, `deepseek_client.py`, `corpus_builder.py`, `response_validator.py`, and the two cleaners.

Source Intake (utilities, artifact writers, and coordinator) is implemented.
The current GUI path creates Registry + Cleaning Job through
`Source Builder\handoff.py` using the Source Intake artifact writers.

---

## 3. Core Design Principles

### ONE PROGRAM = ONE TASK

Rules:
- Each program owns one responsibility.
- Programs communicate through defined artifacts.
- A program does not modify another program's owned files.
- Direct imports between programs are avoided unless explicitly approved as shared utilities.
- Management/orchestration belongs to future manager tools, not individual programs.

Related principles:
- **The parser preserves evidence; it never produces conclusions** (Garbage in, garbage out).
- **Verify over trust** — deterministic checks wherever cheap; never silently repair.
- **The canonical corpus is the single source of truth** (Rule 5); analyzers only read it.
- **Frequency without distribution is incomplete data.**
- **Source Integrity:** every source gets a human-readable `source_id`, a SHA-256 fingerprint, type/processing metadata, and lineage; sources are immutable; the corpus is rebuildable.

---

## 4. Frozen Components

See `CLAUDE.md` for the authoritative list — it's the one Advisor's automatic audit-trigger check runs against. Keeping a single copy there avoids the two files drifting out of sync.

---

## 5. Source Intake Architecture

**Purpose:** Source Intake answers: *"What is this source?"*

**Responsibilities:**
- source registration
- source_id creation
- SHA-256 creation
- duplicate detection
- Source Registry creation
- Cleaning Job creation

**Does NOT:**
- clean files
- execute cleaners
- call APIs
- parse data
- validate parser output
- build corpus

Design rule: `source_type != cleaning_profile` (e.g., `anime_subtitle` → `subtitle_standard_v1`); the mapping is configuration-driven; new cleaners are added by new profile + new program + config update, never a Source Intake redesign. Naming convention: `{type}_{slug}_{sequence}` (e.g., `sub_sousou-no-frieren_ep001`, `pod_conteppei_ep051`, `manga_one-piece_ch012`).

---

## 6. Source Intake Current Implementation Status

**Complete:**

Phase 1 (utilities):
- `hashing.py`
- `source_id.py`
- `schemas.py`

Phase 2 (artifact writers):
- `registry.py`
- `cleaning_job.py`
- `cleaning_result.py`

Phase 3 (coordinator + duplicate detection):
- `source_intake.py` (coordinator)
- `duplicate_check.py`
- `resolver.py`
- configuration integration

**Tests:** Source Intake suite — **109 tests passing** (corrected 2026-08-05; see §10 step 6 and the 2026-08-05 deep audit in `Audits/2026-08-05/DEEP_AUDIT_REPORT.md` — the "106" figure was stale and never propagated here even after the correction was first found).

**Current GUI path note:** The Application Shell / Source Builder creates the
Source Registry entry and Cleaning Job through `Source Builder\handoff.py`,
which reuses the Source Intake artifact writers directly. The standalone
`source_intake.py` coordinator is complete but is not currently invoked by the
GUI/Processing path.

---

## 7. Source Intake File Ownership

- **Source Intake owns:**
  - Source Registry — source identity and metadata.
  - Cleaning Jobs — cleaner instructions.
  - Cleaning Results — cleaner outcome records.
- **Cleaner owns:**
  - Cleaned artifacts.
  - Cleaning Results (written via the Source Intake `cleaning_result.py` writer).
- **Production Manager owns:**
  - Launching pipeline stage programs (as subprocesses).
  - Queue/resume decisions (via artifact evidence).
  - Monitoring / status reporting.

No component may silently modify another component's artifacts.

---

## 8. Artifact Contracts

Three frozen artifacts (schemas defined in `Source Intake\schemas.py`):

- **Source Registry** — answers *"What is this source?"* (identity: `source_id`, `original_filename`, `sha256`; classification: `source_type`, `format`, `language`; processing: `cleaning_profile`, `cleaner_version`; lineage references; `lifecycle_status`).
- **Cleaning Job** — answers *"What should the cleaner process?"* (`source_id`, `raw_path`, `source_type`, `cleaning_profile`, `cleaner_version`, `output_path`).
- **Cleaning Result** — answers *"What happened during cleaning?"* (`source_id`, `success`, `cleaned_artifact`, `statistics`, `errors`).

The Source Package (`Source Builder\source_package.py`) is a GUI-side contract
too: a `.source.json` sidecar beside each canonical source file. See
`SOURCE_PACKAGE_HANDOFF.md`.

All artifacts: UTF-8, `ensure_ascii=False`, `sort_keys=True`, deterministic byte output, atomic writes (temp + rename).

---

## 9. Current Source Intake Files

```
Source Intake\
    hashing.py
    source_id.py
    schemas.py
    registry.py
    cleaning_job.py
    cleaning_result.py
    duplicate_check.py
    resolver.py
    source_intake.py
    tests\
        test_hashing.py
        test_source_id.py
        test_schemas.py
        test_registry.py
        test_cleaning_job.py
        test_cleaning_result.py
        test_duplicate_check.py
        test_resolver.py
        test_source_intake.py
        (and others)
```

---

## 10. Next Planned Task — First Advisor-CC Session Checklist

Work through these in order. Don't skip ahead — several depend on confirming the prior step actually worked.

1. **Sanity-check your own setup.** Confirm you've loaded `CLAUDE.md` and understand you're Advisor by default (read-only, Plan mode). State this back before doing anything else, so Owner can catch a misconfiguration immediately rather than after real work starts.

2. **Verify the standing-instruction files are actually in place** at repo root: `CLAUDE.md`, `QWEN.md`, `AGENTS.md`, this file. Report what you find — don't assume.

3. **Qwen Code authentication — permanently on hold (Owner decision, 2026-08-05) until Owner explicitly says otherwise.** Not "revisit when convenient" — do not propose or pursue this unprompted. Alibaba ModelStudio signup hit a broken email-verification loop; Owner has since decided to leave this on indefinite hold rather than revisit it. Auditor's frozen-component tier falls back to a second CC session when needed (see `CLAUDE.md`'s Auditor section) — Advisor must state plainly in the trigger report whenever this fallback is used, since it's weaker independence than the design calls for.

4. **Delete the two confirmed-identical duplicate files** (verified byte-for-byte identical earlier): `Daily Handoff/Handoff_2026-08-04/PROJECT_STATUS.md` and `Daily Handoff/Handoff_2026-08-04/Session_Handoff_Audit.md`. Keep the root-level / `Audits/2026-08-04/` originals.

5. **Propose a restructure plan for `Daily Handoff/` — propose only, do not execute without Owner approval.** Prior analysis (outside this session) found three distinct things mixed in that folder:
   - `HANDOFF_2026-07-31.md`, `HANDOFF_2026-08-01_QWEN_BUILDER_REVIEW.md`, `HANDOFF_2026-08-02_FLASH_EXPRESSION_POLICY.md` — artifacts of the old ChatGPT-session-handoff system, now superseded by this file. Likely fine to leave in place (git history preserves them) but should not be treated as current input.
   - `Handoff_2026-08-04/CURRENT_IMPLEMENTATION_MAP.md`, `CURRENT_TEST_STATE.md`, `DATA_LIFECYCLE_REALITY.md`, `IMPLEMENTATION_VS_DOCUMENTATION.md` — look like a partial prior attempt at the project audit (task below). Treat as useful starting input to that audit, not clutter.
   - `SOURCE_BUILDER_*.md`, `SOURCE_METADATA_SPEC.md`, `GUI_ARCHITECTURE.md`, the undated `PROJECT_CONTEXT.md` — genuine design/spec docs that don't belong in a folder called "Daily Handoff." Confirm this read is correct and propose where they should actually live.

6. **The actual project audit** (per the design spec, sequenced to happen only after setup is confirmed working): verify current status of everything in §§1–9 above, using the `Handoff_2026-08-04/` snapshot files from step 5 as a starting point rather than starting from zero. Confirm or correct the "Source Intake Phase 3 complete, 106 tests passing" claim and the "5 test failures — stale fixture config" claim specifically — both are unverified carryovers from before the git migration.

   **Done (2026-08-05). Findings, from raw test-run evidence (every `test_*.py` in the repo run directly — this project's tests are standalone scripts, not pytest/unittest — 60 files, 748 tests total):**
   - Entry points (§2) and Frozen Components (§4 / `CLAUDE.md`): all confirmed present on disk, no gaps.
   - Source Intake: **109/109 passing** (not 106 — count grew slightly, e.g. `test_paths.py` covers the newer workspace-separation logic).
   - Repo-wide: **742/748 passing**, 6 failures, two distinct causes:
     - **1 failure was self-inflicted this session**, by the step-5 `Daily Handoff/` → `Archive/` move: `Production Manager/tests/test_production_manager_api_docs.py` hardcoded the old path to `GUI_ARCHITECTURE.md`. Fixed by updating the test to point at the new archive path; confirmed passing again (7/7).
     - **5 failures confirm the old "stale fixture config" claim exactly** (4 in `Source Builder/tests/test_source_builder_gui_presets.py` + 1 in `test_source_builder_quick_presets.py` = 5) — not in Source Intake as the old wording implied, but in Source Builder. Root cause: these tests depend on a `"teppei_beginner"` collection resolving via `Config/collections.json`, which no longer has that entry after the intentional runtime-data reset noted in the checkpoint below. **This is an expected side effect of that reset, not a bug and not migration damage — left as-is per Owner decision (2026-08-05).** Restore the fixture data only if/when real collection config work resumes.
   - `cleaner common.py` (present in the pre-migration backup `C:\Jprogram stable build backup 8-4-26`, absent from the git repo): confirmed dead/unreferenced (zero imports anywhere, content was a stray stale draft of `paths.py` under the wrong filename) — correctly excluded from the git baseline, not lost migration content.
   - Conclusion: **the git migration itself did not break anything found so far.** The only real breakage found was caused by this session's own archive move, and was fixed within the same session.

   **Follow-up (2026-08-05, TASK 1, first Coder command under this protocol):** the 5 confirmed config-isolation failures above were traced further and fixed — `test_source_builder_quick_presets.py` and `test_source_builder_gui_presets.py` were missing the `paths.COLLECTIONS_CONFIG` isolation pattern that 8 sibling test files already use correctly (temp `collections.json` fixture instead of the live workspace config). Fixed by OC, independently verified against raw `git status` and direct test re-runs (not OC's self-report): `quick_presets` now 21/21, `gui_presets` now 7/8, zero regressions across the other 18 Source Builder test files.
   - **New, separate, non-blocking issue found during that fix:** `test_source_builder_gui_presets.py`'s "standalone preset populates identity and source name" test asserts `source_type == "article"`, but the GUI's `_processable_source_types()` (`Source Builder/gui.py:48-55`) filters to `PROCESSING_PROFILES` keys only (`anime_subtitle`, `podcast_transcript`) — `"article"` can never pass regardless of config. This is a latent test-vs-app mismatch, not a config/isolation problem, and not something the isolation fix could address. Left as-is per Owner decision (2026-08-05) — a known, understood, non-blocking single test failure. Revisit if/when `PROCESSING_PROFILES` gains an `article` profile, or the test's expected value should simply change to a currently-processable type.

---

**Original next-task list, superseded by the above but kept for reference:** real-data validation (full workflow with real source material), packaging/installer, external QC review (status was unclear — listed as "pending" in one place, "invoked once in ~60 hours" in another; Qwen Code is now available for this role regardless).

---

## 11. OC Operating Instructions

See `AGENTS.md` (auto-loaded by OpenCode) for the authoritative reporting format and core rules — keeping a single copy there avoids this file and `AGENTS.md` drifting out of sync.

Advisor reads OC's output from `opencode session export` / raw session storage (see `CLAUDE.md`), not terminal display text.

---

## 12. Audit Log

Location: `Audits/Trigger_Log/` — nested under the existing `Audits/` folder rather than a sibling, since it's still fundamentally audit-related content, just a different granularity (every trigger decision, vs. `Audits/2026-08-04/`-style full review reports). Every Advisor trigger-field decision (Yes or No) gets recorded here, giving a queryable history for calibrating invocation rate over time.

---

## 13. Current-Stack Appendix

Provider-specific — revisit if the Coder model/platform changes:
- Coder commands use a fixed opening template, with only the task-specific part varying, to leverage prompt-prefix caching.
- OpenCode's `autoCompact` setting is enabled for long sessions.
- Reasoning effort is scaled per task rather than fixed.


---

## 14. Session Wrap-Up (2026-08-07) — Updated after Session 6

**Read this section first, always — it's kept current at every wrap-up,
not appended to indefinitely.** This update supersedes the "Session 5"
version below it (kept for reference, marked accordingly). If anything
below conflicts with an older section elsewhere in this file, this
section wins — it was last refreshed 2026-08-07, end of session 6.

### Current phase

Same category as Session 5: more `deterministic-parser` branch prep and
cleanup, not the Corpus Change Study's own phases. **The actual
GiNZA/SudachiPy rewrite still has not started.** This session worked
through several `WORKING_LIST.md` items specifically chosen because
they sit outside the upcoming parser rewrite's blast radius (none touch
a Frozen Component), plus one governance change to Advisor's own git
behavior.

Six commits landed on `deterministic-parser` this session, all local,
not yet pushed at the time of this wrap-up (pushing now, as the
session's own end-of-session housekeeping, per the git-handling policy
revised this same session — see below):

1. `71dad32` — swapped Episode/Origin field order on the main Sources
   form (Owner reported it visually backwards from a live screenshot).
2. `2c477c3` — revised `CLAUDE.md`'s Git handling: commits now
   pre-approved once a change passes Advisor's evaluation; pushes
   default to end-of-session wrap-up instead of an explicit ask every
   time (Owner's own initiative — commits are cheap/reversible, gating
   every one added friction without adding safety; push kept at a
   higher bar since it's shared/visible state).
3. `136940c` — removed the per-collection `default_source_type` field
   entirely (not just hidden). Investigation found it was more than a
   stale display: live-wired into `quick_presets.py`'s preset-population
   fallback. Confirmed safe to remove outright because `source_type_var`
   already stays correctly populated from Config independent of that
   mechanism, now that only one `source_type` value exists anywhere.
   Touched `metadata_editor.py`, `config_loader.py`, `quick_presets.py`,
   `gui.py`, `metadata_editor_gui.py`, and 4 test files. OC also caught
   and removed a related dead check in `delete_source_type()` that
   referenced the now-gone field — correct follow-through, not scope
   creep.
4. `9dc506d` — corrected two stale `WORKING_LIST.md` entries found
   already resolved while scanning for parser-rewrite-safe work:
   `RAW_SUBTITLES`/`RAW_TRANSCRIPTS` removal was actually done in
   TASK 15 but never checked off; the `podcast_transcript` import-default
   bug is moot since that `source_type` no longer exists anywhere after
   the TASK 16-18 collapse.
5. `f646709` — added `paths.RAW_IMPORTS` as a standard workspace folder.
   Owner had manually created a `Raw Imports` folder at project root;
   moved it (with its existing `Subtitles`/`For Future Import Types`
   structure intact) into the real Workspace instead, since raw import
   material is customer/runtime data, not product code — matches
   `paths.py`'s own stated product-vs-customer-data split. Wired into
   the existing `WORKSPACE_FOLDERS`/`ensure_workspace()` auto-creation
   mechanism, so no new setup utility was needed (Owner initially
   thought one would be, correctly reconsidered once this was pointed
   out).
6. `6fa18d0` — Import Material's Browse button now defaults to
   `paths.RAW_IMPORTS` and remembers the last-picked folder for the rest
   of the running session, mirroring the Load File button's existing
   pattern exactly.

All six independently verified against raw `git diff` and direct test
re-runs, not OC's self-report — full Source Builder suite green (23
files, 0 failures) after every change. `master` remains the mothballed
DeepSeek-architecture reference, untouched this session.

### Two process/environment findings from this session, not code

- **A citation gap in this project's own docs.** Both this file and
  `WORKING_LIST.md` cite `2026-08-06_blast_radius_scope.md` as the
  source confirming the Analysis modules are unaffected by the parser
  rewrite. That file does not actually exist anywhere in the repo or
  git history — confirmed via direct search. Worked around it this
  session by using `CLAUDE.md`'s Frozen Components list directly (the
  actually-authoritative source regardless). Not fixed: either the
  missing analysis should be redone and saved, or the citation should
  be removed/corrected so it stops pointing at a file that isn't there.
- **This Bash shell has a stale `JPROGRAM_WORKSPACE` environment
  variable** (the pre-relocation value, `C:\Jprogram Workspace`) — the
  real persistent store is correct (confirmed via the direct registry
  read `CLAUDE.md` already prescribes for this exact failure mode).
  Root cause: env vars are inherited once at process start, not
  live-refreshed; the underlying shell process was spawned before the
  variable was last updated. Caused one small accidental side effect
  (an empty folder created in the stale location during a sanity
  check), cleaned up immediately. Owner's plan: a full computer restart
  before the next session resolves it — confirmed sufficient, since a
  fresh login re-reads the registry-stored value cleanly. **Verify this
  directly at the start of next session rather than assuming the
  restart happened or worked** — same standing caution `CLAUDE.md`
  already states for this class of issue.
- Separately, and not addressed this session: a **pre-existing stale
  `C:\Jprogram Workspace` folder tree** (predates this session, not
  created by this session's work) is still sitting on disk — likely
  tied to the still-open "OpenCode desktop may still point at the old
  repo folder" item carried from Session 4. Not touched without Owner's
  say-so; flagged, not cleaned up.

### Last several decisions and why

- **Git handling policy revised** (see commit `2c477c3` above) — the
  reasoning and exact new rule are in `CLAUDE.md` itself now; this
  entry is just the pointer so it isn't missed at next wrap-up.
- **`default_source_type` removed outright, not just hidden** — same
  judgment already established for `origin`/`source_type` cleanup this
  branch: when a field can only ever resolve to one value, keeping it
  around as inert data invites exactly the kind of stale-legacy-value
  confusion already seen elsewhere in this project, so delete rather
  than leave as dead weight.
- **`Raw Imports` corrected to live in the Workspace, not project
  root** — Owner's first instinct was project root (where the folder
  was manually created); corrected against `paths.py`'s own stated
  convention once the "would need a setup utility" concern turned out
  to be moot (the existing auto-creation mechanism already covers it).

### Open risks / unresolved questions

Full detail in `WORKING_LIST.md` — this is a pointer, not a duplicate.
Headline items still open:

- **The Corpus Change Study work itself** — still the big one, still not
  started. Start at
  `C:\AI Development Projects\Corpus change study\00_INDEX.md`.
- **The missing `2026-08-06_blast_radius_scope.md` citation** (new this
  session, see above) — fix by either recreating that analysis or
  removing the dangling reference.
- **This shell's stale `JPROGRAM_WORKSPACE` value** — expected resolved
  by Owner's planned computer restart; verify at next session's start.
- **The pre-existing stale `C:\Jprogram Workspace` folder tree** — still
  on disk, still not cleaned up, still tied to the unresolved OpenCode
  desktop repo-location question from Session 4.
- **12 `ruff` findings deliberately deferred**, all inside Frozen
  Components the parser rewrite will touch anyway — unchanged from
  Session 5, see that section below for the caution about
  `corpus_builder.py`'s re-exports.
- **A forward-looking, unscoped note**: possible future need for
  metadata to organize processor/analysis output data, distinct from
  `origin`. Not a task yet.
- **`origin`'s name itself may change later** — explicitly deferred,
  cheap to do anytime.
- **`sentence_index` "no gaps" not validated** — still deliberately
  deferred, zero current functional impact confirmed.
- **Remaining live-testing GUI backlog** — Import default-folder is now
  done (drop from future carry-forward). Still open: embedded-tabs
  restructure, Analysis multi-file capability (direction already
  settled: one report per file, loop the existing single-file logic,
  no Frozen changes — just not built), Template Editor pass, the
  Tkinter GUI-state error report still blocked on Owner pasting a
  traceback, the `teppei_beginner` stale-selection bug, the
  import-from-subtitle workflow (needs design thought, not scoped).
- **API key structure/utility design** — not started.

### Next immediate task

No hard blocker on anything. In rough priority order:
1. More `WORKING_LIST.md` items outside the parser rewrite's blast
   radius remain if more branch-prep is wanted: the `teppei_beginner`
   stale-selection bug, Analysis multi-file capability, or a Template
   Editor pass are the next-easiest candidates.
2. Otherwise: start the actual Corpus Change Study work from
   `C:\AI Development Projects\Corpus change study\00_INDEX.md` — the
   real reason `deterministic-parser` exists as a branch.
3. Test the freshly-wiped workspace end to end, per Session 5's own
   stated goal — still not done.

### Real-data validation status

Unchanged from Session 5: done once, successfully, via
`QC Test Harness/`. See `QC Test Harness/README.md` for reuse
instructions.

---

## Session 5 wrap-up (2026-08-06) — superseded by the section above, kept for reference

### Current phase

Relocation (Session 4) is old news now, fully absorbed. This session did
three things, in order: (1) revised the Advisor/Auditor contract now that
Qwen Code is permanently off the table, (2) closed out a real "outside
best practice" audit (secrets, dependency tracking, linting, git hygiene),
(3) did substantial product cleanup on the `deterministic-parser`
branch — dead code, a full `source_type` collapse to one `clean_text`
value, and moving `origin` to the workspace. **The deterministic-parser
work itself (the actual GiNZA/SudachiPy rewrite) has still not started** —
everything this session was branch prep and cleanup, not the Corpus
Change Study's own phases.

Coder task count: **20 tasks now** (TASK 14–20 this session), all
independently verified — see `Audits/OC_Reliability_Log.md` and
`Audits/Trigger_Log/2026-08-06_task14-*.md` through `task20-*.md`.
`master` remains the mothballed DeepSeek-architecture reference,
untouched this session. Two commits landed on `deterministic-parser`
this session (`2935fb4`, `3994642`), both pushed to `origin` — nothing
uncommitted right now.

### The Advisor/Auditor contract changed — read `CLAUDE.md` directly, don't assume from memory

Qwen Code is now stated as permanently not part of this project's audit
model (previously "on indefinite hold" with a fallback framing — now just
the settled model). Concretely:
- **Auditor is now a fresh Claude Code subagent/session**, never a
  continuation of the Advisor conversation that evaluated the change —
  used for real this session (TASK 14, see below), including a mistake
  (isolating the subagent in a stale git worktree that didn't have the
  uncommitted diff) caught and corrected before any conclusion was drawn.
- **Advisor/OC boundary redrawn at logic vs. size**, not size alone —
  Advisor may now directly edit docs, config values, path strings, and do
  simple file management; OC still implements anything that changes
  program logic/behavior, no exception for how small the change is.
- **New "Git handling" section** — Owner has no informed git preferences
  (stated directly), so Advisor decides git mechanics and explains
  what/why, only asking for a go/no-go on the action itself (commit,
  push). Established this session: push early on solo feature branches,
  no reason to hold back like the old `master`-only caution.
- **Phase-boundary audit calibration for `deterministic-parser`
  specifically**: once the actual parser rewrite starts, the fresh-subagent
  audit fires once per completed phase (not per Coder command), because
  branch isolation already means mistakes don't reach `master` until
  merge. This does not loosen the automatic-Yes trigger anywhere else.
- **Trigger-log self-check added** — the log had silently lapsed for 4
  tasks (TASK 10–13) before this session caught and backfilled it;
  `CLAUDE.md` now says not to treat a task as closed until the log file
  itself is confirmed on disk.
- `QWEN.md` retired to `Archive/QWEN.md` with a header explaining why.

### "Outside best practice" audit — closed out

A deliberate self-audit against general software-engineering practice
(not just this project's own rules) found and fixed: 5 commits sitting
unpushed (pushed immediately, and push-early is now the standing habit);
zero dependency manifest (added `requirements.txt`/`requirements-dev.txt`,
currently empty runtime deps, ready for GiNZA/SudachiPy); zero lint
tooling (added a conservative `ruff` config, pyflakes-only — it caught a
real closure-capture `NameError` bug on its first run, fixed separately);
a leaked plaintext DeepSeek key sitting in `.claude/settings.local.json`
(confirmed stale/dead, not the live key, but removed anyway).

### TASK 14 — API key fallback removed from `deepseek_client.py` (Frozen, Transport)

The legacy `api_key.txt` file-fallback is gone; `DEEPSEEK_API_KEY` (env
var) is the only supported source now. Removing it exposed a real bug —
`run()`'s exception handler no longer matched what the simplified
`_resolve_api_key()` could raise, so an unset key crashed instead of
failing cleanly. OC found and correctly declined to fix it (Advisor's own
command boundary was too narrow), then fixed it in an immediate follow-up.
This was the first real exercise of the new fresh-subagent Auditor model.

### TASK 15 — dead-code cleanup

Removed a confirmed unreachable duplicate `elif` branch in
`production_manager.py`'s `state_for()`, and the orphaned
`RAW_SUBTITLES`/`RAW_TRANSCRIPTS` path constants (a retired
folder-scan-acquisition design, same root cause investigated further in
TASK 16). One part (removing two apparently-dead methods from `gui.py`)
was correctly blocked by OC — they're called directly by a test file
outside that command's boundary — and Advisor's own follow-up
investigation found the concern was smaller than it looked (both dead
methods delegate to the same shared helper the live binding also uses).
Left as-is; `_on_source_type_selected` was later removed anyway as a
side effect of TASK 19.

### TASK 16–18 — `source_type` collapsed to a single `clean_text` value

The `podcast_transcript`/`anime_subtitle` split was already dead:
subtitle-specific cleaning happens at Import Material's Subtitle File
step (`Subtitle Importer/cleaner.py`, a fully separate implementation),
not at the old `Subtitle Cleaner/clean_subtitles.py` route, which was
confirmed to be an abandoned remnant of the pre-"birth certificate"
design and deleted entirely. Sequenced as three Coder commands — config/
backend (TASK 16), every downstream reference and ~40 test fixture files
(TASK 17, including a real production bug found and fixed in
`source_intake.py` and a genuine GUI test hang root-caused, not just
patched over), then the GUI itself — main-form dropdown and the Metadata
Editor's now-pointless Source Types tab removed (TASK 18). Full suite
green (63/63) after each command.

### TASK 19 — removed the source type display entirely

Even the static display TASK 18 left behind turned out to be
unnecessary once there's only one real value — Owner's call, live in the
app. Removed both display rows and their now-dead plumbing
(`source_type_display_var`, `source_type_label_map`,
`_sync_source_type_display`); `source_type_var` itself and the logic
setting it from the real Config vocabulary are untouched.

### Workspace relocated, and origin moved to live there too

Separately from the repo relocation (Session 4), the **Workspace data
folder** itself moved this session, at Owner's request: `JPROGRAM_WORKSPACE`
now points to `C:\AI Development Projects\Jprogram Workspace` (previously
`C:\Jprogram Workspace`, which stayed put through the Session 4 repo
move on purpose). Owner wiped it clean via the standard "delete folder,
reopen app, `ensure_workspace()` recreates it fresh" procedure — the
workspace is now genuinely empty, a deliberate clean slate for testing
the setup from scratch. Owner also renamed/cleaned up the various
`Jprogram... backup` folders that had accumulated at the old location.

While looking at a live screenshot during this, confirmed `origin` no
longer drives any pipeline routing (absent from Source Intake's resolver/
schemas and every Data Processor stage) — it's pure descriptive metadata
now, same category as `collections`. TASK 20 moved it to live in the
workspace exactly like collections: no shipped defaults, no seeding,
empty until the user adds an entry. This also deleted a real personal
entry (`cijsub`/"CiJapanese Subs") that had been baked into shipped
product config — a live instance of the "no user-specific data in
product" principle being enforced, not just stated.

### Last several decisions and why

- **Qwen Code's retirement is now stated plainly, not softened** — the
  real independence axis in this setup is OC (implementer) vs. Claude
  Code (reviewer), not cross-vendor audit. Fresh-subagent review is the
  cheap substitute that's actually available.
- **The Advisor/OC boundary moved from size to logic** because the old
  "no exception even for trivial" wording kept getting tested by real
  mechanical work (relocation path-fixes, then this session's own
  contract edits) that carried zero implementation judgment.
- **`Subtitle Cleaner/` was deleted outright, not just deprecated** —
  confirmed via direct trace of every caller (none) that it was fully
  dead, not just unused-for-the-recommended-workflow. Matches the
  project's stated aversion to "two sources of truth, only one real."
- **`origin`'s move to the workspace mirrors `collections` exactly**
  (no shipped defaults, no seeding) rather than inventing a new pattern —
  found and reused an existing special-case hook in
  `metadata_editor.py`'s `_config_path()` rather than building parallel
  machinery.
- **Both post-collapse commits used one combined commit each** rather
  than surgical per-task splitting — the fixture-rename passes touched
  nearly every file the preceding cleanup pass had also touched, making
  clean separation impractical without risky interactive staging. Judged
  proportionate for a solo project; each commit message enumerates the
  distinct threads bundled together.

### Open risks / unresolved questions

Full detail in `WORKING_LIST.md` — this is a pointer, not a duplicate.
Headline items still open:

- **The Corpus Change Study work itself** — still the big one, still not
  started. Start at
  `C:\AI Development Projects\Corpus change study\00_INDEX.md`. Now
  genuinely unblocked — no more prep work queued ahead of it that anyone
  is aware of.
- **12 `ruff` findings deliberately deferred**, all inside Frozen
  Components the parser rewrite will touch anyway (`corpus_builder.py`,
  `deepseek_client.py`, `parser_normalizer.py`) — fold into that work,
  don't do a separate pass. One real trap already found there: some of
  `corpus_builder.py`'s "unused" re-exports from `parser_normalizer` are
  actually used externally (`test_corpus_builder.py` via the `cb.` alias)
  — verify each one individually before removing, don't trust ruff's
  suggestion blindly on this file.
- **A forward-looking, unscoped note**: possible future need for
  metadata to organize processor/analysis output data, distinct from
  `origin`. Not a task yet, just don't lose the thought.
- **`origin`'s name itself may change later** — Owner floated this,
  explicitly deferred, cheap to do anytime since it's just a JSON key and
  a few Python identifiers.
- **OpenCode desktop still likely pointed at the old repo folder** —
  Owner action from Session 4, status not re-checked this session.
- **`sentence_index` "no gaps" not validated** — still deliberately
  deferred, zero current functional impact confirmed (Session 3).
- **From the Session-2 code quality audit, still open**: the duplicated
  silent-fallback-to-zero pattern in `corpus_builder.py`'s
  `response_path_for()` and `deepseek_client.py`'s
  `job_number_from_request()`; two unused write helpers
  (`write_jsonl_record`, `Analysis/output_writer.py`). All in Frozen
  Components in the parser-rewrite blast radius — same "defer, don't do
  separately" logic as the ruff findings above. The dead duplicate
  `production_manager.py` branch from this same audit **is now fixed**
  (TASK 15) — drop it from future carry-forward lists.
- **API key structure/utility design** — not started.
- **Remaining live-testing GUI backlog** — embedded-tabs restructure,
  import defaults, Analysis multi-file capability (Owner's direction:
  one report per file, loop the existing single-file logic, no Frozen
  changes — not yet built), Template Editor pass, the Tkinter GUI-state
  error report still blocked on Owner pasting a traceback, the
  `teppei_beginner` stale-selection bug (Owner was going to test this
  live; outcome unknown to Advisor) — see `WORKING_LIST.md`.

### Next immediate task

No hard blocker on anything. In rough priority order per this session's
own momentum:
1. If Owner wants to keep doing branch-prep/cleanup: pick another
   `WORKING_LIST.md` item, same pattern as this session (all clearly
   outside the Frozen-Component blast radius until the parser work
   itself starts).
2. Otherwise: start the actual Corpus Change Study work from
   `C:\AI Development Projects\Corpus change study\00_INDEX.md` — the
   real reason `deterministic-parser` exists as a branch.
3. Test the freshly-wiped workspace end to end (Owner's own stated goal
   for wiping it) — confirm the full setup/workflow still works from a
   genuinely clean state before assuming it does.

### Real-data validation status

Unchanged: done once, successfully, via `QC Test Harness/`. See
`QC Test Harness/README.md` for reuse instructions. Note: the real
workspace was wiped this session — if this needs re-running, it's
starting from a clean slate now, not the previously-populated state.

### Tooling and standing docs available going forward

- `QC Test Harness/` — reusable known-ground-truth pipeline test.
- `requirements.txt` / `requirements-dev.txt` / `pyproject.toml` — new
  this session. Runtime deps currently empty; `ruff` configured
  pyflakes-only, deliberately conservative for a never-linted codebase.
- `oc_session_dump.py` — reads OC's raw session data directly (see
  `OC_Session_Access_Procedure.md`).
- `Audits/OC_Reliability_Log.md` — the evidence-based OC track record,
  now 20 tasks deep.
- `Audits/Trigger_Log/` — every trigger decision this session
  (TASK 14–20) logged individually; the self-check added to `CLAUDE.md`
  should keep this from lapsing again.
- `WORKING_LIST.md` — the living queue; check here first every session.
- `ARTIFACT_CONTRACT_TRACE.md` (see §15 below) — real, on-disk artifact
  examples for every pipeline stage; **stale as of this session** — the
  source_type/origin changes likely shifted some of these examples;
  refresh before trusting it blindly.
- **`C:\AI Development Projects\Corpus change study\`** — the
  deterministic-parser scoping work, outside this repo. Start at
  `00_INDEX.md`. Still nothing built toward it as of this session's end.

---

## 15. Live Artifact Contract Trace (read-only grounding practice)

Established 2026-08-05. Reading schema code (§8) and prior sessions' self-
reported findings gives an *abstract* picture of the pipeline's artifact
contracts — it doesn't confirm what a real instance of each artifact
actually looks like right now. This practice closes that gap without
spending anything: a full real artifact chain (Source Registry → Source
Package → Cleaning Job → Cleaning Result → parser response → canonical
JSONL) is already sitting on disk in the Workspace folder for both the QC
Test Harness fixture and real production sources (e.g. `cijapanese`).
Advisor can read straight through this chain end to end as a pure Read
action — zero new writes, zero new API cost, no conflict with any
concurrent OC session (different directory tree entirely).

**The living reference file:** `ARTIFACT_CONTRACT_TRACE.md` (repo root).
Holds one concrete, currently-verified example of each artifact stage,
captured directly from disk — not reconstructed from schema docs — each
entry dated and citing which real `source_id` it was pulled from.

**Update trigger:** refresh this file whenever a pipeline-stage program
changes in a way that could alter an artifact's actual shape (Source
Intake writers, a cleaner, Job Builder, Request Builder, the parser
prompt, `response_validator.py`, `corpus_builder.py`). Re-pull a fresh
real example after the change lands and is verified, and replace the
relevant section. Since this is read-only, it doesn't require the
write-access ask that other Advisor actions would — but the *file* being
updated (`ARTIFACT_CONTRACT_TRACE.md` itself) is a normal write and still
follows Advisor's usual rules for that.
