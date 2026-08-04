# SOURCE_BUILDER_SPEC

**Japanese Corpus Pipeline — Source Builder V1 Design Specification**

Date: 2026-08-02 (updated 2026-08-03: Ready State Engine)
Status: DESIGN SPECIFICATION (V1, post-implementation)

> **Current-UI terminology note (2026-08-04):** this design document predates
> later UI terminology updates. In the implemented UI: "Create Next Source"
> is **"Add Another"**; the "Workflow Panel" is titled **"Status"**; the
> "Quick Presets" panel is titled **"Templates"**; and the "Send to
> Processing" action was removed (processing is done via the Processing tab).

The Source Builder is the GUI that assembles canonical source files before
they enter the processing pipeline.

---

## Purpose

The Source Builder is the human entry point for creating source files. A
human pastes raw content (transcript, subtitle, article, etc.), reviews it,
and saves it as a canonical source file that the processing pipeline (Source
Intake → Cleaners → ... → Corpus) will later consume.

It replaces the manual process of placing files into raw folders by hand with
a guided, metadata-driven workflow that prevents identity and metadata errors.

---

## Source Builder Design Principles

These principles govern the Source Builder's design. They take priority over
individual feature decisions.

1. **Prevent incomplete canonical source files.** The Source Builder must
   prevent creation of incomplete canonical source files. A file is only
   written when the active identity, required metadata, and source text are
   complete and valid.

2. **Guided workflow application.** The GUI is a guided workflow
   application. It should always indicate the current workflow state and the
   single next valid action.

3. **The Ready State Engine owns workflow state.** The Ready State Engine
   owns workflow state. The GUI presents that state. The GUI must never
   implement workflow decision logic.

4. **The Workflow Panel is the primary user feedback mechanism.** Routine
   workflow information is displayed there. Modal dialogs are reserved for
   unexpected runtime failures only.

5. **Prevent invalid actions rather than correct them afterwards.** Invalid
   actions should be prevented rather than corrected afterwards. If Save is
   enabled, Save should succeed.

6. **Workflow efficiency over visual polish.** Workflow efficiency takes
   priority over visual polish. Reduce clicks. Reduce mouse movement. Reduce
   interruptions.

7. **Administrative actions separated from production workflow.**
   Administrative actions remain visually separated from production
   workflow.

---

## Guided Workflow

The Source Builder is a **guided workflow** application.

- The GUI directs the user toward the next valid action at all times. It
  never leaves the user guessing what to do next.
- The **Ready State Engine** determines workflow state
  (`INCOMPLETE` / `READY` / `SAVED` / `ERROR`). The GUI presents that state;
  it never decides it.
- The **Workflow Panel** communicates workflow state. It is the primary
  feedback area and is never blank.
- The GUI **prevents incomplete canonical source creation**: Save is only
  enabled when the controller reports `READY`, so an enabled Save always
  succeeds.
- **Workflow efficiency has priority over visual polish.** Repetitive source
  entry minimizes clicks, mouse movement, and interruptions:
  - large, solid-filled workflow buttons grouped together (Save Source +
    Create Next) for repeated clicking,
  - administrative actions (Open Folder, Edit Metadata...) visually separated
    at the far right,
  - fixed-width dropdowns that do not span the window,
  - the Workflow Panel drawn prominently below the action row so the outcome
    of every action is immediately visible,
  - the filename preview moved into the Workflow Panel as secondary
    reference information, keeping the primary workflow message dominant.

---

## Responsibilities

The Source Builder:

