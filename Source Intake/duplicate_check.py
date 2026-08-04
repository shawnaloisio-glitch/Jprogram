#!/usr/bin/env python3
"""
duplicate_check.py

Japanese Corpus Pipeline - Source Intake (registration-state query)

Queries the current Source Intake registration state for a candidate
source (sha256 + source_id):
- existing Source Registry entries
- matching sha256 values
- matching source_id values
- whether the related Cleaning Job exists

Read-only. It does NOT decide resume behavior, write artifacts, regenerate
jobs, modify registries, execute cleaners, or manage workflow.
"""

import json
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

import schemas


class DuplicateCheckError(Exception):
    """Raised when the registration-state query cannot be performed."""


def check(sha256, source_id, registry_dir, jobs_dir):
    """
    Query the registration state for a candidate source.

    Input:
        sha256: candidate hash (string).
        source_id: candidate source_id (string).
        registry_dir: Source Registry directory.
        jobs_dir: Cleaning Jobs directory.

    Output:
        {
            "duplicate_by_hash": bool,
            "duplicate_source_id": str | None,
            "match_by_source_id": bool,
            "registry_exists": bool,
            "job_exists": bool,
            "malformed_entries": [str],
        }

    Malformed registry entries are listed in malformed_entries (never
    silently skipped). The caller decides whether to refuse.

    Determinism: registry files are read in sorted order; identical inputs
    produce identical verdicts. No API calls, no external services, no
    hidden state, and nothing is written.

    Raises:
        DuplicateCheckError for invalid inputs or an unusable registry
        directory.
    """
    if not (isinstance(sha256, str) and sha256):
        raise DuplicateCheckError("sha256 must be a non-empty string")
    if not (isinstance(source_id, str) and source_id):
        raise DuplicateCheckError("source_id must be a non-empty string")

    registry_dir = Path(registry_dir)
    jobs_dir = Path(jobs_dir)

    if registry_dir.exists() and not registry_dir.is_dir():
        raise DuplicateCheckError(
            f"registry directory is not a directory: {registry_dir}"
        )

    result = {
        "duplicate_by_hash": False,
        "duplicate_source_id": None,
        "match_by_source_id": False,
        "registry_exists": (registry_dir / f"{source_id}.json").is_file(),
        "job_exists": (jobs_dir / f"{source_id}.cleaning_job.json").is_file(),
        "malformed_entries": [],
    }

    if not registry_dir.exists():
        return result

    for entry_file in sorted(registry_dir.glob("*.json")):

        try:
            data = json.loads(entry_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError, OSError):
            result["malformed_entries"].append(entry_file.name)
            continue

        errors = schemas.validate("registry", data)
        if errors:
            result["malformed_entries"].append(entry_file.name)
            continue

        if data.get("sha256") == sha256 and not result["duplicate_by_hash"]:
            result["duplicate_by_hash"] = True
            result["duplicate_source_id"] = data.get("source_id")

        if data.get("source_id") == source_id:
            result["match_by_source_id"] = True

    return result


__all__ = ["check", "DuplicateCheckError"]
