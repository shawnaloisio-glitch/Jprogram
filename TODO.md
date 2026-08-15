# Jprogram Session Bootstrap

Companion to `CLAUDE.md`. `CLAUDE.md` is auto-loaded and holds Advisor's standing behavior rules (role, permission mode, evidence hierarchy, report format) — read it first if you haven't already. This file holds current project state: what's built, what's next, what to know before touching anything. Unlike `CLAUDE.md`, this file is expected to go stale between sessions and gets refreshed as part of each handoff.

**Note:** structure, section cross-references, and entry points below were re-verified 2026-08-13 against current disk state and git after the de-bloat. §6's test counts remain as last measured by the 2026-08-05 deep audit (see §10); re-verify them whenever the Source Intake suite next runs. **Frozen Components were retired 2026-08-13** (Owner override) — see `CLAUDE.md`'s "Frozen Components (retired 2026-08-13)" section. **`Workspace/` was fully wiped and rebuilt from scratch twice: Session 19 (2026-08-13, initial production run) and Session 20 (2026-08-14, global-counter `source_id` migration)** — see the "Corpus state as of Session 20 end" open item below for current corpus composition; any earlier file-count or `source_id` figures elsewhere in this doc predate that reset.

**Small, concrete pending items** (things to check/decide/fix that aren't
major scope) live in this file's **Open items** section below (folded from
the retired `WORKING_LIST.md`, 2026-08-13 — resolved history archived at
`Archive/WORKING_LIST.md` + `Archive/WORKING_LIST_Resolved.md`). The
numbered sections above hold architecture/state/major tasks only.

---

## Open items (folded from `WORKING_LIST.md`, 2026-08-13)

- **Repo cleaned for sharing / pre-corpus-run (Session 19, 2026-08-13).**
  `Language Coach J/` was found nested inside this git repo — a mistake
  from an earlier cleanup, not (as a now-corrected memory had claimed) a
  deliberate decision. Moved to `C:\AI Development Projects\JapaneseCorpus\Language Coach J`,
  a sibling of this repo folder, matching the existing `ThaiCorpus\Language
  Coach T` precedent; no longer git-tracked here (commit `6c6d807`), dead
  `.gitignore` rules for it removed. This also resolved a real personal-data
  exposure risk (`Language Coach J/Shawn/` vocab/kanji files were tracked in
  git). Verified afterward: no personal data and no code dependency on
  `Language Coach J` remains in this repo. A clean backup zip (303 files,
  code/docs/tests only, excludes one copyrighted parser-fixture file at
  Owner's call) was made at
  `C:\AI Development Projects\JapaneseCorpus\Jprogram_backup_2026-08-13.zip`.
  Both commits pushed to `origin/master`.
- **Standalone-import source_id collisions — FULLY RESOLVED 2026-08-14
  (Session 20): global-counter identity adopted project-wide, superseding
  both the earlier race-condition fix and the naming-collision item that
  followed it below.** The concurrent-write race was already closed
  earlier this session (`write_registry_if_absent`, commit `fe22dae`), but
  a real gap remained: two *different* titles could still slugify to the
  same `source_id` in the first place, and a genuine non-duplicate
  collision had no clean automatic resolution. Owner: "I want to implement
  the unique ID counter the same as mandarincorpus... if we have to redo
  our imports that is fine." Adopted `source_id`s of the form `ja_NNNNNN`
  (global counter, content-independent — see `source_id.generate_counter_id`
  / `next_counter`), replacing the slug-derived scheme everywhere
  (collection mode included, per Owner's explicit "everywhere" scope
  choice, even though collection mode's own `next_auto_sequence` was
  already collision-safe). `Source Builder/handoff.py` gained
  `register_standalone_source`/`register_collection_source`: reserve a
  counter value, attempt create+registry-write, retry with a fresh counter
  on a concurrent collision (bounded, `MAX_ID_RETRIES = 25`).
  **A real bug was found and fixed along the way, not just theorized:**
  the first version of the retry cleanup deleted
  `cleaning_job_path_for(candidate_id)` unconditionally on a collision —
  under genuine multi-process concurrency this sometimes deleted the
  *winning* process's in-progress Cleaning Job file (WinError 5, access
  denied), because ownership of that path isn't decided until the
  Registry write resolves. Root-caused to `handoff()` writing the Cleaning
  Job even when the Registry step failed; fixed by gating Cleaning Job
  creation on Registry success, and the cleanup helper no longer touches
  anything keyed by the contested id at all. Verified with a real 20-
  process concurrency run (not just mocked), repeated 3x clean — 20/20
  distinct ids, 0 errors, 0 leftover artifacts. Full test suite passes
  (2 hardcoded old-format filename assertions updated). Commits `d9e45b1`,
  `d94a119`.
  **Corpus fully rebuilt same session** (Owner: "wipe and remake") — see
  the corpus-state item below for the new totals. `Config/` (creators/
  styles/topics) was restored from the pre-wipe values rather than
  reconstructed from memory. Found and fixed two real issues during the
  rebuild, not code bugs: (1) Kensan's material-level detection reads the
  *immediate parent folder name* (`import_material.suggested_material_level`),
  so pointing the importer straight at the real `kensan` folder fails
  every file with "material_level is required" — the original run must
  have staged files into a folder literally named `ungraded`; reproduced
  by staging the same way this time. (2) the failed first Kensan attempt
  left 113 orphaned canonical `.txt` files with no package/registry
  (`create_standalone_source` writes the canonical file before the
  package), which made the retry's idempotency check think those files
  were already imported (0 to import) until the orphans were deleted.
  Also fixed the LingQ importer's missing `style_id`/`topic_id` at the
  source this time (`d94a119`) instead of the post-hoc sidecar patch the
  original run needed.
