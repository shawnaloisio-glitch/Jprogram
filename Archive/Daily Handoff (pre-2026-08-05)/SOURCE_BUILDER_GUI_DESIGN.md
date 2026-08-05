# SOURCE_BUILDER_GUI_DESIGN

**Japanese Corpus Pipeline — Source Builder V1 GUI Design**

Date: 2026-08-02 (updated 2026-08-03: Ready State, Workflow Panel)
Status: DESIGN SPECIFICATION (V1, post-implementation)

> **Current-UI terminology note (2026-08-04):** in the implemented UI,
> "Create Next Source" is **"Add Another"**, the "Workflow Panel" is titled
> **"Status"**, and the "Quick Presets" panel is titled **"Templates"**.

This document describes the Source Builder GUI's screen layout, controls,
workflow, validation behavior, and user interaction model.

---

## Screen Layout

The main screen is a single vertical form. Top to bottom:

```
┌──────────────────────────────────────────────────────────┐
│  SOURCE BUILDER  —  new source item                       │
├──────────────────────────────────────────────────────────┤
│  1. Identity type                                         │
│     ( ) Collection     ( ) Standalone                    │
├──────────────────────────────────────────────────────────┤
│  2. Metadata (only the active identity path is shown)     │
│     Collection mode:                                      │
│       collection_id  [dropdown: teppei_beginner ▾]        │
│       episode        [  0051  ]                           │
│       source_type    [dropdown: podcast_transcript ▾]     │
│       origin         [dropdown: con_teppei_podcast ▾]     │
│     Standalone mode:                                      │
│       source_name    [ nhk_weather_article_august        ]│
│       source_type    [dropdown: article ▾]                │
│       origin         [dropdown: nhk_news ▾]               │
├──────────────────────────────────────────────────────────┤
│  3. Save location (auto, read-only)                       │
│     Sources\collections\teppei_beginner\                  │
│     teppei_beginner_ep0051.txt                            │
│     [warning: file already exists]  (when applicable)     │
├──────────────────────────────────────────────────────────┤
│  4. Raw text                                              │
│     ┌────────────────────────────────────────────────┐   │
│     │  (paste raw text here; review before saving)   │   │
│     └────────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────────┤
│  5. Action row (workflow left, administrative right;      │
│     aligned with the form grid)                           │
│     [ Save Source ] [ Create Next <label> ]              │
│                               [ Open Folder ]            │
│                                      [ Edit Metadata ]   │
├──────────────────────────────────────────────────────────┤
│  6. Workflow Panel (primary feedback; visually dominant)  │
│     Workflow:                                             │
│     Waiting for source text. / Ready to Save. /           │
│     Saved successfully.                                   │
│                                                           │
│     Filename:                                             │
│     teppei_beginner_ep0051.txt                            │
│     Save Location:                                        │
│     Sources\collections\teppei_beginner\                  │
│         teppei_beginner_ep0051.txt                        │
└──────────────────────────────────────────────────────────┘
```

Language is not part of the form: it is a project-level property, not source
metadata.

### V1.5 ergonomics

- Workflow buttons (**Save Source**, **Create Next <label>**) are solid
  filled, white text, and approximately 50% larger (height, internal
  padding, horizontal padding) for comfortable repeated clicking.
- Button colour reflects the Ready State:
  - disabled / neutral: medium grey background, white text,
  - `READY`: solid green background, white text,
  - `SAVED` (Save): solid blue background, white text.
- Dropdowns are fixed width (~38 average characters), identical across all
  dropdowns, and do **not** span the window. Their height/padding is
  increased approximately 50% to match the larger buttons.
- The **Workflow Panel** is the visually dominant element. It draws the
  user's attention after any action. The workflow message is the primary
  information; filename and save location are secondary reference
  information below it.

---

## Controls

- **Identity type radio buttons** — `Collection` / `Standalone`. Exactly one
  is selected; this is the first control the user interacts with.
- **Dropdowns** for all controlled metadata: `collection_id`, `source_type`,
  `origin`. Values come from the config files; the user never free-types
  controlled values. Language is NOT a dropdown: it is a project-level
  property, not source metadata.
- **Episode number** — a numeric field, shown only in Collection mode.
- **source_name** — a free-text identifier field, shown only in Standalone
  mode.
