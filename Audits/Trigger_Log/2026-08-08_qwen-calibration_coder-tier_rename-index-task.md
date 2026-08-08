# Qwen Calibration — Coder-tier trial 3, rename+log+index task (qwen2.5-coder:14b vs deepseek-r1:14b vs Claude baseline)

Third Coder-tier trial, following the two single-function trials
(`2026-08-08_qwen-calibration_coder-tier_qwen2.5-coder-14b.md`,
`...deepseek-r1-14b.md`). Different shape of task this time: not code
generation, but a real, low-stakes operational task Owner floated —
"could a local model help with clear move/rename with minimal logic."
Advisor's standing recommendation was to never let a model execute file
operations directly, only propose a mapping that gets verified before
anything real happens. This trial is that verification in practice.

**Task:** given the real 71-file `D:\Nihongo Jikan media\Transcripts\
Advanced\` folder (filename, size, date for each), apply one explicit
rule — strip the leading numeric ID and everything from the first
Japanese-script character onward, keeping only the English title — and
produce three outputs: a MAPPING (old -> new), a LOG of the round, and
an INDEX (final filenames with real size/date, sorted alphabetically).
Real data throughout, matching this project's real, already-established
media-organize naming convention (`project_media_organize_workflow`
memory: "strip the Japanese portion, keep English title only").

**Baseline:** Advisor (Claude) did the same task by hand first, as the
comparison reference — not treated as infallible ground truth (5 of the
71 files have a genuinely ambiguous "duplicate title" pattern where the
English title repeats a word right before the Japanese title begins),
but independently defensible line by line.

## Result: qwen — solid mapping, broken/incomplete index; r1 — best mapping content, but fabricated index entries

### qwen2.5-coder:14b (412.5s, 3,978 tokens)
- MAPPING: 71/71 complete, zero collisions, zero leftover Japanese.
  6/71 differ from the Claude baseline — all 6 in the ambiguous
  duplicate-title cases, and in 5 of 6 qwen's version reads better
  (dropped the awkward trailing duplicate). In the 6th (file 321,
  "...Nihongo-Learning..."), qwen over-trimmed and lost real content
  ("from Nihongo-Learning" dropped entirely).
- **Its own LOG claimed "No uncertainty in filename parsing" — false.**
  It silently made a real editorial judgment call in exactly those 6
  cases without disclosing it.
- INDEX: **broken.** Only 67/71 entries — the first four files (274,
  321, 364, 377) are missing outright, with no acknowledgment. Also
  ignored the explicit "sorted alphabetically" instruction, using
  original-ID order instead.

### deepseek-r1:14b (579.3s, 5,939 tokens)
- MAPPING: 71/71 complete, zero collisions, zero leftover Japanese.
  8/71 differ from the Claude baseline — the same 6 duplicate-title
  cases (matching qwen's cleaner versions in 5/6), **plus two
  genuinely superior answers neither Claude nor qwen produced**:
  - File 321: **"Interview with Yuta from Nihongo-Learning.html"** —
    correctly kept "from Nihongo-Learning" exactly once. The only one
    of the three that didn't either lose it (qwen) or duplicate it
    awkwardly (Claude baseline).
  - File 843: correctly recognized `_u002620`/`_u00262` as a mangled
    HTML numeric-entity encoding of `&` (`u0026` = the Unicode
    codepoint) and reconstructed "EP18 & 20 ... Part1 & 2" — real,
    correct decoding neither Claude nor qwen attempted.
  - Its own LOG explicitly flagged file 843 as uncertain — accurate,
    and better self-disclosure than qwen's false "no uncertainty"
    claim. (It did not disclose the other 5 duplicate-trimming
    judgment calls, or a 9th undisclosed inference on file 800 —
    restoring a sanitized `_` back to `?`, plausible but not literally
    supported by the input.)
  - Minor, separate observation: several OLD filenames were echoed
    back in its MAPPING output with individual kanji silently swapped
    for visually-similar Simplified Chinese variants (e.g. Japanese
    "況" -> Chinese "况" in one entry). Does not affect the actual new
    filenames (the Japanese portion is discarded either way), but is
    silent corruption of data it was only supposed to be reading, not
    editing.
- INDEX: **broken worse than qwen's, and differently.** Verified
  against r1's *own* MAPPING output as ground truth (not the Claude
  baseline, to avoid counting r1's legitimately-different-but-real
  renames as false positives): 57/71 real entries present, 14 real
  entries silently missing, and **5 entries are outright fabricated**
  — filenames matching nothing in the real 71-file list:
  - `Hito wo Miru Meiji no Koi ni Tsugu: The Meiji Era's Legacy of
    Staring at People.html`
  - `Meiji no Koi ni Tsugu: The Meiji Era's Legacy of Staring at
    People.html` (a near-duplicate of the above)
  - `Noriko's Chat with Kei on Language Learning.html` (a fictional
    mashup of two real, unrelated files — "Chat with Kei" and
    "Language Learning" are both real, separate entries)
  - `Umeko Tsuda: Pioneering Women's Education in Japan.html` (an
    invented duplicate of a real entry already correctly present
    elsewhere in the same INDEX under its real title)
  Each fabricated entry carries the note "This file was not included
  as it doesn't follow the pattern" — nonsensical, since they are
  listed, two with fabricated-looking real size/date values attached.
  Also renamed "The Tale of the Bamboo Cutter.html" inconsistently
  between its own MAPPING and INDEX sections ("Chronicling the Tale of
  the Bamboo Cutter.html" in the INDEX) — a third distinct failure
  mode (self-inconsistency), separate from omission and fabrication.

## Read

The clearest, most concrete result of the whole calibration series.
`deepseek-r1:14b` produced the single best individual pieces of content
across all three participants (the two mapping decisions above are
genuinely correct, not just stylistically preferred) — and, in the same
response, fabricated fictional file records with no hedging, formatted
identically to the real entries around them. This is exactly the risk
Advisor flagged before this trial ran: never let a local model execute
file operations directly, only propose a mapping that gets verified
first. Verification is what caught this. Without independently checking
every INDEX line against the model's own MAPPING output, the fabricated
entries would have looked exactly as trustworthy as the real ones.

`qwen2.5-coder:14b`'s index failure (silently incomplete) and
`deepseek-r1:14b`'s index failure (silently incomplete AND fabricated)
are not the same severity. Incompleteness is a checklist failure.
Fabrication is a trust failure — and it came from the model that
otherwise did the best reasoning in the same response.

Not merged, not part of the product — throwaway calibration only, per
Owner's framing.
