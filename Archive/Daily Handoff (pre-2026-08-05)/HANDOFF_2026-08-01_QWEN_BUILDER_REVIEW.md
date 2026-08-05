# Builder Milestone Handover — Qwen Independent Architecture Review

**Project:** Japanese Corpus Pipeline
**Project root:** `C:\Jprogram`
**Date:** 2026-08-01
**Handover type:** Corpus Builder milestone → independent architecture review
**Reviewer intended:** Qwen (independent reviewer with no access to this session's history)

This document is self-contained. It summarizes the completed Corpus Builder milestone, the frozen architecture principles, and the exact review questions for an independent reviewer.

---

## 1. Corpus Builder Milestone Summary

**Status: Corpus Builder is COMPLETE and integration-validated.**

The Corpus Builder is the deterministic stage that turns validated DeepSeek parser responses into the canonical sentence-per-line JSONL corpus. It is pure, deterministic Python — no LLM involvement anywhere after the parser response is received.

- **Location:** `C:\Jprogram\Data Processor\corpus_builder.py`
- **Tests:** `C:\Jprogram\Data Processor\corpus_builder_test.py` — 79 tests passing (61 unit + 18 integration/failure-path).
- **Supporting stage:** `C:\Jprogram\Data Processor\response_validator.py` (deterministic gate, 20/20 tests) + `response_validator_test.py`.

The Builder was implemented incrementally in TASKs 23–30 and validated end-to-end against a real Task 20 parser response (`bench_F_B`, 106 sentences from the 1,242-character 折り紙 job).

---

## 2. Frozen Architecture Principles

These decisions are frozen and must not be casually reopened:

- **Only ONE production LLM API boundary exists: the parser.** Every stage downstream of the parser is deterministic Python.
- **The parser preserves evidence; it never produces conclusions.** It preserves sentences, surface words, dictionary/base lexical forms, meaningful grammar chunks, and expressions, with positions.
- **The canonical corpus is the single source of truth** (Rule 5): named, sentence-per-line JSONL. Analyzers only read it.
- **Parser output is an intermediate artifact.** The parser uses a hybrid fixed-position-array format; the Builder expands it into named canonical records.
- **Parser-generated character offsets are NOT authoritative.** They are validated and reported, but the ordered word surfaces are authoritative because they exactly partition each sentence. The Builder recomputes character spans and chunk text deterministically.
- **Request metadata is the authoritative source of identity** (source, source file, job number); the parser's echoed identity values are not trusted.
- **Sections are not trusted from the LLM.** Section assignment is deterministic Builder work (default section when no explicit boundaries exist).
- **Job-local positions only from the parser.** The Builder assigns source-global ordering and IDs.

## 3. Production LLM Boundary

The pipeline has exactly one live-API boundary:

```
DeepSeek parser (deepseek-v4-flash, non-thinking,
                 response_format json_object, max_tokens >= 32768,
                 hybrid fixed-position-array format)
        ↓ (raw response saved verbatim)
Response Validator  (deterministic gate)
        ↓
Corpus Builder      (deterministic: recompute, IDs, sections,
                     provenance, verification, JSONL)
        ↓
Canonical sentence-per-line JSONL corpus
```

Key controls at the LLM boundary (established by controlled benchmarks, TASKs 16–20):
- non-thinking mode eliminates reasoning-token waste;
- `response_format: {"type": "json_object"}` guarantees valid JSON on completion;
- explicit `max_tokens` (≥ 32768) is required because the non-thinking default output cap is only 8192;
- prompt/context caching is automatic; the static parser prompt is a cache-hit prefix, so cached input is nearly free; output tokens are the dominant recurring cost.

## 4. Verification-over-Trust Principle

Wherever verification is deterministic and low cost, the Builder verifies rather than trusts:

- Every stage validates its input structure and raises `CorpusBuilderError` on invalid input — it never guesses, never silently repairs, never continues with corrupt data.
- `verify_source_reconstruction` is a mandatory integrity gate: the ordered sentence texts must reconstruct the clean source text **exactly** (after only two documented structural adjustments: section/header marker lines removed and a single trailing file-terminator newline stripped). Whitespace and punctuation are evidence.
- Global IDs are checked for uniqueness; child IDs are checked to belong to their parent sentence; duplicate canonical IDs in the output stream are rejected.

## 5. Cost/Performance Philosophy

- **Pay for linguistic interpretation once, then process deterministically.** DeepSeek is used only for the parse; all downstream processing is free of API cost.
- Output tokens (content + reasoning) are the dominant recurring cost; reasoning was the major waste and is disabled in production.
- Input cost is negligible and further discounted by automatic prompt caching.
- The parser prompt is static and identical at the front of every request (cacheable prefix).
- Future analyzers compute all statistics from the saved evidence; the corpus is designed to make this cheap (sentence-per-record, traceable IDs, exact spans).

## 6. Completed Builder Stages

1. **Response loading/extraction** — loads the raw response JSON and extracts the parser JSON from `choices[0].message.content`.
2. **Parser JSON extraction** — parses the parser JSON object; parse failures are logged and the job is skipped (processing continues).
3. **Response validation** — calls `response_validator`; invalid responses are logged and skipped; no corrupted output.
4. **Character span recomputation** — deterministic `char_start`/`char_end` from the sentence text and ordered surfaces, guaranteeing `text[char_start:char_end] == surface`.
5. **Canonical chunk reconstruction** — chunk text rebuilt as the exact source slice `text[first_word.char_start : last_word.char_end]`, preserving whitespace and punctuation.
6. **Global ID assignment** — canonical IDs from processing order, independent of parser numbering.
7. **Section assignment** — deterministic sections from explicit boundaries, or a single default section.
8. **Provenance stamping** — source, source file, job number, model, prompt version, sentence id, sentence position.
9. **Source reconstruction verification** — mandatory exact-reconstruction integrity gate.
10. **Canonical JSONL writing** — UTF-8, newline-delimited, stable key ordering, byte-for-byte reproducible, duplicate-ID detection.
11. **Full integration testing** — end-to-end framework path validated on real data.

## 7. TASK 23–30 Completion Summaries

- **TASK 23 — Character spans:** `recompute_character_spans()` walks ordered surfaces left-to-right, greedy exact substring match (`text.find(surface, pos)`), guaranteeing the span invariant. Impossible reconstruction raises. Complexity effectively linear.
- **TASK 24 — Chunk text (first pass):** rebuilt chunk text as the surface concatenation.
- **TASK 24A — Chunk text correction:** canonical chunk text is now the **verbatim source slice** from the recomputed spans, so inter-word whitespace and punctuation are preserved exactly. `CorpusBuilderError` on invalid spans/indices.
- **TASK 25 — Global IDs:** `sentence_id` (per-source ordinal), `word_id = "{sid}.{i}"`, `chunk_id = "{sid}.c{i}"`, `expression_id = "{sid}.e{i}"`, attached under `ids`. Framework threads the per-source counter across jobs. Unique, stable, independent of parser numbering.
- **TASK 26 — Sections:** `assign_sections()` uses explicit boundary list `[{"section": id, "start": ordinal}]` when provided; otherwise assigns the deterministic default section (`"default"`). Canonical order regression and invalid boundaries raise.
- **TASK 27 — Provenance:** `stamp_provenance()` attaches `source`, `source_file`, `job_number`, `model`, `prompt_version`, `sentence_id`, `sentence_position`. Required fields enforced; parser provenance ignored/replaced; evidence unchanged.
- **TASK 28 — Reconstruction verification:** `verify_source_reconstruction()` requires `"\n\n".join(sentence_texts) == source_minus_markers_minus_trailing_newline` exactly. Reports first-difference character position. Verified on real Task 20 output.
- **TASK 29 — JSONL writer:** `write_jsonl_record()` serializes one canonical record per line (UTF-8, `ensure_ascii=False`, `sort_keys=True`), validates required fields, rejects duplicate `sentence_id`, and is byte-for-byte reproducible. Output path `Data Processor\jsonl\<source>.jsonl`.
- **TASK 30 — Integration:** full framework path run against a real request + raw parser response via temp fixtures (project folders untouched). Determinism, failure paths, and output verification all pass.

## 8. Integration Validation Results

- **79/79 tests pass** (corpus_builder_test.py).
- Complete successful pipeline on real data: 106 sentences → 106 canonical JSONL records, reconstruction verified.
- Determinism: two identical runs → byte-identical JSONL; identical IDs, provenance, sections, ordering.
- Failure paths verified: invalid parser JSON (skip + log + continue), validation failure (skip, no corrupt output), reconstruction failure (stops that source), duplicate ID (detected, output not corrupted), missing required metadata (rejected).
- Output verified: valid UTF-8, valid JSON per line, stable ordering, `text`/`ids`/`provenance`/`section` present, IDs unique, sentence text preserved exactly.
- Note: one real benchmark response (`bench_F_A`) is correctly rejected by the validator (a fatal expression-surface mismatch) — intended gate behavior; the integration fixture uses `bench_F_B`, which validates clean and reconstructs exactly.

## 9. Current Canonical Corpus Guarantees

For every record (one per sentence) the corpus guarantees:

- **Exact sentence text** — the original Japanese sentence preserved verbatim (verified by the reconstruction gate).
- **Exact word surfaces and lexical forms** — surfaces partition the sentence exactly; `lexical` is the dictionary/base form (or null).
- **Exact character spans** — deterministically recomputed; `text[char_start:char_end] == surface` for every word.
- **Canonical chunk text** — verbatim source slice; whitespace/punctuation preserved.
- **Unique, stable canonical IDs** — sentence, word, chunk, expression; traceable parent–child relationships (source → sentence → word/lexical → chunk → expression).
- **Deterministic section** — explicit boundary-based or the default section.
- **Complete provenance** — source, source file, job, model, prompt version, sentence position.
- **No LLM-invented values** — positions, IDs, sections, spans, chunk text are all Builder-computed.

## 10. Qwen Review Instructions / Questions

Please review `C:\Jprogram\Data Processor\corpus_builder.py`, `corpus_builder_test.py`, `response_validator.py`, `response_validator_test.py`, `PARSER_OUTPUT_SPEC.md`, `Prompts\parser_prompt.md`, and `README.md`, then answer:

1. **Architecture soundness:** Are the parser → validator → Builder → analyzer boundaries correctly drawn? Is there any leakage of responsibilities?
2. **Determinism:** Is every Builder stage provably deterministic (no hidden randomness, ordering dependence, or platform-dependent behavior)? Any place where "repeated runs produce identical output" could break?
3. **Evidence preservation:** Does the Builder ever alter, drop, or normalize source evidence? Is the exact-reconstruction gate (`verify_source_reconstruction`) correctly designed, and are its two permitted adjustments (marker-line removal, trailing file-terminator newline) sound?
4. **Span/chunk reconstruction:** Is the greedy surface-matching span recomputation correct for all whitespace-delimited and non-whitespace-delimited Japanese inputs, including duplicate surfaces and punctuation? Is the source-slice chunk reconstruction (`text[first.char_start : last.char_end]`) consistent with the recomputed spans?
5. **ID scheme:** Are the composite IDs (`sentence_id`, `word_id`, `chunk_id`, `expression_id`) unique, stable, and sufficient for all planned analyses (frequency, dispersion, distance, context retrieval, Anki extraction)?
6. **Validation/failure semantics:** Is it correct that char-span mismatches are non-fatal (Builder recomputes) while word-surface partition mismatches are fatal? Are there any silent-corruption paths that evade detection?
7. **JSONL writer:** Is the serialization byte-for-byte reproducible? Are duplicate-ID detection and the "never write corrupted records" guarantee sound? Is the per-record append + truncate-then-write framework behavior correct?
8. **Cost/efficiency:** Is "one LLM interpretation, then deterministic processing" the right economic model? Any redundancy the Builder could eliminate without sacrificing evidence?
9. **Test coverage:** Are the 79 tests sufficient? Which edge cases are missing (e.g., multi-job sources spanning section boundaries, degenerate/empty inputs, surrogate/codepoint edge cases)?
10. **Portability (future Chinese pipeline):** Does this Builder design generalize cleanly to a separate Chinese-language project, or are there Japanese-specific assumptions that would need revisiting?

---

*End of Builder milestone handover. No temporary notes included. Production code was not modified to produce this document.*
