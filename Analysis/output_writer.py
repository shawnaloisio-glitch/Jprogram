#!/usr/bin/env python3
"""
output_writer.py

Japanese Corpus Pipeline - Analyzer

Deterministic derived-data writer.

Writes Analyzer structured data products to the Analysis outputs folder.

Outputs must be:
- deterministic (byte-for-byte reproducible for identical input)
- traceable to canonical IDs
- UTF-8 encoded
- reproducible across repeated runs
- suitable for later AI interpretation

Only derived analysis data is written. No interpretation or
recommendation fields are created, and no corpus records are modified.

Deterministic processing requirements:
    - UTF-8 encoding; newline-delimited JSON for JSONL output.
    - Stable key ordering (sort_keys); ensure_ascii=False.
    - Byte-for-byte reproducible for identical input.
    - Overwrite existing output deterministically.
    - No recommendations or conclusions written.
"""

import json
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

from common import ensure_folder

PROGRAM_NAME = "output_writer"


class OutputWriteError(Exception):
    """Raised when an analyzer data product cannot be written."""


def write_json(output_path, data):
    """
    Write one structured data product as UTF-8 JSON.

    Expected input:
        output_path: destination file path (under Analysis outputs).
        data: the structured data product (dict/list).

    Expected output:
        None. Writes the data deterministically: UTF-8, ensure_ascii=False
        (Japanese preserved), sort_keys=True (stable key ordering),
        readable indentation. Existing output is overwritten.

    Errors:
        OutputWriteError if the data cannot be serialized or the file
        cannot be written.
    """
    path = Path(output_path)
    ensure_folder(path.parent)
    try:
        text = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=4)
        path.write_text(text + "\n", encoding="utf-8")
    except (TypeError, ValueError) as ex:
        raise OutputWriteError(f"data is not serializable: {ex}") from ex
    except OSError as ex:
        raise OutputWriteError(f"cannot write {path}: {ex}") from ex


def write_jsonl(output_path, records):
    """
    Write structured records as UTF-8 newline-delimited JSON.

    Expected input:
        output_path: destination file path.
        records: iterable of structured records.

    Expected output:
        None. Writes one record per line, in input order, deterministically:
        UTF-8, ensure_ascii=False, sort_keys=True. Existing output is
        overwritten.

    Errors:
        OutputWriteError if a record cannot be serialized (with the record
        index) or the file cannot be written.
    """
    path = Path(output_path)
    ensure_folder(path.parent)
    index = 0
    try:
        with path.open("w", encoding="utf-8") as file:
            for index, record in enumerate(records):
                line = json.dumps(record, ensure_ascii=False, sort_keys=True)
                file.write(line + "\n")
    except (TypeError, ValueError) as ex:
        raise OutputWriteError(
            f"record {index} is not serializable: {ex}"
        ) from ex
    except OSError as ex:
        raise OutputWriteError(f"cannot write {path}: {ex}") from ex


if __name__ == "__main__":
    print(f"{PROGRAM_NAME}: use write_json / write_jsonl.")
