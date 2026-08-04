# GUI_ARCHITECTURE

**Japanese Corpus Pipeline — GUI Responsibilities and Boundaries**

Date: 2026-08-02
Targets: Production Manager API Version 1.0

---

## The Interface

```
GUI
  ↓  (calls)
Production Manager API  (status, report, dry_run, run_stage, pipeline)
  ↓  (launches)
subprocess()
  ↓
Sandboxed Stage Programs
  ↓
Artifacts
```

The GUI is a thin presentation layer. It never performs pipeline work.

---

## GUI Responsibilities

The GUI:

- **Displays information.** Shows pipeline state, per-stage status, evidence,
  progress, and results for each source.
- **Collects user input.** Selects sources, chooses actions (status, dry-run,
  run stage, run pipeline), provides metadata.
- **Calls the Production Manager API.** Uses the frozen Version 1.0 API
  functions (`status`, `report`, `dry_run`, `run_stage`, `pipeline`).
- **Displays progress.** Renders the structured `events` and `stages_run`
  returned by the API.
- **Displays logs.** Surfaces Production Manager and stage log output to the
  user.
- **Drag & drop.** Accepts dropped raw files and forwards them through the
  Production Manager flow.
- **Folder browsing.** Lets the user browse raw folders and pick sources.

---

## GUI MUST NOT

- **Perform pipeline logic.** No cleaning, job/request/API/corpus processing.
- **Inspect artifacts directly.** It reads state through the API, never by
  opening pipeline artifacts itself.
- **Import stage modules.** Never imports or executes `clean_subtitles.py`,
  `clean_transcript.py`, `job builder.py`, `request builder.py`,
  `deepseek_client.py`, or `corpus_builder.py`.
- **Execute subprocesses.** It never calls `subprocess` for pipeline work;
  only the Production Manager does.
- **Modify JSONL.** The corpus JSONL is owned by the Corpus Builder and is
  read-only to all other components.
- **Duplicate state decisions.** It never re-derives pipeline state from
  artifacts; it consumes the API's structured results.

---

## Boundaries Enforced

- The Production Manager is the only orchestrator.
- Stage programs are the only artifact writers.
- The GUI consumes structured data and produces user interaction.
- No component bypasses these layers.
