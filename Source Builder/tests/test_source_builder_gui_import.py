#!/usr/bin/env python3
"""
test_source_builder_gui_import.py

GUI-level tests for the Source Builder Import Material workflow:

- Import Material button exists,
- Import dialog opens,
- multiple files can be imported,
- imported material reaches the source text area,
- saving imported material creates canonical text + source package,
- existing direct Save workflow still works,
- no processing starts automatically.

Run:
    python "Source Builder/tests/test_source_builder_gui_import.py"
"""

import json
import pathlib
import sys
import tempfile
from unittest.mock import patch

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Subtitle Importer"))
sys.path.insert(0, str(SOURCE_BUILDER))

import tkinter as tk
import tkinter.ttk as ttk

import config_loader
import controller
import gui
import gui_settings
import import_material
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
        paths.ORIGINS_CONFIG,
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
    (config_dir / "origins.json").write_text(json.dumps(
        {"origins": ["con_teppei_podcast", "nhk_news"]}), encoding="utf-8")
    (config_dir / "styles.json").write_text(json.dumps({"styles": []}),
                                            encoding="utf-8")

    controller.SOURCES_ROOT = tmp / "Sources"
    gui_settings.SETTINGS_PATH = tmp / "gui_settings.json"
    quick_presets.PRESETS_PATH = tmp / "quick_presets.json"
    config_loader.CONFIG_DIR = config_dir
    paths.COLLECTIONS_CONFIG = config_dir / "collections.json"
    paths.ORIGINS_CONFIG = config_dir / "origins.json"

    def restore():
        (controller.SOURCES_ROOT, gui_settings.SETTINGS_PATH,
         quick_presets.PRESETS_PATH, config_loader.CONFIG_DIR,
         paths.COLLECTIONS_CONFIG, paths.ORIGINS_CONFIG) = saved

    return restore


def tmp_files():
    folder = pathlib.Path(tempfile.mkdtemp())
    a = folder / "a.txt"
    b = folder / "b.txt"
    a.write_text("一つ目の本文。\n", encoding="utf-8")
    b.write_text("二つ目の本文。\n", encoding="utf-8")
    return a, b


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("import material button exists")
def _():
    restore = sandbox()
    try:
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            check("button", hasattr(app, "import_button"))
            check("label",
                  app.import_button.cget("text") == "Import Material")
        finally:
            root.destroy()
    finally:
        restore()


@test("import dialog opens with two formats")
def _():
    restore = sandbox()
    try:
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            result = {}

            def open_dialog():
                app._import_material()
                result["opened"] = True

            def close_dialog():
                for w in root.winfo_children():
                    if isinstance(w, tk.Toplevel) \
                            and w.title() == "Import Material":
                        radios = []

                        def collect(widget):
                            for child in widget.winfo_children():
                                if isinstance(child, ttk.Radiobutton):
                                    radios.append(child)
                                collect(child)

                        collect(w)
                        result["radio_count"] = len(radios)
                        result["radio_texts"] = sorted(
                            r.cget("text") for r in radios)
                        w.destroy()
                result["closed"] = True

            root.after(50, open_dialog)
            root.after(200, close_dialog)
            root.after(600, root.quit)
            root.mainloop()

            check("dialog opened", result.get("opened") is True)
            check("dialog closed", result.get("closed") is True)
            check("exactly two format radios", result.get("radio_count") == 2)
            check("subtitle radio shown",
                  "Subtitle File" in result.get("radio_texts", ()))
            check("clean text radio shown",
                  "Clean Text" in result.get("radio_texts", ()))
        finally:
            root.destroy()
    finally:
        restore()


@test("multiple files can be imported into the text area")
def _():
    restore = sandbox()
    try:
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            a, b = tmp_files()
            app._do_import(None, _var(import_material.FORMAT_CLEAN_TEXT),
                           _var(f"{a}; {b}"), _var())
            content = app.text_area.get("1.0", "end")
            check("file a present", "一つ目の本文。" in content)
            check("file b present", "二つ目の本文。" in content)
            check("no auto save", app._current_state != "SAVED")
        finally:
            root.destroy()
    finally:
        restore()


def _var(value=""):
    return type("V", (), {"get": lambda self: value})()


