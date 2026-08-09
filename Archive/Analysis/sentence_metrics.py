#!/usr/bin/env python3
"""
sentence_metrics.py

Japanese Corpus Pipeline - Analyzer

Sentence-level structural measurements of the canonical corpus.

For each sentence record, measures structural properties only:
- character_count (len of sentence text)
- word_count
- chunk_count
- expression_count
- chunks_per_word
- expressions_per_word

Plus corpus-level totals and grouped counts by source and by section.

It does NOT judge difficulty, create learning levels, make
recommendations, classify grammar, call LLM/API, or modify corpus
records. No subjective difficulty scores.

Deterministic processing requirements:
    - Pure function of canonical records: identical input -> identical output.
    - No randomness, no time/locale dependence, no LLM calls.
    - Mechanical measurements only; no subjective difficulty scores.
"""

import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

PROGRAM_NAME = "sentence_metrics"


def analyze(records):
    """
    Compute sentence-level metrics and corpus-level summaries.

    Expected input:
        records: iterable of canonical corpus records (from
        corpus_loader), each with text, words, chunks, expressions,
        ids.sentence_id, section, and provenance.source.

    Expected output:
        Structured dict suitable for output_writer:
            {
                "sentences": [ {source, section, sentence_id, metrics} ... ],
                "summary": {
                    "total_sentences": int,
                    "total_words": int,
                    "total_characters": int,
                    "total_chunks": int,
                    "total_expressions": int,
                    "average_characters_per_word": float | null,
                },
                "by_source": { <source>: {sentences, words, characters,
                                          chunks, expressions} },
                "by_section": [ {source, section, sentences, words,
                                 characters, chunks, expressions} ... ],
            }

    Canonical sentence order is preserved. Density values are raw floats
    (or null when a sentence has zero words). Output is deterministic;
    corpus records are never modified.
    """
    sentences = []
    totals = {"words": 0, "characters": 0, "chunks": 0, "expressions": 0}
    source_totals = {}
    section_totals = {}

    for record in records:
        provenance = record.get("provenance") or {}
        source = provenance.get("source")
        section = record.get("section")
        ids = record.get("ids") or {}
        sentence_id = ids.get("sentence_id")
        text = record.get("text") or ""
        words = record.get("words") or []
        chunks = record.get("chunks") or []
        expressions = record.get("expressions") or []

        character_count = len(text)
        word_count = len(words)
        chunk_count = len(chunks)
        expression_count = len(expressions)

        chunks_per_word = (
            chunk_count / word_count if word_count else None
        )
        expressions_per_word = (
            expression_count / word_count if word_count else None
        )

        sentences.append({
            "source": source,
            "section": section,
            "sentence_id": sentence_id,
            "metrics": {
                "character_count": character_count,
                "word_count": word_count,
                "chunk_count": chunk_count,
                "expression_count": expression_count,
                "chunks_per_word": chunks_per_word,
                "expressions_per_word": expressions_per_word,
            },
        })

        totals["words"] += word_count
        totals["characters"] += character_count
        totals["chunks"] += chunk_count
        totals["expressions"] += expression_count

        st = source_totals.setdefault(source, {
            "sentences": 0, "words": 0, "characters": 0,
            "chunks": 0, "expressions": 0,
        })
        st["sentences"] += 1
        st["words"] += word_count
        st["characters"] += character_count
        st["chunks"] += chunk_count
        st["expressions"] += expression_count

        sect = section_totals.setdefault((source, section), {
            "sentences": 0, "words": 0, "characters": 0,
            "chunks": 0, "expressions": 0,
        })
        sect["sentences"] += 1
        sect["words"] += word_count
        sect["characters"] += character_count
        sect["chunks"] += chunk_count
        sect["expressions"] += expression_count

    average_characters_per_word = (
        totals["characters"] / totals["words"] if totals["words"] else None
    )

    by_source = {
        key: source_totals[key]
        for key in sorted(source_totals, key=str)
    }
    by_section = [
        {"source": key[0], "section": key[1], **section_totals[key]}
        for key in sorted(section_totals, key=lambda k: (str(k[0]), str(k[1])))
    ]

    return {
        "sentences": sentences,
        "summary": {
            "total_sentences": len(sentences),
            "total_words": totals["words"],
            "total_characters": totals["characters"],
            "total_chunks": totals["chunks"],
            "total_expressions": totals["expressions"],
            "average_characters_per_word": average_characters_per_word,
        },
        "by_source": by_source,
        "by_section": by_section,
    }


if __name__ == "__main__":
    print(f"{PROGRAM_NAME}: use analyze(records).")
