# Content Consumption Log

Index of what Owner has actually consumed, by source. Owned entirely by
Language Coach — deliberately **not** a tag on Jprogram's Source Registry
(that's a frozen artifact contract on Jprogram's side; adding a field there
would be a Jprogram-side schema change, out of scope here). Cross-
references Jprogram source IDs where they exist, but the log itself lives
here.

**Granularity note (2026-08-07):** this v1 is source-level aggregate totals,
reconstructed from Owner's own journey description in
`LANGUAGE_COACH_OWNER_PROFILE.md`, not a per-item/per-episode log with
dates. A per-item logging tool (Owner floated this 2026-08-07 — "maybe even
make a logging tool") would upgrade this to real entry-by-entry tracking
going forward; see the bootstrap's Open items. Until that exists, update this file
by hand as new consumption happens or gets described.

## Flags (confirmed 2026-08-07)

Three independent Y/N flags per entry, not a single modality label —
content can be consumed multiple ways (e.g. read first, then listened to
separately), and per the Owner profile, *which* modalities apply changes
comprehension level dramatically:

- **Watched** — video, with visual scaffolding
- **Listened** — audio, no video
- **Read** — text

At least these 3; more may get added later if a real need shows up. A
blank/`?` means not clearly stated, not "no" — don't overwrite with a
guessed N/Y without checking.

---

## Log

| Source | Content | Watched | Listened | Read | Amount | Status / notes |
|---|---|---|---|---|---|---|
| CIJ / nijapanese.com | Absolute-beginner tier | Y | Y | N | 100 hours | Phase 1, started Nov 2025 |
| CIJ / nijapanese.com | General content up to difficulty ~45 | Y | Y | N | 181 hours total (incl. above) | At a wall at difficulty ~45 (see profile doc — structural cliff, not just personal plateau) |
| CIJ / nijapanese.com | Old content, rewatch | N | Y | Y | Ongoing | Current activity — deliberately decoupling from visual scaffolding (matches the profile's "reading+audio, low-30s" condition) |
| LingQ | First 40 Japanese mini-stories | N | Y | Y | 40 stories | 3-phase LingQ workflow (see note below) |
| LingQ | Con-teppei episodes | N | Y | Y | Owner states "first 50" | Same 3-phase workflow as mini-stories. **Note:** the transcript file we actually have (`Clean AI transcript 1-50.txt`) only contains episodes 1–28; unresolved whether Owner has 29-50 elsewhere or actual consumption was fewer episodes than stated |
| LingQ | General reading (aggregate) | N | ? | Y | ~85,000 words read (LingQ's own count) | Cumulative; overlaps with the two rows above, not fully separable from them |
| LingQ | Listening (aggregate, passive playlist) | N | Y | N | ~40 hours (rough estimate) | This is specifically phase 3 below (audio-only, no text). Two separate reliability problems, not one: (1) LingQ's timer undercounts — only tracks accurately if the app stays closed, which it often wasn't; (2) **even where tracked, attention varies widely** — sometimes 100% focused attention, sometimes background audio during chores (e.g. doing dishes). The 40-hour figure is not uniform exposure value; real acquisition-relevant exposure is an unknown, smaller fraction of it. Overlaps with the rows above rather than being additive. |

**LingQ's actual 3-phase workflow per item (clarified 2026-08-07),** relevant
because each phase is a different modality condition per the Owner profile:
1. **Read + grade/parse** — active reading pass in LingQ, marking each
   word's known/learning/new status as you go. This is LingQ's own
   per-word known-word tracking — see open follow-up below, potentially a
   much richer known-word source than the manual self-assessment TSV.
2. **Listen while reading along**, playlist view — text visible + audio
   together, simultaneous. Matches the profile's "reading+audio, low-30s"
   condition.
3. **Allocated to the passive listening playlist** — audio-only afterward,
   no text on screen. This is the phase the "~40 hours" aggregate row
   above actually measures. Matches the profile's "audio only, ~level 30"
   condition.
| KanjiDamage (custom-reordered deck) | Kanji recognition | N | N | N | ~400 kanji known | Flashcard drilling (meaning / meaning+radicals+3 examples) doesn't fit the watched/listened/read frame — it's isolated character recognition, not connected-text consumption. Mid deck-transition: original deck retired to review-only at 400, rebuilt custom deck catching up at 50 cards/day, same ordering. See `bootstrap/known_kanji_first400_speedrun.txt`. |

## Open follow-ups

- **Attention/engagement varies within a modality, not just between
  modalities** (2026-08-07) — passive-playlist listening ranges from fully
  focused to background-during-chores, and the current flags can't
  represent that. Worth deciding whether a future logging tool needs an
  attention/quality dimension per entry, not just presence/absence of a
  modality, before treating raw hours as a reliable exposure-value input.
- ~~Check whether LingQ's own per-word known/learning/new grading data is
  exportable~~ — **done 2026-08-07.** Confirmed exportable (not via
  LingQ's native CSV export, which lacks a status field, but via a browser-
  console script hitting LingQ's own `cards` API directly). Pulled all
  6,633 tracked words with status decoded to a 1-5 known-level scale:
  5,365 / 304 / 142 / 773 / 49 across levels 1-5. Saved to
  `bootstrap/lingq_known_words.jsonl`. Full reusable procedure (including
  why simpler options didn't work, and the evidence for the status
  decoding) in `LANGUAGE_COACH_LINGQ_EXPORT_PROCEDURE.md`.
- The two LingQ "aggregate" rows overlap with the mini-stories/con-teppei
  rows rather than being additive — total distinct exposure is smaller than
  summing every row. Not yet reconciled into non-overlapping numbers.
- Con-teppei 50-vs-28-episode discrepancy (above) — worth resolving before
  treating the full "first 50" as consumed.
- Per-item logging tool — floated by Owner (2026-08-07), not yet designed
  or built. Would let this log track individual videos/episodes/sessions
  with dates instead of hand-maintained aggregates, and record the 3 flags
  per item instead of per aggregated row.
- nijapanese content beyond what's summarized here (specific episodes/
  videos within the 181 hours) isn't itemized — only the aggregate is
  known.
