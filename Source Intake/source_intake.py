#!/usr/bin/env python3
"""
source_intake.py

Japanese Corpus Pipeline - Source Intake (coordinator)

Coordinates source registration:
    metadata collection
    source identity generation
    duplicate / registration-state checking
    Source Registry creation
    Cleaning Job creation

Then it stops. It never executes cleaners, calls APIs, parses files for
content, or manages downstream pipeline stages.

Lifecycle (fixed order):
    1. Collect metadata.
    2. Generate source_id.
    3. Generate SHA256.
    4. Check registration state (duplicate_check).
    5. Interpret:
       A. malformed registry entries  -> error (no writes)
       B. same hash, different id     -> duplicate (no writes)
       C. source_id registered + job  -> already_complete (no writes)
       D. source_id registered, no job-> RESUME (write only the job)
       E. no registration             -> write registry, then job
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

from common import (
    ensure_folder,
    print_header,
    print_footer,
    timestamp,
)

from project_config import (
    PROJECT_VERSION,
    SOURCE_TYPES,
    TRANSCRIPT_EXTENSION,
    DEFAULT_LANGUAGE,
)

from paths import (
    SOURCE_REGISTRY,
    CLEANING_JOBS,
    LOG_SOURCE_INTAKE,
)

import cleaning_job
import duplicate_check
import hashing
import registry
import resolver
import source_id


PROGRAM_NAME = "Source Intake"

# Allowed extensions per source type (metadata validation only).

_EXTENSIONS_BY_TYPE = {
    "clean_text": (TRANSCRIPT_EXTENSION,),
}


class SourceIntakeError(Exception):
    """Raised when source registration cannot be completed."""


# ============================================================
# Logging
# ============================================================

def _start_log():
    """Create a new Source Intake run log and return its path."""
    ensure_folder(LOG_SOURCE_INTAKE)
    log_file = (
        LOG_SOURCE_INTAKE
        / (
            "source_intake_"
            + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            + ".log"
        )
    )
    log_file.write_text(
        f"Program: {PROGRAM_NAME}\n"
        f"Version: {PROJECT_VERSION}\n"
        f"Date: {timestamp()}\n"
        "\n",
        encoding="utf-8",
    )
    return log_file


def _append_log(log_file, line):
    """Append one line to the run log."""
    with log_file.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


# ============================================================
# Metadata validation
# ============================================================

def _collect_metadata(raw_path, source_type, language, title, sequence):
    """
    Validate intake metadata.

    Checks: raw path present, source_type known, language non-empty,
    title non-empty, sequence a string or None, and the raw path
    extension valid for the source type. No artifact writes.
    """
    if not (isinstance(raw_path, str) and raw_path):
        raise SourceIntakeError("raw path must be a non-empty string")

    if source_type not in SOURCE_TYPES:
        raise SourceIntakeError(f"unknown source type: {source_type}")

    if not (isinstance(language, str) and language):
        raise SourceIntakeError("language must not be empty")

    if not (isinstance(title, str) and title.strip()):
        raise SourceIntakeError("title must not be empty")

    if sequence is not None and not isinstance(sequence, str):
        raise SourceIntakeError("sequence must be a string or None")

    extensions = _EXTENSIONS_BY_TYPE[source_type]
    suffix = Path(raw_path).suffix.lower()
    if suffix not in extensions:
        raise SourceIntakeError(
            f"invalid extension '{suffix}' for source type "
            f"'{source_type}' (expected {', '.join(extensions)})"
        )


# ============================================================
# Path resolution
# ============================================================

def _resolve_raw_path(raw_path, source_type):
    """
    Resolve and validate the raw source file location.

    The resolved file must reside in the source type's raw directory
    (resolver.raw_dir_for). Relative paths are resolved against it.
    """
    raw_dir = resolver.raw_dir_for(source_type).resolve()

    path = Path(raw_path)
    if not path.is_absolute():
        path = raw_dir / path
    path = path.resolve()

    try:
        inside = path.is_relative_to(raw_dir)
    except AttributeError:
        inside = str(path).startswith(str(raw_dir))

    if not inside:
        raise SourceIntakeError(
            f"raw file must be inside the raw directory: {raw_dir}"
        )

    if not path.is_file():
        raise SourceIntakeError(f"source file not found: {path}")

    return path


# ============================================================
# Registry entry construction
# ============================================================

def _load_registry_entry(source_id_str):
    """Load an existing Source Registry entry (own artifact read)."""
    path = SOURCE_REGISTRY / f"{source_id_str}.json"
    if not path.is_file():
        raise SourceIntakeError(f"registry entry not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, OSError) as ex:
        raise SourceIntakeError(f"failed to read registry entry: {ex}") from ex


def _build_registry_entry(resolved, source_id_str, sha256, source_type, language):
    """Create the Source Registry dict using registry.build_entry."""
    cleaning_profile = resolver.cleaning_profile_for(source_type)
    _cleaner, cleaner_version = resolver.cleaner_and_version_for(cleaning_profile)
    fmt = resolved.suffix.lstrip(".").lower()
    return registry.build_entry(
        source_id=source_id_str,
        original_filename=resolved.name,
        sha256=sha256,
        source_type=source_type,
        format=fmt,
        language=language,
        cleaning_profile=cleaning_profile,
        cleaner_version=cleaner_version,
    )


def _build_cleaning_job(entry):
    """Create the Cleaning Job dict via resolver.cleaning_job_fields."""
    return resolver.cleaning_job_fields(entry)


# ============================================================
# Lifecycle
# ============================================================

def _run_intake(raw_path, source_type, language, title, sequence, log_file):
    """
    Run the registration lifecycle. Returns a result dict:
        {"action": "registered" | "resumed" | "already_complete" | "duplicate",
         "source_id": str, ...}
    """
    _collect_metadata(raw_path, source_type, language, title, sequence)
    resolved = _resolve_raw_path(raw_path, source_type)

    slug = source_id.slugify(title)
    source_id_str = source_id.generate(source_type, slug, sequence)

    try:
        sha256 = hashing.sha256_file(resolved)
    except (OSError, FileNotFoundError) as ex:
        raise SourceIntakeError(f"failed to hash source file: {ex}") from ex

    try:
        verdict = duplicate_check.check(
            sha256, source_id_str, SOURCE_REGISTRY, CLEANING_JOBS
        )
    except duplicate_check.DuplicateCheckError as ex:
        raise SourceIntakeError(f"duplicate check failed: {ex}") from ex

    # CASE A: malformed registry entries -> stop, no writes.
    if verdict["malformed_entries"]:
        raise SourceIntakeError(
            f"malformed registry entries found: "
            f"{verdict['malformed_entries']}"
        )

    # CASE B: same hash registered under a different source_id -> duplicate.
    if (
        verdict["duplicate_by_hash"]
        and verdict["duplicate_source_id"] != source_id_str
    ):
        _append_log(
            log_file,
            f"{timestamp()} DUPLICATE {source_id_str} hash matches "
            f"{verdict['duplicate_source_id']}",
        )
        return {
            "action": "duplicate",
            "source_id": source_id_str,
            "duplicate_source_id": verdict["duplicate_source_id"],
        }

    # CASE C: registered and the cleaning job exists -> already complete.
    if verdict["match_by_source_id"] and verdict["job_exists"]:
        _append_log(log_file, f"{timestamp()} ALREADY-COMPLETE {source_id_str}")
        return {
            "action": "already_complete",
            "source_id": source_id_str,
        }

    # CASE D: registered but the cleaning job is missing -> resume.
    if verdict["match_by_source_id"] and not verdict["job_exists"]:
        entry = _load_registry_entry(source_id_str)
        try:
            job = _build_cleaning_job(entry)
        except resolver.ResolverError as ex:
            raise SourceIntakeError(
                f"failed to reconstruct cleaning job: {ex}"
            ) from ex
        job_path = CLEANING_JOBS / f"{source_id_str}.cleaning_job.json"
        try:
            cleaning_job.write_job(job_path, job)
        except cleaning_job.CleaningJobError as ex:
            raise SourceIntakeError(
                f"failed to write cleaning job: {ex}"
            ) from ex
        _append_log(log_file, f"{timestamp()} RESUMED {source_id_str}")
        return {
            "action": "resumed",
            "source_id": source_id_str,
            "cleaning_job_path": str(job_path),
        }

    # Registry-path collision: a file exists at the target registry path
    # but its internal source_id does not match the candidate -> stop, no
    # writes, so the pre-existing entry is never silently overwritten.
    if verdict["registry_exists"] and not verdict["match_by_source_id"]:
        registry_path = SOURCE_REGISTRY / f"{source_id_str}.json"
        raise SourceIntakeError(
            f"existing registry file at {registry_path} does not match "
            f"expected source_id {source_id_str!r}; cannot safely resolve "
            f"automatically"
        )

    # CASE E: no existing registration -> write registry first, then job.
    entry = _build_registry_entry(
        resolved, source_id_str, sha256, source_type, language
    )
    registry_path = SOURCE_REGISTRY / f"{source_id_str}.json"
    try:
        registry.write_registry(registry_path, entry)
    except registry.RegistryError as ex:
        raise SourceIntakeError(f"failed to write registry: {ex}") from ex

    try:
        job = _build_cleaning_job(entry)
        job_path = CLEANING_JOBS / f"{source_id_str}.cleaning_job.json"
        cleaning_job.write_job(job_path, job)
    except (resolver.ResolverError, cleaning_job.CleaningJobError) as ex:
        raise SourceIntakeError(f"failed to create cleaning job: {ex}") from ex

    _append_log(log_file, f"{timestamp()} REGISTERED {source_id_str}")
    return {
        "action": "registered",
        "source_id": source_id_str,
        "registry_path": str(registry_path),
        "cleaning_job_path": str(job_path),
    }


# ============================================================
# Public entry points
# ============================================================

def register_source(raw_path, source_type, language, title, sequence):
    """
    Register a raw source and create its Source Registry and Cleaning Job.

    Programmatic entry point for tests and future callers. Returns a
    result dict with an "action" field. Raises SourceIntakeError on
    invalid input or a malformed registry.
    """
    log_file = _start_log()
    try:
        result = _run_intake(
            raw_path, source_type, language, title, sequence, log_file
        )
        _append_log(
            log_file,
            f"{timestamp()} END {result['action']} {result.get('source_id')}",
        )
        return result
    except SourceIntakeError as ex:
        _append_log(log_file, f"{timestamp()} ERROR {ex}")
        raise


def main():
    """
    CLI entry point: collect metadata interactively and register a source.
    """

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print_header(PROGRAM_NAME, PROJECT_VERSION)

    raw_path = input("Raw file path (inside the source type raw folder): ").strip()
    source_type = input(f"Source type {sorted(SOURCE_TYPES)}: ").strip()
    language = input(f"Language (default {DEFAULT_LANGUAGE}): ").strip() or DEFAULT_LANGUAGE
    title = input("Title: ").strip()
    sequence = input("Sequence (e.g., ep051; optional): ").strip() or None

    try:
        result = register_source(raw_path, source_type, language, title, sequence)
    except SourceIntakeError as ex:
        print(f"\nERROR: {ex}")
        print_footer()
        input("\nPress Enter to exit...")
        return

    print(f"\nAction      : {result['action']}")
    print(f"Source id   : {result['source_id']}")
    if result.get("registry_path"):
        print(f"Registry    : {result['registry_path']}")
    if result.get("cleaning_job_path"):
        print(f"Cleaning job: {result['cleaning_job_path']}")

    print_footer()
    input("\nPress Enter to exit...")


__all__ = ["register_source", "main", "SourceIntakeError"]
