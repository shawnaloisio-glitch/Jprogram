# Code Quality and Architectural Adherence Audit — 2026-08-05

**Scope:** read-only code review, checked against this project's own
stated principles (one program = one task, verify over trust, no silent
repair, deterministic-by-default, source integrity/immutability) rather
than generic code-quality nitpicks. No changes made — findings only, for
Owner's review. Complements `DEEP_AUDIT_REPORT.md` (behavioral/documentation
audit, same date, different axis).

**Priority order:** Frozen Components first (highest stakes — the parts
Advisor can read but never touch), then subsystems never closely read
this session (Analysis, Production Manager, Common, Templates,
Diagnostics, Subtitle Importer). Areas already closely read as part of
this session's 9 Coder tasks (Source Builder's cleaners, Job Builder,
Metadata Editor, presets, config loader) are not re-covered here — low
marginal value, already verified against real diffs.

**May span a usage-window reset** — Owner's explicit go-ahead. Findings
are written incrementally per subsystem, not held until the end.

---

## 1. `Data Processor/response_validator.py`

Well-built overall: a genuinely pure, deterministic function, correctly
separates fatal from non-fatal errors, never repairs data it's checking
— exactly matches its own stated "gate, not a repair system" contract.

**Finding (risk, not a confirmed active bug):** `_PUNCTUATION` (line 124)
is a hardcoded frozenset of separator characters used to strip
whitespace/punctuation before comparing word-surface reconstruction
against sentence text. It includes common marks (、。！？「」etc.) but
is missing several punctuation marks that appear routinely in real
Japanese media text: wave dash `〜`/`～` (very common in casual/spoken
Japanese for elongation), interpunct `・` (names, lists), and em/en dashes
`―`/`—`. If the frozen parser correctly excludes one of these from a
word's surface (treating it as a separator, matching whatever the parser
prompt actually teaches), but the validator's `_PUNCTUATION` set doesn't
recognize it, `_normalize()` won't strip it from the sentence-text side
of the comparison — producing a **false-positive fatal
`WORD_SURFACE_PARTITION_MISMATCH`**, incorrectly rejecting a genuinely
correct parser response. This is an *inferred risk*, not something
observed failing — the QC Test Harness fixture never exercised text
containing these characters, so this gap hasn't been hit in practice
yet. The real underlying issue: nothing enforces that this hardcoded set
matches whatever the frozen parser prompt actually defines as
word-boundary punctuation — they're two independent sources of truth for
the same rule, coupled only by convention.

**Upgraded from inference to confirmed textual evidence:** checked
`Prompts/parser_prompt.md` directly. Line 142 says only "Word units
never include the spaces or punctuation that separate them" — open-ended,
no enumerated character list, leaving "punctuation" to the model's
judgment. Line 224 uses `～と思います` as a real example expression
pattern in the frozen prompt itself, confirming the wave-dash character
genuinely appears in this corpus's expected real content (casual
Japanese grammar patterns), not a hypothetical edge case. So the risk is
concrete, not manufactured: the prompt's instruction is genuinely broader
than the validator's hardcoded set, and the corpus is expected to contain
exactly the kind of character (〜/～) most likely to expose the gap.

**Confirms an existing WORKING_LIST.md item, not a new finding:**
`_validate_sentence`'s `sentence_index` check (lines 471-486) only
verifies non-negative and strictly-increasing — never checks for gaps
(e.g. `0, 1, 3` passes). Matches the already-tracked open item exactly.

## 2. `Data Processor/corpus_builder.py` + `parser_normalizer.py`

**Significant finding: the actual Frozen-architecture logic lives in a
file that isn't on the Frozen Components list.** `corpus_builder.py`'s
docstring and imports (lines 62-79) openly say it now *re-exports*
`canonicalize`, `verify_source_reconstruction`, `recompute_character_spans`,
`recompute_chunk_text`, `canonical_sentence_texts`, and
`restore_sentence_text` "for backward compatibility (previously owned by
this module)" — confirmed by reading `parser_normalizer.py` directly:
all six functions are genuinely defined there, not in `corpus_builder.py`.
This is exactly the "Frozen architecture (TASK 20/21)" logic the
project's own docs treat as the highest-stakes code in the pipeline (the
exact-reconstruction integrity gate, the authoritative-surfaces
recomputation). `CLAUDE.md`'s Frozen Components list names
`Data Processor/corpus_builder.py` but never mentions
`parser_normalizer.py` — meaning **a change to `parser_normalizer.py`
directly would not auto-trigger Advisor's audit check**, even though it's
where the actual frozen logic now lives. This looks like a real gap
opened by a prior refactor (moving the logic out of `corpus_builder.py`)
that the Frozen Components list was never updated to follow. Worth a
one-line addition to `CLAUDE.md`'s list — a judgment call for Owner, not
something to silently patch given it's a standing-instructions file.

