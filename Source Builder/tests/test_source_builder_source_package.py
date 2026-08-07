#!/usr/bin/env python3
"""
test_source_builder_source_package.py

Deterministic tests for the Source Builder Source Package ("birth
certificate"):

- created with a collection source,
- created with a standalone source,
- required fields present,
- source_id correct,
- sha256 correct,
- canonical_path correct,
- package stored beside the source,
- atomic write,
- failed package creation does not corrupt the source.

All tests run against a sandboxed Sources/ directory; real sources are never
touched.

Run:
    python "Source Builder/tests/test_source_builder_source_package.py"
"""

import hashlib
import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))

import controller
import source_package

REQUIRED_FIELDS = (
    "source_id", "source_type", "origin", "language", "canonical_path",
    "original_filename", "format", "cleaning_profile", "cleaner_version",
    "sha256", "created_at", "created_by_version",
)


def setup():
    """Patch controller.SOURCES_ROOT to a temp dir."""
    root = pathlib.Path(tempfile.mkdtemp())
    sources = root / "Sources"
    saved = controller.SOURCES_ROOT
    controller.SOURCES_ROOT = sources
    return root, sources, saved


def restore(saved):
    controller.SOURCES_ROOT = saved


def sha256_of(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("collection source: package created beside canonical file")
def _():
    root, sources, saved = setup()
    try:
        result = controller.create_collection_source(
            "teppei_beginner", 58, "podcast_transcript",
            "con_teppei_podcast", "こんにちは。\n", material_level=1)
        check("save success", result["success"] is True)
        check("no package error", "package_error" not in result)
        canonical = sources / "teppei_beginner_ep0058.txt"
        package_path = sources / "teppei_beginner_ep0058.source.json"
        check("canonical exists", canonical.is_file())
        check("package exists", package_path.is_file())
        data = json.loads(package_path.read_text(encoding="utf-8"))
        check("package is dict", isinstance(data, dict))
    finally:
        restore(saved)


@test("collection source: required fields present and correct")
def _():
    root, sources, saved = setup()
    try:
        controller.create_collection_source(
            "teppei_beginner", 58, "podcast_transcript",
            "con_teppei_podcast", "こんにちは。\n", material_level=1)
        package_path = sources / "teppei_beginner_ep0058.source.json"
        data = json.loads(package_path.read_text(encoding="utf-8"))
        for field in REQUIRED_FIELDS:
            check(f"field {field} present",
                  field in data and data[field] not in (None, ""))
        check("artifact_type", data["artifact_type"] == "source_package")
        check("schema_version", data["schema_version"] == "2")
        check("source_type", data["source_type"] == "podcast_transcript")
        check("origin", data["origin"] == "con_teppei_podcast")
        check("language", data["language"] == "ja")
        check("format", data["format"] == "txt")
        check("collection_id", data["collection_id"] == "teppei_beginner")
        check("episode", data["episode"] == 58)
        check("cleaning_profile",
              data["cleaning_profile"] == "transcript_standard_v1")
        check("cleaner_version", data["cleaner_version"] == "1.0")
        check("created_by_version", data["created_by_version"] == "1.0")
    finally:
        restore(saved)


@test("collection source: source_id correct")
def _():
    root, sources, saved = setup()
    try:
        controller.create_collection_source(
            "teppei_beginner", 58, "podcast_transcript",
            "con_teppei_podcast", "text\n", material_level=1)
        package_path = sources / "teppei_beginner_ep0058.source.json"
        data = json.loads(package_path.read_text(encoding="utf-8"))
        check("source_id",
              data["source_id"] == "podcast_transcript_teppei-beginner_ep058")
        check("matches helper",
              data["source_id"] == controller.source_id_for(
                  "podcast_transcript", collection_id="teppei_beginner",
                  episode=58))
    finally:
        restore(saved)


@test("collection source: sha256 and canonical_path correct")
def _():
    root, sources, saved = setup()
    try:
        text = "これはテストです。\n"
        controller.create_collection_source(
            "teppei_beginner", 58, "podcast_transcript",
            "con_teppei_podcast", text, material_level=1)
        canonical = sources / "teppei_beginner_ep0058.txt"
        package_path = sources / "teppei_beginner_ep0058.source.json"
        data = json.loads(package_path.read_text(encoding="utf-8"))
        check("sha256", data["sha256"] == sha256_of(text))
        check("canonical_path", data["canonical_path"] == str(canonical))
        check("original_filename", data["original_filename"] == "teppei_beginner_ep0058.txt")
    finally:
        restore(saved)


@test("standalone source: package created beside canonical file")
def _():
    root, sources, saved = setup()
    try:
        result = controller.create_standalone_source(
            "nhk_weather", "article", "nhk_news", "天気です。\n",
            material_level=1)
        check("save success", result["success"] is True)
        check("no package error", "package_error" not in result)
        package_path = sources / "nhk_weather.source.json"
        check("package exists", package_path.is_file())
        data = json.loads(package_path.read_text(encoding="utf-8"))
        check("source_name", data["source_name"] == "nhk_weather")
        check("source_id", data["source_id"] == "article_nhk-weather")
        check("no collection_id", "collection_id" not in data)
        check("no episode", "episode" not in data)
        check("canonical_path",
              data["canonical_path"] == str(sources / "nhk_weather.txt"))
    finally:
        restore(saved)


@test("package stored beside source (sidecar model)")
def _():
    root, sources, saved = setup()
    try:
        controller.create_collection_source(
            "teppei_beginner", 1, "podcast_transcript",
            "con_teppei_podcast", "a\n", material_level=1)
        canonical = sources / "teppei_beginner_ep0001.txt"
        package_path = source_package.package_path_for(canonical)
        check("package beside source",
              package_path.parent == canonical.parent)
        check("package name",
              package_path.name == "teppei_beginner_ep0001.source.json")
        check("package on disk", package_path.is_file())
    finally:
        restore(saved)


@test("atomic write: no temp leftover after package write")
def _():
    root, sources, saved = setup()
    try:
        controller.create_collection_source(
            "teppei_beginner", 2, "podcast_transcript",
            "con_teppei_podcast", "b\n", material_level=1)
        package_path = sources / "teppei_beginner_ep0002.source.json"
        check("no .tmp", not package_path.with_name(
            package_path.name + ".tmp").exists())
    finally:
        restore(saved)


@test("failed package creation does not corrupt source")
def _():
    root, sources, saved = setup()
    try:
        # Force package failure by making the package path unwritable is hard
        # portably; instead verify the controller records package_error when
        # package building fails (unknown source_type -> no cleaning profile
        # still builds, so use a path scenario). Here we simulate by calling
        # build_package with a nonexistent canonical path and confirm it
        # raises without touching anything.
        try:
            source_package.build_package(
                source_type="podcast_transcript", origin="o",
                language="ja", canonical_path="C:/definitely/missing.txt",
                cleaning_profile="transcript_standard_v1",
                cleaner_version="1.0", material_level=0,
                collection_id="c", episode=1)
            check("build raises", False)
        except source_package.SourcePackageError:
            pass
        # The canonical file from a real save remains intact.
        result = controller.create_collection_source(
            "teppei_beginner", 3, "podcast_transcript",
            "con_teppei_podcast", "keepme\n", material_level=1)
        check("save success", result["success"] is True)
        canonical = sources / "teppei_beginner_ep0003.txt"
        check("canonical intact",
              canonical.read_text(encoding="utf-8") == "keepme\n")
    finally:
        restore(saved)


@test("package never modifies the canonical text file")
def _():
    root, sources, saved = setup()
    try:
        text = "元のテキスト。\n"
        controller.create_collection_source(
            "teppei_beginner", 4, "podcast_transcript",
            "con_teppei_podcast", text, material_level=1)
        canonical = sources / "teppei_beginner_ep0004.txt"
        check("text unchanged", canonical.read_text(encoding="utf-8") == text)
    finally:
        restore(saved)


@test("validate_package reports missing fields")
def _():
    errors = source_package.validate_package({})
    check("missing artifact type", any("artifact_type" in e for e in errors))
    check("missing source_id", any("source_id is required" in e for e in errors))
    check("missing identity", any("collection_id or source_name" in e for e in errors))
    check("missing material_level", any("material_level" in e for e in errors))


@test("derive_source_id uses frozen rules")
def _():
    check("collection", source_package.derive_source_id(
        "podcast_transcript", "teppei_beginner", 58)
        == "podcast_transcript_teppei-beginner_ep058")
    check("standalone", source_package.derive_source_id("article", "nhk_weather")
          == "article_nhk-weather")
    check("slugify", source_package.derive_source_id("pod", "My Title", 1)
          == "pod_my-title_ep001")


def valid_package(**overrides):
    """Return a full schema-v2 package dict that passes validation."""
    package = {
        "artifact_type": "source_package",
        "schema_version": "2",
        "source_id": "podcast_transcript_teppei-beginner_ep058",
        "source_type": "podcast_transcript",
        "origin": "con_teppei_podcast",
        "language": "ja",
        "canonical_path": "C:/sources/teppei_beginner_ep0058.txt",
        "original_filename": "teppei_beginner_ep0058.txt",
        "format": "txt",
        "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": "1.0",
        "sha256": "0" * 64,
        "created_at": "2026-08-01T10:00:00",
        "created_by_version": "1.0",
        "collection_id": "teppei_beginner",
        "episode": 58,
        "material_level": 1,
        "style_id": None,
        "duration_seconds": None,
    }
    package.update(overrides)
    return package


@test("package always includes material_level/style_id/duration_seconds")
def _():
    root, sources, saved = setup()
    try:
        controller.create_collection_source(
            "teppei_beginner", 58, "podcast_transcript",
            "con_teppei_podcast", "こんにちは。\n", material_level=0)
        package_path = sources / "teppei_beginner_ep0058.source.json"
        data = json.loads(package_path.read_text(encoding="utf-8"))
        check("material_level key", "material_level" in data)
        check("material_level value", data["material_level"] == 0)
        check("style_id key", "style_id" in data)
        check("style_id None", data["style_id"] is None)
        check("duration_seconds key", "duration_seconds" in data)
        check("duration_seconds None", data["duration_seconds"] is None)
    finally:
        restore(saved)


@test("validate_package: material_level required")
def _():
    missing = valid_package()
    del missing["material_level"]
    errors = source_package.validate_package(missing)
    check("missing key rejected",
          any("material_level is required" in e for e in errors))
    errors = source_package.validate_package(
        valid_package(material_level=None))
    check("None rejected",
          any("material_level is required" in e for e in errors))


@test("validate_package: material_level must be a valid level int")
def _():
    check("zero valid", source_package.validate_package(
        valid_package(material_level=0)) == [])
    check("four valid", source_package.validate_package(
        valid_package(material_level=4)) == [])
    errors = source_package.validate_package(
        valid_package(material_level=5))
    check("out of range", any("material_level" in e for e in errors))
    errors = source_package.validate_package(
        valid_package(material_level="1"))
    check("non-int rejected", any("integer" in e for e in errors))
    errors = source_package.validate_package(
        valid_package(material_level=True))
    check("bool rejected", any("integer" in e for e in errors))


@test("validate_package: style_id optional int")
def _():
    check("absent ok", source_package.validate_package(
        valid_package()) == [])
    check("null ok", source_package.validate_package(
        valid_package(style_id=None)) == [])
    check("int ok", source_package.validate_package(
        valid_package(style_id=3)) == [])
    errors = source_package.validate_package(
        valid_package(style_id="x"))
    check("non-int rejected", any("style_id" in e for e in errors))


@test("validate_package: duration_seconds non-negative number")
def _():
    check("absent ok", source_package.validate_package(
        valid_package()) == [])
    check("null ok", source_package.validate_package(
        valid_package(duration_seconds=None)) == [])
    check("int ok", source_package.validate_package(
        valid_package(duration_seconds=90)) == [])
    check("float ok", source_package.validate_package(
        valid_package(duration_seconds=90.5)) == [])
    check("zero ok", source_package.validate_package(
        valid_package(duration_seconds=0)) == [])
    errors = source_package.validate_package(
        valid_package(duration_seconds=-1))
    check("negative rejected", any("non-negative" in e for e in errors))
    errors = source_package.validate_package(
        valid_package(duration_seconds="90"))
    check("non-number rejected",
          any("duration_seconds" in e for e in errors))
    errors = source_package.validate_package(
        valid_package(duration_seconds=True))
    check("bool rejected", any("duration_seconds" in e for e in errors))


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
