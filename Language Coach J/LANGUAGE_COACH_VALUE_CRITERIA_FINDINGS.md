# Value Criteria — Empirical Findings & Special Cases

A running log of things learned from actually running the value criteria
(design spec §9) against real data — not architecture decisions, not
open questions to resolve, just accumulated empirical findings and edge
cases discovered along the way. Grows over time; organize by topic as it
does. Distinct from the bootstrap's Open items (the open-item queue) and the
design spec (architecture/decisions) — this is specifically "things we
learned by actually doing it."

---

## Exposure must be computed over a bounded session, not a single piece

**First real test (2026-08-08):** con-teppei episode 4 alone (160
sentences) against real LingQ known-word data — no not-yet-known word
came anywhere close to the illustrative "≥30 exposures" threshold from
design spec §9; the max was 21 (抹茶, the episode's actual thematic word).
One episode is too small a sample — single-piece exposure isn't a
workable acquisition metric on its own.

**Refined by Owner (2026-08-08), sharper than "series-level":** the right
unit isn't an abstract whole-series or whole-corpus scan — it's
**whatever bounded set of content Owner is actually about to consume**
(e.g. "the next hour of audio/video," which may span multiple episodes or
even multiple sources). Compute exposure across that specific candidate
set, see what reaches the threshold, rank the rest by value descending.
Ties Mode 1 directly to a real upcoming session rather than a theoretical
scan, and gives Mode 2 (content selection) a concrete job: assembling
that candidate set in the first place.

**Still explicitly theoretical** — Owner's own words: "still all
theoretical number and thresholds." The ≥30 figure and this whole
mechanism remain unvalidated, not a settled rule — this is a refinement
to the *shape* of the idea, not a threshold confirmation.

**Real candidate for the bounded-session unit, found 2026-08-08:** Owner's
full-capacity routine (`LANGUAGE_COACH_OWNER_PROFILE.md`) includes a
genuine pre-existing daily target — **1,500 LingQ words read per day** —
not a made-up number. Worth using this as the actual bounded-session unit
instead of the placeholder "next hour of content" framing, once real
build work on this starts. Currently paused (routine reduced to ~1hr/day
while this project is being built), not abandoned.

## Short grammatical fragments pollute the candidate list

**Found 2026-08-08:** short grammatical fragments (e.g. た, お, でし —
auxiliary/honorific/copula pieces GiNZA's tokenizer splits out on their
own) show up as high-occurrence "unknown" surface forms alongside genuine
vocabulary in a naive occurrence+unknown filter. Not real vocabulary
items. The value criteria will need a filter for this (minimum length, or
excluding function-word fragments) before "high occurrence + unknown" is
a reliable standalone signal. Not solved yet.

## Loanwords need special handling — at least three cases, not a binary

**Found 2026-08-08, in the same episode-4 report:** the report initially
included カフェ ("cafe") and アクセサリー ("accessories") as equivalent-value
candidates to genuine new vocabulary like 抹茶. Both are simple katakana
loanwords with clean, direct meaning transfer from English — Owner
already knows these conceptually if he knows the English word. Not
recognizing them is a katakana-reading/phonetic-decoding issue, not a
comprehension gap, so they shouldn't count as real gaps the way genuine
new vocabulary does.

**False friends are different — Owner grades these normally in LingQ.**
A loanword-looking term whose meaning has actually diverged from the
source word (e.g. マンション meaning "condo/apartment," not "mansion") is a
real comprehension gap and should count like any other unknown word.

**Mechanism clarified by Owner:** when he actually encounters a loanword
in LingQ, he grades it "ignore" — which removes it from LingQ's metrics
entirely, the same observable footprint as never having encountered it at
all. So **absence in the LingQ export can't by itself distinguish
"deliberately excluded as trivial" from "genuinely never seen."** That
part of the problem isn't solved by anything found so far.

What it does give: a directional heuristic, not a determination — an
absent **pure-katakana** term is more likely to be a deliberately-ignored
trivial loanword than an absent kanji/hiragana term is to be anything
other than genuinely unseen, since there's no equivalent "ignore trivial
vocab" behavior for non-loanwords. Worth weighting by, not a solution to
the false-friend-vs-simple-loanword distinction.

**A third case, not just a binary — real example given (2026-08-08):**

> パトレオンというサイトがありますね ("There's a site called Patreon")

サイト is a genuine loanword, but also a **truncation** (short for
ウェブサイト) narrowed to a specific sense ("website"). Unlike a false
friend, it isn't *wrong* — but unlike a clean loanword like カフェ, hearing
plain English "site" doesn't reliably land on "website" either, since
English "site" is broader/more ambiguous (construction site,
archaeological site, etc.).

So the real spectrum is at least three cases:
1. **Simple loanword, full clean meaning transfer** (カフェ) — not a real
   gap.
2. **False friend, meaning genuinely diverged** (マンション) — real gap,
   already graded normally by Owner in LingQ.
3. **Truncated/narrowed loanword** (サイト) — phonetic recognition alone
   doesn't reliably reconstruct the intended meaning; likely still a real
   (if partial) gap.

**Detecting which case a given katakana term falls into isn't solvable
with current data** — needs a loanword reference list or a heuristic.
Real scope for later, not solved yet — just characterized precisely so it
doesn't silently distort future value reports the way this session's
first one did.
