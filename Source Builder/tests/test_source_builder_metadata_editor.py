#!/usr/bin/env python3
"""
test_source_builder_metadata_editor.py

Deterministic tests for the Source Builder metadata editor data layer:

- Collections: load, add, edit, duplicate rejection, delete validation,
  preset reference protection, sequencing default/validation.
- Source Types: add/edit/delete validation.
- Origins: add/edit/delete validation.
- Config persistence: save, reload, atomic write, backup, format preservation.

All tests run against sandboxed Config directories; the real Config\\ files
are never touched.

Run:
    python "Source Builder/tests/test_source_builder_metadata_editor.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))

import metadata_editor


def temp_config_dir():
    root = pathlib.Path(tempfile.mkdtemp())
    return root / "Config"


def write_initial(conf_dir):
    """Write realistic initial config files."""
    conf_dir.mkdir(parents=True, exist_ok=True)
    (conf_dir / "collections.json").write_text(json.dumps({
        "collections": [
            {"collection_id": "teppei_beginner",
             "name": "Con Teppei for Beginner",
             "source_type": "clean_text"},
        ]
    }), encoding="utf-8")
    (conf_dir / "source_types.json").write_text(json.dumps({
        "source_types": ["clean_text", "subtitle", "article"],
    }), encoding="utf-8")
    (conf_dir / "origins.json").write_text(json.dumps({
        "origins": ["con_teppei_podcast", "nhk_news"],
    }), encoding="utf-8")


def conf_path(conf_dir, name):
    return conf_dir / metadata_editor.FILES[name]


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


# ============================================================
# Collections: load
# ============================================================

@test("collections: load from sandbox")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    items = metadata_editor.load_collections(conf_path(conf_dir, "collections"))
    check("one collection", len(items) == 1)
    check("id", items[0]["collection_id"] == "teppei_beginner")
    check("display name", items[0]["display_name"] == "Con Teppei for Beginner")
    check("default source type",
          items[0]["default_source_type"] == "clean_text")


@test("collections: missing file loads empty")
def _():
    conf_dir = temp_config_dir()
    items = metadata_editor.load_collections(conf_path(conf_dir, "collections"))
    check("empty", items == [])


# ============================================================
# Collections: add / edit / duplicate / delete
# ============================================================

@test("collections: add")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    items = metadata_editor.add_collection(
        "nhk_beginner", "NHK Beginner", default_source_type="article",
        path=conf_path(conf_dir, "collections"))
    check("two collections", len(items) == 2)
    check("added id", items[1]["collection_id"] == "nhk_beginner")
    # Reload from disk.
    reloaded = metadata_editor.load_collections(
        conf_path(conf_dir, "collections"))
    check("persisted", len(reloaded) == 2)
    check("persisted default",
          reloaded[1]["default_source_type"] == "article")


@test("collections: add duplicate rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.add_collection(
            "teppei_beginner", "Duplicate",
            path=conf_path(conf_dir, "collections"))
        check("duplicate rejected", False)
    except metadata_editor.MetadataError as exc:
        check("duplicate message", "already exists" in str(exc))


@test("collections: add missing id rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.add_collection(
            "", "No ID", path=conf_path(conf_dir, "collections"))
        check("empty id rejected", False)
    except metadata_editor.MetadataError as exc:
        check("required message", "collection_id is required" in str(exc))


@test("collections: add non-machine-friendly id rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.add_collection(
            "Bad ID!", "Bad", path=conf_path(conf_dir, "collections"))
        check("bad id rejected", False)
    except metadata_editor.MetadataError as exc:
        check("machine-friendly message", "machine-friendly" in str(exc))


@test("collections: add missing display name rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.add_collection(
            "new_col", "   ", path=conf_path(conf_dir, "collections"))
        check("empty display rejected", False)
    except metadata_editor.MetadataError as exc:
        check("display message", "display_name is required" in str(exc))


@test("collections: add unknown default source type rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.add_collection(
            "new_col", "New", default_source_type="nope",
            path=conf_path(conf_dir, "collections"),
            source_type_ids=["clean_text", "subtitle", "article"])
        check("unknown default rejected", False)
    except metadata_editor.MetadataError as exc:
        check("source type message", "not a known source type" in str(exc))


@test("collections: edit display name and default")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.edit_collection(
        "teppei_beginner", "Renamed",
        default_source_type="subtitle",
        path=conf_path(conf_dir, "collections"))
    reloaded = metadata_editor.load_collections(
        conf_path(conf_dir, "collections"))
    check("id unchanged", reloaded[0]["collection_id"] == "teppei_beginner")
    check("display changed", reloaded[0]["display_name"] == "Renamed")
    check("default changed", reloaded[0]["default_source_type"] == "subtitle")


@test("collections: id is immutable after creation")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    # Editing never accepts a new id; the id stays unchanged.
    metadata_editor.edit_collection(
        "teppei_beginner", "Renamed",
        path=conf_path(conf_dir, "collections"))
    reloaded = metadata_editor.load_collections(
        conf_path(conf_dir, "collections"))
    check("id unchanged", reloaded[0]["collection_id"] == "teppei_beginner")


@test("collections: edit missing original rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.edit_collection(
            "ghost", "Name", path=conf_path(conf_dir, "collections"))
        check("missing original rejected", False)
    except metadata_editor.MetadataError as exc:
        check("not found message", "not found" in str(exc))


@test("collections: load defaults sequencing to episodic")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    items = metadata_editor.load_collections(conf_path(conf_dir, "collections"))
    check("default sequencing", items[0]["sequencing"] == "episodic")


@test("collections: load reads explicit sequencing")
def _():
    conf_dir = temp_config_dir()
    conf_dir.mkdir(parents=True, exist_ok=True)
    (conf_dir / "collections.json").write_text(json.dumps({
        "collections": [
            {"collection_id": "cij_corpus", "name": "CIJ Corpus",
             "source_type": "clean_text", "sequencing": "auto"},
        ]
    }), encoding="utf-8")
    items = metadata_editor.load_collections(conf_path(conf_dir, "collections"))
    check("auto sequencing", items[0]["sequencing"] == "auto")


@test("collections: add defaults sequencing to episodic")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    items = metadata_editor.add_collection(
        "nhk_beginner", "NHK Beginner",
        path=conf_path(conf_dir, "collections"))
    check("added default sequencing", items[1]["sequencing"] == "episodic")
    reloaded = metadata_editor.load_collections(
        conf_path(conf_dir, "collections"))
    check("persisted default sequencing",
          reloaded[1]["sequencing"] == "episodic")


@test("collections: add accepts auto sequencing")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    items = metadata_editor.add_collection(
        "cij_corpus", "CIJ Corpus", sequencing="auto",
        path=conf_path(conf_dir, "collections"))
    check("added auto", items[1]["sequencing"] == "auto")
    reloaded = metadata_editor.load_collections(
        conf_path(conf_dir, "collections"))
    check("persisted auto", reloaded[1]["sequencing"] == "auto")


@test("collections: add rejects invalid sequencing")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.add_collection(
            "cij_corpus", "CIJ Corpus", sequencing="bogus",
            path=conf_path(conf_dir, "collections"))
        check("invalid sequencing rejected", False)
    except metadata_editor.MetadataError as exc:
        check("sequencing message",
              "sequencing must be 'episodic' or 'auto'" in str(exc))
    check("no partial add",
          len(metadata_editor.load_collections(
              conf_path(conf_dir, "collections"))) == 1)


@test("collections: edit preserves sequencing when not given")
def _():
    conf_dir = temp_config_dir()
    conf_dir.mkdir(parents=True, exist_ok=True)
    (conf_dir / "collections.json").write_text(json.dumps({
        "collections": [
            {"collection_id": "cij_corpus", "name": "CIJ Corpus",
             "source_type": "clean_text", "sequencing": "auto"},
        ]
    }), encoding="utf-8")
    metadata_editor.edit_collection(
        "cij_corpus", "CIJ Renamed",
        path=conf_path(conf_dir, "collections"))
    reloaded = metadata_editor.load_collections(
        conf_path(conf_dir, "collections"))
    check("display changed", reloaded[0]["display_name"] == "CIJ Renamed")
    check("sequencing preserved", reloaded[0]["sequencing"] == "auto")


@test("collections: edit updates sequencing when given")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.edit_collection(
        "teppei_beginner", "Renamed", sequencing="auto",
        path=conf_path(conf_dir, "collections"))
    reloaded = metadata_editor.load_collections(
        conf_path(conf_dir, "collections"))
    check("sequencing updated", reloaded[0]["sequencing"] == "auto")


@test("collections: edit rejects invalid sequencing")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.edit_collection(
            "teppei_beginner", "Renamed", sequencing="bogus",
            path=conf_path(conf_dir, "collections"))
        check("invalid sequencing rejected", False)
    except metadata_editor.MetadataError as exc:
        check("sequencing message",
              "sequencing must be 'episodic' or 'auto'" in str(exc))


@test("collections: sequencing round-trips to disk")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.add_collection(
        "cij_corpus", "CIJ Corpus", sequencing="auto",
        path=conf_path(conf_dir, "collections"))
    data = json.loads(conf_path(conf_dir, "collections").read_text(
        encoding="utf-8"))
    by_id = {c["collection_id"]: c for c in data["collections"]}
    check("new entry stores auto",
          by_id["cij_corpus"]["sequencing"] == "auto")
    check("legacy entry gains episodic",
          by_id["teppei_beginner"]["sequencing"] == "episodic")


@test("collections: delete unused")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.add_collection(
        "other_col", "Other", path=conf_path(conf_dir, "collections"))
    # Use a temp Sources dir so teppei_beginner has no source files.
    sources_root = pathlib.Path(tempfile.mkdtemp()) / "Sources"
    remaining = metadata_editor.delete_collection(
        "other_col", path=conf_path(conf_dir, "collections"),
        sources_root=sources_root)
    check("one remains", len(remaining) == 1)
    check("right one remains", remaining[0]["collection_id"] == "teppei_beginner")


@test("collections: delete with existing source files blocked")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    sources_root = pathlib.Path(tempfile.mkdtemp()) / "Sources"
    folder = sources_root / "collections" / "teppei_beginner"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "teppei_beginner_ep0001.txt").write_text("x\n",
                                                       encoding="utf-8")
    try:
        metadata_editor.delete_collection(
            "teppei_beginner", path=conf_path(conf_dir, "collections"),
            sources_root=sources_root)
        check("source-referenced delete blocked", False)
    except metadata_editor.MetadataError as exc:
        check("source message", "existing source files" in str(exc))


@test("collections: delete missing rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.delete_collection(
            "ghost", path=conf_path(conf_dir, "collections"))
        check("missing delete rejected", False)
    except metadata_editor.MetadataError as exc:
        check("not found message", "not found" in str(exc))


@test("collections: delete referenced by preset blocked")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    presets = [
        {"slot": 1, "identity_type": "collection",
         "collection_id": "teppei_beginner"},
    ]
    try:
        metadata_editor.delete_collection(
            "teppei_beginner", path=conf_path(conf_dir, "collections"),
            presets=presets)
        check("referenced delete blocked", False)
    except metadata_editor.MetadataError as exc:
        check("reference message", "referenced by a preset" in str(exc))


@test("collections: delete allowed when not referenced by presets")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.add_collection(
        "unused_col", "Unused", path=conf_path(conf_dir, "collections"))
    presets = [{"slot": 1, "identity_type": "collection",
                "collection_id": "teppei_beginner"}]
    sources_root = pathlib.Path(tempfile.mkdtemp()) / "Sources"
    remaining = metadata_editor.delete_collection(
        "unused_col", path=conf_path(conf_dir, "collections"),
        presets=presets, sources_root=sources_root)
    check("unused deleted", len(remaining) == 1)


# ============================================================
# Source Types: add / edit / delete validation
# ============================================================

@test("source types: load accepts object form")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    items = metadata_editor.load_source_types(
        conf_path(conf_dir, "source_types"))
    check("three source types", len(items) == 3)
    check("id", items[0]["source_type_id"] == "clean_text")
    check("display", items[0]["display_name"] == "clean_text")


@test("source types: add")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.add_source_type(
        "video", "Video", path=conf_path(conf_dir, "source_types"))
    reloaded = metadata_editor.load_source_types(
        conf_path(conf_dir, "source_types"))
    check("added", len(reloaded) == 4)
    check("added id", reloaded[3]["source_type_id"] == "video")
    check("added display", reloaded[3]["display_name"] == "Video")


@test("source types: add duplicate rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.add_source_type(
            "subtitle", "Subtitle", path=conf_path(conf_dir, "source_types"))
        check("duplicate rejected", False)
    except metadata_editor.MetadataError as exc:
        check("duplicate message", "already exists" in str(exc))


@test("source types: add bad id rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.add_source_type(
            "No Good", "NG", path=conf_path(conf_dir, "source_types"))
        check("bad id rejected", False)
    except metadata_editor.MetadataError as exc:
        check("machine-friendly message", "machine-friendly" in str(exc))


@test("source types: edit display name only")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.edit_source_type(
        "subtitle", "Subtitles",
        path=conf_path(conf_dir, "source_types"))
    reloaded = metadata_editor.load_source_types(
        conf_path(conf_dir, "source_types"))
    check("id unchanged", reloaded[1]["source_type_id"] == "subtitle")
    check("display changed", reloaded[1]["display_name"] == "Subtitles")


@test("source types: id is immutable after creation")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.edit_source_type(
        "subtitle", "Subtitles", path=conf_path(conf_dir, "source_types"))
    reloaded = metadata_editor.load_source_types(
        conf_path(conf_dir, "source_types"))
    check("id unchanged", reloaded[1]["source_type_id"] == "subtitle")


@test("source types: delete referenced by preset blocked")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    presets = [{"slot": 1, "source_type": "subtitle"}]
    try:
        metadata_editor.delete_source_type(
            "subtitle", path=conf_path(conf_dir, "source_types"),
            presets=presets)
        check("referenced delete blocked", False)
    except metadata_editor.MetadataError as exc:
        check("reference message", "referenced by a preset" in str(exc))


@test("source types: delete default of a collection with sources blocked")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    # teppei_beginner uses clean_text as its default.
    sources_root = pathlib.Path(tempfile.mkdtemp()) / "Sources"
    folder = sources_root / "collections" / "teppei_beginner"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "teppei_beginner_ep0001.txt").write_text("x\n",
                                                       encoding="utf-8")
    try:
        metadata_editor.delete_source_type(
            "clean_text",
            path=conf_path(conf_dir, "source_types"),
            sources_root=sources_root)
        check("default delete blocked", False)
    except metadata_editor.MetadataError as exc:
        check("default message", "default source type" in str(exc))


@test("source types: delete default of a source-less collection allowed")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    # teppei_beginner declares clean_text but has no source files.
    sources_root = pathlib.Path(tempfile.mkdtemp()) / "Sources"
    remaining = metadata_editor.delete_source_type(
        "clean_text",
        path=conf_path(conf_dir, "source_types"),
        sources_root=sources_root)
    check("deleted when no source files", len(remaining) == 2)


@test("source types: delete unused allowed")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.add_source_type(
        "unused_type", "Unused", path=conf_path(conf_dir, "source_types"))
    sources_root = pathlib.Path(tempfile.mkdtemp()) / "Sources"
    remaining = metadata_editor.delete_source_type(
        "unused_type", path=conf_path(conf_dir, "source_types"),
        sources_root=sources_root)
    check("unused deleted", len(remaining) == 3)


# ============================================================
# Origins: add / edit / delete validation
# ============================================================

@test("origins: add")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.add_origin(
        "nhk_radio", "NHK Radio", path=conf_path(conf_dir, "origins"))
    reloaded = metadata_editor.load_origins(conf_path(conf_dir, "origins"))
    check("added", len(reloaded) == 3)
    check("added id", reloaded[2]["origin_id"] == "nhk_radio")
    check("added display", reloaded[2]["display_name"] == "NHK Radio")


@test("origins: edit display name only")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.edit_origin(
        "nhk_news", "NHK News JP", path=conf_path(conf_dir, "origins"))
    reloaded = metadata_editor.load_origins(conf_path(conf_dir, "origins"))
    check("id unchanged", reloaded[1]["origin_id"] == "nhk_news")
    check("display changed", reloaded[1]["display_name"] == "NHK News JP")


@test("origins: id is immutable after creation")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.edit_origin(
        "nhk_news", "Renamed", path=conf_path(conf_dir, "origins"))
    reloaded = metadata_editor.load_origins(conf_path(conf_dir, "origins"))
    check("id unchanged", reloaded[1]["origin_id"] == "nhk_news")


@test("origins: duplicate rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.add_origin(
            "nhk_news", "NHK News", path=conf_path(conf_dir, "origins"))
        check("duplicate rejected", False)
    except metadata_editor.MetadataError as exc:
        check("duplicate message", "already exists" in str(exc))


@test("origins: bad id rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.add_origin(
            "1bad", "Bad", path=conf_path(conf_dir, "origins"))
        check("bad id rejected", False)
    except metadata_editor.MetadataError as exc:
        check("machine-friendly message", "machine-friendly" in str(exc))


@test("origins: delete referenced by preset blocked")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    presets = [{"slot": 1, "origin": "nhk_news"}]
    try:
        metadata_editor.delete_origin(
            "nhk_news", path=conf_path(conf_dir, "origins"), presets=presets)
        check("referenced delete blocked", False)
    except metadata_editor.MetadataError as exc:
        check("reference message", "referenced by a preset" in str(exc))


@test("origins: delete unused allowed")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.add_origin(
        "extra_origin", "Extra", path=conf_path(conf_dir, "origins"))
    remaining = metadata_editor.delete_origin(
        "extra_origin", path=conf_path(conf_dir, "origins"))
    check("unused deleted", len(remaining) == 2)


# ============================================================
# Config persistence
# ============================================================

@test("persistence: save then reload round-trips")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    items = metadata_editor.load_collections(
        conf_path(conf_dir, "collections"))
    items.append({"collection_id": "x", "display_name": "X",
                  "default_source_type": None})
    metadata_editor.save_collections(items, conf_path(conf_dir, "collections"))
    reloaded = metadata_editor.load_collections(
        conf_path(conf_dir, "collections"))
    check("two after save", len(reloaded) == 2)
    check("second id", reloaded[1]["collection_id"] == "x")


@test("persistence: atomic write leaves no temp file")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.add_source_type(
        "video", "Video", path=conf_path(conf_dir, "source_types"))
    target = conf_path(conf_dir, "source_types")
    check("no .tmp", not target.with_name(target.name + ".tmp").exists())


@test("persistence: backup created before modification")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    target = conf_path(conf_dir, "source_types")
    original_text = target.read_text(encoding="utf-8")
    metadata_editor.add_source_type(
        "video", "Video", path=target)
    backup = target.with_name(target.name + ".bak")
    check("backup exists", backup.is_file())
    check("backup holds previous version",
          backup.read_text(encoding="utf-8") == original_text)


@test("persistence: preserves the existing top-level format")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.add_collection(
        "nhk_b", "NHK B", path=conf_path(conf_dir, "collections"))
    data = json.loads(conf_path(conf_dir, "collections").read_text(
        encoding="utf-8"))
    check("top-level key preserved", "collections" in data)
    check("entries are dicts", all(isinstance(c, dict)
                                   for c in data["collections"]))


@test("validation: machine id rule")
def _():
    check("valid", metadata_editor.is_valid_machine_id("teppei_beginner"))
    check("valid digits", metadata_editor.is_valid_machine_id("ep2"))
    check("reject space", metadata_editor.is_valid_machine_id("two words") is False)
    check("reject leading digit",
          metadata_editor.is_valid_machine_id("2fast") is False)
    check("reject empty", metadata_editor.is_valid_machine_id("") is False)
    check("reject uppercase", metadata_editor.is_valid_machine_id("NoGood") is False)


@test("preset_references aggregates all three vocabularies")
def _():
    presets = [
        {"slot": 1, "identity_type": "collection",
         "collection_id": "a", "source_type": "subtitle", "origin": "x"},
        {"slot": 2, "source_type": "article", "origin": "y"},
    ]
    refs = metadata_editor.preset_references(presets)
    check("collections", refs["collections"] == {"a"})
    check("source types", refs["source_types"] == {"subtitle", "article"})
    check("origins", refs["origins"] == {"x", "y"})


@test("preset_references handles None")
def _():
    refs = metadata_editor.preset_references(None)
    check("empty collections", refs["collections"] == set())
    check("empty source types", refs["source_types"] == set())
    check("empty origins", refs["origins"] == set())


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
