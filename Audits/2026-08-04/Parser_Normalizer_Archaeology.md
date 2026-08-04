# Parser Normalizer Archaeology Audit

**Project:** Japanese Corpus Pipeline (C:\Jprogram)
**Date:** 2026-08-04
**Type:** Archaeology audit — no files modified.

**Question:** Was there ever a parser normalization/canonicalization stage
between Parser output and Response Validation?

---

## Summary Answer

**No.** A separate parser normalizer / canonicalizer stage (module or
function) between Parser output and Response Validation **never existed** in
the live code, in the V1_FREEZE reference set, in the Daily Handoff archives,
in the documentation/spec files, or in any backup (there is no git history).

The "normalization / canonicalization / sentence restoration" responsibilities
were always designed and implemented as **part of the Corpus Builder**, which
sits *after* the Response Validator — not between Parser and Validator.

---

## 1. Did a separate normalizer module/function ever exist?

**No dedicated normalizer module or standalone function ever existed.**

Search results across the whole project for every requested concept
(`parser normalizer`, `normalization`, `canonical sentence`, `canonical text`,
`sentence restoration`, `restore sentence`, `clean source authority`,
`source sentence`, `sentence rewrite`, `response normalization`,
`parser post-processing`, `validator preprocessing`,
`parser output transformation`):

| Location | Findings |
|---|---|
| Live `Data Processor\*.py` | No normalizer file. `response_validator.py` has only a private `_normalize(text)` helper (removes whitespace, for evidence comparison) and its docstring says "It normalizes nothing and corrects nothing." `corpus_builder.py` owns `canonical_sentence_texts()` + `restore_sentence_text()`. |
| Live `Data Processor` file inventory | `corpus_builder.py`, `corpus_builder_result.py`, `corpus_builder_test.py`, `deepseek_client.py`, `job builder.py`, `job_builder_result.py`, `process_file.py`, `processing_result.py`, `request builder.py`, `request_builder_result.py`, `response_validator.py`, `response_validator_test.py`. **No normalizer file.** |
| Tests | `response_validator_test.py` and `corpus_builder_test.py` contain no normalizer references; only `canonical_record`/canonical-id test helpers in the corpus builder test. |
| V1_FREEZE `Reference Files\Data Processor` | `corpus_builder.py`, `corpus_builder_result.py`, `deepseek_client.py`, `job builder.py`, `job_builder_result.py`, `processing_result.py`, `request builder.py`, `request_builder_result.py`, `response_validator.py`. **No normalizer file.** |
| Daily Handoff archives | `HANDOFF_2026-07-31.md`, `HANDOFF_2026-08-01_QWEN_BUILDER_REVIEW.md`, `HANDOFF_2026-08-02_FLASH_EXPRESSION_POLICY.md`, GUI/Builder design docs — no normalizer stage mentioned. |
| Documentation / specs | `PARSER_OUTPUT_SPEC.md`, `SOURCE_TEMPLATE_SPEC.md`, `README.md`, `PROJECT_STATUS.md` — pipeline is always Parser → Response Validator → Corpus Builder → Analyzer; normalization is explicitly owned by the Corpus Builder. |
| Backups / history | No `.git` repo; no `.bak`/`.old`/`.orig` code files (only Config JSON backups). No prior `response_validator` version exists other than the frozen copy, which is byte-identical to the live file (same SHA-256). |

**No class/function named `normalizer`, `normalize_parser_output`,
`canonicalizer`, `restore`, or `post_process` was ever present as a standalone
pipeline step.**

---

## 2. Was the normalization step previously at any specific placement?

The normalization/sentence-restoration logic was always located in **option D —
inside the Corpus Builder only**:

- `corpus_builder.canonical_sentence_texts(expected_text)` — derives canonical
  sentence text from the cleaned source (docstring: "The cleaned transcript is
  the authoritative source of sentence text").
- `corpus_builder.restore_sentence_text(records, canonical_texts)` — replaces
  parser "text" with canonical text, recomputes spans/chunk text
  (docstring: "Move sentence text ownership from the parser to the Corpus
  Builder").
- `corpus_builder.verify_source_reconstruction(records, expected_text)` —
  source-level integrity gate.
- Called at the **source level** in `process_source` (lines 1240–1241), i.e.
  *after* the per-job Response Validation gate.

It was **never**:
- A) at the end of parser processing — no; the parser (`deepseek_client.py`)
  explicitly saves the raw response with "no content interpretation".
- B) between parser and validator — no.
- C) inside validator preprocessing — no; the validator is explicitly a
  gate ("normalizes nothing and corrects nothing").

---

## 3. Compare live code against V1_FREEZE

