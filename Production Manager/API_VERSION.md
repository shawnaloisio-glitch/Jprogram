# API_VERSION

**Production Manager Public API — Version Declaration**

---

## API Version: 1.0

## Status: Frozen

The Production Manager public API (see GUI_API.md) is frozen at Version 1.0.
The GUI and all future frontends must target API Version 1.0.

## Breaking changes

Not permitted without explicit architectural approval.

A breaking change is any change that:

- removes or renames a public function (`status`, `report`, `dry_run`,
  `run_stage`, `pipeline`);
- removes or renames a guaranteed return field;
- changes the type or meaning of a guaranteed field;
- changes the subprocess ownership model.

Non-breaking additions (new optional fields, new public functions, new
optional parameters with defaults) are permitted but should be recorded in
GUI_API.md.
