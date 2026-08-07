#!/usr/bin/env python3
"""
controller.py

Japanese Corpus Pipeline - Source Builder controller.

Owns validation, filename generation, and canonical source file creation.
This layer is GUI-free and deterministic so it can be unit tested.

Identity types: collection and standalone (mutually exclusive).

Language is a project-level property, not source metadata. Each project
installation represents one language (this project: ja). Language is NOT a
source-level field and is not validated or stored per source.
"""

import os
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

import paths

import source_package

SOURCES_ROOT = paths.SOURCES

IDENTITY_TYPES = ("collection", "standalone")

# Project-level language (this installation represents one language).
PROJECT_LANGUAGE = "ja"


def _snapshot_or_blank(value):
    """Normalize a snapshot field for comparison; None becomes ''."""
    return "" if value is None else value


class SourceBuilderError(Exception):
    """Raised when a source cannot be validated or created."""


# ============================================================
# Filename generation
# ============================================================

def generate_filename(collection_id, episode):
    """
    Generate the canonical collection-mode filename.

    Input: collection_id (str), episode (int).
    Output: str like "teppei_beginner_ep0051.txt".
    """
    return f"{collection_id}_ep{episode:04d}.txt"


def generate_standalone_filename(source_name):
    """
    Generate the canonical standalone-mode filename.

    Input: source_name (str).
    Output: str like "nhk_weather_article_august.txt".
    """
    return f"{source_name}.txt"


def source_path(collection_id, episode):
    """Return the canonical save path for a collection source."""
    return SOURCES_ROOT / generate_filename(collection_id, episode)


def standalone_source_path(source_name):
    """Return the canonical save path for a standalone source."""
    return SOURCES_ROOT / generate_standalone_filename(source_name)


# ============================================================
# Validation
# ============================================================

def validate_collection_fields(collection_id, episode, source_type, creator,
                               source_text):
    """Validate required fields for a collection-mode source."""
    errors = []

    if not collection_id:
        errors.append("collection is required")
    if episode is None or episode == "":
        errors.append("episode number is required")
    else:
        try:
            episode_value = int(episode)
        except (TypeError, ValueError):
            errors.append("episode number must be an integer")
            episode_value = None
        if episode_value is not None and episode_value < 0:
            errors.append("episode number must be non-negative")

    errors.extend(_validate_common(source_type, creator, source_text))
    return errors


def validate_standalone_fields(source_name, source_type, creator, source_text):
    """Validate required fields for a standalone-mode source."""
    errors = []
    if not source_name:
        errors.append("source name is required")
    errors.extend(_validate_common(source_type, creator, source_text))
    return errors


def _validate_common(source_type, creator, source_text):
    errors = []
    if not source_type:
        errors.append("source type is required")
    if not creator:
        errors.append("creator is required")
    if source_text is None or source_text.strip() == "":
        errors.append("source text is empty")
    return errors


def validate_fields(collection_id, episode, source_type, creator, source_text):
    """
    Validate required fields for a collection-mode source.

    Retained for backward compatibility.
    """
    return validate_collection_fields(collection_id, episode, source_type,
                                      creator, source_text)


# ============================================================
# Collision detection
# ============================================================

def collision_exists(collection_id, episode):
    """Return True if the canonical collection source file already exists."""
    return source_path(collection_id, episode).is_file()


def standalone_collision_exists(source_name):
    """Return True if the canonical standalone source file already exists."""
    return standalone_source_path(source_name).is_file()


# ============================================================
# Source creation
# ============================================================

def _write_atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as file:
        file.write(text)
        file.flush()
        os.fsync(file.fileno())
    temp.replace(path)


def source_id_for(source_type, collection_id=None, episode=None,
                  source_name=None):
    """
    Return the deterministic pipeline source_id for a source.

    Uses the frozen Source Intake source_id rules. For collection mode the
    slug seed is the collection_id; for standalone mode it is the source_name.
    """
    if collection_id is not None:
        return source_package.derive_source_id(source_type, collection_id,
                                               episode)
    return source_package.derive_source_id(source_type, source_name)


