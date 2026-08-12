# Artifact Contract Trace

Purpose: a concrete, currently-verified example of every artifact in the
pipeline chain — Source Registry through canonical JSONL — captured
directly from real files on disk, not reconstructed from schema docs.
Companion to the abstract contracts in `TODO.md` §8;
read this when you need to see what a real instance actually looks like,
not just what it's supposed to look like. See the "Live Artifact Contract
Trace" practice section in `TODO.md` (currently
§15) for when to refresh it.

**Last captured:** 2026-08-05, from `source_id =
podcast_transcript_qc-test-001` (the QC Test Harness's standing fixture —
see `QC Test Harness/README.md`). Sections 1, 2, 5, 6 (Source Registry,
Source Package, parser response, canonical JSONL) are a read-only capture
from an earlier real run, including a real DeepSeek API call — untouched
since, and still accurate (nothing between Request Builder and Corpus
Builder has changed). Sections 3–4 (Cleaning Job, Cleaning Result) were
re-captured via a genuine live re-run of the `clean` and `jobs` stages
later the same day, specifically to confirm TASK 8's new hash-enforcement
code against real on-disk data rather than only unit-test fixtures — both
free, no-network stages, no DeepSeek call needed since TASK 8 never
touched Request Builder or the parser.

**Update trigger:** refresh this file after any change to a pipeline-stage
program (Source Intake writers, a cleaner, Job Builder, Request Builder,
the parser prompt, `response_validator.py`, `corpus_builder.py`) that could
alter an artifact's actual shape. Re-pull a fresh real example (QC harness
or real production data) and replace the relevant section below — don't
just edit the JSON by hand to match a new schema; pull it from a real run.

---

## 1. Source Registry entry

`Jprogram Workspace/Source Registry/podcast_transcript_qc-test-001.json`

```json
{
    "cleaner_version": "1.0",
    "cleaning_profile": "transcript_standard_v1",
    "format": "txt",
    "language": "ja",
    "original_filename": "qc_test_001.txt",
    "schema_version": "1",
    "sha256": "314d0b3bf0186cd009c7286a3f40038d842ba9a3377e8393adfdf791cba2111d",
    "source_id": "podcast_transcript_qc-test-001",
    "source_type": "podcast_transcript"
}
```

## 2. Source Package sidecar

`Jprogram Workspace/Sources/standalone/qc_test_001.source.json`

```json
{
  "artifact_type": "source_package",
  "schema_version": "1",
  "source_id": "podcast_transcript_qc-test-001",
  "source_type": "podcast_transcript",
  "origin": "qc_test",
  "language": "ja",
  "canonical_path": "C:\\Jprogram Workspace\\Sources\\standalone\\qc_test_001.txt",
  "original_filename": "qc_test_001.txt",
  "format": "txt",
  "cleaning_profile": "transcript_standard_v1",
  "cleaner_version": "1.0",
  "sha256": "314d0b3bf0186cd009c7286a3f40038d842ba9a3377e8393adfdf791cba2111d",
  "created_at": "2026-08-05T15:18:15",
  "created_by_version": "1.0",
  "source_name": "qc_test_001"
}
```

## 3. Cleaning Job

`Jprogram Workspace/Cleaning Jobs/podcast_transcript_qc-test-001.cleaning_job.json`

```json
{
    "cleaner_version": "1.0",
    "cleaning_profile": "transcript_standard_v1",
    "output_path": "C:\\Jprogram Workspace\\Cleaned Archive\\podcast_transcript_qc-test-001.clean.txt",
    "raw_path": "C:\\Jprogram Workspace\\Sources\\standalone\\qc_test_001.txt",
    "schema_version": "1",
    "source_id": "podcast_transcript_qc-test-001",
    "source_type": "podcast_transcript"
}
```

## 4. Cleaning Result

`Jprogram Workspace/Cleaning Results/podcast_transcript_qc-test-001.cleaning_result.json`

