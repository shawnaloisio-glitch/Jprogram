#!/usr/bin/env python3
"""
test_source_builder_controller.py

Deterministic tests for the Source Builder controller (vertical slice,
collection mode).

Tests run against sandboxed Sources/ directories by patching the module
global. No pipeline code is touched.

Run:
    python "Source Builder/tests/test_source_builder_controller.py"
"""

import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))

import controller


def setup():
    """Patch controller.SOURCES_ROOT to a temp dir."""
    root = pathlib.Path(tempfile.mkdtemp())
    sources = root / "Sources"
    saved = controller.SOURCES_ROOT
    controller.SOURCES_ROOT = sources
    return root, sources, saved


def restore(saved):
    controller.SOURCES_ROOT = saved


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("filename generation: four-digit episode")
def _():
    check("ep0051", controller.generate_filename("teppei_beginner", 51)
          == "teppei_beginner_ep0051.txt")
    check("ep0001", controller.generate_filename("teppei_beginner", 1)
          == "teppei_beginner_ep0001.txt")
    check("ep0015", controller.generate_filename("teppei_beginner", 15)
          == "teppei_beginner_ep0015.txt")
    check("ep0000", controller.generate_filename("x", 0)
          == "x_ep0000.txt")


@test("source path under the flat Sources root")
def _():
    root, sources, saved = setup()
    try:
        path = controller.source_path("teppei_beginner", 51)
        check("path under Sources",
              sources / "teppei_beginner_ep0051.txt" == path)
    finally:
        restore(saved)


@test("validation: missing fields reported")
def _():
    errors = controller.validate_fields("", "", "", "", "text")
    check("missing collection", "collection" in " ".join(errors))
    check("missing source type", any("source type" in e for e in errors))
    check("missing creator", any("creator" in e for e in errors))


@test("validation: empty source text")
def _():
    errors = controller.validate_fields("c", 1, "s", "o", "   ")
    check("empty text error", any("empty" in e for e in errors))


@test("validation: episode is never required or validated")
def _():
    # episode is a hidden auto-incrementing system identifier; any caller
    # value (empty, non-numeric, negative) is accepted and never validated.
    errors = controller.validate_fields("c", "", "s", "o", "text")
    check("empty episode not required", any("episode" in e for e in errors) is False)
    errors = controller.validate_fields("c", "abc", "s", "o", "text")
    check("non-numeric episode not validated", any("episode" in e for e in errors) is False)
    errors = controller.validate_fields("c", -3, "s", "o", "text")
    check("negative episode not validated", any("episode" in e for e in errors) is False)


@test("validation: valid input passes")
def _():
    errors = controller.validate_fields("teppei_beginner", 51, "clean_text",
                                        "con_teppei_podcast", "こんにちは")
    check("no errors", errors == [])


@test("successful source creation writes canonical file (auto episode)")
def _():
    root, sources, saved = setup()
    try:
        # The caller-supplied episode (51) is ignored; the controller always
        # auto-increments, so the first save lands on episode 1.
        result = controller.create_source(
            "teppei_beginner", 51, "clean_text",
            "con_teppei_podcast", "これはテストです。\n")
        check("success true", result["success"] is True)
        check("filename", result["filename"] == "teppei_beginner_ep0001.txt")
        path = sources / "teppei_beginner_ep0001.txt"
        check("file exists", path.is_file())
        check("text preserved",
              path.read_text(encoding="utf-8") == "これはテストです。\n")
        check("path matches", result["path"] == str(path))
    finally:
        restore(saved)


@test("collection source creation always auto-increments the episode")
def _():
    root, sources, saved = setup()
    try:
        result1 = controller.create_source(
            "teppei_beginner", 51, "clean_text",
            "con_teppei_podcast", "first\n")
        check("first success", result1["success"] is True)
        check("first episode 1", result1["filename"] == "teppei_beginner_ep0001.txt")

        result2 = controller.create_source(
            "teppei_beginner", 99, "clean_text",
            "con_teppei_podcast", "second\n")
        check("second success", result2["success"] is True)
        check("second episode 2", result2["filename"] == "teppei_beginner_ep0002.txt")
        check("first file preserved",
              (sources / "teppei_beginner_ep0001.txt").is_file())
        check("caller episode ignored",
              not (sources / "teppei_beginner_ep0099.txt").exists())
    finally:
        restore(saved)


