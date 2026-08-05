# SOURCE_BUILDER_IMPLEMENTATION_SPEC

**Japanese Corpus Pipeline — Source Builder V1 Implementation Specification**

Date: 2026-08-02 (updated 2026-08-03: Ready State Engine)
Status: DESIGN / IMPLEMENTATION SPECIFICATION (V1, post-implementation)

This document records the implementation-relevant rules for the Source
Builder. It supplements SOURCE_BUILDER_SPEC.md and
SOURCE_BUILDER_GUI_DESIGN.md with concrete behavior rules that the GUI
implementation must follow.

---

## Ready State Engine (implementation rule)

Workflow state is owned by the controller's Ready State Engine, not by the
GUI. The GUI asks the controller for the current Ready State
(`INCOMPLETE` / `READY` / `SAVED` / `ERROR`) and derives all visual behaviour
from it. The GUI never implements workflow decision logic.

- Save is enabled only when the controller reports `READY`.
- Create Next is enabled only when the controller reports `SAVED`.
- The Workflow Panel always shows the engine's message and is never blank.

See SOURCE_BUILDER_SPEC.md — Ready State Engine for the canonical states,
transitions, and blocking reasons.

---

## Create Next Source State Rule

The **Create Next Source** button is state-dependent.

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
- Save remains disabled
- Workflow Panel shows the first blocking reason
- Create Next Source remains disabled

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

## Related Behavior

- **Create Next Source** returns the user to the source creation screen,
  retaining stable metadata (collection_id, source_type, origin) and clearing
  source-specific fields (episode number, pasted text, validation state).
  Selecting it resets the workflow to `INCOMPLETE`.
- The button never creates a source, discards state, or bypasses validation.
- The "Launch Production Manager" button remains a navigation convenience
  only and never auto-selects a source (see SOURCE_BUILDER_SPEC.md).

---

## Boundary

This document is implementation guidance only. It does not modify production
code, the pipeline, the Production Manager, Source Intake, schemas, or tests.
