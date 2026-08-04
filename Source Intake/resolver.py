#!/usr/bin/env python3
"""
resolver.py

Japanese Corpus Pipeline - Source Intake (utility layer)

Deterministic intake rules:
- source_type -> raw directory
- source_type -> default cleaning profile
- cleaning_profile -> (cleaner, cleaner_version)
- source_id -> cleaned output path
- registry entry -> cleaning job fields (resume reconstruction)

Reads configuration (project_config) and paths (paths) only. It does not
read files, hash, or write artifacts. Registry-recorded assignment values
win; it never guesses.
"""

import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

import schemas

from project_config import (
    PROCESSING_PROFILES,
    CLEANER_VERSIONS,
    SOURCE_TYPE_RAW_DIR,
    CLEANED_ARTIFACT_EXTENSION,
)

from paths import (
    PROJECT_ROOT,
    CLEANED_ARCHIVE,
)


class ResolverError(Exception):
    """Raised when an intake rule cannot be resolved deterministically."""


def raw_dir_for(source_type):
    """
    Return the raw source directory for a source type.

    Input: source_type (string).
    Output: a project-root Path.
    Raises: ResolverError for an unknown source type.
    """
    folder = SOURCE_TYPE_RAW_DIR.get(source_type)
    if folder is None:
        raise ResolverError(f"unknown source type: {source_type}")
    return PROJECT_ROOT / folder


def cleaning_profile_for(source_type):
    """
    Return the default cleaning profile for a source type.

    Input: source_type (string).
    Output: cleaning profile string.
    Raises: ResolverError for an unknown source type.
    """
    profile = PROCESSING_PROFILES.get(source_type)
    if profile is None:
        raise ResolverError(f"unknown source type: {source_type}")
    return profile["cleaning_profile"]


def cleaner_and_version_for(cleaning_profile):
    """
    Return (cleaner, cleaner_version) for a cleaning profile.

    The cleaner name is derived deterministically from PROCESSING_PROFILES
    (all source types using the profile must agree on one cleaner). The
    version comes from CLEANER_VERSIONS.

    Input: cleaning_profile (string).
    Output: (cleaner, cleaner_version) tuple of strings.
    Raises: ResolverError if the profile is unknown, unversioned, or maps
    to more than one cleaner.
    """
    version = CLEANER_VERSIONS.get(cleaning_profile)
    if version is None:
        raise ResolverError(f"unknown cleaning profile: {cleaning_profile}")

    cleaners = sorted({
        processing["cleaner"]
        for processing in PROCESSING_PROFILES.values()
        if processing["cleaning_profile"] == cleaning_profile
    })
    if not cleaners:
        raise ResolverError(
            f"no cleaner mapped for cleaning profile: {cleaning_profile}"
        )
    if len(cleaners) != 1:
        raise ResolverError(
            f"ambiguous cleaner for cleaning profile {cleaning_profile}: "
            f"{cleaners}"
        )
    return cleaners[0], version


def cleaned_output_path_for(source_id):
    """
    Return the deterministic cleaned artifact path for a source_id.

    Input: source_id (string).
    Output: a Path under Cleaned Archive (e.g.,
        Cleaned Archive\\<source_id>.clean.txt).
    """
    return CLEANED_ARCHIVE / f"{source_id}{CLEANED_ARTIFACT_EXTENSION}"


def cleaning_job_fields(entry):
    """
    Reconstruct the Cleaning Job fields from a Source Registry entry.

    Used by the resume path. Registry-recorded assignment values
    (cleaning_profile, cleaner_version) are authoritative. raw_path is
    derived from the source type's raw directory and the registry's
    original_filename; output_path from the source_id naming rule.

    Input: entry (registry dict).
    Output: a Cleaning Job dict (valid against schemas "cleaning_job").
    Raises: ResolverError if the entry is missing required fields or the
    source type cannot be resolved to a raw directory.
    """
    if not isinstance(entry, dict):
        raise ResolverError("registry entry must be a dict")

    required = (
        "source_id",
        "original_filename",
        "source_type",
        "cleaning_profile",
        "cleaner_version",
    )
    for field in required:
        value = entry.get(field)
        if not isinstance(value, str) or not value:
            raise ResolverError(
                f"registry entry missing required field: {field}"
            )

    source_type = entry["source_type"]
    if source_type not in SOURCE_TYPE_RAW_DIR:
        raise ResolverError(f"unknown source type: {source_type}")

    job = {
        "schema_version": schemas.schema_version("cleaning_job"),
        "source_id": entry["source_id"],
        "raw_path": str(
            raw_dir_for(source_type) / entry["original_filename"]
        ),
        "source_type": source_type,
        "cleaning_profile": entry["cleaning_profile"],
        "cleaner_version": entry["cleaner_version"],
        "output_path": str(cleaned_output_path_for(entry["source_id"])),
    }

    errors = schemas.validate("cleaning_job", job)
    if errors:
        raise ResolverError("; ".join(errors))

    return job


__all__ = [
    "ResolverError",
    "raw_dir_for",
    "cleaning_profile_for",
    "cleaner_and_version_for",
    "cleaned_output_path_for",
    "cleaning_job_fields",
]
