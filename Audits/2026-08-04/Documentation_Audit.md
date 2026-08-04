# Documentation Audit

**Project:** Japanese Corpus Pipeline (C:\Jprogram)
**Date:** 2026-08-04
**Type:** Documentation audit (audit only — no files modified)

This audit inventories every documentation file in the project, classifies it,
and identifies duplication, conflicts, obsolete references, and coverage gaps.
No recommendations are made.

---

# 1. Current Documentation Inventory

## Root-level documents

| # | Filename | Location | Purpose | Status |
|---|---|---|---|---|
| 1 | README.md | C:\Jprogram\ | Project overview, purpose, pipeline architecture, project philosophy, pipeline rules, evidence-preservation architecture | Current (partially; architecture narrative still accurate, implementation-status lines outdated) |
| 2 | PROJECT_STATUS.md | C:\Jprogram\ | Milestone-by-milestone status and continuation document for a fresh session | Outdated |
| 3 | JPROGRAM_SESSION_BOOTSTRAP.md | C:\Jprogram\ | Fresh-session orientation; frozen principles; Source Intake status | Outdated |
| 4 | PARSER_OUTPUT_SPEC.md | C:\Jprogram\ | Frozen parser output field specification (contract) | Current |
| 5 | SOURCE_TEMPLATE_SPEC.md | C:\Jprogram\ | Frozen V1.0 source template specification | Current |
| 6 | ANALYZER_ARCHITECTURE.md | C:\Jprogram\ | Frozen Analyzer architecture design (no-code-when-written) | Current (design); status header Outdated ("no code yet") |

## Production Manager documentation

| # | Filename | Location | Purpose | Status |
|---|---|---|---|---|
| 7 | Production Manager\README.md | C:\Jprogram\Production Manager\ | PM purpose, ownership boundaries, state machine, CLI, recovery | Current |
| 8 | Production Manager\GUI_API.md | C:\Jprogram\Production Manager\ | Frozen public API contract for frontends (V1.0) | Current |
| 9 | Production Manager\API_VERSION.md | C:\Jprogram\Production Manager\ | API version declaration (V1.0 frozen) | Current |

## Prompts / Templates / Logs

| # | Filename | Location | Purpose | Status |
|---|---|---|---|---|
| 10 | Prompts\parser_prompt.md | C:\Jprogram\Prompts\ | Frozen DeepSeek parser system prompt | Current |
| 11 | Prompts\corpus_analysis_v1.txt | C:\Jprogram\Prompts\ | Placeholder (0 bytes) | Unknown (empty) |
| 12 | Templates\transcript_template.txt | C:\Jprogram\Templates\ | Frozen source template (podcast_transcript, 15 episodes) | Current |
| 13 | Templates\subtitle_template.txt | C:\Jprogram\Templates\ | Frozen source template (anime_subtitle, 15 episodes) | Current |
| 14 | Logs\README.md | C:\Jprogram\Logs\ | Logs folder purpose and philosophy | Current (folder-listing section Outdated) |

## Daily Handoff documentation

| # | Filename | Location | Purpose | Status |
|---|---|---|---|---|
| 15 | Daily Handoff\GUI_ARCHITECTURE.md | C:\Jprogram\Daily Handoff\ | GUI responsibilities and boundaries design | Reference (partly superseded) |
| 16 | Daily Handoff\SOURCE_METADATA_SPEC.md | C:\Jprogram\Daily Handoff\ | Source Builder metadata config spec (V1 pre-implementation) | Historical / Outdated |
| 17 | Daily Handoff\SOURCE_BUILDER_SPEC.md | C:\Jprogram\Daily Handoff\ | Source Builder V1 design specification | Reference / Outdated |
| 18 | Daily Handoff\SOURCE_BUILDER_GUI_DESIGN.md | C:\Jprogram\Daily Handoff\ | Source Builder GUI layout/behavior design | Reference / Outdated |
| 19 | Daily Handoff\SOURCE_BUILDER_GUI_IMPLEMENTATION_PLAN.md | C:\Jprogram\Daily Handoff\ | Source Builder V1 implementation plan | Reference / Outdated |
| 20 | Daily Handoff\SOURCE_BUILDER_IMPLEMENTATION_SPEC.md | C:\Jprogram\Daily Handoff\ | Source Builder implementation rules | Reference / Outdated |
| 21 | Daily Handoff\HANDOFF_2026-07-31.md | C:\Jprogram\Daily Handoff\ | Daily session handoff (Response Validator milestone) | Historical |
| 22 | Daily Handoff\HANDOFF_2026-08-01_QWEN_BUILDER_REVIEW.md | C:\Jprogram\Daily Handoff\ | Corpus Builder milestone + independent review | Historical |
| 23 | Daily Handoff\HANDOFF_2026-08-02_FLASH_EXPRESSION_POLICY.md | C:\Jprogram\Daily Handoff\ | Flash expression extraction policy decision | Historical |
| 24 | Daily Handoff\distribution of roles.txt | C:\Jprogram\Daily Handoff\ | Empty file (0 bytes) | Unknown (empty) |