- Selects a source identity (collection or standalone).
- Collects stable metadata (source_type, collection_id, origin).
- Accepts pasted raw text.
- Displays the pasted text for visual inspection.
- Generates the source filename automatically from the identity.
- Saves the canonical source file into the canonical `Sources\` storage
  location (path determined automatically; the user never picks a save
  location).
- Remembers stable settings where appropriate (e.g., last source_type,
  last origin) to speed up repeated entry.
- Moves on to the next item after each save.

---

## Non-Responsibilities

The Source Builder does NOT:

- Clean text.
- Perform OCR.
- Parse text.
- Call APIs (including the DeepSeek parser).
- Create JSONL.
- Manage pipeline stages.
- Modify artifacts or schemas.
- Duplicate the Production Manager's or pipeline stages' logic.

It is a capture-and-save front end only. Everything downstream of a saved
source file is owned by the existing pipeline.

---

## Metadata Model

Stable controlled fields:

| Field | Meaning | Managed by |
|---|---|---|
| `source_type` | Content format (podcast_transcript, subtitle, article, manga_text, book_text, ...) | `Config\source_types.json` |
| `collection_id` | Controlled collection identifier (used only in collection mode) | `Config\collections.json` |
| `origin` | Where the material came from | `Config\origins.json` |

Machine-friendly names are acceptable and preferred. There are no commercial
UI naming requirements.

Source types are not bound to a fixed content medium. `subtitle` does not
mean "anime only"; collections determine context.

### Language is a project-level property

Language is a project-level property, not source metadata. Each project
installation represents one language. This project represents Japanese;
the language constant is `ja`.

Language is NOT a source-level field:

- not collected in the Source Builder UI,
- not stored in quick presets,
- not part of source metadata validation,
- not stored per source,
- not present in `Config\` (there is no `languages.json`).

The project language is preserved internally (e.g., `PROJECT_LANGUAGE` in the
Source Builder controller) where downstream processing needs it.

### Identifier contract

Identifiers are stable system/vocabulary keys. They are immutable after
creation.

**Collection IDs are storage identifiers.** They directly map to collection
folders and filename prefixes:

```
Collection ID: teppei_beginner
Creates:       Sources\collections\teppei_beginner\
Files:         teppei_beginner_ep0001.txt
```

Collection IDs are immutable after creation because they directly control the
collection folder name, the filename prefix, and the canonical storage path.
The metadata editor labels this field "Collection ID (folder name)" with a
lock indicator and an explanation that it cannot be changed later.

**Source Type IDs and Origin IDs are controlled vocabulary identifiers.**
They are internal references used by presets and validation (source types)
and by source tracking (origins). They do NOT affect folders, filenames, or
storage paths. They are immutable after creation; their display names remain
editable.

**Normal users do not delete metadata.** The normal metadata editor exposes
Add and Edit only. Metadata entries may be referenced by existing source
files, presets, future corpus tools, and processing pipelines, so destructive
operations (unused-metadata cleanup, archival, reference repair, deletion)
belong to future administrator tools. Safety checks remain in the data layer.

### Configuration location

Config controls metadata selection:

```
C:\Jprogram\Config\
    collections.json
    source_types.json
    origins.json
```

Machine-friendly names remain the canonical values.

---

## Identity Model

A source has exactly one identity type. `identity_type` is a binary choice:

- `collection`
- `standalone`

These are mutually exclusive:

- No "none" collection.
- No empty collection.
- No simultaneous collection + standalone.

### Collection mode

Fields:

- `identity_type`: `collection`
- `collection_id`: a controlled vocabulary value (from collections config)
- `episode`: a numeric value

Example:

```
identity_type: collection
collection_id: teppei_beginner
episode: 0051
```

Generated source filename:

```
teppei_beginner_ep0051.txt
```

### Standalone mode

Fields:

- `identity_type`: `standalone`
- `source_name`: a user-supplied identifier

Example:

```
identity_type: standalone
source_name: nhk_weather_article_august
```

Generated source filename:

```
nhk_weather_article_august.txt
```

---

## Canonical Source Unit

The canonical input unit is ONE SOURCE ITEM PER FILE.

Examples:

- podcast episode = one file
- anime episode subtitle = one file
- manga chapter = one file
- article = one file

Compilation files are no longer the canonical format. A single file holds a
single source item with a single identity. Batch import/export may be added
later as convenience features, but the canonical on-disk unit remains one
item per file.

---

## Canonical Source Storage

The finalized production storage model places all canonical source files
under a single `Sources\` root.

```
C:\Jprogram\Sources\
    collections\
        <collection_id>\
            <collection_id>_epNNNN.txt

    standalone\
        <source_name>.txt
```

Examples:

Collection:

```
Sources\
    collections\
        teppei_beginner\
            teppei_beginner_ep0051.txt
```

Standalone:

```
Sources\
    standalone\
        nhk_weather_article_august.txt
