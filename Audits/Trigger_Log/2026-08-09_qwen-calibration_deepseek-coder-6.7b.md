# Qwen Calibration — 2026-08-09 — deepseek-coder:6.7b, same 3 trials

Same trials, same harness. Weakest result of the 4 models tested so far
(qwen2.5-coder:7b 1/3, qwen2.5-coder:14b 2/3, deepseek-r1:14b 3/3,
deepseek-coder:6.7b this entry).

**Trial 1: technically "CLEAN" (right verdict), reasoning confused.**
Conflates `CorpusBuilderError`/`verify_source_reconstruction` -- names
never touched in the diff and never part of the "3 deliberately kept"
set -- with the actual protected names. Raises an unfounded concern
about `test_corpus_builder.py` losing "functionalities," not supported
by anything in the diff. Right answer, not for fully sound reasons.

**Trial 2: no committed verdict, real bug mechanism missed.** Presents
two hypothetical scenarios without tracing the actual code, contrary to
the explicit instruction to give a specific verdict. The reasoning shown
never engages with `cue.split("\n")`, the actual mechanism of the bug --
effectively the same blind spot that broke qwen2.5-coder:7b's trial 2.

**Trial 3: WRONG, and self-contradicting.** Opens with "ruff is correct
... safe to delete" -- the wrong answer -- then immediately hedges
without ever correcting to the right conclusion, despite being handed
identical evidence to every other model tested (all of which got this
one right). Also confuses `canonicalize` into the discussion, a name
not actually part of the ruff-flagged set in this scenario.

## Running read across all models tested so far (4 total)

DeepSeek-Coder is a generation/completion-specialized model, not
reasoning-tuned. It performing worse than even the smallest
instruct-tuned Qwen model is a real, informative data point: "coder"
specialization appears to help with writing code, not with judging or
reviewing it -- a different skill this whole exercise is actually
testing. Combined with R1-14b's clean sweep, the emerging pattern
across 4 models is fairly clear: reasoning-tuning is the variable that
actually matters here, not parameter count and not coding
specialization on its own.

Next candidate: deepseek-coder-v2:16b (MoE, ~2.4B active params -- a
different architecture, worth one more data point) and/or
alibayram/mimo-7b-rl (also reasoning-tuned via RL, same category as R1,
worth checking if the reasoning-tuning pattern replicates at smaller
scale than R1-14b).
