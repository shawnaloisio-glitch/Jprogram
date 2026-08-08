# Qwen Calibration — 2026-08-09 — deepseek-r1:14b, same 3 trials

Same trials, same harness, run against `deepseek-r1:14b` (reasoning-tuned,
distilled onto a Qwen2.5-14B base) via local Ollama.

## Result: 3/3 CORRECT — first clean sweep across all trials tested so far
(qwen2.5-coder:7b: 1/3, qwen2.5-coder:14b: 2/3, deepseek-r1:14b: 3/3)

**Trial 1 (diff-parsing): CORRECT.** Same result as Qwen 14b -- correctly
tracked every removal against the diff.

**Trial 2 (execution-tracing): CORRECT -- the trial that broke both
Qwen sizes.** R1's trace correctly derives the same mechanics Qwen 14b
also correctly derived (two lines processed separately, joined with
`\n\n`), but unlike Qwen 14b, R1 correctly concludes this is a bug --
it does not make the "mechanics right, final judgment wrong" mistake
that made Qwen 14b's failure the more concerning of the two Qwen
results. This is exactly the failure mode a reasoning-tuned model
would be expected to help with: verifying whether a derived result
actually satisfies the stated goal, not just deriving it.

**Trial 3 (cross-file reasoning): CORRECT.** Consistent with both Qwen
sizes -- this task appears to be reliably solvable regardless of
reasoning-tuning, when evidence is handed directly.

## Cost tradeoff
Meaningfully slower than Qwen 14b at the same parameter count: 93.7s vs.
60.4s on trial 1, 61.7s vs. 43.0s on trial 2, 43.4s vs. 25.5s on trial 3
-- consistently ~50-70% slower across all three, consistent with
spending tokens on visible chain-of-thought before the final answer.
Still fast enough in absolute terms (under 2 minutes per trial) to be
practical for the kind of low-risk verification tier this whole
exercise is scoping.

## Running read across all models tested so far
Reasoning-tuning, not raw parameter count, appears to be what actually
fixes the failure mode that mattered most (correctly judging a
correctly-derived result against a stated goal). This is the first
result in this whole calibration exercise that would not have needed a
"do you trust this" caveat if it had come from a real audit task,
though 3 trials is still a small sample -- worth testing DeepSeek-Coder
next (a coder-specialized, non-reasoning-tuned model) as a fourth data
point before drawing a firm conclusion.
