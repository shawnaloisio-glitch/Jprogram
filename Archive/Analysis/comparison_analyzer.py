#!/usr/bin/env python3
"""
comparison_analyzer.py

Japanese Corpus Pipeline - Analyzer

Cross-source comparison.

Produces deterministic evidence datasets comparing two or more canonical
corpora. Measures differences between corpora only. It does NOT decide
which corpus is better, rank materials, recommend study materials, infer
difficulty, or infer learning value.

INDEPENDENCE (frozen rule):
This analyzer reads canonical corpus records directly. It never reads the
output files of frequency/distribution/exposure/expression/chunk analyzers
or sentence_metrics. The canonical corpus is its only input dependency.

Deterministic processing requirements:
    - Pure function of the input sources: identical input -> identical output.
    - Source ordering handled deterministically (sorted source names).
    - No randomness, no time/locale dependence, no LLM calls.
    - No recommendations.
"""

import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

PROGRAM_NAME = "comparison_analyzer"


def _shared_items(items, source_names):
    """Items present in every source (sorted)."""
    return sorted(
        key for key in items
        if all(source in items[key] for source in source_names)
    )


def _unique_items(items, source_names):
    """Items present only in exactly one source (per-source, sorted)."""
    return {
        source: sorted(
            key for key in items if set(items[key].keys()) == {source}
        )
        for source in source_names
    }


def analyze(sources):
    """
    Compare two or more canonical corpora.

    Expected input:
        sources: dict mapping source name -> iterable of canonical corpus
        records for that source (each source's records from
        corpus_loader). At least two sources are required.

    Grouping keys:
        - vocabulary: word.lexical primary, surface fallback
        - expressions: expression.pattern primary, surface fallback
        - chunks: chunk.text

    Expected output:
        Structured dict suitable for output_writer:
            {
                "comparison": {
                    "sources": [sorted source names],
                    "vocabulary": {
                        "shared": [...], "unique": {source: [...]},
                        "by_item": { <lexical>: {source: {
                            "occurrences": int, "surfaces": int}} } },
                    "expressions": {
                        "shared": [...], "unique": {source: [...]},
                        "by_item": { <pattern>: {source: int}} },
                    "chunks": {
                        "shared": [...], "unique": {source: [...]},
                        "by_item": { <text>: {source: int}} },
                    "sentence_metrics": {
                        "by_source": {source: {sentences, words,
                            characters, chunks, expressions}} },
                },
                "summary": {
                    "sources_compared": int,
                    "shared_vocabulary": int,
                    "total_vocabulary": int,
                    "shared_expressions": int,
                    "shared_chunks": int,
                    "records_processed": int,
                },
            }

    Ordering is deterministic; results trace back to source names.
    Corpus records are never modified.
    """
    if not isinstance(sources, dict):
        raise ValueError("sources must be a dict mapping source names to records")
    source_names = sorted(sources)
    if len(source_names) < 2:
        raise ValueError("at least two sources are required for comparison")

    vocab = {}
    exprs = {}
    chunks = {}
    structure = {}

    for source in source_names:
        struct = structure.setdefault(source, {
            "sentences": 0, "words": 0, "characters": 0,
            "chunks": 0, "expressions": 0,
        })

        for record in sources[source]:
            struct["sentences"] += 1
            words = record.get("words") or []
            chunk_list = record.get("chunks") or []
            expression_list = record.get("expressions") or []
            struct["words"] += len(words)
            struct["characters"] += len(record.get("text") or "")
            struct["chunks"] += len(chunk_list)
            struct["expressions"] += len(expression_list)

            for word in words:
                surface = word[1]
                lexical = word[2]
                key = lexical if isinstance(lexical, str) and lexical else surface
                entry = vocab.setdefault(key, {})
                per_source = entry.setdefault(source, {
                    "occurrences": 0, "surfaces": set(),
                })
                per_source["occurrences"] += 1
                per_source["surfaces"].add(surface)

            for expression in expression_list:
                surface = expression[1]
                pattern = expression[4]
                key = pattern if isinstance(pattern, str) and pattern else surface
                entry = exprs.setdefault(key, {})
                entry[source] = entry.get(source, 0) + 1

            for chunk in chunk_list:
                text = chunk[1]
                entry = chunks.setdefault(text, {})
                entry[source] = entry.get(source, 0) + 1

    vocab_by_item = {}
    for key in sorted(vocab):
        vocab_by_item[key] = {
            source: {
                "occurrences": vocab[key][source]["occurrences"],
                "surfaces": len(vocab[key][source]["surfaces"]),
            }
            for source in sorted(vocab[key])
        }

    expressions_by_item = {
        key: dict(sorted(exprs[key].items()))
        for key in sorted(exprs)
    }
    chunks_by_item = {
        key: dict(sorted(chunks[key].items()))
        for key in sorted(chunks)
    }

    return {
        "comparison": {
            "sources": source_names,
            "vocabulary": {
                "shared": _shared_items(vocab, source_names),
                "unique": _unique_items(vocab, source_names),
                "by_item": vocab_by_item,
            },
            "expressions": {
                "shared": _shared_items(exprs, source_names),
                "unique": _unique_items(exprs, source_names),
                "by_item": expressions_by_item,
            },
            "chunks": {
                "shared": _shared_items(chunks, source_names),
                "unique": _unique_items(chunks, source_names),
                "by_item": chunks_by_item,
            },
            "sentence_metrics": {
                "by_source": {source: structure[source] for source in source_names},
            },
        },
        "summary": {
            "sources_compared": len(source_names),
            "shared_vocabulary": len(_shared_items(vocab, source_names)),
            "total_vocabulary": len(vocab),
            "shared_expressions": len(_shared_items(exprs, source_names)),
            "shared_chunks": len(_shared_items(chunks, source_names)),
            "records_processed": sum(
                structure[source]["sentences"] for source in source_names
            ),
        },
    }


if __name__ == "__main__":
    print(f"{PROGRAM_NAME}: use analyze(sources).")
