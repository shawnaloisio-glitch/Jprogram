# Trigger Log — 2026-08-08 — Nihongo Jikan HTML transcript importer + Material Level folder suggestion

**Work done:** first real product task run through the new headless
DeepSeek-Coder mechanism under the new confirmation-gate workflow, in an
isolated git worktree/branch (`add-nihongo-jikan-importer`, merged to
`master` as `af92527`). Two parts: (1) a new importer
(`Nihongo Jikan Importer/html_transcript_cleaner.py`) that parses
`D:\Nihongo Jikan media\Transcripts\`'s HTML/ruby-furigana format —
bare `<p>` tags are real sentences, `<ruby>BASE<rt>READING</rt></ruby>`
keeps only BASE (furigana discarded, Owner decision), attributed
`<p class="...">` and the scraped-page "Copyright Info" widget are
discarded entirely; (2) a small direct folder-name → Material Level
suggestion (`import_material.suggested_material_level`), wired into the
import flow for both the new importer and the existing Subtitle Importer
path, suggestion-only (dropdown stays editable).

**Audit trigger: No — confidence: Moderate, reason:** no Frozen Component
touched — confirmed via `git diff --stat` (only `Nihongo Jikan Importer/`
[new], `Source Builder/import_material.py`, `Source Builder/gui.py`, and
their existing test files). This is net-new code behind an explicit new
format choice, not a modification to shared/frozen parsing logic (unlike
the 2026-08-08 Cleaner sentence-split fix, which touched
`deterministic_parser.py`'s own private function and needed a 20,010-case
fuzz proof of behavior preservation — this task only *reuses*
`Common/sentence_split.py` unchanged). The extraction rule was verified
exhaustively against the real raw corpus *before* implementation (114,940
of 114,940 bare `<p>` tags contain only plain text + ruby/rt; every
attributed `<p class="...">` occurrence in the whole corpus is widget
noise, never real transcript text) rather than assumed. Any future
join/split defect would still be caught by the unmodified Frozen
reconstruction gate (`parser_normalizer.py`) at processing time, not
silently corrupt the corpus.

**Verification summary (Advisor's own, not accepted on Coder's
self-report):**
- `git diff --stat` scope matches Coder's claimed file list exactly, both
  in the worktree and after merge to `master`.
- Full suite independently re-run twice (once in the worktree, once again
  in the real repo after merge): **67/67 non-`ginza`-dependent test files
  pass, 0 failures**, both times. `ginza` is genuinely absent from this
  environment too (confirmed via a direct `import ginza` against
  `master`, not just Coder's claim) — the 2 excluded
  `deterministic_parser`/`deterministic_parser_client` test files are a
  real, pre-existing environment gap, not caused by this task.
- **Minor self-report inaccuracy, not a defect:** Coder's own report
  claimed "69 files, 942 tests" while also noting 2 files couldn't run in
  its environment — the real count of files it could run is 67. Recorded
  for the record; does not change the verdict.
- **Beyond unit tests:** ran the new importer directly against 3 real
  files from `D:\Nihongo Jikan media\Transcripts\` (read-only, nothing
  copied into the repo), including one confirmed to carry a real trailing
  Copyright/Steam-link widget. Result: 607 sentences extracted cleanly,
  zero leftover HTML tags, zero copyright/attribution text leakage, zero
  furigana readings in the output.

**Verdict: CLEAN.** Merged to `master`, worktree and branch removed per
standing procedure.
