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

## 14. Session Wrap-Up (2026-08-07) — Updated after Session 7

**Read this section first, always — it's kept current at every wrap-up,
not appended to indefinitely.** This update supersedes the "Session 6"
version below it (kept for reference, marked accordingly; the old
"Session 5" section has been dropped entirely — git history and
`Audits/OC_Reliability_Log.md` still hold that detail if ever needed).
If anything below conflicts with an older section elsewhere in this
file, this section wins — it was last refreshed 2026-08-07, end of
session 7.

### Current phase — the headline: Corpus Change Study Phases 1-3 are complete

**The deterministic parser is built, validated, stress-tested against
real content, and wired into the real app.** This is the actual reason
the `deterministic-parser` branch exists, and it went from "not
started" to "working end-to-end in the real Processing tab" across this
session and the one before it. `master` remains the mothballed
DeepSeek-architecture reference, completely untouched throughout.

Eight commits landed this session (all pushed to `origin` immediately
after each, per the established push-early habit — nothing sitting
unpushed at any point):

1. `ecdf049` — corrected a Session 6 self-report error (see below).
2. `827d995` — `.gitignore` cleanup (stale entries, added `.venv/`).
3. `1f9ced9` — **Phase 2**: pinned the GiNZA/SudachiPy dependency stack
   in a new project-local `.venv`, verified against the real project
   environment (not the prior session's isolated scratch venv) —
   `click` had to be pinned explicitly to work around a real upstream
   gap in spacy 3.8.13's own packaging metadata.
4. `d79ab05` — **Phase 3**: built `Data Processor/deterministic_parser.py`,
   the actual GiNZA/spaCy parser satisfying the frozen
   `PARSER_OUTPUT_SPEC.md` contract — deterministic sentence splitting,
   the merge-rule algorithm (conjugatable heads absorb their auxiliary/
   te-form continuation chain; noun+サ変可能+する compounds merge; a
   real mid-build finding that `動詞-非自立可能` auxiliary verbs like
   いる/くる/しまう/おく never merge backward, so they stay independently
   trackable vocabulary instead of collapsing into the preceding verb),
   and bunsetu-to-merged-word chunk mapping. Built and unit-tested in
   isolation, 22/22 passing at that point.
5. `db542ca` — **Phase 3 continued**: built
   `deterministic_parser_client.py`, the transport layer mirroring
   `deepseek_client.py`'s job-in/response-out contract exactly (same
   resume behavior, same `processing_result` schema, same exit codes)
   but calling the new parser directly instead of the DeepSeek API.
   15/15 tests, including guards confirming zero writes to the real
   workspace and zero imports outside its transport role.
6. `630f836` — **the big one**: validating against `QC Test Harness`
   surfaced a real architectural gap — `corpus_builder.py` (Frozen)
   required request files (Request Builder's output) to discover jobs
   and extracted its canonicalization ground truth by parsing a
   `"TEXT:\n"` marker out of the DeepSeek prompt. The new path
   deliberately bypasses Request Builder, so it had none. Fixed to
   source `job_text`/provenance from job files directly for **both**
   producers, removing the fragile marker-parsing entirely. Also fixed
   a related bug found in the same pass: provenance's `model` field was
   hardcoded to a constant regardless of which producer actually ran;
   now read per-source from that source's own `processing_result.json`.
   Zero regressions (30/30 + 10/10 required suites, full Data Processor
   suite 9 files/0 failures), then the actual proof: ran the real QC
   harness end-to-end and got a full ground-truth **PASS** — 犬 5/5 at
   exact expected spacing, 猫 5/5 at exact expected spacing, 食べる 4/4
   occurrences across all four inflected surfaces correctly grouped to
   one lexical form. First real, ground-truth-verified confirmation the
   new parser produces correct corpus output through the actual
   pipeline, not just unit tests. Frozen Component touched — audit
   trigger Yes, deferred to fire once per completed phase per this
   branch's calibration; logged in
   `Audits/Trigger_Log/2026-08-07_corpus_builder_job_file_fix.md`.
7. `354a6af` — **real-world stress test**: ran the new parser against
   ~9,600 lines (~52,000 tokens) from a genuine external Japanese media
   library (`D:\Natural Japanese media\Subtitles`, 462 real subtitle
   files, Owner-supplied) — not the QC harness's clean, hand-authored
   data. Found two real, reproducible bugs: (a) `_build_chunks()`'s
   "coarsen into previous chunk" branch used wrong list indices, crashed
   on real whitespace-delimited content (9/60 sampled files crashed);
   (b) the merge rule over-merged across a completed predicate boundary
   (`決まるです` wrongly became one word instead of two, because a
   terminal-form verb's own conjugation state wasn't checked before
   absorbing a following `助動詞`). Fixed both — the second fix required
   inspecting `token.morph`'s Inflection field to distinguish terminal
   (`終止形`) from continuative (`連用形`) forms, a real linguistic
   distinction the original design pass didn't anticipate. Re-verified
   at full scale after the fix: **all 462 files, 68,645 lines, 588,315
   real tokens — 0 crashes, 0 fatal errors, 0 partition mismatches, 0
   empty lemmas.** 20 remaining non-fatal char-span mismatches
   investigated and confirmed to be real caption-transcription artifacts
   (a comma injected mid-word in messy source data), not parser bugs —
   exactly what the "validated but not authoritative" char-span design
   already tolerates.
8. `391d088` — **Production Manager wiring, completing Phase 3**: the
   real app's `"api"` stage now launches `deterministic_parser_client.py`
   via the project's `.venv` interpreter (a new optional per-stage
   `"python"` key in the `STAGES` dispatch table, defaulting to
   `sys.executable` for every other stage, unchanged) instead of
   `deepseek_client.py` via the global interpreter. The `"api"` stage
   key itself was left unchanged everywhere it's referenced — a
   contained repoint, not a rename. Also fixed `processing_tab.py`'s
   now-inaccurate `"Failed during AI processing"` user-facing message to
   `"Failed during parsing"`. Full Production Manager suite (7 files, 0
   failures) + processing_tab suite (19/19), zero regressions. The
   deterministic parser is now reachable through the real app's
   Processing tab, not just `QC Test Harness`'s manual stage invocation.

