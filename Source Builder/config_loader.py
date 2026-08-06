#!/usr/bin/env python3
"""
config_loader.py

Japanese Corpus Pipeline - Source Builder config loader.

Loads controlled vocabulary from the project Config\\ folder for use as
GUI dropdown values. Machine-friendly names are the canonical values.

This module has no GUI dependencies and no pipeline imports.
"""

import json
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

import paths

CONFIG_DIR = paths.PROJECT_ROOT / "Config"

CONFIG_FILES = {
    "collections": "collections.json",
    "source_types": "source_types.json",
    "origins": "origins.json",
}


class ConfigError(Exception):
    """Raised when a config file is missing or malformed."""


def config_path(name):
    """Return the path for a named config file."""
    if name == "origins":
        # Origins are customer/runtime configuration in the workspace, like
        # collections; only source_types remains repository product config.
        return paths.ORIGINS_CONFIG
    return CONFIG_DIR / CONFIG_FILES[name]


def load_json(name):
    """
    Load a named config file as JSON.

    Input: name (str) - one of the CONFIG_FILES keys.
    Output: parsed JSON value.
    Raises: ConfigError if the file is missing or not valid JSON.
    """
    path = config_path(name)
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        raise ConfigError(f"config file unreadable: {path}: {exc}") from exc


def load_collections():
    """
    Load collection options from the customer workspace.

    Collections are customer/runtime configuration; they live at
    paths.COLLECTIONS_CONFIG (WORKSPACE_ROOT/Config/collections.json),
    separate from the repository product configuration.

    Returns a list of collection dicts:
        [{"collection_id": str, "name": str, "source_type": str,
          "sequencing": str}, ...]

    "sequencing" is "episodic" or "auto", defaulting to "episodic" when a
    collection does not declare it.
    """
    path = paths.COLLECTIONS_CONFIG
    if not path.is_file():
        # Collections are customer data in the workspace. A fresh install
        # has none yet; treat it as an empty collection list, not an error.
        return []
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        raise ConfigError(f"config file unreadable: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("collections.json must be a JSON object")
    collections = data.get("collections")
    if not isinstance(collections, list):
        raise ConfigError("collections.json must contain a 'collections' list")
    result = []
    for item in collections:
        if not isinstance(item, dict):
            continue
        collection_id = item.get("collection_id")
        if isinstance(collection_id, str) and collection_id:
            result.append({
                "collection_id": collection_id,
                "name": item.get("name", collection_id),
                "source_type": item.get("source_type"),
                "sequencing": item.get("sequencing", "episodic"),
            })
    return result


def load_collection_ids():
    """Return the ordered list of collection_id values."""
    return [c["collection_id"] for c in load_collections()]


def load_source_types():
    """
    Return the ordered list of source_type values.

    Accepts both plain-string entries and object entries
    {"source_type_id": str, "display_name": str}.
    """
    data = load_json("source_types")
    if isinstance(data, dict):
        values = data.get("source_types")
    else:
        values = data
    if not isinstance(values, list):
        raise ConfigError("source_types.json must contain a list")
    return [_vocab_id(v, "source_type_id") for v in values
            if _vocab_id(v, "source_type_id")]


def load_origins():
    """
    Return the ordered list of origin values.

    Origins are customer data in the workspace; a fresh install has no
    origins.json yet, which is an empty list, not an error (exactly like
    collections). Accepts both plain-string entries and object entries
    {"origin_id": str, "display_name": str}.
    """
    data = _load_origins_raw()
    if data is None:
        return []
    if isinstance(data, dict):
        values = data.get("origins")
    else:
        values = data
    if not isinstance(values, list):
        raise ConfigError("origins.json must contain a list")
    return [_vocab_id(v, "origin_id") for v in values
            if _vocab_id(v, "origin_id")]


def load_source_types_full():
    """
    Return the ordered list of source type entries WITH display names.

    Accepts both plain-string entries and object entries
    {"source_type_id": str, "display_name": str}. display_name falls back
    to the id when the entry is a bare string or omits/empties display_name.

    Returns:
        [{"source_type_id": str, "display_name": str}, ...]
    """
    data = load_json("source_types")
    if isinstance(data, dict):
        values = data.get("source_types")
    else:
        values = data
    if not isinstance(values, list):
        raise ConfigError("source_types.json must contain a list")
    return [_vocab_full(v, "source_type_id") for v in values
            if _vocab_full(v, "source_type_id")]


def load_origins_full():
    """
    Return the ordered list of origin entries WITH display names.

    Origins are customer data in the workspace; a fresh install has no
    origins.json yet, which is an empty list, not an error (exactly like
    collections). Accepts both plain-string entries and object entries
    {"origin_id": str, "display_name": str}. display_name falls back to
    the id when the entry is a bare string or omits/empties display_name.

    Returns:
        [{"origin_id": str, "display_name": str}, ...]
    """
    data = _load_origins_raw()
    if data is None:
        return []
    if isinstance(data, dict):
        values = data.get("origins")
    else:
        values = data
    if not isinstance(values, list):
        raise ConfigError("origins.json must contain a list")
    return [_vocab_full(v, "origin_id") for v in values
            if _vocab_full(v, "origin_id")]


def _load_origins_raw():
    """Read the origins payload, or None when no origins file exists yet.

    Origins are customer data; a fresh install has none, which reads as an
    empty list rather than an error. A corrupt file still raises.
    """
    path = config_path("origins")
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        raise ConfigError(f"config file unreadable: {path}: {exc}") from exc


def _vocab_id(item, key):
    """Extract the canonical id from a string or object vocabulary entry."""
    if isinstance(item, str):
        return item if item else None
    if isinstance(item, dict):
        value = item.get(key)
        return value if isinstance(value, str) and value else None
    return None


def _vocab_full(item, key):
    """Build a {key: id, "display_name": str} entry from a string or object
    vocabulary entry, or return None for an invalid entry.

    display_name falls back to the id when the entry is a bare string or
    omits/empties display_name.
    """
    vid = _vocab_id(item, key)
    if vid is None:
        return None
    display_name = vid
    if isinstance(item, dict):
        candidate = item.get("display_name")
        if isinstance(candidate, str) and candidate:
            display_name = candidate
    return {key: vid, "display_name": display_name}


def default_source_type_for_collection(collection_id):
    """
    Return the default source_type for a collection, or None.

    Uses the collection's declared source_type when present.
    """
    for collection in load_collections():
        if collection["collection_id"] == collection_id:
            return collection.get("source_type")
    return None


__all__ = [
    "CONFIG_DIR",
    "CONFIG_FILES",
    "ConfigError",
    "config_path",
    "load_json",
    "load_collections",
    "load_collection_ids",
    "load_source_types",
    "load_origins",
    "load_source_types_full",
    "load_origins_full",
    "default_source_type_for_collection",
]