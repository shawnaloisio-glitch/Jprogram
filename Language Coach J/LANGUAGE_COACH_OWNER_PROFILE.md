# Owner's Language Journey — Profile (as of 2026-08-07)

Durable context about Shawn's actual Japanese-acquisition history and
current state — distinct from `LANGUAGE_COACH_DESIGN_SPEC.md` (project
architecture) and `WORKING_LIST.md` (open items). This is input data the
project serves, not a decision about the project itself. Expected to be
updated as Owner's level changes, not just at wrap-up.

---

## Why this project is a current priority (confirmed 2026-08-08)

Three real reasons, not just technical interest: (1) genuine enjoyment of
building it, (2) **long-term cost savings** — LingQ and nijapanese
subscriptions together are a real, ongoing expense, and part of the point
is eventually not needing to pay for them once Language Coach/QuadRead can
do the same job (gives the "LingQ is the interim known-word vehicle until
QuadRead's own grading stage exists" note in `CLAUDE.md` real financial
weight, not just an architectural preference), and (3) **a deliberate
short-term-for-long-term trade** — Owner expects building this to speed
up his overall acquisition progress net, even while accepting slower
direct study progress right now (routine already reduced from ~4hrs/day
to ~1hr/day, see the daily-routine section below) while it's being built.

## Goals and theoretical grounding (confirmed 2026-08-08)

**Input-only. No goal to speak or write Japanese, at all.** Purely
receptive — listening and reading comprehension. This isn't a phase or a
current limitation, it's the actual target; nothing in Language Coach
should assume or build toward production ability.

**Staged target, in this stated order:**
1. **Anime with subtitles** — the goal is the ability to enjoy the
   content in the native language. Doesn't matter whether reading is
   supporting listening or the reverse; comfortable enjoyment is the bar,
   not "graduate off subtitles" as an explicit separate goal.
2. **Japanese TV series.**
3. **Reading.**

**No specific target show/series list (confirmed 2026-08-08).** Owner
enjoys a wide range of content, no genre restriction — the plan is to
follow "the natural progression path," starting with easy slice-of-life
content and moving up difficulty as **the corpus's own metrics suggest**,
not a predetermined list Owner picks from. This is a real confirmation
that Mode 2 (content selection/i+1 matching) isn't a nice-to-have — it's
the actual intended mechanism for deciding what to consume next, not a
supplement to a fixed plan.

**But Owner expects reading to actually land first in practice**, despite
being third in the stated goal order — and gave a real, structural reason
why, not just a preference:

- **Theoretical grounding:** Krashen-informed comprehensible-input theory
  — repeated exposure to comprehensible input drives acquisition. Owner
  explicitly does *not* fully agree with the stronger Krashen claim that
  adults acquire language the same way children do; the exposure
  mechanism itself is what he credits, not the full theory.
- **Reading as a better "domain-specific SRS" than Anki:** in Anki, the
  *learner* decides what's worth reviewing, arbitrarily, disconnected from
  real usage. In reading, the *content itself* determines what recurs and
  matters, and a word's meaning builds up progressively across encounters
  within real context, rather than being presented decontextualized from
  the start.
- **Why the trio of programs (Jprogram → Language Coach → QuadRead)
  specifically accelerates reading, not anime/TV:** the tooling solves
  Anki's core weakness (not knowing what the content actually wants to
  teach) by computing real exposure/value data from real text, and
  enables i+1-appropriate content curation (Mode 2) that a reader can't
  do for themselves in advance. **Structural reason this favors reading
  specifically (Advisor's inference, confirmed as matching Owner's
  reasoning):** the whole pipeline is fundamentally a *text*-analysis
  pipeline — parser, exposure math, value criteria, all operate on
  transcribed text, even when the source is a video's subtitle file.
  There's no equivalent "audio-level exposure/value analysis" being
  built. So the tooling investment converts directly into reading
  precision; listening comprehension doesn't get the same structural
  boost from this specific project. That's why reading is likely to
  become the strongest skill first, even though it's the stated
  third-priority goal.
- **Confirmed by Owner (2026-08-08):** no cheap way exists to build
  equivalent audio-level analysis — this isn't just an observation about
  current scope, it's a real practical constraint, not something to
  expect gets solved incidentally later.
