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

## 14. Session Wrap-Up (2026-08-06) — Updated after Session 4

**Read this section first, always — it's kept current at every wrap-up,
not appended to indefinitely.** This update supersedes the "Session 3"
version. If anything below conflicts with an older section elsewhere in
this file, this section wins — it was last refreshed 2026-08-06, end of
session 4.

### Relocation is DONE — repo now lives at the new path

**This session's whole scope.** The plan at
`C:\AI Development Projects\Corpus change study\2026-08-06_relocation_plan.md`
was executed in full and verified step by step, not just self-reported:

1. **Pre-flight** — `JPROGRAM_WORKSPACE` set (User env var) to
   `C:\Jprogram Workspace` *before* the folder moved. Verified directly
   against the real persistent store both before (empty) and after
   (correct value) via `[System.Environment]::GetEnvironmentVariable(...)`,
   and the app was confirmed showing real existing data (Recent Sources,
   templates) with the override active.
2. **Close + move** — done by Owner. Confirmed on disk from two
   independent shells (Bash and PowerShell): `C:\Jprogram` no longer
   exists; `C:\AI Development Projects\Jprogram` exists with `.git` and
   the full tree intact.
3. **Code/config fixes** (done by Advisor directly — Owner's explicit
   one-off exception to the standing Advisor/OC boundary, see below):
   - `oc_session_dump.py`: `JPROGRAM_WORKTREE` is now computed from the
     file's own location (`Path(__file__).resolve().parent`) instead of
     hardcoded — a future move won't need this touched again.
   - `.claude/settings.json`: the one absolute-path permission entry
     updated.
4. **Living docs updated**: `PROJECT_STATUS.md`, `ARCHITECTURE_CURRENT.md`,
   `ANALYZER_ARCHITECTURE.md`, `WORKING_LIST.md`,
   `OC_Session_Access_Procedure.md` (in-repo), plus
   `ECOSYSTEM_OVERVIEW.md` (sibling repo). Deliberately left unchanged:
   `JPROGRAM_SESSION_BOOTSTRAP.md`'s and
   `AI_Coding_Environment_Design_Spec.md`'s only matches were historical
   incident narrative, accurate to when written — rewriting those to the
   new path would have made them factually wrong about the past.
   `LANGZ_SESSION_BOOTSTRAP.md` also left alone — its mention is about
   Claude Code's own working-directory history, not Jprogram's location.
5. **Validated**: `verify_paths()` passes and resolves the real
   `WORKSPACE_ROOT`; all 64 `test_*.py` files pass (checked actual
   PASS/FAIL text, not just exit codes); `git status` showed exactly the
   7 files touched, nothing unexpected; `git log` intact, still 4 commits
   ahead of `origin/master`.
