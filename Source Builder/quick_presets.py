#!/usr/bin/env python3
"""
quick_presets.py

Japanese Corpus Pipeline - Source Builder quick presets storage.

Presets are one-shot field-population templates. They are NOT linked state
and are NOT live bindings: after a preset is applied, the preset has no
further control over the form. Presets reference existing Config vocabulary
values (collection_id, source_type, creator); they never duplicate full
metadata. Resolution against Config tables happens at population time.

Language is a project-level property, not source metadata, and is never
stored in a preset.

This module has no GUI dependencies and no pipeline imports.
"""

import json
import os
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

import paths

PRESETS_PATH = paths.PROJECT_ROOT / "Source Builder" / "quick_presets.json"

SLOT_COUNT = 6
EMPTY_SLOT_NAME = "Empty Slot"
IDENTITY_TYPES = ("collection", "standalone")
PRESET_KEYS = (
    "slot", "display_name", "identity_type", "collection_id", "source_name",
    "source_type", "creator",
)


class PresetError(Exception):
    """Raised when a preset cannot be saved or loaded."""


def _as_str(value):
    return value if isinstance(value, str) else ""


def empty_slots():
    """Return a dict mapping slots 1..SLOT_COUNT to None."""
    return {slot: None for slot in range(1, SLOT_COUNT + 1)}


def _normalize_preset(item):
    """Validate/normalize a single preset dict; return None if invalid."""
    if not isinstance(item, dict):
        return None
    identity_type = item.get("identity_type")
    if identity_type not in IDENTITY_TYPES:
        return None
    display_name = _as_str(item.get("display_name")).strip()
    if not display_name:
        return None
    return {
        "slot": item.get("slot"),
        "display_name": display_name,
        "identity_type": identity_type,
        "collection_id": _as_str(item.get("collection_id")),
        "source_name": _as_str(item.get("source_name")),
        "source_type": _as_str(item.get("source_type")),
        "creator": _as_str(item.get("creator")),
    }


def load_presets(path=None):
    """
    Load all presets.

    Returns a dict mapping slots 1..SLOT_COUNT to a preset dict (or None for
    empty slots). Missing or corrupt files silently yield all-empty slots.
    """
    presets_path = Path(path) if path else PRESETS_PATH
    result = empty_slots()
    if not presets_path.is_file():
        return result
    try:
        with presets_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return result
    if not isinstance(data, dict):
        return result
    items = data.get("presets")
    if not isinstance(items, list):
        return result
    for item in items:
        preset = _normalize_preset(item)
        if preset is None:
            continue
        slot = preset["slot"]
        if isinstance(slot, int) and slot in result:
            result[slot] = preset
    return result


def load_slot(slot, path=None):
    """Return the preset for a slot, or None when empty."""
    return load_presets(path).get(slot)


def save_slot(slot, display_name, identity_type, collection_id="",
              source_name="", source_type="", creator="", path=None):
    """
    Validate and save a single preset slot (atomic write).

    Raises PresetError on invalid input. Returns the updated presets dict.
    """
    if slot not in range(1, SLOT_COUNT + 1):
        raise PresetError(f"preset slot must be 1-{SLOT_COUNT}")
    if not display_name or not display_name.strip():
        raise PresetError("display name is required")
    if identity_type not in IDENTITY_TYPES:
        raise PresetError("identity type must be collection or standalone")
    if identity_type == "collection" and not collection_id:
        raise PresetError("collection is required for a collection preset")

    presets = load_presets(path)
    presets[slot] = {
        "slot": slot,
        "display_name": display_name.strip(),
        "identity_type": identity_type,
        "collection_id": _as_str(collection_id),
        "source_name": _as_str(source_name),
        "source_type": _as_str(source_type),
        "creator": _as_str(creator),
    }
    _write_presets(presets, path)
    return presets


def _write_presets(presets, path):
    presets_path = Path(path) if path else PRESETS_PATH
    items = [presets[slot] for slot in range(1, SLOT_COUNT + 1)
             if presets.get(slot) is not None]
    data = {"presets": items}
    presets_path.parent.mkdir(parents=True, exist_ok=True)
    temp = presets_path.with_name(presets_path.name + ".tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        temp.replace(presets_path)
    except OSError as exc:
        raise PresetError(
            f"cannot write presets: {presets_path}: {exc}") from exc


def preset_population(preset, collection_ids, source_types, creators):
    """
    Compute the one-shot field updates a preset applies (pure, testable).

    Only values that exist in the given Config vocabularies are applied.

    Input:
        preset (dict|None),
        collection_ids (list of str),
        source_types (list of str),
        creators (list of str).

    Output: dict with any of identity_type, collection_id, source_type,
    creator keys that should be populated. Empty dict when nothing applies.
    A standalone preset never populates source_name: presets are reusable
    templates (source_type/creator), not pinned to one specific source name.
    """
    if not isinstance(preset, dict):
        return {}
    identity_type = preset.get("identity_type")
    if identity_type not in IDENTITY_TYPES:
        return {}

    updates = {"identity_type": identity_type}

    if identity_type == "collection":
        if preset.get("collection_id") in collection_ids:
            updates["collection_id"] = preset["collection_id"]

    source_type = preset.get("source_type")
    if source_type in source_types:
        updates["source_type"] = source_type

    if preset.get("creator") in creators:
        updates["creator"] = preset["creator"]

    return updates


__all__ = [
    "PRESETS_PATH",
    "SLOT_COUNT",
    "EMPTY_SLOT_NAME",
    "IDENTITY_TYPES",
    "PRESET_KEYS",
    "PresetError",
    "empty_slots",
    "load_presets",
    "load_slot",
    "save_slot",
    "preset_population",
]
