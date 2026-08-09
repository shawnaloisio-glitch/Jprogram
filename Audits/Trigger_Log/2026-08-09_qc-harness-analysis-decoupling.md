# Trigger Log — 2026-08-09 — QC Test Harness: drop Analysis/ dependency in stage_check()

**Work done:** rewrote `stage_check()` in `QC Test Harness/run_qc_pipeline.py`
so it no longer imports `corpus_loader` / `frequency_analyzer` /
`distribution_analyzer` / `chunk_analyzer` from `Analysis/`. It now scans
the canonical JSONL records' own `words` (`[index, surface, lexical,
char_start, char_end]`) and `chunks` (`[index, text, start_word,
end_word]`) arrays directly, computing exactly what the existing
comparison logic reads (occurrences, per-surface counts, sentence-distance
min/max, chunk occurrence counts) — same PASS/FAIL semantics, same
ground-truth comparison against `qc_test_001_expected.json`, same return
codes. Deliberate simplification made when scoping the task (not a Coder
deviation): sentence-distance mean/median/stddev are not computed, since
the existing comparison code only ever reads `min`/`max` — computing the
unused stats would have been dead work. This was the last live dependency
on `Analysis/` blocking its archival (step 2 of the Jprogram -> Language
Coach scope move, step 1 already merged as `01abde5`).

Built in an isolated git worktree/branch (`fix-qc-stage-check`), via the
headless DeepSeek-Coder mechanism, `--allowedTools Read,Edit` only (no
Bash needed — this is a pure code edit, Advisor ran all verification
separately). Merged to `master` as `566cbce`; worktree and branch removed
per standing procedure.

**Audit trigger: No — confidence: Moderate, reason:** `QC Test Harness/`
is not on the Frozen Components list (Parser/Validator/Builder/Analysis/
Transport) — confirmed by checking `CLAUDE.md`'s list directly, not from
memory. This is Jprogram's own internal self-check tooling, not part of
the live production pipeline or its GUI/downstream consumers: a bug here
would produce a wrong PASS/FAIL verdict on a hand-authored fixture, never
corrupt real corpus data (the actual Frozen `parser_normalizer.py`
reconstruction gate is what protects the real corpus, and it's untouched
by this change). Confidence is Moderate rather than High only because this
is real comparison logic being rewritten, not a pure deletion — but the
verification method below (behavioral match against a captured baseline,
not just diff review) is the strongest evidence this project's process
produces short of a full Auditor pass, and it came back exact.

**Verification summary (Advisor's own, not accepted on Coder's
self-report):**
- Corrected a stale bootstrap assumption first: the `qc_test_001` corpus
  was *not* already sitting in the Workspace as the prior session's notes
  claimed (only the Source Package and Registry entry survived the
  interim production run's data). Regenerated it fresh —
  `setup`/`clean`/`jobs`/`requests`/`parse`/`corpus` — before touching any
  code.
- Captured a baseline `check` run against the *original* (pre-change)
  `stage_check()`: `OVERALL: PASS`, exact occurrence/surface/
  sentence-distance values for 犬/猫/食べる, chunk count 52, one candidate
  chunk match (`勉強することにしました`).
- `git diff --stat`: exactly one file changed (`QC Test Harness/
  run_qc_pipeline.py`), 83 insertions / 12 deletions, confined to the
  module docstring's step-8 line, the `Analysis` `sys.path` insert, and
  inside `stage_check()` itself. The comparison/print logic below the
  rewritten data-gathering block — the part Coder was told not to touch —
  is byte-identical in the diff (no hunk touches it).
- Re-ran `check` against the *rewritten* code, first in the worktree, then
  again in the real repo after merge: both runs reproduced `OVERALL: PASS`
  and every compared value exactly matching the baseline. The only visible
  output difference is the diagnostic `sentence_distance: actual={...}`
  line now shows only `min`/`max` instead of also `mean`/`median`/
  `stddev` — expected, per the scoping decision above, and does not affect
  any PASS/FAIL check.

**Verdict: CLEAN.** Merged to `master`, worktree and branch removed.
