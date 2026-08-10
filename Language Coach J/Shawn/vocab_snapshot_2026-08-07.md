# Vocabulary Snapshot & Prediction — 2026-08-07

Just-for-fun early prediction, recorded to compare against once more data
(real Jprogram corpus exposure/spacing data, a bigger self-assessment,
more LingQ study) is in the system. Method was necessarily crude at this
stage — see caveats.

## Snapshot

- LingQ known+mastered (level 4-5): **822 / 6,633** tracked surface forms (12.4%)
- Known kanji (KanjiDamage-based): **400**
- Known caveat: LingQ-only figure undercounts real knowledge — anything
  learned via CIJ video/audio that never passed through LingQ isn't
  counted here.

## Prediction: highest-priority learning target

**使う (つかう, "to use")** — picked from the pool of 373 words that are
LingQ importance=3 (top frequency tier) but still level 1 (barely
encountered). Reasoning: high-frequency verb, structurally load-bearing.

Runners-up considered from the same pool: いま ("now" — most recently
encountered candidate), 覚える ("to remember/learn").

## Method caveats (why this is a low-confidence first guess)

- Used LingQ's own `importance` field as a frequency proxy — not real
  exposure/spacing data from Jprogram's corpus (not connected yet).
- No spacing/distribution signal at all — just a frequency-tier ×
  known-level filter.
- "Priority" here means "common but not yet known," not validated against
  any actual value criteria from the design spec (those are still
  illustrative, see `LANGUAGE_COACH_DESIGN_SPEC.md` §9).

## To check later

Once real corpus data and a bigger known-word dataset exist, re-run this
and see whether 使う (or something like it) actually shows up as
high-value, and whether the 822/6,633 known-word figure moved in a
sensible direction.
