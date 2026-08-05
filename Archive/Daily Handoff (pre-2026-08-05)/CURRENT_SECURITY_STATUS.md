# CURRENT_SECURITY_STATUS

**Japanese Corpus Pipeline (C:\Jprogram)**
Current security status — authoritative for the published repository state.
Dated: 2026-08-05 (after workspace separation and the GitHub publication baseline).

---

## Current Security Status

- **No API keys are stored in the repository.**
- **`api_key.txt` was removed before public publication.** It is not committed to
  the baseline and does not exist in the repository.
- **Previous API key exposure concerns are historical migration issues only.**
  Historical audit documents (`Audits\2026-08-04\*`, dated handoffs such as
  `Daily Handoff\Handoff_2026-08-04\*`) describe the state *before* the migration.
  They are evidence records, not a description of the current repository.
- **The active API key is supplied through the `DEEPSEEK_API_KEY` environment
  variable.** Key resolution order is: environment variable first, then a file
  fallback (`paths.API_KEY`, retained only for backward compatibility). No key
  value is committed.
- **Repository scans before publication found no credential values.** No `sk-`
  key tokens, no `.env` files, and no personal absolute paths were present in
  the committed content (verified during the G1/G4 pre-publication security
  scans).
- **Runtime/customer data remains outside the repository workspace**
  (`C:\Jprogram Workspace\`, configurable via the `JPROGRAM_WORKSPACE`
  environment variable). Sources, registry, cleaning artifacts, processing
  results, logs, analysis outputs, diagnostics, and user preferences are not
  part of the repository.

---

## How to Read Security History

Historical audit documents may describe previous security problems (for example,
an `api_key.txt` present in an older working state). **Do not treat historical
findings as current state.** Current security status is defined by this document
and by the latest migration security audit (the pre-publication staged-content
scans).

---

*End of current security status.* STOPPED.
