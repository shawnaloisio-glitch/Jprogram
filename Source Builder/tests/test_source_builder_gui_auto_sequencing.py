#!/usr/bin/env python3
"""
test_source_builder_gui_auto_sequencing.py

GUI-level tests for auto-sequencing of non-episodic collections:

- an "auto" collection hides the Episode field and the collection combo
  stays visible,
- an "episodic" collection (and a collection with no sequencing value)
  keeps the visible Episode field,
- switching the selected collection re-applies field visibility,
- standalone mode hides both the collection combo and the episode field,
- selecting an auto collection silently fills the hidden episode with the
  live next sequence (max+1, gaps never filled),
- saving an auto collection recomputes the sequence fresh so a source
  added since selection is never overwritten.

These tests build the actual Tk window (withdrawn) with a sandboxed Config
and a sandboxed Sources root.

Run:
    python "Source Builder/tests/test_source_builder_gui_auto_sequencing.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SOURCE_BUILDER))

import tkinter as tk

import config_loader
import controller
import gui
import gui_settings
import quick_presets
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
    )
    tmp = pathlib.Path(tempfile.mkdtemp())
    config_dir = tmp / "Config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "collections.json").write_text(json.dumps({
        "collections": [
            {"collection_id": "auto_series", "name": "Auto Series",
             "source_type": "clean_text", "sequencing": "auto"},
            {"collection_id": "episodic_series", "name": "Episodic Series",
             "source_type": "clean_text", "sequencing": "episodic"},
            {"collection_id": "unspecified_series",
             "name": "Unspecified Series",
             "source_type": "clean_text"},
        ]
    }), encoding="utf-8")
    (config_dir / "source_types.json").write_text(json.dumps({
        "source_types": ["clean_text"],
    }), encoding="utf-8")
    (config_dir / "creators.json").write_text(json.dumps({
        "creators": ["con_teppei_podcast"],
    }), encoding="utf-8")
    (config_dir / "styles.json").write_text(json.dumps({"styles": []}),
                                            encoding="utf-8")

    controller.SOURCES_ROOT = tmp / "Sources"
    gui_settings.SETTINGS_PATH = tmp / "gui_settings.json"
    quick_presets.PRESETS_PATH = tmp / "quick_presets.json"
    config_loader.CONFIG_DIR = config_dir
    paths.COLLECTIONS_CONFIG = config_dir / "collections.json"
    paths.CREATORS_CONFIG = config_dir / "creators.json"

    def restore():
        (controller.SOURCES_ROOT, gui_settings.SETTINGS_PATH,
         quick_presets.PRESETS_PATH, config_loader.CONFIG_DIR,
         paths.COLLECTIONS_CONFIG, paths.CREATORS_CONFIG) = saved

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


def is_visible(widget):
    """True when a grid-managed widget is currently shown."""
    return widget.winfo_manager() == "grid"


@test("auto collection hides the Episode field, keeps the collection combo")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("auto_series")
            check("collection combo visible", is_visible(app.collection_combo))
            check("episode label hidden", not is_visible(app.episode_label))
            check("episode entry hidden", not is_visible(app.episode_entry))
        finally:
            root.destroy()
    finally:
        restore()


@test("episodic collection shows the Episode field")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("episodic_series")
            check("episode label visible", is_visible(app.episode_label))
            check("episode entry visible", is_visible(app.episode_entry))
        finally:
            root.destroy()
    finally:
        restore()


@test("collection without a sequencing value behaves episodic")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("unspecified_series")
            check("episode shown by default",
                  is_visible(app.episode_label))
            check("episode entry shown by default",
                  is_visible(app.episode_entry))
        finally:
            root.destroy()
    finally:
        restore()


@test("switching the selected collection re-applies field visibility")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("auto_series")
            check("episode hidden for auto", not is_visible(app.episode_label))
            app.collection_var.set("episodic_series")
            check("episode shown for episodic", is_visible(app.episode_label))
            app.collection_var.set("auto_series")
            check("episode hidden again", not is_visible(app.episode_label))
        finally:
            root.destroy()
    finally:
        restore()


@test("standalone mode hides collection combo and episode field")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("auto_series")
            app.identity_var.set("standalone")
            app._on_identity_change()
            check("collection combo hidden", not is_visible(app.collection_combo))
            check("episode label hidden", not is_visible(app.episode_label))
            check("source name shown", is_visible(app.source_name_entry))
        finally:
            root.destroy()
    finally:
        restore()


@test("auto collection fills the hidden episode on selection")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("auto_series")
            check("empty collection starts at 1", app.episode_var.get() == "1")

            for episode in (1, 2, 3):
                controller.create_collection_source(
                    "auto_series", episode, "clean_text",
                    "con_teppei_podcast", "こんにちは。\n")
            app.collection_var.set("episodic_series")
            app.collection_var.set("auto_series")
            check("max+1 after existing episodes",
                  app.episode_var.get() == "4")
        finally:
            root.destroy()
    finally:
        restore()


@test("saving an auto collection recomputes the sequence fresh")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("auto_series")
            check("starts at 1", app.episode_var.get() == "1")
            app.source_type_var.set("clean_text")
            app.creator_var.set("con_teppei_podcast")
            app.material_level_var.set("1")
            app.text_area.insert("1.0", "こんにちは。\n")
            app._on_text_changed()
            check("ready before external add", app._current_state == "READY")

            # A source (episode 1) lands in the folder after selection.
            controller.create_collection_source(
                "auto_series", 1, "clean_text",
                "con_teppei_podcast", "先に作られた。\n")
            app.on_save()

            check("saved", app._current_state == "SAVED")
            check("saved path set", app._saved_path is not None)
            check("episode advanced past stale value",
                  app.episode_var.get() == "2")
            saved_name = pathlib.Path(app._saved_path).name
            check("saved episode 2", saved_name == "auto_series_ep0002.txt")
            check("episode 1 file preserved",
                  controller.source_path("auto_series", 1).is_file())
        finally:
            root.destroy()
    finally:
        restore()


@test("episodic collection keeps a manual episode through save")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("episodic_series")
            check("episode shown", is_visible(app.episode_label))
            app.episode_var.set("7")
            app.source_type_var.set("clean_text")
            app.creator_var.set("con_teppei_podcast")
            app.material_level_var.set("1")
            app.text_area.insert("1.0", "こんにちは。\n")
            app._on_text_changed()
            app.on_save()
            check("saved", app._current_state == "SAVED")
            saved_name = pathlib.Path(app._saved_path).name
            check("manual episode 7 preserved",
                  saved_name == "episodic_series_ep0007.txt")
        finally:
            root.destroy()
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
