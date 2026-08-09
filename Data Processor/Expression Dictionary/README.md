# Expression Dictionary

Reference data for the planned deterministic expression-detection rebuild
(`Data Processor/deterministic_parser.py`'s `expressions` field, currently
always `[]` by design — see `WORKING_LIST.md`'s "Rebuild grammar-pattern
(`expressions`) detection" entry for the full blast-radius/planning
writeup). Not wired into any pipeline code yet — this is prework staging
the pattern-source data before real detection logic is built.

## Source and license

`jmdict_expressions.jsonl` is extracted directly from the **JMdict** XML
dump (the Electronic Dictionary Research and Development Group, Monash
University), already downloaded in the Reasonix/MiniLingQ project
(`Reasonix\packs\_JMdict_e.gz`, per `Reasonix/tools/make_dictionary_pack.py`).

- Original source: JMdict/EDICT — <http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz>
- License: **CC BY-SA 3.0** (Creative Commons Attribution-ShareAlike 3.0) —
  © The Electronic Dictionary Research and Development Group, Monash
  University.
- This copy is a filtered extraction, not the full dictionary: every entry
  in JMdict tagged `exp` ("expressions (phrases, clauses, etc.)") whose
  surface form is 3+ characters (JMdict's own 1-2 character `exp` entries
  are mostly noise for this purpose — particles/fragments, not genuine
  multi-word expressions). **35,633 distinct expression surfaces** survive
  that filter, parsed directly from the raw XML (not via the pre-built
  `Reasonix\packs\ja-pack.jsonl`, since that pack drops the priority/
  frequency tags this file needs — see `score` below).
- Extracted 2026-08-09 from the JMdict XML dump already present in
  `Reasonix\packs\_JMdict_e.gz` — not re-downloaded from EDRDG directly.
- **Known coverage gap, confirmed not a bug:** not every commonly-taught
  Japanese expression has its own `exp`-tagged JMdict entry. Example:
  `ということ` (extremely common in real usage) has no standalone `exp`
  entry — JMdict appears to treat it as a productive combination rather
  than a fixed idiom worth indexing. This is an honest limitation of
  JMdict-as-source, not something this extraction got wrong.

Per CC BY-SA 3.0's share-alike/attribution terms, any further redistribution
of this file (or a derivative built from it) must carry this same
attribution and license.

## Format

One JSON object per line, sorted by `(score, surface)`:

```json
{"surface": "ことにする", "reading": "ことにする", "gloss": "to decide to", "score": 0}
```

- `surface` — the dictionary/base-form expression as JMdict records it
  (**not** a conjugated surface form — e.g. `と思われる` is present,
  `と思います` is not, since JMdict entries are dictionary-form).
- `reading` — the JMdict reading.
- `gloss` — a single English gloss, kept only for human review while
  building/reviewing the pattern library; not used by any matching logic.
- `score` — JMdict's own frequency/commonness signal, lower = more common:
  a number from its `nf01`-`nf48` corpus-frequency bands when present,
  `0` for an entry flagged `ichi`/`news`/`spec`/`gai` ("common word") with
  no numeric band, or `999` when JMdict records no frequency signal at all
  for that entry. **1,338 of the 35,633 entries have a real signal**
  (score < 999) — this is the natural "smallest set first" slice for a
  phased build (see `WORKING_LIST.md`'s phased plan).

## Why base-form matching matters

Because entries are dictionary-form, matching this list against real
sentence text means comparing **lemma sequences**
(`deterministic_parser.py`'s already-computed `lexical` field per word),
not raw surface text — real sentences carry conjugated forms
(`と思います`) that won't literally appear in this file.

## Not yet used for anything

This file is reference data only. No code in this repository reads it yet.
The actual expression-detection algorithm (lemma-sequence matching +
longest-match overlap resolution) is a separate, not-yet-started, real
Coder task against the Frozen `deterministic_parser.py` — see the planning
writeup referenced above before starting that work.
