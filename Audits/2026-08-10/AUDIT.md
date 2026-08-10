# Jprogram Audit — Targeted Check (issues found in the ThaiCorpus derivative)

Date: 2026-08-10
Scope: targeted re-check of the 7 issues found auditing ThaiCorpus (the Thai fork of this
project) against the corresponding code here in Jprogram, the original Japanese pipeline
Thai Corpus was renamed/derived from. Not a full independent audit.

---

- **File/Function:** `Source Intake/source_intake.py` — `_run_intake()`, Case E
- **Line Number/Range:** 299-315 (compare against `verdict["registry_exists"]` computed in `duplicate_check.py` 80)
- **Issue:** Identical to the ThaiCorpus finding — code is byte-for-byte the same in this file. `duplicate_check.check()` returns `registry_exists` as a distinct signal from `match_by_source_id`, but `_run_intake` never reads `registry_exists`; only `match_by_source_id`/`duplicate_by_hash` gate the branches.
- **Impact:** A schema-valid registry file at the target path with a mismatched internal `source_id` field falls through to Case E ("no existing registration") and gets silently overwritten by `registry.write_registry`.

---

- **File/Function:** `Data Processor/job builder.py` — `run()`
- **Line Number/Range:** 257-316
- **Issue:** Identical to the ThaiCorpus finding. `run()` unconditionally sets `success=True` regardless of `job_count`, and `write_job_files` never removes pre-existing `job_XXXX.json` files from a prior run before writing the current batch set.
- **Impact:** A cleaned artifact producing zero batches is still reported as a successful Job Builder run (`job_count=0`); a rerun that produces fewer batches than a previous run leaves orphaned job files that downstream stages (`deterministic_parser_client`/`corpus_builder`, via `job_files_for()`) will pick up alongside the current ones.

---

- **File/Function:** `project_config.py` — `REQUIRE_NONEMPTY_JOB`, `VERIFY_LINE_SEQUENCE`, `SKIP_EXISTING`, `CONFIRM_BEFORE_PROCESSING`, `COPY_TO_PROCESSING`
- **Line Number/Range:** 61-71, 77-83
- **Issue:** Identical to the ThaiCorpus finding. A project-wide grep confirms these five flags are referenced nowhere outside `project_config.py` itself.
- **Impact:** The validation guarantees these flags document (e.g. "every generated job contains at least one line") do not exist anywhere in the pipeline — this is the root cause enabling the Job Builder zero-job issue above.

---

- **File/Function:** `Source Intake/source_intake.py` — `_resolve_raw_path()`
- **Line Number/Range:** 150-177
- **Issue:** Identical to the ThaiCorpus finding — same file, same code. The `is_relative_to` `AttributeError` fallback (`str(path).startswith(str(raw_dir))`) is a naive string-prefix check with no separator boundary.
- **Impact:** Currently dead code (the project's interpreter has `Path.is_relative_to`), but a latent sibling-directory false-positive (e.g. `Raw Transcripts` vs. `Raw TranscriptsExtra`) if the fallback path is ever exercised.

---

## Issues checked but NOT present here

- **Curly-quote `in_quote` matching bug** (ThaiCorpus `parser/sentence.py` / `cleaner/novel.py`): no equivalent code exists in Jprogram. There is no `cleaner/` package and no dialogue/quote-tracking sentence splitter anywhere in this codebase (confirmed by grep for `quote_char`/`in_quote`/`QUOTE_CHARS` — zero matches). Sentence splitting here (`Common/sentence_split.py`, and `Data Processor/deterministic_parser.py`'s Part 1) is punctuation-only and never inspects quote characters. This bug was introduced new in the Thai fork, not inherited from here.

- **Sentence-punctuation-set drift between the cleaner and the parser** (ThaiCorpus `Common/sentence_split.py` vs. `parser/sentence.py`): not present. `Data Processor/deterministic_parser.py` imports `split_line` and `SENTENCE_FINAL_PUNCT` directly from `Common/sentence_split.py` (line 72: `from sentence_split import split_line, SENTENCE_FINAL_PUNCT`) rather than re-implementing its own copy, so the cleaner and the parser are provably using the identical rule — there is no second definition to drift out of agreement. The Thai fork replaced this shared-import design with an independent reimplementation in `parser/sentence.py`, which is where the drift was introduced.

- **Stale "Japanese Corpus Pipeline" branding** (`common.py print_header()`, `app.py` window title): not a defect here — this is the original Japanese-language project, so that branding is correct as written. (It only became a bug in ThaiCorpus, where the string was left behind after the project was renamed.)
