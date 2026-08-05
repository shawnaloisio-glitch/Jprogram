# OC Reliability Log

Purpose: a running, evidence-based record of how well OC's self-reported
work matches independently-verified reality — task by task. This is what
"trust" between Advisor and Coder should actually be built on: not a
subjective impression carried in conversation, but a growing count of
specific checks and their outcomes.

**Why this exists:** verifying every OC report against raw evidence (git
diff/status, direct test runs) costs tokens every time. That verification
stays mandatory regardless of how many tasks pass clean — see `CLAUDE.md`'s
evidence-hierarchy rule — but *how much* verification effort a given task
needs can reasonably scale down over time, for well-understood task
*categories*, once this log shows a real track record for that category.
One clean task is not a track record. This file is how we tell the
difference between "OC seems fine" (a feeling) and "OC has been right N
times out of N on this class of task" (evidence Owner can actually decide
from).

**How to use this log:** append one entry per verified Coder task. Never
edit a past entry's verdict after the fact except to correct a factual
error in the log itself (note the correction, don't silently rewrite
history). Do not skip logging a task because it was "too small to matter"
— small clean tasks are exactly what builds the low-stakes track record;
the point is the count, not just the dramatic cases.

---

## Log format

Each entry:

```
### TASK <n> — <short description> — <date>

**Scope given:** <one line — what OC was asked to do, and the boundary>
**OC's self-reported result:** <claimed files changed, claimed test counts, claimed boundary compliance>
**Independent verification method:** <e.g. "raw git status + direct test re-run">
**Verification result:** <MATCH / MISMATCH — with specifics>
**Scope compliance:** <did it stay within the stated boundary — checked via git diff, not self-report>
**Notable behavior:** <anything worth remembering — e.g. correctly escalated an out-of-scope finding instead of guessing>
**Verdict:** <CLEAN / CLEAN WITH NOTES / DISCREPANCY FOUND>
```

---

## Entries

### TASK 1 — Fix Source Builder preset test isolation — 2026-08-05

**Scope given:** Apply the existing `paths.COLLECTIONS_CONFIG` isolation
pattern (already used correctly in 8 sibling test files) to two test files
that were missing it: `test_source_builder_quick_presets.py` and
`test_source_builder_gui_presets.py`. Strict boundary: only those two
files; no production code; no other test files.

**OC's self-reported result:** `quick_presets.py` 21/21 (was 20/21);
`gui_presets.py` 7/8 (was 4/8, one residual failure identified as a
separate, orthogonal bug — see below); only the two authorized files
modified; all 17 other Source Builder test files still passing.

**Independent verification method:** read OC's full raw session transcript
directly from the OpenCode desktop SQLite database (see
`OC_Session_Access_Procedure.md`), then independently re-ran both fixed
test files plus all 18 other files in `Source Builder/tests/` myself, and
checked `git status --short` against the claimed file list.

**Verification result:** MATCH, exactly. `quick_presets.py` 21/21 confirmed
by direct run. `gui_presets.py` 7/8 confirmed by direct run, same single
remaining failure. All 18 other Source Builder test files: 100% pass,
confirmed by direct run.

**Scope compliance:** MATCH. `git status --short` showed exactly the two
authorized files modified — nothing else touched.

**Notable behavior:** OC discovered a 4th, genuinely separate bug mid-task
(a test asserting `source_type == "article"`, which is structurally
impossible to satisfy given `PROCESSING_PROFILES` only defines
`anime_subtitle`/`podcast_transcript`). Rather than silently fixing it,
silently ignoring it, or guessing at intent, OC used its own `question`
tool to stop and hand the decision to Owner directly, with three clearly-
framed options. This is the correct behavior per `AGENTS.md`'s "no silent
scope creep" rule, and is the opposite of the design spec's documented
API-key incident (where OC's self-classification of its own fix glossed
over an open question instead of surfacing it).

**Verdict:** CLEAN. First data point. See `JPROGRAM_SESSION_BOOTSTRAP.md`
§10 step 6 follow-up for the product-level detail (the residual "article"
mismatch is tracked there as a known, non-blocking issue, not as an OC
reliability concern — OC correctly identified and surfaced it rather than
causing it).
