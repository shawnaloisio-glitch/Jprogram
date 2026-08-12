# Language Coach — Program Outline (v1, "1000 mile" overview — 2026-08-07)

Working name: Language Coach. The middle stage of the Jprogram → Language
Coach → QuadRead pipeline. Supersedes the v0 fragments-only version of this
doc — this is the first real worked outline, built the same way QuadRead's was.

## 1. Purpose

Japanese-language acquisition support (input-based/comprehensible-input
philosophy — i+1, not classroom study). Consumes Jprogram's corpus/parser
output and analysis data to determine what's actually worth a reader's
attention right now, then feeds that into QuadRead so the reader can read it
with highlighting.

## 2. Position in the pipeline

```
Jprogram  (owns: parser output, SQL database, analysis files)
    ↓  (Language Coach reads pre-made analyzer reports + parser output directly)
Language Coach
    ↓  (highlight-word list + grammar-form list, QuadRead's plain-text format)
QuadRead  (reader — holds and displays the report for reading)
    ↑______________________________|
    QuadRead Stage 2 known-word state feeds
    back into Language Coach's i+1 calc
```

## 3. Audience (confirmed 2026-08-07)

Owner only, for now — but worth designing with future multi-learner/profile
support in mind rather than architecting this as permanently single-user.
Not yet decided how or when that would actually shape the design.

## 4. Data model (confirmed 2026-08-07)

**Inputs, assumed to exist:**
- Owner's known-word + known-grammar list. **Bootstrapping mechanism now
  concrete, not just "hand-built" — see §8.**
- The corpus: thousands of content pieces, each broken down to
  word/sentence/grammar level, with positional data. Owned by Jprogram.
- **Owner's personal consumption history** (confirmed 2026-08-07, new) — a
  record of which specific content pieces Owner has actually already read,
  distinct from the corpus as a whole. Not previously part of the data
  model; surfaced as a gap during value-metric research and immediately
  confirmed as available — Owner already knows and will supply what they've
  consumed. See §8.

**Ownership/access (revised 2026-08-09 — structural change by Owner):**
- **Jprogram stops at the parser output** (the canonical corpus JSONL). It
  no longer owns analysis files or the report SQL database on Language
  Coach's behalf.
- **Language Coach owns everything downstream of the corpus**: the analyzer
  suite (`tools/analysis/` — frequency/distribution/exposure/chunk/
  sentence_metrics, adapted to surface-form grouping), the deterministic
  candidate filter (`tools/analysis/candidate_filter.py`), the value-
  criteria/report logic, and the **SQLite query library** (`library.db`)
  built from analyzer outputs + catalog metadata. This is a reversal of the
  original 2026-08-07 arrangement where Jprogram owned the analysis files
  and SQL database and Language Coach only read them.
- **Jprogram → Language Coach handoff is now a single artifact**: the
  canonical corpus JSONL (`Jprogram Workspace/jsonl/`) plus its naming map
  (`rename_log.csv`). Everything after that is Language Coach's.
- **Metadata for reports** (tier, difficulty, teacher, series, human
  title) comes from joining three sources at import time: analyzer outputs
  (counts) + NJ catalog (`Content Collection/nihongo-jikan/catalog/`) +
  rename map (titles). NIJ/con-teppei sources have nulls there until their
  catalogs are joined the same way.
- **Reports are saved queries against the SQLite library, delivered
  conversationally in chat** — not stored as files (Owner decision
  2026-08-09). The one file artifact is the **reader output package**
  (per-episode: corpus JSONL copy + highlight list + grammar list) for
  QuadRead import. Write access to Jprogram is out of bounds regardless
  (see `CLAUDE.md` workspace boundaries). See §6 for the precise shape of
  read access.

## 5. No standalone application — the chat *is* the UI (confirmed 2026-08-07)

Significant scope resolution: Language Coach does not have, and will not
get, a dashboard, desktop GUI, or web app. **Owner interacts with Language
Coach through this chat**, the same session that does the outlining and
implementation work. What's actually being built is the infrastructure to
make that work well:

- **Bootstrap** — state that needs to load reliably each session: corpus DB
  location, known-word/grammar list location, current value-criteria
  settings, etc. Extends the existing `CLAUDE.md` / session-bootstrap
  pattern, but with Language-Coach-specific data, not just process rules.