def _try_write_source_package(source_type, creator, canonical_path,
                              collection_id=None, episode=None,
                              source_name=None, material_level=None,
                              style_id=None, duration_seconds=None):
    """
    Build and atomically write the sidecar Source Package for a saved source.

    Package creation must never corrupt the canonical text file. On failure
    the error string is returned (the canonical file is left intact);
    on success None is returned.
    """
    try:
        cleaning_profile = source_package.cleaning_profile_for(source_type)
        cleaner_version = source_package.cleaner_version_for(cleaning_profile)
        package = source_package.build_package(
            source_type=source_type,
            creator=creator,
            language=PROJECT_LANGUAGE,
            canonical_path=canonical_path,
            cleaning_profile=cleaning_profile,
            cleaner_version=cleaner_version,
            collection_id=collection_id,
            episode=episode,
            source_name=source_name,
            material_level=material_level,
            style_id=style_id,
            duration_seconds=duration_seconds,
        )
        source_package.write_package(package)
    except source_package.SourcePackageError as exc:
        return str(exc)
    return None


def create_collection_source(collection_id, episode, source_type, creator,
                             source_text, overwrite=False, material_level=0,
                             style_id=None, duration_seconds=None):
    """Validate and create a canonical collection source file."""
    errors = validate_collection_fields(collection_id, episode, source_type,
                                        creator, source_text)
    if errors:
        return {"success": False, "filename": None, "path": None,
                "errors": errors}

    episode_value = int(episode)
    path = source_path(collection_id, episode_value)

    if path.exists() and not overwrite:
        return {"success": False, "filename": path.name, "path": str(path),
                "errors": [f"source file already exists: {path.name}"]}

    _write_atomic(path, source_text)
    package_error = _try_write_source_package(
        source_type=source_type,
        creator=creator,
        canonical_path=path,
        collection_id=collection_id,
        episode=episode_value,
        material_level=material_level,
        style_id=style_id,
        duration_seconds=duration_seconds,
    )
    result = {"success": True, "filename": path.name, "path": str(path),
              "errors": []}
    if package_error:
        result["package_error"] = package_error
    return result


def create_standalone_source(source_name, source_type, creator, source_text,
                             overwrite=False, material_level=0,
                             style_id=None, duration_seconds=None):
    """Validate and create a canonical standalone source file."""
    errors = validate_standalone_fields(source_name, source_type, creator,
                                        source_text)
    if errors:
        return {"success": False, "filename": None, "path": None,
                "errors": errors}

    path = standalone_source_path(source_name)

    if path.exists() and not overwrite:
        return {"success": False, "filename": path.name, "path": str(path),
                "errors": [f"source file already exists: {path.name}"]}

    _write_atomic(path, source_text)
    package_error = _try_write_source_package(
        source_type=source_type,
        creator=creator,
        canonical_path=path,
        source_name=source_name,
        material_level=material_level,
        style_id=style_id,
        duration_seconds=duration_seconds,
    )
    result = {"success": True, "filename": path.name, "path": str(path),
              "errors": []}
    if package_error:
        result["package_error"] = package_error
    return result


def create_source(collection_id, episode, source_type, creator, source_text,
                  overwrite=False, material_level=None, style_id=None,
                  duration_seconds=None):
    """
    Validate and create a canonical collection source file.

    Retained for backward compatibility (collection mode).
    """
    return create_collection_source(collection_id, episode, source_type,
                                    creator, source_text, overwrite=overwrite,
                                    material_level=material_level,
                                    style_id=style_id,
                                    duration_seconds=duration_seconds)


# ============================================================
# Create Next Source state
# ============================================================

