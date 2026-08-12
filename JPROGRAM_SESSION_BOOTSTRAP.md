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
  Raw source → cleaned data → parsed structured data → validated corpus → canonical JSONL corpus
  ```
- The project builds an immersion-oriented corpus that preserves raw linguistic evidence so later analyzers can compute frequency, distribution, exposure, and other measurements deterministically. **Jprogram's own scope ends at the finished canonical JSONL corpus (2026-08-09)** — the analyzers themselves now live in Language Coach, not here (see §14, "Major architecture decision").

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
```

Jprogram's pipeline ends here. Analysis (deterministic analyzer utilities
→ evidence datasets → interpretation) is now a separate project's
responsibility — Language Coach, which reads this corpus but is not part
of this repo. See §14's "Major architecture decision" entry.

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

## 15. Session Wrap-Up (2026-08-12) — Session 15 (Natural Japanese import attempt, cleaner fix, batch removal)

**Read this section first, always.** Supersedes the Session 14 version
below (kept for reference as §14). Written 2026-08-12, end of session 15,
at Owner's instruction: "Log everything you have found — we won't make any
changes until Claude is back up." **This session was run without the
Claude-side Advisor/auditor loop (Claude was down); nothing in this
session has been independently audited.** All findings below are the
working agent's own; Claude should review on return (see Audit trigger
entry at `Audits/Trigger_Log/2026-08-12_subtitle-cleaner-vtt-header-fix.md`).

### Current phase

Corpus is back to its exact pre-session state and clean: **384 JSONL /
46,421 sentences**, zero `X-TIMESTAMP-MAP` junk records, zero
`natural_japanese` sources. No decisions pending that require changes; the
next real task (parser-layer investigation, below) is awaiting Owner
authorization and is Frozen-Component territory.

### What happened this session (chronological)

1. **Thai batch deleted (Owner-confirmed pollution).** 1,300 `areeya2519`
   artifacts (100 Thai web-novel chapters) were removed from the Workspace
   (jsonl, Corpus/Processing/Job Results, Cleaning Jobs/Results, Cleaned
   Archive, Source Registry, jobs/, responses/, Logs). This was a separate
   ThaiCorpus project's output that had leaked into the Japanese corpus.
   Corpus went 484 → 384 JSONL (54,753 → 46,421 sentences). NOTE: this
   deletion was done under the same session's earlier standing process;
   Claude should treat it as part of the session record, not re-litigate.
