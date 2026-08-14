#!/usr/bin/env python3
"""
handoff.py

Japanese Corpus Pipeline - Source Builder handoff.

Bridges a Source Package (the authoritative birth certificate) into the
existing pipeline's intake artifacts:

    Source Package (.source.json)
        |
        v
    Handoff
        |
        +--> Source Registry entry  (Source Registry\\<source_id>.json)
        |
        +--> Cleaning Job           (Cleaning Jobs\\<source_id>.cleaning_job.json)
                |
                v
            Cleaner -> Cleaning Result -> Job Creator -> Processor

Responsibilities ONLY:
- read a validated Source Package,
- create the Source Registry artifact,
- create the Cleaning Job artifact.

It does NOT clean text, process text, create job batches, call APIs, modify
source files, or create legacy Raw Transcript / Raw Subtitle folders.

The Cleaning Job's raw_path points directly at the canonical Source Builder
file; the cleaner reads it read-only.

Idempotency: the same source_id with the same sha256 is never recreated, and
existing valid artifacts are never overwritten.
"""

import json
import sys
from pathlib import Path

# Allow imports from the project root, Source Builder, and Source Intake.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "Source Builder"))
sys.path.append(str(PROJECT_ROOT / "Source Intake"))

import cleaning_job
import controller
import registry
import resolver
import source_id
import source_package
from paths import CLEANING_JOBS, SOURCE_REGISTRY

# Global-counter identity scheme (DECIDED 2026-08-14: replaces title-slug
# identity project-wide -- see source_id.generate_counter_id's docstring).
ID_PREFIX = "ja"
MAX_ID_RETRIES = 25


class HandoffError(Exception):
    """Raised when a handoff cannot be completed."""


