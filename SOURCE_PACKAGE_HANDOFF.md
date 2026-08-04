# SOURCE_PACKAGE_HANDOFF

**Japanese Corpus Pipeline — Source Package and Handoff**

Date: 2026-08-04
Status: Current-state reference (matches the implemented Source Builder)

This document describes how a source is created, packaged, and handed off to
the processing pipeline. It covers the Source Package workflow, the Handoff
workflow, the Registry, and the transition into Processing.

---

## 1. Source Creation

**Module:** `Source Builder\controller.py`

The Source Builder captures a source in one of two mutually exclusive identity
modes:

- **Collection mode** — `collection_id` + `episode` (+ source_type, origin).
- **Standalone mode** — `source_name` (+ source_type, origin).

`controller.create_collection_source` / `create_standalone_source`:

1. Validate the identity, metadata, and source text (via `validate_*_fields`).
2. Derive the canonical filename:
   - Collection: `{collection_id}_ep{NNNN}.txt`
   - Standalone: `{source_name}.txt`
3. Write the canonical file atomically to:
   - `Sources\collections\<collection_id>\<collection_id>_epNNNN.txt`
   - `Sources\standalone\<source_name>.txt`
4. Attempt to write the Source Package sidecar (see below). A package error
   does not fail the save; it is reported as a warning.

The Ready State Engine (`controller.ReadyStateEngine`) only permits a save when
the workflow state is `READY`.

---

## 2. Source Package Creation

**Module:** `Source Builder\source_package.py`

Every canonical source file gets a sidecar **Source Package**:

```
Sources\collections\<collection_id>\<collection_id>_epNNNN.txt
Sources\collections\<collection_id>\<collection_id>_epNNNN.source.json
```

Key constants:

- `artifact_type = "source_package"`
- `schema_version = "1"`
- `format = "txt"` (all canonical source files are plain text)

Fields written by `build_package`:

- `artifact_type`, `schema_version`
- `source_id` (derived via `derive_source_id(source_type, slug_seed, episode)`)
- `source_type`, `origin`, `language` (project-level, `ja`)
- `canonical_path`, `original_filename`, `format`
- `cleaning_profile` (null when the source_type has no processing profile),
  `cleaner_version`
- `sha256` (hash of the canonical file)
- `created_at`, `created_by_version`
- `collection_id` + `episode` (collection mode) OR `source_name`
  (standalone mode)

`validate_package(package)` returns a list of error strings; `write_package`
validates and atomically writes the sidecar. The package is the primary
identity and provenance record used downstream.

> Only `podcast_transcript` currently maps to a processing profile
> (`transcript_standard_v1` → `clean_transcript`). Source types without a
> profile produce a package with `cleaning_profile: null`, which cannot be
> handed off until a profile is configured.

---

## 3. Handoff

**Module:** `Source Builder\handoff.py`

Handoff turns a Source Package into the pipeline intake artifacts:

- **Source Registry** entry → `Source Registry\<source_id>.json`
- **Cleaning Job** → `Cleaning Jobs\<source_id>.cleaning_job.json`

Flow (`handoff(package, force=False)`):

1. Load + validate the package (`load_source_package`).
2. Build the registry entry (`registry_entry_for`) using the Source Intake
   `registry.build_entry` writer.
3. Build the cleaning job (`cleaning_job_for`) using the Source Intake
   `cleaning_job.build_job` writer:
   - `raw_path` = the canonical Source Builder file.
   - `output_path` = `Cleaned Archive\<source_id>.clean.txt` (resolved via
     `Source Intake\resolver.py`).
4. Write both artifacts atomically (UTF-8, `ensure_ascii=False`,
   `sort_keys=True`).

**Idempotency:** same `source_id` + same `sha256` → handoff reports the
artifacts already exist and creates nothing. Existing valid artifacts are
never overwritten unless `force=True`.

**Error handling:** `HandoffError` is raised when the package is missing,
unreadable, invalid, or missing required fields for either artifact.

**Entry points:**
- `handoff(package)` — package dict.
- `handoff_for_package_path(package_path)` — load then handoff.

---

## 4. Registry

**Writer:** `Source Intake\registry.py`
**Schema:** `Source Intake\schemas.py` → `ARTIFACT_SCHEMAS["registry"]`
**Location:** `Source Registry\<source_id>.json`

The registry answers *"What is this source?"*:

- identity: `source_id`, `original_filename`, `sha256`
- classification: `source_type`, `format`, `language`
- processing: `cleaning_profile`, `cleaner_version`
- optional lineage: `cleaned_artifact`, `parser_version`,
  `validator_version`, `canonical_corpus`

The registry is written only by its owning writer (via Handoff in the GUI
path). No other component silently modifies it.

---

## 5. Cleaning Job

**Writer:** `Source Intake\cleaning_job.py`
**Schema:** `Source Intake\schemas.py` → `ARTIFACT_SCHEMAS["cleaning_job"]`
**Location:** `Cleaning Jobs\<source_id>.cleaning_job.json`

The cleaning job answers *"What should the cleaner process?"*:

- `source_id`
- `raw_path` (canonical Source Builder file)
- `source_type`, `cleaning_profile`, `cleaner_version`
- `output_path` (Cleaned Archive target)

---

## 6. Transition into Processing

**Module:** `Source Builder\processing_tab.py`

The Processing window lists saved source packages (discovered from `Sources\`).
When the user selects sources and runs **Process Selected**,
`process_sources(packages)`:

1. For each package, `_ensure_registered(package)` runs the Handoff if the
   package has no registry entry yet.
2. Then the Production Manager pipeline runs sequentially:
   `clean → jobs → requests → api → corpus` (`pm.pipeline(..., auto=True)`).

**Retry Failed** (`failed_sources`) selects packages whose PM state is
`failed` and re-runs the pipeline.

**Run Analysis** (`run_analysis`) requires a completed corpus (`jsonl` file);
it runs the frequency analyzer and writes `Analysis\outputs\*.frequency.json`.

The pipeline itself (clean → corpus) is owned by the stage programs and the
Production Manager; Handoff only creates the intake artifacts (Registry +
Cleaning Job).
