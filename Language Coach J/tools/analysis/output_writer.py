#!/usr/bin/env python3
"""
output_writer.py

Language Coach - Analysis tools.

Isolated copy, adapted from Jprogram's Analysis/output_writer.py
(2026-08-07) - not a live import. `ensure_folder` is inlined here rather
than imported from Jprogram's common.py, to keep this module fully
self-contained with zero runtime dependency on Jprogram's code.

Deterministic derived-data writer. Writes structured data products to a
local outputs folder.

Outputs must be:
- deterministic (byte-for-byte reproducible for identical input)
- traceable to canonical IDs
- UTF-8 encoded
- reproducible across repeated runs

Only derived analysis data is written. No interpretation or
recommendation fields are created, and no corpus records are modified.
"""

import json
from pathlib import Path

PROGRAM_NAME = "output_writer"


class OutputWriteError(Exception):
    """Raised when a data product cannot be written."""


def ensure_folder(folder):
    """Create a folder and any required parent folders. No-op if it exists."""
    Path(folder).mkdir(parents=True, exist_ok=True)


def write_json(output_path, data):
    """
    Write one structured data product as UTF-8 JSON.

    Expected input:
        output_path: destination file path.
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
