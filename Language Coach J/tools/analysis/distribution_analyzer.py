#!/usr/bin/env python3
"""
distribution_analyzer.py

Language Coach - Analysis tools.

Isolated copy, adapted from Jprogram's Analysis/distribution_analyzer.py
(2026-08-07) - not a live import. See corpus_loader.py for the boundary
note.

**Adapted for surface-form grouping (design spec §8a)** - see
frequency_analyzer.py for the full rationale. Groups by surface form
directly, not lemma.

Distribution analysis. Measures how exposure to an item is distributed
through the corpus, not only totals. For each surface form, every
occurrence is tracked with its source, section, sentence id, word
position, global corpus word index, and canonical character position.
Gap statistics computed in three distance units:

    PRIMARY:   corpus word-index distance
    SECONDARY: character distance
    CONTEXT:   sentence distance

Raw measurements only - no clustering interpretation, no frequency
importance, no learning value, no I+1, no classification.

Deterministic processing requirements:
    - Pure function of canonical records: identical input -> identical output.
    - No randomness, no time/locale dependence, no LLM calls.
"""

import statistics

PROGRAM_NAME = "distribution_analyzer"


def _stats(gaps):
    """Deterministic gap statistics; a single occurrence yields None values."""
    if not gaps:
        return {
            "gap_count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "stddev": None,
        }
    return {
        "gap_count": len(gaps),
        "min": min(gaps),
        "max": max(gaps),
        "mean": sum(gaps) / len(gaps),
        "median": statistics.median(gaps),
        "stddev": statistics.pstdev(gaps),
    }


def analyze(records):
    """
    Compute exposure distribution metrics for surface-form items.

    Expected input:
        records: iterable of canonical corpus records (from
        corpus_loader), each with a "words" list of canonical word
        records [index, surface, lexical, char_start, char_end], plus
        text, ids.sentence_id, section, and provenance.source.

    Grouping key:
        The word record's "surface" form - see frequency_analyzer.py.

    Distance definitions:
        - global word index: running ordinal of every word in canonical
          record order.
        - character distance: characters between the end of the previous
          surface and the start of the next, accumulated over intervening
          canonical sentence text (line separators excluded).
        - sentence distance: difference in the global sentence ordinal
          (canonical record order), because sentence_id is per-source and
          not globally comparable.

    Expected output:
        Structured dict suitable for output_writer:
            {
                "distribution": { <surface>: {
                    "occurrences": [ {source, section, sentence_id,
                                      word_position, global_word_index,
                                      char_start, char_end}, ... ],
                    "word_distance": {...stats},
                    "character_distance": {...stats},
                    "sentence_distance": {...stats},
                }, ... },
                "summary": {
                    "distinct_items": int,
                    "occurrences_tracked": int,
                    "records_processed": int,
                },
            }

    Ordering is deterministic. Identical input produces identical output.
    Corpus records are never modified.
    """
    items = {}
    records_processed = 0
    global_word_index = 0
    global_sentence_index = 0
    corpus_char_offset = 0

    for record in records:
        records_processed += 1
        provenance = record.get("provenance") or {}
        source = provenance.get("source")
        section = record.get("section")
        ids = record.get("ids") or {}
        sentence_id = ids.get("sentence_id")
        text = record.get("text") or ""
        words = record.get("words") or []

        for word_position, word in enumerate(words):
            surface = word[1]
            key = surface

            entry = items.setdefault(key, {
                "occurrences": [],
                "word_gaps": [],
                "char_gaps": [],
                "sentence_gaps": [],
                "last_word": None,
                "last_char_end": None,
                "last_sentence": None,
            })

            occurrence = {
                "source": source,
                "section": section,
                "sentence_id": sentence_id,
                "word_position": word_position,
                "global_word_index": global_word_index,
                "char_start": word[3],
                "char_end": word[4],
            }

            if entry["last_word"] is not None:
                entry["word_gaps"].append(
                    global_word_index - entry["last_word"]
                )
                entry["char_gaps"].append(
                    (corpus_char_offset + word[3]) - entry["last_char_end"]
                )
                entry["sentence_gaps"].append(
                    global_sentence_index - entry["last_sentence"]
                )

            entry["occurrences"].append(occurrence)
            entry["last_word"] = global_word_index
            entry["last_char_end"] = corpus_char_offset + word[4]
            entry["last_sentence"] = global_sentence_index
            global_word_index += 1

        corpus_char_offset += len(text)
        global_sentence_index += 1

    distribution = {}
    for key in sorted(items):
        entry = items[key]
        distribution[key] = {
            "occurrences": entry["occurrences"],
            "word_distance": _stats(entry["word_gaps"]),
            "character_distance": _stats(entry["char_gaps"]),
            "sentence_distance": _stats(entry["sentence_gaps"]),
        }

    occurrences_tracked = sum(
        len(entry["occurrences"]) for entry in items.values()
    )

    return {
        "distribution": distribution,
        "summary": {
            "distinct_items": len(distribution),
            "occurrences_tracked": occurrences_tracked,
            "records_processed": records_processed,
        },
    }


if __name__ == "__main__":
    print(f"{PROGRAM_NAME}: use analyze(records).")
