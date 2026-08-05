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


@test("source path under collections/<collection_id>")
def _():
    root, sources, saved = setup()
    try:
        path = controller.source_path("teppei_beginner", 51)
        check("path under collections",
              sources / "collections" / "teppei_beginner" / "teppei_beginner_ep0051.txt"
              == path)
    finally:
        restore(saved)


@test("validation: missing fields reported")
def _():
    errors = controller.validate_fields("", "", "", "", "text")
    check("missing collection", "collection" in " ".join(errors))
    check("missing episode", any("episode" in e for e in errors))
    check("missing source type", any("source type" in e for e in errors))
    check("missing origin", any("origin" in e for e in errors))


@test("validation: empty source text")
def _():
    errors = controller.validate_fields("c", 1, "s", "o", "   ")
    check("empty text error", any("empty" in e for e in errors))


@test("validation: invalid episode number")
def _():
    errors = controller.validate_fields("c", "abc", "s", "o", "text")
    check("invalid episode error", any("integer" in e for e in errors))


@test("validation: negative episode number")
def _():
    errors = controller.validate_fields("c", -3, "s", "o", "text")
    check("negative episode error", any("non-negative" in e for e in errors))


@test("validation: valid input passes")
def _():
    errors = controller.validate_fields("teppei_beginner", 51, "podcast_transcript",
                                        "con_teppei_podcast", "こんにちは")
    check("no errors", errors == [])


@test("successful source creation writes canonical file")
def _():
    root, sources, saved = setup()
    try:
        result = controller.create_source(
            "teppei_beginner", 51, "podcast_transcript",
            "con_teppei_podcast", "これはテストです。\n")
        check("success true", result["success"] is True)
        check("filename", result["filename"] == "teppei_beginner_ep0051.txt")
        path = sources / "collections" / "teppei_beginner" / "teppei_beginner_ep0051.txt"
        check("file exists", path.is_file())
        check("text preserved",
              path.read_text(encoding="utf-8") == "これはテストです。\n")
        check("path matches", result["path"] == str(path))
    finally:
        restore(saved)


@test("collision detection: existing file rejected without overwrite")
def _():
    root, sources, saved = setup()
    try:
        result = controller.create_source(
            "teppei_beginner", 51, "podcast_transcript",
            "con_teppei_podcast", "first\n")
        check("first save succeeds", result["success"] is True)

        check("collision detected", controller.collision_exists("teppei_beginner", 51))
        result2 = controller.create_source(
            "teppei_beginner", 51, "podcast_transcript",
            "con_teppei_podcast", "second\n")
        check("second save rejected", result2["success"] is False)
        check("error mentions exists",
              any("already exists" in e for e in result2["errors"]))
        path = sources / "collections" / "teppei_beginner" / "teppei_beginner_ep0051.txt"
        check("original preserved", path.read_text(encoding="utf-8") == "first\n")
    finally:
        restore(saved)


@test("collision detection: overwrite allowed")
def _():
    root, sources, saved = setup()
    try:
        controller.create_source("teppei_beginner", 51, "podcast_transcript",
                                 "con_teppei_podcast", "first\n")
        result = controller.create_source(
            "teppei_beginner", 51, "podcast_transcript",
            "con_teppei_podcast", "second\n", overwrite=True)
        check("overwrite succeeds", result["success"] is True)
        path = sources / "collections" / "teppei_beginner" / "teppei_beginner_ep0051.txt"
        check("overwritten", path.read_text(encoding="utf-8") == "second\n")
    finally:
        restore(saved)


@test("validation failure produces no file")
def _():
    root, sources, saved = setup()
    try:
        result = controller.create_source("", 51, "", "", "")
        check("success false", result["success"] is False)
        check("errors non-empty", len(result["errors"]) > 0)
        check("no file created",
              not (sources / "collections").exists()
              or not any((sources / "collections").rglob("*.txt")))
    finally:
        restore(saved)


