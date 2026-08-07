#!/usr/bin/env python3
"""
recent_sources.py

Japanese Corpus Pipeline - Source Builder recent sources helper.

Derives the most recently saved sources from the existing Source Package
sidecars. The source packages are the authoritative source list; no separate
tracking database is created.

This module is GUI-free and deterministic so it can be unit tested.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Source Builder"))

MAX_RECENT = 10


def _read_package(package_file):
    """Read and validate a source package file; return (package, mtime) or None."""
    try:
        package = json.loads(package_file.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    if not isinstance(package, dict) or not package.get("source_id"):
        return None
    try:
        mtime = package_file.stat().st_mtime
    except OSError:
        mtime = 0.0
    return package, mtime


def recent_packages(sources_root=None, limit=MAX_RECENT):
    """
    Return the most recently created source packages, newest first.

    Uses the source package's created_at timestamp (ISO-8601, lexicographically
    sortable). When timestamps tie (same second), the package file's
    modification time breaks the tie so rapid saves keep a stable order.
    Packages without a created_at are ordered after dated ones.

    Input:
        sources_root (Path|None, default the canonical Sources\\ store),
        limit (int, default 10).

    Output: list of package dicts, newest first, at most `limit`.
    """
    if sources_root is not None:
        root = Path(sources_root)
    else:
        import controller as _controller
        root = _controller.SOURCES_ROOT

    items = []  # (package, mtime)
    if root.is_dir():
        for package_file in root.glob("*.source.json"):
            entry = _read_package(package_file)
            if entry is not None:
                items.append(entry)

    def sort_key(item):
        package, mtime = item
        created = package.get("created_at")
        if isinstance(created, str) and created:
            return (1, created, mtime)
        return (0, "", mtime)

    items.sort(key=sort_key, reverse=True)
    return [item[0] for item in items[:limit]]


def recent_labels(sources_root=None, limit=MAX_RECENT):
    """
    Return human-readable labels for the most recent sources, newest first.

    Uses processing_tab.human_label so labels match the Processing tab. Never
    exposes source_id or paths.

    Input: sources_root (Path|None), limit (int, default 10).
    Output: list of str.
    """
    import processing_tab
    labels = []
    for package in recent_packages(sources_root, limit=limit):
        labels.append(processing_tab.human_label(package))
    return labels


__all__ = [
    "MAX_RECENT",
    "recent_packages",
    "recent_labels",
]
