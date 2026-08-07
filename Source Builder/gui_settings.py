#!/usr/bin/env python3
"""
gui_settings.py

Japanese Corpus Pipeline - Source Builder GUI settings persistence.

Stores user-level GUI state (source_type, creator, material_level) so it is
restored automatically when the Source Builder starts. Collection is
intentionally NOT persisted. Language is a project-level property, not
source metadata, so it is not stored here.

This module has no GUI dependencies and no pipeline imports.
"""

import json
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

import paths

SETTINGS_PATH = paths.PROJECT_ROOT / "Source Builder" / "gui_settings.json"

PERSISTED_KEYS = ("source_type", "creator", "material_level")


class SettingsError(Exception):
    """Raised when GUI settings cannot be read or written."""


def load_settings(path=None):
    """
    Load persisted GUI settings.

    Returns a dict with only the persisted keys present and holding
    non-empty strings. Missing/corrupt files silently yield default values
    (empty strings) rather than raising.
    """
    settings_path = Path(path) if path else SETTINGS_PATH
    defaults = {key: "" for key in PERSISTED_KEYS}
    if not settings_path.is_file():
        return defaults

    try:
        with settings_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return defaults

    if not isinstance(data, dict):
        return defaults

    result = dict(defaults)
    for key in PERSISTED_KEYS:
        value = data.get(key)
        if isinstance(value, str) and value:
            result[key] = value
    return result


def save_settings(settings, path=None):
    """
    Persist GUI settings.

    Input: settings (dict) containing zero or more of source_type, creator,
    material_level.
    Only non-empty string values are written. Atomic write convention.
    """
    settings_path = Path(path) if path else SETTINGS_PATH
    data = {}
    for key in PERSISTED_KEYS:
        value = settings.get(key)
        if isinstance(value, str) and value:
            data[key] = value

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    temp = settings_path.with_name(settings_path.name + ".tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            import os
            os.fsync(file.fileno())
        temp.replace(settings_path)
    except OSError as exc:
        raise SettingsError(f"cannot write settings: {settings_path}: {exc}") from exc


__all__ = [
    "SETTINGS_PATH",
    "PERSISTED_KEYS",
    "SettingsError",
    "load_settings",
    "save_settings",
]