2. **Natural Japanese import planned.** Source:
   `D:\Sourced Content\Japanese Import\Natural Japanese media\` (1,785
   subtitle files: 1,780 .vtt + 5 .srt; authoritative catalog
   `master.csv`, 1,777 rows). Exclusions decided (see WORKING_LIST entry):
   9 rows overlapping existing corpus sources, 9 duplicate rows (keep-
   first), 7 unreferenced files (5 .srt + 2 byte-identical `_`-dups) —
   net 1,759 files. Creator `natural_japanese` added to
   `Workspace/Config/creators.json` (Owner-authorized). Metadata spec:
   style_id 1 (Comprehensible Input), topic_id/episode/season null, duration
   null (fill later from audio/video), Teacher column unused.
3. **Import run (01:32–06:01, 4 × batch_importer.py, one per level).**
   1,759 sources created; **106 failed at the corpus-builder stage**
   (clean/jobs/parse all passed). Failure records:
   `Workspace/natural_japanese_import_failures.csv` (source_id, level,
   error, 106 rows) + `Workspace/natural_japanese_import.log`.
4. **Root cause #1 found and fixed (Owner-authorized cleaner change).**
   WebVTT `X-TIMESTAMP-MAP` header line survived cleaning → 106
   reconstruction failures at character 0; the other 1,651 "successful"
   JSONL carried the same junk line as a repeating record (frequency-skew
   hazard). Fixed `Subtitle Importer/cleaner.py` `VttParser`: skips the
   whole WebVTT header block (WEBVTT + all metadata lines up to first
   blank line, with cue-timestamp guard for malformed files) and skips
   in-text NOTE/STYLE blocks. 8 new unit tests; Subtitle Importer suite
   26/26; full repo sweep 66/69 (3 failures pre-existing: archived
   Analysis/Index tests + retired deepseek_client — verified identical on
   pre-change baseline).
5. **Test batch (8 files) revealed root cause #2 — parser-layer, NOT
   fixed.** With the header gone, `parser_normalizer.py`'s exact
   reconstruction fails on GiNZA word-surface mismatches the header was
   masking: `みです` (「３（み）」ですね), `くださいです`, `寂びです`, `せです`, `持つです`,
   `なさいです`, plus 2 files with "canonical sentence count N does not
   match record count M". These live in **Frozen Components**
   (`Data Processor/parser_normalizer.py` / `deterministic_parser.py`) —
   **NOT touched** (locked project). Whether all 106 share this issue is
   unknown (would require re-processing the remaining 98).
6. **Entire batch removed (Owner decision).** All 1,759 sources + all
   artifacts (incl. `Request Results/` — a directory the first cleanup
   pass missed, 1,757 files identified by Aug-12 mtime) + all 1,651 batch
   JSONL deleted. Corpus restored to exactly pre-import state (verified:
   384 jsonl / 46,421 sentences / 0 junk / 0 natural_japanese).

### Last decisions and why

- **Delete Thai batch** — ThaiCorpus didn't double-check its output; not
  Japanese content, would skew the corpus.
- **Natural Japanese exclusions** — skip 9 overlaps (duplicate content
  already in corpus as transcripts) + 9 dup master rows + unreferenced
  files; "exclude them and make a note".
- **Creator `natural_japanese`**, **style "Comprehensible Input" (1)**,
  **topic/episode/season null** (no topic data in any CSV — verified),
  **duration later** from audio/video.
- **Complete cleaner fix (broad header + in-text)** — unknown sources
  may have arbitrary WebVTT headers; spec-conformant skip is future-proof.
- **Remove the whole batch** — the repeating `X-TIMESTAMP-MAP` record in
  1,651 of 1,759 JSONL would cause a large statistical skew in frequency
  analysis; the 106 had no JSONL at all. Cleanest to clear all of it.

### Open risks / unresolved questions

1. **Parser-layer reconstruction failures (Frozen, needs authorization):
   the blocker for any Natural Japanese re-import.** GiNZA surface
   mismatches in `parser_normalizer.py` (`みです`/`くださいです`-style) and
   sentence-count mismatches. Unknown scope (all 106 vs subset). This is
   the next real work item when Claude is back — investigate, then decide
   fix vs. workaround, with full audit process (Frozen Components).
2. **Pre-existing test failures (not from this session):** archived
   `Archive/Analysis` + `Archive/Index` tests, and
   `Data Processor/tests/test_deepseek_client.py` (retired transport).
   Fail on the pre-change baseline too.
3. **`fix-source-intake-case-e` branch:** 1 commit ahead of master (WIP
   Case E fix), 4 behind — unreconciled, per the standing
   branch-divergence rule.
4. **`style_id` null on batch imports:** `batch_importer.py` has no style
   argument; the NHGJM-style post-import metadata fill is the mechanism
   (moot until a re-import).
5. **`duration_seconds` fill** from audio/video still pending (deferred
   by Owner to after import).
6. **Uncommitted working tree** (Owner freeze: no changes until Claude
   back): `Subtitle Importer/cleaner.py`,
   `Subtitle Importer/tests/test_subtitle_importer_cleaner.py`,
   `WORKING_LIST.md`, `JPROGRAM_SESSION_BOOTSTRAP.md` (+ this file). No
   commit/push made.
7. **Process findings for re-imports (operational, learned this session):**
   - Re-import of an existing source requires deleting ALL artifact types
     with **source_id-based** names (Sources files are stem-based; Source
     Registry / Cleaned Archive / Cleaning Jobs+Results / jobs/ / requests/
     / responses/ / Processing+Corpus+Job Results / Request Results /
     Logs are source_id-based). Stem-based cleanup misses most of them.
   - `requests/` + `responses/` are idempotent-reused: stale files there
     keep old content cycling through the pipeline after re-import.
   - The Source Registry sha256 check fails closed if the source text
     changes (registry entry must be deleted for re-import).
   - There is also a `Request Results/` dir (per-source
     request_builder_result.json) separate from `requests/`.

### Next immediate task (when Claude is back)

1. Claude reviews this session's uncommitted diff (cleaner fix + tests +
   docs) — the change is authorized and tested but **not independently
   audited** (Claude was down). Audit trigger log entry already filed.
2. Then Owner/Claude decide on the parser-layer investigation
   (`parser_normalizer.py` / `deterministic_parser.py` — Frozen) and
   whether to attempt a Natural Japanese re-import after a parser fix.
3. Full re-import path is documented in WORKING_LIST.md's "Natural
   Japanese subtitle batch" entry (staging, exclusions, metadata, batch
   removal). `Natural Japanese Staging/` (1,759 raw copies) is kept;
   `D:` is the source of truth.

---

---

## Archived session wrap-ups (Sessions 9–14)

Historical record only — moved to `Archive/Session_WrapUps_Sessions_9-14.md`
(2026-08-12, token-trap cleanup). The current session's wrap-up is §15 above;
these superseded versions are no longer loaded every session.

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