@test("collision_exists detects an existing canonical file")
def _():
    root, sources, saved = setup()
    try:
        sources.mkdir(parents=True, exist_ok=True)
        check("no collision initially",
              controller.collision_exists("teppei_beginner", 51) is False)
        (sources / "teppei_beginner_ep0051.txt").write_text("x\n",
                                                            encoding="utf-8")
        check("collision now", controller.collision_exists("teppei_beginner", 51))
    finally:
        restore(saved)


@test("validation failure produces no file")
def _():
    root, sources, saved = setup()
    try:
        result = controller.create_source("", 51, "", "", "")
        check("success false", result["success"] is False)
        check("errors non-empty", len(result["errors"]) > 0)
        check("no file created", not any(sources.glob("*.txt")))
    finally:
        restore(saved)


@test("atomic write: no temp leftover after save")
def _():
    root, sources, saved = setup()
    try:
        result = controller.create_source(
            "teppei_beginner", 7, "clean_text",
            "con_teppei_podcast", "text\n")
        check("success true", result["success"] is True)
        path = sources / "teppei_beginner_ep0001.txt"
        check("no .tmp", not path.with_name(path.name + ".tmp").exists())
    finally:
        restore(saved)


# ============================================================
# V1.1: standalone mode + Create Next Source
# ============================================================

@test("standalone filename generation")
def _():
    check("simple", controller.generate_standalone_filename("nhk_weather")
          == "nhk_weather.txt")
    check("with spaces", controller.generate_standalone_filename("my source")
          == "my source.txt")


@test("standalone save path under the flat Sources root")
def _():
    root, sources, saved = setup()
    try:
        path = controller.standalone_source_path("nhk_weather")
        check("path", sources / "nhk_weather.txt" == path)
    finally:
        restore(saved)


@test("standalone validation: missing fields")
def _():
    errors = controller.validate_standalone_fields("", "", "", "text")
    check("missing source name", any("source name" in e for e in errors))
    check("missing source type", any("source type" in e for e in errors))
    check("missing creator", any("creator" in e for e in errors))


@test("standalone validation: empty text")
def _():
    errors = controller.validate_standalone_fields("nhk", "article", "nhk_news",
                                                   "   ")
    check("empty text error", any("empty" in e for e in errors))


@test("standalone validation: valid input passes")
def _():
    errors = controller.validate_standalone_fields("nhk", "article", "nhk_news",
                                                   "本文\n")
    check("no errors", errors == [])


@test("standalone collision detection")
def _():
    root, sources, saved = setup()
    try:
        check("no collision initially",
              controller.standalone_collision_exists("nhk") is False)
        result = controller.create_standalone_source(
            "nhk", "article", "nhk_news", "content\n")
        check("created", result["success"] is True)
        check("collision now", controller.standalone_collision_exists("nhk"))
    finally:
        restore(saved)


@test("standalone save writes canonical file")
def _():
    root, sources, saved = setup()
    try:
        result = controller.create_standalone_source(
            "nhk_weather", "article", "nhk_news", "天気です。\n")
        check("success true", result["success"] is True)
        path = sources / "nhk_weather.txt"
        check("file exists", path.is_file())
        check("text preserved", path.read_text(encoding="utf-8") == "天気です。\n")
        check("filename", result["filename"] == "nhk_weather.txt")
        check("path matches", result["path"] == str(path))
    finally:
        restore(saved)


@test("standalone collision rejected without overwrite")
def _():
    root, sources, saved = setup()
    try:
        controller.create_standalone_source("nhk", "article", "nhk_news",
                                            "first\n")
        result = controller.create_standalone_source(
            "nhk", "article", "nhk_news", "second\n")
        check("rejected", result["success"] is False)
        check("exists error", any("already exists" in e for e in result["errors"]))
        path = sources / "nhk.txt"
        check("original preserved", path.read_text(encoding="utf-8") == "first\n")
    finally:
        restore(saved)


