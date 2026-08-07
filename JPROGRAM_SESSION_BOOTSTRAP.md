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

## 14. Session Wrap-Up (2026-08-07) — Updated after Session 10

**Read this section first, always — it's kept current at every wrap-up,
not appended to indefinitely.** This update supersedes the "Session 9"
version (dropped entirely — the season/episode redesign it scoped as
"next immediate task" got fully built, audited, and shipped this session,
so that narrative is obsolete; git history and `Audits/Trigger_Log/` hold
the detail if ever needed). If anything below conflicts with an older
section elsewhere in this file, this section wins — last refreshed
2026-08-07, end of session 10.

### Current phase — the season/episode identity redesign shipped, audited clean, and pushed

Two commits on `master`, both independently evaluated against raw diffs
and full-suite test runs, then given a genuinely fresh-subagent Auditor
pass before push (no cross-vendor auditor available, per standing
decision):
- `f482aaa` — data layer: episode becomes a hidden, always-auto-incrementing
  system identifier (reuses the existing `next_auto_sequence` mechanism
  unchanged); the per-collection episodic/auto sequencing choice is retired
  entirely (`SEQUENCING_VALUES`, the config field, the GUI dropdown all
  removed); Source Package schema bumps v3→v4 to add two new, fully
  optional, purely cosmetic fields — `episode_number`/`season_number` —
  with zero identity or uniqueness role.
- `f53990f` — GUI layer: the Episode field is now unconditionally hidden
  for every collection (no more visibility branching); a user-typed episode
  value is never honored (this closes a real gap the first commit alone
  left open — confirmed by test before the fix, a typed `63` produced
  `ep001`); Episode#/Season# added to the form (Episode# suggests
  previous+1 after each save, Season# is retained unchanged, both start at
  `"1"` on a fresh session, neither is per-collection).

Auditor's findings: both commits do exactly what they claim, 65/66 tests
pass (the one failure is the deliberately deferred `Index/index_builder.py`
sequencing-column gap — see `WORKING_LIST.md`), scope discipline clean on
both commits, no Frozen Component touched. Two trivial follow-ups now
tracked in `WORKING_LIST.md`: `controller.py`'s `collision_exists()` is
dead code, and `diagnostics.py` has one stale episode-only reference.
Pushed to `origin/master` same session.

### Real process lesson from this session

**A background OC session was not actually stopped by two different
methods in a row — closing its tab, then its own in-app Stop control —
each time causing a real file race against a freshly-dispatched session
on the same files.** Both incidents were caught (the second only because
a system-level file-change reminder surfaced unexpected content) and the
working tree was manually reconciled — via `git checkout` back to a known
commit plus hand-reapplication of an already-evaluated diff, verified
byte-identical before re-committing — before anything was trusted enough
to commit. New standing memory:
`feedback_oc_session_stop_unreliable.md` — verify via Windows Task
Manager, not the app's own stop/close controls, before trusting the
working tree after any "I stopped it" report.

### Branch-divergence check (per `CLAUDE.md`'s standing wrap-up rule)

`git branch -a` shows only `master` (local and remote) — no other
branches exist. Nothing to flag.

### Next immediate task