- **Processor/analysis output metadata (possible future need)** — `origin`
  may shift to domain/topic as a *separate* tag (not a replacement);
  candidate tags: domain/topic, register, format/modality,
  creator/channel — human-recorded at ingestion. Not a task yet; revisit
  when real processor/analysis data organization becomes a live problem.
  (Full discussion in `Archive/WORKING_LIST.md`.)
- **`sentence_index` "no gaps" not validated** — `response_validator.py`
  checks strictly-ascending only; `PARSER_OUTPUT_SPEC.md:253` requires no
  gaps. Confirmed zero current functional impact (inert metadata — nothing
  reads it). Deliberately deferred per Owner; revisit if anything starts
  reading `sentence_index` or the UI/user-issue backlog clears.
- **Tkinter GUI state errors** — console output on specific UI
  interactions; not reproducible from an agent session. **Blocked on Owner
  pasting the actual traceback.**
- **Analysis tab can't analyze multiple files at once** — single-file only.
- **Import-from-subtitle workflow is clunky** — Owner flagged for design
  thought, not an immediate fix.
- **Confirmation-gate presentation, corrected 2026-08-13:** before launching
  a Coder task, present a manager-level plain-English description (what the
  task does, why, its scope) — not the prompt-file mechanics, raw
  `reasonix-cli` invocation, or `--allowed-tools` flags. Owner corrected this
  after Advisor showed the raw command instead of a summary. The technical
  detail still exists (prompt file, worktree, invocation) but stays
  something Advisor can produce on request, not the default gate output.
