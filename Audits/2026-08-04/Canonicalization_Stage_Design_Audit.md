# Canonicalization Stage Design Audit

**Project:** Japanese Corpus Pipeline (C:\Jprogram)
**Date:** 2026-08-04
**Type:** Design audit — no implementation, no file modifications.

**Context:** The real-data pipeline failure
(`WORD_SURFACE_PARTITION_MISMATCH` on every sentence) occurs because the
Response Validator's partition check runs before the Corpus Builder's
sentence-restoration step, and the parser model omits sentence-final
punctuation from word surfaces. This audit examines what a
canonicalization/normalization stage between Parser and Validator would
require, whether the existing functions can be reused, and which frozen
contracts would change.

---

## 1. What exact transformations are required before validation?

The Corpus Builder's existing deterministic functions define the transformation
set needed to canonicalize a parser response **before** validation:

| # | Transformation | Function (corpus_builder.py) | Purpose |
|---|---|---|---|
| 1 | **Sentence replacement** | `restore_sentence_text` (line 703) + `canonical_sentence_texts` (line 683) | Replace the parser's `text` field with the canonical sentence text derived from the cleaned source; the parser's own `text` is ignored (docstring line 709–710). |
| 2 | **Span recalculation** | `recompute_character_spans` (line 101) | Recompute every word's `char_start`/`char_end` so `text[char_start:char_end] == surface`, using the canonical sentence text. Parser spans ignored. |
| 3 | **Chunk text recalculation** | `recompute_chunk_text` (line 169) | Rebuild each chunk's `text` as the verbatim slice `sentence_text[first_word.start : last_word.end]`. Parser chunk text ignored. |
| 4 | **Count verification** | `restore_sentence_text` (line 729) | Raise `CorpusBuilderError` if canonical sentence count != record count. |
| 5 | **Surface-match verification** | `restore_sentence_text` → `recompute_character_spans` | Raise if a surface cannot be matched in the canonical sentence (no silent repair; test 19). |
| 6 | **Source-level reconstruction gate** | `verify_source_reconstruction` (line 754) + `_expected_content` (line 665) | Verify restored texts reproduce the clean source exactly (whitespace/punctuation preserved). This is the builder's own integrity gate, independent of the validator. |

**Not needed before validation:** global IDs (`assign_global_ids`, line 313),
section assignment (`assign_sections`), provenance (`stamp_provenance`) — these
are builder-stage responsibilities that operate on canonical records and can
stay after validation.

**Important verified fact:** `recompute_character_spans`' greedy `text.find`
works even when surfaces omit sentence-final punctuation (verified: `痛い` is
found in `痛い。`; `こと`/`が` are found in canonical `ことが`). The functions
only require each surface to be **findable in order** in the canonical text —
they do NOT require the validator's strict "surfaces reconstruct all
non-whitespace chars" guarantee. So a pre-validation canonicalization is
technically feasible with these exact functions.

---

## 2. Can restore_sentence_text() be moved without duplication?

**Yes — the function is self-contained and import-safe, so it can move (or be
called from) a pre-validation stage without code duplication.**

Evidence:
- `restore_sentence_text` calls only `recompute_character_spans` and
  `recompute_chunk_text`, which depend only on `CorpusBuilderError` and the
  sentence dict — no builder-global state, no file I/O, no pipeline ordering
  state.
- `canonical_sentence_texts` and `_expected_content` depend only on the
  cleaned-source text and the canonical line separator constant.
- `restore_sentence_text` is already unit-tested in isolation
  (tests 17–19), proving it has no hidden dependency on being called from
  `process_source`.

**Constraint (not duplication, but a dependency to relocate):**
`restore_sentence_text` needs the **cleaned source text** to derive canonical
sentences. In the current flow that text comes from the request's job text via
`extract_job_text` / `job_text_from_user_content` (lines 926–966) in
`process_source`. A pre-validation normalizer would need access to the same
cleaned source (the request carries it under the `TEXT:` marker; the cleaned
artifact is on disk). So moving the call requires moving/importing the
`extract_job_text`/`job_text_from_user_content` helpers too (or passing the
cleaned text in), but **not duplicating** the transformation logic.

The cleanest non-duplicating move: relocate the call site (or import these
deterministic helpers) rather than copying the functions.

---

## 3. What is the cleanest ownership?

| Option | Assessment (evidence) |
|---|---|
| **A. New ParserOutputNormalizer module** | Viable and cleanest for ownership clarity. It would own `canonical_sentence_texts`, `restore_sentence_text`, `recompute_character_spans`, `recompute_chunk_text`, `_expected_content` (move, not copy). `corpus_builder` would import them. This matches the frozen principle that sentence text authority belongs outside the parser (SOURCE_TEMPLATE_SPEC §9) and gives the normalizer an explicit owner. Downside: introduces a new module/ownership boundary that must be reflected in tests and docs. |
| **B. Move existing corpus_builder functions** | Equivalent to A's mechanism (relocating the functions) but keeps them under the builder. This preserves the current "Corpus Builder owns sentence text" doctrine and requires the least structural change (reorder `process_job`/`process_source` so restore runs before validation). No new module; no duplication. |
| **C. Validator pre-processing step** | **Not recommended.** The validator is explicitly frozen as "a gate, not a repair system. It normalizes nothing and corrects nothing" (response_validator.py lines 21–22) and PROJECT_STATUS TASK 21. Adding restoration inside the validator would violate its frozen ownership boundary and mix normalization with gating. |

