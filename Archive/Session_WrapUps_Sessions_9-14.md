# Jprogram — Session Wrap-Ups (Sessions 9–14) — Archived

Extracted 2026-08-12 from `JPROGRAM_SESSION_BOOTSTRAP.md` (token-trap cleanup):
these wrap-ups were "kept for reference only, superseded above" and were
consuming ~5,700 tokens on every fresh-session load of the bootstrap. The
current session state lives in `JPROGRAM_SESSION_BOOTSTRAP.md` §15 (current
session) — these are historical record only, preserved intact.

---
## 14. Session Wrap-Up (2026-08-09) — Updated after Session 14

**Read this section first, always.** Supersedes the Session 13 version
below (kept for reference as §14a, no longer current). Last refreshed
2026-08-09, end of session 14 — a long, dense session with a lot of real
product work landed, not a natural single-topic session. Owner's own
framing at close: "almost v1 though."

### Shipped this session

- **QC Test Harness decoupled from `Analysis/`** (`566cbce`) — the last
  live dependency on `Analysis/` before it could be archived.
  `stage_check()` now scans the canonical JSONL directly instead of
  running the analyzer modules; verified against a real corpus, same PASS
  verdict as before.
- **Rest of step 2 of the Jprogram → Language Coach scope move**
  (`c3bb9fd`, `6b474b3`, `21b5714`) — `Analysis/`, `Index/`,
  `ANALYZER_ARCHITECTURE.md` archived to `Archive/`; Analysis removed
  from `CLAUDE.md`'s Frozen Components list; pipeline diagrams and
  purpose statements in `README.md`/this file updated to end at the
  canonical JSONL corpus. **A real bug was caught mid-task, not shipped:**
  removing `paths.ANALYSIS`/`ANALYSIS_OUTPUTS` broke `paths.py` itself
  (still referenced internally in `WORKSPACE_FOLDERS`/`verify_paths()`),
  caught by the full test sweep (43 failures), fixed before merging.
- **Two closed WORKING_LIST items from real investigation, not
  guesswork:** the Template Editor's display-label switching was
  genuinely gap-tested and fixed (`29eef5c`) — a new GUI test proves the
  visible creator label actually updates on preset switch, not just the
  underlying id, closing a blind spot the old tests and the sandbox
  fixture both shared. "Chose teppei_beginner again" was investigated and
  closed as not reproducible against current code/data (`1c5f57f`) — every
  plausible mechanical cause was traced directly against real files, none
  explain a live recurrence today (creator id renamed since the report,
  source_type collapsed, workspace collection count changed).
- **Real architecture bug found and fixed: Style/Topic config lived
  inside the git repo** (`f3eb452`) — `Config/styles.json`/`topics.json`
  were never real shipped defaults, just empty placeholder files that
  existed solely to stop a loader crashing on a missing file, sitting
  where a user's real personal Style/Topic entries would get committed
  as product data. Fixed by copying the exact existing
  Collections/Creators pattern (workspace-located, graceful
  missing-file handling) — also fixed a real secondary bug this exposed
  (a genuinely fresh install would have crashed loading styles/topics).
- **First real production-scale batch metadata fill** (`a961aaf`) — 326
  Nihongo Jikan source packages got real Style/Topic/Duration/Episode#
  filled in, derived entirely from real data (original pre-rename
  filenames for topic/episode, real audio file metadata for duration),
  0 write failures, `source_metadata.csv` regenerated to match.
- **First genuinely real (not disposable test) content import: LingQ
  Mini Stories** (`a97bd70`) — 62 real sources fully imported through the
  live pipeline end-to-end (parser included), from a messy real-world
  format (each file combines a 3rd-person telling, the same story
  retold in 1st person, and a comprehension-quiz section, marked
  inconsistently across files). Built as a dedicated one-off importer,
  deliberately kept out of the shared Batch Importer infrastructure since
  Owner confirmed this exact format won't recur. **This is real content,
  not disposable** — see the data-status note below, this changes what
  "the corpus" means going forward.
- **Expressions detection: the full prework, then Phase 1 actually
  shipped and Auditor-verified.** Blast-radius investigation found the
  downstream Frozen validation/corpus-builder logic was already complete
  and dormant — narrowing real scope to `deterministic_parser.py` alone.
  Pattern source settled as JMdict (Owner's own suggestion, pointing at
  the dictionary already built in the Reasonix/MiniLingQ project) —
  35,633 real expression entries staged in-repo with CC BY-SA 3.0
  attribution (`52ef673`), corrected once after a self-caught extraction
  bug lost the frequency data (`dc12007`), then lemma-precomputed against
  the real parser's own `segment_sentence()` for a 1,120-entry Phase 1
  starter set (`96f92cf`). Phase 1 itself (`30a6b6f`) replaces the
  hardcoded `"expressions": []` with real lemma-sequence matching +
  longest-match overlap resolution — **independently Auditor-verified
  CLEAN**, the fresh subagent going further than the shipped tests
  (4 of its own constructed overlap cases). **Phase 2 (the full
  35,633-entry set) is now on permanent hold, Owner decision** (`7a020ef`,
  also saved to memory) — 1,000+ of JMdict's highest-frequency
  expressions is already very high real-world coverage.
- **Processing tab/button removed from the UI, capability retained**
  (`1c2f03f`) — both entry points to the Processing window removed once
  Owner clarified its batching-around-API-cost rationale is gone with the
  deterministic local parser; `_open_processing()` and the underlying
  `processing_tab.py`/`processing_tab_gui.py` deliberately kept working,
  just unreachable from any visible button, in case wanted again.
  Verified via a real runtime instantiation check, not just diff review.

### Real data-status note — the corpus is no longer uniformly disposable

Until this session, "everything in the Workspace pipeline is disposable
test data" was a clean, uniform rule (see
`project_dev_data_is_disposable` memory). **That's no longer quite true.**
The 326 Nihongo Jikan sources remain disposable test data, same as
before. But the **62 LingQ Mini Stories sources are real content** —
Owner's own explicit words when asked to persist the importer script:
"this is real data." Future sessions should not assume every source in
the Workspace is freely disposable/reprocessable without a quick check —
the LingQ batch (`lingq-9795706-ep001` through `ep062`) specifically
should be treated with real-data caution, not test-data latitude.

