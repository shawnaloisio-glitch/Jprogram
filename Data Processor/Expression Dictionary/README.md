# Expression Dictionary

Reference data for the planned deterministic expression-detection rebuild
(`Data Processor/deterministic_parser.py`'s `expressions` field, currently
always `[]` by design — see `WORKING_LIST.md`'s "Rebuild grammar-pattern
(`expressions`) detection" entry for the full blast-radius/planning
writeup). Not wired into any pipeline code yet — this is prework staging
the pattern-source data before real detection logic is built.

## Source and license

`jmdict_expressions.jsonl` is extracted from **JMdict** (the Electronic
Dictionary Research and Development Group, Monash University), via the copy
already built in the Reasonix/MiniLingQ project
(`Reasonix/tools/make_dictionary_pack.py`, `Reasonix/packs/ja-pack.jsonl`).

- Original source: JMdict/EDICT — <http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz>
- License: **CC BY-SA 3.0** (Creative Commons Attribution-ShareAlike 3.0) —
  © The Electronic Dictionary Research and Development Group, Monash
  University.
- This copy is a filtered extraction, not the full dictionary: every entry
  in JMdict tagged `exp` ("expressions (phrases, clauses, etc.)") whose
  surface form is 3+ characters (JMdict's own 1-2 character `exp` entries
  are mostly noise for this purpose — particles/fragments, not genuine
  multi-word expressions). **35,547 of 35,765** total `exp`-tagged entries
  survive that filter.
- Extracted 2026-08-09, directly from the already-built
  `Reasonix\packs\ja-pack.jsonl` (itself built from a JMdict download dated
  2026-08-08 per that file's own timestamp) — not re-downloaded from
  EDRDG directly.

Per CC BY-SA 3.0's share-alike/attribution terms, any further redistribution
of this file (or a derivative built from it) must carry this same
attribution and license.

## Format

One JSON object per line, sorted by `surface`:

```json
{"surface": "ということ", "reading": "ということ", "gloss": "the fact that"}
```

- `surface` — the dictionary/base-form expression as JMdict records it
  (**not** a conjugated surface form — e.g. `と思われる` is present,
  `と思います` is not, since JMdict entries are dictionary-form).
- `reading` — the JMdict reading.
- `gloss` — a single English gloss, kept only for human review while
  building/reviewing the pattern library; not used by any matching logic.

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