- **Save location / Filename** — read-only, auto-generated from the active
  identity and the canonical `Sources\` storage model. The user never edits
  the path or filename.
- **Raw text** — a large paste area for the source content.
- **Save source file** — commits the current item to `Sources\`. The button
  is enabled only when the Ready State is `READY`; it is never clickable
  otherwise. Solid filled; green when enabled, medium grey when disabled,
  blue after a save (see V1.5 ergonomics).
- **Create Next Source** — returns to the creation screen, retaining stable
  metadata and clearing source-specific fields. It is enabled only when the
  Ready State is `SAVED`. Its label is dynamic ("Create Next Transcript",
  "Create Next Subtitle", ...) from the current Source Type. Solid filled,
  green when enabled.
- **Open Source Folder** — opens the folder containing the saved source
  file. Read-only; does not modify files. Administrative; visually separated
  at the far right.
- **Launch Production Manager** — opens the Production Manager
  interface. No pipeline logic; never runs stages directly.
- **Edit Metadata** — administrative action, visually separated from the
  production workflow (see SOURCE_BUILDER_SPEC.md — Architectural
  Responsibilities). The metadata editor offers **Add** and **Edit** only;
  there is no Delete action in the normal editor. Identifier fields are
  immutable after creation and shown read-only with a lock indicator:
  - Collection ID is labelled "Collection ID (folder name)" with helper text
    explaining it becomes the folder name and filename prefix and cannot be
    changed later.
  - Source Type ID / Origin ID carry helper text explaining they are internal
    identifiers (used by presets/validation and source tracking
    respectively).
- **Workflow Panel** — the primary user feedback mechanism; a permanent,
  non-blank, visually dominant status area driven by the Ready State (see
  Ready State Engine below). Shows the workflow message (primary) followed by
  Filename and Save Location (secondary reference information).
- **Quick Presets panel** — right-side one-click population of common source
  configurations. Six slots; each press populates the form once and has no
  further control (not linked state, not live bindings). Labels come from the
  preset display names; empty slots show `Empty Slot`. **Edit Presets...**
  opens the preset editor (see SOURCE_BUILDER_SPEC.md — Quick Presets).

---

## Workflow

Primary workflow:

```
Select metadata
   ↓
Paste raw text
   ↓
Visual inspection
   ↓
Save source file
   ↓
Post-save action
   ↓
Next item
```

The user intentionally reviews pasted text before committing. The design
optimizes for correctness, not speed.

### Detail

1. The user selects the identity type first.
2. The matching metadata controls appear.
3. The user fills metadata (via dropdowns and a number/text field).
4. The filename is generated and shown automatically.
5. The user pastes raw text into the paste area.
6. The user reads the pasted text to confirm it is correct.
7. The user clicks **Save source file**.
8. The file is written to the canonical `Sources\` storage location with the
   generated filename. The save path is automatic:
   - Collection: `Sources\collections\<collection_id>\<collection_id>_epNNNN.txt`
   - Standalone: `Sources\standalone\<source_name>.txt`
   The user never selects a save location.
9. The post-save action area appears (see Post-Save Actions).
10. Choosing **Create Next Source** clears the form (stable settings
    retained) for the next item.

---

## Post-Save Actions

After a successful save, the GUI shows:

```
Source saved:

<generated filename>

Available actions:

[ Open Source Folder ]
[ Launch Production Manager ]
[ Create Next Source ]
```

### Open Source Folder

- **Purpose:** allow quick verification of the newly created source location.
- **Behavior:** opens the folder containing the saved source file. It does
  not modify files and does not bypass Source Builder ownership rules.

### Launch Production Manager

- **Purpose:** allow transition from source creation to processing.
- **Behavior:** opens the Production Manager interface/application. It does
  not run stages directly, contains no pipeline logic, does not inspect
  artifacts, and does not bypass the Production Manager API.
- **Navigation only:** this button is a navigation convenience. It does NOT
  automatically select the newly created source, the most recent source, any
  source_id, or any previous processing target. The Production Manager opens
  with no source pre-selected; source selection is always an explicit user
  decision there.

Architecture remains:

```
Source Builder
    ↓
Canonical Source File
    ↓
Production Manager
    ↓
Pipeline
```

The Production Manager source selection is an explicit user decision and is
never inferred from creation order.

### Create Next Source

- **Purpose:** support the repeated workflow:

```
Paste episode
   ↓
Save
   ↓
