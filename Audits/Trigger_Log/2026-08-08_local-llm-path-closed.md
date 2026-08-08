# Local-LLM audit/efficiency path — closed (Owner decision, 2026-08-08)

Closing note across the full local-model calibration effort run this
session and last (`2026-08-09_qwen-calibration_*.md`,
`2026-08-08_qwen-calibration_deepseek-coder-v2-16b.md`,
`2026-08-08_qwen-calibration_mimo-7b-rl_and_r1-rerun.md`,
`2026-08-08_local-model-compression-trial.md`). Six local models tested
across two use cases; Owner has closed this path as of this session.

**Verdict-level audit use (the original goal — offloading the
judgment-call-No audit tier): dead.** No model tested was reliable
enough. The two apparent "clean sweeps" (`deepseek-r1:14b`,
`alibayram/mimo-7b-rl`, both 3/3) did not replicate cleanly under a
reworded re-test of the same tasks — `deepseek-r1:14b` dropped to 2/3
on a differently-phrased trial 1, fabricating "safety concerns" on a
commit independently confirmed clean. No score in this series should
be read as a certification.

**Compression/first-pass-triage use (the fallback idea — local model
summarizes noisy raw output for Advisor to then verify): also not
viable as tested.** `qwen2.5-coder:14b` against a real 953-test,
80KB raw suite run got the qualitative signal right (all passed, no
crashes) but hallucinated the actual test count (1981 vs. real 953),
and took 6.7 minutes dominated by prompt-processing time on this
hardware — slower than reading the raw output directly would be.

**Net conclusion:** local models (Ollama, this hardware) are not
currently a usable lever for either reducing Claude token spend on
audit work or compressing large tool output before Advisor reviews it.
Revisit only if hardware changes (a GPU with faster prefill), a
materially different model becomes available locally, or a narrower
task shape is proposed that avoids both failure modes found here
(imprecise counting, slow large-context ingestion).

Cloud options (DeepSeek's existing API key via its documented
Anthropic-compatible endpoint, and/or a MiMo subscription pending
Owner's own trial-month evaluation) remain open and untested as of this
entry — a materially different quality tier (real flagship cloud
models, not local quantized distillations), not covered by this
closing verdict.
