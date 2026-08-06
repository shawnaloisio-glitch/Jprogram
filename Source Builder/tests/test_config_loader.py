#!/usr/bin/env python3
"""
test_config_loader.py

Deterministic tests for the Source Builder config loader:

- load_collections returns collection_id / name / sequencing,
- sequencing defaults to "episodic" when a collection does not declare it,
- explicit "auto" / "episodic" values are read back,
- empty and missing collection configs load as empty lists,
- collection ordering is preserved.

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


def patch_vocab_config(source_types, origins):
    """Point config_loader.CONFIG_DIR and paths.ORIGINS_CONFIG at a sandbox."""
    saved = (config_loader.CONFIG_DIR, paths.ORIGINS_CONFIG)
    tmp = pathlib.Path(tempfile.mkdtemp())
    config_dir = tmp / "Config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "source_types.json").write_text(
        json.dumps({"source_types": source_types}), encoding="utf-8")
    origins_file = config_dir / "origins.json"
    origins_file.write_text(
        json.dumps({"origins": origins}), encoding="utf-8")
    config_loader.CONFIG_DIR = config_dir
    paths.ORIGINS_CONFIG = origins_file

    def restore():
        config_loader.CONFIG_DIR, paths.ORIGINS_CONFIG = saved

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


@test("load_collections: returns the canonical fields")
def _():
    restore = patch_collections_config([
        {"collection_id": "teppei_beginner",
         "name": "Con Teppei for Beginner",
         "sequencing": "auto"},
    ])
    try:
        items = config_loader.load_collections()
        check("one collection", len(items) == 1)
        item = items[0]
        check("collection_id", item["collection_id"] == "teppei_beginner")
        check("name", item["name"] == "Con Teppei for Beginner")
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
        check("legacy source_type ignored", "source_type" not in items[0])
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


@test("load_origins: missing origins file loads empty")
def _():
    saved = paths.ORIGINS_CONFIG
    missing = pathlib.Path(tempfile.mkdtemp()) / "Config" / "origins.json"
    paths.ORIGINS_CONFIG = missing
    try:
        check("load_origins empty", config_loader.load_origins() == [])
        check("load_origins_full empty",
              config_loader.load_origins_full() == [])
    finally:
        paths.ORIGINS_CONFIG = saved


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


@test("load_source_types_full: returns id + display_name pairs in order")
def _():
    restore = patch_vocab_config(
        [{"source_type_id": "clean_text",
          "display_name": "Podcast Transcript"},
         {"source_type_id": "cij_transcript",
          "display_name": "CIJ Transcripts"}],
        [])
    try:
        entries = config_loader.load_source_types_full()
        check("order",
              [e["source_type_id"] for e in entries]
              == ["clean_text", "cij_transcript"])
        check("display name 1",
              entries[0]["display_name"] == "Podcast Transcript")
        check("display name 2",
              entries[1]["display_name"] == "CIJ Transcripts")
    finally:
        restore()


@test("load_origins_full: returns id + display_name pairs in order")
def _():
    restore = patch_vocab_config(
        [],
        [{"origin_id": "cijsub", "display_name": "CiJapanese Subs"},
         {"origin_id": "nhk_news", "display_name": "nhk_news"}])
    try:
        entries = config_loader.load_origins_full()
        check("order", [e["origin_id"] for e in entries]
              == ["cijsub", "nhk_news"])
        check("display name 1", entries[0]["display_name"] == "CiJapanese Subs")
        check("display name 2", entries[1]["display_name"] == "nhk_news")
    finally:
        restore()


@test("full loaders fall back to the id when display_name is absent")
def _():
    restore = patch_vocab_config(
        ["clean_text",
         {"source_type_id": "article"},
         {"source_type_id": "manga_text", "display_name": ""}],
        ["con_teppei_podcast",
         {"origin_id": "nhk_news"},
         {"origin_id": "subtitle", "display_name": ""}])
    try:
        st = config_loader.load_source_types_full()
        check("plain string fallback",
              st[0]["display_name"] == "clean_text")
        check("missing display fallback", st[1]["display_name"] == "article")
        check("empty display fallback",
              st[2]["display_name"] == "manga_text")
        og = config_loader.load_origins_full()
        check("origin plain fallback",
              og[0]["display_name"] == "con_teppei_podcast")
        check("origin missing display fallback",
              og[1]["display_name"] == "nhk_news")
        check("origin empty display fallback",
              og[2]["display_name"] == "subtitle")
    finally:
        restore()


@test("id-only loaders are unchanged by the full loaders")
def _():
    restore = patch_vocab_config(
        [{"source_type_id": "clean_text",
          "display_name": "Podcast Transcript"}],
        [{"origin_id": "cijsub", "display_name": "CiJapanese Subs"}])
    try:
        check("source types ids",
              config_loader.load_source_types() == ["clean_text"])
        check("origins ids",
              config_loader.load_origins() == ["cijsub"])
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
