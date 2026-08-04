#!/usr/bin/env python3
"""
chunk_analyzer.py

Japanese Corpus Pipeline - Analyzer

Chunk / grammar-pattern analysis.

Produces deterministic evidence datasets from canonical corpus chunk
records [index, text, start_word, end_word].

For each chunk (grouped by its canonical text):
- occurrences
- distinct sentences / sources / sections
- occurrence locations (source, section, sentence_id, word span)
- spacing between occurrences using corpus word-index distance and
  sentence distance

IMPORTANT BOUNDARY:
Chunks are parser-provided observed segments. They are NOT grammar
rules, grammar classifications, difficulty indicators, or learning
recommendations. Grammar-pattern analysis is represented here only as
mechanical measurement of the canonical `chunks` layer. There is no
grammar parser and no particle/conjugation/verb-form/grammar
classification.

Deterministic processing requirements:
    - Pure function of canonical records: identical input -> identical output.
    - No randomness, no time/locale dependence, no LLM calls.
    - No grammar parser, no particle/conjugation/verb-form/grammar
      classification. Uses only the existing chunk evidence.
"""

import statistics
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

PROGRAM_NAME = "chunk_analyzer"


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
    Compute chunk frequency, distribution, and context locations.

    Expected input:
        records: iterable of canonical corpus records (from
        corpus_loader), each with a "chunks" list of canonical chunk
        records [index, text, start_word, end_word], a "words" list,
        ids.sentence_id, section, and provenance.source.

    Grouping key:
        chunk.text (the canonical chunk text).

    Word-index position:
        A chunk's corpus word index is the global word index of its
        start_word (the canonical word ordinal in record order).

    Expected output:
        Structured dict suitable for output_writer:
            {
                "chunks": { <chunk text>: {
                    "occurrences": int,
                    "sentences": int,
                    "sources": int,
                    "sections": int,
                    "locations": [ {source, section, sentence_id,
                                    start_word, end_word}, ... ],
                    "distribution": {
                        "word_distance": {...stats},
                        "sentence_distance": {...stats},
                    },
                }, ... },
                "summary": {
                    "distinct_chunks": int,
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

        for chunk in record.get("chunks") or []:
            text = chunk[1]
            start_word = chunk[2]
            end_word = chunk[3]
            key = text

            entry = items.setdefault(key, {
                "occurrences": 0,
                "sentences": set(),
                "sources": set(),
                "sections": set(),
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

    chunks = {}
    for key in sorted(items):
        entry = items[key]
        chunks[key] = {
            "occurrences": entry["occurrences"],
            "sentences": len(entry["sentences"]),
            "sources": len(entry["sources"]),
            "sections": len(entry["sections"]),
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
        "chunks": chunks,
        "summary": {
            "distinct_chunks": len(chunks),
            "total_occurrences": total_occurrences,
            "records_processed": records_processed,
        },
    }


if __name__ == "__main__":
    print(f"{PROGRAM_NAME}: use analyze(records).")
