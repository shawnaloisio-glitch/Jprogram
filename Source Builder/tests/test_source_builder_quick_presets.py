#!/usr/bin/env python3
"""
test_source_builder_quick_presets.py

Deterministic tests for Source Builder quick presets:

- preset storage loading,
- preset population (one-shot application),
- presets do not modify the form after activation (no live binding),
- manual field changes remain after preset use,
- empty preset slots,
- save validation.

Run:
    python "Source Builder/tests/test_source_builder_quick_presets.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))

import config_loader
import paths
import quick_presets

SAMPLE_CONFIG = {
    "collection_ids": ["teppei_beginner", "other_collection"],
    "source_types": ["podcast_transcript", "subtitle", "article"],
    "origins": ["con_teppei_podcast", "nhk_news"],
}


def temp_path():
    root = pathlib.Path(tempfile.mkdtemp())
    return root / "quick_presets.json"


def sandbox():
    """Redirect Config into a temp dir with a seeded collections.json."""
    saved_config_dir = config_loader.CONFIG_DIR
    saved_collections_config = paths.COLLECTIONS_CONFIG

    tmp = pathlib.Path(tempfile.mkdtemp())
    config_dir = tmp / "Config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "collections.json").write_text(json.dumps({
        "collections": [
            {"collection_id": "teppei_beginner",
             "name": "Con Teppei for Beginner",
             "source_type": "podcast_transcript"},
        ]
    }), encoding="utf-8")

    config_loader.CONFIG_DIR = config_dir
    paths.COLLECTIONS_CONFIG = config_dir / "collections.json"

    def restore():
        config_loader.CONFIG_DIR = saved_config_dir
        paths.COLLECTIONS_CONFIG = saved_collections_config

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


# ============================================================
# Storage loading
# ============================================================

@test("load: missing file yields all-empty slots")
def _():
    presets = quick_presets.load_presets(temp_path())
    check("all empty", presets == quick_presets.empty_slots())
    check("slot 1 empty", presets[1] is None)
    check("slot 6 empty", presets[6] is None)


@test("load: corrupt file yields all-empty slots")
def _():
    path = temp_path()
    path.write_text("{ not json", encoding="utf-8")
    presets = quick_presets.load_presets(path)
    check("all empty", presets == quick_presets.empty_slots())


@test("load: non-dict root yields all-empty slots")
def _():
    path = temp_path()
    path.write_text("[1, 2, 3]", encoding="utf-8")
    presets = quick_presets.load_presets(path)
    check("all empty", presets == quick_presets.empty_slots())


@test("save then load round-trips a preset")
def _():
    path = temp_path()
    quick_presets.save_slot(
        1, "Teppei_Beginner", "collection", collection_id="teppei_beginner",
        source_type="podcast_transcript", origin="con_teppei_podcast",
        path=path)
    presets = quick_presets.load_presets(path)
    preset = presets[1]
    check("slot stored", preset["slot"] == 1)
    check("name", preset["display_name"] == "Teppei_Beginner")
    check("identity", preset["identity_type"] == "collection")
    check("collection", preset["collection_id"] == "teppei_beginner")
    check("source type", preset["source_type"] == "podcast_transcript")
    check("origin", preset["origin"] == "con_teppei_podcast")


@test("legacy language key is dropped on load")
def _():
    path = temp_path()
    path.write_text(json.dumps({
        "presets": [
            {"slot": 1, "display_name": "Old", "identity_type": "collection",
             "collection_id": "teppei_beginner", "source_type": "subtitle",
             "origin": "nhk_news", "language": "ja"}
        ]
    }), encoding="utf-8")
    presets = quick_presets.load_presets(path)
    preset = presets[1]
    check("preset loaded", preset is not None)
    check("no language key", "language" not in preset)
    check("known keys kept", preset["collection_id"] == "teppei_beginner")
    check("no language key", "language" not in preset)
    check("slot 2 untouched", presets[2] is None)


@test("save: atomic write leaves no temp file")
def _():
    path = temp_path()
    quick_presets.save_slot(1, "A", "collection", collection_id="teppei_beginner",
                            path=path)
    check("no .tmp", not path.with_name(path.name + ".tmp").exists())


# ============================================================
# Save validation
# ============================================================

@test("save: rejects invalid slot")
def _():
    path = temp_path()
    try:
        quick_presets.save_slot(0, "A", "collection",
                                collection_id="teppei_beginner", path=path)
        check("slot 0 rejected", False)
    except quick_presets.PresetError:
        pass


@test("save: rejects missing display name")
def _():
    path = temp_path()
    try:
        quick_presets.save_slot(1, "   ", "collection",
                                collection_id="teppei_beginner", path=path)
        check("empty name rejected", False)
    except quick_presets.PresetError:
        pass


@test("save: rejects bad identity type")
def _():
    path = temp_path()
    try:
        quick_presets.save_slot(1, "A", "bogus", collection_id="teppei_beginner",
                                path=path)
        check("bad identity rejected", False)
    except quick_presets.PresetError:
        pass


@test("save: collection preset requires collection_id")
def _():
    path = temp_path()
    try:
        quick_presets.save_slot(1, "A", "collection", path=path)
        check("missing collection rejected", False)
    except quick_presets.PresetError:
        pass


@test("save: standalone preset does not require source_name")
def _():
    path = temp_path()
    quick_presets.save_slot(2, "B", "standalone", path=path)
    presets = quick_presets.load_presets(path)
    preset = presets[2]
    check("saved", preset is not None)
    check("identity standalone", preset["identity_type"] == "standalone")
    check("no source name stored", preset["source_name"] == "")


# ============================================================
# Preset population (one-shot)
# ============================================================

def default_source_type(collection_id):
    if collection_id == "teppei_beginner":
        return "podcast_transcript"
    return None


@test("population: collection preset populates known values")
def _():
    preset = {
        "slot": 1, "display_name": "Teppei_Beginner",
        "identity_type": "collection", "collection_id": "teppei_beginner",
        "source_type": "podcast_transcript", "origin": "con_teppei_podcast",
    }
    updates = quick_presets.preset_population(
        preset, **SAMPLE_CONFIG,
        collection_default_source_type=default_source_type)
    check("identity", updates["identity_type"] == "collection")
    check("collection", updates["collection_id"] == "teppei_beginner")
    check("source type", updates["source_type"] == "podcast_transcript")
    check("origin", updates["origin"] == "con_teppei_podcast")
    check("no language", "language" not in updates)


@test("population: standalone preset never populates source_name")
def _():
    preset = {
        "slot": 2, "display_name": "NHK", "identity_type": "standalone",
        "source_name": "nhk_news_article",
        "source_type": "article", "origin": "nhk_news",
    }
    updates = quick_presets.preset_population(preset, **SAMPLE_CONFIG)
    check("identity", updates["identity_type"] == "standalone")
    check("no source name", "source_name" not in updates)
    check("source type", updates["source_type"] == "article")
    check("origin", updates["origin"] == "nhk_news")


@test("population: unknown config values are dropped")
def _():
    preset = {
        "slot": 1, "display_name": "X", "identity_type": "collection",
        "collection_id": "unknown_collection", "source_type": "not_a_type",
        "origin": "not_an_origin",
    }
    updates = quick_presets.preset_population(
        preset, **SAMPLE_CONFIG,
        collection_default_source_type=default_source_type)
    check("identity still set", updates["identity_type"] == "collection")
    check("unknown collection dropped", "collection_id" not in updates)
    check("unknown source type dropped", "source_type" not in updates)
    check("unknown origin dropped", "origin" not in updates)


@test("population: source_type falls back to collection default")
def _():
    preset = {
        "slot": 1, "display_name": "Teppei", "identity_type": "collection",
        "collection_id": "teppei_beginner",
        "source_type": "", "origin": "con_teppei_podcast",
    }
    updates = quick_presets.preset_population(
        preset, **SAMPLE_CONFIG,
        collection_default_source_type=default_source_type)
    check("fallback applied", updates["source_type"] == "podcast_transcript")


@test("population: None preset yields empty updates")
def _():
    updates = quick_presets.preset_population(None, **SAMPLE_CONFIG)
    check("empty", updates == {})


@test("population: bad identity yields empty updates")
def _():
    preset = {"slot": 1, "display_name": "X", "identity_type": "bogus"}
    updates = quick_presets.preset_population(preset, **SAMPLE_CONFIG)
    check("empty", updates == {})


@test("population is a pure one-shot function (no state retained)")
def _():
    preset = {
        "slot": 1, "display_name": "Teppei_Beginner",
        "identity_type": "collection", "collection_id": "teppei_beginner",
        "source_type": "podcast_transcript", "origin": "con_teppei_podcast",
    }
    first = quick_presets.preset_population(
        preset, **SAMPLE_CONFIG,
        collection_default_source_type=default_source_type)
    second = quick_presets.preset_population(
        preset, **SAMPLE_CONFIG,
        collection_default_source_type=default_source_type)
    check("identical outputs", first == second)
    check("output is a fresh dict", first is not second)
    # Mutating one call must not affect another (no shared state).
    first["source_type"] = "mutated"
    third = quick_presets.preset_population(
        preset, **SAMPLE_CONFIG,
        collection_default_source_type=default_source_type)
    check("no shared state", third["source_type"] == "podcast_transcript")


# ============================================================
# Empty slots
# ============================================================

@test("empty preset slots report None and EMPTY_SLOT_NAME")
def _():
    presets = quick_presets.load_presets(temp_path())
    check("slot 1 None", presets[1] is None)
    check("slot 3 None", presets[3] is None)
    check("slot 6 None", presets[6] is None)
    check("empty slot name",
          quick_presets.EMPTY_SLOT_NAME == "Empty Slot")


@test("empty_slots covers slots 1..6")
def _():
    slots = quick_presets.empty_slots()
    check("six slots", list(slots.keys()) == [1, 2, 3, 4, 5, 6])
    check("all None", all(v is None for v in slots.values()))


# ============================================================
# Resolve through existing Config tables
# ============================================================

@test("default_source_type_for_collection resolves via config")
def _():
    restore = sandbox()
    try:
        st = config_loader.default_source_type_for_collection("teppei_beginner")
        check("resolved", st == "podcast_transcript")
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
