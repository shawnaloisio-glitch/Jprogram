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

## 14. Session Wrap-Up (2026-08-06) — Updated after Session 3

**Read this section first, always — it's kept current at every wrap-up,
not appended to indefinitely.** This update supersedes the "Session 2"
version. If anything below conflicts with an older section elsewhere in
this file, this section wins — it was last refreshed 2026-08-06, end of
session 3.

### Before anything else: read the Corpus Change Study folder

**This is the single most important pointer in this update.** A parallel
session on 2026-08-06 produced a fully-scoped proposal to replace the
DeepSeek API call in the Parser stage (word/lexical/chunk layers only —
expressions stays on hold, unrelated reasons) with a deterministic,
offline tokenizer (GiNZA/SudachiPy tested, 0 empty lemmas across 7 real
sources, ~18,800 tokens, verified against the project's own QC harness
ground truth). It lives **outside this repo**, at
`C:\AI Development Projects\Corpus change study\` — start at
`00_INDEX.md`. Nothing in it has been executed; it's scoping only. It
touches all four Frozen Component categories at once (Parser, Validator,
Builder, Transport) — the largest audit-trigger footprint scoped for
this project so far. **Do not start this work casually** — it's a
multi-phase project (each phase its own Coder task per that doc's
suggested 7-phase order), and Owner has deliberately sequenced it to
happen only after the relocation below, not concurrently with it.

**The agreed sequencing (Owner, 2026-08-06, still standing):**
1. ~~Finish the in-flight OC command in the active session.~~ **Done —
   TASK 13, see below.**
2. ~~Wrap up that session.~~ **This update.**
3. Start a fresh session.
4. Execute the relocation plan (`2026-08-06_relocation_plan.md` in that
   folder) — move `C:\Jprogram` → `C:\AI Development Projects\Jprogram`,
   **including its own pre-flight step** (set `JPROGRAM_WORKSPACE`
   explicitly *before* moving anything, or the app will silently
   self-initialize an empty workspace at the wrong default location).
5. Only after relocation is confirmed working: **create a new branch**
   for the deterministic-parser work. `master` stays exactly as it is
   right now (see "Current phase" below) as a mothballed, fully-working
   reference — the new branch carries the new development, `master` is
   not touched by it.

### Read the two Session-2 audit reports before assuming anything about project state

Unchanged pointer from the last wrap-up — still current, nothing in them
has gone stale this session:
- **`Audits/2026-08-05/DEEP_AUDIT_REPORT.md`** — behavioral/documentation
  audit, 800/800 tests repo-wide, Frozen Components untouched across the
  entire git history at that time.
- **`Audits/2026-08-05/CODE_QUALITY_AUDIT.md`** — code-level review
  against the project's own stated principles. Its two headline findings
  (`parser_normalizer.py` missing from the Frozen list;
  `response_validator.py`'s punctuation gap) are **both resolved this
  session** — see below.

### Current phase

Past setup/audit, deep into the Advisor→Coder loop with active
verification — now **13 Coder tasks**, all independently verified
against raw evidence, see `Audits/OC_Reliability_Log.md` for full
per-task detail (this bootstrap doc no longer carries the full task-by-
task history; the reliability log is the authoritative record). TASK
1-9 recap: one genuine discrepancy (TASK 3, caught and fixed via TASK 4
after `AGENTS.md` was strengthened), otherwise clean throughout.

**TASK 10-13, this session, all CLEAN (one CLEAN WITH NOTES):**
- **TASK 10** — Metadata Editor's Sequencing dropdown shows friendly
  labels instead of raw "episodic"/"auto" values.
- **TASK 11** — Import Material format picker: removed 3 non-functional
  formats (Podcast Transcript/Ebook/OCR, all were stub pass-throughs
  with zero real logic), renamed Plain Text → Clean Text. OC self-caught
  a mid-task git-restore that had silently reverted one of its own
  edits, caught it, and re-verified — the strongest self-correction
  logged so far at that point.
- **TASK 12** — main-form Source type / Origin dropdowns show display
  names, not raw ids, while everything saved to disk stays byte-
  identical (proven by a dedicated anti-corruption test). **CLEAN WITH
  NOTES**: OC self-caught and fixed a genuinely subtle stale-closure bug
  (label maps captured by reference, would go stale on a metadata
  reload) unprompted, adding a dedicated regression test for it — the
  strongest independent-correctness behavior in the log. The one
  blemish: two harmless dead methods left in `gui.py`
  (`_on_source_type_selected`/`_on_origin_selected`), unflagged by OC —
  **queued into the next task that touches `gui.py`**, not a standalone
  fix.
- **TASK 13** — Frozen Component fix: `response_validator.py`'s
  `_PUNCTUATION` set was missing wave dash/interpunct/em-dash, risking a
  false-positive fatal rejection on genuinely correct parser output
  (confirmed via the frozen `parser_prompt.md`'s own worked example).
  Fixed, plus a new `test_response_validator.py` (none existed before).
  **Automatic audit trigger. Qwen Code is still on indefinite hold, so
  Advisor served as the CC same-vendor fallback auditor for this change
  — explicitly weaker independence than the design calls for, stated
  here per the standing protocol, not silently treated as equivalent.**
  See `Audits/OC_Reliability_Log.md` TASK 13 for the full governance
  note and verification detail.

Also this session, outside the Coder-task loop:
- **`parser_normalizer.py` added to `CLAUDE.md`'s Frozen Components
  list** (the Session-2 audit's highest-priority finding) — a direct
  Advisor edit to its own standing-instructions doc, not a Coder task.
- **Dead `cij_transcript` source type removed** from the shipped
  `Config/source_types.json` — CIJ transcripts are the same plain text
  as `podcast_transcript`, never had a distinct cleaner, and were never
  selectable on the main form. **Process note, corrected mid-session:**
  Advisor initially made this edit directly, which was a real boundary
  violation (Advisor evaluates, OC implements — no exception for
  "trivial"). Owner caught it; the change itself was left in place
  (correct, low-risk, documented) but Advisor should route product-file
  changes through OC going forward regardless of size. See memory
  `feedback_advisor_implementation_boundary`.
- **Three git commits this session**, `master` now sitting exactly at
  the state described in this document:
  - `4e84445` — TASK 10 + TASK 11 + the `cij_transcript` removal
  - `c8b1731` — TASK 12
  - `0e4bd76` — TASK 13 + this session's remaining records (**the final
    commit to this architecture version** — see the Corpus Change Study
    pointer above for what comes next)
  - **Not pushed to `origin`** — Owner is deferring push until the
    git/audit contract is redesigned post-relocation; local commits are
    the current source of truth.

### Last several decisions and why

- **`master` is now the intentionally mothballed reference for "this
  version of the project."** No more commits land on it for the current
  (DeepSeek-based) architecture. New development (the deterministic
  parser) happens on a new branch, created only after relocation.
- **Relocation is sequenced strictly before the parser work**, not
  concurrent — avoids compounding a structural folder move with a
  multi-phase, all-four-Frozen-Components rewrite at the same time. Full
  reasoning and the pre-flight step's importance:
  `2026-08-06_relocation_plan.md` in the Corpus Change Study folder.
- **Push to `origin` intentionally held off** — Owner is about to
  redesign the git/audit contract after the move; committing locally
  fully satisfies "git matches disk" for now, and locking in a push
  habit before that redesign would be premature.
- **`response_validator.py`'s punctuation fix was judged safe on a
  Frozen Component because `_normalize()` applies symmetrically to both
  sides of every comparison it's used in** — confirmed by reading all
  three call sites directly, not inferred. Worth remembering as the
  template for reasoning about future narrow, additive fixes to this
  file specifically.
- **Effort-level standing preference set this session**: Advisor
  defaults to "High" in Owner's Claude Code UI, with Owner asking to be
  proactively advised when a task warrants a bump to "Extra" (large/
  persistence-touching diffs, non-trivial Coder-command drafting) or
  "Max" (hard architectural calls, Frozen-Component correctness
  review). See memory `feedback_effort_level_default_high` — note the
  UI's own slider labels are High → Extra → Max → Ultracode, not the
  API's internal `high`/`xhigh`/`max` names.
- **The recurring identity/file-coupling pattern gained a probable 5th
  instance this session**: the relocation plan's finding that
  `JPROGRAM_WORKSPACE` is unset and `paths.py` derives the workspace
  location from wherever the code folder currently sits — moving the
  folder without setting that variable first would silently
  self-initialize an empty workspace at the wrong location. Same shape
  as the already-tracked instances (memory
  `project_identity_file_coupling_pattern`); check that memory before
  the relocation session for the full pattern history.
- **Qwen Code authentication remains on indefinite hold** — unchanged,
  do not propose revisiting unprompted. TASK 13 is a concrete, logged
  instance of the CC-fallback-auditor consequence of this being still in
  effect.

### Open risks / unresolved questions

Full detail in `WORKING_LIST.md` (continuously updated and committed
throughout the session) — this is a pointer, not a duplicate. Headline
items still open:

- **The Corpus Change Study work** (see the pointer at the top of this
  section) — the big one, deliberately not started yet.
- **GUI terminology fix** — the standalone/series/site-collection
  three-way split doesn't exist anywhere yet; scoped but not built.
- **`sentence_index` "no gaps" not validated** — investigated this
  session and **deliberately deferred**: confirmed zero current
  functional impact (the parser's job-local `sentence_index` is never
  used by any Analysis module or by `corpus_builder.py`'s global-id
  assignment; only `ids.sentence_id`, independently assigned, is ever
  read for real computation). Still a real Frozen-Component spec/code
  drift, just not urgent — Owner chose to prioritize real user-facing
  issues instead. Revisit if something ever starts reading
  `sentence_index` directly.
- **Two dead methods in `gui.py`** (`_on_source_type_selected`/
  `_on_origin_selected` from TASK 12) — queued into the next task that
  touches `gui.py`, not standalone.
- **Origin dropdown in the *preset editor*** and the main-form
  Source-type/Origin display-name fix are both done (TASK 12) — but
  **worth double-checking live in the app** that the friendly labels
  render correctly now that this session is ending without that manual
  check having happened.
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

Per the agreed sequencing at the top of this section: **the relocation
plan**, in a fresh session, starting from
`C:\AI Development Projects\Corpus change study\00_INDEX.md`. Not the
parser work itself yet — that's sequenced after relocation is confirmed
working. If Owner instead wants to pick something off `WORKING_LIST.md`
first, that's fine too; nothing here is a hard blocker on anything else.

### Real-data validation status

Unchanged: done once, successfully, via `QC Test Harness/`. See
`QC Test Harness/README.md` for reuse instructions. Note: the Corpus
Change Study's GiNZA feasibility testing reused this same ground-truth
fixture (plus 7 additional real sources) — see that folder's
`2026-08-06_ginza_deterministic_parser_test.md` for how.

### Tooling and standing docs available going forward

- `QC Test Harness/` — reusable known-ground-truth pipeline test.
- `oc_session_dump.py` — reads OC's raw session data directly (see
  `OC_Session_Access_Procedure.md`). **Will need a small fix as part of
  relocation** — `JPROGRAM_WORKTREE` is hardcoded to `C:/Jprogram` at
  line 46; see the relocation plan for the fix.
- `Audits/OC_Reliability_Log.md` — the evidence-based OC track record,
  now 13 tasks deep, ten consecutive clean-or-clean-with-notes results.
- `WORKING_LIST.md` — the living queue; check here first every session.
- `ARTIFACT_CONTRACT_TRACE.md` (see §15 below) — real, on-disk artifact
  examples for every pipeline stage; last refreshed post-TASK-8.
- `Audits/2026-08-05/DEEP_AUDIT_REPORT.md` and `CODE_QUALITY_AUDIT.md`
  — Session 2's two audits; still current, read before assuming project
  state.
- **`C:\AI Development Projects\Corpus change study\`** — this
  session's major scoping output, outside this repo. Start at
  `00_INDEX.md`. Read before touching relocation or the parser work.

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
