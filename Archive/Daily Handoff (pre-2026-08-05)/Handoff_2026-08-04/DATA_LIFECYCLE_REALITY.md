# DATA_LIFECYCLE_REALITY

**Project:** Japanese Corpus Pipeline (C:\Jprogram)
**Date:** 2026-08-04
**Type:** Read-only trace of one real source item through the implemented pipeline.

**Traced source:** `podcast_transcript_ci-transcript_ep001`
(collection `ci_transcript`, episode 1 — the one source that was actually run
through the pipeline during real-data testing).

Every artifact below exists on disk and was read this session. The trace ends
at the known pre-fix failure: corpus creation failed because the run predates
the Parser Output Canonicalizer fix.

---

## Stage-by-Stage Trace

### 1. Source Creation

- **Module/file:** `Source Builder\controller.py` (`create_collection_source`)
- **Input:** collection metadata (collection_id `ci_transcript`, episode 1) +
  source text
- **Output artifact:**
  `Sources\collections\ci_transcript\ci_transcript_ep0001.txt`
  (+ Ready State Engine gating; save only when READY)
- **Ownership boundary:** Source Builder owns canonical file creation.

### 2. Source Storage + Source Package

- **Module/file:** `Source Builder\source_package.py` (`build_package` /
  `write_package`)
- **Input:** the canonical `.txt` file
- **Output artifact:**
  `Sources\collections\ci_transcript\ci_transcript_ep0001.source.json`
  (artifact_type `source_package`, schema_version 1, fields: source_id
  `podcast_transcript_ci-transcript_ep001`, source_type `podcast_transcript`,
  origin `user_transcription`, language `ja`, canonical_path, sha256,
  cleaning_profile `transcript_standard_v1`, cleaner_version, created_at,
  collection_id, episode)
- **Ownership boundary:** Source Builder owns the sidecar. Package errors are
  reported as warnings, not save failures.

### 3. Handoff

- **Module/file:** `Source Builder\handoff.py` (`handoff` / `handoff_for_package_path`)
- **Input:** source package
- **Output artifacts:**
  - `Source Registry\podcast_transcript_ci-transcript_ep001.json`
    (registry schema: identity, classification, processing, lineage refs)
  - `Cleaning Jobs\podcast_transcript_ci-transcript_ep001.cleaning_job.json`
    (cleaning job schema: source_id, raw_path, source_type, cleaning_profile,
    cleaner_version, output_path)
- **Ownership boundary:** Source Builder handoff (via Source Intake artifact
  writers `registry.py` / `cleaning_job.py`); idempotent by sha256.

### 4. Cleaning

- **Module/file:** `Transcript Cleaner\clean_transcript.py`
  (dispatched by `Production Manager\production_manager.py` `_cleaner_script`)
- **Input:** cleaning job → raw canonical file
- **Output artifacts:**
  - `Cleaned Archive\podcast_transcript_ci-transcript_ep001.clean.txt`
  - `Cleaning Results\podcast_transcript_ci-transcript_ep001.cleaning_result.json`
    (success true; 200 chars read, 199 written, blank_lines_removed 0)
- **Ownership boundary:** Cleaner owns cleaned artifact + Cleaning Result
  (written via Source Intake `cleaning_result.py` writer).

### 5. Processing — Job Creation

- **Module/file:** `Data Processor\job builder.py`
  (PM stage `jobs`)
- **Input:** cleaned text
- **Output artifacts:**
  - `Data Processor\jobs\podcast_transcript_ci-transcript_ep001\job_000001.json`
  - `Data Processor\Job Results\podcast_transcript_ci-transcript_ep001.job_builder_result.json`
- **Ownership boundary:** Job Builder owns job files + Job Result.

### 6. Processing — Request Creation

- **Module/file:** `Data Processor\request builder.py`
  (PM stage `requests`)
- **Input:** job file
- **Output artifacts:**
  - `Data Processor\requests\podcast_transcript_ci-transcript_ep001\request_000001.json`
    (top-level keys: `cleaned_artifact`, `job_number`, `messages`,
    `prompt_version`, `source_file`, `source_id`, `source_name`; the user
    message carries a `SOURCE METADATA:` block then `TEXT:` + the job text)
  - `Data Processor\Request Results\podcast_transcript_ci-transcript_ep001.request_builder_result.json`
- **Ownership boundary:** Request Builder owns request files + Request Result.

### 7. Parser (DeepSeek API)

- **Module/file:** `Data Processor\deepseek_client.py`
  (PM stage `api`; deepseek-v4-flash, non-thinking, json_object,
  max_tokens)