**The Cleaner bug (see previous update) is now fully scoped — a Coder
command is drafted and ready to run, not yet dispatched.** Confirmed
during scoping that the same bug independently occurs in Subtitle
Importer's cleaner too (a real SRT import hit it, cue #93), which is why
the fix extracts the shared splitting rule into a new `Common/
sentence_split.py` utility rather than patching one Cleaner alone. Run
the drafted command next session, evaluate the diff + full test suite as
usual, then a fresh-subagent Auditor pass before considering it landed
(judgment-call Yes — touches `deterministic_parser.py`, the live parser
stage, even though it's a pure behavior-preserving extraction).

Also shipped this session, small and already committed: `processing_tab.py`'s
`human_label()` renamed its "Episode <N>" text to "ID#<N>" — Owner caught
in real usage that the label implied it reflected the new Episode#/Season#
fields when it's actually the unrelated hidden system counter. Pure
display-text change, zero behavior change, 6 files (`1665cfc`).

Two one-off hand-fixes also landed this session as immediate unblocks
(data fixes, not code — see `WORKING_LIST.md` for exact files): the
`teppeibeginner_ep0002` canonical source and the raw `Seika's Day Out.srt`,
both had the real bug pattern manually split so at least one clean run
could get through meanwhile.

The three small episode/season follow-ups (Index's sequencing column,
`collision_exists()` cleanup, `diagnostics.py`'s stale reference) remain
open too, still none urgent.

**Not yet pushed to `origin`:** two local commits (`1665cfc`, `348adf0`)
ahead of `origin/master` as of this update — push at the start of next
session if not already done. `Config/styles.json` also has an uncommitted
real data change (a "Podcast-Monologue" style added through the app during
testing) — Owner's own data, left uncommitted intentionally, not part of
any task.
Processing tab's fate (removed vs. kept as a simpler status panel, now
that the deterministic parser doesn't need DeepSeek-era rate scheduling)
is still open and undecided, raised but deliberately not resolved this
session. Everything else carried forward unchanged from Session 9's list
(Domain/Topic still loose, the SQLite index still unwired, Import
Material's folder default not type-specific, Material Level's admin
surface undecided, the Session 7 backlog) — see `WORKING_LIST.md` and git
history directly rather than trusting a stale summary here.

---

## 14a. Prior wrap-up (Session 9) — kept for reference only, superseded above

### Current phase — the data-management architecture from Session 8 got built, shipped, and the two long-diverged branches got reconciled

Session 8 was thinking-only; session 9 built almost all of it and closed
a real, multi-session architectural gap. Headline: **`master` and the
long-separate `deterministic-parser` branch are reconciled** — the real
GiNZA/spaCy parser is now the live "api" stage (confirmed directly:
`Production Manager/production_manager.py`'s `_api_script()` returns
`deterministic_parser_client.py`, not `deepseek_client.py`). Both
`deterministic-parser` and the intermediate `flat-source-storage`/
`reconcile-deterministic-parser` branches are merged and deleted, locally
and on `origin`. Only `master` exists now.

**What shipped, in order:**
1. **Flat Sources storage** — `Sources\collections\{id}\` nesting removed;
   everything keyed by filename only, matching the rest of the pipeline.
2. **SQLite index** (`Index\index_builder.py`) — disposable, rebuildable
   cache over Source Package + config data. CLI-only, unwired to any
   pipeline stage (that's still true — no auto-rebuild trigger exists).
3. **Material Level / Style / Duration** — new per-source metadata.
   Backend (`source_package.py` schema v2→v3, `controller.py`'s
   `ReadyStateEngine`, Style CRUD) built once, then **silently dropped**
   when the branch reconciliation took `gui.py`/`metadata_editor_gui.py`
   wholesale from `deterministic-parser` — caught by a fresh Auditor
   subagent pass, not by Advisor's own review, then re-applied against
   the post-reconciliation file structure (not a restore of the old
   commit — Source Type had been removed in the meantime, Origin's row
   position had moved). Now genuinely working end to end.
4. **`deterministic-parser` reconciled into `master`** — real conflicts,
   hand-resolved (see the two Auditor-reviewed commits). Source Type is
   now fully invisible, hardcoded to `"clean_text"` (only valid value).
   `origins.json` moved from repo-root product config to workspace
   config as part of that branch's own prior work.
5. **`origin` renamed to `creator`** throughout — same meaning, same
   mechanism, just a clearer name (the field mixes creator/channel/
   acquisition-method under one vague word; renaming didn't fix that
   ambiguity, just made the label honest). `Config/creators.json`,
   schema bumped to v3 again for the field-name change.

**Verification discipline held throughout:** every OC task this session
was independently re-verified against raw diffs and from-scratch test
re-runs (never accepted on self-report), and the branch reconciliation
got a genuine fresh-subagent Auditor pass before merging to `master` —
which is *how* the dropped GUI work got caught. See
`Audits/Trigger_Log/2026-08-07_reconcile-deterministic-parser_auditor_pass.md`
for that report in full.

### Real process lesson from this session, now a standing rule

Two branches (`deterministic-parser`, then `flat-source-storage`) sat
unreconciled across multiple sessions, diverging far enough (~100 files)
that reconciling them took a full dedicated task with real risk. Owner's
own framing: "I can't know things I don't know and git management is a
not known [area]." Owner proposed replacing git branches with folder-
level backups; Advisor pushed back (backups can't diff, can't
selectively merge, can't prove byte-identity — they solve "recover from
disaster," not "notice two lines of work drifting apart") and Owner
agreed instead to a standing check: **`CLAUDE.md`'s "End of session /
handoff" section now requires a branch-divergence check every
wrap-up** — run `git branch -a`, flag anything besides `master` that's
diverging, unprompted. See memory `feedback_proactive_branch_tracking.md`.

### Last several decisions and why (this session)

- **UI dropped by the reconciliation got re-applied, not just restored** —
  the old commit (`b150f43`) was read as reference material only; the
  actual re-implementation was derived fresh against the current file
  structure, since Source Type's removal had moved surrounding code.
  Confirmed via diff that the re-applied mechanism (the `add_hidden_keys`
  pattern for Style's autoincrement id) matched the original exactly in
  shape, independently re-verified.
- **`origin` → `creator`, not `origin` + `domain/topic` merged** — Owner
  initially said "change origin to domain/topic," which Advisor flagged
  as contradicting an explicit 2026-08-06 decision (domain/topic must
  stay a *separate* tag from origin, to avoid repeating the
  `source_type`-collapse mistake). Owner clarified: not a merge, just
  frustration with `origin` as an unclear *name* for what it actually
  captures (creator/channel/acquisition-method). Domain/Topic remains
  fully deferred, untouched, not part of this rename.
- **Season/episode identity redesign — scoped in discussion, not yet
  built.** LC surfaced that Collections cover real series with seasons
  (TV shows, long-running anime), and the current single `episode` field
  is both the uniqueness key (baked into `source_id`/filename) and the
  human label — a real collision risk if within-season episode numbers
  reset per season. **Settled design (Owner's call, after Advisor laid
  out the tradeoff):** `episode` becomes a fully hidden, always
  auto-incrementing system ID (same mechanism "auto" sequencing already
  uses) — the user never sees or types it. Episode# and Season# become
  new, purely optional Source Package metadata fields (like Material
  Level/Style/Duration), carrying zero uniqueness responsibility, so any
  real-world numbering scheme (gaps, resets, whatever) is safe to enter.
  **Real consequence, confirmed via code read, not yet acted on:** this
  retires the entire "episodic vs auto" sequencing distinction —
  `SEQUENCING_VALUES`, the Collections tab's sequencing dropdown,
  `_is_auto_collection()`, the GUI's episode-field show/hide logic all
  become dead weight once every collection behaves the same way. Owner
  hasn't been asked to confirm that retirement specifically yet — surface
  it plainly when scoping the actual Coder command, don't just fold it in
  silently.
- **All current Workspace data is disposable — reaffirmed a second time**,
  now specifically in the context of identity/schema redesign (not just
  the original `source_type` collapse). No migration path needed for any
  of the above or upcoming season/episode work. See
  `project_dev_data_is_disposable.md`.

### Open risks / unresolved questions

- **Season/episode identity redesign — next immediate task, not started.**
  Design is settled (see above); needs a blast-radius investigation
  (`source_id.py`, `controller.py`'s `generate_filename`/`collision_exists`/
  `next_auto_sequence`, `metadata_editor.py`'s `SEQUENCING_VALUES`, the
  GUI's episode-field visibility logic) before drafting a Coder command,
  matching this project's standing "investigation before implementation"
  discipline. Explicitly confirm with Owner that retiring episodic/auto
  sequencing is wanted, not just inferred.
- **Domain/Topic** — still loose, not solidified, carried forward again
  (now for at least the third session running).
- **The SQLite index is still unwired** — CLI-only, nothing in the app
  triggers a rebuild automatically. Not urgent, just not forgotten.
- **Import Material's folder default isn't type-specific yet** — defaults
  to one generic `Raw Imports` folder (an improvement carried in from the
  `deterministic-parser` merge), not split by format
  (`Raw Subtitles`/`Raw Transcripts`) the way Owner originally asked
  during the post-reconciliation smoke test.
- **Material Level's own admin surface** — still undecided: a small
  Edit-only tab, or a hand-edited `project_config.py` constant. Low
  priority, expected to change close to never.
- Everything carried forward unchanged from Session 7 that Session 8/9
  didn't touch (the Language Reactor cleaner, the Phase 6 doc rewrite,
  12 deferred `ruff` findings, the `WORKING_LIST.md` GUI backlog) — see
  git history / `WORKING_LIST.md` directly rather than trusting a stale
  summary here.

### Next immediate task

Scope the season/episode identity redesign — start with the blast-radius
investigation named above, present findings, confirm the episodic/auto
retirement explicitly, then draft the Coder command. This is a genuine
identity-layer change (touches `source_id` generation and uniqueness),
similar in kind to the flat-storage rewrite earlier this session — same
discipline applies.

### Real-data validation status

Strongest it's been all session. The QC Test Harness ran the actual
end-to-end pipeline (setup → clean → jobs → requests → the real
deterministic parser → corpus) through the reconciled, then re-renamed
codebase and got a clean ground-truth PASS each time re-verified
(犬/猫/食べる exact matches). The SQLite index correctly reflects real
saved sources with the renamed `creator` field. No large-scale real-media
stress test happened this session (that was Session 7's 588,315-token
run against `D:\Natural Japanese media\`) — worth re-running once the
season/episode work lands, since the source_id shape is about to change
again.

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
