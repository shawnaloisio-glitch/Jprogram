# Qwen Calibration — alibayram/mimo-7b-rl (new model) + deepseek-r1:14b re-run on the reconstructed harness

Two things in this entry: (1) the first run of a new model,
`alibayram/mimo-7b-rl` (a second RL-reasoning-tuned model, pulled fresh
this session — 4.68GB via `ollama pull alibayram/mimo-7b-rl`), on the
same 3 reconstructed trials used for `deepseek-coder-v2:16b`
(`2026-08-08_qwen-calibration_deepseek-coder-v2-16b.md`); (2) a re-run
of `deepseek-r1:14b` — the only model to score 3/3 in the original
campaign — on that same reconstructed harness, to check whether its
clean sweep holds up on this exact wording (it does not fully hold up;
see below).

## Result: mimo-7b-rl scores 3/3 — a second clean sweep

| Model | Score (original harness) | Score (reconstructed harness) |
|---|---|---|
| qwen2.5-coder:7b | 1/3 | — |
| qwen2.5-coder:14b | 2/3 | — |
| deepseek-r1:14b | 3/3 | **2/3** |
| deepseek-coder:6.7b | ~0.5/3 | — |
| deepseek-coder-v2:16b | — | 0/3 |
| **alibayram/mimo-7b-rl** | — | **3/3** |

### mimo-7b-rl, trial 1 (diff-parsing) — CORRECT
Correctly identified the 7 names visibly removed via `-` lines in the
diff (missed the `test_sentence_metrics.py` dead-reassignment line and
undercounted relative to the commit message's "9," but explicitly
flagged that discrepancy rather than fabricating extra removals to make
the count match). Correctly confirmed `restore_sentence_text`,
`canonicalize`, and `verify_source_reconstruction` were NOT removed.
Correct "safe" verdict. Notably slow and verbose: 318s, 12,088 tokens
of visible chain-of-thought, including repeated self-correction and
uncertainty about its own line-counting before settling on the right
answer — expensive, but it got there and was honest about what it
wasn't sure of.

### mimo-7b-rl, trial 2 (execution-tracing) — CORRECT
Correctly traced `cue.split("\n")` producing two lines, correctly
derived the fragmented two-piece output, correctly judged that output
against the stated goal (single sentence must survive an unpunctuated
line-wrap) and correctly concluded BUG. 53s, 2,690 tokens. Some visible
mid-reasoning text corruption (stray phrases like "VERY MUCH" appear
in the scratch reasoning, apparently a decoding artifact), but it did
not affect the final traced values or verdict.

### mimo-7b-rl, trial 3 (cross-file reasoning) — CORRECT
Correctly concluded NOT SAFE TO DELETE, with reasoning that explicitly
and correctly walks through *why* `ruff`'s single-file analysis misses
the `cb.` alias usage, and does not contradict itself the way
`deepseek-coder-v2:16b` did on the identical setup. 44.5s, 2,413 tokens.

## deepseek-r1:14b re-run on the reconstructed harness — 2/3, NOT a clean
repeat of the original 3/3

Run to check whether the original campaign's only clean sweep replicates
on this session's reconstructed trial wording (the original harness
script was not found on disk — see the caveat in the
`deepseek-coder-v2-16b` log entry).

**Trial 1 (diff-parsing) — WRONG this time, different failure shape
than any model seen so far.** Its removed-names list this run was
merely incomplete (missed `CANONICAL_LINE_SEPARATOR`, `import json`,
`from pathlib import Path` — no hallucinated kept-names, unlike
`deepseek-coder-v2:16b`), and it correctly confirmed all three
kept-name checks. But its final verdict flipped to "potential safety
concerns," citing two fabricated risks not supported by the diff: that
the dead `result =` reassignment removed from
`test_sentence_metrics.py` "might affect other parts relying on it,"
and that `verify_paths`'s removal "potentially caus[es] issues
elsewhere if used externally." Ground truth (confirmed by the real
fresh-subagent Auditor pass logged in
`2026-08-09_ruff-cleanup_auditor_pass.md`) is CLEAN, no concerns — both
were confirmed dead via repo-wide grep, not local-file analysis alone.
86s, 647 tokens — notably terser and faster than the original
campaign's 93.7s/trial-1 run, consistent with a materially different
(more targeted, 3-part) prompt producing different — and here, worse —
behavior.

**Trial 2 (execution-tracing) — CORRECT**, matching the original
result: correct trace, correct BUG verdict. 92s, 1,332 tokens.

**Trial 3 (cross-file reasoning) — CORRECT**, matching the original
result: correct NOT SAFE TO DELETE with sound reasoning. 35s, 511
tokens.

## Why this matters more than the score itself

The original 3/3 headline for `deepseek-r1:14b` does not hold up
unchanged against a differently-worded version of the same underlying
task. This is not evidence that `deepseek-r1:14b` is actually worse
than previously thought — it's evidence that **a single 3-trial run,
without prompt-wording control or repeated sampling, is not a stable
enough signal to certify any model for even a low-risk audit tier.**
Two live confounds, neither of which this exercise (across any model
tested so far) has controlled for:
1. **Prompt sensitivity** — this trial 1 asked three explicit,
   separately-numbered sub-questions instead of however the original
   was phrased; that alone may be enough to change which parts of the
   diff the model attends to.
2. **Sampling variance** — no `temperature`/`seed` was fixed in any
   trial run in this whole exercise (original campaign or this
   session's), so even a byte-identical prompt run twice is not
   guaranteed to produce the same output.

Both are answerable with more rigor (fix `temperature`/`seed`, run each
trial N>1 times per model, hold the exact prompt text constant and
version it in a real file instead of reconstructing from memory each
session) — but that is real additional cost, which cuts against the
whole point of this exercise (finding a cheap way to offload
verification work). Recommend treating every score in this whole
calibration series, on every model including the two 3/3s, as a
directional signal only, not a certification, until a controlled
multi-run version is actually done — or a decision is made that the
stakes of the judgment-call-No audit tier are low enough not to need
that rigor.

## Cost tradeoff, updated
`mimo-7b-rl`'s trial 1 (318s, 12k tokens) is by a wide margin the most
expensive single trial run in this entire exercise — more than 3x
`deepseek-r1:14b`'s slowest trial. Its trials 2-3 were unremarkable in
cost. If pursued further, `mimo-7b-rl`'s trial-1-shaped tasks
(diff-parsing) in particular would need a token/time budget check
against whatever it's meant to be saving.