@test("standalone overwrite allowed")
def _():
    root, sources, saved = setup()
    try:
        controller.create_standalone_source("nhk", "article", "nhk_news",
                                            "first\n")
        result = controller.create_standalone_source(
            "nhk", "article", "nhk_news", "second\n", overwrite=True)
        check("overwrite succeeds", result["success"] is True)
        path = sources / "nhk.txt"
        check("overwritten", path.read_text(encoding="utf-8") == "second\n")
    finally:
        restore(saved)


@test("next_source_state: collection resets episode to blank")
def _():
    state = controller.next_source_state(
        "collection", "teppei_beginner", 51, "clean_text",
        "con_teppei_podcast")
    check("identity type", state["identity_type"] == "collection")
    check("collection retained", state["collection_id"] == "teppei_beginner")
    check("episode blank", state["episode"] == "")
    check("source type retained", state["source_type"] == "clean_text")
    check("creator retained", state["creator"] == "con_teppei_podcast")
    check("source text reset", state["source_text"] == "")


@test("next_source_state: episode input is never suggested or retained")
def _():
    # Whether the caller passes an int, a string, or junk, the collection
    # output episode is always blank (hidden system identifier).
    for ep in (7, "7", "abc", None):
        state = controller.next_source_state("collection", "c", ep, "s", "o")
        check(f"episode blank for {ep!r}", state["episode"] == "")


@test("next_source_state: standalone blanks source name, retains metadata")
def _():
    state = controller.next_source_state(
        "standalone", "", "", "article", "nhk_news")
    check("identity type", state["identity_type"] == "standalone")
    check("source name blank", state["source_name"] == "")
    check("collection blank", state["collection_id"] == "")
    check("episode blank", state["episode"] == "")
    check("source type retained", state["source_type"] == "article")
    check("creator retained", state["creator"] == "nhk_news")
    check("source text reset", state["source_text"] == "")


@test("next_source_state: standalone ignores collection episode input")
def _():
    state = controller.next_source_state(
        "standalone", "teppei_beginner", 51, "s", "o")
    check("no collection leak", state["collection_id"] == "")
    check("no episode leak", state["episode"] == "")


@test("next_source_state: retains material_level and style_id, resets duration")
def _():
    state = controller.next_source_state(
        "collection", "teppei_beginner", 51, "podcast_transcript",
        "con_teppei_podcast", material_level=2, style_id=3)
    check("material level retained", state["material_level"] == 2)
    check("style id retained", state["style_id"] == 3)
    check("duration always reset", state["duration_seconds"] == "")
    check("source text reset", state["source_text"] == "")


@test("next_source_state: standalone retains material_level and style_id")
def _():
    state = controller.next_source_state(
        "standalone", "", "", "article", "nhk_news",
        material_level=1, style_id=2)
    check("material level retained", state["material_level"] == 1)
    check("style id retained", state["style_id"] == 2)
    check("duration always reset", state["duration_seconds"] == "")
    check("source name blank", state["source_name"] == "")


@test("next_source_state: defaults when material_level/style_id omitted")
def _():
    state = controller.next_source_state("collection", "c", "7", "s", "o")
    check("material level none", state["material_level"] is None)
    check("style id none", state["style_id"] is None)
    check("duration always reset", state["duration_seconds"] == "")


@test("next_source_state: episode_number suggests next, season_number retained")
def _():
    state = controller.next_source_state(
        "collection", "teppei_beginner", "7", "clean_text",
        "con_teppei_podcast", episode_number="5", season_number=2)
    check("episode number suggested", state["episode_number"] == "6")
    check("season number retained", state["season_number"] == 2)
    check("identity episode still blank", state["episode"] == "")


@test("next_source_state: invalid episode_number suggests 1")
def _():
    for value in ("abc", "", "1.5", None):
        state = controller.next_source_state(
            "collection", "c", "7", "s", "o", episode_number=value,
            season_number="2")
        check(f"episode number 1 for {value!r}",
              state["episode_number"] == "1")
        check("season number retained", state["season_number"] == "2")