@test("saving imported material creates canonical text and package")
def _():
    restore = sandbox()
    try:
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            a, _ = tmp_files()
            app._do_import(None, _var(import_material.FORMAT_CLEAN_TEXT),
                           _var(f"{a}"), _var())
            app.collection_var.set("teppei_beginner")
            app.episode_var.set("70")
            app.source_type_var.set("clean_text")
            app.origin_var.set("con_teppei_podcast")
            app.material_level_var.set("1")
            app._on_metadata_changed()
            app.on_save()
            check("saved", app._current_state == "SAVED")
            check("canonical exists", app._saved_path.is_file())
            package_path = source_package.package_path_for(app._saved_path)
            check("package exists", package_path.is_file())
            data = json.loads(package_path.read_text(encoding="utf-8"))
            check("package type", data["artifact_type"] == "source_package")
        finally:
            root.destroy()
    finally:
        restore()


@test("direct save workflow still works")
def _():
    restore = sandbox()
    try:
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            app.collection_var.set("teppei_beginner")
            app.episode_var.set("71")
            app.source_type_var.set("clean_text")
            app.origin_var.set("con_teppei_podcast")
            app.material_level_var.set("1")
            app.text_area.insert("1.0", "直接入力の本文。\n")
            app._on_text_changed()
            app.on_save()
            check("saved", app._current_state == "SAVED")
            check("canonical exists", app._saved_path.is_file())
        finally:
            root.destroy()
    finally:
        restore()


@test("import does not start processing")
def _():
    restore = sandbox()
    try:
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            a, _ = tmp_files()
            with patch.object(import_material, "convert_files",
                              wraps=import_material.convert_files) as conv, \
                 patch.object(controller, "create_collection_source",
                              wraps=controller.create_collection_source) as save:
                app._do_import(None, _var(import_material.FORMAT_CLEAN_TEXT),
                               _var(f"{a}"), _var())
            check("conversion called", conv.called)
            check("no save triggered", not save.called)
        finally:
            root.destroy()
    finally:
        restore()


@test("import browse defaults to RAW_IMPORTS then remembers last folder")
def _():
    restore = sandbox()
    try:
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            a, b = tmp_files()
            picked_folder = pathlib.Path(a).parent
            initialdirs = []
            result = {"round": 0}

            def fake_askopenfilenames(**kwargs):
                initialdirs.append(kwargs.get("initialdir"))
                if len(initialdirs) == 1:
                    return (str(a), str(b))
                return ()

            def find_browse():
                for w in root.winfo_children():
                    if isinstance(w, tk.Toplevel) \
                            and w.title() == "Import Material":
                        button = _find_button(w, "Browse")
                        if button is not None:
                            return button
                return None

            def open_round():
                app._import_material()
                if result["round"] >= 2:
                    root.after(0, root.quit)

            def do_browse_close():
                button = find_browse()
                if button is None:
                    root.after(30, do_browse_close)
                    return
                button.invoke()
                result["round"] += 1
                for w in root.winfo_children():
                    if isinstance(w, tk.Toplevel) \
                            and w.title() == "Import Material":
                        w.destroy()
                if result["round"] < 2:
                    root.after(0, open_round)
                    root.after(50, do_browse_close)

            with patch.object(gui.filedialog, "askopenfilenames",
                              side_effect=fake_askopenfilenames):
                root.after(50, open_round)
                root.after(100, do_browse_close)
                root.after(2000, root.quit)
                root.mainloop()

            expected_default = (paths.RAW_IMPORTS
                                if paths.RAW_IMPORTS.is_dir()
                                else gui.PROJECT_ROOT)
            check("two browse opens", len(initialdirs) == 2)
            check("fresh default is RAW_IMPORTS or project root",
                  initialdirs and pathlib.Path(initialdirs[0])
                  == expected_default,
                  f"got {initialdirs!r}")
            check("reopen uses remembered folder",
                  len(initialdirs) == 2
                  and pathlib.Path(initialdirs[1]) == picked_folder,
                  f"got {initialdirs!r}")
        finally:
            root.destroy()
    finally:
        restore()


def _find_button(widget, text):
    for child in widget.winfo_children():
        if isinstance(child, ttk.Button) and child.cget("text") == text:
            return child
        found = _find_button(child, text)
        if found is not None:
            return found
    return None


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
