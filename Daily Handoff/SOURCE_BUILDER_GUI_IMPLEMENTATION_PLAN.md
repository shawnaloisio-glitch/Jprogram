# SOURCE_BUILDER_GUI_IMPLEMENTATION_PLAN

**Japanese Corpus Pipeline — Source Builder GUI V1 Desktop Prototype Implementation Plan**

Date: 2026-08-02 (updated 2026-08-03: Ready State Engine, V1.5 ergonomics)
Status: IMPLEMENTATION PLAN (V1, post-implementation)

This plan moves the Source Builder from design into a functional desktop
prototype. It is a V1 utility prototype, not a final commercial application.

Priorities:
1. Correct workflow behavior.
2. Easy modification during testing.
3. Clear separation from existing architecture.
4. Minimal unnecessary complexity.

Design principle: "utility over finish". The first version is expected to
change after real-world use; favor simple, understandable, and easy to
modify over polished, complex, and commercial-ready.

---

## Objective

```
External text source
        ↓
Source Builder GUI
        ↓
Canonical Source File
        ↓
Production Manager
```

The Source Builder GUI owns:

- collecting metadata,
- collecting pasted source text,
- validating required fields,
- generating canonical filenames,
- creating source files in `Sources\`,
- basic workflow navigation.

The Source Builder GUI does NOT own:

- parsing,
- cleaning,
- OCR,
- AI processing,
- JSONL creation,
- pipeline execution,
- artifact management.

---

## V1 Functional Requirements

### 1. Identity selection

- **Collection:** `collection_id` (dropdown) + `episode` (number).
- **Standalone:** `source_name` (text).
- Rules: mutually exclusive; explicit user choice via radio buttons; only
  the active path's fields are shown.

### 2. Metadata selection

Controlled fields from `Config\`, presented as dropdowns:

- `source_type`
- `origin`
- `collection` (collection_id)

Dropdown-based selection reduces typing errors.

Language is a project-level property, not source metadata; it is not a
dropdown.

### 3. Source entry

A large paste area for raw source text. The GUI must not modify the pasted
text in any way.

### 4. Preview

Show (read-only):

- generated filename,
- save location (canonical `Sources\` path),
- Ready State (workflow state).

### 5. Save Source

- Validate fields.
- Create the canonical source file.
- Confirm success.

### 6. Create Next Source

- Disabled until a successful save.
- Clears source-specific fields.
- Retains stable metadata.

### 7. Convenience actions (after save)

- **Open Source Folder** — opens the folder containing the saved file.
- **Launch Production Manager** — navigation only; must NOT automatically
  select the saved source.

---

## Implementation Discussion

### 1. Desktop GUI technology choice

Options considered, in manager terms:

**Option A — Tkinter (tkinter / ttk), stdlib only**

- Advantages: ships with Python (already confirmed available, Tk 8.6, on
  Python 3.14); zero dependencies; simple to modify; trivial to run on this
  machine; adequate for forms, dropdowns, text areas, and buttons; no install
  step for a prototype.
- Disadvantages: basic widget styling; limited modern look; no built-in rich
  layout beyond ttk; less suitable for a polished commercial product.
- Long-term impact: fine for V1 utility; the GUI logic is small and can be
  ported later to a richer toolkit without redesigning the workflow.

**Option B — PySide6 / PyQt**

- Advantages: modern, powerful, professional widgets and styling; good for a
  commercial product later.
- Disadvantages: external dependency (not currently installed); heavier
  learning/API surface; more complexity for a small form; longer install and
  larger footprint.
- Long-term impact: the strongest long-term choice if the GUI becomes a real
  product, but overkill for a V1 utility prototype.

**Option C — Web-based (local browser UI, e.g., Flask/FastAPI + HTML)**

- Advantages: flexible layout; could later grow into a real app.
- Disadvantages: introduces a server process, HTTP, and browser launch — much
  more moving parts; unnecessary complexity for a single-user desktop form;
  adds an API layer where none is needed.
- Long-term impact: heavy for the current goal; not recommended for V1.

**Recommendation: Option A — Tkinter/ttk.** It matches "utility over finish":
zero dependencies, easy to modify, and fully sufficient for the required
form, dropdowns, paste area, preview, and buttons. The small GUI logic layer
is isolated so a later move to PySide or a web UI is a re-skin, not a
redesign.

### 2. Project structure

Recommended GUI location, kept clearly separate from the pipeline:

```
C:\Jprogram\Source Builder\
    source_builder.py        # entry point (thin)
    gui.py                   # window/layout/controls (presents Ready State)
    controller.py            # Ready State Engine + validation + save actions
    config_loader.py         # reads Config\ JSON vocabularies
    gui_settings.py          # persistent metadata (source_type/origin)
    quick_presets.py         # quick presets storage/population
    paths.py?                # (no — use existing project paths.py)
```

Notes:

- The GUI does not import or execute any pipeline stage module. It uses the
  existing project `paths.py` for the `Sources\` and `Config\` locations
  (read-only constants), and it may call the Production Manager's public API
  only for the "Launch Production Manager" navigation convenience — or it may
  simply launch the Production Manager as a separate process without passing
  a source.
- Keep the controller (logic) separate from the view (layout) so the workflow
  rules are testable without a window.
- `Config\` and `Sources\` live at the project root, managed by this GUI and
  the future pipeline only.

### 3. Configuration loading

- The GUI reads controlled vocabulary from `C:\Jprogram\Config\`:
  `collections.json`, `source_types.json`, `origins.json`.
- A small `config_loader.py` loads each JSON file into simple lists/dicts and
  populates the dropdowns.
- Loading happens at startup (or on a refresh). Values are plain JSON,
  machine-friendly identifiers (the canonical values).
- Missing/invalid config files are reported with a clear error and the GUI
  starts disabled until config is available.

### 4. Development approach

- **Prototype approach:** build the smallest vertical slice first — identity
  selection, metadata dropdowns, paste area, preview, Save Source, Create Next
  Source — then add the two convenience actions. No speculative features.
- **Testing approach:** keep the controller logic free of GUI code so it can
  be tested deterministically (filename generation, validation, save-path
  resolution, state transitions). The window layer is thin and manual-tested.
- **Migration path if the GUI changes later:** because all workflow rules live
  in the controller (the Ready State Engine) and the GUI is a thin view,
  moving to another toolkit (PySide, web) or reshaping the layout re-uses the
  same controller, config loader, and Ready State Engine. The canonical
  `Sources\` format and the Production Manager API are unchanged.

---

## Design Principle

Optimize for "utility over finish". The first version is expected to change
after real-world use. Favor simple, understandable, and easy to modify over
polished, complex, and commercial-ready.

The implementation follows the Source Builder Design Principles documented in
SOURCE_BUILDER_SPEC.md. The Ready State Engine owns workflow state; the GUI
presents it. Workflow efficiency takes priority over visual polish, and
administrative actions remain visually separated from production workflow.

The application is a **Guided Workflow**: the GUI directs the user toward the
next valid action, the Ready State Engine determines workflow state, the
Workflow Panel communicates workflow state, the GUI prevents incomplete
canonical source creation, and workflow efficiency has priority over visual
polish.

## Boundary

This is an implementation plan. The Source Builder GUI V1 through V1.4
(including the Ready State Engine) has been implemented. This document does
not modify production code, the pipeline, the Production Manager, Source
Intake, schemas, or tests.
