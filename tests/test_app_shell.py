#!/usr/bin/env python3
"""
test_app_shell.py

Tests for the application shell (single user entry point):

- the shell window launches,
- the three tabs exist (Sources / Processing / Analysis),
- the Sources tab embeds the existing Source Builder interface,
- the embedded save flow creates canonical text + source package,
- tab actions are wired (Processing open, Analysis placeholder),
- existing modules import correctly,
- the shell preserves existing launch paths (no files moved/deleted).

Run:
    python tests/test_app_shell.py
"""

import importlib
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import tkinter as tk
import tkinter.ttk as ttk
from unittest import mock

import app


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


def make_shell():
    root = tk.Tk()
    root.withdraw()
    shell = app.ApplicationShell(root)
    return root, shell


@test("shell window launches and builds")
def _():
    root, shell = make_shell()
    try:
        check("root title", "Japanese Corpus Pipeline" in root.title())
        check("notebook present", isinstance(shell.notebook, ttk.Notebook))
    finally:
        root.destroy()


@test("three tabs exist in order")
def _():
    root, shell = make_shell()
    try:
        tabs = [shell.notebook.tab(tab_id, "text")
                for tab_id in shell.notebook.tabs()]
        check("tab order", tabs == ["Sources", "Processing", "Analysis"])
        check("sources tab", "Sources" in tabs)
        check("processing tab", "Processing" in tabs)
        check("analysis tab", "Analysis" in tabs)
    finally:
        root.destroy()


@test("sources tab embeds the Source Builder interface")
def _():
    root, shell = make_shell()
    try:
        check("embedded source builder",
              hasattr(shell, "source_builder"))
        check("instance type",
              isinstance(shell.source_builder, app.source_builder_gui.SourceBuilderApp))
        check("notebook exists", hasattr(shell.source_builder, "notebook")
              or hasattr(shell.source_builder, "save_button"))
    finally:
        root.destroy()


@test("embedded sources interface retains core controls")
def _():
    root, shell = make_shell()
    try:
        sb = shell.source_builder
        check("save button", hasattr(sb, "save_button"))
        check("load file button", hasattr(sb, "load_button"))
        check("collection combo", hasattr(sb, "collection_combo"))
        check("episode entry", hasattr(sb, "episode_entry"))
        check("source type combo", hasattr(sb, "source_type_combo"))
        check("origin combo", hasattr(sb, "origin_combo"))
    finally:
        root.destroy()


@test("embedded save flow creates canonical text and source package")
def _():
    import json
    import controller
    import source_package
    root, shell = make_shell()
    try:
        sb = shell.source_builder
        # Sandbox Sources so we do not touch real data.
        tmp = pathlib.Path(tempfile.mkdtemp())
        saved = controller.SOURCES_ROOT
        controller.SOURCES_ROOT = tmp / "Sources"
        try:
            sb.collection_var.set("teppei_beginner")
            sb.episode_var.set("63")
            sb.source_type_var.set("podcast_transcript")
            sb.origin_var.set("con_teppei_podcast")
            sb.text_area.insert("1.0", "第六十三回のテストです。\n")
            sb._on_text_changed()
            sb.on_save()
            check("saved state", sb._current_state == "SAVED")
            check("saved path set", sb._saved_path is not None)
            canonical = sb._saved_path
            check("canonical exists", canonical.is_file())
            package_path = source_package.package_path_for(canonical)
            check("package exists", package_path.is_file())
            data = json.loads(package_path.read_text(encoding="utf-8"))
            check("package type", data["artifact_type"] == "source_package")
            check("source_id",
                  data["source_id"] == "podcast_transcript_teppei-beginner_ep063")
        finally:
            controller.SOURCES_ROOT = saved
    finally:
        root.destroy()


@test("open processing instantiates the existing processing window")
def _():
    root, shell = make_shell()
    try:
        with mock.patch("processing_tab_gui.ProcessingTabWindow") as cls:
            shell._open_processing()
        cls.assert_called_once_with(shell)
    finally:
        root.destroy()


@test("open analysis opens the analysis window")
def _():
    root, shell = make_shell()
    try:
        with mock.patch("analysis_tab_gui.AnalysisTabWindow") as cls:
            shell._open_analysis()
        cls.assert_called_once_with(shell)
    finally:
        root.destroy()


@test("existing modules import correctly")
def _():
    modules = {
        "Source Builder": ("controller", "source_package", "handoff",
                           "processing_tab", "processing_tab_gui",
                           "analysis_tab_gui", "diagnostics", "gui"),
        "Production Manager": ("production_manager",),
    }
    saved_path = list(sys.path)
    try:
        for folder, names in modules.items():
            sys.path.insert(0, str(PROJECT_ROOT / folder))
            for name in names:
                try:
                    importlib.import_module(name)
                    check(f"module {folder}/{name}", True)
                except Exception:
                    check(f"module {folder}/{name}", False,
                          detail=f"failed to import {name}")
    finally:
        sys.path[:] = saved_path


@test("shell does not move or delete any existing launch path")
def _():
    existing = [
        "Source Builder/source_builder.py",
        "Source Builder/gui.py",
        "Production Manager/production_manager.py",
        "Subtitle Importer/subtitle_importer.py",
    ]
    for rel in existing:
        check(f"exists: {rel}", (PROJECT_ROOT / rel).is_file())


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
