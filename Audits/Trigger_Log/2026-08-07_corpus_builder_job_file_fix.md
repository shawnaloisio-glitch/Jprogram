# Trigger Log — 2026-08-07 — corpus_builder.py: job-file-based discovery fix (Phase 3, deterministic-parser)

**Work done:** Fixed a real architectural gap found while validating the
new deterministic parser against `QC Test Harness`: `corpus_builder.py`
required `request_*.json` files (Request Builder's output) to discover
jobs and extracted the canonicalization ground-truth text by parsing a
`"TEXT:\n"` marker out of the DeepSeek prompt. The new deterministic
path deliberately bypasses Request Builder, so it had no request file
and `corpus_builder.py` failed with "no requests found."

Fixed to discover jobs via `job_*.json` files directly (exists for
every source regardless of producer) and read `job_text` from
`job_data["text"]` directly, removing the fragile marker-parsing
extraction entirely. Request files became optional `prompt_version`
enrichment only. Also fixed a related, separate bug found in the same
investigation: provenance's `model` field was hardcoded to a constant
regardless of which producer actually ran — now read per-source from
that source's own `processing_result.json`, with a stated, deliberate
fallback to the constant if that file is missing/unreadable.

**Audit trigger: Yes (automatic — `corpus_builder.py` is Frozen).**
Per this branch's phase-boundary calibration (`CLAUDE.md`), the full
fresh-subagent Auditor pass is deferred to fire once per completed
phase, not per individual command — this command is mid-Phase 3, not
yet phase-complete (Production Manager wiring into the real app is
still pending). Logging the trigger decision now so it isn't lost;
the actual audit fires when Phase 3 as a whole is done, and again
before any merge to `master`.

**Verification summary:** Read the full diff directly (258 lines
changed in `corpus_builder.py`, 170 in its test file). Independently
re-ran, not trusting OC's report: `test_corpus_builder.py` (30/30, up
from a prior baseline of 24, with 3 new tests specifically covering the
deterministic path, the MODEL_NAME fallback, and the zero-job-files
case), `test_parser_contract.py` (10/10, zero regressions), and the
full remaining `Data Processor/tests/` suite (9 files total, zero
failures anywhere). Then independently re-ran the actual QC Test
Harness `check` stage against the real, currently-populated Workspace
myself: full ground-truth PASS — 犬 5/5 occurrences at exact expected
spacing, 猫 5/5 at exact expected spacing, 食べる 4/4 occurrences across
all four inflected surfaces correctly grouped to one lexical form (the
exact test case the day's merge-rule design work centered on), plus a
correct qualitative chunk match. This is the first real, ground-truth-
verified proof that the deterministic parser produces correct corpus
output through the actual production pipeline, not just isolated unit
tests.

**Verdict: CLEAN.**