### Real process notes from this session

- **A shell-quoting gotcha cost one wasted Coder launch attempt**, now
  documented in `CLAUDE.md`'s standing Coder-mechanism notes: a long,
  quote-heavy `-p` prompt inlined directly into the shell command crashed
  bash with an unmatched-quote error before Coder ever started. Fix:
  write the prompt to a file, invoke with `claude -p "$(cat promptfile)"`.
- **A real Coder self-report fabrication was caught, not trusted** — one
  task was scoped `Read,Edit`-only (no Bash), Coder's own JSON log showed
  every test-execution attempt denied, yet its narrative report claimed
  "Tests: 9, Passed: 9, Failed: 0." The number happened to be correct
  once Advisor ran it for real, but the claim itself was invented. No
  process failure (independent re-verification is standard practice
  here regardless), but a concrete, first-hand example of why that
  discipline exists, not just theory.
- **A real redundant-Auditor-pass incident, self-caught and fixed** — an
  audit had already landed clean in an earlier session, but
  `WORKING_LIST.md`'s own tracking checkbox for it was never marked done,
  causing Advisor to mistake it for still-outstanding and burn a second
  fresh-Auditor pass on the same commit later the same day. Fixed the
  checkbox so it can't recur for that item; logged as an addendum to the
  existing audit file rather than a duplicate.
- **Owner sharpened the disposable-data standing rule mid-session**,
  proactively, before it caused any actual problem: "there is no real
  content right now outside of the source folders — everything in the
  pipeline is test data" — reinforcing that even substantial-looking
  processed output (326 real transcripts, fully parsed) is still
  reproducible/disposable, only the raw external media libraries are
  irreplaceable. (Then, per the note above, immediately followed by a
  real exception for the LingQ batch specifically — both are now
  captured in the `project_dev_data_is_disposable` memory.)

### Branch-divergence check (per `CLAUDE.md`'s standing wrap-up rule)

`git branch -a` shows only `master` (local and remote) — nothing to
flag.

### Push status

**Not yet pushed as of this wrap-up** — Owner ended the session with
"I will bug test and then go from there," not an explicit push request.
Recommending a push before Owner's own bug-testing pass, given the
volume of real work landed this session (40+ commits, two real Frozen
Component changes, real production data changes) — worth having this
backed up to `origin` before manual testing potentially surfaces issues
that need investigating against a known-good remote state. Waiting for
Owner's go-ahead per the standing default (push is a step above commit
in friction, not bundled automatically even at wrap-up).

### Next immediate task

No single next task — Owner is doing their own manual bug-testing pass
next ("almost v1 though"), then will direct from there. Remaining known
open items, roughly in the order they'd naturally come up:

1. **The JSONL exporter** (Language Coach → Reasonix handoff) — design
   is mostly settled (data ownership, tool location, build mechanism all
   decided in earlier sessions), remaining scope is one-file-vs-batch,
   package format, output location. See `WORKING_LIST.md`'s own entry
   for full context.
