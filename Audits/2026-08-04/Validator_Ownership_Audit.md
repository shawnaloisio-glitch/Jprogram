# Validator Ownership Audit

**Project:** Japanese Corpus Pipeline (C:\Jprogram)
**Date:** 2026-08-04
**Type:** Audit only — no files modified.

**Question:** Did the Response Validator previously have a mode where sentence
text / content reconstruction was not validated?

---

## Answer

**No.** The Response Validator never had a lenient/optional mode for sentence
text or word-surface reconstruction validation. There is no validation flag,
no strict/lenient toggle, and no code path that skips the
`WORD_SURFACE_PARTITION_MISMATCH` check. That check has been **fatal** since
the validator was frozen (V1_FREEZE 2026-08-01), and it is byte-identical in
the live code.

---

## 1. Was sentence text validation ever optional?

**No.**

- `validate_response(response, expected_source_name=None, expected_job_number=None)` (line 508) has exactly two optional parameters — both for request-metadata identity matching. There is no flag controlling sentence-text or partition validation.
- The validator contains no `strict`/`lenient`/`mode`/`skip`/`tolerance`/`optional` switches anywhere.
- Live `response_validator.py` is byte-identical to the V1_FREEZE reference copy (same SHA-256), so no mode was ever removed.
- No test, doc, or audit file references an optional/lenient sentence-validation mode.

The only "optional" validation in the validator is the identity check via
`expected_source_name` / `expected_job_number` (line 508) — unrelated to
sentence reconstruction.

---

## 2. Was WORD_SURFACE_PARTITION_MISMATCH intended to be fatal?

**Yes — explicitly and by design.**

- `response_validator.py` line 72 defines the constant; `_validate_partition`
  (line 232) is documented as "the critical evidence-preservation test".
- `_add_error(...)` defaults to `fatal=True` (line 98); the partition check
  does not pass a non-fatal flag, so it is fatal.
- `response_validator_test.py` test 9 (lines 164–171) explicitly asserts:
  `check("partition error fatal", any(e["fatal"] for e in r["errors"]))` and
  `check("not valid", r["valid"] is False)`.
- PROJECT_STATUS (TASK 21, line 1147): "**Fatal vs non-fatal distinction:**
  character-span mismatches are reported as non-fatal (the Corpus Builder
  recomputes them from the authoritative surfaces); everything else ...
  **word-surface partition mismatch** ... is **fatal**."
- PROJECT_STATUS (TASK 21, line 1146): the word-surface partition test is a
  listed validator responsibility.
- The design intent (corpus_builder.py lines 24–25; PROJECT_STATUS line 1138):
  "Ordered word surfaces are authoritative because they exactly partition each
  sentence." The partition check is the enforcement of that evidence-integrity
  invariant.

---

## 3. What fields was the validator originally intended to own?

Per PROJECT_STATUS (line 1146) and the validator docstring (lines 13–22), the
validator owns **structural and evidence-integrity validation only**, and is
explicitly a gate ("normalizes nothing and corrects nothing"):

- Top-level structure and required fields.
- Sentence-level structure and `sentence_index` monotonicity.
- Word validation and indices.
- Chunk validation (record shape, spans, non-overlap).
- Expression validation.
- **Source-identity comparison** against request metadata (the optional
  `expected_source_name`/`expected_job_number`).
- **Word-surface partition test** (evidence integrity — fatal).

The validator does **not** own:
- Character-span correctness — `WORD_CHAR_SPAN_MISMATCH` is explicitly
  **non-fatal** (test 7/8, lines 143–161): "still valid for builder".
- Sentence text authority — the Corpus Builder owns sentence text
  (SOURCE_TEMPLATE_SPEC §9; corpus_builder `restore_sentence_text`).

So the validator was intended to validate the parser's annotations/structure
and that word surfaces are internally consistent with the parser's own
sentence text — while the Corpus Builder owns sentence text authority and
recomputation.

---

## 4. Did corpus_builder restoration assume the validator had already ignored sentence text?

**No — the opposite.** The restoration path does **not** assume the validator
ignored sentence text; it assumes the validator's partition check passed
against the parser's own text, and then independently takes sentence-text
ownership.

Evidence:

- `corpus_builder.py` lines 24–25: "Ordered word surfaces are authoritative
  because they exactly partition each sentence" — i.e., the builder's design
  relies on the validator having confirmed the surfaces reconstruct the
  parser's own sentence text.
- `restore_sentence_text` (line 703) is documented to "Move sentence text
  ownership from the parser to the Corpus Builder... The parser's own 'text'
  field is ignored" — it replaces `text` with the cleaned-source canonical
  text and recomputes spans/chunk text against it.
- `corpus_builder` test (lines 505–542) proves the intended interaction: a
  parser sentence `大きく 変わる こと が できます` (which the surfaces DO
  partition) is restored to the canonical `大きく 変わる ことが できます`, and
  spans/chunk text are recomputed. This fixture would pass the validator's
  partition check (surfaces reconstruct the parser's own text) and then be
  restored by the builder.
- `verify_source_reconstruction` (line 754) validates the **restored canonical
  texts** against the clean source — it is independent of the parser's word
  surfaces and does not depend on the validator's partition verdict.

The current real-data failure differs from this design expectation: the model
emitted surfaces that do **not** include sentence-final punctuation, so the
surfaces do not partition even the parser's own text — the validator rejects
before restoration is reached. The restoration logic itself is proven to work
on the real data (simulated restore + reconstruction verified True in the
Parser_Normalizer_Archaeology audit).

---

## 5. Smallest architectural restoration point

Evidence-only options (no recommendation made):

- **A) Disable sentence reconstruction validation** — would require changing
  the frozen validator's `_validate_partition` (either skip the partition
  check or reclassify it as non-fatal). This contradicts the frozen design
  (PROJECT_STATUS TASK 21 explicitly calls it fatal evidence corruption) and
  the validator test 9.
- **B) Move restoration before validation** — would reorder the Corpus
  Builder flow so `restore_sentence_text` runs before `validate_parser_output`
  (or move the partition/restore logic ahead of the gate). This matches the
  intended "Corpus Builder owns sentence text" design (SOURCE_TEMPLATE_SPEC
  §9) and the existing `restore_sentence_text` capability, but changes the
  frozen `process_job` ordering (validate → build).
- **C) Something else** — e.g., align the parser prompt / PARSER_OUTPUT_SPEC
  so the model emits punctuation as separate word units (as the benchmark and
  corpus_builder test fixtures do), making the validator's partition check
  pass against the parser's own text; or treat the partition check as
  validating the parser's self-consistency rather than the canonical source.
  The frozen prompt and spec currently instruct the model that "word units
  never include punctuation" (parser_prompt.md line 142; PARSER_OUTPUT_SPEC §3
  line 33), which conflicts with the validator's requirement and with the
  corpus_builder test fixture that includes `。` as a word.

No recommendation is offered; this reports the evidence only.

---

## Evidence Index

- `Data Processor\response_validator.py`: docstring "normalizes nothing"
  (lines 21–22); `WORD_SURFACE_PARTITION_MISMATCH` (line 72); `_add_error`
  default fatal (line 98); `_validate_partition` (line 232); `validate_response`
  signature (line 508, only identity-optional params).
- `Data Processor\response_validator_test.py`: span non-fatal (lines 143–161);
  partition fatal (lines 164–171); benchmark clean (lines 265–280).
- `Data Processor\corpus_builder.py`: "surfaces are authoritative because they
  exactly partition each sentence" (lines 24–25); `restore_sentence_text`
  (line 703); `verify_source_reconstruction` (line 754); restore call
  (lines 1240–1241).
- `Data Processor\tests\test_corpus_builder.py`: restore test with differing
  parser vs canonical text (lines 505–542); valid fixture includes `。` as a
  separate word unit (lines 700–708).
- `PROJECT_STATUS.md`: TASK 21 fatal/non-fatal + responsibilities
  (lines 1146–1149); validator-vs-builder (line 1080).
- `SOURCE_TEMPLATE_SPEC.md` §9: "the Corpus Builder owns sentence text".
- `PARSER_OUTPUT_SPEC.md` §3 (line 33): "Word units never include the spaces
  or punctuation that separate them."
- `Prompts\parser_prompt.md` (line 142): same punctuation rule.
- V1_FREEZE reference `response_validator.py` is byte-identical to live.
- No git history; no audit doc describes a validator leniency mode.

---

*End of validator ownership audit.* STOPPED.
