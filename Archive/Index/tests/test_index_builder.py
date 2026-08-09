#!/usr/bin/env python3
"""
test_index_builder.py

Deterministic tests for the standalone SQLite index builder.

Builds run against a sandboxed workspace root (temporary Sources root,
temporary Config with collections.json/creators.json, temporary indexes)
passed explicitly to build_index(); the real Workspace is never touched.

Coverage:
- empty workspace still produces the 5 tables with material_levels seeded
  and everything else empty,
- a mix of collection-mode and standalone-mode source packages populates
  sources correctly, including NULL handling,
- corrupt / missing-source_id .source.json files are skipped and counted,
- running build_index() twice in a row is idempotent with no leftover
  temp file.

Run:
    python Index\\tests\\test_index_builder.py
"""

import json
import pathlib
import sqlite3
import sys
import tempfile
from contextlib import contextmanager

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
INDEX_DIR = PROJECT_ROOT / "Index"
sys.path.insert(0, str(INDEX_DIR))

import index_builder

MATERIAL_LEVELS_EXPECTED = [
    (0, "Ungraded"),
    (1, "Absolute Beginner"),
    (2, "Beginner"),
    (3, "Intermediate"),
    (4, "Advanced"),
]


def make_workspace():
    """Create a temp workspace root with Sources/ and Config/; return root."""
    root = pathlib.Path(tempfile.mkdtemp())
    (root / "Sources").mkdir(parents=True, exist_ok=True)
    (root / "Config").mkdir(parents=True, exist_ok=True)
    return root


def write_collections_config(root, entries):
    path = root / "Config" / "collections.json"
    path.write_text(json.dumps({"collections": entries}, ensure_ascii=False),
                    encoding="utf-8")
    return path


def write_creators_config(root, entries):
    path = root / "Config" / "creators.json"
    path.write_text(json.dumps({"creators": entries}, ensure_ascii=False),
                    encoding="utf-8")
    return path


def write_source_package(root, package, filename):
    path = root / "Sources" / filename
    path.write_text(json.dumps(package, ensure_ascii=False), encoding="utf-8")
    return path


@contextmanager
def db(root):
    """Open the rebuilt index database; always closes the connection."""
    conn = sqlite3.connect(str(root / "indexes" / "jprogram.db"))
    try:
        yield conn
    finally:
        conn.close()