@test("atomic write: no temp leftover after save")
def _():
    root, sources, saved = setup()
    try:
        result = controller.create_source(
            "teppei_beginner", 7, "podcast_transcript",
            "con_teppei_podcast", "text\n")
        check("success true", result["success"] is True)
        path = sources / "collections" / "teppei_beginner" / "teppei_beginner_ep0007.txt"
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


@test("standalone save path under Sources/standalone")
def _():
    root, sources, saved = setup()
    try:
        path = controller.standalone_source_path("nhk_weather")
        check("path", sources / "standalone" / "nhk_weather.txt" == path)
    finally:
        restore(saved)


@test("standalone validation: missing fields")
def _():
    errors = controller.validate_standalone_fields("", "", "", "text")
    check("missing source name", any("source name" in e for e in errors))
    check("missing source type", any("source type" in e for e in errors))
    check("missing origin", any("origin" in e for e in errors))


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
        path = sources / "standalone" / "nhk_weather.txt"
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
        path = sources / "standalone" / "nhk.txt"
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
        path = sources / "standalone" / "nhk.txt"
        check("overwritten", path.read_text(encoding="utf-8") == "second\n")
    finally:
        restore(saved)


@test("next_source_state: collection retains and increments episode")
def _():
    state = controller.next_source_state(
        "collection", "teppei_beginner", 51, "podcast_transcript",
        "con_teppei_podcast")
    check("identity type", state["identity_type"] == "collection")
    check("collection retained", state["collection_id"] == "teppei_beginner")
    check("episode incremented", state["episode"] == "52")
    check("source type retained", state["source_type"] == "podcast_transcript")
    check("origin retained", state["origin"] == "con_teppei_podcast")
    check("source text reset", state["source_text"] == "")


@test("next_source_state: episode as string")
def _():
    state = controller.next_source_state("collection", "c", "7", "s", "o")
    check("string episode increments", state["episode"] == "8")


@test("next_source_state: invalid episode yields blank suggestion")
def _():
    state = controller.next_source_state("collection", "c", "abc", "s", "o")
    check("blank episode", state["episode"] == "")


@test("next_source_state: standalone blanks source name, retains metadata")
def _():
    state = controller.next_source_state(
        "standalone", "", "", "article", "nhk_news")
    check("identity type", state["identity_type"] == "standalone")
    check("source name blank", state["source_name"] == "")
    check("collection blank", state["collection_id"] == "")
    check("episode blank", state["episode"] == "")
    check("source type retained", state["source_type"] == "article")
    check("origin retained", state["origin"] == "nhk_news")
    check("source text reset", state["source_text"] == "")


@test("next_source_state: standalone ignores collection episode input")
def _():
    state = controller.next_source_state(
        "standalone", "teppei_beginner", 51, "s", "o")
    check("no collection leak", state["collection_id"] == "")
    check("no episode leak", state["episode"] == "")


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
                "teppei_beginner", ep, "podcast_transcript",
                "con_teppei_podcast", f"text {ep}\n")
        check("max plus one",
              controller.next_auto_sequence("teppei_beginner") == 4)
    finally:
        restore(saved)


@test("next_auto_sequence: gap is never filled (1,2,5 -> 6)")
def _():
    root, sources, saved = setup()
    try:
        for ep in (1, 2, 5):
            controller.create_collection_source(
                "teppei_beginner", ep, "podcast_transcript",
                "con_teppei_podcast", f"text {ep}\n")
        check("max plus one, gap ignored",
              controller.next_auto_sequence("teppei_beginner") == 6)
    finally:
        restore(saved)


@test("next_auto_sequence: ignores non-episode files")
def _():
    root, sources, saved = setup()
    try:
        controller.create_collection_source(
            "teppei_beginner", 7, "podcast_transcript",
            "con_teppei_podcast", "text\n")
        directory = controller.collection_dir("teppei_beginner")
        (directory / "notes.txt").write_text("not an episode\n",
                                             encoding="utf-8")
        (directory / "other_collection_ep9999.txt").write_text(
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
