# DONE — Jprogram

Session wrap-up log — one entry per session, oldest first. This is the
**log**; current-state (architecture, phase, open items) lives in
`TODO.md`, which holds ONLY the current state.
Per the shared convention (2026-08-12): write a new entry here at each
session wrap-up; never stack wrap-ups into the bootstrap.

---

## Session 16 (2026-08-13) — Parser bugs closed out, reasonix headless troubleshooting, batch-import UI

**Logged late, mid-session, after Owner flagged that per-task DONE.md entries weren't happening** — this session ran a long stretch of completed tasks (doc corrections, three parser fixes, a branch reconciliation, a two-part reasonix investigation, and a new Web UI feature) purely as git commits, with no DONE.md entries until now. Backfilled here in one entry rather than reconstructed as several after the fact.

### Current phase

`PARSERBUG.md`'s parser-layer investigation (open since Session 15) is now **closed**: all three root causes found, fixed, merged, and confirmed — a full re-run of the original 106 failing sources through the fixed pipeline passed **106/106**. Corpus is still clean (386 files, 46,421 sentences, zero contamination). A new Web UI mechanism (`Web UI/server.py`, port 8001) is scaffolded and confirmed working end-to-end; `batch_importer.py` now supports the metadata fields it needs.

### What happened (chronological)

1. **Doc review + corrections.** Swept all `.md` files; found and fixed stale DeepSeek-parser framing in `README.md`/`PARSER_OUTPUT_SPEC.md`/`parser_prompt.md` (still described the retired LLM parser as live).
2. **Frozen Components retired** (Owner's explicit override, given plainly beforehand: the freeze was being removed at the exact moment a live bug was open in two of the files it protected). Audit-trigger is now judgment-call for every file.
3. **Parser bug investigation, three root causes found and fixed** (see `PARSERBUG.md` for the original findings this closes out):
   - Fix #1 (`d62eeec`): `canonical_sentence_texts()` counted an empty `\n\n`-block as a phantom sentence — the "canonical sentence count N does not match record count N-1" family of failures.
   - Fix #2 (`380ecfc`): `MAX_JOB_CHARACTERS` raised 10,000 → 200,000 — the low limit was a leftover from the retired LLM parser's cost budget; the live GiNZA parser has no such constraint (confirmed its own `max_length` is 1,000,000).
   - Fix #3 (`f400d2d`): `_merge_groups()` could fuse two words across a punctuation character stripped out before the adjacency check (`３（み）ですね` → corrupted `みです`).
   - **Revalidation**: re-ran all 106 originally-failing sources through the fixed pipeline — **106/106 pass**, confirming the fixes resolve the real, full failure set, not just the hand-picked examples used to diagnose them.
4. **`fix-source-intake-case-e` branch reconciled** (`2359687`) — a real WIP fix from 2026-08-10, 24 commits behind master, never merged: registry-path collision with a mismatched `source_id` now raises an error instead of silently overwriting. Branch deleted after merge.
5. **Reasonix headless-write investigation — two root causes found and fixed, documented in `Shared\RX_WORKFLOW.md`** (not duplicated here, per C2):
   - Missing `Edit`/`Write` rule in `reasonix.toml`'s `[permissions] allow` list — every headless write hard-failed with `constraint=no-mutation` regardless of `--permission-mode`, because no headless task had ever attempted a real write before this session (confirmed via `reasonix`'s own usage stats: virtually all real coding was `source:desktop`, never CLI).
   - The stable header duplicated `AGENTS.md`'s "prefer read-only unless explicitly authorized" guardrail — sent as literal prompt text on every task, it self-triggered the same read-only lock even after the permission fix. Removed from the header (byte-identical block in `RX_WORKFLOW.md`), kept in `AGENTS.md` where it belongs.
   - **Not fully resolved**: the `batch_importer.py` Coder task (step 6) still blocked with `constraint=no-mutation` despite both fixes. Likely cause (not yet confirmed): `AGENTS.md` itself still carries the same guardrail line and is auto-loaded for every real project task, re-introducing the trigger through a different path than the header. Untested; next session should confirm before spending more on this.
