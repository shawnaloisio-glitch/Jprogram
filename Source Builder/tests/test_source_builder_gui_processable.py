#!/usr/bin/env python3
"""
test_source_builder_gui_processable.py

GUI-level tests for processable source-type filtering in the Source Builder:

- the source type is always the single processable type from Config
  (no visible field; source_type_var tracks the raw id),
- unsupported source types are never used,
- an unprocessable source_type cannot save (plain-language message),
- a valid clean_text / user_transcription still creates a package,
- Import Material still works.

These tests build the actual Tk window (withdrawn) with a sandboxed Config
that includes both processable and non-processable values.

Run:
    python "Source Builder/tests/test_source_builder_gui_processable.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Subtitle Importer"))
sys.path.insert(0, str(SOURCE_BUILDER))

import tkinter as tk

import config_loader
import controller
import gui
import gui_settings
import import_material
import quick_presets
import source_package
import paths


def sandbox():
    """Redirect Sources, settings, presets, and Config into temp dirs."""
    saved = (
        controller.SOURCES_ROOT,
        gui_settings.SETTINGS_PATH,
        quick_presets.PRESETS_PATH,
        config_loader.CONFIG_DIR,
        paths.COLLECTIONS_CONFIG,
        paths.CREATORS_CONFIG,
        paths.STYLES_CONFIG,
        paths.TOPICS_CONFIG,
    )
    tmp = pathlib.Path(tempfile.mkdtemp())
    config_dir = tmp / "Config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "collections.json").write_text(json.dumps({
        "collections": [],
    }), encoding="utf-8")
    (config_dir / "source_types.json").write_text(json.dumps({
        "source_types": [
            {"source_type_id": "clean_text",
             "display_name": "clean_text"},
            {"source_type_id": "cij_transcript",
             "display_name": "CIJ Transcripts"},
            {"source_type_id": "article", "display_name": "article"},
        ],
    }), encoding="utf-8")
    (config_dir / "creators.json").write_text(json.dumps({
        "creators": [
            {"creator_id": "user_transcription",
             "display_name": "user_transcription"},
            {"creator_id": "subtitle", "display_name": "subtitle"},
        ],
    }), encoding="utf-8")
    (config_dir / "styles.json").write_text(json.dumps({"styles": []}),
                                            encoding="utf-8")
    (config_dir / "topics.json").write_text(json.dumps({"topics": []}),
                                            encoding="utf-8")

    controller.SOURCES_ROOT = tmp / "Sources"
    gui_settings.SETTINGS_PATH = tmp / "gui_settings.json"
    quick_presets.PRESETS_PATH = tmp / "quick_presets.json"
    config_loader.CONFIG_DIR = config_dir
    paths.COLLECTIONS_CONFIG = config_dir / "collections.json"
    paths.CREATORS_CONFIG = config_dir / "creators.json"
    paths.STYLES_CONFIG = config_dir / "styles.json"
    paths.TOPICS_CONFIG = config_dir / "topics.json"

    def restore():
        (controller.SOURCES_ROOT, gui_settings.SETTINGS_PATH,
         quick_presets.PRESETS_PATH, config_loader.CONFIG_DIR,
         paths.COLLECTIONS_CONFIG, paths.CREATORS_CONFIG,
         paths.STYLES_CONFIG, paths.TOPICS_CONFIG) = saved

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


def make_app(restore):
    root = tk.Tk()
    root.withdraw()
    app = gui.SourceBuilderApp(root)
    return root, app


@test("source type is always the single processable type from Config")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            # The source type has no visible field; source_type_var always
            # holds the one processable type from Config.
            check("source type is clean_text",
                  app.source_type_var.get() == "clean_text")
        finally:
            root.destroy()
    finally:
        restore()


@test("all configured creators are shown, no format-id filtering")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            # creators.json is authoritative curated config. A value that
            # coincidentally matches an import format id ("subtitle") is a
            # legitimate provenance creator and must still be shown.
            values = app.creator_combo.cget("values")
            check("user_transcription shown", "user_transcription" in values)
            check("subtitle shown", "subtitle" in values)
        finally:
            root.destroy()
    finally:
        restore()


@test("unprocessable source type cannot save")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            # Force an unprocessable source type directly on the form.
            app.collection_var.set("my_collection")
            app.episode_var.set("1")
            app.source_type_var.set("cij_transcript")
            app.creator_var.set("user_transcription")
            app.material_level_var.set("1")
            app.text_area.insert("1.0", "これはテストです。\n")
            app._on_text_changed()
            app._refresh_ready_state()
            check("save blocked",
                  str(app.save_button.cget("state")) == "disabled")
            check("plain-language message",
                  "not currently available for processing"
                  in app.status_var.get().lower())
            app.on_save()
            check("not saved", app._current_state != "SAVED")
            check("no canonical file", app._saved_path is None)
        finally:
            root.destroy()
    finally:
        restore()


@test("valid clean_text / user_transcription still saves a package")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("my_collection")
            app.episode_var.set("1")
            app.source_type_var.set("clean_text")
            app.creator_var.set("user_transcription")
            app.material_level_var.set("1")
            app.text_area.insert("1.0", "これはテストです。\n")
            app._on_text_changed()
            app._refresh_ready_state()
            check("ready", app._current_state == "READY")
            app.on_save()
            check("saved", app._current_state == "SAVED")
            check("saved path set", app._saved_path is not None)
            package_path = source_package.package_path_for(app._saved_path)
            check("package exists", package_path.is_file())
            data = json.loads(package_path.read_text(encoding="utf-8"))
            check("package source type",
                  data["source_type"] == "clean_text")
            check("package creator", data["creator"] == "user_transcription")
            check("package has profile", data["cleaning_profile"] is not None)
        finally:
            root.destroy()
    finally:
        restore()


@test("import material still works")
def _():
    restore = sandbox()
    try:
        tmp = pathlib.Path(tempfile.mkdtemp())
        sample = tmp / "sample.txt"
        sample.write_text("こんにちは。\n元気です。\n", encoding="utf-8")
        converted = import_material.convert_file(
            sample, import_material.FORMAT_CLEAN_TEXT)
        check("converted", "こんにちは。" in converted)
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