- **User contract → "document frequent routines" instead (confirmed
  2026-08-07, supersedes "not yet designed in detail").** No upfront formal
  contract — designing the interaction shape before any real tool has been
  exercised would be premature structure, and risks the same staleness
  problem already flagged for `CLAUDE.md`. Instead: when something becomes
  a real, repeated routine, document it after the fact, same pattern
  already used (without being named as a policy at the time) for
  `LANGUAGE_COACH_LINGQ_EXPORT_PROCEDURE.md`. Revisit the "formal contract"
  idea only if actual friction shows up once real tools exist.
- **Tools** — deterministic Python functions/scripts in this workspace that
  Advisor calls directly (query the corpus DB, compute value-criteria
  scoring, run cross-corpus matching, generate the QuadRead-format export).
  Not a GUI — just callable functions whose output gets discussed
  conversationally.

**Folder convention (confirmed 2026-08-07):** `Shawn/` holds anything Owner
personally interacts with outside the chat itself — tests to fill in,
layman-readable reports, that kind of artifact. Everything else (internal
derived data, working files not meant for Owner to open) stays elsewhere in
the workspace (e.g. `bootstrap/`).

This resolves the earlier "what UI framework / what platform" questions
from a different angle than expected — there's no framework to choose
because there's no separate UI surface to build.

## 6. Data boundary & metric-promotion pipeline (confirmed 2026-08-07)

Resolves the direct-import question raised while researching Jprogram's
Analysis suite (2026-08-07): Language Coach's tools only ever **read data**
from Jprogram, never import/call Jprogram's analyzer code. Two read
sources:

1. **Jprogram's already-generated analyzer reports** (frequency,
   distribution, exposure, expression, chunk, sentence_metrics, comparison
   — see `Jprogram/Analysis/`) — used whenever a report already answers the
   question.
2. **The parser output / canonical corpus directly** (the lemmatized data)
   — used for anything not already covered by an existing report. Example
   given: **series-level analysis** — none of Jprogram's current analyzers
   group above the source/section level, so a "how does this whole series
   look" query has to be computed fresh by Language Coach's own tools
   reading the raw corpus.

This keeps the same boundary discipline already established for QuadRead↔
Jprogram (consume artifacts, don't reach into another program's internals)
— just with two kinds of artifact instead of one, and applied one level
deeper than QuadRead's contract.

**Concrete implementation, built 2026-08-07:** `tools/analysis/` holds
**isolated copies** of Jprogram's 7 analyzer modules — not a live import.
Language Coach owns these copies outright; there is zero runtime
dependency on Jprogram's code, only ever on Jprogram's *data* (the
canonical corpus, read source #2 above). Adapted to group by surface
form rather than lemma, per §8a. This is meaningfully different from
importing Jprogram's code live (`from Jprogram.Analysis import ...`),
which would create real cross-program coupling and was correctly ruled
out — copying keeps each program fully self-contained, arguably *more*
aligned with Jprogram's own one-program-one-task principle than a live
import would be.

**Metric-promotion feedback loop (confirmed 2026-08-07):** if a custom
metric computed in Language Coach's tools turns out to be one we keep
reaching for, Owner will build it into Jprogram's own analyzer suite so the
result becomes a permanent, precomputed part of Jprogram's output (living
in the SQL database once the migration in §4 lands), rather than being
recomputed ad hoc every time. Language Coach's own analysis module stays
the place for exploratory/one-off custom searches and for metrics that
haven't (yet, or ever) earned a permanent home upstream.

## 7. What the tools actually do — two analysis modes (confirmed 2026-08-07)

**Mode 1 — Single-piece value report.** For one piece of content, produce
the list of words/grammar points that meet the current value criteria.
Reviewed and discussed with Owner interactively, then passed to QuadRead,
which holds and displays it for reading.

**Mode 2 — Cross-corpus matching/search.** Compare Owner's known-word list
against many series/pieces in the corpus to find either:
- what's closest to Owner's current i+1 level overall, or
- what gives the best exposure to something specific Owner wants to learn
  (a target word or grammar point).

This is also Language Coach's "content selection" role — helping decide
what to read next, distinct from QuadRead's job of actually rendering the
reading experience.