- **A second, distinct limitation, also raised by Owner (2026-08-08):
  subtitles present meaning in truncated/paraphrased form, not the actual
  words spoken.** Subtitle text (anime source material) is commonly
  condensed for readability/timing, not a verbatim transcript of the
  audio — a real fidelity gap, separate from parser-accuracy concerns
  (DeepSeek vs. `ginza-ja`, etc.) already tracked elsewhere. This means
  subtitle-sourced corpus data is an inherently lossier approximation of
  what's actually spoken than transcript-sourced data (e.g. con-teppei's
  podcast transcripts) is of its own audio. **Sharpens the reading-first
  argument further:** even within "reading," transcript-sourced material
  likely carries more reliable underlying exposure data than
  subtitle-sourced material — worth keeping in mind when Language Coach
  eventually works with actual anime-subtitle sources, not just as a
  general caveat.

**The corpus/reading pipeline is also a bridging mechanism to video, not
just an end in itself (Owner's theory, 2026-08-08, discussed and
refined):** pre-reading material related to a piece of video content
before watching it offloads message-decoding from the brain, freeing
cognitive bandwidth for listening comprehension specifically — making the
video effectively closer to i+1 even though the exact wording won't
match. Advisor's pushback and Owner's resolution, both worth keeping:
- Not literally the same mechanism as visual anchoring (real-time,
  moment-specific support) — pre-reading is macro-level/gist support
  established *before* the fact, a different (related) mechanism, not an
  equivalent one.
- **Goal is content consumption, not comprehension purity** — so relying
  on pre-reading as scaffolding isn't a compromise on the actual goal,
  since the goal was never unaided listening in the first place.
  Decoupling (e.g. rewatching the same content a second time with no
  subtitles) is a natural secondary objective to pursue *after*
  consumption is already happening, not a precondition for the approach
  counting as successful — mirrors, but isn't required to resolve the
  same way as, the visual-scaffolding decoupling already underway with
  CIJ content.

