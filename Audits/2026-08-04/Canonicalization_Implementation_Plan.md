# Canonicalization Implementation Plan

**Project:** Japanese Corpus Pipeline (C:\Jprogram)
**Date:** 2026-08-04
**Type:** Audit/design only — no code changes.

**Purpose:** Define the design for introducing a canonicalization (parser-output
normalization) stage that runs before Response Validation, so the Corpus
Builder's existing sentence-restoration logic becomes reachable. This resolves
the real-data `WORD_SURFACE_PARTITION_MISMATCH` failure caused by the parser
omitting sentence-final punctuation from word surfaces.

---

## 1. New Module Location

**Proposed module:** `Data Processor\parser_normalizer.py`

Rationale:
- It sits in `Data Processor\` alongside the other deterministic stage
  utilities (`response_validator.py`, `corpus_builder.py`, `request builder.py`).
- Naming follows the existing convention (lowercase, underscore-separated),
  parallel to `response_validator.py`.
- It is **not** a result-writer, so no `_result` suffix.
- It imports only standard library (`json`, `pathlib.Path`) plus its own
  exception; it must NOT import `paths`, `project_config`, `response_validator`,
  or `corpus_builder_result` (verified: the moved functions have zero
  dependencies on those).

---

## 2. Public Function Signatures

```python
# parser_normalizer.py

class ParserNormalizerError(Exception):
    """Raised when parser output cannot be canonicalized."""

def canonicalize(
    parser_data: dict,
    cleaned_source_text: str,
) -> dict:
    """Return a canonicalized copy of parser_data.

    - Derives canonical sentence texts from cleaned_source_text.
    - Replaces each sentence's "text" with its canonical text.
    - Recomputes word char_start/char_end and chunk text.
    - Raises ParserNormalizerError on count mismatch or an unmatchable
      surface (never silently repairs).
    """

def canonical_sentence_texts(expected_text: str) -> list:
    """Return canonical sentence strings from the cleaned source text."""

def restore_sentence_text(records: list, canonical_texts: list) -> list:
    """Replace parser sentence text with canonical text; recompute spans."""

def recompute_character_spans(sentence: dict) -> dict:
    """Recompute word char_start/char_end from sentence text + surfaces."""

def recompute_chunk_text(sentence: dict) -> dict:
    """Rebuild chunk text as a verbatim slice of the sentence text."""

def verify_source_reconstruction(sentences: list, expected_text: str) -> dict:
    """Verify restored texts reproduce the clean source exactly."""
```

Supporting (private) helpers moved alongside:
`_expected_content(expected_text)`, `_is_section_marker_line(line)`,
`_first_diff_index(first, second)`, `_is_int(value)`,
`CANONICAL_LINE_SEPARATOR = "\n\n"`.

`CorpusBuilderError` remains the shared exception name (moved to
`parser_normalizer` and re-exported/aliased by `corpus_builder` for backward
compatibility, OR a new `ParserNormalizerError` subclass — decision point noted
in Risks).

---

## 3. Data Flow Before/After

### Current flow (`corpus_builder.process_source` / `process_job`)

```
Parser output (raw response)
  → extract_parser_content / parse_parser_content      (corpus_builder)
  → validate_parser_output → response_validator         (gate; FATAL on partition)
  → [per job] recompute_character_spans, recompute_chunk_text,
    assign_global_ids, assign_sections, stamp_provenance
  → [source] canonical_sentence_texts + restore_sentence_text
    + verify_source_reconstruction
  → JSONL write
```

### Proposed flow

```
Parser output (raw response)
  → extract_parser_content / parse_parser_content      (corpus_builder)
  → PARSER_NORMALIZER.canonicalize(parser_data, cleaned_source_text)
       (restore_sentence_text + recompute_character_spans
        + recompute_chunk_text, using the cleaned source)
  → validate_parser_output → response_validator         (gate; now sees
       canonical records; partition check passes because sentence text is
       authoritative and surfaces are matched against it)
  → [per job] assign_global_ids, assign_sections, stamp_provenance
  → verify_source_reconstruction (optional re-check after provenance)
  → JSONL write
