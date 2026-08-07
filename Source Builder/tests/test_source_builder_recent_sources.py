#!/usr/bin/env python3
"""
test_source_builder_recent_sources.py

Deterministic tests for the Recent Sources helper:

- derives the most recent source packages from the Source Package sidecars,
- newest first,
- limits to 10 entries,
- returns human labels only (no source_id / paths),
- corrupt packages are skipped,
- standalone and collection sources both appear.

Run:
    python "Source Builder/tests/test_source_builder_recent_sources.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))

import config_loader
import controller
import recent_sources
import paths


def make_collection(ep, text, created_at):
    """Write a collection source package at an explicit episode.

    The controller ignores a caller-supplied episode (it is a hidden
    auto-incrementing system identifier), so the canonical file + package
    are written directly here to pin the episode for the test.
    """
    import source_package
    canonical = controller.SOURCES_ROOT / controller.generate_filename(
        "teppei_beginner", ep)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text(text, encoding="utf-8")
    profile = source_package.cleaning_profile_for("clean_text")
    package = source_package.build_package(
        source_type="clean_text",
        creator="con_teppei_podcast",
        language=controller.PROJECT_LANGUAGE,
        canonical_path=canonical,
        cleaning_profile=profile,
        cleaner_version=source_package.cleaner_version_for(profile),
        material_level=1,
        collection_id="teppei_beginner",
        episode=ep,
    )
    package["created_at"] = created_at
    package_path = source_package.package_path_for(canonical)
    package_path.write_text(json.dumps(package, ensure_ascii=False),
                            encoding="utf-8")
    return package


def source_package_pkg_path(result):
    import source_package
    return source_package.package_path_for(result["path"])


def setup():
    """Redirect Sources and Config to temp dirs; return restore fn."""
    root = pathlib.Path(tempfile.mkdtemp())
    sources_root = root / "Sources"
    config_dir = root / "Config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "collections.json").write_text(json.dumps({
        "collections": [
            {"collection_id": "teppei_beginner",
             "name": "Con Teppei for Beginner",
             "source_type": "clean_text"},
        ]
    }), encoding="utf-8")
    (config_dir / "source_types.json").write_text(json.dumps(
        {"source_types": ["clean_text"]}), encoding="utf-8")
    (config_dir / "creators.json").write_text(json.dumps(
        {"creators": ["con_teppei_podcast", "nhk_news"]}), encoding="utf-8")

    saved = (controller.SOURCES_ROOT, config_loader.CONFIG_DIR,
             paths.COLLECTIONS_CONFIG)
    controller.SOURCES_ROOT = sources_root
    config_loader.CONFIG_DIR = config_dir
    paths.COLLECTIONS_CONFIG = config_dir / "collections.json"

    def restore():
        controller.SOURCES_ROOT, config_loader.CONFIG_DIR, paths.COLLECTIONS_CONFIG = saved

    return sources_root, restore


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("recent_packages orders newest first")
def _():
    sources_root, restore = setup()
    try:
        make_collection(63, "a\n", "2026-08-01T10:00:00")
        make_collection(64, "b\n", "2026-08-01T11:00:00")
        make_collection(65, "c\n", "2026-08-01T12:00:00")
        recent = recent_sources.recent_packages(sources_root)
        episodes = [p["episode"] for p in recent]
        check("newest first", episodes == [65, 64, 63])
    finally:
        restore()


@test("recent_labels returns human labels only")
def _():
    sources_root, restore = setup()
    try:
        make_collection(63, "a\n", "2026-08-01T10:00:00")
        labels = recent_sources.recent_labels(sources_root)
        check("one label", len(labels) == 1)
        check("human label",
              labels[0] == "Con Teppei for Beginner — Episode 63")
        check("no source_id", "clean_text_teppei-beginner_ep063"
              not in labels[0])
        check("no path", "Sources" not in labels[0])
        check("no json", ".json" not in labels[0])
    finally:
        restore()


@test("recent limits to 10 entries")
def _():
    sources_root, restore = setup()
    try:
        for ep in range(1, 15):
            make_collection(ep, "x\n",
                            f"2026-08-01T10:00:{ep:02d}")
        recent = recent_sources.recent_packages(sources_root)
        check("max ten", len(recent) == 10)
        check("newest kept", recent[0]["episode"] == 14)
    finally:
        restore()


@test("corrupt packages are skipped")
def _():
    sources_root, restore = setup()
    try:
        make_collection(63, "a\n", "2026-08-01T10:00:00")
        # Corrupt sidecar in the same flat root.
        (sources_root / "bad.source.json").write_text("{ not json",
                                                      encoding="utf-8")
        recent = recent_sources.recent_packages(sources_root)
        check("corrupt skipped", len(recent) == 1)
    finally:
        restore()


@test("packages without created_at sort after dated ones")
def _():
    sources_root, restore = setup()
    try:
        make_collection(64, "b\n", "2026-08-01T11:00:00")
        result = controller.create_standalone_source(
            "nhk_weather", "clean_text", "nhk_news", "y\n",
            material_level=1)
        # standalone package has a created_at too; strip it to test fallback
        pkg_path = source_package_pkg_path(result)
        package = json.loads(pkg_path.read_text(encoding="utf-8"))
        package.pop("created_at", None)
        pkg_path.write_text(json.dumps(package, ensure_ascii=False),
                            encoding="utf-8")
        recent = recent_sources.recent_packages(sources_root)
        check("dated first", recent[0]["episode"] == 64)
        check("undated present",
              any(p.get("source_name") == "nhk_weather" for p in recent))
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
