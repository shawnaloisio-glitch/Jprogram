# Qwen Calibration — Coder-tier trial 1, qwen2.5-coder:14b

Extension of the existing local-model calibration series
(`2026-08-09_qwen-calibration_summary.md` and related entries) into a new
dimension: every prior trial in this series tested *judgment* (does this
diff/execution/import-usage claim hold up) — this is the first trial
testing actual *code generation*. Owner's framing: low-stakes curiosity
("not expecting much, but interesting"), not a candidate to replace the
DeepSeek-headless Coder mechanism.

**Task:** write a single self-contained Python function,
`extract_sentences(html_text) -> list[str]`, implementing the real
Nihongo Jikan HTML extraction rule this session already built and
verified (bare `<p>` = sentence, attributed `<p class="...">` = excluded
widget noise, `<ruby>BASE<rt>READING</rt></ruby>` -> BASE, general HTML
entity unescaping, stdlib only). Real ground truth already existed: the
actual merged `Nihongo Jikan Importer/html_transcript_cleaner.py` and two
real files already verified earlier this session (`865` - no widget,
`862` - has a real Copyright/Steam-link widget block).

**Mechanism:** direct call to Ollama's `/api/chat` (model
`qwen2.5-coder:14b`, `num_ctx` 8192, GPU/Vulkan) — not the `claude -p`
Coder harness, since Ollama has no Anthropic-compatible endpoint the way
DeepSeek does; wiring that up would need real proxy work not attempted
here. 75.9s wall time, 277 output tokens, no API cost.

## Result: correct on the hard part, one real spec-compliance bug

Verified with a standalone test script (`test_local_coder_output.py`,
scratch-only, not part of the repo) — 5 checks, run independently, not
accepted on the model's own claims:

1. Basic bare `<p>` + ruby: correct.
2. Attributed `<p class="...">` exclusion: correct, no leak, in this test.
3. **Named-entity unescaping (`&lt;`, `&gt;`, `&nbsp;`): FAILED.** The
   task explicitly asked for "the general case, not just these three
   examples" (referring to `&amp;`/`&quot;`/`&#x27;` given as illustrative
   examples in the spec) — the model hardcoded exactly those three named
   entities plus a numeric-entity regex, and ignored the instruction to
   generalize. It had `html.unescape()` available (the prompt explicitly
   said the `html` module was fine to use) and chose a partial hand-rolled
   substitute instead. `&lt;`/`&gt;`/`&nbsp;` passed through unescaped,
   literally, in real output.
4. Real file `865` (no widget): 59/59 sentences, exact match to the
   verified reference implementation's output.
5. Real file `862` (has a real Copyright/Steam-link widget block): 580
   entries, zero leaked widget text. 580 independently confirmed to be
   the exact raw bare-`<p>`-tag count in that file — correct for the task
   as scoped (this test deliberately asked for one entry per `<p>`, not
   the further per-sentence punctuation split the real pipeline applies
   as a separate step; the earlier "607" figure from this session's real
   pipeline run is not directly comparable, different task scope, not a
   discrepancy).

**Architectural fragility noted, not a confirmed failure:** the model's
approach to excluding attributed `<p>` tags deletes only the opening tag
via regex (`<p [^>]+>` -> `''`), leaving the inner text and closing `</p>`
loose in the token stream, rather than never matching them in the first
place (the reference implementation's approach, via `<p\s*>` requiring
zero extra characters). It did not leak on either real file tested, but
that depends on every real bare `<p>` closing properly before the widget
starts — true in this dataset, not something the code enforces by
construction. Different file structure could break it.

## Read

Consistent with the pattern from all 5 prior judgment-tier trials
(`qwen2.5-coder:7b/14b`, `deepseek-r1:14b`, `deepseek-coder:6.7b`,
`deepseek-coder-v2:16b`): the mechanical/structural part of the task
(correctly distinguishing bare vs. attributed tags, correctly extracting
and cleaning real Japanese text with embedded furigana markup) was
handled well. The failure is again at spec-adherence, not raw capability
— here, quietly narrowing "the general case" down to three hardcoded
literals instead of reaching for the stdlib tool the prompt pointed at.
For a 14B model running locally at zero API cost in under 80 seconds,
this is a genuinely useful data point, not a dismissal.

Not merged, not part of the product — throwaway calibration only, per
Owner's framing.
