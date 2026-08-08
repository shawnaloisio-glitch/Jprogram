# Qwen Calibration — deepseek-coder-v2:16b, same 3 trials

Continuation of the local-model calibration exercise (see
`2026-08-09_qwen-calibration_summary.md` for the original methodology
and `2026-08-09_qwen-calibration_r1-14b.md` /
`2026-08-09_qwen-calibration_deepseek-coder-6.7b.md` for the two most
recent prior results). Same three trials, reconstructed from the prior
logs' descriptions rather than replayed from a saved script (none was
found on disk — the original trials were run ad hoc within a prior
session, not saved as a reusable harness). Run against
`deepseek-coder-v2:16b` (Ollama, local, `num_ctx` 16384, GPU/Vulkan).

## Result: 0/3 — worst result yet, the first model to fail trial 3

| Model | Score |
|---|---|
| qwen2.5-coder:7b | 1/3 |
| qwen2.5-coder:14b | 2/3 |
| deepseek-r1:14b | 3/3 |
| deepseek-coder:6.7b | ~0.5/3 |
| **deepseek-coder-v2:16b** | **0/3** |

## Trial 1 (diff-parsing) — WRONG, self-contradictory
Fed the real `36dc8be` diff (ruff dead-code cleanup) and asked which
names were actually removed (`-` lines only) vs. kept. Ground truth:
`CANONICAL_LINE_SEPARATOR`, `recompute_character_spans`,
`recompute_chunk_text`, `_is_section_marker_line`, `verify_paths`, a
bare `import parser_normalizer`, `import json`/`from pathlib import
Path`, and one dead-assignment line in `test_sentence_metrics.py` — 9
items across 4 files. `restore_sentence_text`, `canonicalize`,
`verify_source_reconstruction`, and `_expected_content` were never
touched.

The model's own Q1 answer list included `restore_sentence_text`,
`verify_source_reconstruction`, and `_expected_content` as "removed" —
all three false. Its Q2 answer then directly contradicts its own Q1
list, stating those same three names were "not present in the diff as
... deliberately kept." Same root failure as `qwen2.5-coder:7b`'s trial
1 (misreading `-`/context lines in a unified diff), but with the added
tell of contradicting itself within one response.

## Trial 2 (execution-tracing) — WRONG, "mechanics right, verdict
wrong"
Same reconstructed Subtitle Importer regression used for every prior
model (a cue pre-split on internal `\n` before checking punctuation,
fragmenting a sentence that legitimately wraps two display lines with
no line-break punctuation). The model's step-by-step trace is fully
correct: it correctly derives `sentences = ['これは とても',
'長い文です。']` and the fragmented `"これは とても\n\n長い文です。"`
joined output. It then concludes "no bug... works as intended,"
directly contradicted by its own traced output being the exact
fragmentation bug. Identical failure shape to `qwen2.5-coder:14b`'s
trial 2 — the more concerning kind, since the visible reasoning chain
looks sound right up to the final judgment.

## Trial 3 (cross-file reasoning) — WRONG, the first model to fail this
trial
Same evidence-handed-directly setup as every prior model (the
`corpus_builder.py` import block plus the exact `cb.X(...)` call sites
in `test_corpus_builder.py`). Every model tested before this one
(`qwen2.5-coder:7b/14b`, `deepseek-r1:14b`) got this one right. This
model's reasoning body correctly explains *why* the three names are
genuinely used externally via the `cb.` module alias and why `ruff`'s
single-file static analysis would miss that — then states the opposite
final verdict: "SAFE TO DELETE ... it is safe to conclude that these
functions are not necessary imports ... and can be deleted." It even
lays out the correct "NOT SAFE TO DELETE" argument itself, in a section
labeled "Hypothetical," and talks itself out of it. Ground truth is NOT
SAFE TO DELETE; the model's own reasoning proves that, and its own
verdict says the opposite.

## Read after 5 models
`deepseek-coder-v2:16b` is not a case of a *different* failure mode from
what's already been seen — trials 1 and 2 repeat exactly the two
failure shapes already catalogued (diff-misread with self-contradiction;
correct-mechanics-wrong-judgment). What's new is trial 3: a task every
other model handled reliably, including the smallest one
(`qwen2.5-coder:7b`), failed here specifically at the *verdict* step
after correctly reasoning through the evidence — the model's own stated
argument and its own stated conclusion point in opposite directions.
This reinforces the emerging read from the `r1-14b` result: the thing
that actually predicts trustworthiness in this exercise is not parameter
count or "coder" specialization, it's whether the model reliably checks
its own derived conclusion against the question actually asked before
answering — `deepseek-r1:14b`'s reasoning-tuning is the only variant
tested so far that did this consistently.

## Cost
Trial 1: 55s (431 tokens). Trial 2: 30s (838 tokens). Trial 3: 19s (559
tokens). Faster than `deepseek-r1:14b` throughout, comparable to
`qwen2.5-coder:14b` — consistent with `deepseek-coder-v2:16b` not
spending tokens on visible chain-of-thought before answering.

## Methodology caveat
Trials 2 and 3 were reconstructed from the prior logs' written
descriptions (the exact original prompt text was not saved to disk by
the prior session), not replayed byte-for-byte. The reconstructions
preserve the same evidence shape and question each prior trial log
describes (same buggy function logic, same example sentence-wrap case
for trial 2; same import block and same external call sites for trial
3), and produced results consistent with — not contradicting — every
prior model's logged behavior on the same tasks, which is some evidence
the reconstruction is faithful. Still worth flagging: this is not a
literally identical harness run, unlike trials 1-4 among each other
which(per the "same reusable harness" language in prior logs) may also
only have been consistent in intent rather than byte-identical.
