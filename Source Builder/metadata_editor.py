#!/usr/bin/env python3
"""
metadata_editor.py

Japanese Corpus Pipeline - Source Builder metadata editor data layer.

Manages the controlled vocabularies that populate Source Builder dropdowns
and Quick Presets: Collections, Source Types, and Origins.

Language is a project-level property and is NOT managed here.

This module is GUI-free and deterministic so it can be unit tested. It reads
and writes the existing Config files with atomic writes and a .bak backup
before modification.

Canonical on-disk forms (preserving the existing top-level structure):

- Config\\collections.json:
    {"collections": [{"collection_id": str, "name": str,
                      "sequencing": str}]}
  "name" is the display name; "sequencing" is "episodic" or "auto"
  (default "episodic" when absent).
- Config\\source_types.json:
    {"source_types": [{"source_type_id": str, "display_name": str}]}
  (plain-string entries are accepted on read for backward compatibility)
- Workspace Config\\origins.json (customer data, like collections):
    {"origins": [{"origin_id": str, "display_name": str}]}
  (plain-string entries are accepted on read for backward compatibility)
- Config\\styles.json:
    {"styles": [{"style_id": int, "display_name": str}]}
  (style ids are autoincrement; computed as max(existing ids, default=0) + 1
  on each add, never a persisted counter)
"""

import json
import os
import re
import shutil
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

import paths
import source_package

CONFIG_DIR = paths.PROJECT_ROOT / "Config"

FILES = {
    "collections": "collections.json",
    "source_types": "source_types.json",
    "origins": "origins.json",
    "styles": "styles.json",
}

MACHINE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")

SEQUENCING_VALUES = ("episodic", "auto")


class MetadataError(Exception):
    """Raised when metadata cannot be loaded, saved, or validated."""


def _config_path(name, path=None):
    """Return the config path for a named vocabulary.

    Collections and origins are customer/runtime configuration and resolve
    to the workspace (paths.COLLECTIONS_CONFIG / paths.ORIGINS_CONFIG) when
    no explicit path is given. source_types remains repository product
    configuration.
    """
    if path is not None:
        return Path(path)
    if name == "collections":
        return paths.COLLECTIONS_CONFIG
    if name == "origins":
        return paths.ORIGINS_CONFIG
    return CONFIG_DIR / FILES[name]


def _sibling_path(path, name):
    """Given a path to one config file, return the sibling's path."""
    if path is not None:
        return Path(path).with_name(FILES[name])
    if name == "collections":
        return paths.COLLECTIONS_CONFIG
    if name == "origins":
        return paths.ORIGINS_CONFIG
    return CONFIG_DIR / FILES[name]


def _read_json(path):
    """Read a config file as JSON; missing file -> None; corrupt -> raise."""
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        raise MetadataError(f"config file unreadable: {path}: {exc}") from exc


def _backup(path):
    """Copy the current file to <name>.bak before modification."""
    if path.is_file():
        backup_path = path.with_name(path.name + ".bak")
        shutil.copy2(path, backup_path)


