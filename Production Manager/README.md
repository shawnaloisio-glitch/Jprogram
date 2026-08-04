# Production Manager

The Production Manager orchestrates the Japanese Corpus Pipeline for a
single source. It is a thin control layer: it observes artifacts, launches
existing stage programs, and reports status. It performs no processing and
contains no stage logic.

## Purpose

- Report the pipeline state of a source from artifact evidence alone.
- Launch individual processing stages manually.
- Run a source through the full pipeline to a validated corpus.
- Support guided (interactive) and automatic development workflows.

## Ownership Boundaries

The Production Manager is strictly an observer and process launcher.

**Allowed (manager writes only):**

- `Logs\Production Manager\manager.log` — append-only run log.
- Optional human-readable reports under the same folder.

**Forbidden (manager never writes):**

- Source Registry
- Cleaning Jobs / Cleaning Results
- Cleaned Archive
- Jobs / Job Results
- Requests / Request Results
- Responses / Processing Results
- Corpus Results / JSONL
- Analysis outputs

Every pipeline artifact is written exclusively by its owning stage
program. The manager only reads them to decide and report state.

## Artifact-Only Decisions

The manager stores no hidden state and uses no database. Every decision is
derived from the on-disk artifacts by `state_for(source_id)`. Corrupted or
malformed artifacts are reported but never deleted; a stage retry
deterministically overwrites them.

## State Machine

| State | Artifact evidence | Next stage |
|---|---|---|
| unregistered | no registry entry | intake (external) |
| registered | Source Registry only | intake (external) |
| waiting_for_clean | Cleaning Job exists, no success result | clean |
| cleaned | Cleaning Result success + artifact | jobs |
| jobs_created | Job Result success / job files | requests |
| requests_created | request files present, API not started | api |
| api_processing | some responses present, set incomplete | api |
| api_complete | all responses + Processing Result | corpus |
| corpus_available | JSONL + Corpus Result success | — (terminal) |
| failed | any stage result success=false | retry that stage (manual) |

A stage launch is considered successful only when BOTH the subprocess exit
code is zero AND the stage's expected result artifact validates
(`success:true` for clean/jobs/requests/corpus; no failed job in the
Processing Result for api).

## CLI

```
python production_manager.py --source <source_id>
    Read-only status report.

python production_manager.py --run <stage> --source <source_id>
    Run one stage manually: clean | jobs | requests | api | corpus.

python production_manager.py --pipeline <source_id>
    Run the pipeline to a validated corpus. Guided mode: pauses after each
    completed stage, shows artifact evidence, and asks before the next stage.

python production_manager.py --pipeline --auto --source <source_id>
    Run all remaining stages without pauses.

python production_manager.py --pipeline --dry-run --source <source_id>
    Print the planned stages without launching anything or writing anything.

Stage toggles (work with --pipeline and the status report):
    --enable  clean,jobs      only these stages may run
    --disable api             skip these stages

    A disabled stage is never launched; the pipeline stops at the first
    disabled stage in the sequence.

Options:
    --timeout <seconds>   optional subprocess timeout.
```

## Recovery Workflow

1. A failing stage stops the pipeline; the manager reports the failed
   stage and the error summary. There is no automatic retry.
2. Fix the cause (data, config, credentials, network), then re-run the
   failed stage explicitly:
   `python production_manager.py --run <stage> --source <source_id>`
3. Or re-run the pipeline; it recomputes state from artifacts and resumes
   at the correct next stage.
4. A source already at `corpus_available` is reported as complete and is
   never reprocessed.

## Boundaries Enforced

- Pipeline stage programs are invoked as isolated subprocesses with argv
  lists (never shell strings); their logic is never imported.
- The manager writes only its own log. All pipeline artifacts remain owned
  by their stage programs.
- No Analysis Manager, batch processing, cost analysis, or GUI features are
  part of this module.
