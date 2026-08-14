#!/usr/bin/env python3
"""
test_source_builder_handoff.py

Deterministic tests for the Source Builder handoff:

- valid source package creates registry entry,
- valid source package creates cleaning job,
- registry validates against the existing schema,
- cleaning job validates against the existing schema,
- raw_path points to the canonical Sources file,
- output_path points to Cleaned Archive,
- missing package fields rejected,
- duplicate handoff is safe (idempotent),
- failed handoff does not corrupt existing artifacts.

All handoff writes are redirected to sandboxed Source Registry / Cleaning
Jobs directories; real artifacts are never touched.

Run:
    python "Source Builder/tests/test_source_builder_handoff.py"
"""

import json
import pathlib
import sys
import tempfile
from unittest import mock

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Source Intake"))

import schemas

import controller
import handoff
import paths
import source_package

CLEANED_ARCHIVE_DIR = paths.CLEANED_ARCHIVE


def setup():
    """Patch Sources, Registry, and Cleaning Jobs into temp dirs."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    saved = (
        controller.SOURCES_ROOT,
        handoff.SOURCE_REGISTRY,
        handoff.CLEANING_JOBS,
    )
    controller.SOURCES_ROOT = tmp / "Sources"
    handoff.SOURCE_REGISTRY = tmp / "Source Registry"
    handoff.CLEANING_JOBS = tmp / "Cleaning Jobs"
    return saved


def restore(saved):
    controller.SOURCES_ROOT, handoff.SOURCE_REGISTRY, handoff.CLEANING_JOBS = saved


def make_package(sandbox_saved, source_type="clean_text",
                 collection_id="teppei_beginner", episode=58):
    """Create a real source + package in the sandbox; return (package_path, package)."""
    result = controller.create_collection_source(
        collection_id, episode, source_type, "con_teppei_podcast",
        "こんにちは。\n", material_level=1)
    package_path = source_package.package_path_for(result["path"])
    package = json.loads(package_path.read_text(encoding="utf-8"))
    return package_path, package


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("valid package creates a schema-valid registry entry")
def _():
    saved = setup()
    try:
        package_path, package = make_package(saved)
        result = handoff.handoff_for_package_path(package_path)
        check("no errors", result["errors"] == [])
        check("registry created",
              result["registry"]["action"] == "created")
        registry_path = handoff.registry_path_for(package["source_id"])
        check("registry file exists", registry_path.is_file())
        entry = json.loads(registry_path.read_text(encoding="utf-8"))
        check("registry schema valid", schemas.validate("registry", entry) == [])
    finally:
        restore(saved)


@test("valid package creates a schema-valid cleaning job")
def _():
    saved = setup()
    try:
        package_path, package = make_package(saved)
        result = handoff.handoff_for_package_path(package_path)
        check("no errors", result["errors"] == [])
        check("cleaning job created",
              result["cleaning_job"]["action"] == "created")
        job_path = handoff.cleaning_job_path_for(package["source_id"])
        check("job file exists", job_path.is_file())
        job = json.loads(job_path.read_text(encoding="utf-8"))
        check("cleaning job schema valid",
              schemas.validate("cleaning_job", job) == [])
    finally:
        restore(saved)


@test("raw_path points to the canonical Sources file")
def _():
    saved = setup()
    try:
        package_path, package = make_package(saved)
        handoff.handoff_for_package_path(package_path)
        job_path = handoff.cleaning_job_path_for(package["source_id"])
        job = json.loads(job_path.read_text(encoding="utf-8"))
        check("raw_path == canonical_path",
              job["raw_path"] == package["canonical_path"])
        check("raw_path under Sources",
              "Sources" in job["raw_path"].replace("\\", "/"))
        check("raw_path exists", pathlib.Path(job["raw_path"]).is_file())
    finally:
        restore(saved)


@test("output_path points to Cleaned Archive")
def _():
    saved = setup()
    try:
        package_path, package = make_package(saved)
        handoff.handoff_for_package_path(package_path)
        job_path = handoff.cleaning_job_path_for(package["source_id"])
        job = json.loads(job_path.read_text(encoding="utf-8"))
        expected = CLEANED_ARCHIVE_DIR / f"{package['source_id']}.clean.txt"
        check("output_path correct", job["output_path"] == str(expected))
    finally:
        restore(saved)


@test("registry fields populated from package without user input")
def _():
    saved = setup()
    try:
        package_path, package = make_package(saved)
        handoff.handoff_for_package_path(package_path)
        entry = json.loads(
            handoff.registry_path_for(package["source_id"]).read_text(
                encoding="utf-8"))
        check("source_id", entry["source_id"] == package["source_id"])
        check("original_filename",
              entry["original_filename"] == package["original_filename"])
        check("sha256", entry["sha256"] == package["sha256"])
        check("source_type", entry["source_type"] == package["source_type"])
        check("format", entry["format"] == package["format"])
        check("language", entry["language"] == package["language"])
        check("cleaning_profile",
              entry["cleaning_profile"] == package["cleaning_profile"])
        check("cleaner_version",
              entry["cleaner_version"] == package["cleaner_version"])
    finally:
        restore(saved)


@test("missing package fields rejected")
def _():
    saved = setup()
    try:
        package_path, package = make_package(saved)
        package.pop("sha256", None)
        try:
            handoff.handoff(package)
            check("missing field rejected", False)
        except handoff.HandoffError as exc:
            check("missing message", "sha256" in str(exc))
    finally:
        restore(saved)


@test("missing package file rejected")
def _():
    saved = setup()
    try:
        try:
            handoff.handoff_for_package_path(
                "C:/definitely/not/a_package.source.json")
            check("missing file rejected", False)
        except handoff.HandoffError:
            pass
    finally:
        restore(saved)


@test("duplicate handoff is safe (idempotent)")
def _():
    saved = setup()
    try:
        package_path, package = make_package(saved)
        first = handoff.handoff_for_package_path(package_path)
        second = handoff.handoff_for_package_path(package_path)
        check("first no errors", first["errors"] == [])
        check("first registry created",
              first["registry"]["action"] == "created")
        check("second no errors", second["errors"] == [])
        check("second registry exists",
              second["registry"]["action"] == "exists")
        check("second job exists",
              second["cleaning_job"]["action"] == "exists")
    finally:
        restore(saved)


@test("failed handoff does not corrupt existing artifacts")
def _():
    saved = setup()
    try:
        package_path, package = make_package(saved)
        handoff.handoff_for_package_path(package_path)
        registry_content = handoff.registry_path_for(
            package["source_id"]).read_text(encoding="utf-8")
        job_content = handoff.cleaning_job_path_for(
            package["source_id"]).read_text(encoding="utf-8")

        # A bad package with the same source_id must not touch the artifacts.
        bad = dict(package)
        bad["sha256"] = "0" * 64  # different hash
        try:
            handoff.handoff(bad)
        except handoff.HandoffError:
            pass
        check("registry unchanged",
              handoff.registry_path_for(package["source_id"]).read_text(
                  encoding="utf-8") == registry_content)
        check("job unchanged",
              handoff.cleaning_job_path_for(package["source_id"]).read_text(
                  encoding="utf-8") == job_content)
    finally:
        restore(saved)


@test("standalone package handoff works")
def _():
    saved = setup()
    try:
        result = controller.create_standalone_source(
            "nhk_weather", "clean_text", "nhk_news", "天気です。\n",
            material_level=1)
        package_path = source_package.package_path_for(result["path"])
        h = handoff.handoff_for_package_path(package_path)
        check("no errors", h["errors"] == [])
        check("registry created", h["registry"]["action"] == "created")
        check("job created", h["cleaning_job"]["action"] == "created")
        job = json.loads(
            handoff.cleaning_job_path_for(h["source_id"]).read_text(
                encoding="utf-8"))
        check("job schema valid", schemas.validate("cleaning_job", job) == [])
    finally:
        restore(saved)


@test("source type with no processing profile is rejected cleanly")
def _():
    saved = setup()
    try:
        result = controller.create_standalone_source(
            "nhk_weather", "article", "nhk_news", "天気です。\n",
            material_level=1)
        package_path = source_package.package_path_for(result["path"])
        package = json.loads(package_path.read_text(encoding="utf-8"))
        check("no cleaning profile recorded",
              package.get("cleaning_profile") is None)
        try:
            handoff.handoff(package)
            check("handoff rejected", False)
        except handoff.HandoffError as exc:
            check("rejection message", "cleaning_profile" in str(exc))
    finally:
        restore(saved)


@test("register_standalone_source assigns a global-counter source_id")
def _():
    saved = setup()
    try:
        result = handoff.register_standalone_source(
            "nhk_weather", "clean_text", "nhk_news", "天気です。\n",
            material_level=1)
        check("no errors", result["errors"] == [])
        check("registry created", result["registry"]["action"] == "created")
        check("counter-style id",
              result["source_id"].startswith("ja_"), result["source_id"])
        check("create result attached", result["create"]["success"] is True)
    finally:
        restore(saved)


@test("register_collection_source assigns a global-counter source_id")
def _():
    saved = setup()
    try:
        result = handoff.register_collection_source(
            "teppei_beginner", "clean_text", "con_teppei_podcast",
            "こんにちは。\n", material_level=1)
        check("no errors", result["errors"] == [])
        check("registry created", result["registry"]["action"] == "created")
        check("counter-style id",
              result["source_id"].startswith("ja_"), result["source_id"])
        # Filename still uses the collection/episode convention, unaffected
        # by the counter-based identity.
        check("filename uses collection episode convention",
              "teppei_beginner_ep0001.txt" in result["create"]["filename"])
    finally:
        restore(saved)


@test("register_standalone_source: two calls get two distinct ids")
def _():
    saved = setup()
    try:
        first = handoff.register_standalone_source(
            "source_one", "clean_text", "nhk_news", "一。\n",
            material_level=1)
        second = handoff.register_standalone_source(
            "source_two", "clean_text", "nhk_news", "二。\n",
            material_level=1)
        check("distinct ids", first["source_id"] != second["source_id"])
        check("sequential counters",
              second["source_id"] == "ja_000002",
              f"{first['source_id']} -> {second['source_id']}")
    finally:
        restore(saved)


@test("register_standalone_source: retries past a counter collision")
def _():
    saved = setup()
    try:
        # Simulate another process having already won counter value 1
        # (registered under an unrelated source_name) between our scan and
        # our write -- the exact race next_counter's docstring describes.
        handoff.SOURCE_REGISTRY.mkdir(parents=True, exist_ok=True)
        (handoff.SOURCE_REGISTRY / "ja_000001.json").write_text(
            "{}", encoding="utf-8")

        with mock.patch.object(
                handoff, "_next_candidate_id",
                side_effect=["ja_000001", "ja_000002"]) as spy:
            result = handoff.register_standalone_source(
                "source_three", "clean_text", "nhk_news", "三。\n",
                material_level=1)
        check("retried exactly once", spy.call_count == 2)
        check("won the second candidate", result["source_id"] == "ja_000002")
        check("no errors", result["errors"] == [])
        check("canonical file exists under the winning attempt",
              (controller.SOURCES_ROOT / "source_three.txt").is_file())
        package_path = source_package.package_path_for(
            controller.SOURCES_ROOT / "source_three.txt")
        package = json.loads(package_path.read_text(encoding="utf-8"))
        check("package carries the winning id",
              package["source_id"] == "ja_000002")
        check("no leftover cleaning job for the losing id",
              not handoff.cleaning_job_path_for("ja_000001").is_file())
    finally:
        restore(saved)


@test("register_standalone_source: non-collision create failure is not retried")
def _():
    saved = setup()
    try:
        with mock.patch.object(handoff, "_next_candidate_id",
                               return_value="ja_000001") as spy:
            result = handoff.register_standalone_source(
                "", "clean_text", "nhk_news", "空。\n", material_level=1)
        check("called once, no retry on validation failure",
              spy.call_count == 1)
        check("failure reported", result["success"] is False)
        check("no registry key on a create-level failure",
              "registry" not in result)
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