## 8. Known-level bootstrap via consumption history (confirmed 2026-08-07)

**This is likely the actual first real task**, ahead of Mode 1/Mode 2
tooling — it produces the known-word list Modes 1 and 2 both depend on, and
Owner indicated it's probably first in sequence.

Owner is early in this project and knows what they've already consumed.
Concrete workflow:

1. Owner supplies their personal consumption history — which specific
   content pieces they've actually read (format/shape not yet decided).
2. Language Coach searches/restricts analysis to just that consumed
   subset (not the whole corpus) and produces a frequency list of the
   words and grammar actually encountered within it.
3. That frequency list drives generated test/quiz material to assess
   Owner's **true current level** — this is the concrete bootstrapping
   mechanism for the known-word/grammar list (data model §4's first
   input), replacing the vaguer "hand-built frequency list + self-
   assessment quizzes" idea carried over from the original QuadRead-
   conversation fragments with something grounded in material Owner has
   actually been exposed to.
4. **Empirical acquisition-threshold calibration:** cross-referencing test
   results (known vs. not, per item) against each tested item's exposure
   count *within the consumed material* gives a real, personally-
   calibrated estimate of how many exposures it actually takes Owner to
   acquire a word or grammar point — replacing the illustrative/arbitrary
   "≥30 exposures" example in §9 with a derived number specific to Owner,
   grounded in Owner's own data rather than a guess.

**Related refinement to the series-onboarding-curve idea (§9 research):**
the same per-episode new-vocabulary curve doesn't just show a difficulty
gradient — it also marks the point where a series shifts from effortful
"work" (conscious decoding, heavy new-vocabulary load) to comfortable
"content consumption" (Owner is just enjoying it). That transition point is
itself a useful signal, e.g. for deciding whether to push through a slow
start or for setting expectations before starting a series.

**Open:**
- Format/shape of the consumption-history data Owner will supply.
- Whether this is a one-time bootstrap or a recurring recalibration as
  Owner's level grows (re-test periodically?).

### 8a. Known-word granularity: surface form, not lemma (confirmed 2026-08-07)

**Significant decision, applies project-wide, not just to this bootstrap.**
Different inflected/conjugated forms of a word (e.g. 食べる/食べた/食べれば)
are tracked as **distinct known-word items**, not collapsed to one lemma.
Owner's own reasoning: he isn't explicitly studying grammar or practicing
conjugation — the success metric is **whether he can consume content**, not
"how many words I know" in the abstract. Whether he can parse the exact
surface form actually appearing in a text is what matters; abstractly
knowing the dictionary form doesn't guarantee that.

Practical implications:
- Jprogram's analyzers (frequency/distribution/exposure/etc.) group by
  lemma by default, falling back to surface only when lemma is null — but
  each lemma entry keeps a nested per-surface breakdown (`"surfaces": {
  <surface>: count, ... }`). Language Coach's tools need to read at the
  surface level (flatten that nested breakdown) rather than trust the
  lemma-level grouping directly. Not yet built — a design note for §5/§6's
  tools, not a blocker today.
- LingQ's own `term` field is already surface-form-native (confirmed via
  the reconciliation below) — good alignment, not a mismatch to fix.
- The interim self-assessment approach (§8, `Shawn/teppei_1-50_self_assessment.tsv`)
  was built from NotebookLM's **lemma**-grouped baseline — now the wrong
  granularity per this decision. Not redone yet; flagged in
  the bootstrap's Open items.

### 8b. Reconciling the two known-word datasets (2026-08-07)

Two independently-built known-word datasets exist:
- **LingQ** (`bootstrap/lingq_known_words.jsonl`) — 6,633 surface-form
  terms, level 1-5, built from casual in-app engagement across ~9 months.
- **Manual self-assessment** (`Shawn/teppei_1-50_self_assessment.tsv`) —
  352 lemma-form words, strict "confident recall out of context" standard.

Cross-referencing the 352 self-assessed words against LingQ by exact
string match (226/352 found — the rest are lemma forms LingQ never
recorded as an exact surface occurrence, expected given §8a):

