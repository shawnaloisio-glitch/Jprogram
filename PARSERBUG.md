# PARSERBUG — Corpus-builder reconstruction failures on Natural Japanese subtitles (2026-08-12)

Status: **OPEN — root cause identified, fix NOT made (Frozen-Component
territory, project locked; needs Owner authorization + audit).**

Written 2026-08-12 from the Session 15 record (originally logged in
WORKING_LIST.md / JPROGRAM_SESSION_BOOTSTRAP.md §15, which were retired in
the 2026-08-13 tracker restructuring; this file preserves the findings).

---

## Summary

The Natural Japanese subtitle import (1,759 files from
`D:\Sourced Content\Japanese Import\Natural Japanese media\`, cataloged by
`master.csv`) produced **106 corpus-builder failures** plus **1,651
"successful" JSONL polluted with a repeating junk record**. Two independent
root causes, stacked:

1. **FIXED (cleaner):** the WebVTT `X-TIMESTAMP-MAP` header line survived
   cleaning and broke/dirtied the corpus.
2. **NOT FIXED (parser — this bug):** with the header gone, the
   canonicalizer's exact-reconstruction gate fails on **GiNZA word-surface
   mismatches** — the parser's word surfaces do not literally match the
   source text for certain sentences.

The entire batch was subsequently **removed** (Owner decision — the
repeating junk record would cause a large statistical skew in frequency
analysis), and the corpus is back to its clean pre-import state:
**384 JSONL / 46,421 sentences, zero junk records.**

---

## Root cause #1 — WebVTT header survived cleaning (FIXED)

- Every staged `.vtt` starts with:
  `WEBVTT` + `X-TIMESTAMP-MAP=LOCAL:00:00:00.000,MPEGTS:130000` (uniform,
  verified across all 1,759 files; no NOTE/STYLE/REGION variants).
- `Subtitle Importer/cleaner.py`'s `VttParser` skipped `WEBVTT` but kept
  the `X-TIMESTAMP-MAP` line as a "cue" → it landed in the source text,
  parse jobs, and corpus.
- 106 files: corpus builder failed at character 0 (reconstruction).
- 1,651 files: reconstruction happened to pass, but the junk line is
  embedded as a record in every JSONL (frequency-skew hazard).
- **Fix (implemented, Owner-authorized, uncommitted):** `VttParser` now
  skips the whole WebVTT header block (WEBVTT + all metadata lines up to
  the first blank line, stopping early at a cue timestamp for malformed
  files) and skips in-text `NOTE`/`STYLE` blocks between cues. 8 new unit
  tests; Subtitle Importer suite 26/26; full repo sweep 66/69 (3
  failures pre-existing). Audit trigger logged at
  `Audits/Trigger_Log/2026-08-12_subtitle-cleaner-vtt-header-fix.md`
  (auditor pass deferred — Claude was down).

## Root cause #2 — GiNZA word-surface reconstruction failures (THIS BUG, OPEN)

With the header gone, re-importing 8 representative failed files through
the fixed pipeline **still failed at the corpus stage**, all with
`parser_normalizer.py` `canonicalize()` errors:

```
ParserNormalizerError: words[16] surface 'みです' cannot be matched in the
sentence text after position 25 (impossible reconstruction).
```

### Concrete evidence (8/8 test-batch files failed, exact surfaces)

| Source | Parser surface that cannot be matched |
|---|---|
| `早口言葉 レベル１ Tongue Twister Level 1` | `みです` (from 「３（み）」ですね; reading `みる` — GiNZA merged `み）」で`) |
| `「入らないでください」 _Please do not enter._` | `くださいです` |
| `侘び寂び とは What is _Wabi-Sabi__` | `寂びです` |
| `カタカナ禁止ゲーム #1 No Katakana Game #1` | `せです` |
| `ChatGPTに恋愛相談 Asking ChatGPT for Love Advice` | `持つです` |
| `「乳幼児マーク」は誰のため？ Who Is the _Infant Mark_ For_` | `なさいです` |
| `AI vs 人間：よりいい音楽を作るのは？ …` | `canonical sentence count 503 does not match record count 502` |
| `日本語でゲーム Unpacking EP08 …` | `canonical sentence count 747 does not match record count 746` |

### Where it lives (Frozen Components — NOT touched)

- `Data Processor/parser_normalizer.py` — `canonicalize()` runs BEFORE
  validation; it recomputes spans/chunk text from parser output against
  the authoritative source text and enforces exact reconstruction. It
  aborts on the first surface it cannot match.
- `Data Processor/deterministic_parser.py` — the GiNZA/spaCy driver whose
  word segmentation produces the mismatched surfaces.

The mismatches are **content-specific GiNZA segmentation quirks** (unusual
punctuation inside text like 「３（み）」, compound/te-form boundaries, etc.).
The 1,653 historically-successful imports went through the same parser, so
the quirk is not universal — it triggers on specific sentences.

### Scope uncertainty

Whether **all 106** failed files share this underlying parser issue (vs.
only some, with the rest being pure-header failures) is **unknown**.
Determining it requires re-processing the remaining 98 files through the
fixed cleaner — NOT done (pending Owner decision; pipeline frozen).

---

## Current state (verified 2026-08-12)

- Corpus: 384 JSONL / 46,421 sentences, zero `X-TIMESTAMP-MAP` records,
  zero `natural_japanese` sources — exact pre-import state.
- Entire Natural Japanese batch removed (all 1,759 sources + all
  artifacts incl. `Request Results/`; see WORKING_LIST.md record in
  `Archive/WORKING_LIST.md`).
- Kept: `Workspace/natural_japanese_import.log`,
  `Workspace/natural_japanese_import_failures.csv` (106 rows with
  errors), `Workspace/Natural Japanese Staging/` (1,759 raw copies),
  `natural_japanese` entry in `Workspace/Config/creators.json`,
  cleaner fix in `Subtitle Importer/cleaner.py` (+ tests, uncommitted).

## What is needed to close this bug

1. **Owner authorization** to modify/investigate Frozen parser components
   (`parser_normalizer.py` / `deterministic_parser.py`) — project is
   locked; the cleaner change was explicitly authorized, the parser change
   has not been.
2. **Investigation**: determine whether the surfaces are (a) GiNZA
   tokenization quirks to handle in the normalizer's span-matching (e.g.
   tolerance/fallback for unmatched surfaces), (b) sentence-splitting
   mismatches (the 503-vs-502 class), and scope across all 106.
3. **Audit** of any parser change per project governance (audit-trigger
   log entry required).
4. **Re-import** after the fix (path fully documented: staging → 4 ×
   `batch_importer.py` runs → verify; re-import requires deleting all
   prior artifacts — see "Re-import pitfalls" below).

## Re-import pitfalls learned this session (operational)

- Artifacts are **source_id-based** except `Sources/*.txt` +
  `*.source.json` (stem-based). A stem-based cleanup misses most artifacts.
- `requests/` + `responses/` are idempotent-reused: stale files there keep
  old content cycling through the pipeline after re-import — delete them.
- There is a separate `Request Results/` dir (per-source
  `request_builder_result.json`) in addition to `requests/`.
- Source Registry sha256 fails closed if the source text changes — the
  registry entry must be deleted for re-import.
- `batch_importer.py` has no style argument → `style_id` comes out null;
  a post-import metadata fill (NHGJM pattern) is the mechanism.
- `duration_seconds` fill from audio/video remains pending (Owner-deferred).
