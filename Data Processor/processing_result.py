#!/usr/bin/env python3
"""
processing_result.py

Japanese Corpus Pipeline - Processing Result artifact writer (utility layer)

Owns ONLY Processing Result artifact creation.

Allowed:
- build processing result JSON from supplied data
- validate using its own schema definition
- write processing result JSON atomically (UTF-8, ensure_ascii=False, sort_keys=True)

Does:
- create Processing Results\\<source_id>.processing_result.json
  (at the caller path)

Does NOT:
- send API requests, read request files, interpret parser content,
  calculate cost, scan folders, modify the Source Registry, or know
  about downstream stages.
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
    "model": "string",
    "requests_processed": "int",
    "jobs": "list",
    "totals": "dict",
}

OPTIONAL = {
    "completion_time": "string",
}

JOB_REQUIRED = {
    "request_id": "string",
    "job_number": "int",
    "status": "string",
    "prompt_tokens": "int_or_null",
    "completion_tokens": "int_or_null",
    "total_tokens": "int_or_null",
    "finish_reason": "string_or_null",
    "attempts": "int",
    "http_status": "int_or_null",
    "timestamp": "string",
}

TOTALS_REQUIRED = {
    "prompt_tokens": "int",
    "completion_tokens": "int",
    "total_tokens": "int",
}


class ProcessingResultError(Exception):
    """Raised when a Processing Result artifact cannot be built or written."""


def _matches_type(field_type, value):
    if field_type == "string":
        return isinstance(value, str) and value != ""
    if field_type == "string_or_null":
        return value is None or (isinstance(value, str) and value != "")
    if field_type == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if field_type == "int_or_null":
        return value is None or (isinstance(value, int) and not isinstance(value, bool))
    if field_type == "list":
        return isinstance(value, list)
    if field_type == "dict":
        return isinstance(value, dict)
    return False


def _validate_dict_fields(fields, prefix, data):
    errors = []
    for field, field_type in sorted(fields.items()):
        if field not in data:
            errors.append(f"{prefix} missing required field '{field}'")
            continue
        if not _matches_type(field_type, data[field]):
            errors.append(
                f"{prefix} field '{field}' has invalid value ({data[field]!r})"
            )
    return errors


def validate_result(result):
    """
    Validate a Processing Result dict against its schema.

    Input: result (dict).
    Output: a list of error strings (empty when valid).
    """
    if not isinstance(result, dict):
        return [
            "processing_result: expected a JSON object, "
            f"got {type(result).__name__}"
        ]

    errors = []

    if result.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            "processing_result: schema_version mismatch "
            f"(expected {SCHEMA_VERSION!r}, got {result.get('schema_version')!r})"
        )

    errors.extend(_validate_dict_fields(REQUIRED, "processing_result", result))

    for field, field_type in sorted(OPTIONAL.items()):
        if field not in result:
            continue
        if not _matches_type(field_type, result[field]):
            errors.append(
                f"processing_result: optional field '{field}' has invalid "
                f"value ({result[field]!r})"
            )

    jobs = result.get("jobs")
    if isinstance(jobs, list):
        for index, job in enumerate(jobs):
            if not isinstance(job, dict):
                errors.append(f"processing_result: jobs[{index}] must be a dict")
                continue
            errors.extend(
                _validate_dict_fields(
                    JOB_REQUIRED, f"processing_result: jobs[{index}]", job
                )
            )

    totals = result.get("totals")
    if isinstance(totals, dict):
        errors.extend(
            _validate_dict_fields(
                TOTALS_REQUIRED, "processing_result: totals", totals
            )
        )

    return errors


def build_result(source_id, model, requests_processed, jobs, totals,
                 completion_time=None):
    """
    Build a Processing Result dict.

    Input: the required fields plus optional completion_time.
    Output: a dict (with schema_version) ready for validation/writing.
    """
    result = {
        "schema_version": SCHEMA_VERSION,
        "source_id": source_id,
        "model": model,
        "requests_processed": requests_processed,
        "jobs": jobs,
        "totals": totals,
    }
    if completion_time is not None:
        result["completion_time"] = completion_time
    return result


def build_job_entry(request_id, job_number, status, prompt_tokens,
                    completion_tokens, total_tokens, finish_reason,
                    attempts, http_status, timestamp):
    """
    Build one job entry dict for the processing result.

    Input: the ten job fields.
    Output: a dict matching the JOB_REQUIRED schema.
    """
    return {
        "request_id": request_id,
        "job_number": job_number,
        "status": status,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "finish_reason": finish_reason,
        "attempts": attempts,
        "http_status": http_status,
        "timestamp": timestamp,
    }


def build_totals(prompt_tokens, completion_tokens, total_tokens):
    """
    Build the totals dict for the processing result.

    Input: three non-negative integer sums.
    Output: a dict matching the TOTALS_REQUIRED schema.
    """
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def write_result(path, result):
    """
    Validate and atomically write a Processing Result artifact.

    Input:
        path: destination file path
            (Processing Results\\<source_id>.processing_result.json).
        result: the processing result dict (see build_result).

    Output:
        None.

    Raises:
        ProcessingResultError if schema validation fails or the write fails.
    """
    errors = validate_result(result)
    if errors:
        raise ProcessingResultError("; ".join(errors))

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
    "build_job_entry",
    "build_totals",
    "validate_result",
    "write_result",
    "ProcessingResultError",
]