6. **Owner's own environment — investigated, mostly nothing to do**:
   - Desktop shortcut: doesn't exist. Checked the real (OneDrive-
     redirected) Desktop and every `.lnk` there by actual target path,
     not filename — none point at Jprogram. The plan's assumption about
     an existing shortcut didn't match reality.
   - Shell aliases/profile scripts: none exist (`$PROFILE` absent, no
     `.bashrc`/`.bash_profile`/`.profile`). Nothing to fix.
   - OpenCode desktop's working directory: found its per-workspace state
     file (`opencode.workspace.C--Jprogram.*.dat` under
     `%APPDATA%\ai.opencode.desktop\`), but it's an opaque JSON format
     keyed by a hash of the old path — not something safe to hand-edit.
     **Still open, Owner action**: next time OC opens, point it at
     `C:\AI Development Projects\Jprogram` directly; it will create a
     fresh, correctly-keyed entry on its own.

**Not yet done: nothing committed.** The 7 touched files
(`oc_session_dump.py`, `.claude/settings.json`, and the 5 in-repo docs)
are sitting as uncommitted working-tree changes. Advisor deliberately did
not commit without an explicit ask — see "Next immediate task" below.

### Read the two Session-2 audit reports before assuming anything about project state

Unchanged pointer, still current:
- **`Audits/2026-08-05/DEEP_AUDIT_REPORT.md`** — behavioral/documentation
  audit, 800/800 tests repo-wide, Frozen Components untouched across the
  entire git history at that time.
- **`Audits/2026-08-05/CODE_QUALITY_AUDIT.md`** — code-level review
  against the project's own stated principles. Its two headline findings
  were resolved in Session 3.

### Current phase

Relocation complete and verified. Still **13 Coder tasks** logged (no new
Coder tasks this session — every edit this session was a direct Advisor
edit under Owner's one-off authorization, not an OC task), see
`Audits/OC_Reliability_Log.md` for full per-task detail. `master` remains
the intentionally mothballed reference for the current (DeepSeek-based)
architecture, now sitting at the new path with 7 uncommitted relocation-
fix files on top of it. Per the original agreed sequencing, the
deterministic-parser work (Corpus Change Study) is the next major
project, on a new branch — not started yet.

### Last several decisions and why

- **Advisor made this session's code/doc edits directly, as an explicit
  one-off exception** to the standing Advisor/OC boundary
  (`feedback_advisor_implementation_boundary`) — Owner authorized this
  specifically for the relocation's mechanical path-string updates, not
  as a general precedent. Route future product-file changes through OC
  as usual.
- **OpenCode's per-workspace state file was deliberately left untouched**
  rather than hand-edited — its format is undocumented/opaque (hash-keyed
  JSON), and the correct fix (opening OC pointed at the new folder)
  achieves the same result without risking corrupting app-internal state
  Advisor doesn't fully understand. Consistent with "verify over trust" —
  don't act on state you can't confirm the shape of.
- **Relocation changes were verified independently at each step**, not
  accepted from either tool self-report or assumption — the env var via a
  direct persistent-store read (twice), the move via two separate shells
  agreeing, the app's real-data read via Owner's own screenshot, the
  tests via actual PASS/FAIL text. No step was taken on trust alone.
- **Commit deliberately deferred** — 7 files modified, nothing staged or
  committed. This wasn't asked for as part of "wrap up," and committing
  is an explicit-permission action; Owner should decide whether these
  land on `master` (most likely, since they're maintenance on the current
  architecture, not new-branch work) before the next branch gets cut.
- **The recurring identity/file-coupling pattern's 5th instance (from
  Session 3) is now resolved**, not just tracked — the
  `JPROGRAM_WORKSPACE` pre-flight step worked exactly as designed.

### Open risks / unresolved questions

Full detail in `WORKING_LIST.md` — this is a pointer, not a duplicate.
Headline items still open:

- **The Corpus Change Study work** — the big one. No longer blocked
  (relocation is done) but still deliberately not started. Start at
  `C:\AI Development Projects\Corpus change study\00_INDEX.md`.
- **Uncommitted relocation-fix changes** (this session) — 7 files, needs
  an explicit commit decision from Owner.
- **A real DeepSeek API key in plaintext**, found in
  `.claude/settings.local.json` (git-ignored, not tracked, but still live
  on disk) — flagged in the relocation plan's own "separate finding," not
  yet rotated. Carrying this forward explicitly so it doesn't get lost.
- **OpenCode desktop still pointed at the old folder** — Owner action,
  see step 6 above.
- **GUI terminology fix** — the standalone/series/site-collection
  three-way split doesn't exist anywhere yet; scoped but not built.
- **`sentence_index` "no gaps" not validated** — deliberately deferred
  (Session 3), zero current functional impact confirmed. Revisit if
  something ever starts reading `sentence_index` directly.
- **Two dead methods in `gui.py`** (`_on_source_type_selected`/
  `_on_origin_selected` from TASK 12) — queued into the next task that
  touches `gui.py`, not standalone.
- **From the Session-2 code quality audit, still open**: the dead
  duplicate branch in `production_manager.py`'s state machine; the
  duplicated silent-fallback-to-zero pattern in two files
  (`corpus_builder.py`'s `response_path_for()`,
  `deepseek_client.py`'s `job_number_from_request()`); two unused write
  helpers (`write_jsonl_record`, `output_writer.py`).
- **API key structure/utility design** — not started.
- **Remaining live-testing GUI backlog** — embedded-tabs restructure,
  import defaults, Analysis multi-file, Template Editor pass, the
  Tkinter-error report still blocked on Owner pasting a traceback,
  Import Material default-format GUI fix — see `WORKING_LIST.md`.

### Next immediate task

Two open decisions, neither a hard blocker on the other:
1. **Commit the 7 relocation-fix files** — Owner's call on whether these
   land on `master` (this bootstrap doc's read: yes, since they're
   maintenance on the current architecture, not new-branch work).
2. **Create the new branch for the deterministic-parser work**, per the
   original sequencing — now unblocked. Start from
   `C:\AI Development Projects\Corpus change study\00_INDEX.md`.

If Owner instead wants to pick something off `WORKING_LIST.md` first,
that's fine too.

### Real-data validation status

Unchanged: done once, successfully, via `QC Test Harness/`. See
`QC Test Harness/README.md` for reuse instructions.

### Tooling and standing docs available going forward

- `QC Test Harness/` — reusable known-ground-truth pipeline test.
- `oc_session_dump.py` — reads OC's raw session data directly (see
  `OC_Session_Access_Procedure.md`). Fixed this session — worktree path
  now computed dynamically, no longer hardcoded.
- `Audits/OC_Reliability_Log.md` — the evidence-based OC track record,
  13 tasks deep, ten consecutive clean-or-clean-with-notes results.
- `WORKING_LIST.md` — the living queue; check here first every session.
- `ARTIFACT_CONTRACT_TRACE.md` (see §15 below) — real, on-disk artifact
  examples for every pipeline stage; last refreshed post-TASK-8.
- `Audits/2026-08-05/DEEP_AUDIT_REPORT.md` and `CODE_QUALITY_AUDIT.md`
  — Session 2's two audits; still current, read before assuming project
  state.
- **`C:\AI Development Projects\Corpus change study\`** — the
  deterministic-parser scoping work, outside this repo. Start at
  `00_INDEX.md`. Read before starting that work.

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
