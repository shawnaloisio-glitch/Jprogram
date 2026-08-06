#!/usr/bin/env python3
"""
test_source_builder_gui_analysis.py

GUI-level tests for the Analysis report surface:

- Analysis window opens,
- lists completed corpora with human labels only,
- Run Analysis calls the existing analysis workflow,
- success and failure messages are shown in plain language,
- Open Reports action exists.

Run:
    python "Source Builder/tests/test_source_builder_gui_analysis.py"
"""

import json
import pathlib
import sys
import tempfile
from unittest import mock

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Source Builder"))
sys.path.insert(0, str(PROJECT_ROOT / "Production Manager"))

import tkinter as tk

import config_loader
import controller
import gui
import gui_settings
import processing_tab
import quick_presets
import paths

import analysis_tab_gui


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


def make_completed_source(ep, jsonl_content="こんにちは。\n"):
    """Create a source package and a fake corpus JSONL for it."""
    controller.create_collection_source(
        "teppei_beginner", ep, "clean_text", "con_teppei_podcast",
        "本文。\n")
    source_id = controller.source_id_for(
        "clean_text", collection_id="teppei_beginner", episode=ep)
    jsonl = pathlib.Path(tempfile.mkdtemp()) / f"{source_id}.jsonl"
    jsonl.write_text(jsonl_content, encoding="utf-8")
    return source_id, jsonl


class _JsonlPathContext:
    """Redirect processing_tab.pm.jsonl_path to a source_id->path map."""

    def __init__(self, paths):
        self._paths = dict(paths)

    def __enter__(self):
        self._saved = processing_tab.pm.jsonl_path
        processing_tab.pm.jsonl_path = lambda sid: self._paths.get(
            sid, pathlib.Path(tempfile.mkdtemp()) / f"{sid}.jsonl")
        return self

    def __exit__(self, *exc):
        processing_tab.pm.jsonl_path = self._saved
        return False


def make_app_with_corpora(restore, completed_ids):
    """Build the app with a jsonl_path mock; return (root, app)."""
    root, app = make_app(restore)
    paths = {}
    for source_id in completed_ids:
        paths[source_id] = pathlib.Path(tempfile.mkdtemp()) / f"{source_id}.jsonl"
        paths[source_id].write_text("こんにちは。\n", encoding="utf-8")
    ctx = _JsonlPathContext(paths)
    ctx.__enter__()
    return root, app, ctx


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


@test("analysis window opens and lists completed corpora")
def _():
    restore = sandbox()
    try:
        sid58, _ = make_completed_source(58)
        sid59, _ = make_completed_source(59)
        root, app, ctx = make_app_with_corpora(restore, [sid58, sid59])
        try:
            window = analysis_tab_gui.AnalysisTabWindow(app)
            check("rows listed", len(window.rows) == 2)
            labels = [r["label"] for r in window.rows]
            check("ep58 label", "Episode 58" in " ".join(labels))
            check("ep59 label", "Episode 59" in " ".join(labels))
            window.window.destroy()
        finally:
            ctx.__exit__()
            root.destroy()
    finally:
        restore()


@test("analysis rows use human labels only")
def _():
    restore = sandbox()
    try:
        sid, _ = make_completed_source(58)
        root, app, ctx = make_app_with_corpora(restore, [sid])
        try:
            window = analysis_tab_gui.AnalysisTabWindow(app)
            for row in window.rows:
                check("no source_id in label",
                      "clean_text_teppei-beginner_ep" not in row["label"])
                check("no path", "Sources" not in row["label"]
                      and "\\" not in row["label"])
                check("no json", ".json" not in row["label"])
            window.window.destroy()
        finally:
            ctx.__exit__()
            root.destroy()
    finally:
        restore()


@test("run analysis calls the existing analysis workflow")
def _():
    restore = sandbox()
    try:
        sid, _ = make_completed_source(58)
        root, app, ctx = make_app_with_corpora(restore, [sid])
        try:
            window = analysis_tab_gui.AnalysisTabWindow(app)
            window.tree.selection_set(sid)
            with mock.patch.object(processing_tab, "run_analysis",
                                   return_value={"output_path": "x.json",
                                                 "summary": {}}) as ra, \
                 mock.patch("tkinter.messagebox.showinfo") as info:
                window._on_run()
            check("run_analysis called", ra.called)
            check("status success",
                  window.status_var.get().startswith("Analysis complete"))
            check("info shown", info.called)
            window.window.destroy()
        finally:
            ctx.__exit__()
            root.destroy()
    finally:
        restore()


@test("run analysis shows plain-language failure message")
def _():
    restore = sandbox()
    try:
        sid, _ = make_completed_source(58)
        root, app, ctx = make_app_with_corpora(restore, [sid])
        try:
            window = analysis_tab_gui.AnalysisTabWindow(app)
            window.tree.selection_set(sid)
            with mock.patch.object(processing_tab, "run_analysis",
                                   side_effect=processing_tab.ProcessingTabError(
                                       "no corpus")) as ra, \
                 mock.patch("tkinter.messagebox.showerror") as err:
                window._on_run()
            check("run_analysis called", ra.called)
            check("plain failure status",
                  window.status_var.get() == "Analysis could not be completed")
            check("error shown", err.called)
            message = err.call_args[0][1]
            check("no stack trace", "Traceback" not in message
                  and "no corpus" not in message)
            window.window.destroy()
        finally:
            ctx.__exit__()
            root.destroy()
    finally:
        restore()


@test("open reports action exists and opens the outputs folder")
def _():
    restore = sandbox()
    try:
        sid, _ = make_completed_source(58)
        root, app, ctx = make_app_with_corpora(restore, [sid])
        try:
            window = analysis_tab_gui.AnalysisTabWindow(app)
            check("open button", hasattr(window, "open_button"))
            check("label", window.open_button.cget("text") == "Open Reports")
            with mock.patch("analysis_tab_gui.os.startfile") as startfile:
                window._on_open_reports()
            check("startfile called", startfile.called)
            window.window.destroy()
        finally:
            ctx.__exit__()
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
