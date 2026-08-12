# Working List — Resolved Items (archive)

Resolved-item history moved here from `WORKING_LIST.md` on 2026-08-13 (token-bloat de-bloat).
WORKING_LIST.md is the running queue (open items only); this file is history — not loaded every session.

---

## Resolved

- [x] **Section markers (`===== Episode N =====`) — confirmed legacy artifact, no fix needed (2026-08-05).** Originally flagged as an architectural gap (`corpus_builder.py`'s `assign_sections()` never receives real boundaries; `parser_normalizer.py` strips marker lines without extracting their positions), and OC's TASK 2 audit confirmed the fix would have been genuinely contained (5 analyzers already handle real sections correctly, only the Builder side was missing). But Owner clarified the markers themselves only ever existed for an old workflow — pasting ~20 episodes into one big text file for cheaper bulk chatbot lemmatization — that no longer exists under the current one-source-per-file acquisition model (paste directly into Source Maker, hit next; any multi-episode download gets split into individual files before processing). `_is_section_marker_line()` stays as harmless legacy-format tolerance in case an old batch file ever needs reprocessing; no further investment needed. Every source getting `DEFAULT_SECTION_ID = "default"` is correct behavior going forward, not a gap.
- [x] **`project_audit.py` — confirmed legacy, archived.** Was an attempt at functional handover reporting for the old pre-`JPROGRAM_SESSION_BOOTSTRAP.md` process, same category as the already-archived `Daily Handoff/` docs. Moved to `Archive/project_audit.py` (2026-08-05), no other file referenced it (confirmed via grep before moving).

- [x] **Phase 1 detection algorithm — done and Auditor-clean (2026-08-09),
  `30a6b6f`.** `deterministic_parser.py`'s `detect_expressions()` matches
  each sentence's word lemmas against the 1,120-entry Phase 1 dictionary
  via a first-lemma-indexed lookup, then resolves overlaps by accepting
  candidates longest-span-first and rejecting anything that shares a word
  index with an already-accepted span — this is what enforces the
  longest-complete-expression rule now that no LLM prompt exists to do it
  implicitly. `response_validator.py` got one stale-comment fix (no logic
  change) reflecting this. Independently verified twice: once by Advisor
  (diff review, full 59-file suite re-run, real-sentence smoke test
  beyond the fixtures) and once by a genuinely fresh-subagent Auditor
  pass (automatic trigger, two Frozen Components touched) that went
  further still — constructed 4 of its own independent overlap test
  cases beyond what shipped and confirmed the rule holds on all of them.
  Verdict: CLEAN. Full detail in
  `Audits/Trigger_Log/2026-08-09_expressions-phase1-auditor-pass.md`.
  One non-defect implementation detail flagged for awareness: exact
  span-length ties between overlapping candidates resolve to the earlier
  `start_word` — deterministic, but not something the spec explicitly
  mandates.
- [x] **Phase 2 — permanent hold (2026-08-09), Owner decision.** Scaling
  from the 1,120-entry Phase 1 dictionary to the full 35,633-entry set is
  not planned. Owner's explicit reasoning: 1,000+ of JMdict's own
  highest-frequency/most-common-flagged expressions is already a very
  high coverage level for real content — the long tail of the remaining
  ~34,500 entries (no frequency signal at all, `score: 999`) isn't worth
  chasing. Not "revisit later," a settled call — don't propose reopening
  this unprompted, matching how [[project_qwen_code_on_hold]] is handled.

### Metadata entry for batch-imported sources (2026-08-09) — done as a scripted fill, not a UI tool

- [x] **Closed (2026-08-09), `a961aaf`.** Originally scoped as a small
  hand-assignment UI (Style/Topic/Duration/Episode#/Season#, Material
  Level override) for the 326 Batch-Importer-created `nihongo_jikan`
  sources, which left all of those fields unset. During scoping, real
  per-episode data turned out to be recoverable directly from disk (the
  original pre-rename filenames embed show name + episode number;
  matching `.mp3` files in a sibling Audio folder carry real duration
  metadata), so a one-off deterministic script
  (`Batch Metadata Fill/fill_nihongo_jikan_metadata.py`) replaced the
  planned UI entirely — no hand-entry needed for 322 of the 326 fields
  filled. Style is uniform ("Comprehensible Input"); Topic is derived
  per-source (`Let's Play`/`Father and Son`/`Mini-Fantasy Theater`/
  `Various`, Owner-specified grouping rules); Episode# parsed from the
  original title (89 of 326, the recurring-series subset); Duration
  read from real audio file metadata (326/326 matched); Season# and
  Material Level left as-is (no data source for the former; already
  correctly set for the latter). Full detail, including a real
  architecture bug found and fixed along the way (Style/Topic config
  was incorrectly living inside the git repo instead of the Workspace,
  unlike Collections/Creators — see the separate entry below), in
  `Audits/Trigger_Log/2026-08-09_batch-metadata-fill.md` and
  `2026-08-09_style-topic-config-workspace-move.md`.
  - The Batch Importer's hard-fail-on-unmatched-folder behavior for
    Material Level (see Batch Importer's own note below) remains
    open, untouched by this task — revisit separately if it turns out
    to matter for a future real batch.

### Style/Topic config lived inside the git repo instead of the Workspace (2026-08-09)

- [x] **Found and fixed (2026-08-09), `f3eb452`.** Discovered while
  scoping the batch metadata fill task above: `Config/styles.json`/
  `Config/topics.json` lived under `PROJECT_ROOT` (tracked, committed)
  instead of `WORKSPACE_ROOT` like the same category of user-managed
  vocabulary (Collections/Creators) already correctly does — meaning a
  user's real Style/Topic entries would get committed as product data,
  violating the standing "zero user-specific data in product" principle.
  Root cause: the repo's `styles.json`/`topics.json` were never real
  shipped defaults, just empty placeholder files that existed solely to
  stop `load_json()` raising `ConfigError` on a missing file — a gap
  that also meant a genuinely fresh install with no styles.json/
  topics.json yet would crash rather than start with an empty
  vocabulary. Fixed by copying the exact existing Collections/Creators
  pattern (new `paths.STYLES_CONFIG`/`TOPICS_CONFIG` workspace
  constants, graceful missing-file handling, 10 test files updated).
  Full detail in `Audits/Trigger_Log/2026-08-09_style-topic-config-workspace-move.md`.

### New small tool needed: JSONL exporter for the reader (2026-08-09, expanded)

Owner request, not yet scoped or built. Real workflow it needs to serve
(clarified 2026-08-09, same day): Language Coach helps Owner decide what
to read next, but has to *display* human-friendly titles while doing
that — Owner is picking a reading list by title, not by `source_id`.
Once the reading list is finalized, the export/rename step runs, and
packages the renamed JSONL file(s) together with Language Coach's own
report for that content, ready for Owner to import into Reasonix for a
daily lesson. So this isn't just a rename utility — it's the real
Language Coach → Reasonix handoff mechanism (see
`Shared\ECOSYSTEM_OVERVIEW.md`'s "Language Coach → Reasonix" row, which
only documents the grammar-list/known-words half of that handoff today,
not this content-selection-and-packaging half).

Two real naming hops now, not one: `source_id` -> Source Package
`source_name` (e.g. `NHGJM id00056`, already resolvable without touching
`rename_log.csv`) -> `rename_log.csv`'s `real_name` (the true original
title, e.g. `264 - Chatting with My Daughter 娘とおしゃべり.html`). If
Owner wants to see real original titles (not just the rename tool's
short label) both when Language Coach is presenting choices AND in the
final exported filename, the second hop matters too — meaning this tool
(or Language Coach itself, for the display half) needs read access to
`rename_log.csv`, not just the Source Package.

**Data ownership settled (Owner decision, 2026-08-09):** the corpus
JSONL and the naming cross-reference (`rename_log.csv`) are Jprogram
data, full stop — they live here, and this repo is authoritative for
them. Language Coach gets **read-only** access, never write. It reads
these to resolve human-friendly titles for display while helping Owner
pick a reading list; it must never modify the JSONL, the Source
Package/Registry data, or `rename_log.csv`. This also settles that the
naming-resolution logic itself belongs in Jprogram (the data's owner),
not duplicated or forked into Language Coach.

**Tool location settled too (Owner decision, 2026-08-09, same day):**
the export/rename/package tool itself will **live in Language Coach**
— its purpose is consuming media that falls under Language Coach's own
selection/reading-list responsibility, so that's where it belongs
functionally. But **Jprogram develops it**, since this side owns and
understands the data chain (`source_id` -> Source Package -> Source
Registry -> `rename_log.csv`) better than Language Coach does. In
practice: a Jprogram-side build that reads Jprogram data read-only (per
the ownership rule above) and gets delivered into Language Coach's repo
— the read-only boundary holds regardless of who writes the code.
Governance point still applies: this is real logic, built via the Coder
process, not an Advisor-direct script, wherever it ends up living.
Remaining scope to settle before drafting that Coder task: one file vs.
a whole reading-list batch, package format, output location.

**Mechanism settled (Owner decision, 2026-08-09):** build and test it
here, in Jprogram, using the normal worktree/Coder process — it needs
real access to Jprogram's own Workspace data (JSONL, Source
Package/Registry, `rename_log.csv`) to test against, which it already
has naturally from inside this repo. Once verified working, move a copy
into Language Coach's repo (the live, actually-used location) and keep
an archived copy here too (Jprogram's own record of what it built).

**Real technical detail this raises, for whoever drafts the Coder
task:** once moved to Language Coach, the tool is no longer sitting
next to Jprogram's own modules (`paths.py`, `source_package.py`, etc.)
the way every other Jprogram tool assumes via
`PROJECT_ROOT = Path(__file__).resolve().parent.parent`-style relative
resolution. It needs to reference Jprogram's location explicitly
(an absolute path, or something configurable) rather than relying on
being co-located — build it that way from the start rather than
discovering it breaks after the move.

**Also required (Owner, 2026-08-09):** the copy that lands in Language
Coach must ship with its own README covering what a fresh agent working
in Language Coach's context needs to do to actually set it up there —
at minimum: how to point it at Jprogram's location (per the path-config
detail above), what real data it needs read access to and where that
lives, and how to verify it's working before trusting it. A future
Language Coach session won't have this conversation's context, so the
README needs to stand alone.

### Natural Japanese subtitle batch — import selection, metadata decisions, exclusions (2026-08-12)

Source: `D:\Sourced Content\Japanese Import\Natural Japanese media\` — 1,785
subtitle files (1,780 `.vtt` + 5 `.srt`) across `complete-beginner`,
`beginner`, `intermediate`, `advanced`; authoritative catalog is
`master.csv` (1,777 rows, columns Index/Level/SiteID/TitleEN/TitleJP/
Audio/Subtitle/Video/Creator/Teacher/SiteStatus/Notes — the last two are
entirely empty). Status: **planned and metadata-specified; import NOT yet
run** — awaiting Owner's go signal. No files staged, no pipeline run.

**Metadata spec (Owner decisions, 2026-08-12):**
- creator: `natural_japanese` ("Natural Japanese") — entry added to
  `Workspace/Config/creators.json` (2026-08-12)
- source_name: `TitleJP TitleEN` from `master.csv`, NFC-normalized (246 of
  1,785 on-disk names are NFD; `Subtitles/manifest.csv` `basename_nfc`
  documents the canonical names)
- material_level: by folder (`complete-beginner`→1, `beginner`→2,
  `intermediate`→3, `advanced`→4) — matches `master.csv` Level column and
  `import_material.suggested_material_level()`
- style_id: `1` ("Comprehensible Input", already in styles.json)
- topic_id: `null` for all — no topic data exists in any CSV (checked
  master.csv, Backup master, `_catalog_history.json`, all three manifests;
  grep for "topic" = 0 hits); Owner chose null over title-inference
- episode_number / season_number: `null` (Owner decision)
- duration_seconds: `null` at import; fill later from actual audio/video
  files (NHGJM-style metadata pass) — Audio/Video manifests have no
  duration column
- Teacher column (Yuki/Meika/… 23 values): not mapped to any schema field
  (single style covers the batch)

**Import mechanism:** existing `Batch Importer/batch_importer.py`
(`--folder <staged level dir> --creator natural_japanese`, 4 runs, one per
level; `--dry-run` first). Subtitle `.vtt`/`.srt` handling + cleaning
already exists (`import_material.convert_file` → `Subtitle
Importer/cleaner.py`). Staging (copy to a workspace staging folder, NFC
names, source `D:` remains read-only) is what enforces the exclusions
below — batch_importer has no skip-list and is non-recursive.

**Exclusions (Owner decision 2026-08-12: "exclude them and make a note"):**
1. **9 master.csv rows overlapping existing corpus sources** (same video
   already imported as a transcript source; subtitle version would be
   duplicate content):
   - CB0010 `天気 Weather.vtt` ↔ existing `10 - Weather 天気`
   - CB0035 `何がしたい？ What do you want to do_.vtt` ↔ `111 - What Do You Want to Do_`
   - B0062 `暑い日に使うもの Things I use on a hot day.vtt` ↔ `114 - Things I Use on Hot Days`
   - I0005 `ヒヤッとした出来事 Things that scared me.vtt` ↔ `19 - Things That Scared Me`
   - CB0244 `コーヒー Coffee.vtt` ↔ `21 - Coffee`
   - A0003 `2023年上半期Z世代の流行語 Top buzzword among Japanese Gen Z for the first half of 2023.vtt` ↔ `421 - Top Buzzword…`
   - A0016 `Notionを使ったコンテンツ管理 My content calendar in Notion.vtt` ↔ `461 - My Content Calendar in Notion`
   - I0007 `梅雨 Rainy Season.vtt` ↔ `81 - Rainy Season`
   - B0651 `せいか先生のお出かけ Seika's Day Out.vtt` ↔ `Seika's Day Out`
2. **9 duplicate master.csv rows** (same Subtitle filename listed under 2–3
   levels/Indices; keep the first, exclude the rest — for `コーヒー
   Coffee.vtt` both rows are excluded since CB0244 is also an overlap):
   - `日本のクリスマス Christmas in Japan.vtt`: keep CB0117, exclude B0144, I0044
   - `ディズニーランド Disneyland.vtt`: keep CB0326, exclude I0043
   - `日本のハロウィン Halloween in Japan.vtt`: keep B0205, exclude I0037
   - `クリスマスマーケット Christmas Market.vtt`: keep B0226, exclude B0365
   - `引っ越し Moving.vtt`: keep B0440, exclude I0322
   - `日本への帰国 Returning to Japan.vtt`: keep B0534, exclude I0294
   - `せいか先生が韓国で食べたもの What Seika Ate in Korea.vtt`: keep B0565, exclude B0615
   - `コーヒー Coffee.vtt`: exclude both CB0244 (overlap) and B0002 (dup)
3. **7 folder files not referenced by master.csv at all** (never part of
   the import list; noted for completeness): 5 `.srt` files whose titles
   exist as `.vtt` in master (せいか先生のお出かけ, せいか先生のゴールデンウィーク,
   めいか先生の仕事の経歴, プレゼント交換ゲーム ホワイトエレファント, 母からの贈り物) and 2
   duplicate `_`-suffixed `.vtt` (`AI vs 人間…Music_.vtt`, `トムとジェリー…Jolly
   Fish_.vtt`, byte-identical to the non-`_` versions). (Correction
   2026-08-12: an earlier version of this note listed 3 more files —
   「入らないでください」, 「松コースお願いします！」, のだめカンタービレ — as uncataloged; that
   was an NFC/NFD comparison flaw, they ARE in master.csv and were
   imported with the rest.)

Net selection: **1,759 unique subtitle files to import** (1,777 master rows
− 9 overlap rows − 9 duplicate rows; CB0244 counted in the overlap set).

**Import run — DONE 2026-08-12 (01:32–06:01 SEAST), 4 × `batch_importer.py`
runs, one per level, `--creator natural_japanese`.** Result: 1,759 sources
created; **106 failed at the corpus-builder stage** (clean/jobs/parse all
passed); 1,653 JSONL produced. Full failure list with source_id, level,
and error text: `Workspace/natural_japanese_import_failures.csv`. All 106
failures are the corpus builder's exact-reconstruction integrity gate:
`source reconstruction failed at character 0: expected ...'X-TIMESTAMP-MAP=LOCA'...`
— the WebVTT `X-TIMESTAMP-MAP` header line survives cleaning
(`Subtitle Importer/cleaner.py` doesn't strip it) into the parse text; for
these 106 files the parser's round-trip breaks reconstruction. 38 of the
106 report the generic `1 job(s) failed` wrapper, 2 report `2 job(s)
failed`, 66 the explicit reconstruction error. **Not fixed — the cleaner
would need a change (Frozen-adjacent: cleaning logic), and the project is
locked; Owner must authorize any code change.** Re-running the failed
sources' corpus stage (or the pipeline) is possible later once the cleaner
handles the header line; batch idempotency makes re-runs safe.
Post-import metadata still pending: `style_id` came out `null` (the batch
importer has no style argument) — needs the same metadata-fill pass as
NHGJM to set style 1; `duration_seconds` fill from audio/video also still
pending (Owner decision, deferred to after import).

**Cleaner fix — DONE 2026-08-12 (Owner-authorized).** `Subtitle
Importer/cleaner.py` `VttParser` now skips the whole WebVTT header block
(the `WEBVTT` line plus every metadata line — `X-TIMESTAMP-MAP`, `NOTE`,
`STYLE`, custom `X-*` — up to the first blank line, stopping early at a
cue timestamp so a malformed header can't eat the first cue) and skips
in-text `NOTE`/`STYLE` blocks between cues. 8 new unit tests (26/26
Subtitle Importer suite; full repo sweep 66/69 — the 3 failures are
pre-existing: archived Analysis/Index tests + retired deepseek_client,
confirmed identical on the pre-change baseline). Verified on real data:
the re-cleaned source text no longer contains `X-TIMESTAMP-MAP`.

**Test batch — 8 failed files re-imported through the fixed pipeline
(2026-08-12): header problem FIXED, but all 8 still fail at the corpus
stage with a second, independent error.** With the junk header gone,
`parser_normalizer.py`'s exact-reconstruction exposed GiNZA word-surface
mismatches the header was masking: `早口言葉 レベル１` (「３（み）」ですね → parser
surface `みです`), `「入らないでください」` (`くださいです`), `侘び寂び` (`寂びです`),
`カタカナ禁止ゲーム` (`せです`), `ChatGPTに恋愛相談` (`持つです`), `乳幼児マーク`
(`なさいです`), plus 2 files with "canonical sentence count N does not
match record count M" (`AI vs 人間`, `Unpacking EP08`). All in `Data
Processor/parser_normalizer.py` / `deterministic_parser.py` — **Frozen
Components; NOT touched (locked project, needs Owner authorization).**
Whether all 106 share this underlying parser issue (vs. only the header)
is unknown — determining it requires re-processing the remaining 98, not
done pending Owner decision.

**Batch removed — DONE 2026-08-12 (Owner decision: "clear out all the
files we processed that don't have clean data").** The entire Natural
Japanese import was removed from the Workspace: all 1,759 sources (Sources
txt + source.json, Source Registry, Cleaned Archive, Cleaning Jobs/Results,
jobs/, requests/, responses/, Processing/Corpus/Job Results, Request
Results, Logs) and all 1,651 batch JSONL (each carried the repeating
`X-TIMESTAMP-MAP` junk record — a frequency-skew hazard; the 106 failures
had no JSONL at all). Corpus restored exactly to pre-import state: 384
JSONL / 46,421 sentences, zero `X-TIMESTAMP-MAP` anywhere, zero
natural_japanese sources. Kept (records/config, not corpus data):
`natural_japanese_import.log`, `natural_japanese_import_failures.csv`, the
`natural_japanese` entry in `Config/creators.json` (Owner-authorized), and
`Natural Japanese Staging/` (1,759 raw copies; `D:` remains the source of
truth). Re-import path is fully documented above once the parser-layer
question is resolved.

**Data-status note:** this is real user content (like the LingQ batch), not
disposable test data — the `D:` source tree is read-only during import.

### Cleaner bug: two sentences sharing one source line breaks reconstruction (2026-08-07)

Found via a real "Failed" processing run on `con_teppei_beginner_ep002`
("Con-Teppei Beginner — Episode 2"), diagnosed from the app's own
Troubleshooting-data dump. Root cause traced by directly re-running the
real `response_validator.validate_response` (passed clean, 160 sentences,
no errors) and the real `parser_normalizer.verify_source_reconstruction`
(failed at char 1716) against the dumped source/response — not guessed.

**Root cause:** `Transcript Cleaner/clean_transcript.py`'s
`join_transcript_lines()` docstring assumes "each non-blank line is one
utterance (one sentence for the parser)" but never enforces it — it just
blank-line-separates whatever lines the raw input already has. The parser
splits at every sentence-final `。！？` regardless of line breaks. When a
raw line has two sentences on it (`通りません。はい。` in the real source —
plausible for any hand-typed/pasted `clean_text` source, not a fluke),
the parser correctly produces two sentences, but reconstruction inserts a
`\n\n` between them that was never in the actual cleaned source →
mismatch, "1 job(s) failed" in the app.

**Owner-confirmed:** this is a Cleaner bug, not a `parser_normalizer.py`
issue — the Frozen reconstruction gate is behaving correctly by rejecting
the mismatch; the Cleaner should not have produced a false "one line = one
sentence" contract in the first place. `parser_normalizer.py`/
`corpus_builder.py` (Frozen) do not need to change.

**Blast radius checked:** only this 1 line across all 4 currently-cleaned
real/test sources — low current impact, but the gap is structural and can
recur for any hand-typed content.

**Fix mechanism identified, not yet built:** `Data Processor/
deterministic_parser.py` already has a pure, deterministic `_split_line()`
implementing exactly the boundary rule needed (sentence-final punctuation
marks a boundary, stays attached to the preceding sentence). Reusing this
in the Cleaner — rather than writing separate splitting logic that could
drift out of agreement with the parser's actual behavior — closes the gap
permanently instead of patching this one instance.

- [x] **Fixed and committed (2026-08-08), `4d4ff4e`.** Extracted
  `_split_line` into a new shared `Common/sentence_split.py` after
  confirming a second, independent occurrence of the same bug via a real
  Subtitle Importer import (`せいか先生のお出かけ Seika's Day Out.srt`,
  cue #93 — `Subtitle Importer/cleaner.py`'s `clean_text()` had the
  identical cue-per-sentence assumption as the Transcript Cleaner), so two
  real call sites now share one rule instead of risking drift.
  **Caught before commit, via direct code execution, not just review:**
  the first Subtitle Importer implementation pre-split each cue on its
  internal `\n` before checking punctuation, which fragmented a single
  sentence legitimately wrapped across two display lines within one cue
  into a punctuation-less piece plus its completion — a real regression,
  not just the original bug. Fixed in an immediate same-session follow-up
  (`clean_text` now applies `split_line` to each cue's full text as one
  string, never pre-splitting on internal newlines) and re-verified both
  independently and via a fresh-subagent Auditor pass launched the same
  session (see `Audits/Trigger_Log/` once it reports back — launched
  2026-08-08, result not yet in hand as of this note). Full suite: 68
  files, only the pre-existing/deferred `Index/index_builder.py` failure
  below remains. Two one-off hand-fixes from earlier in the session (data,
  not code, not part of this commit): `Sources\teppeibeginner_ep0002.txt`
  (+ Source Registry/Source Package sha256 kept in sync) and the raw
  `Seika's Day Out.srt` (cue #93 split by hand, no registry involved since
  it wasn't registered yet).
- [x] **Fixed directly by Advisor (2026-08-09), doc-only edit, no OC
  needed.** `CLAUDE.md`'s Frozen Components list now includes
  `Data Processor/deterministic_parser.py` under "Parser" and
  `Data Processor/deterministic_parser_client.py` under "Transport"
  alongside the retired `deepseek_client.py` (kept frozen rather than
  removed, in case it's ever revived).

### Episode/season identity redesign — small follow-ups (2026-08-07)

Main redesign landed and audited clean on `master` (`f482aaa`, `f53990f`):
episode is now a hidden, always-auto-incrementing system identifier;
Episode#/Season# are new optional, purely cosmetic metadata fields.

- [x] **All three follow-ups fixed and committed (2026-08-09), `1e28453`
  — no audit triggered (deliberately: none of the three touch a Frozen
  file, and the goal this session was avoiding audit token overhead for
  genuinely low-risk work).** `Index/index_builder.py`'s `collections`
  table no longer reads a `sequencing` column that no longer exists on
  the config side — this was also the last known failing test, so the
  full suite is now 67/67 fully green with zero known failures for the
  first time. `controller.py`'s dead `collision_exists()` deleted along
  with its test. `diagnostics.py`'s identity dump now also surfaces
  `episode_number`/`season_number` alongside the existing hidden
  `episode` field.

### Piece B GUI wiring deferred — structure built first, UI later (2026-08-07)

- [x] **Material Level / Style / Duration: wired into the Source Builder GUI — done and re-verified (2026-08-07), after one real revert in between.** Built once (`b150f43`), silently dropped when the `reconcile-deterministic-parser` merge took `gui.py`/`metadata_editor_gui.py` wholesale from a branch that predated this work (caught by a fresh Auditor pass, not by Advisor's own review — see the git-management lesson in `CLAUDE.md`'s wrap-up section), then re-applied on `master` against the post-reconciliation file structure (Source Type gone, Origin now precedes Episode — not a restore of the old commit, the surrounding code had genuinely moved). Current state: Material Level (mandatory dropdown) and Style (optional dropdown, leading "(none)" entry) on the main capture form via `_wire_label_combo()`; optional numeric Duration field, validated at save; a Styles tab in `metadata_editor_gui.py` (Add/Edit only, no Delete, autoincrement id hidden on Add / locked on Edit via a small `add_hidden_keys` mechanism). Independently verified: 66/66 repo-wide test files re-run, zero failures. Still open, not addressed by any of this: whether Material Level ever gets its own small Edit-only admin surface, or stays a hand-edited `project_config.py` constant — low priority, expected to change close to never.

### Forward-looking note, not scoped yet (2026-08-06)

- [x] **9 of the 12 fixed and committed (2026-08-09), `36dc8be`.** Each removal individually verified via direct grep (zero external callers, zero internal usage) before touching, not just accepted from ruff's output — completed the "not yet checked" verification the original note below called for: `CANONICAL_LINE_SEPARATOR`, `recompute_character_spans`, `recompute_chunk_text`, `_is_section_marker_line` (all 4 confirmed genuinely dead) plus the previously-known-safe bare `import parser_normalizer`, `deepseek_client.py`'s unused `verify_paths` import, `parser_normalizer.py`'s unused `json`/`Path` imports, and a cosmetic double-assignment in `Analysis/tests/test_sentence_metrics.py`. Full suite 67/67 green after. **The original 3 confirmed false positives remain, deliberately, and always will unless their actual callers change:** `canonical_sentence_texts`, `restore_sentence_text`, `_expected_content` in `corpus_builder.py` — ruff flags them but `test_corpus_builder.py` calls them externally via the `cb.X` module alias; removing them would be a real regression, not a cleanup. Repo-wide ruff count: 15 → 3.
  - [x] **Audit trigger: Yes (automatic — Frozen Components touched), landed same day (2026-08-09).** Fresh-subagent Auditor pass came back CLEAN — see `Audits/Trigger_Log/2026-08-09_ruff-cleanup_auditor_pass.md`. This checkbox itself was left stale (never marked done despite the audit landing), which caused a second, redundant fresh-Auditor pass to be run later the same day under the mistaken belief this was still outstanding — see that same trigger-log file's addendum for the redundant run's own (also CLEAN) result. No harm to the commit's correctness, just wasted verification effort from a stale tracking doc.

### Recurring pattern: identity/config coupled to raw file structure instead of the token abstraction

Owner identified (2026-08-05) that this session found two instances of one
recurring architectural pattern — the **third and fourth** known instances
in this project's history (first was pre-git, told by Owner: the "con_teppei"
ghost tag under an older file-structure-coupled registration system).
**Update:** of the two this-session instances, only one turned out to be a
real, current-day issue — see below.

1. **Episode=0 for non-episodic collections** (still open, see below) — would have coupled source_id identity to a non-unique value. Real, current issue.
2. **Section markers** (`===== Episode N =====`) — turned out to be a legacy artifact, not a live gap. See Resolved section: confirmed 2026-08-05 by Owner that these existed only for an old batch-acquisition workflow (paste many episodes into one file for cheaper bulk chatbot processing) that no longer exists under the current one-source-per-file model. No fix needed.

Worth keeping the pattern-recognition lesson regardless — the next time raw file structure/content seems like it should inform identity, check whether it's actually still load-bearing before designing a fix for it.

**Confirmed real-world requirement, not theoretical (2026-08-05):** Owner has actual collections exceeding 1,000 items (e.g. One Piece). Verified directly: `source_id.py`'s `format_sequence(episode, "ep", width=3)` zero-pads to a *minimum* of 3 digits, not a fixed width — Python's format spec doesn't truncate, so episode 1000 produces `ep1000` (4 digits) sitting alongside `ep001`-style 3-digit ones. Confirmed via direct test that this breaks lexicographic sort: `sorted(['ep999','ep1000','ep1050'])` puts `ep1000` and `ep1050` *before* `ep999`. No functional/data-integrity impact currently (grepped — nothing scans for "max episode" to make decisions), but it does affect GUI display ordering (`processing_tab.py`'s label-string sort, already flagged by OC's audit as buggy even at the 1-vs-2-digit boundary) — this makes it materially worse at real collection scale. Any redesign of the sequence-slot mechanism must handle widths beyond 3 digits correctly, not just avoid episode=0.

- [x] **Closed as moot (2026-08-09), Owner decision.** The deterministic GiNZA/spaCy parser permanently replaced the DeepSeek API path — it was slow and expensive, and Owner confirmed there is no plan to ever revive it. No live system needs an API key going forward, so a fresh key-structure design has nothing to design for.
- [x] **QC harness real API test, second full pass with a permanent key — confirmed PASS (2026-08-05).** Extended troubleshooting session getting a valid `DEEPSEEK_API_KEY` recognized ended up being caused by two separate issues, both resolved: (1) an early `setx "..."` paste that included literal quote characters in the value, and (2) a much larger one — Advisor's own Bash tool session held a stale, cached copy of the environment variable from early in the conversation and never picked up any of Owner's later, correctly-made changes (via `setx` or the Environment Variables GUI), causing several rounds of misdiagnosed "invalid key" failures that were actually just Advisor reading old cached state. Root-caused by reading the value directly from the persistent store (`powershell.exe -Command "[System.Environment]::GetEnvironmentVariable(...)"`) instead of the shell's own environment, which immediately revealed the mismatch. Fix logged in `CLAUDE.md`'s standing sandbox-caution section so this doesn't repeat. Final result: "Jprogram Key" was valid the whole time; full pipeline re-ran end-to-end and passed every ground-truth check again.
- [x] **Closed as moot (2026-08-09), Owner decision — same reason as above.** The `DEEPSEEK_API_KEY` variable this collision was about belongs to the retired transport path; with no live system reading it, the collision has nothing left to affect.
- [x] **Closed as moot (2026-08-09), Owner decision — same reason as above.** No provider needs a pasted key anymore, so there's nothing for this utility to manage.
- [x] **Text/file-based key storage is now legacy — both remnants cleaned up (2026-08-06, TASK 14 + direct Advisor edit).**
  1. `paths.py`'s `API_KEY = PROJECT_ROOT / "api_key.txt"` constant and `deepseek_client.py`'s `load_api_key()` fallback removed via a scoped OC command (Frozen Component); a real bug the removal exposed (`run()`'s stale `except (FileNotFoundError, ValueError)` no longer matching the new `EnvironmentError`) was found by OC itself, confirmed via a fresh-subagent audit, and fixed in a tight follow-up. See `Audits/Trigger_Log/2026-08-06_task14-api-key-fallback-removal.md`.
  2. The plaintext stale key entry in `.claude/settings.local.json` removed directly (Advisor's own tool config, not a product file, not tracked in git).
- [x] **Closed as moot (2026-08-09), Owner decision.** This was specifically about testing an LLM-based transport (DeepSeek or Claude) as an alternative parser backend. The deterministic GiNZA/spaCy parser replaced that whole approach for good — faster, cheaper, no API dependency — so there's no remaining reason to stand up a second LLM transport to compare against.

- [x] **Hash verification is computed but never enforced anywhere downstream — fixed and verified (TASK 8, 2026-08-05).** Both `Subtitle Cleaner/clean_subtitles.py` and `Transcript Cleaner/clean_transcript.py` (confirmed both had the identical gap, not just Subtitle Cleaner) now re-hash `raw_path` at cleaner entry and fail closed against the Source Registry's recorded `sha256`. `Data Processor/job builder.py`'s `cleaning_result_errors()` now re-hashes the cleaned artifact against the Cleaning Result's `output_hash`. Both reuse the existing `Source Intake/hashing.py` utility; no schema changes. Mid-task, OC found a 4th test file (`Integration/tests/test_intake_cleaner_boundary.py`, outside the original scope — an Advisor investigation gap, not an OC error) regressed and correctly stopped to ask before fixing it; Owner authorized the minimal fixture patch. See `Audits/OC_Reliability_Log.md` TASK 8 for full detail.
  - Confirmed NOT a gap: the SRT/Subtitle Importer is intentionally pre-intake; the official chain of custody starts at Source Builder's raw-text ingestion, not at whatever tool produced that text (by design, to allow future manga-OCR/audio-TTS importers without touching the tracked pipeline).
  - Addendum, still not fixed, deliberately out of scope: `deepseek_client.py` has the same asymmetry (no hash computed/stored for saved response files). Lower severity — `response_validator.py` + `parser_normalizer.py`'s exact source-reconstruction gate already do strong content-level verification downstream, which would likely catch corruption anyway even without a hash. `deepseek_client.py` is also a Frozen Component, so any future fix here would auto-trigger an audit.

### Import Material dialog offers 3 non-functional formats — confirmed real gap (2026-08-05)

- [x] **Removed Podcast Transcript/Ebook/OCR from the Import Material format picker; renamed "Plain Text" → "Clean Text" — done and verified (TASK 11, 2026-08-05).** Owner chose removal over disable ("no use showing non-existent items"); they can be re-added if real per-format conversion logic is ever built. `import_material.py` now exposes only `FORMAT_SUBTITLE` + `FORMAT_CLEAN_TEXT` (value `"clean_text"`, label "Clean Text"); `gui.py`'s Import dialog default moved to Subtitle; the radio loop auto-shrank to two, confirmed by a hardened test that asserts exactly 2 radios with labels "Subtitle File"/"Clean Text". See `Audits/OC_Reliability_Log.md` TASK 11. Note: `Audits/2026-08-04/Project_Audit.md` still lists the old five-format set — a historical audit record, deliberately left as-is.

### source_type collapsed to a single "clean_text" category — done (2026-08-06, TASK 16-18)

- [x] **Collapsed `podcast_transcript`/`anime_subtitle` to a single `clean_text` source_type, id renamed (not just relabeled), across config, backend, every test fixture, and the GUI.** The original blocking caveat — the "Load File" button's raw-`.txt` bypass path — was resolved by Owner confirming it's the same accepted user-responsibility model manual paste always had, not a distinct safety gap; the real subtitle-specific cleaning happens earlier, at Import Material's Subtitle File step (`Subtitle Importer/cleaner.py`, a separate, independent implementation), before source_type routing ever matters. That confirmed `Subtitle Cleaner/clean_subtitles.py` (the old `anime_subtitle` route) was a fully dead remnant from the pre-"birth certificate" design, not a live safety net — deleted entirely (TASK 16). Sequenced as 3 Coder commands: config/backend collapse + `Subtitle Cleaner/` deletion (TASK 16), every downstream reference and ~40 test fixture files renamed, including a real production bug found and fixed in `source_intake.py` and a genuine GUI test hang root-caused and fixed (TASK 17), then the main-form dropdown and Metadata Editor's Source Types tab removed as dead UI, converted to a static display driven by the real Config vocabulary rather than hardcoded (TASK 18). All three independently verified clean; full suite green (63/63) after the final command. See `Audits/Trigger_Log/2026-08-06_task16-*.md` through `task18-*.md` for full detail.

