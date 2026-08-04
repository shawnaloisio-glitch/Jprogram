#!/usr/bin/env python3
"""
cleaning_job.py

Japanese Corpus Pipeline - Source Intake (artifact writer layer)

Owns ONLY Cleaning Job artifact creation.

Allowed:
- build cleaning job JSON from supplied data
- validate using schemas.py
- write cleaning job JSON atomically (UTF-8, ensure_ascii=False, sort_keys=True)

Does:
- create Cleaning Jobs\\<source_id>.cleaning_job.json (at the caller path)

Does NOT:
- create registry entries, calculate hashes, generate source IDs, execute
  cleaners, or modify the Source Registry.
"""

import json
import os
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

import schemas


class CleaningJobError(Exception):
    """Raised when a Cleaning Job artifact cannot be built or written."""


def build_job(source_id, raw_path, source_type, cleaning_profile,
              cleaner_version, output_path):
    """
    Build a Cleaning Job dict.

    Input: the six required fields.
    Output: a dict (with schema_version "1") ready for validation/writing.
    """
    return {
        "schema_version": schemas.schema_version("cleaning_job"),
        "source_id": source_id,
        "raw_path": raw_path,
        "source_type": source_type,
        "cleaning_profile": cleaning_profile,
        "cleaner_version": cleaner_version,
        "output_path": output_path,
    }


def write_job(path, job):
    """
    Validate and atomically write a Cleaning Job artifact.

    Input:
        path: destination file path (Cleaning Jobs\\<source_id>.cleaning_job.json).
        job: the cleaning job dict (see build_job).

    Output:
        None.

    Raises:
        CleaningJobError if schema validation fails or the write fails.
    """
    errors = schemas.validate("cleaning_job", job)
    if errors:
        raise CleaningJobError("; ".join(errors))

    _write_atomic(path, job)


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


__all__ = ["build_job", "write_job", "CleaningJobError"]
