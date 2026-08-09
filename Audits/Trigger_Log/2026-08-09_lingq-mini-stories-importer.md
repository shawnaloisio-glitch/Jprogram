# Trigger Log — 2026-08-09 — LingQ Mini Stories one-off importer

**Work done:** examined a new real source ("Content Explorer" handoff,
LingQ folder 9795706, 62 episode files) to determine whether it needed a
new cleaner. Confirmed yes: the existing Transcript Cleaner treats every
non-blank line as one corpus sentence and has no concept of sections,
but this source's files each combine three real sections — a story told
in 3rd person, the same story retold in 1st person (near-duplicate
content), and a "質問:" (Questions) comprehension-quiz section — marked
inconsistently (58/62 files use "A)"/"B)" prefixes, 59/62 contain the
質問 marker, with several genuine outliers, including a 3-file split
story, `ep060`/`ep061`/`ep062`, where the usual all-in-one-file
structure is instead spread across three separate files).

Two real content-design questions were Owner's to decide, not a cleaning
detail: whether to keep the 1st-person retelling (kept — Owner: both
count as real exposure) and whether to keep the Q&A section (kept —
Owner: still real Japanese, treat like any other sentence). Given both
are kept, the actual cleaning need reduced to stripping only two
unambiguous structural markers: line-start `A)`/`B)` (exactly 2 chars,
consistent meaning wherever it appears, including inside individual
Q&A lines) and standalone `質問:`/`質問：` label lines. The numbered
question-index prefixes (`一:`, `二:`, ... plus an observed `ー:`
variant) are deliberately left embedded — Owner's explicit call, since
reliably stripping every stylistic variant was judged a real risk of
clipping actual sentence content for a cosmetic gain.

Owner confirmed this is a one-off format that will not recur, so the
importer was built as a small, dedicated script — deliberately **not**
integrated into the shared `Batch Importer`/`import_material.py`
infrastructure — mirroring `batch_importer.py`'s `import_one()` call
sequence exactly (`create_standalone_source` → `handoff` →
`production_manager.py --pipeline --auto`), swapping only the
conversion step for the LingQ-specific cleaning. `creator="lingq"` and
the corresponding Workspace `creators.json` entry were added directly by
Advisor (config data, matching the earlier Style/Topic precedent, not
routed through Coder). Owner explicitly wanted the real pipeline
exercised end-to-end with this real data, not just a clean/convert step.

Built via the headless DeepSeek-Coder mechanism in an isolated worktree
(`add-lingq-mini-stories-importer`), `--allowedTools Read,Write,Edit,Bash`,
dry-run only during Coder's own testing. Merged to `master` as `a97bd70`.

**Audit trigger: No — confidence: High, reason:** no Frozen Component
touched — new, standalone script, no modification to any pipeline stage,
writes only through the existing `create_standalone_source`/`handoff`/
`production_manager.py` API exactly as the already-proven Batch Importer
does. Confidence is High because of the verification depth below: this
is real content (Owner explicitly flagged it as such, not disposable
test data), so every claim was independently re-derived from raw
evidence — including running the actual pipeline, not just reviewing
code — before the real batch import happened.

**Verification summary (Advisor's own):**
- Read the full script directly: matches every specified rule exactly.
- Independently, from scratch, hand-verified the cleaning logic against
  raw file inspection (not just re-running the script): `ep019.txt` has
  51 raw lines; lines 1/11/22/37 carry an `A)`/`B)` prefix, line 21 is a
  pure `質問:` label. Expected result: 51 − 1 dropped = 50 cleaned
  lines, 4 stripped — matches both the script's own dry-run output and
  Coder's report exactly.
- Independently re-ran the script's `--dry-run` myself from the real
  repo: byte-for-byte identical to Coder's reported output (62 files,
  same per-file line/strip counts).
- Before running the real batch, tested one file's entire pipeline in
  isolation (`ep001` → `clean_text_lingq-9795706-ep001`): a first attempt
  hit a real environment issue (module imported from the worktree
  resolved `PROJECT_ROOT` to the worktree, which has no `.venv`, since
  the module computes its own project root from `__file__` — an artifact
  of the verification method, not a bug in the script itself, confirmed
  by copying the script into the real repo first and re-running
  cleanly). The canonical file, Source Package, and Registry entry from
  that first attempt were real and valid (not corrupted), so the pipeline
  stage was simply run to completion for that one source directly —
  Clean → Jobs → Requests → Parser (deterministic) → Corpus, all exit
  code 0, `CORPUS_AVAILABLE`.
- Read the resulting real corpus JSONL for that test source directly:
  46 sentences (matching the predicted clean line count exactly), no
  `A)`/`B)`/`質問:` artifacts present, numbered question prefixes
  correctly preserved as decided.
- Ran the full batch for real: **61 imported, 1 correctly skipped**
  (the already-imported test source), **0 failures**.
- Final on-disk confirmation: **62/62** real corpus JSONL files exist
  under the Workspace; the split-story trio (`ep060`/`ep061`/`ep062`)
  produced exactly 10/10/26 sentences, matching the dry-run prediction
  precisely.

**Verdict: CLEAN.** Script committed to `master` (`a97bd70`); the real
import already happened against the live Workspace (untracked by git,
as expected for customer/runtime data — but this data is explicitly
real, per Owner, not the disposable test batch discussed earlier this
session). Worktree and branch removed.
