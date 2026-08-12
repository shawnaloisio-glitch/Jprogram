# Suggestions for Jprogram (queue retired 2026-08-13)

Compiled 2026-08-07 from a Language Coach session — surfaced while
reviewing Jprogram's schema and current state from the consumer side.
Owner: add whichever of these you want to Jprogram's own the bootstrap's Open items
when back in that project. Not written there directly — Language Coach's
write access doesn't extend to Jprogram.

---

## 1. `source_name` → `title` rename not yet applied to the GUI

Confirmed decision earlier this session (standalone-identity content,
e.g. nijapanese, needs a title since collection+episode carries no
descriptive weight for non-series content — collection-type content
still uses collection `display_name` + episode instead). The Sources tab
GUI still labels the field "Source name:" on the Standalone form.
Language-only rename, no schema/data change — just confirm whether it was
missed or intentionally deferred.

## 2. Flat occurrence-index SQL table — a targeted addition, not a JSON dump

Discussed at length this session. Not a proposal to move the canonical
JSONL corpus into SQL, or to duplicate it wholesale — that wouldn't
actually help (the exposure/distribution math Language Coach needs is
inherently sequential, not relational, so a 1:1 JSON mirror doesn't speed
anything up).

What would help: a **flat, indexed table of occurrences**, derived from
the JSONL and kept as a disposable/rebuildable cache — same pattern
`jprogram.db`'s existing metadata tables already use, just extended to
cover content, not just identity:

- One row per word occurrence: `source_id, sentence_id, global_position, surface, lexical`
- Same idea for chunks and expressions

**Why it's worth it, and why now specifically:** at "a couple thousand
imports" scale, the real bottleneck for Language Coach's cross-corpus
matching (Mode 2 — "does word X appear anywhere, and where") won't be the
sequential distribution math itself, it'll be finding *which sources are
even relevant* before running that math — which today means reading
every JSONL file into Python just to check. An indexed SQL table turns
that into an instant lookup; the actual sequential analysis then only
runs on the narrowed candidate set. Building this now, while volume is
still small, avoids a painful backfill later.

Doesn't touch Frozen Components (`corpus_builder.py`, `parser_normalizer.py`)
or change the canonical JSONL's status as source of truth — this is a new
downstream consumer reading already-produced output, not a change to how
it's produced.

## 3. `jprogram.db`'s metadata index is currently stale

Checked directly (2026-08-07): the `sources` table still has `origin_id`
and `source_name` columns, and no `season` column at all — doesn't match
the current GUI (Season# is already live, origin→creator rename already
done in code). Consistent with the known gap that the index has no
auto-rebuild trigger. Not urgent, but worth a manual rebuild so the index
actually reflects current reality, especially before relying on it for
anything (including item 2 above).

## 4. Nihongo Jikan intake — second cleaner (ruby-HTML → plain text): **DONE 2026-08-08**

**Resolved — no longer a pending suggestion.** Owner confirmed the ruby
cleaner was finished; the last 8 corpus sources in Jprogram's workspace
are its output (NJ ids 10, 19, 21, 81, 111, 114, 421, 461 — e.g.
`clean_text_114-things-i-use-on-hot-days-暑い日に使うもの`). Source Registry
records confirm the shape: `original_filename` = `{id} - {title}.txt`,
`cleaning_profile: transcript_standard_v1`, cleaner_version 1.0 — ruby
stripped to plain text, no furigana, then through the normal Jprogram
intake.

Kept here for reference — the original request and spec, as agreed:

Original request (confirmed needed 2026-08-08 by Owner): the Nihongo
Jikan library (`D:\Nihongo Jikan media\Transcripts\`) is raw HTML
fragments with furigana annotations (`<ruby>漢字<rt>かんじ</rt></ruby>`),
**no timestamps** — a genuinely different intake format from Natural
Japanese's timed `.vtt` subtitles. The "transcript-cleanup pass" had been
noted in Content Collection (`LIBRARY_STATUS.md`) but never started; this
was that pass, scoped as Jprogram-side intake work.

**Cleaner spec (Owner-confirmed 2026-08-08):** strip `<ruby>`/`<rt>` markup
to plain text — **no furigana kept**. Owner reads deliberately without
furigana ("the hard way"), so the corpus text must match what he actually
reads; furigana must not be treated as part of the consumed text.
Sentence-per-`<p>`, no timing alignment (none exists on the site).

**Data note for ingest:** 22 videos (ids 882, 888, 891-914) have no
transcript published on the site at all — genuinely absent, not an
extraction bug; worth a periodic recheck in case the site adds them.
