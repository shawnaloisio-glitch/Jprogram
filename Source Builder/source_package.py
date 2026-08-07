#!/usr/bin/env python3
"""
source_package.py

Japanese Corpus Pipeline - Source Builder source package ("birth certificate").

The Source Package is the authoritative identity record for a canonical
source. It is created only after a successful source save and lives as a
sidecar beside the canonical text:

    Sources\\<collection_id>_epNNNN.txt
    Sources\\<collection_id>_epNNNN.source.json

    Sources\\<source_name>.txt
    Sources\\<source_name>.source.json

The package never modifies the canonical text file. It carries every field a
future handoff module needs to produce a Source Registry entry and a Cleaning
Job without asking the user for identity information again.

This module is GUI-free and deterministic so it can be unit tested.
"""

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Allow imports from the project root and Source Intake utilities.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "Source Intake"))

import source_id as source_id_util

from project_config import (
    CLEANER_VERSIONS,
    PROCESSING_PROFILES,
    PROJECT_VERSION,
)

ARTIFACT_TYPE = "source_package"
SCHEMA_VERSION = "1"
PACKAGE_SUFFIX = ".source.json"
FORMAT = "txt"


class SourcePackageError(Exception):
    """Raised when a source package cannot be built or written."""


def package_path_for(canonical_path):
    """
    Return the sidecar package path for a canonical source file.

    Input: canonical_path (str or Path), e.g.
        Sources\\teppei_beginner_ep0058.txt
    Output: Path with the ".txt" extension replaced by ".source.json", e.g.
        Sources\\teppei_beginner_ep0058.source.json
    """
    path = Path(canonical_path)
    return path.with_suffix(PACKAGE_SUFFIX)


def derive_source_id(source_type, slug_seed, episode=None):
    """
    Derive the deterministic pipeline source_id.

    Uses the frozen Source Intake rules:
        {source_type}_{slug}_{sequence}
    where slug = slugify(slug_seed) and sequence = format_sequence(episode,
    "ep", width=3).

    Input:
        source_type (str), slug_seed (str), episode (int|None).
    Output: source_id string.
    """
    slug = source_id_util.slugify(slug_seed)
    if episode is None:
        return source_id_util.generate(source_type, slug)
    sequence = source_id_util.format_sequence(episode, "ep", width=3)
    return source_id_util.generate(source_type, slug, sequence)


def cleaning_profile_for(source_type):
    """Return the cleaning profile for a source_type (None if unknown)."""
    profile = PROCESSING_PROFILES.get(source_type)
    if profile is None:
        return None
    return profile.get("cleaning_profile")


def processable_source_types():
    """Return the sorted source types that have a processing profile."""
    return sorted(PROCESSING_PROFILES.keys())


def is_processable_source_type(source_type):
    """Return True when a source type has an active processing profile."""
    return source_type in PROCESSING_PROFILES


def cleaner_version_for(cleaning_profile):
    """Return the configured cleaner version for a profile (None if unknown)."""
    return CLEANER_VERSIONS.get(cleaning_profile)


def sha256_file(file_path):
    """Return the lowercase hex SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with Path(file_path).open("rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_package(source_type, origin, language, canonical_path,
                  cleaning_profile, cleaner_version, source_id=None,
                  collection_id=None, episode=None, source_name=None,
                  created_at=None):
    """
    Build a Source Package dict.

    Input:
        source_type (str), origin (str), language (str),
        canonical_path (str), cleaning_profile (str|None),
        cleaner_version (str|None), source_id (str|None, derived if None),
        collection_id (str|None, collection mode),
        episode (int|None, collection mode),
        source_name (str|None, standalone mode),
        created_at (str|None, auto now).

    Output: the source package dict.

    The sha256 is computed from the canonical file. format is fixed to "txt".
    """
    canonical = Path(canonical_path)
    if not canonical.is_file():
        raise SourcePackageError(f"canonical source file not found: {canonical}")

    if collection_id is None and source_name is None:
        raise SourcePackageError(
            "source package requires collection_id or source_name")

    if source_id is None:
        slug_seed = collection_id if collection_id is not None else source_name
        source_id = derive_source_id(source_type, slug_seed, episode)

    if created_at is None:
        created_at = datetime.now().isoformat(timespec="seconds")

    package = {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "source_id": source_id,
        "source_type": source_type,
        "origin": origin,
        "language": language,
        "canonical_path": str(canonical),
        "original_filename": canonical.name,
        "format": FORMAT,
        "cleaning_profile": cleaning_profile,
        "cleaner_version": cleaner_version,
        "sha256": sha256_file(canonical),
        "created_at": created_at,
        "created_by_version": PROJECT_VERSION,
    }
    if collection_id is not None:
        package["collection_id"] = collection_id
        package["episode"] = episode
    if source_name is not None:
        package["source_name"] = source_name
    return package


def validate_package(package):
    """
    Validate a source package dict; return a list of error strings.

    Checks required fields and type/basic rules. Returns [] when valid.
    """
    errors = []
    if not isinstance(package, dict):
        return ["source package must be a dict"]
    if package.get("artifact_type") != ARTIFACT_TYPE:
        errors.append("artifact_type must be 'source_package'")
    if package.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be '{SCHEMA_VERSION}'")

    required_strings = (
        "source_id", "source_type", "origin", "language", "canonical_path",
        "original_filename", "format", "sha256", "created_at",
        "created_by_version",
    )
    for field in required_strings:
        value = package.get(field)
        if not isinstance(value, str) or not value:
            errors.append(f"{field} is required")

    # Cleaning profile / version keys must be present, but their value may
    # be null when the source_type has no processing profile (e.g. a source
    # type not yet mapped in PROCESSING_PROFILES). A future handoff can only
    # create a Cleaning Job when both are present and non-null.
    for field in ("cleaning_profile", "cleaner_version"):
        if field not in package:
            errors.append(f"{field} is required")

    has_collection = isinstance(package.get("collection_id"), str) \
        and bool(package.get("collection_id"))
    has_source_name = isinstance(package.get("source_name"), str) \
        and bool(package.get("source_name"))
    if not has_collection and not has_source_name:
        errors.append("collection_id or source_name is required")
    return errors


def write_package(package, path=None):
    """
    Validate and atomically write a Source Package artifact.

    Input:
        package (dict), path (str|Path|None - sidecar beside canonical when
        omitted, derived from package["canonical_path"]).

    Output: the written Path.
    """
    errors = validate_package(package)
    if errors:
        raise SourcePackageError("; ".join(errors))
    if path is None:
        path = package_path_for(package["canonical_path"])

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(package, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        temp.replace(target)
    except OSError as exc:
        raise SourcePackageError(
            f"cannot write source package: {target}: {exc}") from exc
    return target


__all__ = [
    "ARTIFACT_TYPE",
    "SCHEMA_VERSION",
    "PACKAGE_SUFFIX",
    "FORMAT",
    "SourcePackageError",
    "package_path_for",
    "derive_source_id",
    "cleaning_profile_for",
    "processable_source_types",
    "is_processable_source_type",
    "cleaner_version_for",
    "sha256_file",
    "build_package",
    "validate_package",
    "write_package",
]
