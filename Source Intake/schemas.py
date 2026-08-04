#!/usr/bin/env python3
"""
schemas.py

Japanese Corpus Pipeline - Source Intake (utility layer)

Artifact schema definitions and validation only.

Defines the frozen artifact contracts:
    - Source Registry JSON ("registry")
    - Cleaning Job JSON ("cleaning_job")
    - Cleaning Result JSON ("cleaning_result")

This module does not create artifacts, write files, or own metadata.
It is a shared utility used by artifact-creating modules.

Deterministic: identical input produces an identical validation result.
"""

import re
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


# ============================================================
# Schema definitions
# ============================================================

ARTIFACT_SCHEMAS = {
    "registry": {
        "schema_version": "1",
        "required": {
            "source_id": "string",
            "original_filename": "string",
            "sha256": "sha256",
            "source_type": "string",
            "format": "string",
            "language": "string",
            "cleaning_profile": "string",
            "cleaner_version": "string",
        },
        "optional": {
            "cleaned_artifact": "string_or_null",
            "parser_version": "string_or_null",
            "validator_version": "string_or_null",
            "canonical_corpus": "string_or_null",
        },
    },
    "cleaning_job": {
        "schema_version": "1",
        "required": {
            "source_id": "string",
            "raw_path": "string",
            "source_type": "string",
            "cleaning_profile": "string",
            "cleaner_version": "string",
            "output_path": "string",
        },
        "optional": {
            "created_by_version": "string",
            "priority": "int",
            "notes": "string",
        },
    },
    "cleaning_result": {
        "schema_version": "1",
        "required": {
            "source_id": "string",
            "success": "bool",
            "cleaned_artifact": "string_or_null",
            "statistics": "dict",
            "errors": "list",
        },
        "optional": {
            "cleaner_version": "string",
            "completion_time": "string",
            "output_hash": "string",
        },
    },
}


# ============================================================
# Validation
# ============================================================

def artifact_names():
    """Return the supported artifact schema names (sorted)."""
    return sorted(ARTIFACT_SCHEMAS)


def schema_version(name):
    """Return the schema version for an artifact name (or None)."""
    schema = ARTIFACT_SCHEMAS.get(name)
    return schema["schema_version"] if schema else None


def _matches_type(field_type, value):
    if field_type == "string":
        return isinstance(value, str) and value != ""
    if field_type == "sha256":
        return isinstance(value, str) and bool(SHA256_PATTERN.match(value))
    if field_type == "string_or_null":
        return value is None or (isinstance(value, str) and value != "")
    if field_type == "bool":
        return isinstance(value, bool)
    if field_type == "dict":
        return isinstance(value, dict)
    if field_type == "list":
        return isinstance(value, list)
    if field_type == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    return False


def validate(name, data):
    """
    Validate an artifact against its schema.

    Input:
        name: artifact schema name ("registry", "cleaning_job",
            "cleaning_result").
        data: the artifact (dict).

    Output:
        A list of error strings (empty when valid).

    Checks: schema existence, object type, required fields present and
    correctly typed, optional fields correctly typed when present, and
    schema_version match.
    """
    schema = ARTIFACT_SCHEMAS.get(name)
    if schema is None:
        return [f"unknown artifact schema: {name}"]

    if not isinstance(data, dict):
        return [
            f"{name}: expected a JSON object, got {type(data).__name__}"
        ]

    errors = []

    for field in sorted(schema["required"]):
        if field not in data:
            errors.append(f"{name}: missing required field '{field}'")
            continue
        field_type = schema["required"][field]
        if not _matches_type(field_type, data[field]):
            errors.append(
                f"{name}: field '{field}' has invalid value "
                f"({data[field]!r})"
            )

    for field in sorted(schema["optional"]):
        if field not in data:
            continue
        field_type = schema["optional"][field]
        if not _matches_type(field_type, data[field]):
            errors.append(
                f"{name}: optional field '{field}' has invalid value "
                f"({data[field]!r})"
            )

    version = schema["schema_version"]
    if "schema_version" not in data:
        errors.append(f"{name}: missing required field 'schema_version'")
    elif data["schema_version"] != version:
        errors.append(
            f"{name}: schema_version mismatch (expected {version}, "
            f"got {data['schema_version']!r})"
        )

    return errors


__all__ = [
    "ARTIFACT_SCHEMAS",
    "artifact_names",
    "schema_version",
    "validate",
]