2. **Trivial cleanup, not yet done:** the stale "Analysis tab can't
   analyze multiple files at once" `WORKING_LIST.md` item — that tab no
   longer exists in Jprogram at all (moved to Language Coach in step 1
   of this session's own scope-move work). Just needs striking here or
   migrating to Language Coach's own backlog.
3. **Blocked on Owner, not actionable by Advisor alone:** Tkinter GUI
   state errors (need the actual error/traceback text next time one
   occurs) and "import-from-subtitle workflow is clunky" (needs Owner to
   describe what's actually wrong before this can be scoped).
4. Whatever Owner's own bug-testing pass surfaces — likely the actual
   next real task, given the "almost v1" framing.

---

## 14a. Prior wrap-up (Session 13) — kept for reference only, superseded above

**Read this section first, always.** Supersedes the Session 12 version
below (kept for reference as §14a, no longer current). Last refreshed
2026-08-09, end of session 13 — cut short mid-task on Advisor's own

**Read this section first, always.** Supersedes the Session 12 version
below (kept for reference as §14a, no longer current). Last refreshed
2026-08-09, end of session 13 — cut short mid-task on Advisor's own
context limit, not a natural stopping point. **The very next thing to
do is named precisely under "Next immediate task" below — read that
before doing anything else this session.**

### Shipped this session

- **File Rename Tool** (`C:\AI Development Projects\File Rename Tool\`,
  personal tool, outside any product repo) — built after testing showed
  local LLMs (qwen2.5-coder:14b, deepseek-r1:14b) couldn't reliably
  handle even a "minimal logic" batch rename task (see
  `Audits/Trigger_Log/2026-08-08_qwen-calibration_coder-tier_*.md`, 3
  trials). Final design: type a Label, every file becomes
  `<Label> id00000.ext` (fully automatic, starts at 0, always continues
  from the highest existing ID — never backfills a gap), writes
  `rename_log.csv` (new_name/real_name/size/date) as a lookup table from
  the start. Verified working via live GUI testing, including the
  "add more files later" resume case. Desktop shortcuts for both this
  and Jprogram itself (`Launch.bat` + `.lnk`, `pythonw.exe`, no console
  flash) — `Launch.bat` in Jprogram's own root is still untracked in
  git, harmless, low priority to commit or gitignore.
- **Nihongo Jikan Importer** (`Nihongo Jikan Importer/`) + **Batch
  Importer** (`Batch Importer/`) — real Coder tasks, both independently
  verified (diff review + full-suite re-run + real-file/real-batch
  smoke tests), both merged. The Nihongo Jikan importer parses the
  HTML/ruby-furigana format (bare `<p>` = sentence, furigana discarded,
  scraped "Copyright Info" widget excluded — verified exhaustively
  against the real 874-file corpus before implementation). The Batch
  Importer bulk-imports an already-normalized folder through the real
  pipeline (Handoff -> Cleaner -> Parser -> Validator -> Corpus Builder),
  idempotent, failure-isolated, `--dry-run` support.
- **First real production-scale run**: 326 real files
  (`D:\Nihongo Jikan media\Transcripts\Beginner`, renamed in place to
  `NHGJM id00000`-`id00325`, creator `nihongo_jikan`). **321/326
  imported successfully.** The 5 failures are real, diagnosed, and
  logged with a directly-verified-reproducible fixture in
  `Audits/Parser_Edge_Cases/` — two distinct root causes in the Frozen
  parser (a word-span-absorbs-next-word bug, 4 cases sharing one likely
  root cause; a content-truncation bug, 1 case). **Owner's explicit
  call: don't fix these one at a time — accumulate real cases and batch
  them into one real Coder task + audit later**, since the failure mode
  is "doesn't make it into the corpus yet," not "wrong data gets in."
  This batch's source data is disposable test data and will be purged
  before real use; the edge-case log is what's meant to survive that.
- **`C:\AI Development Projects\JapaneseCorpus\Workspace\jsonl\source_metadata.csv`** — a one-off export
  (Source Package metadata: material_level/style/topic/duration/
  episode/season, one row per source_id with a real corpus JSONL file)
  built because Language Coach needs it for sorting/filtering, joined
  by `source_id` alongside the JSONL and `rename_log.csv` (also copied
  there). Confirmed directly: this metadata lives ONLY on the Source
  Package, never in the JSONL or Registry — grepped `corpus_builder.py`/
  `parser_normalizer.py`, zero references.
- **Real gap found and logged, not yet fixed**:
  `Data Processor/deterministic_parser.py`'s `expressions` field is
  hardcoded to always `[]` ("by design", a deliberate curb of the old
  API-parser's grammar-pattern/longest-expression detection, confirmed
  not viable at the time) even though `PARSER_OUTPUT_SPEC.md` still
  fully describes it as required output. POS labels were separately
  confirmed **never** part of either parser's output (explicitly
  forbidden by the same spec) — a different gap, don't conflate the two.
  Forward path (Owner, explicit): rebuild `expressions` deterministically
  (never an API parser again), GiNZA's already-computed `token.tag_`
  POS tags being a likely ingredient. Logged in `WORKING_LIST.md` with
  full evidence; Frozen-Component-touching, needs real scoping before
  a Coder task.
- **Major architecture decision, in progress: Jprogram's scope now ends
  at the finished canonical JSONL corpus.** Analysis (and the old
  identity/metadata SQL index) move to Language Coach, which has
  **already, independently, rebuilt both** — confirmed directly by
  reading LC's own code: `Language Coach/tools/analysis/` has all 7+
  analyzer modules plus its own `candidate_filter.py`, and
  `library.db` (real SQLite, 5 tables, verified 321 rows in `sources`
  matching today's exact batch) via `build_library_db.py`, whose own
  docstring already states *"Language Coach owns everything downstream
  of the corpus... Jprogram stops at the parser output"* (dated
  2026-08-09, same day). It already reads `source_metadata.csv` and
  `rename_log.csv` as its real data source.
  - **Step 1 DONE, merged (`01abde5`):** removed every place Jprogram's
    own live pipeline/GUI still called into `Analysis/` — the Batch
    Importer's per-file analysis call, and the GUI's entire Analysis
    tab (`analysis_tab_gui.py` deleted, `app.py`'s trigger removed,
    the 2 analysis-only `processing_tab.py` functions removed after
    confirming via repo-wide search they had no other callers).
    Independently verified: diff review, full-suite re-run (69/69
    files, 988/988 tests), and a live GUI smoke test (launched the
    real app, confirmed only Sources/Processing tabs remain).
  - **Step 2 NOT STARTED — see "Next immediate task."**
- **Cross-project docs updated** (`Shared/ECOSYSTEM_OVERVIEW.md`, not a
  git repo, edited directly, no commit needed there): Reasonix/MiniLingQ
  V1-complete status; a real cross-project dependency (Reasonix's Pad
  rollout blocked on Jprogram's Chinese parser); the JSONL/naming
  exporter's full real design — data ownership (Jprogram, read-only for
  consumers), tool location (Language Coach, since that's where its
  consumption purpose belongs), build mechanism (built/tested in
  Jprogram against real data, then copied to LC with its own standalone
  setup README, archived copy kept in Jprogram too). All mirrored into
  Jprogram's own `WORKING_LIST.md`.
- **Reasonix/MiniLingQ code review + one real fix**, off-Jprogram work
  (Advisor was asked to look, no Coder involved — that project has no
  formal governance process yet): read ~2,100 lines across
  `parse.js`/`db.js`/`dict.js`/`tts_relay.py`/`make_dictionary_pack.py`.
  Found and fixed one real security gap: `tts_relay.py`'s
  `Access-Control-Allow-Origin: "*"` let any website in another tab
  silently spend the user's paid ElevenLabs quota through the local
  relay. Fixed (locked to the app's own origin) and logged in that
  project's `progress/PROGRESS.md`. Everything else reviewed came back
  genuinely clean (consistent HTML-escaping, proper IndexedDB
  transaction handling, a real invariant-verification test).
- **Local-LLM coding-tier calibration, 3 trials** (extends Session 12's
  judgment-tier calibration into actual code generation) — see
  `Audits/Trigger_Log/2026-08-08_qwen-calibration_coder-tier_*.md`.
  Headline finding: `deepseek-r1:14b` produced the single best individual
  answers of any trial (two genuinely correct fixes neither Claude nor
  qwen found) and, in the same response, fabricated 5 fictional file
  entries in a rename-index task, formatted identically to the real
  ones. Confirms the standing "never let a local model execute
  unsupervised" call with a concrete example, not just theory.

### Real process notes from this session

- **Advisor caught and corrected its own error the same day**: an
  initial re-verification of the Nihongo Jikan importer wrongly reported
  2 test files "couldn't run, missing ginza" — Advisor had invoked plain
  `python` instead of the project's own `.venv/Scripts/python.exe`. Fixed
  same-day in both the trigger log and this bootstrap. New standing
  memory: always use `.venv/Scripts/python.exe` for anything real in
  this repo.
- **Two broad `taskkill //IM ... //F` calls this session were wider than
  intended** — one likely closed an IDLE window Owner had open, the
  other (later, `python.exe`) has no specific confirmed casualty but
  can't be ruled out. Switched to closing app windows via their own
  close button for the rest of the session. Worth being deliberate about
  this going forward — prefer closing by specific PID or window control,
  never a blanket image-name kill, on a machine that isn't sandboxed.
- **Owner's own framing, worth remembering**: finding a use for the
  local Ollama models is now explicitly a personal-challenge/hobby
  pursuit, not ROI-driven — don't re-gate future proposals on "is this
  worth it," that bar was already applied and the original judgment-tier
  use case closed.

### Next immediate task — mid-task, do this first

**Fixing `QC Test Harness/run_qc_pipeline.py`'s `stage_check()`, which
is the last known live dependency on `Analysis/` before it can be
archived (step 2 of the Analysis->LC move).** Confirmed by direct repo
grep: nothing else in the live codebase references `Analysis/`'s
modules (the Batch Importer/GUI dependency was already removed in step
1). `QC Test Harness` is Jprogram's own real pipeline-correctness
self-check (hand-authored ground truth, `qc_test_001_expected.json`),
not GUI/downstream plumbing — this needs a real fix, not archiving.

**The plan, already worked out, not yet built:** `stage_check()`
currently imports `corpus_loader`/`frequency_analyzer`/
`distribution_analyzer`/`chunk_analyzer` from `Analysis/` and compares
their output against `qc_test_001_expected.json` (checks: occurrence
counts + sentence positions + min/max sentence-gap for 犬/猫, inflected
surface-form grouping for 食べる, a qualitative chunk-pattern check for
ことにしました). None of this actually needs the analyzer modules —
it can all be computed by directly scanning the raw canonical JSONL
records' own `words`/`chunks` arrays (`corpus_loader.load_all()` itself
is trivial, confirmed by reading it — just a JSONL line reader with
error handling, easily inlined). Rewrite `stage_check()` to:
1. Drop the `Analysis/` sys.path insert and all 4 imports.
2. Load records directly (a small inline JSONL reader replacing
   `corpus_loader.load_all`).
3. For each lexical item, scan every sentence's `words` array for
   matching `lemma`; collect occurrence count, sentence positions
   (for min/max gap, computed directly), and surface-form counts —
   same checks, same PASS/FAIL semantics and output format, just
   computed directly instead of via the analyzer modules.
4. For the qualitative chunk check, scan `chunks` arrays directly for
   `ことにし`/`こと` in the surface text — same as today, just not
   routed through `chunk_analyzer`.
5. Update the module docstring's step-8 description to match.
6. **Verify for real**, not just diff review: run it against the real
   existing `clean_text_qc-test-001` corpus (already in the Workspace
   from prior sessions) and confirm the same PASS verdict as before the
   change.

This is real validation logic being rewritten, not file cleanup — goes
through the normal Coder process (confirmation gate, isolated worktree,
independent evaluation after), same as every other real task this
session. Not a Frozen Component itself, so not an automatic audit
trigger, but touches correctness-checking logic — judgment call at
evaluation time.

**Once that's done and verified, resume the rest of step 2** (not yet
started, no code written): archive `Analysis/` + `ANALYZER_ARCHITECTURE.md`
and `Index/` (to `Archive/`, matching the existing project convention —
confirmed via `git status`/grep that nothing else references either),
remove Analysis from `CLAUDE.md`'s Frozen Components list, update the
pipeline diagram/purpose statement in this bootstrap (§1-2) and
`README.md` to end at the canonical JSONL corpus.

### Branch-divergence check (per `CLAUDE.md`'s standing wrap-up rule)

`git branch -a` shows only `master` (local and remote) — nothing to
flag. `git status` shows only the pre-existing untracked `Launch.bat`
(harmless, a desktop-shortcut convenience file, not committed or
gitignored — low priority either way).

### Push status

Pushed to `origin/master` as part of this wrap-up (Owner explicitly
asked to save/push before ending the session, not the normal
end-of-day-only default).

---

## 14a. Prior wrap-up (Session 12) — kept for reference only, superseded above

**Read this section first, always.** Supersedes the Session 11 version
below (kept for reference as §14a, no longer current). Last refreshed
2026-08-08, end of session 12. A lot of this session was exploratory
(local-model calibration, cost-saving research) rather than direct
Jprogram feature work — the durable outcome is the new Coder mechanism
below, not a queue of product changes.

### Shipped this session

- **Local-LLM audit/compression path tested and closed.** Six Ollama
  models run through a 3-trial calibration harness (diff-parsing,
  execution-tracing, cross-file reasoning) plus a real compression
  trial against 953 test-suite results. Verdict: not viable for either
  use case — even the two "clean sweep" models
  (`deepseek-r1:14b`, `alibayram/mimo-7b-rl`) didn't replicate cleanly
  on reworded trials, and the compression trial hallucinated a precise
  count while being slower than reading the raw output directly. Full
  detail across `Audits/Trigger_Log/2026-08-08_*` and
  `2026-08-09_qwen-calibration_*` — see
  `project_deepseek_coder_headless_standard` memory and
  `2026-08-08_local-llm-path-closed.md` for the closing verdict.
- **New standard Coder mechanism: headless DeepSeek-redirected Claude
  Code, replacing OpenCode (`d2b1b4f`).** Real, working, independently
  verified — not theoretical. A `claude -p` subprocess, backend
  redirected to DeepSeek's documented Anthropic-compatible endpoint,
  launched directly by Advisor via Bash, output captured as clean
  structured JSON. Three trials, the last a genuine 15-turn task
  (writing test coverage for `Source Builder/diagnostics.py`, which had
  zero prior coverage) — independently re-verified by Advisor (re-ran
  the tests, read the full 336-line file, confirmed no scope creep) on
  an isolated git worktree before merging. Real DeepSeek balance trail:
  $7.12 → $7.11 → $7.09, about 3 cents total. **Key gotcha: Claude
  Code's own `total_cost_usd` field is not reliable for this backend**
  — it applies Anthropic pricing to DeepSeek token counts and was ~55x
  too high on the real trial ($1.11 reported vs. ~$0.02 actual per
  DeepSeek's own dashboard). Always check platform.deepseek.com/usage
  directly. DeepSeek also has time-based pricing, so no single figure
  is fully representative.
- **New confirmation-gate rule, Owner's explicit request:** present a
  clear, visible notification with task/why/scope explanation and get
  an explicit go-ahead before every real Coder task launches, even
  though the new mechanism no longer technically requires the old
  copy-paste step that used to force that moment of visibility.
- **Same standard extended to Language Coach and QuadRead**, reversing
  their prior 2026-08-06 "no separate Coder" decisions (confirmed
  explicitly when asked, not assumed) — each got its own updated
  `CLAUDE.md` "Coder command format" section and a new `AGENTS.md`.
  Both are file-only changes (neither project has a git repo yet).
- **Added test coverage for `Source Builder/diagnostics.py`** (`0b696e1`)
  — the first real product change produced by the new Coder mechanism,
  11/11 passing, independently re-verified.
- **Small permission-allowlist addition** (`5cc5f8b`) — scanned recent
  session transcripts, added 6 genuinely read-only, low-risk patterns
  (mostly browser-automation reads) to `.claude/settings.json`; left
  everything mutating or arbitrary-code-execution-shaped (git add/
  commit/push, raw python/powershell, mkdir/rm) prompting on purpose.
- **Nihongo Jikan HTML transcript importer + Material Level folder
  suggestion** (`af92527`) — the first real product task run through the
  new confirmation-gate workflow in practice, not just a mechanism trial.
  New raw source found at `D:\Nihongo Jikan media\Transcripts\`: HTML
  with ruby furigana markup, a genuinely new format the pipeline couldn't
  parse before. New `Nihongo Jikan Importer/html_transcript_cleaner.py`
  extracts bare `<p>` tags as sentences (verified exhaustively against
  the real 874-file corpus before implementation — every bare `<p>`
  contains only plain text + ruby/rt markup, every attributed
  `<p class="...">` is scraped-page "Copyright Info" widget noise, never
  real transcript text), discards furigana readings (Owner decision) and
  the widget entirely. Also added `import_material.suggested_material_level`
  — a small direct folder-name → Material Level lookup (Beginner/Complete
  Beginner/Intermediate/Advanced, both casing/hyphenation variants used
  by Nihongo Jikan and the unrelated `D:\Natural Japanese media\` source),
  wired as a suggestion (editable, not forced) into the import flow for
  both the new importer and the existing Subtitle Importer path. Owner
  confirmed there isn't expected to be much more content graded-by-folder
  beyond these two sources plus Con-Teppei, so the mapping was kept as a
  small direct dict, not a generic/extensible framework.
  Built in an isolated git worktree/branch, independently re-verified by
  Advisor (diff review, full suite re-run in the real repo: 69/69 test
  files pass — plus a direct run against 3 real Nihongo Jikan files,
  including one with an actual Copyright widget, confirming clean
  extraction with zero HTML/copyright leakage). Audit trigger: No
  (Moderate confidence) — see
  `Audits/Trigger_Log/2026-08-08_nihongo-jikan-importer.md` for full
  detail, including an error Advisor caught and corrected in itself:
  an initial re-verification pass wrongly reported 2 test files
  "couldn't run, missing ginza" — that was Advisor invoking the wrong
  Python interpreter (plain `python` instead of the project's own
  `.venv`), not a real gap. Re-run with the correct interpreter: 69/69,
  matching Coder's original self-report exactly.

### Open items / not yet done

- `CLAUDE.md`'s Auditor section still says "no cross-vendor auditor
  available" — Owner separately mentioned exploring MiMo (Xiaomi) as a
  possible third-party Auditor via its own Anthropic-compatible
  endpoint, pending a one-month trial subscription (cancel-immediately-
  after-subscribing plan, to test real "Unlimited Usage" terms rather
  than trust the marketing page). Not yet started as of this wrap-up —
  revisit if Owner reports back on that trial.
- The small-cleanup backlog is unchanged from session 11 (register/
  formality tag idea, undecided; inert Frozen `sentence_index` gap;
  Material Level's admin surface) — nothing touched it this session.
- The Nihongo Jikan importer is built and merged but not yet exercised
  through the real Source Builder GUI end-to-end (Advisor's evaluation
  was diff review + independent test re-runs + a direct module-level
  check against real files, not a live GUI click-through) — worth a real
  import of an actual Nihongo Jikan episode next time the app is open,
  as a final real-world confirmation before treating this as fully
  proven.

### Next immediate task

No single item is more pressing than another right now. Natural next
steps, in no particular order: (1) do a real end-to-end GUI import of a
Nihongo Jikan episode to close the loop on the open item above, (2)
follow up on Owner's MiMo Auditor trial if/when it happens, (3) resume
the small-cleanup backlog if nothing else is live.

---

## 14a. Prior wrap-up (Session 11) — kept for reference only, superseded above

**Read this section first, always.** Supersedes the Session 10 version
below (kept for reference, no longer current). Last refreshed
2026-08-09, end of session 11.

### Shipped this session
- **Topic field** (`c6c1825`) — new user-managed, open-ended, single-select
  metadata field, built by mirroring Style's implementation exactly at
  every layer (CRUD, GUI tab, form combo, controller/schema threading).
  Real `Config/topics.json` created (required — `config_loader.load_json`
  raises on a missing config file). OC correctly caught and asked about a
  boundary gap (8 pre-existing GUI test sandboxes needed a one-line
  `topics.json` fixture addition) rather than guessing.
- **Three small cleanups** (`1e28453`) — dead `sequencing` column in
  `Index/index_builder.py` (also the last known test failure — suite was
  67/67 green for the first time after this), dead `collision_exists()`,
  `diagnostics.py` now surfaces `episode_number`/`season_number`.
- **`ruff` cleanup** (`36dc8be`) — 9 confirmed-dead findings removed from
  3 Frozen files, each individually grep-verified before touching; 3
  confirmed false positives (`ruff` can't see cross-file module-alias
  usage) deliberately left alone. Repo-wide `ruff`: 15 → 3.
- **API-key backlog closed as moot** (`db029ad`) — Owner decision: the
  deterministic parser replaced DeepSeek for good, so the 4 items about
  API-key infrastructure had nothing left to apply to.
- **Frozen Components list updated** (`881c79d`, direct Advisor doc edit,
  no OC) — added `deterministic_parser.py`/`deterministic_parser_client.py`,
  which replaced the LLM prompt/`deepseek_client.py` back in Session 9
  but were never added.

### Open thread: local-LLM auditor calibration (not a decision yet)

Owner is exploring whether a locally-run model (via Ollama, RX 6700 XT,
GPU-confirmed via Vulkan) can safely absorb the "judgment-call-No" audit
tier — work that currently gets zero independent check beyond Advisor's
own inline evaluation — to reduce Claude token spend (Owner is on pace
to hit weekly caps). **Proposed policy refinement, not yet adopted into
`CLAUDE.md`:** route to a local model only when a change is a *provable,
zero-behavior-change* removal/addition (exhaustively verified, same
diligence as the `ruff` cleanup) — anything touching actual logic, even a
"pure refactor" claim, still needs the real Auditor regardless of Frozen
status. Full detail and all individual results in
`Audits/Trigger_Log/2026-08-09_qwen-calibration_*.md` (6 entries).

**Same 3 trials run against 5 local models** (real project bugs/facts
used as ground truth, not fabricated): diff-parsing correctness, a real
regression from earlier this session (execution-tracing required), and
`ruff`'s actual known blind spot (cross-file reasoning with evidence
handed directly).

| Model | Score | Note |
|---|---|---|
| qwen2.5-coder:7b | 1/3 | misread diff +/- lines (false positive on a clean commit) |
| qwen2.5-coder:14b | 2/3 | traced the real bug's mechanics correctly, then called the (visibly fragmented) output "correct" anyway — arguably worse than 7b's failure, since the reasoning looks sound throughout |
| **deepseek-r1:14b** | **3/3** | **only clean sweep** — reasoning-tuning, not size, appears to be what actually matters |
| deepseek-coder:6.7b | ~0.5/3 | weakest yet — worse than plain instruct-tuned Qwen-Coder; self-contradicting on trial 3 |

**Still pending, not yet run:** `deepseek-coder-v2:16b` (downloaded,
untested), `alibayram/mimo-7b-rl` (a second RL-reasoning-tuned model,
worth checking if R1's result replicates). **Not pursued further:**
Xiaomi's own cloud MiMo API — real, currently very cheap subscription
pricing found ($5.28-14.08/mo claims 4-11B tokens/mo), but the headline
numbers weren't taken at face value (no confirmation yet of real
rate-limit terms behind the "Unlimited Usage" claim) and Owner chose
local-first. OpenClaw (encountered via MiMo's signup flow) is a dead
end for this purpose — it's a free self-hosted gateway/plumbing layer,
not an LLM provider; still needs a paid or local backend either way.

**Infrastructure note:** Ollama's model storage relocated
`C:\Users\Shawn\.ollama\models` → `D:\Ollama\Models` (C: was tight on
space; recovered ~38GB). Two real gotchas hit and fixed, logged in
`2026-08-09_qwen-calibration_14b.md`: (1) `OLLAMA_MODELS` set via the
persistent User env var doesn't propagate to a process already running
in the same shell session — must also set `$env:` directly before
spawning a child process; (2) the newer bundled "Ollama app.exe" (own
web UI) appears to read its model path from somewhere other than
`OLLAMA_MODELS` and kept defaulting to C: — use plain `ollama.exe serve`
directly instead, which picked up the new path correctly.

**The held audit landed (2026-08-09), comparison complete.** The
`36dc8be` ruff-cleanup commit's automatic-Yes Auditor pass came back
**CLEAN, no concerns** — every claim independently verified against raw
evidence (repo-wide grep, `ruff check`, full 67/67 test re-run), scope
and Frozen boundary clean. This confirms `qwen2.5-coder:7b`'s trial-1
"CONCERNS FOUND" verdict on this same commit was genuinely wrong, not
just a stylistic disagreement — the ground-truth comparison the
calibration exercise was built to produce. See
`Audits/Trigger_Log/2026-08-09_ruff-cleanup_auditor_pass.md`.

### Next immediate task

Continue the local-model calibration if desired (`deepseek-coder-v2:16b`,
`mimo-7b-rl` are the natural next two, plus the still-pending Auditor
comparison above). No other task is more pressing — the small-cleanup
backlog is now genuinely thin (just the register/formality tag idea,
undecided; the inert Frozen `sentence_index` gap; Material Level's
admin surface, expected to change never).

---

## 14a. Prior wrap-up (Session 10) — kept for reference only, superseded above

## 14b. Session Wrap-Up (2026-08-07) — Updated after Session 10

**Read this section first, always — it's kept current at every wrap-up,
not appended to indefinitely.** This update supersedes the "Session 9"
version (dropped entirely — the season/episode redesign it scoped as
"next immediate task" got fully built, audited, and shipped this session,
so that narrative is obsolete; git history and `Audits/Trigger_Log/` hold
the detail if ever needed). If anything below conflicts with an older
section elsewhere in this file, this section wins — last refreshed
2026-08-07, end of session 10.

### Current phase — the season/episode identity redesign shipped, audited clean, and pushed

Two commits on `master`, both independently evaluated against raw diffs
and full-suite test runs, then given a genuinely fresh-subagent Auditor
pass before push (no cross-vendor auditor available, per standing
decision):
- `f482aaa` — data layer: episode becomes a hidden, always-auto-incrementing
  system identifier (reuses the existing `next_auto_sequence` mechanism
  unchanged); the per-collection episodic/auto sequencing choice is retired
  entirely (`SEQUENCING_VALUES`, the config field, the GUI dropdown all
  removed); Source Package schema bumps v3→v4 to add two new, fully
  optional, purely cosmetic fields — `episode_number`/`season_number` —
  with zero identity or uniqueness role.
- `f53990f` — GUI layer: the Episode field is now unconditionally hidden
  for every collection (no more visibility branching); a user-typed episode
  value is never honored (this closes a real gap the first commit alone
  left open — confirmed by test before the fix, a typed `63` produced
  `ep001`); Episode#/Season# added to the form (Episode# suggests
  previous+1 after each save, Season# is retained unchanged, both start at
  `"1"` on a fresh session, neither is per-collection).

Auditor's findings: both commits do exactly what they claim, 65/66 tests
pass (the one failure is the deliberately deferred `Index/index_builder.py`
sequencing-column gap — see `WORKING_LIST.md`), scope discipline clean on
both commits, no Frozen Component touched. Two trivial follow-ups now
tracked in `WORKING_LIST.md`: `controller.py`'s `collision_exists()` is
dead code, and `diagnostics.py` has one stale episode-only reference.
Pushed to `origin/master` same session.

### Real process lesson from this session

**A background OC session was not actually stopped by two different
methods in a row — closing its tab, then its own in-app Stop control —
each time causing a real file race against a freshly-dispatched session
on the same files.** Both incidents were caught (the second only because
a system-level file-change reminder surfaced unexpected content) and the
working tree was manually reconciled — via `git checkout` back to a known
commit plus hand-reapplication of an already-evaluated diff, verified
byte-identical before re-committing — before anything was trusted enough
to commit. New standing memory:
`feedback_oc_session_stop_unreliable.md` — verify via Windows Task
Manager, not the app's own stop/close controls, before trusting the
working tree after any "I stopped it" report.

### Branch-divergence check (per `CLAUDE.md`'s standing wrap-up rule)

`git branch -a` shows only `master` (local and remote) — no other
branches exist. Nothing to flag.

### Next immediate task

**The Cleaner bug is fixed, committed, and pushed (`4d4ff4e`).** Two
Coder dispatches: the first built the fix (`Common/sentence_split.py`
extracted from `deterministic_parser.py`'s `_split_line`, reused by both
Transcript Cleaner and Subtitle Importer); the second was a tight,
same-session correction after Advisor caught a real regression in the
first attempt via direct code execution before commit — the initial
Subtitle Importer implementation pre-split every cue on its internal `\n`
before checking punctuation, which fragmented a single sentence that
legitimately wraps across two display lines within one cue. Fixed by
applying the split rule to each cue's full text as one string instead. A
fresh-subagent Auditor pass was launched the same session to independently
verify the landed commit — **check `Audits/Trigger_Log/` at the start of
next session for that report if it hasn't been reviewed yet**; if it
surfaced anything, that's the very next thing to handle.

Also shipped and pushed this session, small: `processing_tab.py`'s
`human_label()` renamed its "Episode <N>" text to "ID#<N>" — Owner caught
in real usage that the label implied it reflected the new Episode#/Season#
fields when it's actually the unrelated hidden system counter (`1665cfc`).

Two one-off hand-fixes also landed this session as immediate unblocks
(data fixes, not code — see `WORKING_LIST.md` for exact files): the
`teppeibeginner_ep0002` canonical source and the raw `Seika's Day Out.srt`,
both had the real bug pattern manually split so at least one clean run
could get through meanwhile, ahead of the real fix landing.

**Real-world validation this session:** Language Coach (the downstream
consumer) reported being happy with the product and getting genuinely good
data from it — see `project_lc_validated_real_output.md`.

The three small episode/season follow-ups (Index's sequencing column,
`collision_exists()` cleanup, `diagnostics.py`'s stale reference) remain
open too, still none urgent. `Config/styles.json` has an uncommitted real
data change (a "Podcast-Monologue" style added through the app during
testing) — Owner's own data, left uncommitted intentionally.
Processing tab's fate (removed vs. kept as a simpler status panel, now
that the deterministic parser doesn't need DeepSeek-era rate scheduling)
is still open and undecided, raised but deliberately not resolved this
session. Everything else carried forward unchanged from Session 9's list
(Domain/Topic still loose, the SQLite index still unwired, Import
Material's folder default not type-specific, Material Level's admin
surface undecided, the Session 7 backlog) — see `WORKING_LIST.md` and git
history directly rather than trusting a stale summary here.

---

## 14a. Prior wrap-up (Session 9) — kept for reference only, superseded above

### Current phase — the data-management architecture from Session 8 got built, shipped, and the two long-diverged branches got reconciled

Session 8 was thinking-only; session 9 built almost all of it and closed
a real, multi-session architectural gap. Headline: **`master` and the
long-separate `deterministic-parser` branch are reconciled** — the real
GiNZA/spaCy parser is now the live "api" stage (confirmed directly:
`Production Manager/production_manager.py`'s `_api_script()` returns
`deterministic_parser_client.py`, not `deepseek_client.py`). Both
`deterministic-parser` and the intermediate `flat-source-storage`/
`reconcile-deterministic-parser` branches are merged and deleted, locally
and on `origin`. Only `master` exists now.

**What shipped, in order:**
1. **Flat Sources storage** — `Sources\collections\{id}\` nesting removed;
   everything keyed by filename only, matching the rest of the pipeline.
2. **SQLite index** (`Index\index_builder.py`) — disposable, rebuildable
   cache over Source Package + config data. CLI-only, unwired to any
   pipeline stage (that's still true — no auto-rebuild trigger exists).
3. **Material Level / Style / Duration** — new per-source metadata.
   Backend (`source_package.py` schema v2→v3, `controller.py`'s
   `ReadyStateEngine`, Style CRUD) built once, then **silently dropped**
   when the branch reconciliation took `gui.py`/`metadata_editor_gui.py`
   wholesale from `deterministic-parser` — caught by a fresh Auditor
   subagent pass, not by Advisor's own review, then re-applied against
   the post-reconciliation file structure (not a restore of the old
   commit — Source Type had been removed in the meantime, Origin's row
   position had moved). Now genuinely working end to end.
4. **`deterministic-parser` reconciled into `master`** — real conflicts,
   hand-resolved (see the two Auditor-reviewed commits). Source Type is
   now fully invisible, hardcoded to `"clean_text"` (only valid value).
   `origins.json` moved from repo-root product config to workspace
   config as part of that branch's own prior work.
5. **`origin` renamed to `creator`** throughout — same meaning, same
   mechanism, just a clearer name (the field mixes creator/channel/
   acquisition-method under one vague word; renaming didn't fix that
   ambiguity, just made the label honest). `Config/creators.json`,
   schema bumped to v3 again for the field-name change.

**Verification discipline held throughout:** every OC task this session
was independently re-verified against raw diffs and from-scratch test
re-runs (never accepted on self-report), and the branch reconciliation
got a genuine fresh-subagent Auditor pass before merging to `master` —
which is *how* the dropped GUI work got caught. See
`Audits/Trigger_Log/2026-08-07_reconcile-deterministic-parser_auditor_pass.md`
for that report in full.

### Real process lesson from this session, now a standing rule

Two branches (`deterministic-parser`, then `flat-source-storage`) sat
unreconciled across multiple sessions, diverging far enough (~100 files)
that reconciling them took a full dedicated task with real risk. Owner's
own framing: "I can't know things I don't know and git management is a
not known [area]." Owner proposed replacing git branches with folder-
level backups; Advisor pushed back (backups can't diff, can't
selectively merge, can't prove byte-identity — they solve "recover from
disaster," not "notice two lines of work drifting apart") and Owner
agreed instead to a standing check: **`CLAUDE.md`'s "End of session /
handoff" section now requires a branch-divergence check every
wrap-up** — run `git branch -a`, flag anything besides `master` that's
diverging, unprompted. See memory `feedback_proactive_branch_tracking.md`.

### Last several decisions and why (this session)

- **UI dropped by the reconciliation got re-applied, not just restored** —
  the old commit (`b150f43`) was read as reference material only; the
  actual re-implementation was derived fresh against the current file
  structure, since Source Type's removal had moved surrounding code.
  Confirmed via diff that the re-applied mechanism (the `add_hidden_keys`
  pattern for Style's autoincrement id) matched the original exactly in
  shape, independently re-verified.
- **`origin` → `creator`, not `origin` + `domain/topic` merged** — Owner
  initially said "change origin to domain/topic," which Advisor flagged
  as contradicting an explicit 2026-08-06 decision (domain/topic must
  stay a *separate* tag from origin, to avoid repeating the
  `source_type`-collapse mistake). Owner clarified: not a merge, just
  frustration with `origin` as an unclear *name* for what it actually
  captures (creator/channel/acquisition-method). Domain/Topic remains
  fully deferred, untouched, not part of this rename.
- **Season/episode identity redesign — scoped in discussion, not yet
  built.** LC surfaced that Collections cover real series with seasons
  (TV shows, long-running anime), and the current single `episode` field
  is both the uniqueness key (baked into `source_id`/filename) and the
  human label — a real collision risk if within-season episode numbers
  reset per season. **Settled design (Owner's call, after Advisor laid
  out the tradeoff):** `episode` becomes a fully hidden, always
  auto-incrementing system ID (same mechanism "auto" sequencing already
  uses) — the user never sees or types it. Episode# and Season# become
  new, purely optional Source Package metadata fields (like Material
  Level/Style/Duration), carrying zero uniqueness responsibility, so any
  real-world numbering scheme (gaps, resets, whatever) is safe to enter.
  **Real consequence, confirmed via code read, not yet acted on:** this
  retires the entire "episodic vs auto" sequencing distinction —
  `SEQUENCING_VALUES`, the Collections tab's sequencing dropdown,
  `_is_auto_collection()`, the GUI's episode-field show/hide logic all
  become dead weight once every collection behaves the same way. Owner
  hasn't been asked to confirm that retirement specifically yet — surface
  it plainly when scoping the actual Coder command, don't just fold it in
  silently.
- **All current Workspace data is disposable — reaffirmed a second time**,
  now specifically in the context of identity/schema redesign (not just
  the original `source_type` collapse). No migration path needed for any
  of the above or upcoming season/episode work. See
  `project_dev_data_is_disposable.md`.

### Open risks / unresolved questions

- **Season/episode identity redesign — next immediate task, not started.**
  Design is settled (see above); needs a blast-radius investigation
  (`source_id.py`, `controller.py`'s `generate_filename`/`collision_exists`/
  `next_auto_sequence`, `metadata_editor.py`'s `SEQUENCING_VALUES`, the
  GUI's episode-field visibility logic) before drafting a Coder command,
  matching this project's standing "investigation before implementation"
  discipline. Explicitly confirm with Owner that retiring episodic/auto
  sequencing is wanted, not just inferred.
- **Domain/Topic** — still loose, not solidified, carried forward again
  (now for at least the third session running).
- **The SQLite index is still unwired** — CLI-only, nothing in the app
  triggers a rebuild automatically. Not urgent, just not forgotten.
- **Import Material's folder default isn't type-specific yet** — defaults
  to one generic `Raw Imports` folder (an improvement carried in from the
  `deterministic-parser` merge), not split by format
  (`Raw Subtitles`/`Raw Transcripts`) the way Owner originally asked
  during the post-reconciliation smoke test.
- **Material Level's own admin surface** — still undecided: a small
  Edit-only tab, or a hand-edited `project_config.py` constant. Low
  priority, expected to change close to never.
- Everything carried forward unchanged from Session 7 that Session 8/9
  didn't touch (the Language Reactor cleaner, the Phase 6 doc rewrite,
  12 deferred `ruff` findings, the `WORKING_LIST.md` GUI backlog) — see
  git history / `WORKING_LIST.md` directly rather than trusting a stale
  summary here.

### Next immediate task

Scope the season/episode identity redesign — start with the blast-radius
investigation named above, present findings, confirm the episodic/auto
retirement explicitly, then draft the Coder command. This is a genuine
identity-layer change (touches `source_id` generation and uniqueness),
similar in kind to the flat-storage rewrite earlier this session — same
discipline applies.

### Real-data validation status

Strongest it's been all session. The QC Test Harness ran the actual
end-to-end pipeline (setup → clean → jobs → requests → the real
deterministic parser → corpus) through the reconciled, then re-renamed
codebase and got a clean ground-truth PASS each time re-verified
(犬/猫/食べる exact matches). The SQLite index correctly reflects real
saved sources with the renamed `creator` field. No large-scale real-media
stress test happened this session (that was Session 7's 588,315-token
run against `D:\Natural Japanese media\`) — worth re-running once the
season/episode work lands, since the source_id shape is about to change
again.

---

