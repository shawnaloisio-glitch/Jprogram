# Local-model compression trial — qwen2.5-coder:14b, full test-suite output

Not an audit-trigger decision — a trial of a different proposed use for
the local models already calibrated tonight (see the three
`2026-08-08/09_qwen-calibration_*.md` entries): since none proved
reliable enough for verdict-level audit work, tried them instead as a
cheap first-pass compression/extraction layer over large noisy output,
with Advisor still checking the underlying evidence directly — same
"verify over trust" discipline, applied to a lower-stakes task shape.

**Setup:** ran all 67 standalone `test_*.py` files in the repo directly
(`.venv/Scripts/python.exe <file>`), captured the full raw combined
output (1,771 lines, ~80KB). Ground truth pulled directly via grep/sum
before asking any model to summarize, specifically so the model's
summary could be checked rather than trusted: **67 files, 953 tests,
953 passed, 0 failed, no crashes/tracebacks anywhere in the raw
output.**

Fed the full raw output to `qwen2.5-coder:14b` (chosen for speed and
because it was the model whose trial-1 extraction-shaped result came
back clean in tonight's earlier calibration) with a prompt asking for:
total files/tests/passed/failed, any failing test names, and anything
unusual in the raw output.

## Result: qualitatively right, quantitatively wrong, and too slow to
be worth it as tested

- **Files run: 67 — correct.**
- **Zero failures, no crashes — correct.**
- **Total test count: reported 1981. Actual: 953.** A real
  hallucination on the one precise number the task asked for, not a
  rounding error — roughly double the true figure, with no visible
  reasoning for where it came from.
- **Timing: 404s (6.7 minutes) total. 340s of that was prompt
  processing alone** (20,440 input tokens) **vs. 62s actually
  generating** the 110-token summary. The bottleneck is ingesting a
  large input on this GPU (Vulkan backend, not CUDA), not answering the
  question.

## Read

The qualitative signal (pass/fail/crash-or-not) was usable, which means
this task shape isn't dead on arrival — but two real problems surfaced:
1. **Can't trust it for precise counts even when the qualitative
   verdict is right.** A wrong "1981" sitting next to a correct "all
   passed" is a worse failure mode than an obviously wrong answer,
   because the correct parts build false confidence in the wrong part.
2. **At ~80KB / ~20k tokens of input, prefill time alone (340s) likely
   exceeds how long a direct read of the same raw output would take.**
   This specific use — "dump something large at a local model to save
   reading time" — does not hold up as tested on this hardware. It may
   still work for genuinely small inputs (a few hundred lines), where
   prefill cost is negligible, but that's a narrower and less useful
   claim than "compress anything big," which was the original idea.

**Not pursued further tonight.** If this angle is revisited, the next
test should be on a much smaller input to isolate whether the failure
is input-size-specific (prefill cost) or a more general unreliability
at precise counting, independent of size.
