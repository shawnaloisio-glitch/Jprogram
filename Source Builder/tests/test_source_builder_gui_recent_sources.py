#!/usr/bin/env python3
"""
test_source_builder_gui_recent_sources.py

GUI-level tests for the Recent Sources panel:

- panel appears in the window,
- saved source appears in the list (top),
- human labels displayed (no source_id/paths),
- existing Save behavior unchanged (canonical + package still created),
- max 10 entries enforced by the helper.

Run:
    python "Source Builder/tests/test_source_builder_gui_recent_sources.py"
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
import quick_presets
import source_package
import paths


def sandbox():
    """Redirect Sources, settings, presets, and config into temp dirs."""
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
            {"collection_id": "teppei_beginner",
             "name": "Con Teppei for Beginner",
             "source_type": "clean_text"},
        ]
    }), encoding="utf-8")
    (config_dir / "source_types.json").write_text(json.dumps(
        {"source_types": ["clean_text"]}), encoding="utf-8")
    (config_dir / "creators.json").write_text(json.dumps(
        {"creators": ["con_teppei_podcast", "nhk_news"]}), encoding="utf-8")
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

    def restore():
        (controller.SOURCES_ROOT, gui_settings.SETTINGS_PATH,
         quick_presets.PRESETS_PATH, config_loader.CONFIG_DIR,
         paths.COLLECTIONS_CONFIG, paths.CREATORS_CONFIG) = saved

    return restore


def fill_and_save(app, ep):
    app.collection_var.set("teppei_beginner")
    app.episode_var.set(str(ep))
    app.source_type_var.set("clean_text")
    app.creator_var.set("con_teppei_podcast")
    app.material_level_var.set("1")
    app.text_area.insert("1.0", f"エピソード{ep}の本文。\n")
    app._on_text_changed()
    app.on_save()


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


def list_items(app):
    return [app.recent_list.get(i) for i in range(app.recent_list.size())]


@test("recent sources panel appears")
def _():
    restore = sandbox()
    try:
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            check("panel exists", hasattr(app, "recent_frame"))
            check("listbox exists", hasattr(app, "recent_list"))
        finally:
            root.destroy()
    finally:
        restore()


@test("right panels are in the side container and recent sits below presets")
def _():
    restore = sandbox()
    try:
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            check("presets in side", app.presets_frame.master is app.side)
            check("recent in side", app.recent_frame.master is app.side)
            check("recent packed below presets",
                  app.recent_frame.pack_info()["side"] == "top")
            check("presets packed in side",
                  app.presets_frame.pack_info()["side"] == "top")
        finally:
            root.destroy()
    finally:
        restore()


@test("form metadata rows stay compact (no grid inflation)")
def _():
    restore = sandbox()
    try:
        root = tk.Tk()
        root.geometry("900x800")
        app = gui.SourceBuilderApp(root)
        try:
            root.update_idletasks()
            root.update()
            gap_c_o = (app.creator_label.winfo_y()
                       - app.collection_label.winfo_y())
            check("compact gap collection-creator", gap_c_o < 80)
            gap_o_e = (app.material_level_label.winfo_y()
                       - app.creator_label.winfo_y())
            check("compact gap creator-material-level", gap_o_e < 80)
            check("text area expanded", app.text_area.winfo_height() > 60)
        finally:
            root.destroy()
    finally:
        restore()


@test("workflow panel sits below the action row")
def _():
    restore = sandbox()
    try:
        root = tk.Tk()
        root.geometry("900x800")
        app = gui.SourceBuilderApp(root)
        try:
            root.update_idletasks()
            root.update()
            text_y = app.text_area.winfo_y()
            actions_y = app.actions_frame.winfo_y()
            status_y = app.status_frame.winfo_y()
            check("text above actions", text_y < actions_y)
            check("actions above status", actions_y < status_y)
        finally:
            root.destroy()
    finally:
        restore()


@test("sources tab uses user-facing terminology")
def _():
    restore = sandbox()
    try:
        root = tk.Tk()
        root.geometry("900x800")
        app = gui.SourceBuilderApp(root)
        try:
            root.update_idletasks()
            root.update()
            def widget_texts(widget):
                texts = []
                try:
                    texts.append(widget.cget("text"))
                except tk.TclError:
                    pass
                for child in widget.winfo_children():
                    texts.extend(widget_texts(child))
                return texts

            all_texts = widget_texts(app.root)
            check("add another present", "Add Another" in all_texts)
            check("send-to-processing absent",
                  "Send to Processing" not in all_texts)
            check("templates present",
                  app.presets_frame.cget("text") == "Templates")
            check("status panel title",
                  app.status_frame.cget("text") == "Status")
            check("no identity type label",
                  "Identity Type" not in all_texts)
        finally:
            root.destroy()
    finally:
        restore()


@test("saved source appears at top of recent list")
def _():
    restore = sandbox()
    try:
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            # The hidden identity episode is auto-computed by the controller,
            # so a fresh sandbox save lands on episode 1, then 2.
            fill_and_save(app, 63)
            items = list_items(app)
            check("one recent entry", len(items) == 1)
            check("label at top",
                  items[0] == "Con Teppei for Beginner — ID#1")
            # Save another -> newest first.
            fill_and_save(app, 64)
            items = list_items(app)
            check("newest first",
                  items[0] == "Con Teppei for Beginner — ID#2")
            check("two entries", len(items) == 2)
        finally:
            root.destroy()
    finally:
        restore()


@test("recent list shows human labels only (no ids/paths/json)")
def _():
    restore = sandbox()
    try:
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            fill_and_save(app, 65)
            for item in list_items(app):
                check("no source_id", "clean_text_teppei-beginner_ep065"
                      not in item)
                check("no path", "Sources" not in item and "\\" not in item)
                check("no json", ".json" not in item)
        finally:
            root.destroy()
    finally:
        restore()


@test("save still creates canonical text and package (unchanged)")
def _():
    restore = sandbox()
    try:
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            fill_and_save(app, 66)
            check("saved path", app._saved_path is not None)
            canonical = app._saved_path
            check("canonical exists", canonical.is_file())
            package_path = source_package.package_path_for(canonical)
            check("package exists", package_path.is_file())
            data = json.loads(package_path.read_text(encoding="utf-8"))
            check("package type", data["artifact_type"] == "source_package")
        finally:
            root.destroy()
    finally:
        restore()


@test("recent list enforces max 10 (helper level)")
def _():
    import recent_sources
    restore = sandbox()
    try:
        root = tk.Tk()
        root.withdraw()
        gui.SourceBuilderApp(root)
        try:
            # Create 12 sources via the controller (bypassing GUI) then refresh.
            for ep in range(1, 13):
                controller.create_collection_source(
                    "teppei_beginner", ep, "clean_text",
                    "con_teppei_podcast", f"x{ep}\n", material_level=1)
                pkg_path = source_package.package_path_for(
                    controller.source_path("teppei_beginner", ep))
                package = json.loads(pkg_path.read_text(encoding="utf-8"))
                package["created_at"] = f"2026-08-01T10:00:{ep:02d}"
                pkg_path.write_text(json.dumps(package, ensure_ascii=False),
                                    encoding="utf-8")
            labels = recent_sources.recent_labels(controller.SOURCES_ROOT)
            check("max ten", len(labels) == 10)
            check("newest first", "ID#12" in labels[0])
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
