#!/usr/bin/env python3
"""
test_source_builder_gui_presets.py

GUI-level tests for Source Builder quick presets (one-shot behaviour):

- applying a preset populates the form once,
- the preset does NOT modify the form after activation,
- manual field changes are never overwritten by the preset afterwards,
- empty preset slots show "Empty Slot" and clicking them reports empty.

These tests build the actual Tk window (withdrawn). They require a display
(Tk 8.6 on this machine). Sources, settings, presets, and Config files are
redirected to a sandboxed temp directory.

Run:
    python "Source Builder/tests/test_source_builder_gui_presets.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))

import tkinter as tk

import config_loader
import controller
import gui
import gui_settings
import paths
import quick_presets


def sandbox():
    """Redirect Sources, settings, presets, and Config into temp dirs."""
    saved_sources = controller.SOURCES_ROOT
    saved_settings = gui_settings.SETTINGS_PATH
    saved_presets = quick_presets.PRESETS_PATH
    saved_config_dir = config_loader.CONFIG_DIR
    saved_collections_config = paths.COLLECTIONS_CONFIG
    saved_origins_config = paths.ORIGINS_CONFIG

    tmp = pathlib.Path(tempfile.mkdtemp())
    config_dir = tmp / "Config"
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
    (config_dir / "origins.json").write_text(json.dumps(
        {"origins": ["con_teppei_podcast", "nhk_news"]}), encoding="utf-8")

    controller.SOURCES_ROOT = tmp / "Sources"
    gui_settings.SETTINGS_PATH = tmp / "gui_settings.json"
    quick_presets.PRESETS_PATH = tmp / "quick_presets.json"
    config_loader.CONFIG_DIR = config_dir
    paths.COLLECTIONS_CONFIG = config_dir / "collections.json"
    paths.ORIGINS_CONFIG = config_dir / "origins.json"

    def restore():
        controller.SOURCES_ROOT = saved_sources
        gui_settings.SETTINGS_PATH = saved_settings
        quick_presets.PRESETS_PATH = saved_presets
        config_loader.CONFIG_DIR = saved_config_dir
        paths.COLLECTIONS_CONFIG = saved_collections_config
        paths.ORIGINS_CONFIG = saved_origins_config

    return restore


def make_app(restore):
    root = tk.Tk()
    root.withdraw()
    app = gui.SourceBuilderApp(root)
    return root, app


def make_visible_app(restore):
    """Build the app with a visible root so child windows can map."""
    root = tk.Tk()
    app = gui.SourceBuilderApp(root)
    return root, app


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("preset click populates fields once")
def _():
    restore = sandbox()
    try:
        quick_presets.save_slot(
            1, "Teppei_Beginner", "collection",
            collection_id="teppei_beginner",
            source_type="clean_text", origin="con_teppei_podcast")
        root, app = make_app(restore)
        try:
            app._on_preset_click(1)
            check("collection", app.collection_var.get() == "teppei_beginner")
            check("source type",
                  app.source_type_var.get() == "clean_text")
            check("origin", app.origin_var.get() == "con_teppei_podcast")
            check("status mentions preset",
                  "Preset loaded: Teppei_Beginner" in app.status_var.get())
        finally:
            root.destroy()
    finally:
        restore()


@test("preset does not modify form after activation")
def _():
    restore = sandbox()
    try:
        quick_presets.save_slot(
            1, "Teppei_Beginner", "collection",
            collection_id="teppei_beginner",
            source_type="clean_text", origin="con_teppei_podcast")
        root, app = make_app(restore)
        try:
            app._on_preset_click(1)
            # Simulate a user edit on the left side.
            app.source_type_var.set("subtitle")
            app.collection_var.set("other_collection")
            app._refresh_ready_state()
            check("manual source type kept",
                  app.source_type_var.get() == "subtitle")
            check("manual collection kept",
                  app.collection_var.get() == "other_collection")
            check("origin untouched by manual edits",
                  app.origin_var.get() == "con_teppei_podcast")
        finally:
            root.destroy()
    finally:
        restore()


@test("manual edits are never overwritten by the preset afterwards")
def _():
    restore = sandbox()
    try:
        quick_presets.save_slot(
            1, "Teppei_Beginner", "collection",
            collection_id="teppei_beginner",
            source_type="clean_text", origin="con_teppei_podcast")
        root, app = make_app(restore)
        try:
            app._on_preset_click(1)
            # An unrelated dropdown change must not revert the preset values.
            app.source_type_var.set("subtitle")
            app._refresh_ready_state()
            check("manual source type stays", app.source_type_var.get() == "subtitle")
            check("collection stays", app.collection_var.get() == "teppei_beginner")
            check("origin stays", app.origin_var.get() == "con_teppei_podcast")
        finally:
            root.destroy()
    finally:
        restore()


@test("empty preset slot shows Empty Slot and click reports empty")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            check("slot 2 label empty",
                  app.preset_buttons[2].cget("text") == "Empty Slot")
            app._on_preset_click(2)
            check("empty reported",
                  "Empty Slot" in app.status_var.get())
        finally:
            root.destroy()
    finally:
        restore()


@test("preset buttons relabel from display names after save")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            quick_presets.save_slot(
                3, "My Preset", "standalone",
                source_type="article", origin="nhk_news")
            app._refresh_presets()
            check("slot 3 relabelled",
                  app.preset_buttons[3].cget("text") == "My Preset")
        finally:
            root.destroy()
    finally:
        restore()


@test("standalone preset populates identity and metadata, never source_name")
def _():
    restore = sandbox()
    try:
        quick_presets.save_slot(
            4, "NHK Article", "standalone",
            source_type="clean_text", origin="nhk_news")
        root, app = make_app(restore)
        try:
            app._on_preset_click(4)
            check("identity standalone",
                  app.identity_var.get() == "standalone")
            check("source name not populated",
                  app.source_name_var.get() == "")
            check("source type",
                  app.source_type_var.get() == "clean_text")
            check("origin", app.origin_var.get() == "nhk_news")
        finally:
            root.destroy()
    finally:
        restore()


@test("preset editor window opens centred over the parent")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            root.geometry("+100+200")
            root.update()
            app._open_preset_editor()
            editors = [w for w in root.winfo_children()
                       if isinstance(w, tk.Toplevel)]
            check("editor created", len(editors) == 1)
            editor = editors[0]
            editor.update_idletasks()

            # Parent geometry (the Source Builder window).
            parent_x = root.winfo_rootx()
            parent_y = root.winfo_rooty()
            parent_w = root.winfo_width()
            parent_h = root.winfo_height()

            # Child requested size.
            child_w = editor.winfo_reqwidth()
            child_h = editor.winfo_reqheight()

            # Expected centred position.
            exp_x, exp_y = gui.centered_position(
                parent_x, parent_y, parent_w, parent_h, child_w, child_h)

            # Actual geometry is "WxH+X+Y".
            geom = editor.geometry()
            parts = geom.split("+")
            actual_x = int(parts[-2])
            actual_y = int(parts[-1])

            check("x centred over parent", actual_x == exp_x)
            check("y centred over parent", actual_y == exp_y)
        finally:
            root.destroy()
    finally:
        restore()


@test("centred position uses the parent's on-screen location")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            root.geometry("+0+0")
            root.update()
            app._open_preset_editor()
            editor = [w for w in root.winfo_children()
                      if isinstance(w, tk.Toplevel)][0]
            editor.update_idletasks()

            parent_x = root.winfo_rootx()
            child_w = editor.winfo_reqwidth()
            # Editor x must be derived from the parent's actual x.
            geom = editor.geometry()
            actual_x = int(geom.split("+")[-2])
            check("editor x derived from parent x",
                  actual_x == parent_x + (root.winfo_width() - child_w) // 2)
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
