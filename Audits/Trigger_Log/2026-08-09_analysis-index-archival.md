# Trigger Log — 2026-08-09 — Archive Analysis/ and Index/; Jprogram scope ends at the corpus

**Work done:** completed step 2 of the Jprogram -> Language Coach scope
move (step 1, removing Jprogram's own live calls into `Analysis/`, merged
earlier this session as `01abde5`; the last live dependency, the QC Test
Harness's `stage_check()`, was fixed and merged first as `566cbce` — see
`2026-08-09_qc-harness-analysis-decoupling.md`). This step:

- Moved `Analysis/`, `Index/`, and `ANALYZER_ARCHITECTURE.md` to
  `Archive/` via `git mv` (`c3bb9fd`) — confirmed via repo-wide grep
  beforehand that nothing live referenced either directory (only
  `paths.py`'s own `ANALYSIS`/`ANALYSIS_OUTPUTS` constants did, both
  removed).
- Removed Analysis from `CLAUDE.md`'s Frozen Components list (the
  authoritative copy) and from `AGENTS.md`'s duplicate summary line,
  which now points back at `CLAUDE.md` as authoritative instead of
  carrying its own copy — a direct fix for the exact drift pattern that
  already caused `AGENTS.md` to silently miss the Session 11
  `deterministic_parser.py`/`deterministic_parser_client.py` Frozen
  additions.
- Updated the pipeline diagrams and purpose statements in `README.md`
  and `JPROGRAM_SESSION_BOOTSTRAP.md` to end at the canonical JSONL
  corpus, and fixed two stale `ANALYZER_ARCHITECTURE.md`/Analysis-layer
  references in `QC Test Harness/README.md` (`21b5714`).

All of this was direct Advisor file management / doc / path-constant
editing, no Coder dispatch — within the Advisor/OC boundary's explicit
carve-out for "moves, renames, archiving" and doc/config/path edits
(`CLAUDE.md`'s Advisor section).

**Audit trigger: No — confidence: Moderate, reason:** no Frozen Component
was touched *while* frozen — Analysis is being removed *from* the Frozen
list as part of this change, and the moved files become inert reference
copies under `Archive/`, not live code. The actual functional risk
surface was narrow: `paths.py`'s constant removal and one path-count
check in `verify_paths()`/`WORKSPACE_FOLDERS`. Confidence is Moderate
rather than High specifically because that narrow surface *did* produce
a real, caught defect (see below) — the process worked, but it's a
reminder this wasn't purely mechanical.

**Verification summary (Advisor's own):**
- Repo-wide grep for `Analysis`/`index_builder`/`ANALYZER_ARCHITECTURE`
  before moving anything, to confirm no live dependency existed beyond
  what step 1 and the QC harness fix had already removed.
- **Real bug caught before it shipped:** removing `paths.ANALYSIS` /
  `paths.ANALYSIS_OUTPUTS` broke `paths.py` itself — both constants were
  still referenced inside its own `WORKSPACE_FOLDERS` tuple and
  `verify_paths()`'s `required` list, which an initial grep for
  cross-file `paths.ANALYSIS` usage did not catch (it only checked other
  modules calling in, not internal self-reference). A full run of every
  `test_*.py` in the repo (59 files, via `.venv/Scripts/python.exe`)
  caught it immediately: 43/59 files failed with
  `AttributeError: module 'paths' has no attribute 'ANALYSIS_OUTPUTS'`.
  Fixed both internal list references, plus one legitimate test
  assertion in `Source Intake/tests/test_paths.py` that explicitly
  checked `ANALYSIS` was a valid product-folder constant (removed that
  name from the check, not the test). Re-ran the full sweep clean:
  **59/59 test files pass.**
- `import app` (module-level import, not full GUI launch) confirmed no
  startup failure from the `paths.py` changes.
- Re-ran the QC Test Harness `check` stage one more time after all
  `paths.py` edits landed: still `OVERALL: PASS`, unchanged from the
  baseline captured for the prior task.
- **Process slip, self-caught:** the first `git add` for the `paths.py`
  fix used two stale pathspecs (`"Analysis"`, `"Index"` — already moved
  by that point) which errored and silently left `paths.py` and
  `Source Intake/tests/test_paths.py` out of commit `c3bb9fd`. Caught by
  checking `git status` immediately after committing, fixed with a
  small dedicated follow-up commit (`6b474b3`) rather than amending.

**Verdict: CLEAN**, after one real defect found and fixed by this
session's own verification discipline (not by a later audit). Three
commits on `master`: `c3bb9fd`, `6b474b3`, `21b5714`.
