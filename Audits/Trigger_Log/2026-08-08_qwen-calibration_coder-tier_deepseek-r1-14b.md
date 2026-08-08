# Qwen Calibration — Coder-tier trial 2, deepseek-r1:14b

Same task, same methodology, same ground truth as
`2026-08-08_qwen-calibration_coder-tier_qwen2.5-coder-14b.md` (read that
entry first) — a direct side-by-side on `extract_sentences(html_text)`.
`deepseek-r1:14b` was picked for this second trial specifically because
it was the only model to score 3/3 in the earlier judgment-tier
calibration series; the question here is whether that judgment-tier
result predicts anything about code-generation ability. Short answer:
not simply.

**Mechanism:** same direct Ollama `/api/chat` call, `num_ctx` 8192,
GPU/Vulkan. Needed a much longer timeout than the qwen trial — the first
attempt (300s) hit a raw socket timeout mid-generation and had to be
rerun at 900s. **296.3s wall time, 7,883 output tokens** (vs. qwen's
75.9s / 277 tokens) — consistent with `deepseek-r1:14b` spending most of
its budget on visible chain-of-thought before emitting code, as seen
throughout the judgment-tier trials.

## Result: fatal crash as-shipped; underlying logic sound once patched

**As-given, the function does not run at all**, on any input:

```python
def extract_sentences(html_text: str) -> list[str]:
    unesc = unescape()          # <- html.unescape() called with NO args
    ...
    sentence = unesc(stripped_content.strip())   # <- then "called" as if
                                                  #    it were a reusable
                                                  #    partial function
```

`html.unescape` takes a string directly (`unescape(s)`); it is not a
factory that returns a callable. Confirmed by direct execution on the
simplest possible test case (`<p>こんにちは。</p>`):
`TypeError: unescape() missing 1 required positional argument: 's'`.
This is a basic stdlib API-usage error, not a subtle logic bug — it
fails before processing a single character of real input.

**In fairness — same standard applied to any real Coder output — the one
broken line was patched (`unesc = unescape` instead of `unescape()`) and
the rest of the logic re-verified against the same 5 checks used for the
qwen trial:**

1. Basic bare `<p>` + ruby: correct.
2. Attributed `<p class="...">` exclusion: correct, no leak.
3. **General entity case (`&lt;`, `&gt;`, `&nbsp;`) — correct**, unlike
   `qwen2.5-coder:14b`'s hardcoded-3-literals gap. `deepseek-r1:14b`
   actually used `html.unescape` as intended, once its own broken call
   convention is fixed — the *design* was right, only the invocation was
   wrong.
4. Real file `865` (no widget): 59/59, exact match.
5. Real file `862` (has the real widget): 580 entries, zero leaked
   widget text, matching the exact raw bare-`<p>` count (same
   task-scope note as the qwen trial: no further punctuation-boundary
   split was requested).

**Structural note, favoring this model's approach over qwen's:** its
tag-matching regex (`r'(<p\b[^>]*?>)(.*?)</p>'`) captures every `<p...>`
opening tag — bare or attributed — then explicitly filters to
`opening_tag == '<p>'`. This never mismatches an attributed tag's content
into a real span in the first place, unlike `qwen2.5-coder:14b`'s
delete-the-opening-tag-and-hope approach (previous entry, "architectural
fragility" note). More robust by construction, not just by luck on this
dataset.

## Read

A genuinely interesting split result, not a simple "which model wins":
`deepseek-r1:14b`'s *design* was more correct than `qwen2.5-coder:14b`'s
on both axes where the two differed (entity generalization, tag-exclusion
robustness) — consistent with r1 being the standout performer across the
whole calibration series. But it shipped code that doesn't run at all,
a failure mode `qwen2.5-coder:14b` didn't have. Best judgment-tier score
did not predict best out-of-the-box code-generation reliability. At
~4x the latency and ~28x the token cost of the qwen trial for this one
task, the reasoning overhead did not buy correctness on the dimension
that would have actually mattered first (does it run).

Not merged, not part of the product — throwaway calibration only, per
Owner's framing.
