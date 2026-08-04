# GUI_API

**Production Manager Public API — Frozen Interface for Frontends**

API Version: 1.0 (see API_VERSION.md)
Date: 2026-08-02

This document is the contract between the GUI (and any future frontend) and
the Production Manager. All functions live in
`Production Manager/production_manager.py` and are importable as:

```python
from production_manager import status, report, dry_run, run_stage, pipeline
```

---

## Architectural Rule

```
GUI
  ↓
Production Manager API
  ↓
subprocess()
  ↓
Sandboxed Stage Programs
```

The GUI must never import or execute stage programs directly. All pipeline
work flows through the Production Manager API.

---

## status(source_id, enabled=None)

**Purpose:** Return the current pipeline state for a source from artifact
evidence only. Read-only; never launches anything.

**Parameters:**
- `source_id` (str, required) — the source identifier.
- `enabled` (set or None, optional) — set of stage names allowed to run;
  affects the reported next_stage / stage markers. Defaults to all stages.

**Return structure (dict):**
- `success` (bool) — always True (read-only success).
- `source_id` (str) — echo of the input.
- `state` (str) — one of: `unregistered`, `registered`, `waiting_for_clean`,
  `cleaned`, `jobs_created`, `requests_created`, `api_processing`,
  `api_complete`, `corpus_available`, `failed`.
- `failed_stage` (str or None) — the failing stage when `state == "failed"`.
- `next_stage` (str or None) — the stage to run next (None when terminal).
- `stages` (dict) — per-stage status: `{stage: "done"|"failed"|"pending"}`.
- `evidence` (dict) — the raw artifact-evidence map (booleans/counts).

**Exit/error conditions:** None. This function does not raise for missing
sources; an unknown source returns `state: "unregistered"`.

**Example call:**
```python
data = status("podcast_transcript_con-teppei_ep052")
```

**Example returned dictionary:**
```json
{
  "success": true,
  "source_id": "podcast_transcript_con-teppei_ep052",
  "state": "corpus_available",
  "failed_stage": null,
  "next_stage": null,
  "stages": {
    "clean": "done", "jobs": "done", "requests": "done",
    "api": "done", "corpus": "done"
  },
  "evidence": { "...": true }
}
```

---

## report(source_id, enabled=None)

**Purpose:** Return a structured human-relevant report for a source.

**Parameters:** Same as `status`.

**Return structure (dict):** Identical to `status` — `success`, `source_id`,
`state`, `failed_stage`, `next_stage`, `stages`, `evidence`.

**Exit/error conditions:** None (same guarantees as `status`).

**Example call:**
```python
data = report("podcast_transcript_con-teppei_ep052")
```

**Example returned dictionary:** same shape as `status`.

---

## dry_run(source_id, enabled=None)

**Purpose:** Return the planned pipeline stages without launching anything.
Read-only; never writes artifacts.

**Parameters:**
- `source_id` (str, required).
- `enabled` (set or None, optional) — restrict allowed stages.

**Return structure (dict):**
- `success` (bool) — always True.
- `source_id` (str).
- `state` (str) — the terminal state the plan would reach (e.g.,
  `corpus_available`).
- `plan` (list of str) — ordered stages that would run.
- `boundary` (str or None) — why the plan stopped, e.g. `intake`,
  `disabled:<stage>`, `failed:<stage>`, or None when it reaches
  `corpus_available`.

**Exit/error conditions:** None.

**Example call:**
```python
data = dry_run("podcast_transcript_con-teppei_ep052")
```

**Example returned dictionary:**
```json
{
  "success": true,
  "source_id": "podcast_transcript_con-teppei_ep052",
  "state": "corpus_available",
  "plan": ["clean", "jobs", "requests", "api", "corpus"],
  "boundary": null
}
```

---

## run_stage(source_id, stage, timeout=None, enabled=None)

**Purpose:** Run exactly one stage for a source and return structured result
data. This is the manual/step execution entry point.

**Parameters:**
- `source_id` (str, required).
- `stage` (str, required) — one of `clean`, `jobs`, `requests`, `api`,
  `corpus`.
- `timeout` (int or None, optional) — subprocess timeout in seconds.
- `enabled` (set or None, optional) — reserved; not used to gate a manual
  run.

**Return structure (dict):**
- `stage` (str) — the stage that ran.
- `source_id` (str).
- `command` (list of str) — the argv used (empty list if none).
- `exit_code` (int or None) — subprocess exit code, or None on pre-launch
  failure / timeout.
- `stdout` (str) — captured stdout.
- `stderr` (str) — captured stderr.
- `success` (bool) — True only when exit code is 0 AND the stage's result
  artifact validates.
- `error` (str or None) — failure description.
- `state` (dict or None) — refreshed `state_for` result on success, else
  None.

**Exit/error conditions:** The function never raises for a failing stage; it
returns `success: false` with an `error` describing the cause (missing
executable, non-zero exit, missing/invalid result artifact, timeout).

**Example call:**
```python
result = run_stage("podcast_transcript_con-teppei_ep052", "jobs", timeout=300)
```

**Example returned dictionary (success):**
```json
{
  "stage": "jobs",
  "source_id": "podcast_transcript_con-teppei_ep052",
  "command": ["python", "Data Processor/job builder.py", "--source", "..."],
  "exit_code": 0,
  "stdout": "",
  "stderr": "",
  "success": true,
  "error": null,
  "state": { "state": "jobs_created", "...": "..." }
}
```

