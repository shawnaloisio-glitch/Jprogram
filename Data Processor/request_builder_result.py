#!/usr/bin/env python3
"""
request_builder_result.py

Japanese Corpus Pipeline - Request Builder Result artifact writer (utility layer)

Owns ONLY Request Builder Result artifact creation.

Allowed:
- build request builder result JSON from supplied data
- validate using its own schema definition
- write request builder result JSON atomically (UTF-8, ensure_ascii=False, sort_keys=True)

Does:
- create Data Processor\\Request Results\\<source_id>.request_builder_result.json
  (at the caller path)

Does NOT:
- build requests, read jobs, scan folders, run deepseek client, validate
  parser output, call APIs, modify the Source Registry, or know about
  downstream stages.
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
    "requests_created": "bool",
    "jobs_processed": "int",
    "errors": "list",
}

OPTIONAL = {
    "completion_time": "string",
}


class RequestBuilderResultError(Exception):
    """Raised when a Request Builder Result artifact cannot be built or written."""


def _matches_type(field_type, value):
    if field_type == "string":
        return isinstance(value, str) and value != ""
    if field_type == "bool":
        return isinstance(value, bool)
    if field_type == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if field_type == "list":
        return isinstance(value, list)
    return False


def validate_result(result):
    """
    Validate a Request Builder Result dict against its schema.

    Input: result (dict).
    Output: a list of error strings (empty when valid).
    """
    if not isinstance(result, dict):
        return [
            "request_builder_result: expected a JSON object, "
            f"got {type(result).__name__}"
        ]

    errors = []

    if result.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            "request_builder_result: schema_version mismatch "
            f"(expected {SCHEMA_VERSION!r}, got {result.get('schema_version')!r})"
        )

    for field, field_type in sorted(REQUIRED.items()):
        if field not in result:
            errors.append(
                f"request_builder_result: missing required field '{field}'"
            )
            continue
        if not _matches_type(field_type, result[field]):
            errors.append(
                f"request_builder_result: field '{field}' has invalid value "
                f"({result[field]!r})"
            )

    for field, field_type in sorted(OPTIONAL.items()):
        if field not in result:
            continue
        if not _matches_type(field_type, result[field]):
            errors.append(
                f"request_builder_result: optional field '{field}' has invalid "
                f"value ({result[field]!r})"
            )

    return errors


def build_result(source_id, success, requests_created, jobs_processed,
                 errors, completion_time=None):
    """
    Build a Request Builder Result dict.

    Input: the required fields plus optional completion_time.
    Output: a dict (with schema_version) ready for validation/writing.
    """
    result = {
        "schema_version": SCHEMA_VERSION,
        "source_id": source_id,
        "success": success,
        "requests_created": requests_created,
        "jobs_processed": jobs_processed,
        "errors": errors,
    }
    if completion_time is not None:
        result["completion_time"] = completion_time
    return result


def write_result(path, result):
    """
    Validate and atomically write a Request Builder Result artifact.

    Input:
        path: destination file path
            (Data Processor\\Request Results\\<source_id>.request_builder_result.json).
        result: the request builder result dict (see build_result).

    Output:
        None.

    Raises:
        RequestBuilderResultError if schema validation fails or the write fails.
    """
    errors = validate_result(result)
    if errors:
        raise RequestBuilderResultError("; ".join(errors))

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
    "RequestBuilderResultError",
]
