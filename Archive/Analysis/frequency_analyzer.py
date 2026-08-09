#!/usr/bin/env python3
"""
frequency_analyzer.py

Japanese Corpus Pipeline - Analyzer

Frequency analysis.

Produces deterministic frequency evidence datasets from the canonical
corpus: for each lexical item, the total occurrence count and the number
of sentences, sources, and sections that contain it. Surface information
is preserved alongside each lexical item.

Mechanical measurements only. No interpretation, ranking, difficulty,
recommendation, or classification. No LLM calls. No corpus records are
modified.

Deterministic processing requirements:
    - Pure function of canonical records: identical input -> identical output.
    - No randomness, no time/locale dependence, no LLM calls.
    - Every derived value must be traceable to canonical IDs.
    - Reports frequency only; never importance, difficulty, or ranking.
"""

import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

PROGRAM_NAME = "frequency_analyzer"


def analyze(records):
    """
    Compute frequency and coverage for lexical items.

    Expected input:
        records: iterable of canonical corpus records (from
        corpus_loader), each with a "words" list of canonical word
        records [index, surface, lexical, char_start, char_end], plus
        ids.sentence_id, section, and provenance.source.

    Grouping key:
        The word record's "lexical" (dictionary/base) field is the
        primary grouping key. If "lexical" is null/empty, the word is
        grouped by its "surface" (occurrence) form.

    Distinct-counting semantics:
        - sentences: distinct (source, sentence_id)
        - sources: distinct provenance.source
        - sections: distinct (source, section)

    Expected output:
        Structured dict suitable for output_writer:
            {
                "frequency": { <lexical>: {
                    "occurrences": int,
                    "sentences": int,
                    "sources": int,
                    "sections": int,
                    "surfaces": { <surface>: int, ... },
                }, ... },
                "summary": {
                    "distinct_lexical_items": int,
                    "total_occurrences": int,
                    "records_processed": int,
                },
            }

    Keys are deterministically sorted. Frequency alone is insufficient
    (distribution is measured separately).
    """
    items = {}
    records_processed = 0
    total_occurrences = 0

    for record in records:
        records_processed += 1
        provenance = record.get("provenance") or {}
        source = provenance.get("source")
        section = record.get("section")
        ids = record.get("ids") or {}
        sentence_id = ids.get("sentence_id")

        for word in record.get("words") or []:
            surface = word[1]
            lexical = word[2]
            key = lexical if isinstance(lexical, str) and lexical else surface

            item = items.setdefault(key, {
                "occurrences": 0,
                "sentences": set(),
                "sources": set(),
                "sections": set(),
                "surfaces": {},
            })
            item["occurrences"] += 1
            total_occurrences += 1
            item["surfaces"][surface] = item["surfaces"].get(surface, 0) + 1

            if source is not None:
                item["sources"].add(source)
                item["sentences"].add((source, sentence_id))
                item["sections"].add((source, section))

    frequency = {}
    for key in sorted(items):
        item = items[key]
        frequency[key] = {
            "occurrences": item["occurrences"],
            "sentences": len(item["sentences"]),
            "sources": len(item["sources"]),
            "sections": len(item["sections"]),
            "surfaces": {
                surface: item["surfaces"][surface]
                for surface in sorted(item["surfaces"])
            },
        }

    return {
        "frequency": frequency,
        "summary": {
            "distinct_lexical_items": len(frequency),
            "total_occurrences": total_occurrences,
            "records_processed": records_processed,
        },
    }


if __name__ == "__main__":
    print(f"{PROGRAM_NAME}: use analyze(records).")