| Aspect | Live (2026-08-04) | V1_FREEZE (2026-08-01/02) | Difference |
|---|---|---|---|
| `response_validator.py` | Present | Present (Reference Files) | **Identical** (same SHA-256) |
| `parser_prompt.md` | Present | Present | **Identical** (same SHA-256) |
| `corpus_builder.py` | 1431 lines | 1407 lines | Live adds `extract_job_text` + `job_text_from_user_content` (Request Builder SOURCE-METADATA fix) — an additive lineage change; **not** a normalization-stage change |
| `restore_sentence_text` / `canonical_sentence_texts` | Present (lines 683, 703; called 1240–1241) | Present (lines 683, 703; called 1216–1217) | Present in both; call order unchanged (after validation gate) |
| Pipeline ordering | Parser → Validator → Corpus Builder | Parser → Validator → Corpus Builder | Unchanged |
| Extra live files | `corpus_builder_test.py`, `process_file.py`, `response_validator_test.py` (dev scripts, not in freeze) | — | Dev-only; not pipeline stages |

**No missing files, no moved functions, no merged normalizer responsibilities.**
The only change in the frozen set is the additive `extract_job_text` helper in
`corpus_builder.py`. There was never a normalizer to have been moved or merged.

---

## 4. Trace the current pipeline

```
Parser output creation (deepseek_client.py)
   ↓  raw response saved verbatim to responses\<source_id>\response_XXXXXX.json
       (explicitly "no content interpretation"; no transformation)
   ↓
Response Validator (response_validator.py)   ← gate; validates ONLY the parser
       response in isolation; has NO access to the cleaned source
       - structure, indices, spans, chunk/expression validity
       - word-surface partition check against the parser's own sentence text
         (fatal on mismatch)
       - "normalizes nothing"
   ↓  (validation must pass; else job counted failed, no records produced)
Corpus Builder (corpus_builder.py)
       - per job: recompute char spans, chunk text, global ids, sections, provenance
       - source level: canonical_sentence_texts(cleaned) →
         restore_sentence_text(records, canonical_texts) →
         verify_source_reconstruction
   ↓
Canonical JSONL (one sentence = one record)
```

The intended design (cleaned sentence authoritative; validator validates
annotations; builder restores canonical sentence) is implemented **entirely
inside the Corpus Builder**, downstream of the validator. There is no
transformation step between Parser output creation and the validator.

---

## 5. If a previous normalizer existed — restore vs recreate

**There was no previous separate normalizer to restore.** The sentence
restoration / canonicalization logic exists today in
`corpus_builder.restore_sentence_text` + `canonical_sentence_texts` and is
proven functional (simulated restoration of the real failing data: 20 records
restored, `verify_source_reconstruction` returned verified=True).

The relevant question is therefore not "restore a normalizer" but whether the
existing downstream restoration path is reachable. Currently it is gated behind
the Response Validator's fatal `WORD_SURFACE_PARTITION_MISMATCH` check, which
runs before any records reach the builder. Evidence of placement and reachable
state is reported above; no fix recommendation is made in this audit.

---

## 6. Evidence Index (no fixes recommended)

- `Data Processor\corpus_builder.py`: `canonical_sentence_texts` (line 683),
  `restore_sentence_text` (line 703), `validate_parser_output` (line 1039),
  per-job validation gate in `process_job` (lines 1144–1157), source-level
  restore in `process_source` (lines 1240–1241).
- `Data Processor\response_validator.py`: docstring "normalizes nothing"
  (lines 21–22); `_normalize` helper (line 120); `_validate_partition`
  (line 232, fatal partition mismatch, line 239–247).
- `Data Processor\deepseek_client.py`: docstring "no content interpretation"
  (lines 16–19).
- `README.md` line 473: "The Corpus Builder ... normalizes records".
- `SOURCE_TEMPLATE_SPEC.md` §9: "the cleaned transcript is the canonical
  authority for sentence text (the Corpus Builder owns sentence text)".
- `PARSER_OUTPUT_SPEC.md` line 6: contract boundary is
  Parser → Response Validator → Corpus Builder → Analyzer.
- `Daily Handoff\HANDOFF_2026-07-31.md` (line 141) and
  `HANDOFF_2026-08-01_QWEN_BUILDER_REVIEW.md` (line 35): "the Corpus Builder
  must deterministically recompute character spans and chunk text" — confirms
  normalization is a builder responsibility.
- V1_FREEZE reference files are byte-identical to live for
  `response_validator.py` and `parser_prompt.md`; no normalizer exists in the
  frozen set either.
- No git history exists (`C:\Jprogram\.git` absent); no backup code files
  beyond Config JSON backups.

---

*End of parser normalizer archaeology audit.* STOPPED.
