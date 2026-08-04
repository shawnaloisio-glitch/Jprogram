# Final Baseline Audit

**Project:** Japanese Corpus Pipeline (C:\Jprogram)
**Date:** 2026-08-04
**Type:** Final internal baseline record before snapshot. Audit only — no files modified.

---

## 1. Current Application State

Verified by launching `app.ApplicationShell` (the production entry point):

| Check | Result |
|---|---|
| App launches (`app.py` shell) | ✅ Launches with `config_error: None` |
| Sources tab | ✅ Present; Source Builder embedded |
| Processing tab | ✅ Present; opens Processing window |
| Analysis tab | ✅ Present; opens Analysis window |
| Empty data state | ✅ Recent Sources empty; Processing packages 0; Processing window rows 0; Analysis rows 0; completed corpora 0 |

Tab list confirmed: `['Sources', 'Processing', 'Analysis']`.

**Empty-data behavior:** the application starts cleanly with no user data —
dropdowns populate from the (minimal) Config, all three surfaces open, and no
errors are raised. This confirms a clean-install launch path.

---

## 2. Runtime Data State

All generated/runtime stores are empty:

| Store | Count |
|---|---|
| Sources (collections/standalone) | 0 |
| Source Registry | 0 |
| Cleaning Jobs | 0 |
| Cleaning Results | 0 |
| Cleaned Archive | 0 |
| Processing Results | 0 |
| Diagnostics | 0 |
| Analysis outputs | 0 |
| Corpus JSONL (`Data Processor\jsonl`) | 0 |
| Data Processor jobs | 0 |
| Data Processor requests | 0 |
| Data Processor responses | 0 |
| Data Processor processing | 0 |
| Data Processor completed / failed | 0 |
| Data Processor indexes | 0 |
| Data Processor Corpus Results / Job Results / Request Results | 0 |
| Logs (excluding `Logs\README.md`) | 0 |

Runtime stores are present as empty folders; the application is in a clean,
fresh-install-equivalent state.

---

## 3. Configuration State

| File | Content | Status |
|---|---|---|
| `Config\collections.json` | `{"collections": []}` | ✅ Clean (empty) |
| `Config\source_types.json` | `[{"source_type_id": "podcast_transcript", ...}]` | ✅ Clean (required default) |
| `Config\origins.json` | `[{"origin_id": "user_transcription", ...}]` | ✅ Clean (generic default) |

**Confirmed:** the configuration is at the intended clean baseline — empty
collections, single pipeline-backed source type, single generic origin. No
development leftover values remain in the Config JSON files.

**Note (pre-existing, not part of this audit's scope to change):** the runtime
user-preference files `Source Builder\gui_settings.json` (holds
`origin: "con_teppei_podcast"`) and `Source Builder\quick_presets.json` (holds
a preset referencing `teppei_beginner` / `con_teppei_podcast`) still contain
stale references to removed vocabulary. The application safely ignores these
(out-of-vocabulary values are not applied), so they do not break the baseline,
but they are recorded as a known cosmetic/cleanup item.

---

## 4. Documentation State

Active documentation present:

| Doc | Present | Notes |
|---|---|---|
| `README.md` | ✅ | Status sections updated (Source Intake complete; shell added) |
| `PROJECT_STATUS.md` | ✅ | Current-state section + status table updated |
| `JPROGRAM_SESSION_BOOTSTRAP.md` | ✅ | Updated as current handover |
| `ARCHITECTURE_CURRENT.md` | ✅ | New — current architecture |
| `SOURCE_PACKAGE_HANDOFF.md` | ✅ | New — package/handoff workflow |

Audit records present in `Audits\2026-08-04\`: `Documentation_Audit.md`,
`Project_Audit.md`, `Documentation_Reconciliation.md` (this file adds
`Final_Baseline_Audit.md`).

**Stale status claims in active docs:** the only remaining "stale" matches are
in `PROJECT_STATUS.md` historical sections (e.g. Section 10 "parser prompt has
NOT yet been written"), which are annotated with a 2026-08-04 note clarifying
they are historical statements. No active status claims are stale.

**Frozen contracts unchanged:** verified last-modified timestamps —
`Prompts\parser_prompt.md` (08-02), `PARSER_OUTPUT_SPEC.md` (08-01),
`SOURCE_TEMPLATE_SPEC.md` (08-02), `Production Manager\GUI_API.md` (08-02),
`API_VERSION.md` (08-02). None were modified by the documentation update.

---

## 5. Testing State

| Metric | Value |
|---|---|
| Total tests | **722** across all suites |
| Passing | **717** |
| Failing | **5** |

Suite breakdown (all passing unless noted):

- Source Builder + shell: 269 passing / 274 total (5 known failures below)
- Data Processor (proper suites): 95 / 95
- Subtitle Importer: 16 / 16
- Subtitle Cleaner: 15 / 15
- Transcript Cleaner: 17 / 17
- Common: 26 / 26
- Integration: 10 / 10
- Templates: 8 / 8
- Production Manager: 77 / 77
- Analysis: 78 / 78
- Source Intake: 106 / 106

**Known failures (5) — intentional/documented:**
- `test_source_builder_quick_presets.py` — 1 failure:
  `default_source_type_for_collection resolves via config` (queries removed
  collection `teppei_beginner` in the live Config).
- `test_source_builder_gui_presets.py` — 4 failures: preset-population tests
  whose fixtures reference removed values (`teppei_beginner`,
  `podcast_transcript`-preset `con_teppei_podcast`, `article`, `nhk_news`); the
  file reads the live Config (no sandbox redirect).

**Classification:** these 5 failures are **documented and intentional** — they
are test-fixture dependencies on the previously-removed development metadata,
not code defects. They were flagged in the metadata cleanup task and the
Project Audit. No new failures were introduced in this baseline pass.

---

## 6. Known Remaining Risks

| Risk | Status / Notes |
|---|---|
| **API key handling** | `api_key.txt` exists at project root containing a real `sk-...` key (35 chars). Must be removed/rotated and loading moved to a non-committed mechanism before any external review or distribution. |
| **Real data validation** | Not yet completed. The full pipeline (import → save → process → corpus → analysis) has not been validated with real source material end-to-end; automated tests mock the PM subprocess/API path. |
| **Packaging** | Not completed. No installer/launcher packaging exists; application runs via `python app.py`. |
| **External QC review (Qwen)** | Pending. All audits and documentation updates are prepared for this review. |
| **Stale runtime user files** | `gui_settings.json` / `quick_presets.json` contain removed-vocab references (harmless at runtime, cosmetic cleanup item). |
| **5 test failures** | Documented fixture issues tied to removed Config values; to be resolved via test sandboxing/neutral fixtures. |

---

## 7. Snapshot Recommendation

**Is this a valid backup baseline?**
**YES.**

**Explanation:** the project is at a well-defined, reproducible state:

- The application launches cleanly with all three surfaces (Sources /
  Processing / Analysis) functional.
- Runtime data is fully reset; the application is in a clean-install-equivalent
  state with empty stores and the intended minimal configuration.
- Documentation now reflects the current implementation (active docs updated,
  frozen contracts verified unchanged, audit trail in place).
- The regression suite is 717/722 passing; the 5 failures are documented,
  intentional fixture issues related to the completed metadata cleanup — they
  do not indicate application defects and are already recorded.

This is a valid internal baseline for a project snapshot **before** the
external Qwen review. The known risks (API key, real-data validation,
packaging) are tracked and are appropriate pre-review/pre-release items rather
than blockers to capturing this snapshot.

---

*End of final baseline audit.* STOPPED.