- **Reasonix headless Coder writes: extensively investigated 2026-08-13
  (Session 18), still unresolved, work-around is direct Advisor
  implementation for now.** Removed `AGENTS.md`'s "Direct sessions" ask-first
  paragraph and `CLAUDE.md`'s matching "direct Reasonix sessions" callout
  (both auto-loaded into every Coder session) — real task still blocked
  identically afterward. Built a clean-room test workspace (`C:\testingfolder`)
  and ruled out, one at a time, with the actual file verified on disk after
  each test (never trusting the JSON self-report, which lies in both
  directions): missing permission rule, `reasonix-cli`'s `-p` mode itself,
  the large 66-rule `reasonix.toml`, Advisor's own tool being sandboxed
  (Owner independently reproduced the same result in their own terminal),
  the stable header + task-template wording, `AGENTS.md`'s content in every
  variant tried, `AGENTS.md`'s specific filename, accumulated session
  history, and a fully fresh Reasonix uninstall+reinstall. A raw DeepSeek API
  call (no agent framework at all) responded instantly and cleanly, ruling
  out DeepSeek-server-side load/throttling as the cause *at that moment*.
  Owner reported ~6 Reasonix updates since Monday and the same problem now
  showing up in the manual copy-paste desktop workflow too — the strongest
  lead is a regression in a recent Reasonix release, external to this
  project's own config. **Not going to keep spending on this for now**
  (Owner's call) — Parts 1/2/3 of the batch-import optimization below were
  implemented directly by Advisor instead, bypassing Coder entirely for this
  stretch of work. Revisit Reasonix once a further update lands.
  **One more theory tested and eliminated (Session 19, 2026-08-14):** Owner
  found the Reasonix desktop app's Settings → Permissions → "Writer mode"
  was set to "ask (prompt before writers)" with no fine-grained overrides —
  plausible cause, since a headless session has nobody to answer an "ask"
  prompt. Owner switched it to "allow (auto-run ordinary writers)"; verified
  the change actually persisted to `C:\Users\Shawn\AppData\Roaming\reasonix\
  config.toml`'s `[permissions] mode = "allow"` (file mtime matched the
  change). Reran the exact same `C:\testingfolder` headless write test
  immediately after — **still blocked, identical `constraint=no-mutation`
  failure.** This is first-hand proof (file confirmed changed, test rerun
  after, same result), not inference — rules out the writer-mode fallback
  setting definitively. Combined with everything else already ruled out,
  very little remains on the "something in our config" side; strengthens
  the external-regression conclusion further. (Separately, while
  investigating: found and fixed an unrelated real `reasonix.toml` TOML
  parse error in **QuadRead** — two permission-allow entries had a raw
  unescaped newline instead of `\n`, corrupting the whole file. Not
  Jprogram's file, not related to this block, but worth knowing QuadRead's
  own Permissions UI was broken for an unrelated reason.)
  **Retested immediately after a fresh Reasonix update (2026-08-14,
  same session): still blocked.** Version now `reasonix v1.25.1`. Identical
  `constraint=no-mutation` failure on the same `C:\testingfolder` test —
  the agent explicitly confirmed `reasonix.toml` already has `"Write"` in
  its allow list before hitting the block, and characterized the block as
  coming from *"the task's own execution policy header... a hard
  host-level constraint for this session"* — i.e. something `reasonix-cli`
  applies to headless/`-p` sessions itself, not a config value. This is the
  update Session 18 said to wait for; it did not fix the issue.
  **Narrowed precisely 2026-08-15 (Session 20) after another Owner-installed
  patch, `reasonix v1.25.2` — the block is real but narrower than it
  looked.** `Write` now works cleanly in both `-p` and `run` mode: file
  creation, and full-file overwrite of an existing file, both actually
  persisted to disk (verified by reading the file back after the process
  exited, not trusting the JSON self-report). But `Edit` (diff-style
  modification of an existing file) is still hard-blocked with the exact
  same `constraint=no-mutation` message, identically in both `-p` and `run`
  — confirmed with a real edit task (change one line in a Python file), not
  just a file-creation probe. `reasonix doctor` shows nothing locally that
  would explain it (`permissions: mode allow, rules allow:68 ask:0 deny:0`,
  no no-mutation flag anywhere in `reasonix.toml` or the roaming config) —
  this is baked into the binary/prompt layer for this build, not a local
  setting. Owner's read, plausible but unconfirmed (no way to check
  Reasonix's own issue tracker/changelog, and a vendor wouldn't announce a
  security-relevant fix like this until it's actually closed anyway): this
  looks like a deliberate, still-incomplete lockdown — `Edit` specifically
  disabled while `Write` stays open — rather than a random crash regression.
  **Practical workaround available now, not yet adopted:** scope a Coder
  task's `--allowed-tools` to `Write` only and have it emit complete file
  contents for anything it touches, instead of `Edit`. Costs more tokens
  per touched file (full content vs. a diff) but is genuinely functional.
  **Owner's call: still not reinstating Coder yet** — this is progress
  (something is actively being worked on vendor-side, `Write` alone
  already unblocks a meaningful subset of tasks), not a green light. Revisit
  the `Write`-only workaround, or full reinstatement, after `Edit` itself
  is confirmed fixed or Owner decides the workaround is worth adopting now.