**Example returned dictionary (failure):**
```json
{
  "stage": "jobs",
  "source_id": "podcast_transcript_con-teppei_ep052",
  "command": ["python", "Data Processor/job builder.py", "--source", "..."],
  "exit_code": 5,
  "stdout": "",
  "stderr": "boom",
  "success": false,
  "error": "stage exited with code 5",
  "state": null
}
```

---

## pipeline(source_id, auto=False, timeout=None, confirm_fn=None,
           enabled=None, dry_run=False)

**Purpose:** Execute the pipeline for a source to a validated corpus and
return structured result data. This is the non-printing engine behind the
CLI; it never prints and never imports argparse.

**Parameters:**
- `source_id` (str, required).
- `auto` (bool, optional) — when True, run all remaining stages without
  pauses. Default False (guided mode pauses between stages).
- `timeout` (int or None, optional) — subprocess timeout in seconds.
- `confirm_fn` (callable or None, optional) — used only in guided mode
  (`auto=False`). Receives the prompt text and returns a string; the caller
  decides how to present it. For non-interactive callers, pass a function
  that returns `"y"`.
- `enabled` (set or None, optional) — allowed stages.
- `dry_run` (bool, optional) — when True, plan and return without launching
  or writing.

**Return structure (dict):**
- `success` (bool).
- `exit_code` (int) — 0 complete/stopped, 1 failure/intake/no-progress,
  2 paused by user.
- `source_id` (str).
- `state` (str) — terminal or stopping state.
- `failed_stage` (str or None).
- `next_stage` (str or None).
- `stages_run` (list of str) — stages that were launched.
- `exit_codes` (dict) — `{stage: exit_code}` for launched stages.
- `boundary` (str or None) — stop reason: `intake`, `paused`,
  `disabled:<stage>`, `failed:<stage>`, `no_progress`, `unsupported:<stage>`,
  `stopped`, or None when `corpus_available`.
- `plan` (list of str) — present only in `dry_run` mode.
- `events` (list of dict) — one event per launched stage (see PART 3).

**Exit/error conditions:** The function returns structured results rather
than raising. Failures produce `success: false` with `exit_code: 1` and an
appropriate `boundary`. Guided-mode cancellation produces `exit_code: 2`.

**Example call (auto):**
```python
result = pipeline("podcast_transcript_con-teppei_ep052",
                  auto=True, timeout=300)
```

**Example returned dictionary (auto, complete):**
```json
{
  "success": true,
  "exit_code": 0,
  "source_id": "podcast_transcript_con-teppei_ep052",
  "state": "corpus_available",
  "failed_stage": null,
  "next_stage": null,
  "stages_run": ["clean", "jobs", "requests", "api", "corpus"],
  "exit_codes": {"clean": 0, "jobs": 0, "requests": 0, "api": 0, "corpus": 0},
  "boundary": null,
  "events": [ "...stage event objects..." ]
}
```

**Example call (dry-run):**
```python
result = pipeline("podcast_transcript_con-teppei_ep052", auto=True,
                  dry_run=True)
```

**Example returned dictionary (dry-run):**
```json
{
  "success": true,
  "exit_code": 0,
  "source_id": "podcast_transcript_con-teppei_ep052",
  "state": "corpus_available",
  "failed_stage": null,
  "next_stage": null,
  "stages_run": [],
  "exit_codes": {},
  "plan": ["clean", "jobs", "requests", "api", "corpus"],
  "boundary": null,
  "events": []
}
```

---

## Guaranteed Fields by API

| API | Always present | Present conditionally |
|---|---|---|
| `status` | success, source_id, state, failed_stage, next_stage, stages, evidence | — |
| `report` | same as `status` | — |
| `dry_run` | success, source_id, state, plan, boundary | — |
| `run_stage` | stage, source_id, command, exit_code, stdout, stderr, success, error | `state` (on success) |
| `pipeline` | success, exit_code, source_id, state, failed_stage, next_stage, stages_run, exit_codes, boundary, events | `plan` (dry_run only) |

---

## Event Contract

The `events` list returned by `pipeline()` contains one structured stage
result object per launched stage. Fields per event:

- `type` (str) — the stage name (`clean`, `jobs`, `requests`, `api`,
  `corpus`). This is the existing event discriminator.
- `stage` (str) — the stage that ran (same as `type`).
- `source_id` (str) — the source.
- `command` (list of str) — the argv used.
- `exit_code` (int or None).
- `stdout` (str).
- `stderr` (str).
- `success` (bool).
- `error` (str or None).
- `state` (dict or None) — refreshed state on success.

There is no separate timestamp field in the current event objects; timing is
available in the Production Manager run log. No new events are added by this
contract; this documents the existing structure only.

---

## Future Extension Points

- **Production Manager:** pipeline orchestration, state engine, artifact
  verification.
- **GUI:** watch folders, notifications, settings, progress bars, batch
  selection.
- **Stage Programs:** subtitle cleaning, transcript cleaning, ebook cleaning,
  parser improvements.
- **Analysis Manager:** statistics, corpus analysis, vocabulary, reports.
