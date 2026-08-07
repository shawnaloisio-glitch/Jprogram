#!/usr/bin/env python3
"""
test_source_builder_gui_handoff.py

GUI-level tests for the Sources UI after removal of "Send to Processing":

- Save creates a source package,
- the Sources UI no longer contains a "Send to Processing" button,
- existing Save/Create Next behavior unchanged.

Handoff itself is still driven by the Processing tab (processing_tab.py) and is
tested separately at module level (test_source_builder_handoff.py).

Run:
    python "Source Builder/tests/test_source_builder_gui_handoff.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Source Intake"))

import tkinter as tk

import controller
import gui
import gui_settings
import quick_presets
import source_package


def sandbox():
    """Redirect Sources, settings, and presets into temp dirs."""
    saved = (
        controller.SOURCES_ROOT,
        gui_settings.SETTINGS_PATH,
        quick_presets.PRESETS_PATH,
    )
    tmp = pathlib.Path(tempfile.mkdtemp())
    controller.SOURCES_ROOT = tmp / "Sources"
    gui_settings.SETTINGS_PATH = tmp / "gui_settings.json"
    quick_presets.PRESETS_PATH = tmp / "quick_presets.json"

    def restore():
        (controller.SOURCES_ROOT, gui_settings.SETTINGS_PATH,
         quick_presets.PRESETS_PATH) = saved

    return restore


def make_app(restore):
    root = tk.Tk()
    root.withdraw()
    app = gui.SourceBuilderApp(root)
    return root, app


def fill_and_save(app, collection_id="teppei_beginner", episode="1"):
    app.collection_var.set(collection_id)
    app.episode_var.set(episode)
    app.source_type_var.set("podcast_transcript")
    app.origin_var.set("con_teppei_podcast")
    app.material_level_var.set("1")
    app.text_area.insert("1.0", "こんにちは。\n")
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


@test("save creates a source package beside the canonical file")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            fill_and_save(app)
            check("saved state", app._current_state == "SAVED")
            check("saved path set", app._saved_path is not None)
            package_path = source_package.package_path_for(app._saved_path)
            check("package exists", package_path.is_file())
            data = json.loads(package_path.read_text(encoding="utf-8"))
            check("package type", data["artifact_type"] == "source_package")
            check("package schema valid",
                  source_package.validate_package(data) == [])
        finally:
            root.destroy()
    finally:
        restore()


@test("sources UI no longer contains send-to-processing button")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            texts = [b.cget("text")
                     for b in app.workflow_actions.winfo_children()]
            check("button absent",
                  "Send to Processing" not in texts)
            check("no handoff button attribute",
                  not hasattr(app, "handoff_button"))
        finally:
            root.destroy()
    finally:
        restore()


@test("existing save/create-next behavior unchanged")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            fill_and_save(app)
            check("saved", app._current_state == "SAVED")
            check("save disabled in saved",
                  app.save_button.cget("state") == "disabled")
            check("next enabled in saved",
                  app.next_button.cget("state") == "normal")
            app.on_next_source()
            check("next -> incomplete", app._current_state == "INCOMPLETE")
            check("episode incremented", app.episode_var.get() == "2")
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