def next_source_state(identity_type, collection_id, episode,
                      source_type, creator, material_level=None,
                      style_id=None):
    """
    Prepare the state for the next source after a successful save.

    Retains stable metadata (identity type, collection, source_type, creator,
    material_level, style_id) and resets source-specific fields. Returns
    only state data; no file is created and no save occurs.

    Collection mode: suggests the next episode number (episode + 1).
    Standalone mode: blank source name.

    duration_seconds always resets to blank: each source's duration is
    distinct and never a sensible carryover default.

    Input:
        identity_type (str), collection_id (str), episode (int/str),
        source_type (str), creator (str), material_level (int|None),
        style_id (int|None).

    Output: dict:
        {
            "identity_type": str,
            "collection_id": str,   # retained or ""
            "episode": str,          # suggested next (collection) or ""
            "source_name": str,      # "" (standalone) or "" (collection)
            "source_type": str,
            "creator": str,
            "material_level": int | None,   # retained
            "style_id": int | None,         # retained
            "duration_seconds": "",         # always reset
            "source_text": "",       # always reset
        }
    """
    if identity_type == "standalone":
        return {
            "identity_type": "standalone",
            "collection_id": "",
            "episode": "",
            "source_name": "",
            "source_type": source_type,
            "creator": creator,
            "material_level": material_level,
            "style_id": style_id,
            "duration_seconds": "",
            "source_text": "",
        }

    # collection mode
    next_episode = ""
    if episode is not None and episode != "":
        try:
            next_episode = str(int(episode) + 1)
        except (TypeError, ValueError):
            next_episode = ""

    return {
        "identity_type": "collection",
        "collection_id": collection_id,
        "episode": next_episode,
        "source_name": "",
        "source_type": source_type,
        "creator": creator,
        "material_level": material_level,
        "style_id": style_id,
        "duration_seconds": "",
        "source_text": "",
    }


# ============================================================
# Auto sequence
# ============================================================

def next_auto_sequence(collection_id):
    """
    Return the next automatic sequence number for an "auto" collection.

    Scans the flat Sources root on every call and returns the maximum
    episode number already present (files matching the generate_filename
    pattern "<collection_id>_ep<digits>.txt") plus one. Returns 1 when the
    collection has no matching source files yet. Gaps are never filled;
    the result is always max + 1.

    This is a live filesystem scan on every call, not a persisted counter.

    Input: collection_id (str).
    Output: int (the next sequence number, always >= 1).
    """
    directory = SOURCES_ROOT
    prefix = f"{collection_id}_ep"
    highest = 0
    if directory.is_dir():
        for path in directory.iterdir():
            if not path.is_file():
                continue
            name = path.name
            if not name.startswith(prefix) or not name.endswith(".txt"):
                continue
            digits = name[len(prefix):-len(".txt")]
            if digits.isdigit():
                highest = max(highest, int(digits))
    return highest + 1


# ============================================================
# Ready State Engine
# ============================================================

READY_STATES = ("INCOMPLETE", "READY", "SAVED", "ERROR")


