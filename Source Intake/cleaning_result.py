#!/usr/bin/env python3
"""
cleaning_result.py

Japanese Corpus Pipeline - Cleaning Result artifact writer (utility layer)

Owns ONLY Cleaning Result artifact creation.

Allowed:
- build cleaning result JSON from supplied data
- validate using schemas.py
- write cleaning result JSON atomically (UTF-8, ensure_ascii=False, sort_keys=True)

Does:
- create Cleaning Results\\<source_id>.cleaning_result.json (at the caller path)

Does NOT:
- run cleaners, inspect raw files, calculate cleaning statistics, update
  the Source Registry, create cleaning jobs, or know about downstream stages.
"""

import json
import os
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

import schemas


class CleaningResultError(Exception):
    """Raised when a Cleaning Result artifact cannot be built or written."""


def build_result(source_id, success, cleaned_artifact, statistics, errors,
                 cleaner_version=None, completion_time=None,
                 output_hash=None):
    """
    Build a Cleaning Result dict.

    Input: the five required fields plus optional fields.
    Output: a dict (with schema_version "1") ready for validation/writing.
    """
    result = {
        "schema_version": schemas.schema_version("cleaning_result"),
        "source_id": source_id,
        "success": success,
        "cleaned_artifact": cleaned_artifact,
        "statistics": statistics,
        "errors": errors,
    }
    if cleaner_version is not None:
        result["cleaner_version"] = cleaner_version
    if completion_time is not None:
        result["completion_time"] = completion_time
    if output_hash is not None:
        result["output_hash"] = output_hash
    return result


def validate_result(result):
    """
    Validate a Cleaning Result dict against its schema.

    Input: result (dict).
    Output: a list of error strings (empty when valid).
    """
    return schemas.validate("cleaning_result", result)


def write_result(path, result):
    """
    Validate and atomically write a Cleaning Result artifact.

    Input:
        path: destination file path
            (Cleaning Results\\<source_id>.cleaning_result.json).
        result: the cleaning result dict (see build_result).

    Output:
        None.

    Raises:
        CleaningResultError if schema validation fails or the write fails.
    """
    errors = schemas.validate("cleaning_result", result)
    if errors:
        raise CleaningResultError("; ".join(errors))

    _write_atomic(path, result)


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


__all__ = [
    "build_result",
    "validate_result",
    "write_result",
    "CleaningResultError",
]
