#!/usr/bin/env python3
"""
test_source_builder_gui_processing.py

GUI-level tests for the Processing tab window:

- window opens from the app,
- source list populated with human labels (no source_id),
- action buttons present (Process Selected / Retry Failed /
  Export Diagnostics),
- checkbox toggling selects rows.

Config, Sources, settings, presets, and diagnostics output are redirected to
temp dirs; the Production Manager functions are patched so no pipeline runs.

Run:
    python "Source Builder/tests/test_source_builder_gui_processing.py"
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
sys.path.insert(0, str(PROJECT_ROOT / "Production Manager"))

import tkinter as tk
import tkinter.ttk as ttk

import config_loader
import controller
import diagnostics
import gui
import gui_settings
import processing_tab
import processing_tab_gui
import quick_presets
import paths


def sandbox():
    """Redirect Sources, settings, presets, config, and diagnostics."""
    saved = (
        controller.SOURCES_ROOT,
        gui_settings.SETTINGS_PATH,
        quick_presets.PRESETS_PATH,
        config_loader.CONFIG_DIR,
        diagnostics.DIAGNOSTICS_DIR,
        paths.COLLECTIONS_CONFIG,
    )
    tmp = pathlib.Path(tempfile.mkdtemp())
    config_dir = tmp / "Config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "collections.json").write_text(json.dumps({
        "collections": [
            {"collection_id": "teppei_beginner",
             "name": "Con Teppei for Beginner",
             "source_type": "podcast_transcript"},
        ]
    }), encoding="utf-8")
    (config_dir / "source_types.json").write_text(json.dumps(
        {"source_types": ["podcast_transcript"]}), encoding="utf-8")
    (config_dir / "origins.json").write_text(json.dumps(
        {"origins": ["con_teppei_podcast", "nhk_news"]}), encoding="utf-8")

    controller.SOURCES_ROOT = tmp / "Sources"
    gui_settings.SETTINGS_PATH = tmp / "gui_settings.json"
    quick_presets.PRESETS_PATH = tmp / "quick_presets.json"
    config_loader.CONFIG_DIR = config_dir
    paths.COLLECTIONS_CONFIG = config_dir / "collections.json"
    diagnostics.DIAGNOSTICS_DIR = tmp / "Diagnostics"

    def restore():
        (controller.SOURCES_ROOT, gui_settings.SETTINGS_PATH,
         quick_presets.PRESETS_PATH, config_loader.CONFIG_DIR,
         diagnostics.DIAGNOSTICS_DIR,
         paths.COLLECTIONS_CONFIG) = saved

    return restore


def make_source(package_spec):
    if package_spec[0] == "collection":
        return controller.create_collection_source(
            package_spec[1], package_spec[2], "podcast_transcript",
            "con_teppei_podcast", "こんにちは。\n")
    return controller.create_standalone_source(
        package_spec[1], "podcast_transcript", "nhk_news", "天気です。\n")


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("processing window opens with source list and actions")
def _():
    restore = sandbox()
    try:
        make_source(("collection", "teppei_beginner", 58))
        make_source(("standalone", "nhk_weather", None))
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            window = processing_tab_gui.ProcessingTabWindow(app)
            rows = window.rows
            check("two sources", len(rows) == 2)
            labels = [r["label"] for r in rows]
            check("collection label present",
                  "Episode 58" in " ".join(labels))
            check("standalone label present",
                  "nhk_weather" in " ".join(labels))
            check("no source_id in labels",
                  not any("teppei-beginner_ep058" in l for l in labels))
            buttons = {
                window.process_button.cget("text"),
                window.retry_button.cget("text"),
                window.analysis_button.cget("text"),
                window.dump_button.cget("text"),
            }
            check("has process", "Process Selected" in buttons)
            check("has retry", "Retry Failed" in buttons)
            check("has analysis", "Run Analysis" in buttons)
            check("has dump", "Export Diagnostics" in buttons)
            check("no legacy dump label",
                  "Dump Troubleshooting Data" not in buttons)
            check("no help-file label",
                  "Get Help File" not in buttons)
            window.window.destroy()
        finally:
            root.destroy()
    finally:
        restore()


@test("selecting one row allows action execution")
def _():
    restore = sandbox()
    try:
        make_source(("collection", "teppei_beginner", 58))
        make_source(("standalone", "nhk_weather", None))
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            window = processing_tab_gui.ProcessingTabWindow(app)
            source_id = window.rows[0]["source_id"]
            window.tree.selection_add(source_id)
            window.tree.event_generate("<<TreeviewSelect>>")
            selected = window._selected_rows()
            check("one selected", len(selected) == 1)
            check("correct selected", selected[0]["source_id"] == source_id)
            check("checkbox synced", window.rows[0]["var"].get())
            with mock.patch.object(gui.messagebox, "showinfo") as info, \
                 mock.patch.object(
                     processing_tab, "process_sources",
                     return_value=[{"source_id": source_id,
                                    "state": "cleaned"}]) as ps:
                window._on_process_selected()
            check("no no-selection dialog", not info.called)
            check("process received one", len(ps.call_args.args[0]) == 1)
            window.window.destroy()
        finally:
            root.destroy()
    finally:
        restore()


@test("selecting multiple rows returns all selected sources")
def _():
    restore = sandbox()
    try:
        make_source(("collection", "teppei_beginner", 58))
        make_source(("standalone", "nhk_weather", None))
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            window = processing_tab_gui.ProcessingTabWindow(app)
            ids = [row["source_id"] for row in window.rows]
            window.tree.selection_set(ids)
            window.tree.event_generate("<<TreeviewSelect>>")
            selected = window._selected_rows()
            check("both selected", len(selected) == 2)
            check("all ids", {r["source_id"] for r in selected} == set(ids))
            window.window.destroy()
        finally:
            root.destroy()
    finally:
        restore()


@test("no selection still shows the existing message")
def _():
    restore = sandbox()
    try:
        make_source(("collection", "teppei_beginner", 58))
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            window = processing_tab_gui.ProcessingTabWindow(app)
            infos = []
            with mock.patch.object(
                    gui.messagebox, "showinfo",
                    side_effect=lambda *a, **k: infos.append(a)), \
                 mock.patch.object(processing_tab, "process_sources") as ps:
                window._on_process_selected()
            check("dialog shown", len(infos) == 1)
            check("message", infos[0][1] == "Select one or more sources first.")
            check("no run", not ps.called)
            window.window.destroy()
        finally:
            root.destroy()
    finally:
        restore()


@test("run analysis receives the selected source(s)")
def _():
    restore = sandbox()
    try:
        make_source(("collection", "teppei_beginner", 58))
        make_source(("standalone", "nhk_weather", None))
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            window = processing_tab_gui.ProcessingTabWindow(app)
            ids = [row["source_id"] for row in window.rows]
            window.tree.selection_set(ids)
            window.tree.event_generate("<<TreeviewSelect>>")
            calls = []
            with mock.patch.object(
                    gui.messagebox, "showinfo",
                    side_effect=lambda *a, **k: calls.append(a)), \
                 mock.patch.object(
                     processing_tab, "run_analysis",
                     return_value={"output_path": "/tmp/a.json"}) as ra:
                window._on_run_analysis()
            check("analysis ran per selection",
                  ra.call_count == len(ids))
            window.window.destroy()
        finally:
            root.destroy()
    finally:
        restore()


@test("dump button writes a gzipped bundle")
def _():
    restore = sandbox()
    try:
        make_source(("collection", "teppei_beginner", 58))
        root = tk.Tk()
        root.withdraw()
        app = gui.SourceBuilderApp(root)
        try:
            window = processing_tab_gui.ProcessingTabWindow(app)
            source_id = window.rows[0]["source_id"]
            window.tree.selection_add(source_id)
            infos = []
            with mock.patch.object(gui.messagebox, "showinfo",
                                   side_effect=lambda *a, **k: infos.append(a)), \
                 mock.patch.object(diagnostics.pm, "report",
                                   return_value={"state": "unregistered"}):
                window._on_dump()
            check("info shown", len(infos) == 1)
            dumps = list(diagnostics.DIAGNOSTICS_DIR.glob("*.json.gz"))
            check("dump created", len(dumps) == 1)
            window.window.destroy()
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
