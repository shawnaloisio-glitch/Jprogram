#!/usr/bin/env python3
"""
frequency_analyzer.py

Language Coach - Analysis tools.

Isolated copy, adapted from Jprogram's Analysis/frequency_analyzer.py
(2026-08-07) - not a live import. See corpus_loader.py for the boundary
note.

**Adapted for surface-form grouping (design spec §8a, confirmed
2026-08-07):** Jprogram's original groups by lemma primary, falling back
to surface only when lemma is null. Language Coach groups by **surface
form directly** instead - different inflected/conjugated forms are
tracked as distinct items, per Owner's decision that the success metric
is content consumption, not abstract vocabulary/grammar knowledge.

Frequency analysis. Produces deterministic frequency evidence datasets
from the canonical corpus: for each surface form, the total occurrence
count and the number of sentences, sources, and sections that contain it.

Mechanical measurements only. No interpretation, ranking, difficulty,
recommendation, or classification. No LLM calls. No corpus records are
modified.

Deterministic processing requirements:
    - Pure function of canonical records: identical input -> identical output.
    - No randomness, no time/locale dependence, no LLM calls.
    - Every derived value must be traceable to canonical IDs.
    - Reports frequency only; never importance, difficulty, or ranking.
"""

PROGRAM_NAME = "frequency_analyzer"


def analyze(records):
    """
    Compute frequency and coverage for surface-form items.

    Expected input:
        records: iterable of canonical corpus records (from
        corpus_loader), each with a "words" list of canonical word
        records [index, surface, lexical, char_start, char_end], plus
        ids.sentence_id, section, and provenance.source.

    Grouping key:
        The word record's "surface" (occurrence) form - not lemma. See
        module docstring for why this differs from Jprogram's original.

    Distinct-counting semantics:
        - sentences: distinct (source, sentence_id)
        - sources: distinct provenance.source
        - sections: distinct (source, section)

    Expected output:
        Structured dict suitable for output_writer:
            {
                "frequency": { <surface>: {
                    "occurrences": int,
                    "sentences": int,
                    "sources": int,
                    "sections": int,
                    "lexical": <lexical form, or null>,
                }, ... },
                "summary": {
                    "distinct_surface_forms": int,
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
            key = surface

            item = items.setdefault(key, {
                "occurrences": 0,
                "sentences": set(),
                "sources": set(),
                "sections": set(),
                "lexical": lexical,
            })
            item["occurrences"] += 1
            total_occurrences += 1

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
            "lexical": item["lexical"],
        }

    return {
        "frequency": frequency,
        "summary": {
            "distinct_surface_forms": len(frequency),
            "total_occurrences": total_occurrences,
            "records_processed": records_processed,
        },
    }


if __name__ == "__main__":
    print(f"{PROGRAM_NAME}: use analyze(records).")
