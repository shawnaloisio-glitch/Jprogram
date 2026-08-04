#!/usr/bin/env python3
"""
registry.py

Japanese Corpus Pipeline - Source Intake (artifact writer layer)

Owns ONLY Source Registry artifact creation.

Allowed:
- build registry JSON from supplied data
- validate using schemas.py
- write registry JSON atomically (UTF-8, ensure_ascii=False, sort_keys=True)

Does:
- create Source Registry\\<source_id>.json (at the caller-supplied path)

Does NOT:
- generate source_id, calculate hashes, check duplicates, select cleaning
  profiles, call cleaners, create cleaning jobs, or modify other artifacts.
"""

import json
import os
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

import schemas


class RegistryError(Exception):
    """Raised when a Source Registry artifact cannot be built or written."""


def build_entry(source_id, original_filename, sha256, source_type, format,
                language, cleaning_profile, cleaner_version):
    """
    Build a Source Registry entry dict.

    Input: the eight required identity/classification/processing fields.
    Output: a dict (with schema_version "1") ready for validation/writing.
    """
    return {
        "schema_version": schemas.schema_version("registry"),
        "source_id": source_id,
        "original_filename": original_filename,
        "sha256": sha256,
        "source_type": source_type,
        "format": format,
        "language": language,
        "cleaning_profile": cleaning_profile,
        "cleaner_version": cleaner_version,
    }


def write_registry(path, entry):
    """
    Validate and atomically write a Source Registry artifact.

    Input:
        path: destination file path (Source Registry\\<source_id>.json).
        entry: the registry dict (see build_entry).

    Output:
        None.

    Raises:
        RegistryError if schema validation fails or the write fails.
    """
    errors = schemas.validate("registry", entry)
    if errors:
        raise RegistryError("; ".join(errors))

    _write_atomic(path, entry)


def _write_atomic(path, data):
    """
    Write JSON deterministically to a temp file and rename it into place.

    UTF-8, ensure_ascii=False, sort_keys=True, readable indentation,
    trailing newline. A crash cannot leave a partial final artifact.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (
        json.dumps(data, ensure_ascii=False, sort_keys=True, indent=4)
        + "\n"
    )
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as file:
        file.write(text)
        file.flush()
        os.fsync(file.fileno())
    temp.replace(path)


__all__ = ["build_entry", "write_registry", "RegistryError"]
