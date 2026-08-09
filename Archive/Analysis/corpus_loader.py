#!/usr/bin/env python3
"""
corpus_loader.py

Japanese Corpus Pipeline - Analyzer

Deterministic canonical JSONL reader.

This module reads the canonical sentence-per-line JSONL corpus
(paths.JSONL) in canonical record order. It is the shared input boundary
for every Analyzer utility.

Deterministic processing requirements:
    - Preserve canonical record (line) order exactly.
    - Read files in a sorted, deterministic manner.
    - Never transform, normalize, or reinterpret linguistic evidence.
    - Identical input must produce identical output.

Validation is structural and limited to loading:
    - each line must be valid JSON
    - each record must be a JSON object

No linguistic validation is performed. This module does not duplicate
Response Validator or Corpus Builder logic, and it never infers or
repairs missing fields.
"""

import json
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

PROGRAM_NAME = "corpus_loader"


class CorpusLoadError(Exception):
    """Raised when a canonical corpus file cannot be loaded."""


def load_corpus(corpus_path):
    """
    Yield canonical corpus records in canonical order.

    Expected input:
        corpus_path: path to a canonical sentence-per-line JSONL file
        (the canonical corpus produced by the Corpus Builder).

    Expected output:
        Yields one canonical record per JSONL line, preserving canonical
        record (sentence) order exactly. Records are returned as parsed
        dicts and are never modified.

    Errors:
        FileNotFoundError if the file does not exist.
        CorpusLoadError if a line is not valid JSON or a record is not a
        JSON object (reported with the offending line number).

    Determinism: file/line order is preserved exactly; identical input
    produces identical output.
    """
    path = Path(corpus_path)
    if not path.is_file():
        raise FileNotFoundError(f"corpus file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, ValueError) as ex:
                raise CorpusLoadError(
                    f"invalid JSON at line {line_number}: {ex}"
                ) from ex
            if not isinstance(record, dict):
                raise CorpusLoadError(
                    f"malformed record at line {line_number}: "
                    f"expected a JSON object, got "
                    f"{type(record).__name__}"
                )
            yield record


def load_all(corpus_path):
    """
    Load every canonical record into a list.

    Expected input:
        corpus_path: path to a canonical JSONL file.

    Expected output:
        A list of canonical records in canonical order.

    Errors:
        Same as load_corpus.
    """
    return list(load_corpus(corpus_path))


if __name__ == "__main__":
    print(f"{PROGRAM_NAME}: use load_corpus / load_all.")
