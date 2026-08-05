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

**Tests:** Source Intake suite — **106 tests passing**.

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

## 14. Session Wrap-Up (2026-08-05) — First Advisor-CC Session, Complete

The §10 checklist above is **fully complete** — all 6 steps done, verified
against raw evidence throughout, not self-report. This session went well
beyond the checklist into real feature work; this section is the actual
"start here" for whoever picks this up next.

### Current phase

Past initial setup/audit, now doing real implementation work through the
Advisor→Coder loop with active verification. 4 Coder tasks completed and
independently verified (raw `git status`/`git diff`, direct test re-runs,
not self-report) — see `Audits/OC_Reliability_Log.md` for the full,
evidence-based history: TASK 1 (test-isolation fix) clean, TASK 2
(read-only audit) clean, TASK 3 (sequencing field, part of a 3-part
assignment) **a genuine discrepancy** — only 1 of 3 parts delivered, not
flagged — TASK 4 (the remaining 2 parts, after `AGENTS.md` was
strengthened to require explicit per-part reporting) clean again. Don't
read the TASK 3 discrepancy as "OC is unreliable" — read the TASK
1→2→3→4 sequence as the actual evidence: verification caught a real gap,
a process fix was made, and the very next task in the same family came
back clean. Keep verifying every task regardless — that pattern is early,
not proven.

### Last several decisions and why

- **Non-episodic collection sequencing backend is fully implemented**
  (`sequencing` field, `next_auto_sequence()`, the `processing_tab.py`
  sort-key fix) — because Owner has real ~800-item non-episodic
  collections (CI Japanese) that the original episode=0 proposal would
  have collided on (confirmed via code before any fix was designed).
  GUI wiring is the explicit next step, not yet started.
- **Section markers confirmed as legacy, not a gap** — because the old
  batch-acquisition workflow that motivated them (paste ~20 episodes into
  one file for cheaper bulk chatbot processing) no longer exists under
  the current one-source-per-file model. Avoided building real
  marker-to-boundary logic for something that will never receive input
  again.
- **Qwen Code authentication is on indefinite hold** — Owner's explicit
  call, not a technical blocker; do not propose revisiting unprompted
  (see §10 step 3, and memory).
- **A recurring architectural pattern was named**: identity/config
  getting coupled to raw file structure instead of the token/source_id
  abstraction (3 known instances — the historical "con_teppei" ghost tag,
  the episode=0 collision risk, and the Metadata Editor's still-live
  `PROCESSING_PROFILES` validation gap that let `cij_transcript` get
  configured with no working cleaner behind it). Worth checking for this
  shape of mistake whenever raw file content/structure seems like it
  should inform identity going forward.

### Open risks / unresolved questions

All granular detail lives in `WORKING_LIST.md` (kept continuously updated
and committed throughout this session, not saved for one big handoff) —
this is a pointer, not a duplicate. Headline items:

- **GUI wiring for the sequencing feature** — Metadata Editor combobox,
  `gui.py` conditional field visibility, save-flow branch. Next natural
  Coder task for this thread.
- **GUI terminology fix** — the standalone/series/site-collection
  three-way split doesn't exist anywhere yet (today's radio buttons are
  only a two-way collection/standalone split); scoped but not built.
- **Metadata Editor validation gap** — `validate_collection()`/
  `validate_source_type()` never cross-check against `PROCESSING_PROFILES`,
  confirmed still live (real data: `cijapanese` collection is currently
  configured with the non-processable `cij_transcript`). Related to but
  separate from the sequencing field work.
- **Hash verification computed but never enforced downstream** — a real
  chain-of-custody gap (sha256/output_hash recorded but never read back
  and checked), scoped as two small deterministic fixes, not yet actioned.
- **Live-testing GUI bug backlog** — cancel button, status indicator,
  redundant Analysis button, embedded-tabs restructure, import defaults,
  and others — see `WORKING_LIST.md`'s "Live testing issues" section.
- **`sentence_index` "no gaps" not validated** — small, deterministic,
  scoped, not yet actioned.
- **API key structure/utility design** — not started.

### Next immediate task

Owner's call on sequencing — either continue that thread (GUI wiring,
now that the backend is fully done and verified) or pick something else
from `WORKING_LIST.md`. No hard dependency forcing one over the other.

### Real-data validation status

No longer just "next" — done once, successfully. `QC Test Harness/` ran a
hand-authored source through the full real pipeline including a real
DeepSeek API call, and every ground-truth check passed (see
`WORKING_LIST.md`'s Resolved section, and `QC Test Harness/README.md` for
reuse instructions). Confirms the pipeline works end-to-end in practice,
not just in code review — though it's one synthetic test, not broad
real-world coverage yet.

### Tooling built this session, available going forward

- `QC Test Harness/` — reusable known-ground-truth pipeline test.
- `oc_session_dump.py` — reads OC's raw session data directly; use this,
  don't hand-roll the query again (see `OC_Session_Access_Procedure.md`).
- `Audits/OC_Reliability_Log.md` — the evidence-based OC track record.
- `WORKING_LIST.md` — the living queue; check here first every session.

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