```

### Ownership rule

The Source Builder owns creation of canonical source files. The user does not
manually select save locations during the normal workflow. The save path is
determined automatically from the active identity:

- `identity_type`, `collection_id`, `episode` (collection mode), or
- `source_name` (standalone mode).

### Identity to storage rule

- `identity_type = collection` requires `collection_id` and `episode`.
  Creates:
  `Sources\collections\<collection_id>\<collection_id>_epNNNN.txt`
- `identity_type = standalone` requires `source_name`.
  Creates:
  `Sources\standalone\<source_name>.txt`

The two identity paths remain mutually exclusive.

---

## Production Install Assumption

Development and testing will eventually be completed. The production
workflow begins from a clean empty project structure. Existing development
datasets are migrated separately and are not the canonical production state.

---

## GUI State Rules

- The identity type is selected first. Exactly one of Collection or
  Standalone is active at any time; only the active path's fields are shown.
- When Collection is active, the collection_id is chosen from a dropdown
  (never free-typed), and the episode is a numeric value.
- When Standalone is active, the source_name is a free-text identifier field.
- The generated filename is always derived from the active identity; it is
  never free-typed.
- A source cannot be saved without a complete, valid identity.
- Duplicate target filenames must be flagged before saving (prevent
  accidental overwrite).

All GUI behaviour derives from the Ready State (see Ready State Engine
below). The GUI does not decide workflow state; it asks the controller.

---

## Ready State Engine

The Ready State Engine is part of the implemented architecture. It is a
controller-owned finite state machine that owns workflow state and workflow
decisions. The GUI presents that state; it never implements workflow decision
logic.

### Canonical states

The engine reports exactly one of four states:

| State | Meaning | Examples |
|---|---|---|
| `INCOMPLETE` | One or more required conditions are not satisfied | source text empty, required metadata missing, episode/source name invalid, filename already exists |
| `READY` | All required information exists; saving will succeed | identity selected, metadata valid, episode/source name valid, source text present, filename available |
| `SAVED` | A successful save has completed | — |
| `ERROR` | An unexpected runtime failure occurred | — |

### All GUI behaviour derives from these states

Examples:

- **Button enablement:** Save is enabled only in `READY`. Create Next is
  enabled only in `SAVED`.
- **Button colour:** buttons are coloured to indicate the current valid
  action (green when enabled; neutral/grey when not).
- **Workflow Panel messages:** the panel always shows the current state's
  message (e.g. "Waiting for source text.", "Ready to Save.",
  "Saved successfully", "Filename: <filename>", "Ready for next <label>.").
  The panel is never blank.
- **Create Next availability:** Create Next is only available in `SAVED`;
  selecting it returns the workflow to `INCOMPLETE`.

### State transitions

```
INCOMPLETE ──(all requirements met)──► READY
READY      ──(successful save)──────► SAVED
SAVED      ──(Create Next)──────────► INCOMPLETE
SAVED      ──(field edited)─────────► INCOMPLETE (or READY)
any        ──(unexpected failure)───► ERROR
ERROR      ──(reset)────────────────► INCOMPLETE
```

### Save rule

Save must never be clickable unless the controller reports `READY`. If the
Save button is enabled, Save should succeed. Invalid actions are prevented
rather than corrected afterwards.

### Blocking reasons

In `INCOMPLETE`, the engine reports the first blocking reason, in order:

1. identity type missing,
2. collection or source name missing,
3. episode missing / invalid / negative,
4. source type or origin missing,
5. source text empty,
6. filename already exists.

---

## Architectural Responsibilities

Responsibilities are split so the controller owns decisions and the GUI only
presents them.

### Controller

- owns the Ready State Engine,
- owns workflow decisions,
- owns validation,
- owns filename generation,
- owns canonical source file creation.

### GUI

- presents workflow state,
- displays button colours,
- enables/disables controls,
- shows Workflow Panel messages,
- never decides workflow state,
- never decides whether a save should be allowed.

---

## Workflow Panel

The Workflow Panel is the primary user feedback mechanism. It is the
permanent, non-blank status area below the action buttons. It is drawn
visually dominant so it naturally draws the user's attention after pressing a
button.

Routine workflow information is displayed there, in order:

1. **Workflow** — the current state's message (primary information):
   - blocking reason in `INCOMPLETE`,
   - "Ready to Save." in `READY`,
   - "Saved successfully." in `SAVED`,
   - clear error message in `ERROR`.
2. **(blank line)**
3. **Filename** — the canonical filename (secondary reference information).
4. **Save Location** — the canonical `Sources\` path (secondary reference
   information).

The workflow message is the primary information; the filename and save
location are secondary reference information. They are updated live from the
current form and from the Ready State.

Modal dialogs are reserved for unexpected runtime failures only. Routine
workflow information is never delivered via a modal dialog.

---

## Quick Presets

The Quick Presets panel sits in the right-side UI dead space and provides
one-click population of common source configurations. Six preset slots are
available; each slot carries a display name and references existing Config
vocabulary values:

- `identity_type` (collection or standalone),
- `collection_id` (collection mode) or `source_name` (standalone mode),
- `source_type`,
- `origin`.

Presets reference existing source configuration values; they never duplicate
full metadata. Language is never stored in a preset (it is a project-level
property).

### One-shot behaviour

Presets are NOT linked state and are NOT live bindings:

- A preset button press populates the fields once.
- After population the preset has no further control over the form.
- User edits on the left side always take priority.
- Changing dropdowns manually is never overwritten by the preset afterwards.
- The Ready State Engine continues to evaluate the current form only.

Applying a preset performs no save, no reset, and no automatic sync. The
status message reports `Preset loaded: <display name>`.

### Empty slots

An unconfigured slot shows the label `Empty Slot`. Pressing an empty slot
reports that it is empty rather than changing the form.

### Editing

**Edit Presets...** opens a separate editor window with a slot selector
(1–6), display name, identity type, collection/source-name, source type, and
origin fields, plus Save Preset / Cancel. Saving validates the slot and
writes the preset; the panel relabels immediately.

---

## Filename Generation Rules

- Collection mode: `{collection_id}_ep{episode:04d}.txt`
  - `teppei_beginner` + episode 51 → `teppei_beginner_ep0051.txt`
- Standalone mode: `{source_name}.txt`
  - `nhk_weather_article_august` → `nhk_weather_article_august.txt`
- Filenames are machine-friendly (lowercase, underscores, no spaces).
- Episode numbers are zero-padded to four digits.

---

## Future Extension Points

- **Batch import/export:** bulk creation of source files (convenience only;
  does not change the canonical one-item-per-file format).
- **Additional source types:** extend `Config\source_types.json`.
- **Additional collections / origins:** extend the corresponding config files
  without code changes.
- **OCR:** a future optional capture path for image-based sources; the Source
  Builder itself never performs OCR.
- **Raw folder routing:** the canonical `Sources\` storage is the frozen
  model. When the pipeline grows more source types, routing from
  `Sources\` to pipeline raw folders is a pipeline concern, not a Source
  Builder concern.

---

## Migration Note (future)

Existing development datasets will be converted into canonical Source
Builder files before production use. Migration should:

- assign correct metadata,
- create canonical filenames,
- place files into `Sources\`,
- validate through Source Intake.

Existing datasets are not modified during this documentation task.

---

## Workflow Convenience Elements

After a successful save, the Source Builder offers small post-save actions
to support the one-person workflow. These are conveniences only; they do not
expand Source Builder responsibilities.

Available actions after save:

- **Open Source Folder** — opens the folder containing the saved source file
  for quick verification. Does not modify files; does not bypass ownership
  rules.
- **Launch Production Manager** — opens the Production Manager
  interface/application to transition from source creation to processing.
  Does not run stages directly, contains no pipeline logic, does not inspect
  artifacts, and does not bypass the Production Manager API. It is a
  navigation convenience only: it does NOT automatically select the newly
  created source, the most recent source, any source_id, or any previous
  processing target. The Production Manager opens with no source
  pre-selected.
- **Create Next Source** — returns the user to the source creation screen
  for the repeated workflow. Retains stable metadata (collection_id,
  source_type, origin) and resets source-specific fields (episode number,
  pasted text, Ready State). It is enabled only when the Ready State
  is `SAVED`. Its label is dynamic ("Create Next Transcript", "Create Next
  Subtitle", ...) based on the current Source Type to reduce cognitive load
  during repetitive entry.

### Production Manager launch rule

The **Launch Production Manager** button is a navigation convenience only. It
opens the Production Manager interface/application. It does NOT automatically
select:

- the newly created source,
- the most recent source,
- any source_id,
- any previous processing target.

**Reasoning:** source creation and source processing are separate workflows.
The user may create sources days or weeks before processing them. Examples:

- create multiple podcast episodes, then process them later,
- revisit an older source with different settings,
- reprocess existing data after model changes,
- run analysis on existing collections.

The system must not infer processing intent from creation order. The
Production Manager source selection is an explicit user decision.

Architecture remains unchanged:

```
Source Builder
    ↓
Canonical Source File
    ↓
Production Manager
    ↓
Pipeline
```

The Production Manager source selection remains an explicit user decision.

### Responsibility boundary

The convenience actions never cross the Source Builder responsibility
boundary. The Source Builder still:

- collects metadata,
- collects pasted source text,
- creates canonical source files,
- saves into `Sources\`.

The Source Builder still does NOT:

- execute pipeline stages,
- inspect artifacts,
- manage jobs,
- duplicate Production Manager functions.
