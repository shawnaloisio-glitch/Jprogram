# QC Test Harness

A reusable, known-ground-truth test source for exercising the real
pipeline end-to-end (Source Builder birth-certificate creation through
Corpus Builder and the canonical JSONL corpus), using the actual
production functions and scripts -- not a reimplementation or a mock.
The `check` stage scans the canonical corpus records directly (no
Analysis/ module dependency, since 2026-08-09 -- see
`CLAUDE.md`'s Frozen Components note).

Because the test source is hand-authored with deliberately controlled
word placement, the expected analyzer output is known in advance
(`qc_test_001_expected.json`), so this doubles as independent QC: real
output gets checked against recorded expectations rather than just
trusted.

## Files

- `qc_test_001_source.txt` -- the test document (20 short Japanese
  sentences, one per line, single blank line between each -- matches the
  Transcript Cleaner's documented contract so it survives cleaning with
  sentence boundaries intact).
- `qc_test_001_expected.json` -- ground truth: which lexical items should
  appear, how many times, at which sentence positions, and the resulting
  frequency/distribution statistics.
- `run_qc_pipeline.py` -- orchestration script. Runs each real pipeline
  stage via its actual CLI entry point (subprocess, exactly like
  Production Manager would), then compares real analyzer output against
  the expected JSON.

## Usage

```
python "QC Test Harness/run_qc_pipeline.py" setup     # birth certificate + Registry + Cleaning Job
python "QC Test Harness/run_qc_pipeline.py" clean     # Transcript Cleaner
python "QC Test Harness/run_qc_pipeline.py" jobs      # Job Builder
python "QC Test Harness/run_qc_pipeline.py" requests  # Request Builder
python "QC Test Harness/run_qc_pipeline.py" send      # DeepSeek Client -- REAL API CALL, costs money
python "QC Test Harness/run_qc_pipeline.py" corpus    # Corpus Builder
python "QC Test Harness/run_qc_pipeline.py" check     # Compare real output against expected values
python "QC Test Harness/run_qc_pipeline.py" all       # Runs every stage above in order, including "send"
```

Every stage except `send` is free and makes no network call. `setup` is
idempotent (safe to re-run -- Source Intake's handoff reports "exists"
rather than duplicating). `send` resumes rather than re-sending if a
response file already exists; to force a fresh parse, delete
`responses\podcast_transcript_qc-test-001\` first.

`send` requires a valid `DEEPSEEK_API_KEY` environment variable. Set it
with `setx DEEPSEEK_API_KEY your-key-value` -- no quote characters
inside the value itself, only whatever your shell needs around it.

## Design notes (why the source text looks the way it does)

Three lexical items are deliberately placed at known sentence positions
(0-indexed, canonical order):

- **犬 ("dog")** -- 5 occurrences, every consecutive gap exactly 3
  sentences apart. Positive test case for a "learning threshold" rule
  like *>=5 occurrences with >=3 sentences between instances*.
- **猫 ("cat")** -- also 5 occurrences (same frequency as 犬), but
  clustered (min gap = 1). Negative-control case: proves frequency alone
  doesn't satisfy a spacing-based threshold -- distribution must be
  measured separately from frequency (formerly documented in
  `ANALYZER_ARCHITECTURE.md`, now archived at
  `Archive/ANALYZER_ARCHITECTURE.md`; the principle itself lives on in
  Language Coach's analyzer).
- **食べる ("to eat")** -- 4 occurrences across 4 different inflected
  surfaces (食べました / 食べません / 食べて / 食べる). Tests that the
  real DeepSeek parser correctly groups inflected forms under one
  dictionary-form lexical key, per `PARSER_OUTPUT_SPEC.md` §4.

One filler sentence (position 19) reuses the exact grammar pattern from
`PARSER_OUTPUT_SPEC.md`'s own worked example (ことにしました) as a
qualitative chunk-extraction check -- not hard-asserted, since exact word
spans are the parser's judgment call.

First run: 2026-08-05, first send attempt failed with HTTP 401 (the
`DEEPSEEK_API_KEY` value had stray quote characters pasted into it from
a `setx "..."` command) -- confirmed a key-formatting issue, not a
pipeline defect. Retry once a valid key is set.