## Daily Handoff\V1_FREEZE_2026-08-02 (frozen session set)

| # | Filename | Location | Purpose | Status |
|---|---|---|---|---|
| 25 | 01_PROJECT_STATUS.md | Daily Handoff\V1_FREEZE_2026-08-02\ | V1 freeze status snapshot | Historical (frozen snapshot) |
| 26 | 02_ARCHITECTURE.md | Daily Handoff\V1_FREEZE_2026-08-02\ | Permanent architecture (V1 freeze) | Historical (frozen snapshot) |
| 27 | 03_DECISIONS.md | Daily Handoff\V1_FREEZE_2026-08-02\ | Architectural decisions (V1 freeze) | Historical (frozen snapshot) |
| 28 | 04_OPEN_ISSUES.md | Daily Handoff\V1_FREEZE_2026-08-02\ | Open issues (V1 freeze) | Historical (frozen snapshot) |
| 29 | 05_TOMORROW.md | Daily Handoff\V1_FREEZE_2026-08-02\ | Development plan (2026-08-03) | Historical (frozen snapshot) |
| 30 | 06_WORKFLOW.md | Daily Handoff\V1_FREEZE_2026-08-02\ | Human workflow (V1 freeze) | Historical (frozen snapshot) |
| 31 | 07_COMMAND_REFERENCE.md | Daily Handoff\V1_FREEZE_2026-08-02\ | Command reference (V1 freeze) | Historical (frozen snapshot) |
| 32 | 08_FILE_INDEX.md | Daily Handoff\V1_FREEZE_2026-08-02\ | Important files index (V1 freeze) | Historical (frozen snapshot) |
| 33 | 09_RECOMMENDATIONS.md | Daily Handoff\V1_FREEZE_2026-08-02\ | Recommendations (V1 freeze) | Historical (frozen snapshot) |
| 34 | 10_SESSION_SUMMARY.md | Daily Handoff\V1_FREEZE_2026-08-02\ | OpenCode session summary | Historical (frozen snapshot) |
| 35 | PROJECT_TREE.txt | Daily Handoff\V1_FREEZE_2026-08-02\ | Project tree snapshot (V1 freeze) | Historical (frozen snapshot) |
| 36 | Previous Handoffs\HANDOFF_2026-07-31.md | Daily Handoff\V1_FREEZE_2026-08-02\ | Duplicate of #21 | Historical (duplicate) |
| 37 | Previous Handoffs\HANDOFF_2026-08-01_QWEN_BUILDER_REVIEW.md | Daily Handoff\V1_FREEZE_2026-08-02\ | Duplicate of #22 | Historical (duplicate) |
| 38 | Previous Handoffs\HANDOFF_2026-08-02_FLASH_EXPRESSION_POLICY.md | Daily Handoff\V1_FREEZE_2026-08-02\ | Duplicate of #23 | Historical (duplicate) |
| 39 | Previous Handoffs\distribution of roles.txt | Daily Handoff\V1_FREEZE_2026-08-02\ | Duplicate of #24 (0 bytes) | Historical (duplicate) |
| 40 | Reference Files\ANALYZER_ARCHITECTURE.md | Daily Handoff\V1_FREEZE_2026-08-02\Reference Files\ | Frozen copy of #6 | Reference (frozen duplicate) |
| 41 | Reference Files\JPROGRAM_SESSION_BOOTSTRAP.md | Daily Handoff\V1_FREEZE_2026-08-02\Reference Files\ | Frozen copy of #3 | Reference (frozen duplicate) |
| 42 | Reference Files\PARSER_OUTPUT_SPEC.md | Daily Handoff\V1_FREEZE_2026-08-02\Reference Files\ | Frozen copy of #4 | Reference (frozen duplicate) |
| 43 | Reference Files\parser_prompt.md | Daily Handoff\V1_FREEZE_2026-08-02\Reference Files\ | Frozen copy of #10 | Reference (frozen duplicate) |
| 44 | Reference Files\PROJECT_STATUS.md | Daily Handoff\V1_FREEZE_2026-08-02\Reference Files\ | Frozen copy of #2 | Reference (frozen duplicate) |
| 45 | Reference Files\README.md | Daily Handoff\V1_FREEZE_2026-08-02\Reference Files\ | Frozen copy of #1 | Reference (frozen duplicate) |

