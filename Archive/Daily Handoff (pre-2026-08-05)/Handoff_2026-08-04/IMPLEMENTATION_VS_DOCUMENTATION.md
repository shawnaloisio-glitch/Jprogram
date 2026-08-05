# IMPLEMENTATION_VS_DOCUMENTATION

**Project:** Japanese Corpus Pipeline (C:\Jprogram)
**Date:** 2026-08-04
**Type:** Read-only comparison of the repository against the documented state.

**Compared against:**
- `Daily Handoff\PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- Files in `Daily Handoff\Handoff_2026-08-04\` (PROJECT_CONTEXT.md, PROJECT_STATUS.md, Session_Handoff_Audit.md)

**Classification legend:**
- **MATCH** — implementation agrees with documentation.
- **DRIFT** — documentation describes an older or different state.
- **UNDOCUMENTED** — code exists but documentation does not describe it.
- **MISSING** — documentation expects something that is not present.

---

## A. Architecture and Pipeline

| Finding | Class | Evidence |
|---|---|---|
| Pipeline: Clean Source → Parser → **Parser Output Canonicalizer** → Response Validator → Corpus Builder → JSONL → Analysis | **MATCH** | `corpus_builder.py:797` calls `canonicalize(parser_data, job_text)` before `validate_parser_output` (:805). PROJECT_CONTEXT §4 documents this flow. |
| Corpus Builder no longer owns canonicalization (re-exports for compat) | **MATCH** | `corpus_builder.py:66-79` imports/re-exports from `parser_normalizer`; PROCESS journal confirms move. |
| Validator validates canonical records with punctuation-normalized partition check | **MATCH** | `response_validator.py:120-139, 249-268`. |
| Clean source is the sentence authority | **MATCH** | `parser_normalizer.py:287-304` derives canonical texts from cleaned source. |
| Application shell: 3 tabs (Sources / Processing / Analysis) | **MATCH** | `app.py` verified in baseline audit; tab list confirmed `['Sources','Processing','Analysis']`. |
| PM pipeline stages `clean → jobs → requests → api → corpus` | **MATCH** | PM tests materialize exactly these 5 stages. |
| Frozen contracts unchanged since freeze (parser_prompt, PARSER_OUTPUT_SPEC, SOURCE_TEMPLATE_SPEC, PM API) | **MATCH** (code unchanged) | Timestamps unchanged; V1_FREEZE copies byte-identical for validator/prompt (archaeology audit). |

---

## B. Frozen Contract Narratives (documentation-side drift)

| Finding | Class | Evidence |
|---|---|---|
| `PARSER_OUTPUT_SPEC.md` §3 (line 33): "Word units never include the spaces or punctuation that separate them" — **no mention of a canonicalization stage before validation** | **DRIFT** | The validator now accepts surfaces omitting punctuation because canonicalization precedes validation; the spec still describes the pre-canonicalizer contract. Code changed; spec not updated. |
| `PARSER_OUTPUT_SPEC.md` §14 validation contract — validator checks raw parser text/partition (fatal) | **DRIFT** | Validator now runs against **canonical** records with punctuation-normalized partition. Spec §14 not updated. |
| `Prompts\parser_prompt.md` (lines 52, 142): punctuation-in-sentence-text / "word units never include punctuation" | **DRIFT** | Same conflict: prompt still assumes parser-only path; canonicalizer is the downstream owner now. Prompt file itself is unchanged (frozen). |
| `README.md` (line 473): "the Corpus Builder ... normalizes records, recomputes character spans and chunk text" | **DRIFT** | That responsibility moved to `parser_normalizer.py`; README narrative not updated. |
| `PROJECT_STATUS.md` (line 1080): "Validator vs builder: ... the Corpus Builder deterministically normalizes and recomputes" | **DRIFT** | Now owned by the canonicalizer stage; status doc not updated. |
| `PROJECT_STATUS.md` historical sections (parser prompt "not written", Corpus Builder "not started", GUI "future") | **DRIFT** | Annotated as historical (2026-08-04 note) at lines 12-15; current-state section is accurate. |

---

## C. Implementation State Claims

| Finding | Class | Evidence |
|---|---|---|
| Regression "740 tests — 735 passing / 5 failing" (PROJECT_CONTEXT, Session_Handoff_Audit) | **MATCH** | Verified this session by running all test files (see CURRENT_TEST_STATE.md). |
| Baseline docs state "722 tests / 717 passing / 5 failing" (Final_Baseline_Audit) | **DRIFT** (superseded) | Older number predates the canonicalizer test additions (test_parser_normalizer +12, corpus_builder +1). Both are correct for their point in time. |
| Runtime data reset to clean state (Final_Baseline_Audit: Sources 0, Registry 0, etc.) | **DRIFT** (superseded) | Baseline was clean; real-data testing since then left: 6 sources (5 collection ep + 1 standalone), 1 registry entry, 1 cleaning job/result, 1 job/request/processing result, 1 failed corpus result, 2 diagnostics bundles. No JSONL corpus yet. |
| Config clean (collections empty, source_types=[podcast_transcript], origins=[user_transcription]) | **DRIFT** (superseded) | Current Config: collections = [cijapanese, ci_transcript]; source_types = [podcast_transcript, cij_transcript]; origins = [user_transcription, subtitle]. |
| `anime_subtitle` exists in pipeline profiles but not in Config (Project_Audit §3/§7) | **MATCH** | `project_config.py:187` has anime_subtitle profile; `Config\source_types.json` does not include it. |

---

## D. Undocumented Code / State

| Finding | Class | Evidence |
|---|---|---|
| `parser_normalizer.py` module | **UNDOCUMENTED** (in frozen docs) | Implemented and tested; PARSER_OUTPUT_SPEC/parser_prompt/README/PROJECT_STATUS narratives not yet reconciled (see B). |
| `Daily Handoff\PROJECT_CONTEXT.md` document itself | **UNDOCUMENTED** (new) | Created this session as continuity doc; not referenced by older docs. |
| `Config\collections.json.bak`, `origins.json.bak`, `source_types.json.bak` | **UNDOCUMENTED** | Backup JSON files present in Config; not described in any doc. |
| `Data Processor\jobs\<sid>\`, `requests\<sid>\`, `responses\<sid>\` per-source subfolders | **UNDOCUMENTED** (in current docs) | ARCHITECTURE_CURRENT lists jobs/requests/responses but not the per-source subfolder layout. |
| `Prompts\corpus_analysis_v1.txt` (0 bytes), `Daily Handoff\distribution of roles.txt` (0 bytes) | **UNDOCUMENTED** | Empty placeholders, referenced by nothing. |
| `Sources\collections\ci_transcript\` real test data + standalone "I like apples" | **UNDOCUMENTED** (in current docs) | Real-data test residue not described by any current-state doc. |

---

## E. Missing Items

| Finding | Class | Evidence |
|---|---|---|
| A corpus JSONL produced by the fixed pipeline | **MISSING** (no doc claims otherwise; runtime empty) | `Data Processor\jsonl\` empty; Corpus Result for the one real source is `success: false`. The docs correctly list "real-data validation" as remaining. |
| `anime_subtitle` selectable as a GUI source type | **MISSING** vs pipeline support | Profile exists in `project_config.py`; absent from `Config\source_types.json`; Project_Audit documents this gap (M1/future item). |
| Any automated test exercising the real end-to-end pipeline | **MISSING** (documented) | Documented as remaining work in Project_Audit §5 ("Weakly tested areas"); not present. |
| `Source Intake\source_intake.py` coordinator invoked by the GUI path | **MISSING** (documented) | Documented in multiple audits: coordinator is complete but not invoked; Handoff uses the writers directly. |

---

## F. Summary

| Classification | Count |
|---|---|
| MATCH | 6 |
| DRIFT | 10 |
| UNDOCUMENTED | 6 |
| MISSING | 4 |

**Key conclusion:** the code and the current-state architecture documents
(PROJECT_CONTEXT, ARCHITECTURE_CURRENT, Session_Handoff_Audit) agree on the
implemented pipeline including the Parser Output Canonicalizer. The drift is
concentrated in (1) the frozen-contract narratives (PARSER_OUTPUT_SPEC,
parser_prompt, README, PROJECT_STATUS §32/§39) which still describe the
pre-canonicalizer architecture, and (2) older baseline documents superseded by
the real-data testing that followed (Config and runtime data are no longer at
the clean baseline).

---

*End of implementation vs documentation comparison.* STOPPED.
