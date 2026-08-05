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

## 3. `Data Processor/deepseek_client.py`

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