Create next episode
```

- **Behavior:** returns the user to the source creation screen.
  - Retains stable metadata: `collection_id`, `source_type`, `origin`.
  - Resets source-specific fields: episode number (unless a sequential
    increment is later added), pasted text, and validation state.
- **State-dependent availability:** the **Create Next Source** button is
  disabled by default and becomes enabled only after the current source has
  been successfully saved (see Create Next Source State Rule).

---

## Ready State Engine

The Ready State Engine is a controller-owned finite state machine. The GUI
never decides workflow state; it asks the controller and derives all visual
behaviour from the returned Ready State. The four canonical states are
`INCOMPLETE`, `READY`, `SAVED`, and `ERROR`.

All GUI behaviour derives from these states:

- button enablement (Save enabled only in `READY`; Create Next only in
  `SAVED`),
- button colour,
- Workflow Panel messages,
- Create Next availability.

See SOURCE_BUILDER_SPEC.md — Ready State Engine for the state definitions,
transitions, and blocking reasons.

---

## Create Next Source State Rule

The **Create Next Source** button is state-dependent, driven by the Ready
State Engine.

### Default state

- `[ Create Next Source ]` is **disabled** by default (Ready State
  `INCOMPLETE`).

### Enable condition

- It becomes **enabled** only after the current source has been successfully
  saved (Ready State `SAVED`).

### Reasoning

There is no useful workflow reason to move away from an incomplete source
form. If required information is missing:

- the user should correct the current form,
- no new source should be created,
- no source state should be discarded.

### Validation flow

```
New Source (INCOMPLETE)
    ↓
User enters metadata/text
    ↓
Ready State: READY
    ↓
Click Save Source
    ↓
Save succeeds → Ready State: SAVED

If not READY:
- Save stays disabled
- Workflow Panel shows the first blocking reason
- Create Next remains disabled

If READY and save succeeds:
- create canonical source file
- Ready State → SAVED
- enable Create Next Source
```

### Button rules

Before successful save:

```
[ Save Source ]     [ Create Next Source disabled ]
```

After successful save (SAVED):

```
[ Save Source disabled ]     [ Create Next Source ]
```

---

## Validation Behavior

Validation is owned by the controller and reflected in the Ready State. The
GUI never decides validity; it reports the engine's first blocking reason in
the Workflow Panel.

- **Identity completeness:** the item cannot be `READY` unless the active
  identity is complete.
  - Collection mode: `collection_id` selected AND `episode` is a valid
    non-negative integer.
  - Standalone mode: `source_name` is a non-empty identifier.
- **Controlled vocabulary:** `collection_id`, `source_type`, `origin` must
  come from the config dropdowns. Invalid/unknown values are not accepted.
  Language is not a source field.
- **Filename collision:** if the generated filename already exists at its
  canonical `Sources\` location, the Ready State is `INCOMPLETE` with
  "Filename already exists." as the blocking reason. Save remains disabled
  (prevent rather than correct afterwards).
- **Empty raw text:** an empty source text keeps the Ready State at
  `INCOMPLETE` ("Waiting for source text."). Save is disabled until text is
  present.
- **Filename safety:** generated filenames are checked to be within the
  canonical `Sources\` location and to match the machine-friendly pattern
  (lowercase, underscores, `.txt`).

---

## User Interaction Model

- **Guided and error-averse:** the GUI steers the user through controlled
  choices (radio + dropdowns) to prevent typos.
- **Guided workflow application:** the interface always indicates the current
  Ready State and the single next valid action. Buttons are never enabled
  without a valid reason; Save is only enabled when the controller reports
  `READY`.
- **Workflow Panel feedback:** routine workflow information is shown in the
  Workflow Panel; modal dialogs are reserved for unexpected runtime failures
  only.
- **Stable settings are remembered:** last origin and last source_type
  persist across sessions; the collection is not persisted (see persistent
  metadata rules).
- **Review-before-commit:** the paste area is displayed prominently and the
  workflow pauses at inspection; there is no auto-save.
- **One item at a time:** the form always represents exactly one source item;
  there is no multi-item editing view in V1.
- **Workflow efficiency over polish:** buttons that belong to the production
  workflow are grouped; administrative actions (Open Folder, Edit Metadata)
  are visually separated.

---

## Canonical Storage and Production Assumption

The finalized production storage model is used by the GUI's save action:

```
C:\Jprogram\Sources\
    collections\
        <collection_id>\
            <collection_id>_epNNNN.txt

    standalone\
        <source_name>.txt
```

- Collection identity saves to `Sources\collections\<collection_id>\`.
- Standalone identity saves to `Sources\standalone\`.
- The save path is always derived automatically from the active identity;
  the user never selects a location.

Metadata dropdown values come from the `C:\Jprogram\Config\` files
(`collections.json`, `source_types.json`, `origins.json`). Machine-friendly
names are the canonical values. Language is a project-level property and is
not part of the source metadata.

Development and testing will eventually be completed. The production
workflow begins from a clean empty project structure. Existing development
datasets are migrated separately (assigned metadata, canonical filenames,
placed into `Sources\`, validated through Source Intake) and are not the
canonical production state.

---

## Boundaries

The GUI does not clean, parse, OCR, call APIs, create JSONL, or manage
pipeline stages. It saves canonical source files only.
