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

### TASK 2 — Read-only audit: source_id/episode and section-field assumptions — 2026-08-05

**Scope given:** Pure investigation, zero implementation. Map every place
in the codebase (a) source_id/episode-sequence structure is
parsed/assumed/predicted, and (b) the canonical corpus `section` field is
read, written, or asserted. Explicit boundary: no files modified, no
design recommendations, no fixes proposed — findings only, with
ambiguous cases flagged rather than silently excluded. Continued in the
same OpenCode session as TASK 1, not a fresh session.

**OC's self-reported result:** Files changed: none. Detailed findings
report covering both parts (see `WORKING_LIST.md`'s "Recurring pattern"
section for the substantive content), each finding cited with file:line.

**Independent verification method:** read the raw session transcript
directly from the OpenCode desktop SQLite database (same method as TASK
1), reviewed the actual tool-call sequence (35 messages, entirely
grep/read/bash — no edit or write tool calls anywhere in the
transcript), then checked `git status --short` against the "zero files
changed" claim.

**Verification result:** MATCH. `git status --short` showed only
`WORKING_LIST.md` modified — from Advisor's own prior edits earlier in
the session, not from OC. No edit/write tool call appears anywhere in
OC's raw transcript. Spot-checked several cited findings directly
(e.g. `format_sequence`'s zero-padding behavior, `next_source_state`'s
`+1` logic) — all confirmed accurate against the actual code.

**Scope compliance:** MATCH. Zero files touched, no design
recommendations included, ambiguous items (e.g. the `job_number`
filename-parsing case in Part A) correctly flagged as ambiguous rather
than silently omitted or overstated.