**Finding: two independent JSONL-write mechanisms exist, only one of
which is actually used in production.** `write_jsonl_record()` (lines
470-536) is fully implemented, carefully documented (atomicity claims,
duplicate-`sentence_id` detection, stable key ordering), and has direct
test coverage in `test_corpus_builder.py` — but it's never called by the
real execution path. `run()` → `process_source()` (lines 858-927)
builds the entire output text in memory and writes the whole file at
once via `write_atomic_text()` instead (lines 911-915), never calling
`write_jsonl_record()`. So the function whose docstring makes the
strongest correctness claims about how records get written isn't
actually what writes them — the tests exercising it are verifying a code
path production doesn't take. Not a functional bug (the path that *is*
used is itself correctly atomic), but a real maintenance/trust hazard:
two sources of truth for "how does the corpus get written," and reading
the more heavily-documented one gives a misleading picture of actual
behavior.

**Minor finding:** `response_path_for()` (lines 608-624) falls back to
parsing a job number from the request filename when `request_data`
lacks one, and silently defaults to `job_number = 0` if that parse also
fails (line 622-623, bare `except ValueError`). This is a "silently
guess a value rather than fail loudly" pattern, which is the one thing
this project's own stated principle ("verify over trust... never
silently repair") explicitly warns against. Low real-world probability —
it requires both the request data and the filename to lack a usable job
number — but the failure mode if it ever triggers is silently looking
for the wrong response file rather than raising a clear error.

## 3. `Analysis/` modules vs. `ANALYZER_ARCHITECTURE.md`

**Analyzer Independence Principle (§8, frozen design) — confirmed intact.**
Checked every analyzer module's imports directly: none of the 9 modules
import another analyzer module. Each is genuinely a pure function taking
already-loaded `records` and returning a structured dict — real
independence, not just claimed independence.

**Significant finding: `output_writer.py` — the architecture's own
"deterministic derived-data writer" (§3, §7) — is never actually used by
production code.** Confirmed via repo-wide grep: the only import of
`output_writer` anywhere is its own test file
(`Analysis/tests/test_output_writer.py`). The one real production caller,
`Source Builder/processing_tab.py`'s `run_analysis()`, writes the
analysis result with a manual `json.dump(result, ..., ensure_ascii=False,
indent=2)` — **no `sort_keys=True`** — instead of calling
`output_writer.write_json()`, which does supply it. This is the same
shape of finding as `corpus_builder.py`'s unused `write_jsonl_record()`:
a properly-built, tested component the real path doesn't wire up to.

**Correction after reading the actual analyzer code (worth stating
plainly — my first-pass severity assessment here was overstated):**
I initially inferred this bypass could cause real byte-for-byte
non-determinism via Python's per-process string-hash randomization
affecting `set` iteration order. Having now read `frequency_analyzer.py`
and `distribution_analyzer.py` in full, that's not the actual risk here:
both build their output dicts via explicit `for key in sorted(items):`
at every nesting level (top-level lexical keys, and `frequency_analyzer`'s
nested `surfaces` dict too), and only use `set()` internally for
order-independent counting (`len(item["sentences"])`), never iterating
a set directly into output order. So these two analyzers' outputs are
already deterministically ordered by construction, independent of
`sort_keys` at the JSON layer — the missing flag doesn't actually risk
non-determinism for them specifically. **Update — all 9 modules now read, discipline confirmed consistent
throughout.** `exposure_analyzer.py`, `expression_analyzer.py`,
`chunk_analyzer.py`, `sentence_metrics.py`, and `comparison_analyzer.py`
all follow the identical pattern: `for key in sorted(items):` (or
equivalent `sorted()`-keyed construction) at every dict-nesting level,
`set()` used only for order-independent counting. `sentence_metrics.py`'s
top-level `sentences` list is deliberately left in canonical record order
rather than sorted — correct, since that's its documented, meaningful
order, not something that should be alphabetized.
`comparison_analyzer.py` additionally confirmed compliant with its own
frozen independence rule (§8): its `analyze(sources)` signature takes raw
canonical records per source directly (`each source's records from
corpus_loader`), never another analyzer's output — real independence,
not just a docstring claim. **Net conclusion:** the whole `Analysis/`
subsystem is genuinely well-built and deterministic by construction; the
one real, still-standing finding is narrower than my first pass suggested
— `output_writer.py` sits unused in production, a real gap from the
architecture's own stated design, but not a live correctness risk given
how carefully every analyzer already orders its own output.

