# DONE — Jprogram

Session wrap-up log — one entry per session, oldest first. This is the
**log**; current-state (architecture, phase, open items) lives in
`JPROGRAM_SESSION_BOOTSTRAP.md`, which holds ONLY the current state.
Per the shared convention (2026-08-12): write a new entry here at each
session wrap-up; never stack wrap-ups into the bootstrap.

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

## Earlier sessions (9–14)

Historical record only — moved to `Archive/Session_WrapUps_Sessions_9-14.md`
(2026-08-12, token-trap cleanup). These superseded versions are no longer
loaded every session; they live in the archive if ever needed.
