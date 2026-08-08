# Qwen Calibration Summary — 2026-08-09 — 3 trials

Follow-up to `2026-08-09_qwen-calibration_ruff-cleanup.md` (trial 1). Two
more trials run the same day, same model (`qwen2.5-coder:7b` via local
Ollama, RX 6700 XT, confirmed GPU-accelerated via Vulkan). All three used
real project history as ground truth — no fabricated test cases.

**Correction from trial 1's log:** that write-up used `num_ctx` default
(4096, confirmed from Ollama's own server log). Trials 2 and 3 explicitly
raised `num_ctx` to 16384 to rule out context-window truncation as a
confound — both still small enough to fit at either size, so this doesn't
change trial 1's verdict, but is worth noting for future trials on larger
diffs (the Topic field commit, ~1000 lines, would need this raised).

## Trial 1 — clean commit, whole-diff-as-text format (see separate log)
**Result: FALSE POSITIVE.** Verdict "CONCERNS FOUND" on a commit Advisor
had already hand-verified clean. Root cause: misread which lines carried
`-` (removed) vs. context in the unified diff — claimed
`restore_sentence_text` was removed when it was never touched, and
flagged a non-existent "discrepancy" in the removal count.

## Trial 2 — real regression, code-execution tracing required
**Setup:** reconstructed OC's actual first (flawed) attempt at the
Subtitle Importer fix from earlier this session — the version that
pre-split each cue on internal `\n` before checking punctuation, which
really did fragment a single sentence wrapped across two display lines
into a bogus fragment + completion. This is a real bug Advisor caught via
direct code execution, not by inspection, before it was ever committed.

**Result: FALSE NEGATIVE — missed the bug, verdict "CORRECT."** Notably,
Qwen's own trace *correctly described* the code's actual behavior in one
step ("splits each line by newline to process individually") but then
did not actually execute that description in its next step — it ran
`split_line()` on the un-split combined string instead of the two pieces
its own stated algorithm would produce, arriving at a coincidentally
clean-looking (and wrong) answer. This is a code-execution-simulation
failure, not a knowledge gap — it stated the right mechanism and then
didn't follow it.

## Trial 3 — cross-file usage reasoning, evidence handed directly
**Setup:** the actual known `ruff` blind spot in `corpus_builder.py` —
three imports `ruff` flags as unused because it can't see they're called
externally via a module alias (`cb.restore_sentence_text(...)` etc.) in
`test_corpus_builder.py`. Unlike trials 1-2, this test handed Qwen both
pieces of evidence directly (the import block, and the exact external
usage lines) rather than asking it to locate or trace anything itself.

**Result: CORRECT.** "NOT SAFE TO DELETE," with accurate reasoning about
why `ruff`'s single-file static analysis missed the cross-file usage.
6.5s, notably faster and more direct than trials 1-2.

## Overall read

**2 failures out of 3, and the failure pattern is consistent and
diagnostic, not random:** Qwen (this model, this basic prompt-only
format, no tool access) is unreliable at two specific mechanical tasks —
precisely parsing unified-diff +/- markers, and simulating multi-step
code execution — but reasons correctly once given clean, pre-gathered
evidence and a direct, well-posed question.

**Implication for how a Qwen tier should actually work, if pursued
further:** not as a general "review this diff, tell me if it's safe"
tool (where it failed twice) — that's exactly the shape of trials 1-2.
It may still be useful as a narrower, second-opinion tool for
specific, pre-formulated claims Advisor has already investigated (closer
to trial 3's shape: "here's the evidence, does this specific conclusion
follow"), which is a much smaller and different role than a real
auditor pass. Not yet validated as a replacement for any current audit
tier — this remains a trial, not a decision.

**Next step, per Owner's original plan:** run the real fresh-subagent
Claude Auditor on the `36dc8be` ruff-cleanup commit at end of session
(still deliberately deferred) and compare directly against trial 1's
result on that same commit.