```

Key changes:
- `canonicalize` runs **before** `validate_parser_output`, so the validator
  validates canonical records whose sentence `text` comes from the cleaned
  source and whose surfaces are matched to that text.
- The per-job recompute calls move into the normalizer (they are part of
  canonicalization); the builder retains global IDs / sections / provenance.
- `restore_sentence_text` no longer runs a second time in `process_source`
  (removed from lines 1240–1241) to avoid double work; the source-level
  `verify_source_reconstruction` may remain as the integrity gate.

---

## 4. Functions Moving from corpus_builder.py

Moved **verbatim** (no logic change) to `parser_normalizer.py`:

| Function | Live line range | Notes |
|---|---|---|
| `recompute_character_spans` | 101–167 | Pure; no pipeline deps |
| `recompute_chunk_text` | 169–309 | Pure; no pipeline deps |
| `_is_section_marker_line` | 659–662 | Helper |
| `_expected_content` | 665–681 | Helper |
| `canonical_sentence_texts` | 683–700 | Pure |
| `restore_sentence_text` | 703–742 | Pure |
| `_first_diff_index` | 745–752 | Helper |
| `verify_source_reconstruction` | 754–815 | Pure |
| `CANONICAL_LINE_SEPARATOR` | 83 | Constant |
| `CorpusBuilderError` | 86 | Exception (shared) |

**Not moved** (stay in `corpus_builder.py`): `assign_global_ids`,
`assign_sections`, `new_section_state`, `stamp_provenance`,
`jsonl_writer_state`, `canonical_output_path`, `write_jsonl_record`,
`request_files_for`, `load_request`, `extract_job_text`,
`job_text_from_user_content`, `response_path_for`, `load_response`,
`extract_parser_content`, `parse_parser_content`, `validate_parser_output`,
`process_job`, `process_source`, `run`, `main`, `write_result`, `write_log`,
`fail`, `append_log`, `start_log`, `write_atomic_text`.

`corpus_builder.py` then imports from `parser_normalizer` (e.g.
`from parser_normalizer import (canonicalize, canonical_sentence_texts,
restore_sentence_text, verify_source_reconstruction, CorpusBuilderError)`),
keeping a thin re-export so existing external references remain valid.

---

## 5. Tests That Move/Update

| Test file | Change |
|---|---|
| `Data Processor\tests\test_corpus_builder.py` (proper suite) | Update imports/references to moved functions: `restore_sentence_text` (lines 519, 559, 582, 592), `canonical_sentence_texts` (601, 606), `_expected_content` (604), `job_text_from_user_content` (771, 775 stays in corpus_builder). Tests 17–20 (restore/recompute/verify) move to a new `Data Processor\tests\test_parser_normalizer.py`; test 25 (job_text) stays. |
| `Data Processor\corpus_builder_test.py` (dev script, package root) | Extensive direct calls to `recompute_character_spans` (lines 74–236), `recompute_chunk_text` (267–415), `verify_source_reconstruction` (775–905). Update to import from `parser_normalizer`. |
| **New:** `Data Processor\tests\test_parser_normalizer.py` | New unit tests for `canonicalize`, `restore_sentence_text`, `recompute_character_spans`, `recompute_chunk_text`, `verify_source_reconstruction`, plus a regression test for the real punctuation-omission case (sentence `痛い。` with word `[0,"痛い",…]`) proving canonicalize succeeds and validation then passes. |
| `Data Processor\tests\test_corpus_builder.py` | Add/update an end-to-end test proving **canonicalize → validate → build** succeeds for the real-data punctuation case (currently untested ordering). |

---

## 6. Frozen Documents Requiring Updates

| Document | Required change |
|---|---|
| `PARSER_OUTPUT_SPEC.md` §3 (line 33) | "Word units never include the spaces or punctuation that separate them." → Add a canonicalization clause: punctuation may be omitted from word surfaces; a canonicalization stage restores authoritative sentence text before validation. |
| `PARSER_OUTPUT_SPEC.md` §14 (Validation Contract, lines 248–260) | Specify that the validator runs against **canonical** records (post-normalizer); the partition check is defined against the canonical sentence text, not the raw parser text. |
| `Prompts\parser_prompt.md` (lines 52, 79, 142) | Align the word-unit/punctuation instruction with the canonicalization decision (the model preserves punctuation in sentence `text`; punctuation need not be a word unit). |
| `SOURCE_TEMPLATE_SPEC.md` §9 (line 132) | Minor: confirm the canonicalization stage (not just the Corpus Builder) owns sentence-text authority. |
| `README.md` / `PROJECT_STATUS.md` | Update the pipeline narrative: Parser → **Parser Normalizer** → Response Validator → Corpus Builder; update the "validator vs builder" line (PROJECT_STATUS line 1080). |
| `response_validator.py` + `response_validator_test.py` (frozen behavior) | If the validator now receives canonical records, its partition check semantics and test 9 must be reviewed/updated (frozen-contract change requiring explicit approval). |

---

## 7. Migration Risks

| Risk | Impact | Mitigation |
|---|---|---|
| **Shared `CorpusBuilderError`** — moving it changes the exception namespace; `corpus_builder` and `response_validator` (if any) reference it. | High (import breakage) | Keep `CorpusBuilderError` in `parser_normalizer` and re-export from `corpus_builder` (or alias); update imports in both test files. |
| **Double restoration** — if `process_source` still calls `restore_sentence_text` after the normalizer, spans recomputed twice (idempotent but wasteful). | Low | Remove the post-validate restore call; keep only the source-level `verify_source_reconstruction`. |
| **Cleaned-source availability in the normalizer** — `canonicalize` needs the cleaned text; currently derived from request job text (`extract_job_text`). | Medium | Pass the cleaned text (or request_data) into `canonicalize`; keep `extract_job_text`/`job_text_from_user_content` in `corpus_builder` (unchanged). |
| **Validator semantics change** — validator now sees canonical records; its partition check/fatal classification must be re-decided. | High (frozen contract) | Handle as an explicit, approved contract change with updated tests; do not silently relax. |
| **Dev script `corpus_builder_test.py`** — heavy direct use of moved functions. | Medium | Update imports; it is a dev-only script (not in `tests\`). |
| **Chunk/expression span validity after canonicalization** — recomputing spans may change chunk text; ensure `start_word`/`end_word` still valid against canonical text. | Medium | `recompute_chunk_text` already slices by word spans; verify tests 17–18 cover the canonical-text case. |
| **Regression of the 722-test suite** — any import re-wiring risk. | Medium | Move functions verbatim; run full regression; keep `corpus_builder` re-exports. |

---

## 8. Rollback Plan

1. **Single-file move, single-commit discipline:** the migration is a
   mechanical relocation of pure functions plus an import change in
   `corpus_builder.py`. If anything breaks, revert to the pre-change state by
   restoring `corpus_builder.py` (keep the original as-is; the moved functions
   remain byte-identical).
2. **Backward-compatible re-export:** because `corpus_builder` re-exports the
   moved names (`restore_sentence_text`, `canonical_sentence_texts`,
   `recompute_character_spans`, `recompute_chunk_text`,
   `verify_source_reconstruction`, `CorpusBuilderError`), any code/tests that
   import from `corpus_builder` keep working even after the move — rollback is
   simply reverting the re-export + the `process_source` reorder.
3. **Ordering change is additive:** the normalizer call is added *before*
   `validate_parser_output`; if the new ordering fails, revert to calling
   validation first (the old behavior) without deleting the new module — the
   module is inert if not invoked.
4. **Frozen contracts:** no frozen document or validator behavior is changed
   in step 1. If the validator's partition semantics must change, that is a
   separate, explicitly-approved step with its own rollback (revert the
   validator/test change; the normalizer still runs but the gate remains as
   today).
5. **Verification:** after any step, run the full regression suite (722+
   tests). The rollback criterion is "regression returns to green with the old
   ordering" — which is guaranteed because the module is additive and the
   re-export preserves existing imports.

---

*End of canonicalization implementation plan.* STOPPED.