@test("next_source_state: integer episode_number also suggests next")
def _():
    state = controller.next_source_state(
        "collection", "c", "7", "s", "o", episode_number=3,
        season_number=1)
    check("episode number suggested", state["episode_number"] == "4")
    check("season number retained", state["season_number"] == 1)


@test("next_source_state: standalone also suggests episode_number and retains season")
def _():
    state = controller.next_source_state(
        "standalone", "", "", "article", "nhk_news",
        episode_number=3, season_number=1)
    check("episode number suggested", state["episode_number"] == "4")
    check("season number retained", state["season_number"] == 1)


@test("create_collection_source stores episode_number/season_number in the package")
def _():
    root, sources, saved = setup()
    try:
        result = controller.create_collection_source(
            "teppei_beginner", 51, "clean_text", "con_teppei_podcast",
            "本文。\n", material_level=1, episode_number=5, season_number=2)
        check("success true", result["success"] is True)
        import json
        import source_package
        package = json.loads(source_package.package_path_for(
            result["path"]).read_text(encoding="utf-8"))
        check("episode number stored", package["episode_number"] == 5)
        check("season number stored", package["season_number"] == 2)
    finally:
        restore(saved)


@test("create_standalone_source stores episode_number/season_number in the package")
def _():
    root, sources, saved = setup()
    try:
        result = controller.create_standalone_source(
            "nhk_weather", "clean_text", "nhk_news", "天気です。\n",
            material_level=1, episode_number=8, season_number=3)
        check("success true", result["success"] is True)
        import json
        import source_package
        package = json.loads(source_package.package_path_for(
            result["path"]).read_text(encoding="utf-8"))
        check("episode number stored", package["episode_number"] == 8)
        check("season number stored", package["season_number"] == 3)
    finally:
        restore(saved)


@test("create_collection_source omits episode_number/season_number when not given")
def _():
    root, sources, saved = setup()
    try:
        result = controller.create_collection_source(
            "teppei_beginner", 51, "clean_text", "con_teppei_podcast",
            "本文。\n", material_level=1)
        check("success true", result["success"] is True)
        import json
        import source_package
        package = json.loads(source_package.package_path_for(
            result["path"]).read_text(encoding="utf-8"))
        check("episode number none", package["episode_number"] is None)
        check("season number none", package["season_number"] is None)
    finally:
        restore(saved)


@test("next_auto_sequence: empty collection returns 1")
def _():
    root, sources, saved = setup()
    try:
        check("empty", controller.next_auto_sequence("teppei_beginner") == 1)
    finally:
        restore(saved)


@test("next_auto_sequence: existing episodes 1-3 returns 4")
def _():
    root, sources, saved = setup()
    try:
        for ep in (1, 2, 3):
            controller.create_collection_source(
                "teppei_beginner", ep, "clean_text",
                "con_teppei_podcast", f"text {ep}\n")
        check("max plus one",
              controller.next_auto_sequence("teppei_beginner") == 4)
    finally:
        restore(saved)


@test("next_auto_sequence: gap is never filled (1,2,5 -> 6)")
def _():
    root, sources, saved = setup()
    try:
        sources.mkdir(parents=True, exist_ok=True)
        for ep in (1, 2, 5):
            (sources / controller.generate_filename("teppei_beginner", ep))\
                .write_text("x\n", encoding="utf-8")
        check("max plus one, gap ignored",
              controller.next_auto_sequence("teppei_beginner") == 6)
    finally:
        restore(saved)


@test("next_auto_sequence: ignores non-episode files")
def _():
    root, sources, saved = setup()
    try:
        sources.mkdir(parents=True, exist_ok=True)
        (sources / controller.generate_filename("teppei_beginner", 7))\
            .write_text("x\n", encoding="utf-8")
        (sources / "notes.txt").write_text("not an episode\n",
                                           encoding="utf-8")
        (sources / "other_collection_ep9999.txt").write_text(
            "x\n", encoding="utf-8")
        check("only matching episodes counted",
              controller.next_auto_sequence("teppei_beginner") == 8)
    finally:
        restore(saved)


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
