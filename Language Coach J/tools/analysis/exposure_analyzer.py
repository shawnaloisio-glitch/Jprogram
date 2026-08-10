#!/usr/bin/env python3
"""
exposure_analyzer.py

Language Coach - Analysis tools.

Isolated copy, adapted from Jprogram's Analysis/exposure_analyzer.py
(2026-08-07) - not a live import. See corpus_loader.py for the boundary
note.

**Adapted for surface-form grouping (design spec §8a)** - see
frequency_analyzer.py for the full rationale.

Vocabulary exposure analysis. For each surface form, tracks the full
encounter history: first occurrence, total occurrences, encounter counts
across sentences/sources/sections, ordered occurrence locations, and
spacing between encounters.

IMPORTANT BOUNDARY:
Exposure is NOT learning status, known/unknown classification,
vocabulary importance, difficulty, I+1 analysis, or recommendation.
Those determinations belong to the value-criteria layer (design spec §9),
never to this module. This module never infers acquisition or assigns
learning levels.

Deterministic processing requirements:
    - Pure function of canonical records: identical input -> identical output.
    - No randomness, no time/locale dependence, no LLM calls.
    - Never determines learning status, difficulty, importance, or I+1.
"""

import statistics

PROGRAM_NAME = "exposure_analyzer"


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
    Compute exposure metrics for surface-form items.

    Expected input:
        records: iterable of canonical corpus records (from
        corpus_loader), each with a "words" list of canonical word
        records [index, surface, lexical, char_start, char_end], plus
        ids.sentence_id, section, and provenance.source.

    Grouping key:
        The word record's "surface" form - see frequency_analyzer.py.

    Word-index position:
        The global word index is the canonical word ordinal in record
        order.

    Expected output:
        Structured dict suitable for output_writer:
            {
                "exposure": { <surface>: {
                    "occurrences": int,
                    "sentences": int,
                    "sources": int,
                    "sections": int,
                    "lexical": <lexical form, or null>,
                    "first_seen": {source, section, sentence_id,
                                   word_position, global_word_index},
                    "locations": [ {source, section, sentence_id,
                                    word_position, global_word_index}, ... ],
                    "distribution": {
                        "word_distance": {...stats},
                        "sentence_distance": {...stats},
                    },
                }, ... },
                "summary": {
                    "distinct_items": int,
                    "total_occurrences": int,
                    "records_processed": int,
                },
            }

    Canonical order is preserved; keys are deterministically sorted.
    Corpus records are never modified.
    """
    items = {}
    records_processed = 0
    global_word_index = 0
    global_sentence_index = 0

    for record in records:
        records_processed += 1
        provenance = record.get("provenance") or {}
        source = provenance.get("source")
        section = record.get("section")
        ids = record.get("ids") or {}
        sentence_id = ids.get("sentence_id")

        for word_position, word in enumerate(record.get("words") or []):
            surface = word[1]
            lexical = word[2]
            key = surface

            entry = items.setdefault(key, {
                "occurrences": 0,
                "sentences": set(),
                "sources": set(),
                "sections": set(),
                "lexical": lexical,
                "first_seen": None,
                "locations": [],
                "word_gaps": [],
                "sentence_gaps": [],
                "last_word": None,
                "last_sentence": None,
            })

            location = {
                "source": source,
                "section": section,
                "sentence_id": sentence_id,
                "word_position": word_position,
                "global_word_index": global_word_index,
            }

            if entry["occurrences"] == 0:
                entry["first_seen"] = dict(location)

            entry["occurrences"] += 1
            if source is not None:
                entry["sentences"].add((source, sentence_id))
                entry["sources"].add(source)
                entry["sections"].add((source, section))
            entry["locations"].append(location)

            if entry["last_word"] is not None:
                entry["word_gaps"].append(
                    global_word_index - entry["last_word"]
                )
                entry["sentence_gaps"].append(
                    global_sentence_index - entry["last_sentence"]
                )
            entry["last_word"] = global_word_index
            entry["last_sentence"] = global_sentence_index
            global_word_index += 1

        global_sentence_index += 1

    exposure = {}
    for key in sorted(items):
        entry = items[key]
        exposure[key] = {
            "occurrences": entry["occurrences"],
            "sentences": len(entry["sentences"]),
            "sources": len(entry["sources"]),
            "sections": len(entry["sections"]),
            "lexical": entry["lexical"],
            "first_seen": entry["first_seen"],
            "locations": entry["locations"],
            "distribution": {
                "word_distance": _stats(entry["word_gaps"]),
                "sentence_distance": _stats(entry["sentence_gaps"]),
            },
        }

    total_occurrences = sum(
        entry["occurrences"] for entry in items.values()
    )

    return {
        "exposure": exposure,
        "summary": {
            "distinct_items": len(exposure),
            "total_occurrences": total_occurrences,
            "records_processed": records_processed,
        },
    }


if __name__ == "__main__":
    print(f"{PROGRAM_NAME}: use analyze(records).")