class ReadyStateEngine:
    """
    Controller-owned workflow state machine.

    The GUI never decides whether buttons are enabled; it asks this engine
    for the current state and derives all visual behaviour from it.

    States:
        INCOMPLETE  one or more required conditions are not satisfied
        READY       all required information exists; saving will succeed
        SAVED       a successful save has completed
        ERROR       an unexpected runtime failure occurred
    """

    def __init__(self):
        self._saved_snapshot = None
        self._error_message = None

    def reset(self):
        """Return to INCOMPLETE (Create Next / startup / error recovery)."""
        self._saved_snapshot = None
        self._error_message = None

    def mark_saved(self, snapshot):
        """
        Record a successful save.

        Input: snapshot dict:
            {
                "identity_type": str,
                "collection_id": str,
                "source_name": str,
                "episode": str,
                "source_type": str,
                "creator": str,
                "source_text": str,
                "filename": str,
                "material_level": int | None,   # optional
                "style_id": int | None,         # optional
                "duration_seconds": int | float | None,  # optional
            }
        The engine returns SAVED only while the form still matches this
        snapshot (i.e. until the user edits a field).
        """
        self._saved_snapshot = dict(snapshot)
        self._error_message = None

    def set_error(self, message):
        """Record an unexpected runtime failure."""
        self._error_message = str(message)

    def evaluate(self, identity_type, collection_id, source_name, episode,
                 source_type, creator, source_text, material_level=0,
                 style_id=None, duration_seconds=None):
        """
        Return the current workflow state for the given form fields.

        material_level is mandatory: the engine stays INCOMPLETE until a
        level is supplied. style_id and duration_seconds are optional; they
        are tracked in the saved snapshot but never block.

        Output: dict:
            {
                "state": "INCOMPLETE" | "READY" | "SAVED" | "ERROR",
                "message": str,       # human-readable status / blocking reason
                "save_enabled": bool,
                "next_enabled": bool,
                "saved_filename": str | None,
            }
        """
        if self._error_message is not None:
            return {
                "state": "ERROR",
                "message": self._error_message,
                "save_enabled": False,
                "next_enabled": False,
                "saved_filename": None,
            }

        if self._saved_snapshot is not None and self._matches_saved(
                identity_type, collection_id, source_name, episode,
                source_type, creator, source_text, material_level, style_id,
                duration_seconds):
            return {
                "state": "SAVED",
                "message": "Saved successfully.",
                "save_enabled": False,
                "next_enabled": True,
                "saved_filename": self._saved_snapshot["filename"],
            }

        blocking = self._first_blocking_reason(
            identity_type, collection_id, source_name, episode,
            source_type, creator, source_text, material_level)
        if blocking is not None:
            return {
                "state": "INCOMPLETE",
                "message": blocking,
                "save_enabled": False,
                "next_enabled": False,
                "saved_filename": None,
            }

        return {
            "state": "READY",
            "message": "Ready to Save.",
            "save_enabled": True,
            "next_enabled": False,
            "saved_filename": None,
        }

    def _matches_saved(self, identity_type, collection_id, source_name,
                       episode, source_type, creator, source_text,
                       material_level=None, style_id=None,
                       duration_seconds=None):
        snap = self._saved_snapshot
        return (
            identity_type == snap["identity_type"]
            and (collection_id or "") == (snap.get("collection_id") or "")
            and (source_name or "") == (snap.get("source_name") or "")
            and (episode or "") == (snap.get("episode") or "")
            and (source_type or "") == (snap.get("source_type") or "")
            and (creator or "") == (snap.get("creator") or "")
            and (source_text or "") == (snap.get("source_text") or "")
            and _snapshot_or_blank(material_level) == _snapshot_or_blank(
                snap.get("material_level", 0))
            and _snapshot_or_blank(style_id) == _snapshot_or_blank(
                snap.get("style_id"))
            and _snapshot_or_blank(duration_seconds) == _snapshot_or_blank(
                snap.get("duration_seconds"))
        )

    def _first_blocking_reason(self, identity_type, collection_id,
                               source_name, episode, source_type, creator,
                               source_text, material_level=None):
        """Return the first blocking reason string, or None when ready."""
        if identity_type not in IDENTITY_TYPES:
            return "Waiting for identity type."

        if identity_type == "collection":
            if not collection_id:
                return "Waiting for collection."
            if episode is None or episode == "":
                return "Waiting for episode number."
            try:
                episode_value = int(episode)
            except (TypeError, ValueError):
                return "Episode number must be an integer."
            if episode_value < 0:
                return "Episode number must be non-negative."
        else:
            if not source_name:
                return "Waiting for source name."

        if not source_type:
            return "Waiting for source type."
        if not creator:
            return "Waiting for creator."
        if material_level is None:
            return "Waiting for material level."
        if source_text is None or source_text.strip() == "":
            return "Waiting for source text."
        if not source_package.is_processable_source_type(source_type):
            return ("That source type is not currently available for "
                    "processing.")

        if identity_type == "collection":
            if collision_exists(collection_id, int(episode)):
                return "Filename already exists."
        else:
            if standalone_collision_exists(source_name):
                return "Filename already exists."

        return None


__all__ = [
    "SOURCES_ROOT",
    "IDENTITY_TYPES",
    "PROJECT_LANGUAGE",
    "READY_STATES",
    "SourceBuilderError",
    "generate_filename",
    "generate_standalone_filename",
    "source_path",
    "standalone_source_path",
    "validate_fields",
    "validate_collection_fields",
    "validate_standalone_fields",
    "collision_exists",
    "standalone_collision_exists",
    "create_source",
    "create_collection_source",
    "create_standalone_source",
    "next_source_state",
    "next_auto_sequence",
    "source_id_for",
    "ReadyStateEngine",
]