def _write_json(path, data):
    """Write a config file atomically, backing up the previous version."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _backup(path)
    temp = path.with_name(path.name + ".tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        temp.replace(path)
    except OSError as exc:
        raise MetadataError(f"cannot write config file: {path}: {exc}") from exc


# ============================================================
# Loading (normalized views)
# ============================================================

def load_collections(path=None):
    """
    Load collections as a list of dicts:
        [{"collection_id": str, "display_name": str,
          "sequencing": str}, ...]
    """
    data = _read_json(_config_path("collections", path))
    if data is None:
        return []
    if not isinstance(data, dict):
        raise MetadataError("collections.json must be a JSON object")
    items = data.get("collections")
    if not isinstance(items, list):
        raise MetadataError("collections.json must contain a 'collections' list")
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        collection_id = item.get("collection_id")
        if not isinstance(collection_id, str) or not collection_id:
            continue
        display_name = item.get("name", collection_id)
        result.append({
            "collection_id": collection_id,
            "display_name": display_name if isinstance(display_name, str)
            else collection_id,
            "sequencing": item.get("sequencing", "episodic"),
        })
    return result


def load_source_types(path=None):
    """
    Load source types as a list of dicts:
        [{"source_type_id": str, "display_name": str}, ...]
    Accepts plain-string entries for backward compatibility.
    """
    data = _read_json(_config_path("source_types", path))
    if data is None:
        return []
    if isinstance(data, dict):
        values = data.get("source_types")
    else:
        values = data
    if not isinstance(values, list):
        raise MetadataError("source_types.json must contain a list")
    return [_item_to_named(values[i], "source_type_id") for i in
            range(len(values)) if _item_to_named(values[i], "source_type_id")]


def load_origins(path=None):
    """
    Load origins as a list of dicts:
        [{"origin_id": str, "display_name": str}, ...]
    Accepts plain-string entries for backward compatibility.
    """
    data = _read_json(_config_path("origins", path))
    if data is None:
        return []
    if isinstance(data, dict):
        values = data.get("origins")
    else:
        values = data
    if not isinstance(values, list):
        raise MetadataError("origins.json must contain a list")
    return [_item_to_named(values[i], "origin_id") for i in
            range(len(values)) if _item_to_named(values[i], "origin_id")]


def load_styles(path=None):
    """
    Load styles as a list of dicts:
        [{"style_id": int, "display_name": str}, ...]
    """
    data = _read_json(_config_path("styles", path))
    if data is None:
        return []
    if not isinstance(data, dict):
        raise MetadataError("styles.json must be a JSON object")
    items = data.get("styles")
    if not isinstance(items, list):
        raise MetadataError("styles.json must contain a 'styles' list")
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        style_id = item.get("style_id")
        if not isinstance(style_id, int) or isinstance(style_id, bool):
            continue
        display_name = item.get("display_name")
        result.append({
            "style_id": style_id,
            "display_name": display_name if isinstance(display_name, str)
            else str(style_id),
        })
    return result


def _item_to_named(item, key):
    """Normalize a string or dict entry into {key: str, display_name: str}."""
    if isinstance(item, str):
        return {key: item, "display_name": item}
    if isinstance(item, dict):
        value = item.get(key)
        if not isinstance(value, str) or not value:
            return None
        display_name = item.get("display_name", value)
        return {
            key: value,
            "display_name": display_name if isinstance(display_name, str)
            else value,
        }
    return None


def is_processable(source_type):
    """Return True when a source type has an active processing profile."""
    return source_package.is_processable_source_type(source_type)


# ============================================================
# Validation
# ============================================================

def is_valid_machine_id(value):
    """Machine-friendly naming rule: lowercase start, [a-z0-9_]*."""
    return isinstance(value, str) and bool(MACHINE_ID_RE.match(value))


def validate_id(value, label):
    """Validate a machine-friendly identifier; return list of errors."""
    errors = []
    if not value:
        errors.append(f"{label} is required")
    elif not isinstance(value, str):
        errors.append(f"{label} must be a string")
    elif not is_valid_machine_id(value):
        errors.append(
            f"{label} must be machine-friendly: lowercase letters, digits, "
            f"and underscores, starting with a letter")
    return errors


def validate_display_name(value, label):
    """Validate a required display name; return list of errors."""
    if not value or not str(value).strip():
        return [f"{label} is required"]
    return []


def _check_unique(value, existing, original=None, label=None):
    """Return an error if value duplicates another entry (ignoring original)."""
    if value and value != original and value in existing:
        if label:
            return [f"{label} '{value}' already exists"]
        return [f"{value} already exists"]
    return []


def validate_collection(collection_id, display_name, existing_ids,
                        original_id=None, sequencing=None,
                        existing_display_names=None,
                        original_display_name=None):
    """Validate a collection entry; return list of errors."""
    errors = validate_id(collection_id, "collection_id")
    errors += _check_unique(collection_id, existing_ids, original_id)
    errors += validate_display_name(display_name, "display_name")
    if existing_display_names is not None:
        normalized = display_name.strip() if isinstance(display_name, str) \
            else display_name
        errors += _check_unique(normalized, existing_display_names,
                                original_display_name, label="display name")
    if sequencing is not None and sequencing not in SEQUENCING_VALUES:
        errors.append(
            f"sequencing must be 'episodic' or 'auto' (got {sequencing!r})")
    return errors


def validate_source_type(source_type_id, display_name, existing_ids,
                         original_id=None, existing_display_names=None,
                         original_display_name=None):
    """Validate a source type entry; return list of errors."""
    errors = validate_id(source_type_id, "source_type_id")
    errors += _check_unique(source_type_id, existing_ids, original_id)
    errors += validate_display_name(display_name, "display_name")
    if existing_display_names is not None:
        normalized = display_name.strip() if isinstance(display_name, str) \
            else display_name
        errors += _check_unique(normalized, existing_display_names,
                                original_display_name, label="display name")
    return errors


def validate_origin(origin_id, display_name, existing_ids, original_id=None,
                    existing_display_names=None, original_display_name=None):
    """Validate an origin entry; return list of errors."""
    errors = validate_id(origin_id, "origin_id")
    errors += _check_unique(origin_id, existing_ids, original_id)
    errors += validate_display_name(display_name, "display_name")
    if existing_display_names is not None:
        normalized = display_name.strip() if isinstance(display_name, str) \
            else display_name
        errors += _check_unique(normalized, existing_display_names,
                                original_display_name, label="display name")
    return errors


def validate_style(display_name, existing_display_names):
    """Validate a style entry; return list of errors."""
    errors = validate_display_name(display_name, "display_name")
    normalized = display_name.strip() if isinstance(display_name, str) \
        else display_name
    errors += _check_unique(normalized, existing_display_names,
                            label="display name")
    return errors


# ============================================================
# Raw item helpers
# ============================================================

def _raw_collection(item):
    """Convert a normalized collection dict to its on-disk form."""
    return {
        "collection_id": item["collection_id"],
        "name": item["display_name"],
        "sequencing": item.get("sequencing", "episodic"),
    }


def _raw_source_type(item):
    return {"source_type_id": item["source_type_id"],
            "display_name": item["display_name"]}


def _raw_origin(item):
    return {"origin_id": item["origin_id"], "display_name": item["display_name"]}


def _raw_style(item):
    return {"style_id": item["style_id"], "display_name": item["display_name"]}


# ============================================================
# Persistence
# ============================================================

def _save(name, items, raw_fn, path):
    raw = [raw_fn(item) for item in items]
    data = {name: raw}
    _write_json(_config_path(name, path), data)


def save_collections(items, path=None):
    """Persist collections (normalized dicts). Returns the raw count."""
    _save("collections", items, _raw_collection, path)


def save_source_types(items, path=None):
    """Persist source types (normalized dicts). Returns the raw count."""
    _save("source_types", items, _raw_source_type, path)


def save_origins(items, path=None):
    """Persist origins (normalized dicts). Returns the raw count."""
    _save("origins", items, _raw_origin, path)


def save_styles(items, path=None):
    """Persist styles (normalized dicts). Returns the raw count."""
    _save("styles", items, _raw_style, path)


# ============================================================
# CRUD
# ============================================================

def add_collection(collection_id, display_name, path=None, sequencing=None):
    """Add a collection; raises MetadataError on invalid input."""
    items = load_collections(path)
    existing = [c["collection_id"] for c in items]
    existing_names = [c["display_name"] for c in items]
    errors = validate_collection(
        collection_id, display_name, existing, sequencing=sequencing,
        existing_display_names=existing_names)
    if errors:
        raise MetadataError("; ".join(errors))
    items.append({
        "collection_id": collection_id,
        "display_name": display_name.strip(),
        "sequencing": sequencing if sequencing is not None else "episodic",
    })
    save_collections(items, path)
    return items


def edit_collection(original_id, display_name, path=None, sequencing=None):
    """
    Edit a collection's editable fields by original_id.

    The collection_id is immutable after creation and cannot be changed.
    sequencing=None preserves the collection's existing value.
    """
    items = load_collections(path)
    for item in items:
        if item["collection_id"] == original_id:
            existing_ids = [c["collection_id"] for c in items]
            existing_names = [c["display_name"] for c in items]
            errors = validate_collection(
                item["collection_id"], display_name, existing_ids,
                original_id=item["collection_id"], sequencing=sequencing,
                existing_display_names=existing_names,
                original_display_name=item["display_name"])
            if errors:
                raise MetadataError("; ".join(errors))
            item["display_name"] = display_name.strip()
            if sequencing is not None:
                item["sequencing"] = sequencing
            break
    else:
        raise MetadataError(f"collection not found: {original_id}")
    save_collections(items, path)
    return items


def collection_has_sources(collection_id, sources_root=None):
    """Return True when any flat root source file belongs to this collection."""
    root = Path(sources_root) if sources_root else paths.SOURCES
    if not root.is_dir():
        return False
    return any(root.glob(f"{collection_id}_ep*.txt"))


def delete_collection(collection_id, path=None, presets=None,
                      sources_root=None):
    """
    Delete a collection; blocked when referenced by presets or by existing
    source files.
    """
    items = load_collections(path)
    references = preset_references(presets)
    if collection_id in references["collections"]:
        raise MetadataError(
            f"collection {collection_id} is referenced by a preset; "
            f"edit the preset first")
    if collection_has_sources(collection_id, sources_root):
        raise MetadataError(
            f"collection {collection_id} has existing source files and "
            f"cannot be deleted")
    remaining = [c for c in items if c["collection_id"] != collection_id]
    if len(remaining) == len(items):
        raise MetadataError(f"collection not found: {collection_id}")
    save_collections(remaining, path)
    return remaining


def add_source_type(source_type_id, display_name, path=None):
    """Add a source type; raises MetadataError on invalid input."""
    items = load_source_types(path)
    existing = [s["source_type_id"] for s in items]
    existing_names = [s["display_name"] for s in items]
    errors = validate_source_type(source_type_id, display_name, existing,
                                  existing_display_names=existing_names)
    if errors:
        raise MetadataError("; ".join(errors))
    items.append({"source_type_id": source_type_id,
                  "display_name": display_name.strip()})
    save_source_types(items, path)
    return items


def edit_source_type(original_id, display_name, path=None):
    """
    Edit a source type's display name by original_id.

    The source_type_id is immutable after creation and cannot be changed.
    """
    items = load_source_types(path)
    for item in items:
        if item["source_type_id"] == original_id:
            existing_ids = [s["source_type_id"] for s in items]
            existing_names = [s["display_name"] for s in items]
            errors = validate_source_type(
                item["source_type_id"], display_name, existing_ids,
                original_id=item["source_type_id"],
                existing_display_names=existing_names,
                original_display_name=item["display_name"])
            if errors:
                raise MetadataError("; ".join(errors))
            item["display_name"] = display_name.strip()
            break
    else:
        raise MetadataError(f"source type not found: {original_id}")
    save_source_types(items, path)
    return items


def delete_source_type(source_type_id, path=None, presets=None):
    """
    Delete a source type; blocked when referenced by presets.
    """
    items = load_source_types(path)
    references = preset_references(presets)
    if source_type_id in references["source_types"]:
        raise MetadataError(
            f"source type {source_type_id} is referenced by a preset; "
            f"edit the preset first")
    remaining = [s for s in items if s["source_type_id"] != source_type_id]
    if len(remaining) == len(items):
        raise MetadataError(f"source type not found: {source_type_id}")
    save_source_types(remaining, path)
    return remaining


def add_origin(origin_id, display_name, path=None):
    """Add an origin; raises MetadataError on invalid input."""
    items = load_origins(path)
    existing = [o["origin_id"] for o in items]
    existing_names = [o["display_name"] for o in items]
    errors = validate_origin(origin_id, display_name, existing,
                             existing_display_names=existing_names)
    if errors:
        raise MetadataError("; ".join(errors))
    items.append({"origin_id": origin_id, "display_name": display_name.strip()})
    save_origins(items, path)
    return items


def edit_origin(original_id, display_name, path=None):
    """
    Edit an origin's display name by original_id.

    The origin_id is immutable after creation and cannot be changed.
    """
    items = load_origins(path)
    for item in items:
        if item["origin_id"] == original_id:
            existing_ids = [o["origin_id"] for o in items]
            existing_names = [o["display_name"] for o in items]
            errors = validate_origin(
                item["origin_id"], display_name, existing_ids,
                original_id=item["origin_id"],
                existing_display_names=existing_names,
                original_display_name=item["display_name"])
            if errors:
                raise MetadataError("; ".join(errors))
            item["display_name"] = display_name.strip()
            break
    else:
        raise MetadataError(f"origin not found: {original_id}")
    save_origins(items, path)
    return items


def add_style(display_name, path=None):
    """
    Add a style; raises MetadataError on invalid input.

    The next style_id is computed as max(existing ids, default=0) + 1 on
    each add (a live scan, never a persisted counter).
    """
    items = load_styles(path)
    existing = [s["display_name"] for s in items]
    errors = validate_style(display_name, existing)
    if errors:
        raise MetadataError("; ".join(errors))
    next_id = max((s["style_id"] for s in items), default=0) + 1
    items.append({"style_id": next_id, "display_name": display_name.strip()})
    save_styles(items, path)
    return items


def edit_style(style_id, display_name, path=None):
    """
    Edit a style's display name by style_id.

    The style_id is autoincrement and immutable after creation.
    """
    items = load_styles(path)
    for item in items:
        if item["style_id"] == style_id:
            existing = [s["display_name"] for s in items
                        if s["style_id"] != style_id]
            errors = validate_style(display_name, existing)
            if errors:
                raise MetadataError("; ".join(errors))
            item["display_name"] = display_name.strip()
            break
    else:
        raise MetadataError(f"style not found: {style_id}")
    save_styles(items, path)
    return items


def delete_origin(origin_id, path=None, presets=None):
    """Delete an origin; blocked with a warning when referenced by presets."""
    items = load_origins(path)
    references = preset_references(presets)
    if origin_id in references["origins"]:
        raise MetadataError(
            f"origin {origin_id} is referenced by a preset; edit the preset "
            f"first")
    remaining = [o for o in items if o["origin_id"] != origin_id]
    if len(remaining) == len(items):
        raise MetadataError(f"origin not found: {origin_id}")
    save_origins(remaining, path)
    return remaining


# ============================================================
# Preset reference detection
# ============================================================

def preset_references(presets=None):
    """
    Return the vocabulary ids referenced by presets.

    Input: presets (iterable of preset dicts) or None.
    Output: dict with "collections", "source_types", "origins" sets.
    """
    references = {"collections": set(), "source_types": set(),
                  "origins": set()}
    if not presets:
        return references
    for preset in presets:
        if not isinstance(preset, dict):
            continue
        if preset.get("collection_id"):
            references["collections"].add(preset["collection_id"])
        if preset.get("source_type"):
            references["source_types"].add(preset["source_type"])
        if preset.get("origin"):
            references["origins"].add(preset["origin"])
    return references


__all__ = [
    "CONFIG_DIR",
    "FILES",
    "SEQUENCING_VALUES",
    "MetadataError",
    "is_valid_machine_id",
    "is_processable",
    "load_collections",
    "load_source_types",
    "load_origins",
    "load_styles",
    "save_collections",
    "save_source_types",
    "save_origins",
    "save_styles",
    "add_collection",
    "edit_collection",
    "delete_collection",
    "collection_has_sources",
    "add_source_type",
    "edit_source_type",
    "delete_source_type",
    "add_origin",
    "edit_origin",
    "delete_origin",
    "add_style",
    "edit_style",
    "preset_references",
]