- **Input:** request file
- **Output artifacts:**
  - `Data Processor\responses\podcast_transcript_ci-transcript_ep001\response_000001.json`
    (raw response saved verbatim — "no content interpretation")
  - `Processing Results\podcast_transcript_ci-transcript_ep001.processing_result.json`
    (model deepseek-v4-flash, 1 job, http_status 200, finish_reason stop,
    completion 2379 / prompt 2855 tokens)
- **Ownership boundary:** deepseek_client owns raw response + Processing Result.

### 8. Canonicalization

- **Module/file:** `Data Processor\parser_normalizer.py` (`canonicalize`)
  — invoked inside `corpus_builder.process_job` (corpus_builder.py:797)
- **Input:** parsed parser output + job text (cleaned source extracted from the
  request via `extract_job_text`)
- **Output:** canonicalized parser output (sentence `text` replaced with
  clean-source sentence; char spans + chunk text recomputed; reconstruction
  verified)
- **Ownership boundary:** Parser Normalizer owns canonicalization. **Note:**
  the traced run predates this fix (see Stage 10), so no canonicalization
  evidence exists for this source on disk.

### 9. Validation

- **Module/file:** `Data Processor\response_validator.py`
  (`validate_parser_output` via `validate_response`)
- **Input:** canonicalized parser output + request metadata
- **Output:** validation verdict (valid/errors/warnings/summary) — a gate, no
  artifact written
- **Ownership boundary:** Validator owns gating only (never repairs).
  **Note:** the traced run hit the pre-fix fatal
  `WORD_SURFACE_PARTITION_MISMATCH` (surfaces omitted sentence-final
  punctuation); with the current punctuation-normalized partition check this
  is expected to pass.

### 10. Corpus Creation

- **Module/file:** `Data Processor\corpus_builder.py`
  (PM stage `corpus`; canonicalize → validate → build)
- **Input:** validated canonical records + request metadata
- **Output artifacts:**
  - `Data Processor\Corpus Results\podcast_transcript_ci-transcript_ep001.corpus_builder_result.json`
    — **present, `success: false`**, errors `["1 job(s) failed"]`,
    `jobs_failed 1`, `records_written 0`, `output_file null`, `verified false`
  - `Data Processor\jsonl\<source_id>.jsonl` — **NOT produced** (folder empty)
- **Ownership boundary:** Corpus Builder owns canonical JSONL + Corpus Result.
- **Failure cause (recorded):** the run at 2026-08-04 21:42 predates the
  canonicalizer fix (22:34–22:39); the validator rejected the response before
  any records were built. This is the documented real-data failure that the
  fix addresses and has **not yet been re-run**.

### 11. Analysis

- **Module/file:** `Source Builder\processing_tab.py` (`run_analysis`) +
  `Analysis\frequency_analyzer.py` / `corpus_loader.py` / `output_writer.py`
- **Input:** canonical JSONL corpus
- **Output artifact:** `Analysis\outputs\<source_id>.frequency.json`
- **Ownership boundary:** analyzers are read-only consumers; output is a
  derived data product.
- **Current state for this source:** none (no corpus exists).

---

## Artifact-to-Responsibility Summary

| Stage | Responsible module | Input artifact | Output artifact |
|---|---|---|---|
| Source creation | `Source Builder\controller.py` | metadata + text | `Sources\...\*.txt` |
| Source package | `Source Builder\source_package.py` | canonical file | `*.source.json` |
| Handoff | `Source Builder\handoff.py` (+ Source Intake writers) | package | Registry + Cleaning Job |
| Cleaning | `Transcript Cleaner\clean_transcript.py` (via PM) | Cleaning Job | `.clean.txt` + Cleaning Result |
| Jobs | `Data Processor\job builder.py` (PM stage jobs) | clean text | `jobs\...\job_*.json` + Job Result |
| Requests | `Data Processor\request builder.py` (PM stage requests) | job | `requests\...\request_*.json` + Request Result |
| Parser | `Data Processor\deepseek_client.py` (PM stage api) | request | `responses\...\response_*.json` + Processing Result |
| Canonicalization | `Data Processor\parser_normalizer.py` (inside corpus_builder) | parsed output + job text | canonicalized output (in-memory) |
| Validation | `Data Processor\response_validator.py` | canonicalized output | verdict (no artifact) |
| Corpus | `Data Processor\corpus_builder.py` (PM stage corpus) | canonical records + metadata | `jsonl\<source_id>.jsonl` + Corpus Result |
| Analysis | `Source Builder\processing_tab.py` + `Analysis\*` | canonical JSONL | `Analysis\outputs\*.frequency.json` |

**Ownership rule observed in practice:** each stage writes only its own
artifacts; the Production Manager only launches/observes; the GUI reads state
through the PM API plus direct package discovery.

---

*End of data lifecycle reality trace.* STOPPED.