- **Two Audit-trigger-Yes parser fixes (d62eeec, f400d2d) have not had an
  independent Auditor pass** — applied directly by Advisor during the
  reasonix outage, re-verified against tests each time, but never reviewed
  fresh per the normal process. Session 17 (2026-08-13) added strong real-data
  evidence (156 real Natural Japanese files, including all 106 originally-
  failing sources, 0 failures) but that is re-verification, not the
  independent code-review pass this item asks for. Worth doing before full
  production volume.
- **Language Coach J does not use Jprogram's Source Registry for
  human-readable filenames (found 2026-08-13, Session 17).** Verified by
  reading its code, not assumed: `corpus_loader.py` reads only the JSONL
  corpus (raw `source_id`, no name resolution); the one place a title gets
  produced (`build_library_db.py:43-91,165-166`) reads a separate
  `rename_log.csv`/`source_metadata.csv`, not
  `Workspace/Source Registry/<source_id>.json`. If a `source_id` isn't in
  `rename_log.csv`, it falls back to showing the raw slugified `source_id`.
  The Source Registry is real, persistent, and one-file-per-source (never
  overwritten — confirmed via `registry.py`), so the data exists; it's just
  not the thing Language Coach actually reads. Practical effect: none of the
  176 sources imported in Session 17 will show a human-readable title in
  Language Coach unless something else populates `rename_log.csv` for them.
  This is Language Coach J's project, not Jprogram's, so no fix belongs
  here — flagging so it isn't lost, and because it directly affects how
  trustworthy any name shown for Jprogram-sourced content is downstream.
- **Corpus state as of Session 20 end (2026-08-14): 3,161 sources, 5
  creators, `Workspace/` fully wiped and rebuilt again to pick up the new
  global-counter `source_id` scheme (`ja_NNNNNN`).** Every `source_id` from
  Session 19's rebuild is gone and replaced; nothing carries over.
  Breakdown: `nat_jap` (Natural Japanese, 1,773: all 4 level folders —
  1,780 real files minus 7 cross-level filename duplicates the importer's
  existing idempotency check correctly caught and skipped),
  `nihongo_jikan` (876: all 4 level folders, matches Session 19 exactly),
  `kensan` (113, staged into a folder literally named `ungraded` — see the
  resolved item above for why), `lingq` (62, `style_id`/`topic_id` now
  correct at import time instead of a post-hoc patch), `conteppei` (337).
  1,773+876+113+62+337 = 3,161, matching Registry/Sources/Cleaning Jobs/
  jsonl counts exactly, and every Registry filename matches `ja_\d{6}\.json`.
  Full session detail in `DONE.md` Session 20.
- **Environment gotcha for future process investigation (2026-08-13):** this
  machine's Python installations (both the project `.venv` and standalone
  installs) show every `python.exe` invocation as **two OS processes** —
  a stub parent that re-execs into a real-interpreter child, identical
  command line, near-zero CPU on the stub. Confirmed via `ParentProcessId`
  chains, not assumed. Don't mistake this for a duplicate/racing process —
  killing the wrong half (the working child, not an idle stub) can interrupt
  real work. Check `ParentProcessId` before killing anything that looks like
  a duplicate.

---

## 1. Project Purpose

