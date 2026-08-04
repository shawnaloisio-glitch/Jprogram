# Session Handoff Audit

**Project:** Japanese Corpus Pipeline (C:\Jprogram)
**Date:** 2026-08-04
**Type:** Session handoff / continuation audit — audit only, no project files modified.

This document is the audit-first, modify-second handoff for a new session. It
records the current architecture (verified against the implementation), the
regression state, known issues, completed fixes since the previous baseline,
pending real-world validation issues, and the recommended next work order.

---

## 1. Current Architecture Summary

Verified against live code (this session).

### Pipeline (current, implemented)

```
Clean Source
    |
    v
DeepSeek Parser          (deepseek_client.py — raw response saved verbatim)
    |
    v
Parser Output Canonicalizer   (parser_normalizer.py — NEW authoritative stage)
    |   replace sentence text from the clean source (sentence authority)
    |   recompute word char spans
    |   recompute chunk text
    |   verify source reconstruction (integrity gate)
    v
Response Validator      (response_validator.py — validates CANONICAL records)
    v
Corpus Builder          (corpus_builder.py)
    |   assign global IDs
    |   assign sections
    |   stamp provenance
    v
Canonical JSONL Corpus  (Data Processor\jsonl\<source_id>.jsonl)
    v
Analysis                (Analysis\ analyzers, read-only consumers)
```

### Verified ownership confirmations (Phase 2 checks)

| Check | Result | Evidence |
|---|---|---|
| Corpus Builder no longer owns canonicalization logic | ✅ | Canonicalization functions moved to `parser_normalizer.py`; `corpus_builder.py` imports/re-exports them for backward compatibility (corpus_builder.py:66-79). |
| Parser Normalizer is the authoritative canonicalization stage | ✅ | `corpus_builder.process_job` calls `canonicalize(parser_data, job_text)` **before** `validate_parser_output` (corpus_builder.py:797 → :805). |
| Validator validates canonical records | ✅ | The validator receives the canonicalized output; its partition check compares word surfaces against canonical sentence content with punctuation/whitespace excluded (response_validator.py:120-139, 249-268). |
| Clean source remains the sentence authority | ✅ | `canonical_sentence_texts` derives authoritative sentence text from the cleaned job text; parser `text` is ignored (parser_normalizer.py:287-304, 307-346). |
| One responsibility per stage | ✅ | Normalizer = canonicalization; Validator = gate (never repairs); Builder = IDs/sections/provenance; Analyzers = statistics. |

### Module inventory (pipeline)

- **Parser Output Canonicalizer:** `Data Processor\parser_normalizer.py` (485
  lines) — `canonicalize`, `canonical_sentence_texts`, `restore_sentence_text`,
  `recompute_character_spans`, `recompute_chunk_text`,
  `verify_source_reconstruction`; `ParserNormalizerError` (aliased
  `CorpusBuilderError`). No dependency on paths/config/validator/result writers.
- **Response Validator:** `Data Processor\response_validator.py` (680 lines) —
  partition check now punctuation-normalized so parser surfaces that omit
  sentence-final punctuation are accepted against canonical text.
- **Corpus Builder:** `Data Processor\corpus_builder.py` (1094 lines) —
  canonicalize → validate → build ordering; per-job recompute removed from the
  builder; source-level `verify_source_reconstruction` retained as the final
  gate before JSONL write.

### Application shell / Source Builder / Processing / Analysis

