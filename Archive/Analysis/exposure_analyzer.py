#!/usr/bin/env python3
"""
exposure_analyzer.py

Japanese Corpus Pipeline - Analyzer

Vocabulary exposure analysis.

Produces deterministic corpus exposure evidence datasets from canonical
word records. For each lexical item, tracks the full encounter history:
first occurrence, total occurrences, encounter counts across sentences /
sources / sections, surface variations, ordered occurrence locations,
and spacing between encounters.

IMPORTANT BOUNDARY:
Exposure is NOT learning status, known/unknown classification,
vocabulary importance, difficulty, I+1 analysis, or recommendation.
Those decisions belong to the later AI interpretation layer. This module
never infers acquisition or assigns learning levels.

Deterministic processing requirements:
    - Pure function of canonical records: identical input -> identical output.
    - No randomness, no time/locale dependence, no LLM calls.
    - Never determines learning status, difficulty, importance, or I+1.
"""

import statistics
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

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
    Compute exposure metrics for lexical items.

    Expected input:
        records: iterable of canonical corpus records (from
        corpus_loader), each with a "words" list of canonical word
        records [index, surface, lexical, char_start, char_end], plus
        ids.sentence_id, section, and provenance.source.

    Grouping key:
        word.lexical primary; surface fallback when lexical is empty.

    Word-index position:
        The global word index is the canonical word ordinal in record
        order.

    Expected output:
        Structured dict suitable for output_writer:
            {
                "exposure": { <lexical>: {
                    "occurrences": int,
                    "sentences": int,
                    "sources": int,
                    "sections": int,
                    "first_seen": {source, section, sentence_id,
                                   word_position, global_word_index},
                    "surfaces": { <surface>: int, ... },
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
            key = lexical if isinstance(lexical, str) and lexical else surface

            entry = items.setdefault(key, {
                "occurrences": 0,
                "sentences": set(),
                "sources": set(),
                "sections": set(),
                "first_seen": None,
                "surfaces": {},
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
            entry["surfaces"][surface] = entry["surfaces"].get(surface, 0) + 1
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
            "first_seen": entry["first_seen"],
            "surfaces": {
                surface: entry["surfaces"][surface]
                for surface in sorted(entry["surfaces"])
            },
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