Note: `Daily Handoff\V1_FREEZE_2026-08-02\Reference Files\` also contains a full
duplicate copy of the source code (common.py, paths.py, project_config.py,
all Source Intake / Data Processor / Production Manager / Cleaner / Common
`.py` files). These are code duplicates, not documentation, and are listed
only for completeness of the freeze inventory.

---

# 2. Documentation Coverage

Documented project areas:

| Project area | Documented? | Where |
|---|---|---|
| Application Shell (tabs, app.py) | Not documented | — (only via V1 freeze file index mentions) |
| Sources (Source Builder GUI) | Yes (design/spec) | SOURCE_BUILDER_SPEC.md, SOURCE_BUILDER_GUI_DESIGN.md, SOURCE_BUILDER_GUI_IMPLEMENTATION_PLAN.md, SOURCE_BUILDER_IMPLEMENTATION_SPEC.md, SOURCE_METADATA_SPEC.md |
| Source Package | Not documented | — |
| Handoff | Not documented | — |
| Import Material workflow | Not documented | — |
| Recent Sources | Not documented | — |
| Quick Presets / Templates (GUI) | Not documented | — (Templates file format documented in SOURCE_TEMPLATE_SPEC.md) |
| Processing (Processing tab) | Not documented as GUI; pipeline side documented | PM README, GUI_API.md, PROCESSING via PM |
| Analysis (Analysis tab) | Design documented; implemented modules not documented | ANALYZER_ARCHITECTURE.md (design only) |
| Pipeline (clean→jobs→requests→api→corpus) | Yes | README.md, PROJECT_STATUS.md, PM README, GUI_API.md, PARSER_OUTPUT_SPEC.md |
| Cleaner | Partially | README.md, PROJECT_STATUS.md, JPROGRAM_SESSION_BOOTSTRAP.md |
| Job Builder | Partially | PROJECT_STATUS.md, PM README |
| Request Builder | Partially | PROJECT_STATUS.md, PM README |
| DeepSeek Client / Transport | Partially | PROJECT_STATUS.md, PM README |
| Response Validator | Yes | PROJECT_STATUS.md, PARSER_OUTPUT_SPEC.md |
| Corpus Builder | Partially | PROJECT_STATUS.md (older sections), HANDOFF 08-01 |
| Parser prompt | Yes (frozen) | parser_prompt.md |
| Source Intake | Yes | JPROGRAM_SESSION_BOOTSTRAP.md, PROJECT_STATUS.md |
| Production Manager | Yes | PM README, GUI_API.md, API_VERSION.md |
| Configuration (Config\ JSON) | Partially | SOURCE_METADATA_SPEC.md (pre-implementation) |
| Templates | Yes (frozen) | SOURCE_TEMPLATE_SPEC.md |
| Testing | Not documented as a guide | — (tests exist; no test documentation) |
| Packaging / release | Not documented | — |
| Diagnostics | Not documented | — |

---

# 3. Documentation Gaps

Missing documentation (not present anywhere in the project):

- Application Shell (app.py, tab structure, embedding Source Builder).
- Source Package artifact (schema, sidecar layout, fields).
- Handoff process (registry + cleaning-job creation from the GUI).
- Import Material workflow (formats, conversion rules, subtitle reuse).
- Recent Sources feature.
- Quick Presets / Templates GUI feature (the file-format spec exists, the
  GUI presets feature does not).
- Processing window (GUI behavior, selection, batch, retry, analysis, export).
- Analysis window (GUI behavior).
- Implemented Analysis modules (corpus_loader, frequency_analyzer,
  distribution_analyzer, exposure_analyzer, expression_analyzer,
  chunk_analyzer, sentence_metrics, comparison_analyzer, output_writer).
- Implemented Corpus Builder module behavior.
- Implemented DeepSeek Client / request builder / job builder behavior as a
  current-state guide.
- Source Intake coordinator (source_intake.py) current behavior.
- Diagnostics (dump bundle contents, usage).
- Config\ JSON files current controlled vocabulary.
- GUI_settings.json / quick_presets.json runtime files.
- Testing guidance (how to run the regression suite, what it covers).
- Packaging / release / installation instructions.
- Current command reference (the only one, 07_COMMAND_REFERENCE.md, is a
  dated V1 freeze snapshot).

---

# 4. Documentation Consistency

Contradictions and inconsistencies observed:

1. **PROJECT_STATUS.md internally contradicts itself.**
   - Section 10 and Section 24 state the parser prompt "has NOT yet been
     written" / "must not be created yet"; Section 28's status table lists
     "Parser prompt — Complete (frozen)"; Section 34 says parser_prompt.md
     was created and is frozen. Both statements are in the same file.
   - Section 28 lists "Corpus Builder — Not started"; Sections 35–38 and the
     HANDOFF 08-01 describe the Corpus Builder as complete and validated.
   - Section 28 lists "GUI — Future possibility"; Section 25 also says GUI is
     "NOT currently part of the implementation plan"; the app shell and GUI
     now exist and are tested.

2. **JPROGRAM_SESSION_BOOTSTRAP.md vs current state.** States Source Intake
   Phase 3 (coordinator, duplicate_check) is "not implemented" and awaiting
   Phase 3; these files now exist (source_intake.py, duplicate_check.py) and
   Source Intake is complete/tested.

3. **README.md vs current state.** README's pipeline diagram shows "Source
   Intake (utility + artifact writers implemented)" with "Not yet
   implemented: source_intake.py coordinator, duplicate_check.py, cleaner
   execution, pipeline orchestration" and "(planned) UI". All of these now
   exist. README's architecture narrative remains valid; its
   implementation-status lines are stale.

4. **ANALYZER_ARCHITECTURE.md status header** says "no code yet", but the
   Analysis\ modules it specifies now exist and are tested. The design is
   followed; the status label is stale.

5. **GUI_ARCHITECTURE.md vs implemented GUI.** The design describes a
   drag-and-drop, status/browse GUI talking only to the Production Manager.
   The implemented shell is a tabbed application embedding the Source Builder
   and using Processing/Analysis windows. The design no longer matches the
   shipped interface (the Processing tab does use the PM API path via
   processing_tab.py, but the described drag & drop and artifact-browsing GUI
   does not exist).

6. **SOURCE_METADATA_SPEC.md vs cleaned Config.** The spec's example
   source_types (podcast_transcript, subtitle, article, manga_text,
   book_text) and origins (con_teppei_podcast, nhk_news, anime_broadcast,
   user_transcription) no longer match the cleaned Config (source_types:
   podcast_transcript only; origins: user_transcription only).

7. **Logs\README.md folder listing** shows "Cleaner/, Job Builder/,
   Processor/, Merger/, Analysis/" but the actual Logs\ subfolders are
   Analysis, Cleaning, Corpus Builder, DeepSeek Client, Job Builder,
   Job Creation, Merging, Processing, Production Manager, Request Builder,
   Source Intake, Subtitle Cleaner, Transcript Cleaner.

8. **Duplicate documentation.** The same handoff files exist twice:
   Daily Handoff\HANDOFF_2026-07-31.md == Daily Handoff\V1_FREEZE...\
   Previous Handoffs\HANDOFF_2026-07-31.md (same 31,497 bytes), and likewise
   for the 08-01 and 08-02 handoffs and the empty distribution-of-roles file.
   Root README / PROJECT_STATUS / SESSION_BOOTSTRAP / PARSER_OUTPUT_SPEC /
   ANALYZER_ARCHITECTURE / parser_prompt are also duplicated inside
   Reference Files\.

9. **SOURCE_BUILDER_SPEC / GUI_DESIGN reference superseded UI terms.** The
   specs describe "Workflow Panel", "Create Next Source", and an
   "Edit Metadata..." admin group — the current UI uses "Status", "Add
   Another", and the admin group now includes a "Processing" button. The
   design docs were not updated for the terminology changes.

10. **Daily Handoff\SOURCE_BUILDER_SPEC.md status** is labelled
    "post-implementation" while its referenced button/panel names no longer
    match the implemented UI.

11. **Prompts\corpus_analysis_v1.txt (0 bytes)** and
    **Daily Handoff\distribution of roles.txt (0 bytes)** — empty files with
    no content; status unknown, referenced by nothing in the docs.

---

# 5. Overall Assessment

The project has a substantial documentation set centered on the frozen
pipeline contracts (parser prompt, parser output spec, source template spec,
Production Manager API) which are current and internally consistent, plus a
large body of dated design, session-handoff, and V1-freeze material that
documents how the pipeline was built. The documentation does not yet reflect
the post-pipeline application layer: the Source Package, Handoff, Import
Material, Recent Sources, the Source Builder/Processing/Analysis GUI, and the
implemented Analysis modules have no current documentation, and the primary
status/continuation documents (PROJECT_STATUS.md, JPROGRAM_SESSION_BOOTSTRAP.md,
README implementation notes) describe earlier milestones that have since been
completed, with several internal contradictions. The frozen contracts remain
valid; the project-level "current state" documentation is stale.

---

*End of documentation audit.*