Unchanged since the previous baseline and verified present: `app.py` (3 tabs),
`Source Builder\` (gui, controller, source_package, handoff, processing_tab,
analysis_tab_gui, metadata_editor, etc.), `Production Manager\`, `Analysis\`,
`Source Intake\`, cleaners, `Config\`.

---

## 2. Current Regression Status

Full regression executed this session (all `test_*.py` under the project,
excluding the two dev-only scripts that hardcode external benchmark paths).

**Total: 740 tests — 735 passing / 5 failing (documented).**

| Suite | Pass | Fail | Notes |
|---|---|---|---|
| Data Processor (incl. parser_normalizer) | 108 | 0 | `test_parser_normalizer.py` 12/12; `test_corpus_builder.py` 28/28 (was 27; +1 E2E canonicalizer regression) |
| Source Builder + shell | 269 | 5 | same 5 known failures (below) |
| Production Manager | 77 | 0 | |
| Analysis | 78 | 0 | |
| Source Intake | 106 | 0 | |
| Other (cleaners, Common, Integration, Templates) | 97 | 0 | |
| **Total** | **735** | **5** | |

**The 5 failures are the documented live-Config fixture issues, unchanged from
the previous baseline:**
- `test_source_builder_quick_presets.py` — 1 failure:
  `default_source_type_for_collection resolves via config` (queries removed
  collection `teppei_beginner` in the live Config).
- `test_source_builder_gui_presets.py` — 4 failures: preset-population fixtures
  reference removed values (`teppei_beginner`, `con_teppei_podcast`,
  `article`, `nhk_news`) while reading the live Config.

These are fixture-vs-config issues, not code defects. The canonicalization
change introduced **no** new failures.

---

## 3. Current Known Issues

| # | Issue | Severity | State |
|---|---|---|---|
| 1 | **Real-data pipeline not re-verified after the canonicalization fix.** The only real-data run (21:42, source `podcast_transcript_ci-transcript_ep001`) produced a raw DeepSeek response but FAILED at corpus build (Corpus Result `success: false`, `jobs_failed: 1`, 0 records). The canonicalizer + validator rework was applied at 22:34–22:39, *after* that run; the fixed pipeline has not yet been exercised against the existing response. | High | Open |
| 2 | **P0 Item 8 (collection/source-type synchronization) is live.** `Config\source_types.json` now contains `cij_transcript`, which has **no** `PROCESSING_PROFILE` in `project_config.py` (only `anime_subtitle`, `podcast_transcript`). Collections `cijapanese` and `ci_transcript` declare default `cij_transcript`; the standalone source "I like apples" is `cij_transcript_i-like-apples`. These sources cannot hand off/process. | High | Open |
| 3 | **Frozen contracts not reconciled with the canonicalization stage.** `PARSER_OUTPUT_SPEC.md` §3 (line 33, "word units never include punctuation"), §14 (validation contract), `Prompts\parser_prompt.md` (lines 52, 142), `README.md` (line 473: "the Corpus Builder ... recomputes character spans and chunk text"), and `PROJECT_STATUS.md` (line 1080: "the Corpus Builder deterministically normalizes") still describe the pre-canonicalizer architecture. Code changed; docs did not. Frozen-contract updates require deliberate approval. | Medium | Open |
| 4 | **5 documented regression failures** (live-Config fixtures). | Low | Open (documented) |
| 5 | **`api_key.txt` still contains a real 35-char `sk-` key** at the project root. Release-critical secret; must be removed/rotated and moved to a non-committed mechanism before external review/distribution. | High | Open |
| 6 | **Stale runtime metadata (Item 7).** `Source Builder\gui_settings.json` still holds `origin: "con_teppei_podcast"` (removed from Config). `Source Builder\quick_presets.json` preset references collection `cijapanese` with `source_type: podcast_transcript` while the collection's declared default is `cij_transcript` — the preset/collection mismatch of Item 8. | Medium | Open |
| 7 | **Config no longer at clean baseline.** Since the baseline reset, real-data testing added: collections `cijapanese` / `ci_transcript`; source types `podcast_transcript` + `cij_transcript`; origins `user_transcription` + `subtitle`. | Low | Intentional test data, but drift from the documented clean baseline |
| 8 | **Runtime data present (not empty).** `Sources\` 12 files (5× `ci_transcript_epNNNN` txt+sidecar, 1× standalone "I like apples" txt+sidecar); Registry 1; Cleaning Jobs 1; Cleaning Results 1; Processing Results 1; Diagnostics 2 (`.json.gz`). No JSONL corpus yet (`Data Processor\jsonl` empty). | Low | Real-data test residue |
| 9 | Remaining register items (see Section 5) — processing cancel (P1), subtitle workflow (P1), import filesystem (P1), collection hierarchy (P2), non-episode model (P2), duplicate analysis (P2), embedded tab workflow (P2), template editor validation (P2). | — | Open |

---

## 4. Completed Fixes Since Previous Baseline

Previous baseline = `Final_Baseline_Audit.md` (2026-08-04), which recorded a
clean runtime, empty Config, and a parser→validator→builder pipeline with no
canonicalization stage.

| # | Fix | Files | Verification |
|---|---|---|---|
| 1 | **Parser Output Canonicalizer implemented** as a real stage that runs before Response Validation (per `Canonicalization_Implementation_Plan.md`). | `Data Processor\parser_normalizer.py` (new, 22:34) | 12/12 new tests; E2E regression in test_corpus_builder 5b (28/28) |
| 2 | **Corpus Builder rewired** — `process_job` now runs `canonicalize` before `validate_parser_output`; per-job span/chunk recompute moved out of the builder; backward-compatible re-export of moved names. | `Data Processor\corpus_builder.py` (22:39) | full suite green (no new failures) |
| 3 | **Validator updated to validate canonical records** — partition comparison is now punctuation/whitespace-normalized (surfaces exclude punctuation; punctuation preservation is enforced by the normalizer's source-reconstruction gate). | `Data Processor\response_validator.py` (22:39) | validator/contract/corpus suites green |

No changes were made to the frozen parser prompt, PARSER_OUTPUT_SPEC, source
template spec, PM API, or Source Intake schemas in this fix set (see Issue 3 —
the narrative docs still need reconciliation).

---

## 5. Pending Real-World Validation Issues

Full register: `Audits\2026-08-04\REAL_WORLD_VALIDATION_ISSUES.md`.

| Priority | Item | Summary |
|---|---|---|
| **P0** | 8 | Collection/source-type synchronization — a collection default source type must be processable; `cij_transcript` currently is not. Direct cause of the real-data handoff failure. |
| **P0-adjacent** | 7 | Remove hidden Teppei metadata dependencies — stale `gui_settings.json` / `quick_presets.json` references. |
| **P1** | 4 | Processing cancellation — no cancel for in-flight multi-source runs. |
| **P1** | 10 | Subtitle import workflow — two overlapping subtitle paths; profile not exposed. |
| **P1** | 1 | Import filesystem — no folder/bulk import. |
| **P2** | 2 | Collection folder hierarchy — season/volume grouping missing. |
| **P2** | 3 | Non-episode content model. |
| **P2** | 5 | Duplicate analysis workflow. |
| **P2** | 6 | Embedded tab workflow. |
| **P2** | 9 | Template editor validation limitations. |

---

## 6. Recommended Next Work Order

Per the audit-first principle, each implementation must be preceded by the
five-part statement (Problem / Current owner / Correct owner / Proposed change /
Regression risk) and wait for approval.

1. **Re-run the real-data pipeline on the existing response** for
   `podcast_transcript_ci-transcript_ep001` through the fixed Corpus Builder
   (canonicalize → validate → build) to confirm the
   `WORD_SURFACE_PARTITION_MISMATCH` failure is resolved and a canonical JSONL
   corpus is produced. This closes the loop on the canonicalization fix before
   any further real-data work. (Validation, not a code change.)
2. **Item 8 (P0)** — collection/source-type synchronization:
   decide the fate of `cij_transcript` (either add a processing profile +
   config plumbing, or mark unprocessable and exclude from processable
   selections, with editor-time validation). Correct owner: Source Builder
   metadata/config layer + `project_config.py`.
3. **Item 7 (P1)** — clean the Teppei metadata: reset `gui_settings.json` and
   `quick_presets.json` to neutral defaults; reconcile the preset's source_type
   with the collection default.
4. **Item 4 (P1)** — processing cancellation design that respects PM's
   artifact-only resume behavior.
5. **Item 10 (P1)** — subtitle import workflow unification.
6. **Item 1 (P1)** — import filesystem (folder/bulk import).
7. **P2 items** in register order (2, 3, 5, 6, 9).
8. **Reconcile the frozen-contract narrative** with the canonicalization stage
   (PARSER_OUTPUT_SPEC §3/§14, parser_prompt.md, README.md, PROJECT_STATUS.md)
   — deliberate, approved contract update; keep code and docs in step.
9. **Security hygiene** — remove/rotate `api_key.txt` and move key loading to a
   non-committed mechanism before any external review or distribution.

---

## Project Principles to Maintain (unchanged)

- One responsibility per stage.
- No hidden dependencies.
- No language-specific defaults in core architecture (project-level `ja` is
  intentional).
- User metadata must not leak into portable builds.
- Frozen contracts must be updated deliberately.
- No temporary patches that bypass architectural problems.
- Prefer correct ownership over minimum line changes.
- Audit first, modify second; state Problem / Owner / Change / Regression risk
  and wait for approval before modifying.

---

*End of session handoff audit.* STOPPED.