## 4. `Production Manager/production_manager.py` (in progress, 1344 lines)

Well-architected overall so far: genuinely launches pipeline stages as
isolated subprocesses (confirmed no direct imports of any stage module —
matches its own "does NOT... import pipeline stage modules" claim
exactly), and `launch_stage()` correctly requires both a zero exit code
*and* a valid result artifact before reporting success — "Exit code alone
is never sufficient" is a real, enforced rule here, not just a comment.

**Confirmed defect, not a risk — a genuinely dead, duplicate branch in
the core state-machine function.** `state_for()` (lines 536-605) contains
two consecutive `elif` branches with the **exact same condition**:

```python
elif evidence["requests_count"] > 0:
    state = "requests_created"
elif evidence["requests_count"] > 0:      # line 579 — unreachable
    state = "requests_created"
```

The second branch (line 579-580) can never execute — if the identical
condition at line 576 was false, evaluating it again on the same
unchanged `evidence` dict is also false. Both branches assign the same
value, so this is functionally harmless today, but it's clear evidence of
either a copy-paste artifact left over from an edit, or — more
concerning — a distinct intermediate state that was meant to exist here
and got lost in a refactor, leaving a stub branch behind. Worth a quick
fix (delete the duplicate) and worth checking whether it signals a
missing state distinction that was actually intended.

## 5. `Data Processor/deepseek_client.py`

Careful, well-scoped transport layer — genuinely does only what its
docstring claims (send, receive, save raw, record metadata; never
interprets). API key handling matches the documented contract exactly
(never logged/printed/stored in response files; env var correctly
preferred over the file, consistent with the already-known name-collision
gotcha logged in `WORKING_LIST.md`). Retry logic (`send_with_retry`)
correctly distinguishes permanent failures (401/403 raises immediately,
other 4xx doesn't retry) from transient ones (429, 5xx, network errors
retry with backoff) — a genuinely well-thought-out state machine.

**Same fallback-to-zero pattern found a second time, now confirmed as
recurring rather than one-off.** `job_number_from_request()` (line 140)
has the identical "parse from filename, silently default to `0` if that
fails too" pattern already flagged in `corpus_builder.py`'s
`response_path_for()`. Two independent files now share the same
silent-guess risk for the same underlying value (a missing/unparseable
job number) — worth a single shared fix if this is ever addressed, not
two separate ones, since they're clearly meant to agree.

**Minor observation, not a real gap given the atomic-write guarantee:**
the resume/skip logic (`run()`, line 557) treats any pre-existing response
file as "completed" based purely on file existence — no re-validation of
its content, not even a basic JSON-parses check, before counting it as
done and moving on. `_completed_entry_from_existing()` calls
`extract_usage()` on it, which degrades gracefully to `None` token counts
if the file doesn't parse — so a corrupted existing file wouldn't crash,
but would silently report success with null usage metadata rather than
flagging the corruption at this stage. In practice this is well-guarded:
`save_response_atomic()`'s temp-file-then-replace pattern means this
client's own crash recovery can never produce a partially-written file in
the first place — the only way a corrupted response could exist here is
external tampering or a bug elsewhere, and downstream `response_validator.py`
would catch structural corruption regardless. Noted as a documented
design tradeoff (content validation is deliberately not this layer's job),
not a finding requiring action.