All eight independently verified against raw `git diff`, direct test
re-runs, and (for the two most consequential commits) direct re-runs of
the actual QC harness and stress-test scripts myself — not from OC's
self-report.

### Language Reactor (LR) cleaner — investigated, explicitly not scoped as a task yet

Owner is exploring a new source type: Language Reactor's subtitle
export (a browser extension for YouTube). Confirmed via direct
inspection of a real exported file: **Excel is the right format** — it
exports clean, unambiguous columns (`Subtitle` / `Machine Translation` /
`Romaji` / `Hiragana` for a Japanese source), not HTML's markup-tied
structure or Saved-Items' vocabulary-only fragment. Confirmed the HTML
export gives nothing different — direct visual comparison showed
identical underlying data, same caption fragmentation, just a different
rendering; "Save as" was greyed out on that page anyway (dynamically
rendered, not a real backing resource).

**Real structural gap found, worth remembering when this becomes an
actual task:** LR's row boundaries are caption-display timing chunks,
not sentence or word boundaries. Concatenating rows with no separator
produces perfectly coherent continuous Japanese — meaning a single
sentence routinely splits mid-clause across rows, and individual
conjugations get split too (confirmed directly: `違い ます` appears with
a literal space where it should read `違います`, purely because that's
where the caption line wrapped for display). This would break
`deterministic_parser.py`'s whitespace-preservation logic (the Word
Rule's MUST) if fed in raw — it would treat the spurious caption-break
space as a deliberate word boundary and wrongly split real conjugations
apart. **The fix, already scoped but not built:** concatenate all rows
into one continuous blob, strip all internal whitespace (it's caption
noise here, not the deliberate kind LingQ's export had), then re-derive
real sentence boundaries via punctuation — which can reuse
`deterministic_parser.split_sentences()`'s existing logic directly, not
build something new. Owner explicitly said to hold off on building this
— not an open task, just don't lose the finding.

### Two process/environment findings from this session

- **The stale `JPROGRAM_WORKSPACE` shell env var, flagged at the end of
  Session 6, is confirmed resolved.** Owner's planned full computer
  restart worked exactly as expected — verified directly at the start
  of this session (not assumed): this Bash shell's own copy of the
  variable now matches the real persistent registry value exactly. No
  more need to force it explicitly per command.
- **A large, genuinely useful new resource appeared mid-session**:
  Owner pointed to `D:\Natural Japanese media\` (462 real subtitle
  files, 781 audio files, graded by difficulty tier) as available for
  testing. This is what the Phase 3 stress test (commit `354a6af`
  above) actually ran against, and it's a real, reusable asset for any
  future correctness work on this pipeline, not a one-time prop.
- Still not addressed, carried forward again: the **pre-existing stale
  `C:\Jprogram Workspace` folder tree** (predates Session 6, not
  created by this session's work) is still sitting on disk — likely
  tied to the still-open "OpenCode desktop may still point at the old
  repo folder" item from Session 4. Not touched without Owner's say-so.

### Last several decisions and why (this session)

- **`corpus_builder.py` fixed to read job files directly rather than
  synthesizing a fake request artifact** — Owner's own call between two
  options Advisor presented. The more durable fix (single source of
  truth, removes a fragile string-parsing hack) over the lower-risk one
  (zero Frozen-file changes, but a confusing "request" that was never
  sent). Justified specifically because this branch is safe to carry
  that risk — `master` stays untouched until merge regardless.
- **`動詞-非自立可能` auxiliary verbs never merge backward** — settled
  mid-build with OC, not assumed in the original design pass. Keeps
  these auxiliary verbs (progressive/completive/benefactive/directional
  aspect markers) independently trackable as their own recurring
  vocabulary rather than collapsing them into whatever main verb
  precedes them — matches the project's "evidence, not conclusions"
  principle over convenience.
- **Language Reactor cleaner work explicitly held off** — the
  structural gap (caption rows != sentence/word boundaries) is real and
  scoped, but Owner chose to stop at "found and understood" rather than
  build it this session. Don't treat the scoped fix as a green light to
  just go build it next session without checking first.

### Open risks / unresolved questions

Full detail in `WORKING_LIST.md` — this is a pointer, not a duplicate.
Headline items:

- **Language Reactor cleaner** — scoped (see above), not built, not
  authorized to start without checking with Owner first.
- **The Corpus Change Study's own Phase 6** (retire/archive
  `parser_prompt.md`, rewrite `PARSER_OUTPUT_SPEC.md`'s framing from
  LLM-instruction language to implementation-rule language) — the only
  formal phase from the original 7-phase order not yet done. Low
  urgency: the contract *shape* never changed, only the prose describing
  who follows it would need updating. `deepseek_client.py`/
  `parser_prompt.md` themselves are staying dormant as an Advisor-only
  fallback, not being retired — that decision was already settled this
  session's predecessor.
- **The UI-simplification idea from earlier this session is now
  actually actionable** — collapsing Import straight into processor
  output, since the deterministic parser removes the cost-timing reason
  the Sources/Processing split existed. This was a design note only
  until now; the parser being genuinely live changes that. Worth
  revisiting as a real task if GUI work resumes.
- **12 `ruff` findings deferred to "fold into the parser rewrite work"**
  — that work just happened (`corpus_builder.py` was directly modified
  this session). Worth checking now whether those specific findings are
  still present/relevant, rather than continuing to defer indefinitely.
- **Pre-existing stale `C:\Jprogram Workspace` folder tree** — still not
  cleaned up, carried forward again from Session 4.
- **`origin`'s name change** and **`sentence_index` "no gaps"
  validation** — both still explicitly deferred, unchanged.
- **The broader `WORKING_LIST.md` GUI backlog** — `teppei_beginner`
  stale-selection bug, Template Editor pass, Analysis multi-file
  capability, embedded-tabs restructure, API key utility design — all
  still open, all lower priority than the parser work now that it's
  actually done.
- Test the freshly-wiped workspace end to end — still not done, carried
  forward since Session 5.

### Next immediate task

No hard blocker on anything; the parser rewrite's core work is done.
In rough priority order:
1. If continuing pipeline/architecture work: the now-actionable
   UI-simplification (Import straight to processor output) is the most
   natural next step, directly following from today's completion.
2. `WORKING_LIST.md`'s GUI backlog if branch-prep/UI polish is wanted
   instead — same candidates as before, all confirmed outside the
   parser's blast radius.
3. Language Reactor cleaner, if/when Owner decides to pick it back up —
   scoping is already done, see above.
4. The formal Phase 6 documentation rewrite, lowest urgency of the
   above.

### Real-data validation status

Substantially stronger than any prior session. `QC Test Harness` gives
a full ground-truth **PASS** through the real pipeline using the new
deterministic parser (犬/猫/食べる all exact-match against hand-verified
expected values). Separately, stress-tested against a real, external
462-file Japanese media library — **588,315 real tokens, 0 crashes, 0
fatal errors, 0 partition mismatches, 0 empty lemmas** after two real
bugs found and fixed. See `QC Test Harness/README.md` for reuse
instructions; the stress-test script itself lives only in this
session's scratchpad, not the repo — reusable in concept, not as a
checked-in tool yet.

### Session 6 wrap-up (2026-08-07) — superseded by the section above, kept for reference

#### Current phase

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

- **Correction to a Session 6 finding, not a real gap after all.** Last
  session reported `2026-08-06_blast_radius_scope.md` as missing
  entirely (cited by this file and `WORKING_LIST.md` as the source
  confirming Analysis modules are unaffected by the parser rewrite).
  That was Advisor's own search error, not a real documentation gap —
  the file exists and always did, at
  `C:\AI Development Projects\Corpus change study\2026-08-06_blast_radius_scope.md`,
  a separate sibling folder outside the Jprogram repo. Last session's
  search only covered the repo itself. No action needed; the citation
  was correct all along. A UI/workflow simplification insight (see
  Session 7 below) was added to that file as an addendum this session.
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