6. **`batch_importer.py` extended** (`0e4cc06`) to accept `--style`/`--topic`/`--episode`/`--season`, closing the known null-metadata gap. Coder's read-only analysis (twice-blocked, per above) caught a real bug in Advisor's own task design before any code was written — `--style`/`--topic` needed int conversion (`load_styles()`/`load_topics()` return ints) that the original task spec, written as `str`, would have missed. Applied directly by Advisor per Coder's fully-specified design.
7. **Web UI mechanism built** (`Web UI/server.py`, port 8001) — a generic Advisor-served-form channel, not a fixed app: stdlib `http.server`, no new dependencies, serves whatever's in `forms/` (currently `batch_import.html`), `/api/config` reads real creators/styles/topics for dropdowns, `/api/submit` writes to `pending_submission.json`. Confirmed working end-to-end (config load, form load, submit round-trip) via direct `curl` checks. Watcher-based pickup agreed (Advisor watches for the submission file, no "done" message needed) but not yet wired to an actual watch — no real submission has been made yet.

### Last decisions and why

- **Frozen Components removed** — Owner's call, made with the risk stated plainly first, per the standing override rule.
- **Two of three parser fixes applied directly by Advisor, not through Coder** — reasonix was broken all day; Coder's diagnosis was correct and re-verified independently each time, so applying its already-correct, already-converged-on fix directly was faster and equally safe as waiting on a broken delivery mechanism. Same for the batch_importer extension.
- **Revalidate against the full 106, not just examples** — Owner asked directly whether the pipeline was ready for production use; hand-verified examples weren't sufficient evidence for that question, a full re-run was.
- **Reasonix fixes documented centrally in `RX_WORKFLOW.md`, not per-project** — this workspace's own C2 (no rule duplication) convention; every project already defers to that file for Coder-mechanism detail.

### Open risks / unresolved questions

1. **Reasonix headless writes are still not reliable for real multi-part tasks** — two root causes fixed, but the `batch_importer.py` task blocked again after both fixes. Suspected but unconfirmed: `AGENTS.md`'s own copy of the read-only guardrail line, auto-loaded per task. Needs a cheap isolated test (real project worktree WITH `AGENTS.md`, simple task) before spending more attempts on a real task.
2. **Two Audit-trigger-Yes changes (fix #1, fix #3) have not had an independent Auditor pass** — applied directly by Advisor as authorized exceptions during the reasonix outage, correctly re-verified against tests each time, but never reviewed by a fresh session per the normal Auditor process. Worth doing before trusting them at full production volume.
3. **`Language Coach J/DONE.md`** — found stale during the earlier doc survey (missing several sessions' wrap-ups); not yet fixed.
4. **`Audits/OC_Reliability_Log.md`** — looks abandoned since 2026-08-06; not yet addressed.
5. **Web UI watcher not yet wired** — the mechanism works, but Advisor hasn't yet set up the actual watch-for-submission step since no real form has been used yet. Next real use of the batch-import form needs this in place first.
6. **This DONE.md logging gap itself** — per-task logging should resume going forward; this entry is a one-time backfill, not a new normal.

### Next immediate task

Confirm/fix the remaining reasonix headless-write blocker (AGENTS.md hypothesis) if more Coder tasks are needed soon; otherwise, wire up the Web UI watcher and hand the batch-import form to Owner for its first real use.

---

## Session 15 (2026-08-12) — Natural Japanese import attempt, cleaner fix, batch removal

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
   `WORKING_LIST.md`, `TODO.md` (+ this file). No
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

## Earlier sessions (9–14)

Historical record only — moved to `Archive/Session_WrapUps_Sessions_9-14.md`
(2026-08-12, token-trap cleanup). These superseded versions are no longer
loaded every session; they live in the archive if ever needed.
