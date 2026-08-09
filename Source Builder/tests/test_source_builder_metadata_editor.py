#!/usr/bin/env python3
"""
test_source_builder_metadata_editor.py

Deterministic tests for the Source Builder metadata editor data layer:

- Collections: load, add, edit, duplicate rejection, delete validation,
  preset reference protection.
- Source Types: add/edit/delete validation.
- Creators: add/edit/delete validation.
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
import paths


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
    (conf_dir / "creators.json").write_text(json.dumps({
        "creators": ["con_teppei_podcast", "nhk_news"],
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
        "nhk_beginner", "NHK Beginner",
        path=conf_path(conf_dir, "collections"))
    check("two collections", len(items) == 2)
    check("added id", items[1]["collection_id"] == "nhk_beginner")
    # Reload from disk.
    reloaded = metadata_editor.load_collections(
        conf_path(conf_dir, "collections"))
    check("persisted", len(reloaded) == 2)


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


@test("collections: edit display name")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.edit_collection(
        "teppei_beginner", "Renamed",
        path=conf_path(conf_dir, "collections"))
    reloaded = metadata_editor.load_collections(
        conf_path(conf_dir, "collections"))
    check("id unchanged", reloaded[0]["collection_id"] == "teppei_beginner")
    check("display changed", reloaded[0]["display_name"] == "Renamed")


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


@test("collections: legacy sequencing keys are ignored on read")
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
    check("one collection", len(items) == 1)
    check("no sequencing key", "sequencing" not in items[0])
    check("id", items[0]["collection_id"] == "cij_corpus")
    check("display", items[0]["display_name"] == "CIJ Corpus")


@test("collections: saved output omits sequencing entirely")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.add_collection(
        "nhk_beginner", "NHK Beginner",
        path=conf_path(conf_dir, "collections"))
    data = json.loads(conf_path(conf_dir, "collections").read_text(
        encoding="utf-8"))
    check("two entries", len(data["collections"]) == 2)
    check("no sequencing key stored",
          all("sequencing" not in c for c in data["collections"]))


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
    sources_root.mkdir(parents=True, exist_ok=True)
    (sources_root / "teppei_beginner_ep0001.txt").write_text("x\n",
                                                             encoding="utf-8")
    try:
        metadata_editor.delete_collection(
            "teppei_beginner", path=conf_path(conf_dir, "collections"),
            sources_root=sources_root)
        check("source-referenced delete blocked", False)
    except metadata_editor.MetadataError as exc:
        check("source message", "existing source files" in str(exc))


@test("collection_has_sources matches the collection's own filename pattern")
def _():
    sources_root = pathlib.Path(tempfile.mkdtemp()) / "Sources"
    sources_root.mkdir(parents=True, exist_ok=True)
    check("no sources", metadata_editor.collection_has_sources(
        "teppei_beginner", sources_root) is False)
    (sources_root / "nhk_weather.txt").write_text("x\n", encoding="utf-8")
    (sources_root / "other_ep0001.txt").write_text("x\n", encoding="utf-8")
    check("unrelated files ignored", metadata_editor.collection_has_sources(
        "teppei_beginner", sources_root) is False)
    (sources_root / "teppei_beginner_ep0001.txt").write_text("x\n",
                                                             encoding="utf-8")
    check("own file detected", metadata_editor.collection_has_sources(
        "teppei_beginner", sources_root) is True)


@test("collections: delete only blocked by the collection's own files")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.add_collection(
        "other_col", "Other", path=conf_path(conf_dir, "collections"))
    # Unrelated flat-root files must not make this collection look
    # source-backed.
    sources_root = pathlib.Path(tempfile.mkdtemp()) / "Sources"
    sources_root.mkdir(parents=True, exist_ok=True)
    (sources_root / "nhk_weather.txt").write_text("x\n", encoding="utf-8")
    (sources_root / "other_ep0001.txt").write_text("x\n", encoding="utf-8")
    remaining = metadata_editor.delete_collection(
        "other_col", path=conf_path(conf_dir, "collections"),
        sources_root=sources_root)
    check("unrelated files do not block delete", len(remaining) == 1)
    check("right one remains",
          remaining[0]["collection_id"] == "teppei_beginner")


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


@test("source types: delete unused allowed")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.add_source_type(
        "unused_type", "Unused", path=conf_path(conf_dir, "source_types"))
    remaining = metadata_editor.delete_source_type(
        "unused_type", path=conf_path(conf_dir, "source_types"))
    check("unused deleted", len(remaining) == 3)


# ============================================================
# Creators: add / edit / delete validation
# ============================================================

@test("creators: missing workspace file loads empty list")
def _():
    saved = paths.CREATORS_CONFIG
    missing = pathlib.Path(tempfile.mkdtemp()) / "Config" / "creators.json"
    paths.CREATORS_CONFIG = missing
    try:
        check("loads empty", metadata_editor.load_creators() == [])
    finally:
        paths.CREATORS_CONFIG = saved


@test("creators: add creates the file from an empty workspace")
def _():
    saved = paths.CREATORS_CONFIG
    tmp = pathlib.Path(tempfile.mkdtemp())
    creators_file = tmp / "Config" / "creators.json"
    paths.CREATORS_CONFIG = creators_file
    try:
        metadata_editor.add_creator("nhk_radio", "NHK Radio")
        check("file created", creators_file.is_file())
        reloaded = metadata_editor.load_creators()
        check("added", [o["creator_id"] for o in reloaded] == ["nhk_radio"])
    finally:
        paths.CREATORS_CONFIG = saved


@test("styles: missing workspace file loads empty list")
def _():
    saved = paths.STYLES_CONFIG
    missing = pathlib.Path(tempfile.mkdtemp()) / "Config" / "styles.json"
    paths.STYLES_CONFIG = missing
    try:
        check("loads empty", metadata_editor.load_styles() == [])
    finally:
        paths.STYLES_CONFIG = saved


@test("topics: missing workspace file loads empty list")
def _():
    saved = paths.TOPICS_CONFIG
    missing = pathlib.Path(tempfile.mkdtemp()) / "Config" / "topics.json"
    paths.TOPICS_CONFIG = missing
    try:
        check("loads empty", metadata_editor.load_topics() == [])
    finally:
        paths.TOPICS_CONFIG = saved


@test("creators: add")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.add_creator(
        "nhk_radio", "NHK Radio", path=conf_path(conf_dir, "creators"))
    reloaded = metadata_editor.load_creators(
        conf_path(conf_dir, "creators"))
    check("added", len(reloaded) == 3)
    check("added id", reloaded[2]["creator_id"] == "nhk_radio")
    check("added display", reloaded[2]["display_name"] == "NHK Radio")


@test("creators: edit display name only")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.edit_creator(
        "nhk_news", "NHK News JP", path=conf_path(conf_dir, "creators"))
    reloaded = metadata_editor.load_creators(conf_path(conf_dir, "creators"))
    check("id unchanged", reloaded[1]["creator_id"] == "nhk_news")
    check("display changed", reloaded[1]["display_name"] == "NHK News JP")


@test("creators: id is immutable after creation")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.edit_creator(
        "nhk_news", "Renamed", path=conf_path(conf_dir, "creators"))
    reloaded = metadata_editor.load_creators(conf_path(conf_dir, "creators"))
    check("id unchanged", reloaded[1]["creator_id"] == "nhk_news")


@test("creators: duplicate rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.add_creator(
            "nhk_news", "NHK News", path=conf_path(conf_dir, "creators"))
        check("duplicate rejected", False)
    except metadata_editor.MetadataError as exc:
        check("duplicate message", "already exists" in str(exc))


@test("creators: bad id rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.add_creator(
            "1bad", "Bad", path=conf_path(conf_dir, "creators"))
        check("bad id rejected", False)
    except metadata_editor.MetadataError as exc:
        check("machine-friendly message", "machine-friendly" in str(exc))


@test("creators: delete referenced by preset blocked")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    presets = [{"slot": 1, "creator": "nhk_news"}]
    try:
        metadata_editor.delete_creator(
            "nhk_news", path=conf_path(conf_dir, "creators"), presets=presets)
        check("referenced delete blocked", False)
    except metadata_editor.MetadataError as exc:
        check("reference message", "referenced by a preset" in str(exc))


@test("creators: delete unused allowed")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.add_creator(
        "extra_creator", "Extra", path=conf_path(conf_dir, "creators"))
    remaining = metadata_editor.delete_creator(
        "extra_creator", path=conf_path(conf_dir, "creators"))
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
    items.append({"collection_id": "x", "display_name": "X"})
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
         "collection_id": "a", "source_type": "subtitle", "creator": "x"},
        {"slot": 2, "source_type": "article", "creator": "y"},
    ]
    refs = metadata_editor.preset_references(presets)
    check("collections", refs["collections"] == {"a"})
    check("source types", refs["source_types"] == {"subtitle", "article"})
    check("creators", refs["creators"] == {"x", "y"})


@test("preset_references handles None")
def _():
    refs = metadata_editor.preset_references(None)
    check("empty collections", refs["collections"] == set())
    check("empty source types", refs["source_types"] == set())
    check("empty creators", refs["creators"] == set())


# ============================================================
# Styles: load / add / edit / uniqueness
# ============================================================

@test("styles: missing file loads empty")
def _():
    conf_dir = temp_config_dir()
    items = metadata_editor.load_styles(conf_path(conf_dir, "styles"))
    check("empty", items == [])


@test("styles: add assigns autoincrement ids from max+1")
def _():
    conf_dir = temp_config_dir()
    items = metadata_editor.add_style(
        "Documentary", path=conf_path(conf_dir, "styles"))
    check("first id", items[0]["style_id"] == 1)
    items = metadata_editor.add_style(
        "Podcast", path=conf_path(conf_dir, "styles"))
    check("second id", items[1]["style_id"] == 2)
    reloaded = metadata_editor.load_styles(conf_path(conf_dir, "styles"))
    check("persisted two", len(reloaded) == 2)
    check("persisted ids", [s["style_id"] for s in reloaded] == [1, 2])
    check("persisted names", [s["display_name"] for s in reloaded]
          == ["Documentary", "Podcast"])


@test("styles: add skips gaps (max+1, no persisted counter)")
def _():
    conf_dir = temp_config_dir()
    conf_dir.mkdir(parents=True, exist_ok=True)
    (conf_dir / "styles.json").write_text(json.dumps({
        "styles": [
            {"style_id": 5, "display_name": "A"},
            {"style_id": 2, "display_name": "B"},
        ]
    }), encoding="utf-8")
    items = metadata_editor.add_style(
        "C", path=conf_path(conf_dir, "styles"))
    check("max plus one", items[-1]["style_id"] == 6)


@test("styles: add duplicate display name rejected")
def _():
    conf_dir = temp_config_dir()
    metadata_editor.add_style("Documentary", path=conf_path(conf_dir, "styles"))
    try:
        metadata_editor.add_style(
            "Documentary", path=conf_path(conf_dir, "styles"))
        check("duplicate rejected", False)
    except metadata_editor.MetadataError as exc:
        check("duplicate message", "already exists" in str(exc))


@test("styles: add missing display name rejected")
def _():
    conf_dir = temp_config_dir()
    try:
        metadata_editor.add_style("   ", path=conf_path(conf_dir, "styles"))
        check("empty display rejected", False)
    except metadata_editor.MetadataError as exc:
        check("display message", "display_name is required" in str(exc))


@test("styles: edit display name keeps id")
def _():
    conf_dir = temp_config_dir()
    metadata_editor.add_style("Documentary", path=conf_path(conf_dir, "styles"))
    items = metadata_editor.edit_style(
        1, "Documentary Series", path=conf_path(conf_dir, "styles"))
    check("id unchanged", items[0]["style_id"] == 1)
    check("display changed", items[0]["display_name"] == "Documentary Series")
    reloaded = metadata_editor.load_styles(conf_path(conf_dir, "styles"))
    check("persisted", reloaded[0]["display_name"] == "Documentary Series")


@test("styles: edit to another style's display name rejected")
def _():
    conf_dir = temp_config_dir()
    metadata_editor.add_style("Documentary", path=conf_path(conf_dir, "styles"))
    metadata_editor.add_style("Podcast", path=conf_path(conf_dir, "styles"))
    try:
        metadata_editor.edit_style(
            1, "Podcast", path=conf_path(conf_dir, "styles"))
        check("edit duplicate rejected", False)
    except metadata_editor.MetadataError as exc:
        check("duplicate message", "already exists" in str(exc))


@test("styles: edit keeping own display name allowed")
def _():
    conf_dir = temp_config_dir()
    metadata_editor.add_style("Documentary", path=conf_path(conf_dir, "styles"))
    items = metadata_editor.edit_style(
        1, "Documentary", path=conf_path(conf_dir, "styles"))
    check("allowed", items[0]["display_name"] == "Documentary")


@test("styles: edit missing style rejected")
def _():
    conf_dir = temp_config_dir()
    try:
        metadata_editor.edit_style(
            99, "X", path=conf_path(conf_dir, "styles"))
        check("missing original rejected", False)
    except metadata_editor.MetadataError as exc:
        check("not found message", "not found" in str(exc))


@test("styles: no delete_style function (dead-code avoidance)")
def _():
    check("no delete_style", not hasattr(metadata_editor, "delete_style"))


# ============================================================
# Topics: load / add / edit / uniqueness (mirrors Styles)
# ============================================================

@test("topics: config file entry present in FILES")
def _():
    check("topics file name", metadata_editor.FILES["topics"] == "topics.json")


@test("topics: missing file loads empty")
def _():
    conf_dir = temp_config_dir()
    items = metadata_editor.load_topics(conf_path(conf_dir, "topics"))
    check("empty", items == [])


@test("topics: load returns ordered integer topic ids")
def _():
    conf_dir = temp_config_dir()
    conf_dir.mkdir(parents=True, exist_ok=True)
    (conf_dir / "topics.json").write_text(json.dumps({
        "topics": [
            {"topic_id": 3, "display_name": "A"},
            {"topic_id": 1, "display_name": "B"},
            {"topic_id": 2, "display_name": "C"},
        ]
    }), encoding="utf-8")
    items = metadata_editor.load_topics(conf_path(conf_dir, "topics"))
    check("order", [t["topic_id"] for t in items] == [3, 1, 2])
    check("int ids", all(isinstance(t["topic_id"], int) for t in items))
    check("display names",
          [t["display_name"] for t in items] == ["A", "B", "C"])


@test("topics: load skips non-integer and non-dict entries")
def _():
    conf_dir = temp_config_dir()
    conf_dir.mkdir(parents=True, exist_ok=True)
    (conf_dir / "topics.json").write_text(json.dumps({
        "topics": [
            {"topic_id": 1, "display_name": "A"},
            {"topic_id": "x", "display_name": "Bad"},
            {"topic_id": True, "display_name": "Bool"},
            "plain",
            {"display_name": "No id"},
        ]
    }), encoding="utf-8")
    items = metadata_editor.load_topics(conf_path(conf_dir, "topics"))
    check("only valid int ids", [t["topic_id"] for t in items] == [1])


@test("topics: add assigns autoincrement ids from max+1")
def _():
    conf_dir = temp_config_dir()
    items = metadata_editor.add_topic(
        "Grammar", path=conf_path(conf_dir, "topics"))
    check("first id", items[0]["topic_id"] == 1)
    items = metadata_editor.add_topic(
        "Vocabulary", path=conf_path(conf_dir, "topics"))
    check("second id", items[1]["topic_id"] == 2)
    reloaded = metadata_editor.load_topics(conf_path(conf_dir, "topics"))
    check("persisted two", len(reloaded) == 2)
    check("persisted ids", [t["topic_id"] for t in reloaded] == [1, 2])
    check("persisted names", [t["display_name"] for t in reloaded]
          == ["Grammar", "Vocabulary"])


@test("topics: add skips gaps (max+1, no persisted counter)")
def _():
    conf_dir = temp_config_dir()
    conf_dir.mkdir(parents=True, exist_ok=True)
    (conf_dir / "topics.json").write_text(json.dumps({
        "topics": [
            {"topic_id": 5, "display_name": "A"},
            {"topic_id": 2, "display_name": "B"},
        ]
    }), encoding="utf-8")
    items = metadata_editor.add_topic(
        "C", path=conf_path(conf_dir, "topics"))
    check("max plus one", items[-1]["topic_id"] == 6)


@test("topics: add duplicate display name rejected")
def _():
    conf_dir = temp_config_dir()
    metadata_editor.add_topic("Grammar", path=conf_path(conf_dir, "topics"))
    try:
        metadata_editor.add_topic(
            "Grammar", path=conf_path(conf_dir, "topics"))
        check("duplicate rejected", False)
    except metadata_editor.MetadataError as exc:
        check("duplicate message", "already exists" in str(exc))


@test("topics: add missing display name rejected")
def _():
    conf_dir = temp_config_dir()
    try:
        metadata_editor.add_topic("   ", path=conf_path(conf_dir, "topics"))
        check("empty display rejected", False)
    except metadata_editor.MetadataError as exc:
        check("display message", "display_name is required" in str(exc))


@test("topics: edit display name keeps id")
def _():
    conf_dir = temp_config_dir()
    metadata_editor.add_topic("Grammar", path=conf_path(conf_dir, "topics"))
    items = metadata_editor.edit_topic(
        1, "Grammar & Style", path=conf_path(conf_dir, "topics"))
    check("id unchanged", items[0]["topic_id"] == 1)
    check("display changed", items[0]["display_name"] == "Grammar & Style")
    reloaded = metadata_editor.load_topics(conf_path(conf_dir, "topics"))
    check("persisted", reloaded[0]["display_name"] == "Grammar & Style")


@test("topics: edit to another topic's display name rejected")
def _():
    conf_dir = temp_config_dir()
    metadata_editor.add_topic("Grammar", path=conf_path(conf_dir, "topics"))
    metadata_editor.add_topic("Vocabulary", path=conf_path(conf_dir, "topics"))
    try:
        metadata_editor.edit_topic(
            1, "Vocabulary", path=conf_path(conf_dir, "topics"))
        check("edit duplicate rejected", False)
    except metadata_editor.MetadataError as exc:
        check("duplicate message", "already exists" in str(exc))


@test("topics: edit keeping own display name allowed")
def _():
    conf_dir = temp_config_dir()
    metadata_editor.add_topic("Grammar", path=conf_path(conf_dir, "topics"))
    items = metadata_editor.edit_topic(
        1, "Grammar", path=conf_path(conf_dir, "topics"))
    check("allowed", items[0]["display_name"] == "Grammar")


@test("topics: edit missing topic rejected")
def _():
    conf_dir = temp_config_dir()
    try:
        metadata_editor.edit_topic(
            99, "X", path=conf_path(conf_dir, "topics"))
        check("missing original rejected", False)
    except metadata_editor.MetadataError as exc:
        check("not found message", "not found" in str(exc))


@test("topics: no delete_topic function (dead-code avoidance)")
def _():
    check("no delete_topic", not hasattr(metadata_editor, "delete_topic"))


# ============================================================
# Display-name uniqueness (Part 6 fix, all four vocabularies)
# ============================================================

@test("collections: add duplicate display name rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.add_collection(
            "new_col", "Con Teppei for Beginner",
            path=conf_path(conf_dir, "collections"))
        check("duplicate display rejected", False)
    except metadata_editor.MetadataError as exc:
        check("message", "already exists" in str(exc))


@test("collections: edit to another collection's display name rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    metadata_editor.add_collection(
        "nhk_beginner", "NHK Beginner", path=conf_path(conf_dir, "collections"))
    try:
        metadata_editor.edit_collection(
            "nhk_beginner", "Con Teppei for Beginner",
            path=conf_path(conf_dir, "collections"))
        check("edit duplicate display rejected", False)
    except metadata_editor.MetadataError as exc:
        check("message", "already exists" in str(exc))


@test("collections: edit keeping own display name allowed")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    items = metadata_editor.edit_collection(
        "teppei_beginner", "Con Teppei for Beginner",
        path=conf_path(conf_dir, "collections"))
    check("allowed", items[0]["display_name"] == "Con Teppei for Beginner")


@test("source types: add duplicate display name rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.add_source_type(
            "new_type", "subtitle",
            path=conf_path(conf_dir, "source_types"))
        check("duplicate display rejected", False)
    except metadata_editor.MetadataError as exc:
        check("message", "already exists" in str(exc))


@test("source types: edit to another source type's display name rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.edit_source_type(
            "article", "subtitle",
            path=conf_path(conf_dir, "source_types"))
        check("edit duplicate display rejected", False)
    except metadata_editor.MetadataError as exc:
        check("message", "already exists" in str(exc))


@test("creators: add duplicate display name rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.add_creator(
            "new_creator", "nhk_news", path=conf_path(conf_dir, "creators"))
        check("duplicate display rejected", False)
    except metadata_editor.MetadataError as exc:
        check("message", "already exists" in str(exc))


@test("creators: edit to another creator's display name rejected")
def _():
    conf_dir = temp_config_dir()
    write_initial(conf_dir)
    try:
        metadata_editor.edit_creator(
            "nhk_news", "con_teppei_podcast",
            path=conf_path(conf_dir, "creators"))
        check("edit duplicate display rejected", False)
    except metadata_editor.MetadataError as exc:
        check("message", "already exists" in str(exc))


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