**Practical implication:** Language Coach's actual near-term value to
Owner is concentrated in reading/text-comprehension support — consistent
with everything already built (QuadRead is a reading app, the value criteria
operate on parsed text, §9a's leech-handling hands off to Anki
specifically for cases where reading-driven acquisition isn't working).
Not a scope change, but confirms the existing direction is the right one,
not an accident of what happened to get built first.

## Timeline

Started studying Japanese **November 2025** (~9 months in, as of this
writing).

1. **Phase 1 — pure visual/audio immersion.** 100 hours of absolute-
   beginner content on CIJ (cijapanese.com, since renamed nijapanese.com),
   paid subscription. Video, no subtitles, heavy visual scaffolding.
2. **Phase 2 — added reading + audio, on top of continuing Phase 1.**
   LingQ: read the first 40 Japanese mini-stories and the first 50
   con-teppei episodes. LingQ listening was audio of transcripts already
   read, largely passive/background listening (LingQ's own timer
   undercounts this significantly — app has to stay closed to track
   accurately, which it often wasn't).
3. **Kanji, parallel track throughout.** Started KanjiDamage, reordered by
   character-recognition priority (recognition was identified as the
   bottleneck holding back reading). Custom-trimmed the cards down to
   meaning / meaning+radicals+3 examples as he went. Reached 400 kanji on
   that original deck, then retired it to review-only and rebuilt a fresh
   custom deck at the same ordering from scratch. Currently doing 50 new
   cards/day on the rebuilt deck, catching it back up to the same 400-point
   the original deck reached, before fully retiring the original.

## Current exposure stats (self-reported, 2026-08-07)

| Source | Stat |
|---|---|
| CIJ/nijapanese (video, heavy visual scaffolding) | 181 hours; sitting at difficulty ~45 on nijapanese's scale, explicitly **at a wall** there |
| LingQ reading | ~85,000 words read |
| LingQ listening | ~40 hours (rough estimate — timer known to undercount) |
| Kanji (KanjiDamage-based, custom deck) | ~400 known (see `bootstrap/known_kanji_first400_speedrun.txt`) |

**Current activity:** deliberately rewatching old CIJ content audio/text
only (no video) — actively working to decouple comprehension from visual
scaffolding rather than assuming the 181-hour/level-45 figure reflects
unaided ability.

## Daily routine / pace (confirmed 2026-08-08)

**Full-capacity routine** (before reducing time to build this project),
~4 hours/day total:
- Anki — kanji recognition *and* katakana strengthening (a distinct,
  actively-trained skill, separate from vocabulary — relevant context for
  why the loanword/katakana-decoding distinction in
  `LANGUAGE_COACH_VALUE_CRITERIA_FINDINGS.md` matters so much to him).
- 1 hour nijapanese — on-level video only until hitting the difficulty
  wall (§ above), then regressed to audio+readalong, still current.
- 2 hours LingQ reading, **with a real daily target: 1,500 LingQ words
  read per day.** This is a genuine pre-existing pace goal, not a made-up
  number — a strong candidate for anchoring the "bounded session" exposure
  unit from `LANGUAGE_COACH_VALUE_CRITERIA_FINDINGS.md`, rather than the
  placeholder "next hour" framing used there so far.

**Current, reduced routine** (while actively building this project),
~1 hour/day: Anki daily (maintained), some nijapanese time, passive
listening in the LingQ passive playlist. The 1,500-word/day active
reading goal is currently paused, not abandoned.

## Modality-specific level — the real picture, not a single number

Owner's own breakdown, more precise than the aggregate stats above suggest:

- **Video + audio + visual scaffolding:** ~level 45 (nijapanese scale) —
  but this number is inflated by visual support, not a clean listening
  score.
- **Audio only, zero visual support:** ~level 30. This is a real ceiling,
  not the 45 figure.
- **Reading + audio together:** also feels like low-30s — audio is doing
  the load-bearing work here; text isn't adding independent difficulty
  when paired with sound.
- **Reading alone, no audio, no visual:** **not reliably placeable at any
  level** — the weakest skill by a wide margin, "would honestly struggle
  at any level."

**Owner's own framing: "visual is a hard carry, audio is a strong carry
after that."** I.e. a carry hierarchy — visual > audio > text-alone (~no
carry, closest to raw underlying ability).

**Why this matters for Language Coach specifically:** QuadRead is a *reading*
app. The modality that matters for its i+1 calc is exactly the one
flagged above as weakest and least reliable. This also explains, in
hindsight, the `Shawn/teppei_1-50_self_assessment.tsv` results (81/352
confidently known out of context) — that's close to the pure-reading
condition (no audio, no visual crutch), so the low confident-known count
isn't overly strict grading, it's an accurate reflection of reading being
the underdeveloped skill relative to listening/video.

**Practical implication (not yet a final decision):** nijapanese's numeric
`difficulty` field is calibrated against listening/video content, so it's
likely the wrong ruler for Owner's actual reading level. The
self-assessment-based approach (built directly from what Owner can
actually read, out of context) is probably the more trustworthy signal
for Language Coach's real purpose, even though it's slower to build out
than reusing an existing platform's difficulty scale.

## Reading practice: deliberately no furigana (confirmed 2026-08-08)

Owner reads without furigana on purpose — "I do this the hard way for now,
no furigana." Confirmed in the context of the Nihongo Jikan intake format
(its transcripts ship as ruby-annotated HTML). Two consequences for the
pipeline:

- **Corpus text must be furigana-stripped.** The consumed text is the
  kanji+kana surface form with `<ruby>`/`<rt>` readings removed — that's
  what he actually reads, so that's what the corpus should contain. See
  `LANGUAGE_COACH_SUGGESTIONS_FOR_JPROGRAM.md` item 4 (the ruby-HTML
  intake cleaner spec).
- **Don't treat embedded readings as a grading crutch.** Furigana in
  source material is not equivalent to known-kanji; reading ability must
  be measured against furigana-free text (consistent with the
  reading-alone = weakest modality finding above, and with the
  kanji-recognition baseline living in `bootstrap/`).

## Platform-specific insight: nijapanese difficulty ~45 is a structural cliff

Not a smooth continuum. At difficulty ~45 on nijapanese specifically,
three things change at once: speech transitions toward near-native speed,
most visual scaffolding disappears, and a new tier of grammar gets
introduced in a block rather than gradually. A numeric difficulty score
that looks continuous is misleading right around this point — treat
content just above/below 45 as a discontinuity, not a linear step, when
this becomes relevant to Mode 2 (cross-corpus i+1 matching).

## Self-assessment data so far

`Shawn/teppei_1-50_self_assessment.tsv` (con-teppei ep 1-28 vocab, 1,374
lemmas, frequency-sorted): Owner assessed the first 352 rows (by
frequency rank) before stopping.

- **81 marked `y`** — confidently known out of context (high bar).
- **271 left blank within the assessed range** — recognized, probably
  understood if encountered in a sentence, just not confident enough to
  call "known" on isolated recall. Functionally closer to known-for-
  reading than to unknown — **not** a negative signal.
- **Rows 353–1,374** — not assessed yet, no signal either way.

See `WORKING_LIST.md` for the caveat on the underlying vocab-count data
itself (NotebookLM-derived, unverified against a real parser).
