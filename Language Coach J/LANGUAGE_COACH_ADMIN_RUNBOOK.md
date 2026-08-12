# Language Coach — Administrator Runbook

Operations guide for the **finished** Language Coach system, written from
the administrator's seat (drafted 2026-08-08 by Coder per Owner's request,
as a prospective frame — the project is still mid-build; see
`TODO.md` for actual current state). Distinct
from the other roles: Owner consumes content and makes calls; Advisor
designs/evaluates; Coder builds. **The admin keeps data fresh and the
machinery trustworthy** so every working session starts from accurate
state.

Calibration: hobby-project, not enterprise rigor. Cadences below are
**proposed defaults, not settled policy** — tune to observed staleness.

---

## 1. What the finished system is (operational view)

- No standalone app — the chat session is the UI (`LANGUAGE_COACH_DESIGN_SPEC.md` §5).
- Deterministic Python tools in `tools/analysis/` (isolated copies of
  Jprogram's 7 analyzers, grouped by **surface form** per §8a), called
  conversationally by Advisor.
- Two modes: **Mode 1** single-piece/bounded-session value report; **Mode 2**
  cross-corpus i+1 matching.
- Output: highlight-word + grammar-form list in QuadRead's plain clean-text-list
  format (§10).
- Primary known-vocabulary source: **LingQ, level ≥4 = known** (§8b).

## 2. Data assets inventory

| Asset | Path | Freshness driver | Known caveats |
|---|---|---|---|
| LingQ known words | `bootstrap/lingq_known_words.jsonl` | Owner keeps studying; status goes stale | Undercounts knowledge learned outside LingQ (CIJ/audio) — ~13.6% of confidently-known words absent entirely; `extended_status` 0-vs-None loose end |
| Kanji baseline | `bootstrap/known_kanji_first400_speedrun.txt` | Rebuilt deck catching up past 400 | Currently 400; refresh at milestones |
| Self-assessment | `Shawn/teppei_1-50_self_assessment.tsv` | Calibration spot-checks | Lemma-granularity (wrong per §8a; pending surface-form rebuild); NotebookLM-derived baseline, unverified |
| Corpus (parsed) | Jprogram output (e.g. `clean_text_teppeibeginner_ep004.jsonl`) | Jprogram processing | Only ep004 currently trustworthy; ep1 old/DeepSeek, ep2-3 failed |
| Consumption log | `LANGUAGE_COACH_CONSUMPTION_LOG.md` | Hand-maintained aggregates | Not per-item; con-teppei 28-vs-50 discrepancy unresolved |
| Findings log | `LANGUAGE_COACH_VALUE_CRITERIA_FINDINGS.md` | Every new production edge case | Read before trusting any raw value report |
| Session state | `TODO.md` | Each wrap-up | Refresh at session close |

## 3. Recurring operations

### 3.1 LingQ known-word refresh (the core recurring task)
**Cadence:** monthly default; **also before any Mode 1/2 run where known-word
accuracy matters materially** (i.e. almost every report run).
1. Trigger Owner to run the browser-console export per
   `LANGUAGE_COACH_LINGQ_EXPORT_PROCEDURE.md` (Owner's own logged-in
   session; Advisor-side fetch is blocked by design).
2. Process raw download → `bootstrap/lingq_known_words.jsonl` (decoded
   `lingq_level` 1-5; raw download not kept).
3. Sanity-check the distribution against the last pull (6,633 total:
   5,365/304/142/773/49 as of 2026-08-07) — a big jump in level 1 usually
   means new reading volume, not data corruption; a *drop* in totals is
   the anomaly to chase.

### 3.2 Consumption log update
**Cadence:** whenever consumption happens or gets described; at minimum each
wrap-up. Preserve the independent Watched/Listened/Read flags; a blank/`?`
means "not stated," never overwrite with a guess. Flag modality changes
(e.g. rewatch-without-video) — they change comprehension conditions per the
Owner profile.

### 3.3 Kanji baseline refresh
**Cadence:** milestone-driven (every +100 on the rebuilt deck). Update the
file and the 400-count references in `LANGUAGE_COACH_OWNER_PROFILE.md` /
`Shawn/vocab_snapshot_2026-08-07.md` if they're still cited.

### 3.4 Corpus sync from Jprogram
**Cadence:** event-driven — whenever Jprogram outputs new parsed data.
1. Verify the new JSONL is current-generation (`ginza-ja` output; ep004-style,
   not the old DeepSeek data — the parser matters).
2. Run the analysis toolchain (`tools/analysis/`) against it; record the run
   (distinct surfaces, occurrences, spacing stats).
3. Flag processing failures to Advisor/Owner (episodes 2-3 failed on
   Jprogram's side — that's a Jprogram worklist item, admin tracks but
   doesn't fix).

### 3.5 Mode 1 — value report run
1. Assemble the **bounded session** candidate set: the actual batch of
   content Owner is about to consume ("next hour," or the 1,500-LingQ-
   words/day unit when that returns) — never a single piece in isolation
   (empirical: ep004 alone topped out at 21 exposures vs. the illustrative
   ≥30 threshold).
2. Run value criteria (exposure threshold + spacing + not-known).
3. **Manual review before trusting** — until the two filters are built, the
   admin is the filter (see §5 checklist).
4. Hand the resulting highlight list to QuadRead in its plain-text format.

### 3.6 Mode 2 — cross-corpus matching
For content selection: known-word list vs. candidate series/pieces → closest
to i+1 overall, or best exposure to a specific target. `comparison_analyzer`
is the ready-made engine for per-source target-item counts.

### 3.7 Criteria maintenance
- **Threshold recalibration:** derive from self-assessment results vs.
  exposure counts (§8 step 4) when enough new data accumulates — don't
  re-derive on every run.
- **Leech list:** track words past threshold but still unacquired → flag for
  Anki handoff (cloze/sentence cards), **stop targeting via reading** (§9a).
- **Findings log:** append new edge cases to
  `LANGUAGE_COACH_VALUE_CRITERIA_FINDINGS.md` as production runs surface
  them — that file is the running log, don't re-explain findings inline
  elsewhere.

## 4. Health checks (each working session, before real work)

1. `tools/analysis/` smoke-run still passes (analyzers import and run on the
   latest corpus file).
2. `bootstrap/lingq_known_words.jsonl` exists, non-empty, distribution sane.
3. Session bootstrap file reflects current phase (refresh at wrap-up).
4. No known-data staleness items open that this session's task depends on
   (e.g. don't run a report on a 3-week-old LingQ export without flagging it).

## 5. Mode 1 review checklist (the admin's judgment seat)

Until the fragment/loanword filters are built, **this review is what makes a
report trustworthy** — treat it as mandatory, not optional:

- [ ] **Fragment noise:** any short function-word fragments (た, お, でし —
  GiNZA tokenizer splits) ranked as high-occurrence "unknown"? Exclude.
- [ ] **Loanword noise, 3 cases:** simple clean transfer (カフェ — not a real
  gap), false friend (マンション — real gap), truncated/narrowed (サイト —
  likely real gap). Katakana-only terms absent from LingQ skew toward
  deliberately-ignored trivial loanwords (directional heuristic only —
  absence can't distinguish "ignored as trivial" from "never seen").
- [ ] **Bounded-session exposure** used, not single-piece.
- [ ] **Known-word undercount** acknowledged: words absent from LingQ may
  still be known (CIJ/audio-learned) — don't over-flag them.
- [ ] **Leech check:** any word well past threshold still unacquired →
  Anki handoff, not re-targeting.

## 6. Escalation paths (what the admin does vs. hands off)

| Situation | Action |
|---|---|
| Data stale, sanity check fails, report looks noisy | Admin fixes or re-runs (this runbook) |
| Value-criteria change / threshold tuning / new findings | Escalate to **Advisor** (criteria are Advisor/Owner judgment, §9) |
| New consumption-modality questions | Escalate to **Owner** (profile doc is Owner's own data) |
| Jprogram-side failures or schema items | Track, queue for **Jprogram's** worklist (see `LANGUAGE_COACH_SUGGESTIONS_FOR_JPROGRAM.md`) — never write there |
| Cost/subscription decisions (LingQ expiry, DeepSeek pricing change) | Escalate to **Owner** |

## 7. Known watch items (not blockers, tracked)

- `extended_status` 0-vs-`None` inconsistency — doesn't affect level mapping.
- Con-teppei "first 50" vs. 28 episodes actually in the transcript file.
- LingQ undercount (~13-42% of confidently-known words absent) — LingQ is
  the settled primary source regardless.
- DeepSeek pricing change warning ("significant increase expected") — re-check
  the cost math for the Coder redirect when that lands.
- nijapanese.com access ends ~2026-09-25 — **content extraction is already
  complete locally** (904/906 text pieces across all four levels, excl.
  Yuki; see the bootstrap's Open items), so this is no longer a data-preservation
  deadline; it only affects re-fetching/reconciliation against the live
  site after the cutoff.

## 8. Change log

- **2026-08-08** — Drafted by Coder per Owner request (prospective frame;
  project still mid-build). Cadences marked as proposed defaults pending
  Owner/Advisor review.
