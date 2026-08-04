# CURRENT_TEST_STATE

**Project:** Japanese Corpus Pipeline (C:\Jprogram)
**Date:** 2026-08-04
**Type:** Read-only test-state report.

---

## Test Command Used

```
python "C:\Users\Shawn\AppData\Local\Temp\opencode\run_all_tests.py"
```

The runner executes every `test_*.py` file under `C:\Jprogram` (all suites)
as a subprocess and aggregates the per-file `Tests: N  Passed: N  Failed: N`
summary lines. Tests are self-contained scripts with a `TESTS` list and an
inline runner (no pytest/unittest).

**Excluded from the run (documented, dev-only):**
- `Data Processor\corpus_builder_test.py` — dev script hardcoding external
  benchmark path `C:\Users\Shawn\AppData\Local\Temp\opencode\parser_bench`.
- `Data Processor\response_validator_test.py` — same external-path dependency.

---

## Results

| Metric | Value |
|---|---|
| Test files executed | 60 |
| **Total tests** | **740** |
| **Passing tests** | **735** |
| **Failing tests** | **5** |

---

## Failure Breakdown

| Suite | Failures | Test names |
|---|---|---|
| `Source Builder\tests\test_source_builder_quick_presets.py` | 1 | `default_source_type_for_collection resolves via config` |
| `Source Builder\tests\test_source_builder_gui_presets.py` | 4 | `preset click populates fields once: collection failed.` · `preset does not modify form after activation: origin untouched by manual edits failed.` · `manual edits are never overwritten by the preset afterwards: collection stays failed.` · `standalone preset populates identity and source name: source type failed.` |

All other 58 files pass fully (including `Data Processor\tests\`
test_parser_normalizer 12/12 and test_corpus_builder 28/28).

---

## Classification of the 5 Failures

**Classification: stale fixtures tied to the live Config — NOT code defects,
NOT environment issues.**

Evidence:
- The failing tests query the **live `Config\`** (no sandbox redirect) for
  values that were removed during the metadata cleanup:
  - `teppei_beginner` (removed collection) — quick_presets failure.
  - `con_teppei_podcast`, `article`, `nhk_news`, `teppei_beginner` (removed
    vocabulary) — gui_presets failures.
- These are the same 5 failures documented in `Final_Baseline_Audit.md`
  (2026-08-04), `Project_Audit.md`, and `Session_Handoff_Audit.md` — they
  predate this session and are known/expected.
- No new failures were introduced by the Parser Output Canonicalizer work
  (that change touched `Data Processor\` only; all Data Processor suites pass).
- The tests run identically on a clean interpreter run; there is no
  environment/import/encoding issue (all other 735 tests execute and pass).

**Recommended resolution (not performed — read-only task):** neutral
fixtures/sandboxing of `Config\` in those two suites, or removal of the
stale-value fixtures.

---

## Suite-Level Summary

| Suite dir | Files | Tests | Pass | Fail |
|---|---|---|---|---|
| tests\ (root, app shell) | 1 | 9 | 9 | 0 |
| Analysis\tests\ | 9 | 78 | 78 | 0 |
| Common\tests\ | 1 | 26 | 26 | 0 |
| Data Processor\tests\ | 6 | 108 | 108 | 0 |
| Integration\tests\ | 1 | 10 | 10 | 0 |
| Production Manager\tests\ | 7 | 77 | 77 | 0 |
| Source Builder\tests\ | 20 | 274 | 269 | 5 |
| Source Intake\tests\ | 12 | 106 | 106 | 0 |
| Subtitle Cleaner\tests\ | 1 | 15 | 15 | 0 |
| Subtitle Importer\tests\ | 1 | 16 | 16 | 0 |
| Templates\tests\ | 1 | 8 | 8 | 0 |
| Transcript Cleaner\tests\ | 1 | 17 | 17 | 0 |
| **Total** | **60** | **740** | **735** | **5** |

---

## Caveats

- The two dev-only `*_test.py` scripts in `Data Processor\` (package root) are
  not part of this count; they require external benchmark data and would fail
  on another machine.
- No real end-to-end pipeline run (real subprocess + real API → real corpus →
  real analysis) is exercised by any automated suite; that is documented as
  remaining real-data validation work, not covered here.

---

*End of current test state.* STOPPED.
