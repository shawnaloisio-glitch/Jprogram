# Trigger Log — 2026-08-09 — Expressions-rebuild prework: JMdict data staging

**Work done:** blast-radius and planning prework for the "Rebuild
grammar-pattern (`expressions`) detection" item (`WORKING_LIST.md`), done
entirely by Advisor as investigation — no Coder task, no pipeline code
touched. Full findings logged in `WORKING_LIST.md`'s own entry rather than
duplicated here; summary: the downstream Frozen validation/corpus-builder
logic for `expressions` is already complete and dormant, narrowing the
real scope to `deterministic_parser.py` alone; the pattern-source question
was settled by pointing at JMdict's `exp`-tagged entries (already
extracted once in the Reasonix/MiniLingQ project); a filtered copy
(35,547 entries) was staged into this repo at
`Data Processor/Expression Dictionary/jmdict_expressions.jsonl` with a
CC BY-SA 3.0 attribution README, as reference data only.

**Audit trigger: No — confidence: High, reason:** no code changed, no
Frozen Component touched (`deterministic_parser.py` itself is untouched —
this only stages a reference data file alongside it). The commit is data
+ documentation only, directly comparable to prior direct-Advisor data/
config actions this session (Style/Topic vocab creation, the `lingq`
creator entry) — file management and reference-data staging, not program
logic.

**Verification summary:** confirmed the extraction is real and correctly
filtered (35,547 of 35,765 total JMdict `exp` entries survive the >2-char
filter, independently recounted after writing the file, not just trusted
from the extraction script's own printed count); confirmed the file
isn't gitignored before committing; confirmed `git status` shows only the
intended 3 files (the new folder, `WORKING_LIST.md`).

**Verdict: CLEAN.** Committed to `master` (`52ef673`). No worktree/branch
was used — pure Advisor-direct data staging, not a Coder task.
