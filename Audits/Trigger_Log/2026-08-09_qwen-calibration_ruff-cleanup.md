# Qwen Calibration Trial — 2026-08-09 — ruff cleanup commit `36dc8be`

**Not a standard Auditor Trigger Log entry.** This is a calibration exercise,
not a real audit-trigger decision — testing whether a local Qwen2.5-Coder-7B
model (via Ollama, run locally on Owner's own GPU) can be trusted to handle
audit-tier review for genuinely low-risk changes, freeing the fresh-subagent
Claude Auditor for higher-stakes work. Explicitly logged for later
side-by-side comparison against a real Claude Auditor pass on this same
commit, planned for end of this session.

**Commit audited:** `36dc8be`, "Remove 9 confirmed-dead ruff findings from
Frozen Components" — already independently hand-verified by Advisor before
commit (direct grep confirming zero callers for each of the 9 removed
names, full 67/67 test suite green after). This is exactly the kind of
change the proposed Qwen tier is meant for: pure, provable dead-code
removal in Frozen files, not a behavior change.

**Method:** the commit's full diff (`git show 36dc8be`) fed directly as
plain text to `qwen2.5-coder:7b` via Ollama's local HTTP API
(`/api/generate`, single-shot prompt, no tool/file access, no streaming),
asking it to independently verify the removals are safe and that the three
claimed-protected re-exports were genuinely left untouched. 25 seconds
elapsed, 389 tokens generated.

**Result: Qwen's verdict was "CONCERNS FOUND" — incorrectly.**

The stated concerns were based on a real misread of the diff, not a real
issue:
- Qwen claimed `restore_sentence_text` was "explicitly removed from the
  import block." **False** — it was never touched; only
  `CANONICAL_LINE_SEPARATOR`, `recompute_character_spans`,
  `recompute_chunk_text`, `_is_section_marker_line`, and the bare
  `import parser_normalizer` were removed from that file.
- Qwen's own point 1 lists `canonicalize` and `verify_source_reconstruction`
  as "completely gone" alongside `restore_sentence_text` — **also false**,
  neither was removed.
- Qwen flagged a "discrepancy" between "9 confirmed-dead findings" and
  "only three mentioned imports removed" — this conflates the 3
  *deliberately-kept* names (mentioned in the commit message as false
  positives) with the count of things actually removed. The 9 removals are
  fully and correctly accounted for across all four files in the real diff.

In short: Qwen appears to have struggled to correctly track which lines
carried a `-` (removed) versus which were unchanged context in a unified
diff — a foundational parsing task for any code review, not a judgment
call it got wrong, a comprehension error.

**Verdict on Qwen, this trial only:** not yet trustworthy for even
low-risk automated verification in this basic prompt format (whole diff as
plain text, no tool access). Worth retrying with a different prompt
structure or a smaller/more targeted diff before drawing a final
conclusion — one trial is not enough to fully judge the model, but this is
a real, concrete failure, not a stylistic quibble.

**Next step:** run the real fresh-subagent Claude Auditor on this same
commit at end of session (already deliberately deferred, per Owner's
earlier instruction to hold the automatic-Yes trigger until then) and
compare results directly.
