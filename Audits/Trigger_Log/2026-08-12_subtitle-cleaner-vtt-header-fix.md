# Trigger Log — 2026-08-12 — Subtitle cleaner WebVTT header/in-text block fix

**Work done:** `Subtitle Importer/cleaner.py` — `VttParser` now skips the
whole WebVTT header block (the `WEBVTT` line plus every metadata line —
`X-TIMESTAMP-MAP`, `NOTE`, `STYLE`, custom `X-*` — up to the first blank
line, stopping early at a cue timestamp so a malformed header can't eat
the first cue) and skips in-text `NOTE`/`STYLE` blocks between cues. Plus
8 new unit tests in `Subtitle Importer/tests/test_subtitle_importer_cleaner.py`.

**Why:** the Natural Japanese subtitle import (this session) produced
1,759 sources of which 106 failed at the corpus-builder reconstruction
gate and the other 1,651 "successful" JSONL carried the WebVTT
`X-TIMESTAMP-MAP=LOCAL:00:00:00.000,MPEGTS:130000` header line as a
repeating junk record (frequency-skew hazard). The header line survived
cleaning; the parser could not round-trip it for 106 files.

**Audit trigger decision: Yes — confidence: Moderate.**
- Not an automatic Yes: `Subtitle Importer/cleaner.py` is NOT on the
  Frozen Components list (parser prompt/spec, deterministic_parser.py,
  response_validator.py, corpus_builder.py, parser_normalizer.py, the
  canonical JSONL format, deepseek_client.py, deterministic_parser_client.py).
- Judgment-call Yes (Moderate): it is a real logic change to live
  cleaning behavior (parsing rules for incoming subtitle content), in a
  project that was Owner-declared **locked** (no project-code changes
  without explicit authorization — this change WAS explicitly authorized
  by Owner on 2026-08-12: "lets do the complete fix broad header and in
  text"). The change is behavior-visible to all future `.vtt` imports, so
  an independent review is warranted.
- **Auditor pass NOT yet run — deferred.** Claude (the Claude-side
  Advisor/auditor) was down at session end and Owner froze all further
  changes ("we won't make any changes until claude is back up").
  The fresh-subagent Auditor pass on this change must run when Claude is
  back, before any commit/push of this work.

**Verification performed (working agent, pre-audit):**
- Subtitle Importer suite: 26/26 pass (18 original + 8 new).
- Full repo sweep: 66/69 test files pass; the 3 failures are
  pre-existing (archived `Archive/Analysis` + `Archive/Index` tests, and
  retired `Data Processor/tests/test_deepseek_client.py`) — confirmed
  identical on the pre-change baseline via `git stash` re-run.
- Real-data check: a re-cleaned source text no longer contains
  `X-TIMESTAMP-MAP` (job text char count 2544 → 2494).

**Status:** change complete, tested, Owner-authorized; uncommitted
(Owner freeze). Audit pending Claude's return. Related session record:
`JPROGRAM_SESSION_BOOTSTRAP.md` §15.
