#!/usr/bin/env python3
"""
test_config_loader.py

Deterministic tests for the Source Builder config loader:

- load_collections returns collection_id / name / source_type / sequencing,
- sequencing defaults to "episodic" when a collection does not declare it,
- explicit "auto" / "episodic" values are read back,
- empty and missing collection configs load as empty lists,
- collection ordering is preserved,
- default_source_type_for_collection resolves through the loaded data.

Config is redirected to a sandboxed directory; the real workspace Config
file is never touched.

Run:
    python "Source Builder/tests/test_config_loader.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))
sys.path.insert(0, str(PROJECT_ROOT))

import config_loader
import paths


def patch_collections_config(collections):
    """Point paths.COLLECTIONS_CONFIG at a sandbox file; return restore fn."""
    saved = paths.COLLECTIONS_CONFIG
    tmp = pathlib.Path(tempfile.mkdtemp())
    config_dir = tmp / "Config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "collections.json"
    config_file.write_text(json.dumps({"collections": collections}),
                           encoding="utf-8")
    paths.COLLECTIONS_CONFIG = config_file

    def restore():
        paths.COLLECTIONS_CONFIG = saved

    return restore


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("load_collections: returns the four canonical fields")
def _():
    restore = patch_collections_config([
        {"collection_id": "teppei_beginner",
         "name": "Con Teppei for Beginner",
         "source_type": "podcast_transcript",
         "sequencing": "auto"},
    ])
    try:
        items = config_loader.load_collections()
        check("one collection", len(items) == 1)
        item = items[0]
        check("collection_id", item["collection_id"] == "teppei_beginner")
        check("name", item["name"] == "Con Teppei for Beginner")
        check("source_type", item["source_type"] == "podcast_transcript")
        check("sequencing", item["sequencing"] == "auto")
    finally:
        restore()


@test("load_collections: sequencing defaults to episodic when absent")
def _():
    restore = patch_collections_config([
        {"collection_id": "cijapanese", "name": "CI Japanese",
         "source_type": "cij_transcript"},
    ])
    try:
        items = config_loader.load_collections()
        check("one collection", len(items) == 1)
        check("default sequencing", items[0]["sequencing"] == "episodic")
    finally:
        restore()


@test("load_collections: reads explicit episodic and auto values")
def _():
    restore = patch_collections_config([
        {"collection_id": "episodic_series", "name": "Episodic Series",
         "sequencing": "episodic"},
        {"collection_id": "auto_series", "name": "Auto Series",
         "sequencing": "auto"},
    ])
    try:
        items = config_loader.load_collections()
        by_id = {c["collection_id"]: c for c in items}
        check("episodic preserved",
              by_id["episodic_series"]["sequencing"] == "episodic")
        check("auto preserved", by_id["auto_series"]["sequencing"] == "auto")
    finally:
        restore()


@test("load_collections: empty list loads empty")
def _():
    restore = patch_collections_config([])
    try:
        check("empty", config_loader.load_collections() == [])
    finally:
        restore()


@test("load_collections: missing config file loads empty")
def _():
    saved = paths.COLLECTIONS_CONFIG
    missing = pathlib.Path(tempfile.mkdtemp()) / "Config" / "collections.json"
    paths.COLLECTIONS_CONFIG = missing
    try:
        check("empty", config_loader.load_collections() == [])
    finally:
        paths.COLLECTIONS_CONFIG = saved


@test("load_collections: ordering preserved")
def _():
    restore = patch_collections_config([
        {"collection_id": "b", "name": "B"},
        {"collection_id": "a", "name": "A"},
        {"collection_id": "c", "name": "C"},
    ])
    try:
        items = config_loader.load_collections()
        check("order",
              [c["collection_id"] for c in items] == ["b", "a", "c"])
    finally:
        restore()


@test("default_source_type_for_collection resolves via loaded data")
def _():
    restore = patch_collections_config([
        {"collection_id": "teppei_beginner",
         "name": "Con Teppei for Beginner",
         "source_type": "podcast_transcript"},
    ])
    try:
        check("resolved",
              config_loader.default_source_type_for_collection(
                  "teppei_beginner") == "podcast_transcript")
        check("unknown collection",
              config_loader.default_source_type_for_collection(
                  "missing") is None)
    finally:
        restore()


@test("load_collection_ids reflects collections in order")
def _():
    restore = patch_collections_config([
        {"collection_id": "b", "name": "B"},
        {"collection_id": "a", "name": "A"},
    ])
    try:
        check("ids", config_loader.load_collection_ids() == ["b", "a"])
    finally:
        restore()


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