- A **Japanese language corpus project**.
- **Goal:** create reliable corpus data from Japanese media sources (podcasts, anime subtitles; future manga, novels, web articles).
- **Pipeline purpose:**
  ```
  Raw source → cleaned data → parsed structured data → validated corpus → canonical JSONL corpus
  ```
- The project builds an immersion-oriented corpus that preserves raw linguistic evidence so later analyzers can compute frequency, distribution, exposure, and other measurements deterministically. **Jprogram's own scope ends at the finished canonical JSONL corpus (2026-08-09)** — the analyzers themselves now live in Language Coach, not here (see §14).

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
    Request Builder (jobs → parser requests)
    Parser          (deterministic GiNZA/spaCy engine; DeepSeek API path retired)
    Validator       (deterministic gate)
    Corpus Builder  (deterministic → canonical corpus)
   ↓
Canonical JSONL Corpus   (sentence-per-line, the single source of truth)
```

Jprogram's pipeline ends here. Analysis (deterministic analyzer utilities
→ evidence datasets → interpretation) is now a separate project's
responsibility — Language Coach, which reads this corpus but is not part
of this repo. See §14.

Entry points today:

- **`app.py`** — the application shell (Sources / Processing / Analysis tabs). This is the primary entry point.
- **`Source Builder\source_builder.py`** — standalone Source Builder launcher.
- **Production Manager CLI** — `python "Production Manager\production_manager.py" --source/--run/--pipeline/--dry-run`. (Note: "Production Manager" here is the software component that launches pipeline-stage subprocesses — not the Advisor/OC workflow role discussed in the design spec, which uses the term "Advisor" instead to avoid this exact collision.) Gained an in-process execution path (Session 18, commit `584888f`): `pipeline(..., launcher=launch_stage_inprocess)` runs all 5 stages via direct function calls instead of a subprocess per stage; the existing subprocess-per-stage default (`launch_stage`) and every stage's own standalone CLI are unchanged.
- **`Batch Importer\batch_importer.py`** — bulk-imports a folder of already-normalized source files (`.vtt`/`.srt`/`.html`) through the real pipeline as standalone sources. Non-recursive, idempotent, failure-isolated. Real production use confirmed 2026-08-13 (Session 17): 176 real Natural Japanese sources imported this way, 0 failures. Gained `--batch-mode` (Session 18, commit `39cd4c8`): runs every file's pipeline stage in the same long-lived process instead of a fresh subprocess per file per stage, so the parser model loads once per batch, not once per file (~1.97s/file vs ~12.9s/file baseline).
- **`Batch Importer\parallel_batch_import.py`** (Session 18, commit `cb8a665`) — orchestration-only wrapper around `batch_importer.py --batch-mode`: splits a folder's still-unimported files across N (default 6) parallel worker processes. No changes to `batch_importer.py`/`production_manager.py` themselves. Real 268-file run: 170s, 0 failures, ~0.63s/file effective (~20x the original baseline).
- **`Web UI\server.py`** (port 8001) — generic Advisor-served form channel, stdlib `http.server`, no framework. Serves the batch-import form (`Web UI\forms\batch_import.html`) and, as of Session 19 (2026-08-13), `Web UI\forms\manage_config.html` (add creators/styles/topics), plus a landing page (`Web UI\index.html`) linking to whatever forms exist. Submissions land in `Web UI\pending_submission.json`; Advisor watches for them during a live session (Monitor-based, archives to `Web UI\submission_archive\` rather than deleting). Also has a native OS folder-picker (`/api/browse-folder`, tkinter-in-subprocess) and a shared dark/light theme (`Web UI\theme.js`) any new form can pick up. Both forms had real bugs found and fixed in real use Session 19: `batch_import.html`'s submit button not re-enabling after success, and `manage_config.html`'s creator-ID pattern hint not actually being enforced (now a live input mask).
- **`LingQ Mini Stories Importer\import_lingq_mini_stories.py`** and **`Con-Teppei Importer\import_con_teppei.py`** — one-off importers (Session 19, 2026-08-13) for two source formats that don't fit the generic Batch Importer: LingQ Mini Stories needs A)/B)/quiz-label stripping, and Con-Teppei's `ep001.txt`-style filenames don't reflect real episode order (the real number lives in `manifest.csv` and each file's own header line — the importer parses and cross-validates it rather than trusting file order). Both real-run verified, 0 failures (62 and 337 files respectively). Neither is meant to generalize — same one-off pattern as the rest of the `*.py` scripts outside `Batch Importer/`.
- Pipeline stage scripts: `job builder.py`, `request builder.py`, `deterministic_parser.py`, `deterministic_parser_client.py`, `corpus_builder.py`, `response_validator.py`, and the two cleaners. (The DeepSeek API path — `deepseek_client.py` — is retired; kept unused in case it's ever revived.)

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

## 4. Frozen Components (retired 2026-08-13)

Removed at Owner's explicit override. See `CLAUDE.md`'s "Frozen Components (retired 2026-08-13)" section for what this replaces and why the timing (an open correctness bug in two of the formerly-frozen files) is worth remembering.

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

**Tests:** Source Intake suite — **109 tests passing** (corrected 2026-08-05; see the 2026-08-05 deep audit in `Audits/2026-08-05/DEEP_AUDIT_REPORT.md` — the "106" figure was stale and never propagated here even after the correction was first found).

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

## 10. First Advisor-CC Session Checklist — executed (2026-08-05)

Executed and superseded; the checklist itself was removed from this
current-state file (git history preserves it). Full record of that
session: `Audits/2026-08-05/DEEP_AUDIT_REPORT.md` and
`Audits/Trigger_Log/2026-08-05_first-advisor-session.md`.

---

**Original next-task list, superseded by the above but kept for reference:** real-data validation (full workflow with real source material), packaging/installer, external QC review (status was unclear — listed as "pending" in one place, "invoked once in ~60 hours" in another; Qwen Code is now available for this role regardless).

---

## 11. OC Operating Instructions

See `AGENTS.md` (auto-loaded into every Coder session by reasonix-cli) for the authoritative reporting format and core rules — keeping a single copy there avoids this file and `AGENTS.md` drifting out of sync.

Advisor reads OC's final result from the reasonix-cli `--output-format json` stdout (see `CLAUDE.md`'s "Coder command format"), not terminal display text.

---

## 12. Audit Log

Location: `Audits/Trigger_Log/` — nested under the existing `Audits/` folder rather than a sibling, since it's still fundamentally audit-related content, just a different granularity (every trigger decision, vs. `Audits/2026-08-04/`-style full review reports). Every Advisor trigger-field decision (Yes or No) gets recorded here, giving a queryable history for calibrating invocation rate over time.

---

## 13. Current-Stack Appendix

Provider-specific — revisit if the Coder model/platform changes:
- Coder runs via `reasonix-cli.exe` (DeepSeek native API — prompt caching
  engaged, cache-hit input ~98% cheaper). See `CLAUDE.md`'s "Coder command
  format" and `Shared\RX_WORKFLOW.md` for the full mechanism.
- The Coder task prompt opens with the byte-identical stable header (see
  `Shared\RX_WORKFLOW.md`) to keep DeepSeek's prefix cache engaged; never
  reword it.
- Reasoning effort is scaled per task rather than fixed.
- Retired mechanisms, kept for history only: OpenCode desktop-app relay,
  headless `claude -p` → DeepSeek redirect (no caching), Qwen Code. See
  `AI_Coding_Environment_Design_Spec.md` + `Archive/OC_Session_Access_Procedure.md`.


---


## 14. Major architecture decision (2026-08-09): analysis moved to Language Coach

Jprogram's scope ends at the finished canonical JSONL corpus. The analysis layer (deterministic analyzer utilities → evidence datasets → interpretation) moved to the separate Language Coach project, which reads this corpus but is not part of this repo. See `Shared\ECOSYSTEM_OVERVIEW.md`.

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