def load_source_package(path):
    """
    Read and validate a Source Package artifact.

    Input: path (str or Path).
    Output: the source package dict.
    Raises: HandoffError when the file is missing, unreadable, or invalid.
    """
    package_path = Path(path)
    if not package_path.is_file():
        raise HandoffError(f"source package not found: {package_path}")
    try:
        package = json.loads(package_path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        raise HandoffError(f"source package unreadable: {package_path}: {exc}")

    errors = source_package.validate_package(package)
    if errors:
        raise HandoffError("; ".join(errors))
    return package


def registry_path_for(source_id):
    """Return the Source Registry artifact path for a source_id."""
    return SOURCE_REGISTRY / f"{source_id}.json"


def cleaning_job_path_for(source_id):
    """Return the Cleaning Job artifact path for a source_id."""
    return CLEANING_JOBS / f"{source_id}.cleaning_job.json"


def _load_existing_sha256(path):
    """Return the sha256 of an existing JSON artifact, or None."""
    if not Path(path).is_file():
        return None
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None
    if isinstance(data, dict):
        return data.get("sha256")
    return None


def registry_entry_for(package):
    """
    Build the Source Registry entry from a source package.

    Input: package (dict).
    Output: registry dict (registry schema).
    Raises: HandoffError when the package cannot produce a registry entry.
    """
    required = (
        "source_id", "original_filename", "sha256", "source_type", "format",
        "language", "cleaning_profile", "cleaner_version",
    )
    for field in required:
        value = package.get(field)
        if not isinstance(value, str) or not value:
            raise HandoffError(
                f"source package missing required field for registry: {field}")

    return registry.build_entry(
        source_id=package["source_id"],
        original_filename=package["original_filename"],
        sha256=package["sha256"],
        source_type=package["source_type"],
        format=package["format"],
        language=package["language"],
        cleaning_profile=package["cleaning_profile"],
        cleaner_version=package["cleaner_version"],
    )


def cleaning_job_for(package):
    """
    Build the Cleaning Job from a source package.

    The raw_path points directly at the canonical Source Builder file; the
    output_path points at Cleaned Archive\\<source_id>.clean.txt.

    Input: package (dict).
    Output: cleaning job dict (cleaning_job schema).
    Raises: HandoffError when the package cannot produce a cleaning job.
    """
    required = ("source_id", "canonical_path", "source_type",
                "cleaning_profile", "cleaner_version")
    for field in required:
        value = package.get(field)
        if not isinstance(value, str) or not value:
            raise HandoffError(
                f"source package missing required field for cleaning job: "
                f"{field}")

    output_path = resolver.cleaned_output_path_for(package["source_id"])
    return cleaning_job.build_job(
        source_id=package["source_id"],
        raw_path=package["canonical_path"],
        source_type=package["source_type"],
        cleaning_profile=package["cleaning_profile"],
        cleaner_version=package["cleaner_version"],
        output_path=str(output_path),
    )


def handoff(package, force=False):
    """
    Create the Source Registry entry and Cleaning Job for a source package.

    Idempotent: same source_id + same sha256 -> reports already exists and
    creates nothing. Existing valid artifacts are never overwritten unless
    force=True.

    Input:
        package (dict) - validated source package,
        force (bool) - overwrite existing artifacts (default False).

    Output: dict:
        {
            "source_id": str,
            "registry": {"action": "created"|"exists"|"failed",
                         "path": str},
            "cleaning_job": {"action": "created"|"exists"|"failed",
                             "path": str},
            "errors": [str, ...],
        }
    """
    errors = source_package.validate_package(package)
    if errors:
        raise HandoffError("; ".join(errors))

    source_id = package["source_id"]
    sha256 = package["sha256"]

    registry_entry = registry_entry_for(package)
    cleaning = cleaning_job_for(package)

    registry_path = registry_path_for(source_id)
    job_path = cleaning_job_path_for(source_id)

    result = {
        "source_id": source_id,
        "registry": {"action": "failed", "path": str(registry_path)},
        "cleaning_job": {"action": "failed", "path": str(job_path)},
        "errors": [],
    }

    # Registry. write_registry_if_absent is an atomic OS-level exclusive
    # create -- at most one of two callers racing on the same source_id
    # can ever win it, closing the read-then-write gap the old
    # check-then-write sequence had (confirmed real: two parallel workers
    # could both pass an existence check before either wrote, and the
    # second write would silently win with neither reporting a failure).
    try:
        created = registry.write_registry_if_absent(registry_path, registry_entry)
    except registry.RegistryError as exc:
        result["errors"].append(f"registry write failed: {exc}")
        created = None
    if created is True:
        result["registry"]["action"] = "created"
    elif created is False:
        # Someone (this call, sequentially, or a racing worker) already
        # created it first. Fall back to the same sha256-compare logic as
        # before -- now race-safe, since the exclusive create above is
        # what actually decided "first or not," not this read.
        existing_reg_sha = _load_existing_sha256(registry_path)
        if existing_reg_sha == sha256:
            result["registry"]["action"] = "exists"
        else:
            if not force:
                result["errors"].append(
                    "registry exists with a different sha256; "
                    "use force to overwrite")
            else:
                try:
                    registry.write_registry(registry_path, registry_entry)
                    result["registry"]["action"] = "created"
                except registry.RegistryError as exc:
                    result["errors"].append(f"registry write failed: {exc}")

    # Cleaning Job. Only attempted when the Registry step actually
    # succeeded (created or exists) -- if it's still "failed" here, this
    # source_id was never really ours: skipping avoids two racing workers
    # BOTH writing to the exact same Cleaning Job path when they collide on
    # the same source_id (cleaning_job.write_job's temp filename is not
    # per-process-unique, unlike registry.py's atomic exclusive create --
    # confirmed real 2026-08-14 during global-counter concurrency testing,
    # WinError 5 access-denied when two processes raced the same shared
    # ".tmp" path). Under the global-counter scheme every source_id has at
    # most one legitimate winner, so this can never skip a Cleaning Job a
    # caller actually needed.
    if result["registry"]["action"] == "failed":
        return result

    existing_job = Path(job_path).is_file()
    if existing_job:
        if not force:
            result["cleaning_job"]["action"] = "exists"
        else:
            try:
                cleaning_job.write_job(job_path, cleaning)
                result["cleaning_job"]["action"] = "created"
            except cleaning_job.CleaningJobError as exc:
                result["errors"].append(f"cleaning job write failed: {exc}")
    else:
        try:
            cleaning_job.write_job(job_path, cleaning)
            result["cleaning_job"]["action"] = "created"
        except cleaning_job.CleaningJobError as exc:
            result["errors"].append(f"cleaning job write failed: {exc}")

    return result


def handoff_for_package_path(package_path, force=False):
    """Load a source package and run handoff for it."""
    package = load_source_package(package_path)
    return handoff(package, force=force)


def _next_candidate_id():
    """Return a fresh global-counter candidate source_id."""
    counter = source_id.next_counter(SOURCE_REGISTRY, ID_PREFIX)
    return source_id.generate_counter_id(ID_PREFIX, counter)


def _is_id_collision(handoff_result):
    """
    True when a handoff() failure means "another process already claimed
    this exact counter value," not a genuine validation/IO failure.

    Under the global-counter scheme every source_id is content-independent,
    so a sha256 mismatch at an already-occupied registry path can only mean
    a different, unrelated source won this exact id concurrently -- always
    safe to retry with a fresh counter (unlike the old slug-derived scheme,
    where the same mismatch could also mean a genuine two-different-titles
    naming collision requiring manual resolution).
    """
    return any("different sha256" in e for e in handoff_result.get("errors", []))


def _cleanup_failed_attempt(canonical_path, package_path):
    """
    Remove the artifacts written for a losing id-assignment attempt so the
    next retry starts clean: the canonical source file and its Source
    Package sidecar. These two are always exclusively ours (their paths
    are keyed by source_name/collection+episode, not by the contested
    candidate source_id), so deleting them can never touch another
    process's artifacts.

    Deliberately does NOT touch anything under the losing candidate's
    source_id (e.g. a Cleaning Job path) -- handoff() only ever writes a
    Cleaning Job once its Registry step actually succeeds, so on a
    collision the candidate's id belongs entirely to whichever process
    won it; a losing process reaching into that path (even to "clean up")
    would be deleting or racing a different, legitimate process's
    in-progress or completed write. Confirmed real 2026-08-14: an earlier
    version of this cleanup unlinked cleaning_job_path_for(candidate_id)
    unconditionally and hit WinError 5 (access denied) under genuine
    multi-process concurrency, because the path it was deleting belonged
    to the concurrently-writing winner, not to this losing attempt.
    """
    Path(canonical_path).unlink(missing_ok=True)
    Path(package_path).unlink(missing_ok=True)


def register_standalone_source(source_name, source_type, creator, source_text,
                               overwrite=False, material_level=0,
                               style_id=None, topic_id=None,
                               duration_seconds=None, episode_number=None,
                               season_number=None):
    """
    Create and fully register (Source Package + Registry + Cleaning Job) a
    standalone source under a fresh global-counter source_id, retrying with
    a new counter value whenever a concurrent process wins the same one
    first (the counter scan-then-write is not atomic across processes --
    see source_id.next_counter's docstring). Bounded by MAX_ID_RETRIES.

    Safe to call from multiple parallel worker processes (e.g. Batch
    Importer workers) racing on the same registry directory: at most one
    attempt per counter value can ever win, and every losing attempt's
    artifacts are cleaned up before the next retry.

    Output: same shape as handoff(), with an added "create" key holding
    controller.create_standalone_source's own result dict. On a
    non-collision create failure, returns controller's result unchanged
    (no "registry"/"cleaning_job" keys).
    Raises: HandoffError if MAX_ID_RETRIES is exhausted on persistent
    collisions.
    """
    last_result = None
    for _attempt in range(MAX_ID_RETRIES):
        candidate_id = _next_candidate_id()
        created = controller.create_standalone_source(
            source_name, source_type, creator, source_text,
            overwrite=overwrite, material_level=material_level,
            style_id=style_id, topic_id=topic_id,
            duration_seconds=duration_seconds,
            episode_number=episode_number, season_number=season_number,
            source_id=candidate_id,
        )
        if not created["success"] or created.get("package_error"):
            return created

        package_path = source_package.package_path_for(created["path"])
        package = load_source_package(package_path)
        result = handoff(package)
        if not _is_id_collision(result):
            result["create"] = created
            return result

        _cleanup_failed_attempt(created["path"], package_path)
        last_result = result
    raise HandoffError(
        f"failed to register {source_name!r} after {MAX_ID_RETRIES} "
        f"attempts (persistent counter collision): {last_result['errors']}")


def register_collection_source(collection_id, source_type, creator,
                                source_text, overwrite=False,
                                material_level=0, style_id=None,
                                topic_id=None, duration_seconds=None,
                                episode_number=None, season_number=None):
    """
    Collection-mode counterpart to register_standalone_source. The
    collection filename's episode number still comes from
    controller.next_auto_sequence (file ordering, unaffected); only the
    pipeline source_id is now a retried global-counter value instead of
    being derived from collection_id/episode.

    Output / Raises: see register_standalone_source.
    """
    last_result = None
    for _attempt in range(MAX_ID_RETRIES):
        candidate_id = _next_candidate_id()
        created = controller.create_collection_source(
            collection_id, None, source_type, creator, source_text,
            overwrite=overwrite, material_level=material_level,
            style_id=style_id, topic_id=topic_id,
            duration_seconds=duration_seconds,
            episode_number=episode_number, season_number=season_number,
            source_id=candidate_id,
        )
        if not created["success"] or created.get("package_error"):
            return created

        package_path = source_package.package_path_for(created["path"])
        package = load_source_package(package_path)
        result = handoff(package)
        if not _is_id_collision(result):
            result["create"] = created
            return result

        _cleanup_failed_attempt(created["path"], package_path)
        last_result = result
    raise HandoffError(
        f"failed to register a {collection_id!r} source after "
        f"{MAX_ID_RETRIES} attempts (persistent counter collision): "
        f"{last_result['errors']}")


__all__ = [
    "HandoffError",
    "load_source_package",
    "registry_path_for",
    "cleaning_job_path_for",
    "registry_entry_for",
    "cleaning_job_for",
    "handoff",
    "handoff_for_package_path",
    "register_standalone_source",
    "register_collection_source",
]
