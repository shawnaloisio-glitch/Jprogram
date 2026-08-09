#!/usr/bin/env python3
"""
expression_analyzer.py

Japanese Corpus Pipeline - Analyzer

Expression analysis.

Produces deterministic evidence datasets for parser-provided
expressions, measured from the canonical expression records
[index, surface, start_word, end_word, pattern].

For each expression (grouped by pattern; surface preserved as
variations):
- total occurrences
- sentence / source / section coverage
- surface breakdown
- occurrence locations (source, section, sentence_id, word span)
- spacing between occurrences using corpus word-index distance and
  sentence distance

Mechanical measurements only. No grammar classification, grammar rules,
conjugation classification, difficulty, learning priorities, or LLM/API.

Deterministic processing requirements:
    - Pure function of canonical records: identical input -> identical output.
    - No randomness, no time/locale dependence, no LLM calls.
    - Mechanical measurements only; no importance, difficulty, or ranking.
"""

import statistics
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

PROGRAM_NAME = "expression_analyzer"


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
    Compute expression frequency, distribution, and context locations.

    Expected input:
        records: iterable of canonical corpus records (from
        corpus_loader), each with an "expressions" list of canonical
        expression records [index, surface, start_word, end_word,
        pattern], a "words" list, ids.sentence_id, section, and
        provenance.source.

    Grouping key:
        The expression's "pattern" is the primary key. If pattern is
        null/empty, the expression is grouped by its "surface".

    Word-index position:
        An expression's corpus word index is the global word index of
        its start_word (the canonical word ordinal in record order).

    Expected output:
        Structured dict suitable for output_writer:
            {
                "expressions": { <pattern>: {
                    "occurrences": int,
                    "sentences": int,
                    "sources": int,
                    "sections": int,
                    "surfaces": { <surface>: int, ... },
                    "locations": [ {source, section, sentence_id,
                                    start_word, end_word}, ... ],
                    "word_distance": {...stats},
                    "sentence_distance": {...stats},
                }, ... },
                "summary": {
                    "distinct_expressions": int,
                    "total_occurrences": int,
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

    for record in records:
        records_processed += 1
        provenance = record.get("provenance") or {}
        source = provenance.get("source")
        section = record.get("section")
        ids = record.get("ids") or {}
        sentence_id = ids.get("sentence_id")
        words = record.get("words") or []

        record_start_word = global_word_index
        global_word_index += len(words)

        for expression in record.get("expressions") or []:
            surface = expression[1]
            start_word = expression[2]
            end_word = expression[3]
            pattern = expression[4]
            key = pattern if isinstance(pattern, str) and pattern else surface

            entry = items.setdefault(key, {
                "occurrences": 0,
                "sentences": set(),
                "sources": set(),
                "sections": set(),
                "surfaces": {},
                "locations": [],
                "word_gaps": [],
                "sentence_gaps": [],
                "last_word": None,
                "last_sentence": None,
            })

            word_index = record_start_word + start_word
            location = {
                "source": source,
                "section": section,
                "sentence_id": sentence_id,
                "start_word": start_word,
                "end_word": end_word,
            }

            entry["occurrences"] += 1
            entry["surfaces"][surface] = entry["surfaces"].get(surface, 0) + 1
            if source is not None:
                entry["sentences"].add((source, sentence_id))
                entry["sources"].add(source)
                entry["sections"].add((source, section))
            entry["locations"].append(location)

            if entry["last_word"] is not None:
                entry["word_gaps"].append(word_index - entry["last_word"])
                entry["sentence_gaps"].append(
                    global_sentence_index - entry["last_sentence"]
                )
            entry["last_word"] = word_index
            entry["last_sentence"] = global_sentence_index

        global_sentence_index += 1

    expressions = {}
    for key in sorted(items):
        entry = items[key]
        expressions[key] = {
            "occurrences": entry["occurrences"],
            "sentences": len(entry["sentences"]),
            "sources": len(entry["sources"]),
            "sections": len(entry["sections"]),
            "surfaces": {
                surface: entry["surfaces"][surface]
                for surface in sorted(entry["surfaces"])
            },
            "locations": entry["locations"],
            "word_distance": _stats(entry["word_gaps"]),
            "sentence_distance": _stats(entry["sentence_gaps"]),
        }

    total_occurrences = sum(
        entry["occurrences"] for entry in items.values()
    )

    return {
        "expressions": expressions,
        "summary": {
            "distinct_expressions": len(expressions),
            "total_occurrences": total_occurrences,
            "records_processed": records_processed,
        },
    }


if __name__ == "__main__":
    print(f"{PROGRAM_NAME}: use analyze(records).")