| Self-assessment | LingQ level 4-5 (Known/Mastered) | LingQ level 1-3 | Not in LingQ |
|---|---|---|---|
| Y — confidently known (n=81) | 50.6% | 35.8% | 13.6% |
| blank — recognized, unconfident (n=271) | 10.3% | 47.2% | 42.4% |

**Real, meaningful correlation** (confidently-known words are ~5x more
likely to be LingQ-Known than the unconfident bucket) — the two signals
aren't noise relative to each other. **But neither is a complete picture
on its own:**
- LingQ under-counts: over a third of Owner's confidently-known words sit
  at LingQ level 1-3, or aren't in LingQ's tracked set at all (13.6%) —
  plausibly learned through CIJ/audio exposure rather than LingQ itself.
- The self-assessment is too narrow in scope (352 words, one source) to
  serve as a general-purpose known-word list on its own.
- LingQ is also a more lenient signal than the strict self-assessment
  standard (10.3% of "unconfident" words are already LingQ-Known) —
  consistent with the earlier caveat that LingQ status reflects casual
  clicking, not confident recall.

**Grading discipline, worth trusting more than typical LingQ data (2026-08-07):**
Owner's own practice: if he stumbles on a word LingQ has marked at a
higher status, he manually downgrades it rather than leaving the status
inflated. Explicitly stated reasoning — "very little ego in this, value
data over feeling like I'm progressing." This is a self-correcting signal,
not just monotonic upward clicking, which is a real reason to weight
LingQ's status data more heavily than the "casual/lenient" framing above
might suggest on its own — the leniency caveat still holds (10.3% figure
above), but it isn't compounded by motivated/inflated grading.

**Confirmed 2026-08-07 (no longer just a working recommendation):** LingQ's
6,633-word set is the primary known-vocabulary source going forward (best
available scale, surface-form-aligned per §8a), with **level ≥4 as the
"known" threshold** — while acknowledging it will under-count real
knowledge acquired outside LingQ. The self-assessment approach is better
suited as an occasional calibration/spot-check than as the primary source.
Building the actual tooling around this is tracked in the bootstrap's Open items.

**Grammar known-state tracking is explicitly deferred** (confirmed
2026-08-07) — not attempted until real corpus/learning-history data exists
in the system. Method undecided: may replicate this vocabulary approach,
or something different once there's real data to design against. LingQ's
Vocabulary page has an unexplored "Phrases" tab, worth checking first.

## 9. Value criteria (illustrative example, not finalized — 2026-08-07)

Example given: a word counts as valuable if it has ≥30 exposures, ≥2
sentences average spacing between exposures (not clustered), and is not
already on the known list. **§8 gives a concrete path to replace the ≥30
with an empirically-derived, Owner-specific number.**

**Explicitly not settled as a fixed rule.** Owner: "learning what is
valuable is part of the process" — the criteria themselves are expected to
be tuned/iterated over time, not fixed once and left alone. Given §5 (chat
is the UI), tuning most likely happens conversationally — Owner asks for a
re-run with adjusted parameters rather than adjusting a GUI control — but
this is Advisor's inference, not something Owner has confirmed explicitly.

**Research done 2026-08-07** (read all 7 analyzer modules directly, not
just names) surfaced concrete candidate signals beyond the original
example, none chosen yet — listed as researched raw material, not
decisions:
- **Coverage breadth / concentration ratio** — occurrences ÷ distinct
  sources. Low ratio (spread thin across many sources) marks broadly-
  useful "core" vocabulary; high ratio (concentrated in one or two
  sources) marks domain-specific jargon, valuable only if Owner is
  invested in that specific content.
- **Exposure-spacing consistency** — gap stddev distinguishes steady,
  evenly-spaced exposure (good for natural reinforcement) from bursty,
  clustered-then-abandoned exposure.
- **Surface-form novelty** — a lexical item can be "known" while a
  specific inflected surface form is still new; scorable at the surface
  level via the `surfaces` breakdown every analyzer already reports, not
  just at the lexical/lemma level.
- **Same 3-part formula applied to `chunks`** (the grammar-pattern layer,
  in the absence of a real grammar parser) and to `expressions` (fixed
  phrases) — extends the word-level formula to grammar and idiom value.