def table_names(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("empty workspace: five tables, material_levels seeded, others empty")
def _():
    root = make_workspace()
    summary = index_builder.build_index(workspace_root=root)
    with db(root) as conn:
        names = table_names(conn)
        for expected in ("sources", "collections", "creators",
                         "material_levels", "styles"):
            check(f"table {expected}", expected in names)
        levels = conn.execute(
            "SELECT level, display_name FROM material_levels "
            "ORDER BY level").fetchall()
        check("five levels", len(levels) == 5)
        check("seeded rows", levels == MATERIAL_LEVELS_EXPECTED)
        check("sources empty",
              conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 0)
        check("collections empty",
              conn.execute(
                  "SELECT COUNT(*) FROM collections").fetchone()[0] == 0)
        check("creators empty",
              conn.execute(
                  "SELECT COUNT(*) FROM creators").fetchone()[0] == 0)
        check("styles empty",
              conn.execute("SELECT COUNT(*) FROM styles").fetchone()[0] == 0)
    check("summary material_levels", summary["material_levels"] == 5)
    check("summary skipped zero", summary["skipped"] == 0)
    check("summary styles zero", summary["styles"] == 0)


@test("sources: collection and standalone populate with NULL handling")
def _():
    root = make_workspace()
    write_collections_config(root, [
        {"collection_id": "teppei_beginner",
         "name": "Con Teppei for Beginner",
         "source_type": "podcast_transcript", "sequencing": "episodic"},
    ])
    write_creators_config(root, ["con_teppei_podcast", "nhk_news"])
    write_source_package(root, {
        "source_id": "podcast_transcript_teppei-beginner_ep001",
        "source_type": "podcast_transcript",
        "creator": "con_teppei_podcast",
        "collection_id": "teppei_beginner",
        "episode": 1,
        "created_at": "2026-08-01T10:00:00",
    }, "teppei_beginner_ep0001.source.json")
    write_source_package(root, {
        "source_id": "article_nhk-weather",
        "source_type": "article",
        "creator": "nhk_news",
        "source_name": "nhk_weather",
        "created_at": "2026-08-02T10:00:00",
    }, "nhk_weather.source.json")

    summary = index_builder.build_index(workspace_root=root)
    check("two sources", summary["sources"] == 2)
    check("one collection", summary["collections"] == 1)
    check("two creators", summary["creators"] == 2)

    with db(root) as conn:
        rows = conn.execute(
            "SELECT source_id, collection_id, episode, source_name, "
            "creator_id, material_level, style_id, duration_seconds "
            "FROM sources ORDER BY source_id").fetchall()
        check("two rows", len(rows) == 2)
        collection_row = [r for r in rows if r[1] == "teppei_beginner"][0]
        check("collection episode", collection_row[2] == 1)
        check("collection source_name NULL", collection_row[3] is None)
        check("collection creator", collection_row[4] == "con_teppei_podcast")
        check("material_level NULL", collection_row[5] is None)
        check("style_id NULL", collection_row[6] is None)
        check("duration NULL", collection_row[7] is None)
        standalone_row = [r for r in rows if r[4] == "nhk_news"][0]
        check("standalone collection_id NULL", standalone_row[1] is None)
        check("standalone episode NULL", standalone_row[2] is None)
        check("standalone source_name", standalone_row[3] == "nhk_weather")

        collections = conn.execute(
            "SELECT collection_id, display_name FROM collections").fetchall()
        check("collection row", collections == [
            ("teppei_beginner", "Con Teppei for Beginner")])
        creators = conn.execute(
            "SELECT creator_id, display_name FROM creators "
            "ORDER BY creator_id").fetchall()
        check("creator rows", creators == [
            ("con_teppei_podcast", "con_teppei_podcast"),
            ("nhk_news", "nhk_news"),
        ])


@test("sources: corrupt and missing-source_id packages are skipped")
def _():
    root = make_workspace()
    write_source_package(root, {
        "source_id": "article_nhk-weather",
        "source_type": "article",
        "creator": "nhk_news",
        "source_name": "nhk_weather",
        "created_at": "2026-08-02T10:00:00",
    }, "nhk_weather.source.json")
    (root / "Sources" / "bad.source.json").write_text("{ not json",
                                                      encoding="utf-8")
    (root / "Sources" / "no_id.source.json").write_text(
        json.dumps({"source_type": "article"}), encoding="utf-8")

    summary = index_builder.build_index(workspace_root=root)
    check("one source inserted", summary["sources"] == 1)
    check("two skipped", summary["skipped"] == 2)
    with db(root) as conn:
        count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        check("sources table reflects insert", count == 1)


@test("rebuild twice is idempotent with no leftover temp file")
def _():
    root = make_workspace()
    write_collections_config(root, [
        {"collection_id": "teppei_beginner",
         "name": "Con Teppei for Beginner",
         "source_type": "podcast_transcript"},
    ])
    write_creators_config(root, ["con_teppei_podcast"])
    write_source_package(root, {
        "source_id": "podcast_transcript_teppei-beginner_ep001",
        "source_type": "podcast_transcript",
        "creator": "con_teppei_podcast",
        "collection_id": "teppei_beginner",
        "episode": 1,
        "created_at": "2026-08-01T10:00:00",
    }, "teppei_beginner_ep0001.source.json")

    first = index_builder.build_index(workspace_root=root)
    second = index_builder.build_index(workspace_root=root)
    check("same source count", first["sources"] == second["sources"])
    check("same collection count",
          first["collections"] == second["collections"])
    check("same creator count", first["creators"] == second["creators"])
    check("same skipped count", first["skipped"] == second["skipped"])
    check("no leftover temp",
          not (root / "indexes" / "jprogram.db.tmp").exists())
    with db(root) as conn:
        count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        check("no duplicate rows", count == first["sources"])
        distinct = conn.execute(
            "SELECT COUNT(DISTINCT source_id) FROM sources").fetchone()[0]
        check("distinct source_ids", distinct == first["sources"])


@test("material_levels seeds from the shared project_config constant")
def _():
    import project_config
    check("same object as project_config",
          index_builder.MATERIAL_LEVELS == project_config.MATERIAL_LEVELS)
    check("same five rows",
          list(index_builder.MATERIAL_LEVELS) == MATERIAL_LEVELS_EXPECTED)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    passed = 0
    failed = 0
    failures = []
    for name, fn in TESTS:
        try:
            fn()
            passed += 1
            print(f"  PASS  {name}")
        except AssertionError as ex:
            failed += 1
            failures.append((name, str(ex)))
            print(f"  FAIL  {name}: {ex}")
        except Exception as ex:
            failed += 1
            failures.append((name, f"{type(ex).__name__}: {ex}"))
            print(f"  FAIL  {name}: {type(ex).__name__}: {ex}")

    print()
    print(f"Tests: {len(TESTS)}  Passed: {passed}  Failed: {failed}")
    if failures:
        print("Failures:")
        for name, detail in failures:
            print(f"  - {name}: {detail}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