```json
{
    "cleaned_artifact": "C:\\Jprogram Workspace\\Cleaned Archive\\podcast_transcript_qc-test-001.clean.txt",
    "cleaner_version": "1.0",
    "completion_time": "2026-08-05 20:46:16",
    "errors": [],
    "output_hash": "314d0b3bf0186cd009c7286a3f40038d842ba9a3377e8393adfdf791cba2111d",
    "schema_version": "1",
    "source_id": "podcast_transcript_qc-test-001",
    "statistics": {
        "blank_lines_removed": 0,
        "bom_removed": false,
        "characters_read": 263,
        "characters_written": 263,
        "repeated_spaces_removed": 0,
        "trimmed_lines": 0
    },
    "success": true
}
```

Note: raw `sha256` and cleaned `output_hash` match exactly here only
because this fixture required zero cleaning changes (all statistics are
0) — that's a coincidence of this specific source, not evidence on its
own that raw-vs-cleaned hash verification is enforced.

**Updated 2026-08-05:** it now is. TASK 8 (same day, see
`Audits/OC_Reliability_Log.md`) added enforcement at both cleaners'
entry points (re-hash `raw_path` against the Source Registry's recorded
`sha256`, fail closed) and at Job Builder (re-hash the cleaned artifact
against this Cleaning Result's `output_hash`, fail closed). Confirmed
directly, not just by reading the diff: re-ran the `clean` and `jobs`
stages live against this real fixture post-TASK-8 (`completion_time`
above reflects that re-run) — identical `output_hash`, `errors: []`,
`success: true`. The new fail-closed hash check ran for real against
real on-disk data and passed cleanly; this isn't inferred from the code
or from unit tests alone.

## 5. Raw parser response (DeepSeek), excerpt

`Jprogram Workspace/responses/podcast_transcript_qc-test-001/response_000001.json`
(full file has all 20 sentences; first two shown)

```json
{
  "source_name": "podcast_transcript_qc-test-001",
  "job_number": 1,
  "sentences": [
    {
      "sentence_index": 0,
      "text": "犬が公園にいます。",
      "words": [[0, "犬", "犬", 0, 1], [1, "が", "が", 1, 2], [2, "公園", "公園", 2, 4], [3, "に", "に", 4, 5], [4, "います", "いる", 5, 8], [5, "。", "。", 8, 9]],
      "chunks": [[0, "犬が", 0, 2], [1, "公園に", 2, 4], [2, "います", 4, 5], [3, "。", 5, 6]],
      "expressions": []
    },
    {
      "sentence_index": 1,
      "text": "猫が家にいます。",
      "words": [[0, "猫", "猫", 0, 1], [1, "が", "が", 1, 2], [2, "家", "家", 2, 3], [3, "に", "に", 3, 4], [4, "います", "いる", 4, 7], [5, "。", "。", 7, 8]],
      "chunks": [[0, "猫が", 0, 2], [1, "家に", 2, 4], [2, "います", 4, 5], [3, "。", 5, 6]],
      "expressions": []
    }
  ]
}
```

Confirms inflection grouping works correctly in real output: elsewhere in
this same response, 食べました / 食べません / 食べて / 食べる all
resolve to the same lexical key `食べる` (`PARSER_OUTPUT_SPEC.md` §4).

## 6. Canonical JSONL line (post-Validator, post-Corpus-Builder)

`Jprogram Workspace/jsonl/podcast_transcript_qc-test-001.jsonl`, line 1

```json
{"chunks": [[0, "犬が", 0, 2], [1, "公園に", 2, 4], [2, "います", 4, 5], [3, "。", 5, 6]], "expressions": [], "ids": {"chunk_ids": ["0.c0", "0.c1", "0.c2", "0.c3"], "expression_ids": [], "sentence_id": 0, "word_ids": ["0.0", "0.1", "0.2", "0.3", "0.4", "0.5"]}, "provenance": {"job_number": 1, "model": "deepseek-v4-flash", "prompt_version": "1.0", "sentence_id": 0, "sentence_position": 0, "source": "podcast_transcript_qc-test-001", "source_file": "C:\\Jprogram Workspace\\Cleaned Archive\\podcast_transcript_qc-test-001.clean.txt", "source_id": "podcast_transcript_qc-test-001"}, "section": "default", "sentence_index": 0, "text": "犬が公園にいます。", "words": [[0, "犬", "犬", 0, 1], [1, "が", "が", 1, 2], [2, "公園", "公園", 2, 4], [3, "に", "に", 4, 5], [4, "います", "いる", 5, 8], [5, "。", "。", 8, 9]]}
```