- **Productive pattern vs. fixed idiom** — an expression `pattern` with
  many distinct `surfaces` is a productive, generalizable rule; one with
  only one or two surfaces is a fixed idiom, only worth memorizing as-is.
  Same underlying data, pedagogically different kind of value.
- **Best example-sentence finder** — for a target word, find the sentence
  among its occurrence locations where it's the *only* new/valuable item
  and everything else is already known — a genuinely different output
  ("here's the best sentence to learn X from") than a flat word list.
- **Series onboarding curve** — per-episode new-valuable-word count across
  a series, in order; shows where a series "settles" into comfortable
  vocabulary, a possible better entry-point episode, and (§8) the
  work-to-consumption transition point.
- **Redundancy/diversity check** — `comparison_analyzer`'s shared-
  vocabulary overlap between two candidate sources, used to flag when two
  pieces of content would give largely duplicate exposure rather than
  complementary value.
- **Per-sentence digestibility** — `chunks_per_word`/`expressions_per_word`
  density flags sentences that pack in a lot of unfamiliar structure at
  once vs. ones that introduce value more gently.
- **Per-source "sweet spot" scoring** — % of a source's distinct vocabulary
  that's known vs. valuable-and-new vs. far beyond threshold, for ranking
  candidate content in Mode 2.
- `comparison_analyzer` is already a ready-made engine for Mode 2's
  "best exposure to X" search (per-source occurrence counts for a
  specific target item).

