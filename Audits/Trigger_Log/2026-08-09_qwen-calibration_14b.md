# Qwen Calibration — 2026-08-09 — qwen2.5-coder:14b, same 3 trials

Same trials as the 7b calibration (`2026-08-09_qwen-calibration_summary.md`),
same reusable harness, run against `qwen2.5-coder:14b` (Ollama, GPU/Vulkan,
now relocated to `D:\Ollama\Models` -- see disk-space note at bottom).

## Trial 1 (diff-parsing) — CORRECT (improvement over 7b)
Correctly tracked every removed name against the actual diff, correctly
confirmed the three protected re-exports were left untouched. 7b failed
this same trial by claiming a kept name (`restore_sentence_text`) had
been removed.

## Trial 2 (execution-tracing) — STILL WRONG, different and more
concerning failure shape than 7b's
14b's mechanical trace was actually correct this time: it correctly
simulated `cue.split("\n")` producing two lines, correctly ran
`split_line()` on each independently, and correctly stated the two
resulting pieces get joined with `"\n\n"`. Its own shown "Final Output"
is genuinely the buggy, fragmented result (the two pieces separated by a
blank line). But its verdict text then asserts this output is "correctly
identified and handled as a single grammatically complete sentence,
preserving the intended meaning" -- which is false; the shown output is
exactly the real regression, not a preserved single sentence.

**This is a different failure mode than 7b's** (which botched the
mechanical simulation itself and got a coincidentally-clean-looking wrong
answer). 14b got the mechanics right and then misjudged whether its own
correctly-derived output actually satisfies the stated correctness
criterion. Arguably worse for trust calibration: the visible reasoning
chain looks sound throughout, which would make a human reviewer more
likely to accept the wrong final verdict on the strength of the shown
work, right up until the last interpretive step.

## Trial 3 (cross-file reasoning) — CORRECT
Same result as 7b: correctly concluded NOT SAFE TO DELETE with sound
reasoning about the module-alias usage.

## Read after 2 models (7b, 14b)
Scale measurably helped diff-parsing (trial 1) and made no difference on
the already-solid cross-file-reasoning task (trial 3), but did not fix
the core problem: neither size can be trusted to reach a correct final
verdict on a task requiring execution-tracing PLUS judging whether the
traced result satisfies a stated goal. 14b's failure is arguably a worse
trust signal than 7b's, precisely because the visible reasoning no longer
contains an obvious tell.

## Infrastructure note (unrelated to model quality)
Mid-session, `.ollama\models` was relocated from `C:\Users\Shawn\.ollama\`
to `D:\Ollama\Models` (C: was tight on space; D: has room). Found and
corrected two real issues in the process, both logged here for anyone
revisiting this setup:
- `OLLAMA_MODELS` set via the persistent User-scope environment variable
  does not propagate to a process already running in the same shell
  session that set it -- the session's own `$env:` copy must also be set
  explicitly before spawning a child process expected to see the new
  value.
- The newer bundled "Ollama app.exe" (with its own web UI -- chats,
  cloud, etc.) appears to manage its model path through a separate
  mechanism from `OLLAMA_MODELS` and kept reading the old C: path even
  after the variable was correctly set. Running the plain `ollama.exe
  serve` process directly (not the GUI app wrapper) picked up the new
  path correctly on the first try. If the GUI app's own chat/cloud
  features are ever used directly, its model path should be verified
  separately -- it may still default to C:.