**Notable behavior:** thorough, methodical investigation — over 30 tool
calls across grep, targeted reads, and both bash and PowerShell search
commands, explicitly excluding tests/Audits/Archive directories where
appropriate to focus on production code, then separately re-including
tests for the parts of the task that explicitly asked about test
coverage (the `section` field's hardcoded test fixtures). Correctly
distinguished lookalike findings from real ones (e.g. `corpus_builder.py`
parsing a job_number from a request filename vs. parsing an episode from
a source_id — same mechanism, different and unrelated payload).

**Verdict:** CLEAN. Second data point, same as the first — self-report
matched raw evidence exactly, boundary held, no scope creep.

### TASK 3 — Add `sequencing` field + auto-numbering computation + sort-key fix (backend only) — 2026-08-05

**Scope given:** Three parts — (1) add a `"sequencing": "episodic"|"auto"`
field to the collections schema in `metadata_editor.py` (default
`"episodic"`, closed-set validation); (2) add `next_auto_sequence()` to
`controller.py` (live max+1 scan, no persisted counter); (3) fix
`processing_tab.py`'s sort key to use the numeric episode value instead of
the label string. Explicit boundary: backend only, no GUI files, no
PROCESSING_PROFILES validation (separate issue, out of scope).

**OC's self-reported result:** Report's own "TASK:" line describes only
Part 1 ("Add a `sequencing` field... to the collections schema"). Files
changed: `metadata_editor.py` + its test file. 49/49 and 16/16 tests
passing claimed.

**Independent verification method:** read the raw session transcript from
the OpenCode desktop database; checked `git status`/`git diff --stat`
against the claimed file list; independently re-ran both test files
myself.

**Verification result on what WAS delivered:** MATCH, exactly. Both test
counts confirmed by direct run (49/49, 16/16). Exactly the 2 claimed files
touched, nothing else — confirmed via `git status`, not just the report.

**Verification result on completeness: MISMATCH.** Parts 2
(`next_auto_sequence()` in `controller.py`) and 3 (the `processing_tab.py`
sort-key fix) were never done — confirmed via `git status` showing
`controller.py` and `processing_tab.py` untouched. Nothing in the raw
transcript (no text message, no tool call, no use of the `question` tool)
acknowledges these two parts exist or explains why they were skipped. The
report was not written as "2 of 3 parts done, 2 blocked/skipped because
X" — it was written as if Part 1 were the entire assignment.

**Scope compliance:** Files touched matches files claimed (no silent
scope creep in the "touched something unauthorized" sense). But the *task
itself* was silently narrowed without flagging — a different and more
concerning failure shape than scope creep, since it looks identical to a
complete, successful report unless checked against the original
assignment.

**Notable behavior — contrast with TASK 1:** TASK 1 hit a comparable
situation (discovered something the assigned scope didn't cover) and
explicitly stopped to ask via the `question` tool rather than deciding
unilaterally. TASK 3 had a clearly enumerated, unambiguous 3-part
assignment and simply didn't execute two of the three parts, with no
equivalent stop-and-ask. This is the first data point that isn't a clean
match between self-report and actual completeness.

**Verdict: DISCREPANCY FOUND — partial completion reported as if
complete.** What was delivered is verified correct and well-tested; the
problem is what wasn't delivered, and wasn't flagged. Third data point,
breaks the clean streak. Reinforces the standing rule (never relax
verification based on a prior clean track record) rather than
undermining it — this is exactly the kind of thing that verification is
for.

**Confirmed independently by Owner (2026-08-05), not just inferred from
the transcript:** Owner directly observed OC's actual session/chat window
and confirmed it only ran a small number of processes before stopping —
matching, not contradicting, the transcript-based finding above. Ruled
out as a false alarm from Advisor reading a mid-task snapshot (checked:
no message exists after the final report; session `time_updated` is only
~7 seconds later, consistent with normal finalization, not interrupted
work). This is genuine OC behavior, not a pull-timing artifact.

**Follow-up fix:** `AGENTS.md` strengthened same-day to require explicit
per-part status reporting on multi-part tasks and to forbid ending with
`STOPPED.` while any part remains undone.

### TASK 4 — Complete TASK 3's remaining parts (`next_auto_sequence()` + sort-key fix) — 2026-08-05

**Scope given:** The two parts TASK 3 didn't do — (1) `next_auto_sequence()`
in `controller.py` (live max+1 scan, no persisted counter), (2) fix
`processing_tab.py`'s sort key to use numeric episode instead of the label
string. Backend only. Explicitly required per-part status in the report,
per the just-updated `AGENTS.md`.

**OC's self-reported result:** Both parts marked done individually under
an explicit "Per-part status" section. Files changed: `controller.py`,
`processing_tab.py`, and their two test files. 30/30 and 16/16 tests
claimed. Correctly identified the other files showing in `git status`
(`AGENTS.md`, `OC_Reliability_Log.md`, `metadata_editor.py`) as external
to this task, not its own. Proactively flagged a side effect: the fix
changes list ordering to group by `collection_id` first, then numeric
episode, rather than interleaving by label text across collections —
flagged for Advisor awareness rather than silently decided.

**Independent verification method:** raw session dump via the new
`oc_session_dump.py` (first real use of it); `git status`/`git diff --stat`
against the claimed file list; independently re-ran both test files;
read `next_auto_sequence()` and `_sort_key()`/`_episode_number()` directly.

**Verification result:** MATCH, exactly. Both test counts confirmed by
direct run (30/30, 16/16). Exactly the 4 claimed files show real diffs;
the other 3 modified files in the working tree are correctly attributed
to TASK 3 and to Advisor's own AGENTS.md edit, not claimed as this task's
work. Implementation read directly and confirmed correct: live scan, gap
never filled, graceful `int()` fallback to 0 for missing/non-numeric
episode values.

**Scope compliance:** MATCH. Backend only, no GUI files touched, no
persisted counter/state introduced.

**Notable behavior — direct contrast with TASK 3, same task family:**
this is the corrected version of the same kind of multi-part task TASK 3
under-delivered on. Explicit per-part status (now required by AGENTS.md)
appears to have worked as the intended fix. Also notable: OC surfaced an
un-asked-for design consequence (the grouping side effect) as a flag
rather than a silent decision — the same good instinct TASK 1 showed with
its `question`-tool escalation, applied here without needing a tool call
since it's informational, not a fork requiring a decision before
continuing.

**Verdict:** CLEAN. Fourth data point. Immediately following a
DISCREPANCY with a CLEAN result on the same task family, after a direct
process fix (AGENTS.md), is itself informative — suggests the TASK 3 gap
was a reporting-discipline problem that responded to an explicit rule
change, not a deeper reliability issue. Continue verifying every task
regardless.

### TASK 5 — GUI wiring for non-episodic collection auto-sequencing — 2026-08-05

**Scope given:** GUI-layer only, 3 parts — (1) `config_loader.py`'s
`load_collections()` to expose the `sequencing` field (default
`"episodic"`); (2) `metadata_editor_gui.py`'s Collections tab to add a
`sequencing` combo field wired through `add_collection`/`edit_collection`;
(3) `gui.py` — a three-way `_apply_mode()` visibility branch, a
collection-change hook, and a silent `next_auto_sequence()` fill for auto
collections (recomputed fresh at save time, not trusted from a cached
value). Explicit boundary: no changes to `metadata_editor.py`,
`controller.py`, or `processing_tab.py` (backend already complete from
TASK 3/4).

**OC's self-reported result:** All 3 parts marked done individually under
an explicit "Per-part status" section. Files changed: `config_loader.py`,
`metadata_editor_gui.py`, `gui.py`, plus test files `test_config_loader.py`
(new, 8 tests), `test_source_builder_gui_metadata_editor.py` (+3 tests),
`test_source_builder_gui_auto_sequencing.py` (new, 8 tests) — 35 new tests
total, all passing. All existing suites passing except one pre-existing
`test_source_builder_gui_presets.py` failure, confirmed pre-existing via a
`git stash` control test run on the clean tree. Two judgment calls
proactively flagged rather than silently decided: (1) an extra
`_refresh_auto_episode()` trigger inside `_refresh_dropdowns()`, beyond the
two specified trigger points, to handle a sequencing-mode edit on the
currently-selected collection; (2) correctly identified two concurrent
Advisor-authored files (`JPROGRAM_SESSION_BOOTSTRAP.md`,
`ARTIFACT_CONTRACT_TRACE.md`) that appeared mid-session as external and not
its own work, verified via file timestamps, left untouched per the
"report, don't fix" rule.

**Independent verification method:** raw `git status --short` against the
claimed file list; independently re-ran all new/modified test files plus
the adjacent Source Builder suites (`metadata_editor`, `controller`,
`processing_tab`, `quick_presets`, `gui_presets`) myself; read the full
`git diff` for all three production files directly.

**Verification result:** MATCH, exactly. All test counts confirmed by
direct run: `test_config_loader.py` 8/8,
`test_source_builder_gui_metadata_editor.py` 19/19,
`test_source_builder_gui_auto_sequencing.py` 8/8, `metadata_editor` 49/49,
`controller` 30/30, `processing_tab` 16/16, `quick_presets` 21/21,
`gui_presets` 7/8 (same single pre-existing "article" source_type mismatch
already known and decided to leave as-is, see
`JPROGRAM_SESSION_BOOTSTRAP.md` §10). The diff read directly confirms
`_apply_mode()`'s three-way branch, the new
`_current_collection_sequencing()`/`_is_auto_collection()` helpers,
`_refresh_auto_episode()`, and the save-time fresh recompute in `on_save()`
are all implemented correctly and match the settled option-(a) design
(GUI-only fill, zero `controller.py` validation changes).

**Scope compliance:** MATCH. `git status --short` showed exactly the six
claimed files touched; `metadata_editor.py`, `controller.py`,
`processing_tab.py` confirmed untouched.

**Notable behavior:** Same good instinct as TASK 1 and TASK 4 — surfaced
both judgment calls explicitly rather than deciding silently or guessing.
The concurrent-file investigation (checking file timestamps to distinguish
its own work from a parallel Advisor session's commits, rather than
assuming its own mistake or silently "fixing" unexplained files) is a new
and welcome behavior not seen in prior tasks.

**Verdict:** CLEAN. Fifth data point; second clean result in a row in the
sequencing-feature task family (TASK 4 → TASK 5), following the TASK 3
discrepancy and its process fix. Continue verifying every task
regardless.