**Still open:**
- Do grammar points get scored by the same three-part criteria as words, or
  their own distinct rule? (Mechanically possible via `chunk_analyzer` —
  not yet decided whether that's the actual rule to use.)
- Exact final shape of the "bounded session" exposure unit (e.g. "next
  hour of content") — the right shape of the idea is confirmed, the
  mechanism isn't built.

### 9a. Leech handling — a second decision branch, not just a threshold (confirmed 2026-08-08)

Owner's personal "leech" philosophy (SRS terminology: an item that keeps
resisting acquisition despite repeated review) applies to the value
criteria directly, and isn't just a tuning knob on the existing exposure
threshold — it's a genuinely separate behavior:

- **Normal case:** exposure accumulating toward the threshold, not yet
  known → keep targeting via reading (the existing §9 mechanism).
- **Leech case:** exposure has accumulated well *past* the threshold
  (illustrative, unconfirmed number: 60 good exposures) and the word is
  **still** not acquired → stop targeting it through reading entirely.
  Reading/exposure clearly isn't the effective method for this specific
  word, so continuing to chase it there is wasted effort — flag it for
  handoff to a different acquisition method instead (e.g. cloze
  flashcards, sentence cards in Anki), outside Language Coach's own
  reading-value-report scope.

Broader philosophy behind this, worth keeping in mind for scope
calibration generally, stated directly by Owner: "we want high quality
material but are not going to waste 99% of our time chasing that last
1%." Same principle behind being fine with the occasional bunsetsu
chunk-coarsening exception (§9's chunk-boundary discussion) rather than
demanding perfection everywhere.

**Not built yet** — needs the same cumulative/bounded-set exposure
tracking as the main criteria (§9's "next session" refinement) before a
leech threshold can even be evaluated meaningfully.

**Empirical findings and special cases** (single-piece vs. bounded-session
exposure, grammatical-fragment noise, loanword handling with a real
three-case split) now live in their own file —
`LANGUAGE_COACH_VALUE_CRITERIA_FINDINGS.md` — since this is expected to
keep growing and doesn't belong crammed into this section indefinitely.
Check there before assuming a value report's raw output is trustworthy.

## 10. Output (carried over from the original fragments, not re-confirmed this session)

Intended: a highlight-word list and grammar-form list, in the plain
clean-text-list format QuadRead's Stage 1 already expects (deterministic
exact-match against source text; grammar given as longest surface form).
Should be re-confirmed once Mode 1's actual output shape is designed in
detail.

## 11. Development model & runtime convention (confirmed 2026-08-06, see `CLAUDE.md`)

- No Coder/OC stage — Owner + Advisor only. Advisor implements tools
  directly once a task is approved.
- If the built program makes any AI API calls, development uses
  Anthropic's API; production switches to DeepSeek's API. Still open
  whether Language Coach needs AI calls at all — current direction
  (confirmed 2026-08-07) leans deterministic tools doing the actual
  analysis work, consistent with Jprogram's own stated priority order.
- Tech stack: Python, matching Jprogram — natural fit for reading its SQL
  DB/corpus files directly (confirmed 2026-08-07). No UI framework needed
  per §5.

## 12. Not yet defined

- ~~What "domain" means~~ — **resolved 2026-08-07** for at least the
  nijapanese source: its catalog has a real 138-entry, multi-label topic
  taxonomy per video (genre, grammar-focus, format, regional/holiday
  content — see `Content Collection/nijapanese/catalog/nij_catalog_topics.tsv`).
  This is "domain." Whether other sources (con-teppei, future manga) have
  an equivalent taxonomy, or need one imposed, is still open.
- **Jprogram schema gap review, worked through with Owner 2026-08-07
  while he was mid-task on Jprogram's schema — final resolution below,
  supersedes the original field-wishlist (which incorrectly assumed
  nijapanese would be collection-type; it's actually standalone):**

  | Gap | Resolution |
  |---|---|
  | Fine-grained numeric `difficulty` | **Not added to Jprogram's schema** — source-specific to nijapanese, and nijapanese will end up a small fraction of the library, so it doesn't belong in a universal field. Language Coach instead cross-references `Content Collection/nijapanese/catalog/` directly when working with nijapanese content. |
  | Teacher identity (`teacherIds`) | **Skipped** — also too site-specific (only nijapanese has multiple teachers under one platform). The original motivating concern (excluding Yuki's content) turns out to already be enforced upstream in `Content Collection`, before anything reaches Jprogram — no loss from skipping this. |
  | Title | **No new field** — nijapanese is standalone-identity (not collection+episode as first assumed), so its existing `source_name` field gets renamed to `title` and directly covers this. For true collection-type series (One Piece, TV series), the collection's `display_name` + episode number serves as the effective title; whether a distinct per-episode title is also needed there is still undecided ("will need more thought," per Owner). |
  | Traceability from a Jprogram source back to its original catalog row | **Turned out to be a non-issue.** Jprogram only ever ingests from the already-downloaded local catalog snapshot, not a live query — so even though nijapanese will likely reindex/recompile after Yuki's ~800 videos leave the platform, that never needs reconciling against, since Owner loses site access entirely after ~2026-09-25 anyway (see the bootstrap's Open items). |
  | Season indicator | **Real gap, added.** Collection-type identity was flat `collection_id`+`episode` with no season field — doesn't work for real multi-season TV series. Now part of the collection schema (alongside `origin`→renamed `creator`, e.g. NIJ/NHG/NHK/ANIME as platform-level tags, not individual-teacher — consistent with skipping teacher identity above). |

  Net effect: no field was added to Jprogram's schema for nijapanese-
  specific richness (difficulty, teacher) — Language Coach reads that
  directly from the Content Collection catalog instead, keeping Jprogram's
  core schema source-agnostic. `topicIds`/domain remains genuinely
  unimplemented in Jprogram (see the "domain" resolution above) and is the
  one real schema gap still queued to build.
- Whether the corpus DB (per §4's flat+SQL migration) exists yet in a form
  Language Coach can actually build/test against, or whether that's
  blocked on Jprogram's own upcoming migration work.
- Format/shape of Owner's consumption-history data (§8) — this is now the
  more concrete open item that supersedes the old vague "interim known-word
  bootstrap tool, where does it live" question.
- Detailed design of the bootstrap file, the user contract, and the tools
  themselves (§5) — this outline establishes that they're the actual
  deliverable, not their contents.
- Exact SQL schema / connection mechanism for Language Coach to reach
  Jprogram's database.
- Which of §9's researched candidate value signals (if any) actually get
  used, and with what thresholds — §8 gives a path to derive at least the
  core exposure threshold empirically rather than choosing arbitrarily.

## Next step

Likely sequence: (1) get Owner's consumption history and run the §8
bootstrap to establish a real known-word/grammar list and a calibrated
exposure threshold, before (2) detail-designing the §5 components
(bootstrap, user contract, tools) that Modes 1/2 depend on. Still blocked
on whether Jprogram's DB migration has landed yet, since the tools need
something real to query — but the §8 bootstrap may be doable against
already-consumed material regardless.
