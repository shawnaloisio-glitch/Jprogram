#!/usr/bin/env python3
"""
corpus_builder_result.py

Japanese Corpus Pipeline - Corpus Builder Result artifact writer (utility layer)

Owns ONLY Corpus Builder Result artifact creation.

Allowed:
- build corpus builder result JSON from supplied data
- validate using its own schema definition
- write corpus builder result JSON atomically (UTF-8, ensure_ascii=False, sort_keys=True)

Does:
- create Data Processor\\Corpus Results\\<source_id>.corpus_builder_result.json
  (at the caller path)

Does NOT:
- build the corpus, read request/response files, call the Response
  Validator, scan folders, call APIs, modify the Source Registry, or
  know about downstream stages.
"""

import json
import os
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

SCHEMA_VERSION = "1"

REQUIRED = {
    "source_id": "string",
    "success": "bool",
    "jobs_processed": "int",
    "jobs_failed": "int",
    "records_written": "int",
    "verified": "bool",
    "output_file": "string_or_null",
    "errors": "list",
}

OPTIONAL = {
    "completion_time": "string",
}


class CorpusBuilderResultError(Exception):
    """Raised when a Corpus Builder Result artifact cannot be built or written."""


def _matches_type(field_type, value):
    if field_type == "string":
        return isinstance(value, str) and value != ""
    if field_type == "string_or_null":
        return value is None or (isinstance(value, str) and value != "")
    if field_type == "bool":
        return isinstance(value, bool)
    if field_type == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if field_type == "list":
        return isinstance(value, list)
    return False


def validate_result(result):
    """
    Validate a Corpus Builder Result dict against its schema.

    Input: result (dict).
    Output: a list of error strings (empty when valid).
    """
    if not isinstance(result, dict):
        return [
            "corpus_builder_result: expected a JSON object, "
            f"got {type(result).__name__}"
        ]

    errors = []

    if result.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            "corpus_builder_result: schema_version mismatch "
            f"(expected {SCHEMA_VERSION!r}, got {result.get('schema_version')!r})"
        )

    for field, field_type in sorted(REQUIRED.items()):
        if field not in result:
            errors.append(
                f"corpus_builder_result: missing required field '{field}'"
            )
            continue
        if not _matches_type(field_type, result[field]):
            errors.append(
                f"corpus_builder_result: field '{field}' has invalid value "
                f"({result[field]!r})"
            )

    for field, field_type in sorted(OPTIONAL.items()):
        if field not in result:
            continue
        if not _matches_type(field_type, result[field]):
            errors.append(
                f"corpus_builder_result: optional field '{field}' has invalid "
                f"value ({result[field]!r})"
            )

    return errors


def build_result(source_id, success, jobs_processed, jobs_failed,
                 records_written, verified, output_file, errors,
                 completion_time=None):
    """
    Build a Corpus Builder Result dict.

    Input: the required fields plus optional completion_time.
    Output: a dict (with schema_version) ready for validation/writing.
    """
    result = {
        "schema_version": SCHEMA_VERSION,
        "source_id": source_id,
        "success": success,
        "jobs_processed": jobs_processed,
        "jobs_failed": jobs_failed,
        "records_written": records_written,
        "verified": verified,
        "output_file": output_file,
        "errors": errors,
    }
    if completion_time is not None:
        result["completion_time"] = completion_time
    return result


def write_result(path, result):
    """
    Validate and atomically write a Corpus Builder Result artifact.

    Input:
        path: destination file path
            (Data Processor\\Corpus Results\\<source_id>.corpus_builder_result.json).
        result: the corpus builder result dict (see build_result).

    Output:
        None.

    Raises:
        CorpusBuilderResultError if schema validation fails or the write fails.
    """
    errors = validate_result(result)
    if errors:
        raise CorpusBuilderResultError("; ".join(errors))

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
    "SCHEMA_VERSION",
    "build_result",
    "validate_result",
    "write_result",
    "CorpusBuilderResultError",
]