**Evidence-based cleanest:** **B** (reorder the existing builder flow so
restoration runs before validation, calling the existing functions) is the
smallest change; **A** (a dedicated module owning the moved functions) is the
cleanest long-term ownership if a named stage is desired. Both avoid
duplication. **C** contradicts the frozen validator contract.

---

## 4. What tests prove the architecture?

`Data Processor\tests\test_corpus_builder.py` (27 tests) — the architectural
proofs are:

| Test | Proves |
|---|---|
| **17. corpus builder owns sentence text (parser text ignored)** (line 502) | `restore_sentence_text` replaces parser text with cleaned-source text; JSONL uses canonical text; spans/chunk text match canonical. |
| **18. offset verification still succeeds after restore** (line 545) | Recomputed spans/chunk text are exact slices of the canonical text even when the parser split `ことが` → `こと が`. |
| **19. deliberately incorrect offset still fails** (line 569) | Unmatchable surface or count mismatch raises `CorpusBuilderError` — no silent repair. |
| **20. canonical sentence splitting matches expected content** (line 598) | `canonical_sentence_texts` + `_expected_content` reconstruct the clean source deterministically. |
| **23. validator accepts empty expressions** (line 691) | Validator/restore/builder accept the Flash empty-expressions policy. |
| **24. corpus validation passes with metadata-supplied request** (line 711) | End-to-end: request metadata + restored corpus validation passes. |
| **25. job_text_from_user_content strips the metadata header** (line 763) | Cleaned job text extraction (needed to derive canonical sentences). |

`response_validator_test.py` proves the validator's non-ownership: char-span
errors are **non-fatal** and response still "valid for builder" (tests 7–8),
while partition mismatch is **fatal** (test 9).

These tests collectively prove the two-stage ownership: the builder
canonicalizes/owns sentence text (17–20), and the validator gates structure/
evidence without owning sentence text (validator tests 7–9). They do **not**
currently test restoration running *before* validation (that ordering change is
untested).

---

## 5. What frozen contracts must change?

| Contract | Current frozen statement | Required change (if a pre-validation normalizer or reorder is adopted) |
|---|---|---|
| **PARSER_OUTPUT_SPEC.md** §3 (line 33) | "Word units never include the spaces or punctuation that separate them." | Reconcile with the validator's partition requirement and the canonicalization design: either state punctuation may be omitted from word surfaces (and validation is performed after canonicalization), or require punctuation as word units. This is the central spec conflict. |
| **PARSER_OUTPUT_SPEC.md** §14 (lines 248–260) Validation Contract | Validator checks `text[char_start:char_end] == surface` and word-surface partition; fatal. | Clarify the ordering: if canonicalization runs before validation, the validator should validate against the **canonical** sentence text (post-restore), not the parser's raw text; and the partition check must be defined against the canonical text. |
| **Prompts\parser_prompt.md** (lines 52, 79, 142) | "Preserve punctuation and all surface text" + "Word units never include the spaces or punctuation that separate them." | Align with the decision: either the model must emit punctuation as word units, or the prompt must reflect that punctuation is preserved in sentence `text` and handled by canonicalization (not required in the word layer). |
| **SOURCE_TEMPLATE_SPEC.md** §9 (line 132) | "the cleaned transcript is the canonical authority for sentence text (the Corpus Builder owns sentence text)." | Already consistent with a pre-validation canonicalizer; may need a wording touch to name the canonicalization stage's owner, but does not contradict the design. |
| **README.md / PROJECT_STATUS.md** (architecture narrative) | Pipeline drawn as Parser → Response Validator → Corpus Builder. | If a normalizer stage is added or ordering changes, update the pipeline description and the "validator vs builder" line (PROJECT_STATUS line 1080). |
| **response_validator.py / response_validator_test.py** (frozen behavior) | Partition mismatch fatal; validator "normalizes nothing". | If canonicalization precedes validation, the validator's input becomes canonical records; its partition check (or its role) must be redefined, and test 9 updated. This is a frozen-contract change requiring explicit approval. |

---

## Summary

- The transformation set needed before validation is exactly what
  `corpus_builder` already implements: sentence replacement
  (`restore_sentence_text`), span recalculation (`recompute_character_spans`),
  chunk-text recalculation (`recompute_chunk_text`), plus count and
  surface-match verification. Global IDs/sections/provenance can remain
  post-validation.
- `restore_sentence_text` is self-contained and can move/call without
  duplication; the only relocated dependency is access to the cleaned source
  text (via the existing `extract_job_text`/`job_text_from_user_content`
  helpers or the on-disk clean artifact).
- Cleanest ownership: **B** (reorder the existing builder functions so
  restoration runs before validation) is the smallest change; **A** (a
  dedicated ParserOutputNormalizer module owning the moved functions) is the
  cleanest long-term named stage; **C** (validator pre-processing) contradicts
  the frozen validator gate contract.
- Tests 17–20 (and validator tests 7–9) already prove the two-stage
  ownership; an ordering change (restore-before-validate) is currently
  untested.
- The frozen contracts that must change are primarily **PARSER_OUTPUT_SPEC.md**
  (§3 punctuation rule, §14 validation contract), **parser_prompt.md**
  (punctuation/word-unit instruction), and the frozen **validator behavior/
  test 9**; SOURCE_TEMPLATE_SPEC and README/PROJECT_STATUS narratives would
  need minor updates.

*End of canonicalization stage design audit.* STOPPED.
