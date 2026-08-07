#!/usr/bin/env python3
"""
index_builder.py

Japanese Corpus Pipeline - standalone SQLite index builder.

Builds a disposable, rebuildable SQLite index over the existing Source
Package sidecars and Config artifacts. The index is a cache, never a
second source of truth: build_index() always performs a full rebuild
into a temp file and atomically replaces the live database.

No FOREIGN KEY constraints are declared because the index rebuilds from
potentially messy source data and must not hard-fail when a source
references a collection_id or creator_id that config no longer has.

material_level, style_id, and duration_seconds are reserved columns and
are always NULL in this task; the styles table stays schema only (zero
rows). This module is CLI-only and is not wired into any pipeline.

CLI:
    python Index\\index_builder.py
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

# Allow imports from the project root and Source Builder (project convention).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "Source Builder"))

import config_loader
import controller
import metadata_editor
import paths
import project_config

INDEX_FILENAME = "jprogram.db"
TEMP_FILENAME = "jprogram.db.tmp"

# Material levels come from the shared project_config constant (single
# source of truth); never read from a file.
MATERIAL_LEVELS = project_config.MATERIAL_LEVELS

# Exactly the five canonical tables. No FOREIGN KEY constraints.
SCHEMA_STATEMENTS = (
    """
    CREATE TABLE sources (
        source_id TEXT PRIMARY KEY,
        source_type TEXT,
        collection_id TEXT,
        episode INTEGER,
        source_name TEXT,
        creator_id TEXT,
        material_level INTEGER,
        style_id INTEGER,
        duration_seconds REAL,
        created_at TEXT
    )
    """,
    """
    CREATE TABLE collections (
        collection_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        sequencing TEXT
    )
    """,
    """
    CREATE TABLE creators (
        creator_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE material_levels (
        level INTEGER PRIMARY KEY,
        display_name TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE styles (
        style_id INTEGER PRIMARY KEY AUTOINCREMENT,
        display_name TEXT NOT NULL UNIQUE
    )
    """,
)

def _sources_root(workspace_root):
    """Return the Sources root scanned for source packages."""
    if workspace_root is not None:
        return Path(workspace_root) / "Sources"
    return controller.SOURCES_ROOT


def _collections_config_path(workspace_root):
    """Return the collections.json path, or None for the loader default."""
    if workspace_root is not None:
        return Path(workspace_root) / "Config" / "collections.json"
    return None


def _creators_config_path(workspace_root):
    """Return the creators.json path, or None for the loader default."""
    if workspace_root is not None:
        return Path(workspace_root) / "Config" / "creators.json"
    return None


def _populate_creators(conn, path):
    """Populate creators via the workspace-aware config_loader.

    config_loader resolves creators from the workspace
    (paths.CREATORS_CONFIG), the same customer-data location metadata_editor
    uses. The optional path is applied by temporarily pointing
    paths.CREATORS_CONFIG at it so sandboxed rebuilds (workspace_root=...)
    stay isolated.
    """
    saved = paths.CREATORS_CONFIG
    if path is not None:
        paths.CREATORS_CONFIG = path
    try:
        for creator in config_loader.load_creators_full():
            conn.execute(
                "INSERT INTO creators (creator_id, display_name) "
                "VALUES (?, ?)",
                (
                    creator.get("creator_id"),
                    creator.get("display_name"),
                ),
            )
    finally:
        paths.CREATORS_CONFIG = saved


def _indexes_dir(workspace_root):
    """Return the directory that receives the rebuilt index database."""
    if workspace_root is not None:
        return Path(workspace_root) / "indexes"
    return paths.INDEXES


def _read_source_package(package_file):
    """Read and validate a source package file; return dict or None."""
    try:
        package = json.loads(package_file.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    if not isinstance(package, dict) or not package.get("source_id"):
        return None
    return package


def _episode_value(value):
    """Coerce an episode to int, or None when missing/invalid."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _create_schema(conn):
    """Create the five canonical tables."""
    for statement in SCHEMA_STATEMENTS:
        conn.execute(statement)


def _seed_material_levels(conn):
    """Insert the fixed material level rows."""
    conn.executemany(
        "INSERT INTO material_levels (level, display_name) VALUES (?, ?)",
        MATERIAL_LEVELS,
    )


def _populate_collections(conn, path):
    """Populate collections from the tested metadata_editor loader."""
    for collection in metadata_editor.load_collections(path):
        conn.execute(
            "INSERT INTO collections (collection_id, display_name, sequencing) "
            "VALUES (?, ?, ?)",
            (
                collection.get("collection_id"),
                collection.get("display_name"),
                collection.get("sequencing"),
            ),
        )


def _populate_sources(conn, sources_root):
    """
    Populate sources from the flat Sources root's Source Package sidecars.

    Collection-mode packages contribute collection_id and episode; the
    source_name column stays NULL. Standalone packages contribute
    source_name; collection_id and episode stay NULL. material_level,
    style_id, and duration_seconds are always NULL (reserved for later
    work). Returns the number of package files skipped (unparseable or
    missing source_id).
    """
    skipped = 0
    if not sources_root.is_dir():
        return skipped
    for package_file in sources_root.glob("*.source.json"):
        package = _read_source_package(package_file)
        if package is None:
            skipped += 1
            continue
        collection_id = package.get("collection_id")
        if collection_id:
            episode = _episode_value(package.get("episode"))
            source_name = None
        else:
            episode = None
            source_name = package.get("source_name")
        conn.execute(
            "INSERT INTO sources ("
            "    source_id, source_type, collection_id, episode, source_name,"
            "    creator_id, material_level, style_id, duration_seconds,"
            "    created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                package.get("source_id"),
                package.get("source_type"),
                collection_id,
                episode,
                source_name,
                package.get("creator"),
                None,
                None,
                None,
                package.get("created_at"),
            ),
        )
    return skipped


def _table_counts(conn):
    """Return a dict of row counts per table."""
    return {
        "sources": conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
        "collections": conn.execute(
            "SELECT COUNT(*) FROM collections").fetchone()[0],
        "creators": conn.execute(
            "SELECT COUNT(*) FROM creators").fetchone()[0],
        "material_levels": conn.execute(
            "SELECT COUNT(*) FROM material_levels").fetchone()[0],
        "styles": conn.execute(
            "SELECT COUNT(*) FROM styles").fetchone()[0],
    }


def build_index(workspace_root=None):
    """
    Rebuild the SQLite index from scratch.

    Always a full rebuild, never an incremental update. The database is
    built into a temp file and atomically moved over the live database
    with os.replace; the live db is never opened and mutated in place.

    Input: workspace_root (Path|None). When None, the canonical locations
    are used (controller.SOURCES_ROOT, paths.INDEXES, and the loader
    default Config paths). When given, all inputs and the output index are
    derived from that root (Sources/, Config/, indexes/) so callers never
    touch the real Workspace.

    Output: dict summary with the row count written per table plus the
    number of source package files skipped as unparseable.
    """
    sources_root = _sources_root(workspace_root)
    indexes_dir = _indexes_dir(workspace_root)
    indexes_dir.mkdir(parents=True, exist_ok=True)
    target = indexes_dir / INDEX_FILENAME
    temp = indexes_dir / TEMP_FILENAME

    try:
        conn = sqlite3.connect(str(temp))
        try:
            _create_schema(conn)
            _seed_material_levels(conn)
            _populate_collections(conn,
                                  _collections_config_path(workspace_root))
            _populate_creators(conn, _creators_config_path(workspace_root))
            skipped = _populate_sources(conn, sources_root)
            conn.commit()
            counts = _table_counts(conn)
        finally:
            conn.close()
        os.replace(temp, target)
    except Exception:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    return {
        "sources": counts["sources"],
        "collections": counts["collections"],
        "creators": counts["creators"],
        "material_levels": counts["material_levels"],
        "styles": counts["styles"],
        "skipped": skipped,
        "db_path": str(target),
    }


def main():
    """Run one rebuild and print a plain-text summary to stdout."""
    summary = build_index()
    print("Index rebuild complete.")
    print(f"sources: {summary['sources']}")
    print(f"collections: {summary['collections']}")
    print(f"creators: {summary['creators']}")
    print(f"material_levels: {summary['material_levels']}")
    print(f"styles: {summary['styles']}")
    print(f"source packages skipped (unparseable): {summary['skipped']}")
    print(f"database: {summary['db_path']}")
    return 0


__all__ = [
    "INDEX_FILENAME",
    "TEMP_FILENAME",
    "MATERIAL_LEVELS",
    "SCHEMA_STATEMENTS",
    "build_index",
    "main",
]


if __name__ == "__main__":
    sys.exit(main())
