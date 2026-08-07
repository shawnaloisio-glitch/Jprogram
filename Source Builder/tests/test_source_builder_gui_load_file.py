#!/usr/bin/env python3
"""
test_source_builder_gui_load_file.py

GUI-level tests for the Source Builder Load File feature:

- successful text load places contents into the source text area,
- empty file handling,
- missing file handling,
- load does not create a source file,
- Ready State updates after loading,
- unreadable (non-UTF-8) file handling.

The file picker and message boxes are patched so no interactive dialogs are
shown. Config, Sources, settings, and presets are redirected to temp dirs.

Run:
    python "Source Builder/tests/test_source_builder_gui_load_file.py"
"""

import pathlib
import sys
import tempfile
from unittest.mock import patch

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))

import tkinter as tk

import controller
import gui
import gui_settings
import paths
import quick_presets


def sandbox():
    """Redirect Sources, settings, presets, and Intake into temp dirs."""
    saved_sources = controller.SOURCES_ROOT
    saved_settings = gui_settings.SETTINGS_PATH
    saved_presets = quick_presets.PRESETS_PATH
    saved_project_root = gui.PROJECT_ROOT
    saved_intake = paths.INTAKE

    tmp = pathlib.Path(tempfile.mkdtemp())
    controller.SOURCES_ROOT = tmp / "Sources"
    gui_settings.SETTINGS_PATH = tmp / "gui_settings.json"
    quick_presets.PRESETS_PATH = tmp / "quick_presets.json"
    # Point the app's project root and workspace Intake at the temp dir.
    gui.PROJECT_ROOT = tmp
    paths.INTAKE = tmp / "Intake"

    def restore():
        controller.SOURCES_ROOT = saved_sources
        gui_settings.SETTINGS_PATH = saved_settings
        quick_presets.PRESETS_PATH = saved_presets
        gui.PROJECT_ROOT = saved_project_root
        paths.INTAKE = saved_intake

    return restore


def make_app(restore):
    root = tk.Tk()
    root.withdraw()
    app = gui.SourceBuilderApp(root)
    return root, app


def make_file(text):
    tmp = pathlib.Path(tempfile.mkdtemp())
    path = tmp / "loaded.txt"
    path.write_text(text, encoding="utf-8")
    return path


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


def text_area_content(app):
    return app.text_area.get("1.0", "end")


@test("load file places contents into the source text area")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            path = make_file("こんにちは。\nお元気ですか？\n")
            with patch.object(gui.filedialog, "askopenfilename",
                              return_value=str(path)):
                app._load_file()
            check("text loaded", "こんにちは。\nお元気ですか？" in
                  text_area_content(app))
            check("status mentions loaded", "Loaded: loaded.txt" in
                  app.status_var.get())
        finally:
            root.destroy()
    finally:
        restore()


@test("load does not create a source file")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            path = make_file("hello\n")
            with patch.object(gui.filedialog, "askopenfilename",
                              return_value=str(path)):
                app._load_file()
            # No collection is selected, so no canonical file can exist.
            found = list((controller.SOURCES_ROOT).rglob("*.txt"))
            check("no source file created", found == [])
        finally:
            root.destroy()
    finally:
        restore()


@test("empty file shows error and loads nothing")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            path = make_file("   \n\n")
            errors = []
            with patch.object(gui.filedialog, "askopenfilename",
                              return_value=str(path)), \
                 patch.object(gui.messagebox, "showerror",
                              side_effect=lambda *a, **k: errors.append(a)):
                app._load_file()
            check("error shown", len(errors) == 1)
            check("empty message", "empty" in str(errors[0]).lower())
            check("area still empty", text_area_content(app).strip() == "")
        finally:
            root.destroy()
    finally:
        restore()


@test("missing file shows error and loads nothing")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            errors = []
            with patch.object(gui.filedialog, "askopenfilename",
                              return_value=r"C:\definitely\missing.txt"), \
                 patch.object(gui.messagebox, "showerror",
                              side_effect=lambda *a, **k: errors.append(a)):
                app._load_file()
            check("error shown", len(errors) == 1)
            check("area still empty", text_area_content(app).strip() == "")
        finally:
            root.destroy()
    finally:
        restore()


@test("cancel picker loads nothing")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            with patch.object(gui.filedialog, "askopenfilename",
                              return_value=""):
                app._load_file()
            check("area still empty", text_area_content(app).strip() == "")
        finally:
            root.destroy()
    finally:
        restore()


@test("unreadable (non-UTF-8) file shows error")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            tmp = pathlib.Path(tempfile.mkdtemp())
            path = tmp / "binary.txt"
            path.write_bytes(b"\xff\xfe\x00\x01")
            errors = []
            with patch.object(gui.filedialog, "askopenfilename",
                              return_value=str(path)), \
                 patch.object(gui.messagebox, "showerror",
                              side_effect=lambda *a, **k: errors.append(a)):
                app._load_file()
            check("error shown", len(errors) == 1)
            check("area still empty", text_area_content(app).strip() == "")
        finally:
            root.destroy()
    finally:
        restore()


@test("ready state updates after loading")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            check("incomplete before",
                  app._current_state == "INCOMPLETE")
            # Fill metadata; only source text remains missing.
            app.collection_var.set("teppei_beginner")
            app.episode_var.set("1")
            app.source_type_var.set("clean_text")
            app.origin_var.set("con_teppei_podcast")
            app.material_level_var.set("1")
            check("still incomplete without text",
                  app._current_state == "INCOMPLETE")

            path = make_file("こんにちは。\n")
            with patch.object(gui.filedialog, "askopenfilename",
                              return_value=str(path)):
                app._load_file()
            check("ready after load", app._current_state == "READY")
            check("save enabled", app.save_button.cget("state") == "normal")
        finally:
            root.destroy()
    finally:
        restore()


@test("load file default dir: first open targets Intake")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            intake = paths.INTAKE
            intake.mkdir(parents=True, exist_ok=True)
            captured = {}
            with patch.object(
                    gui.filedialog, "askopenfilename",
                    side_effect=lambda **kw: captured.update(kw) or ""):
                app._load_file()
            check("initialdir is Intake",
                  pathlib.Path(captured["initialdir"]) == intake)
        finally:
            root.destroy()
    finally:
        restore()


@test("load file default dir: previous folder remembered in session")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            other = pathlib.Path(tempfile.mkdtemp()) / "elsewhere"
            other.mkdir(parents=True, exist_ok=True)
            src = other / "loaded.txt"
            src.write_text("hello\n", encoding="utf-8")

            # First load from the "elsewhere" folder.
            with patch.object(gui.filedialog, "askopenfilename",
                              return_value=str(src)):
                app._load_file()
            check("remembered folder set", app._load_file_dir == other)

            # Second open should use the remembered folder, not Intake.
            captured = {}
            with patch.object(
                    gui.filedialog, "askopenfilename",
                    side_effect=lambda **kw: captured.update(kw) or ""):
                app._load_file()
            check("initialdir is remembered folder",
                  pathlib.Path(captured["initialdir"]) == other)
        finally:
            root.destroy()
    finally:
        restore()


@test("load file default dir: fallback to project root when Intake missing")
def _():
    restore = sandbox()
    try:
        # Intake does not exist during this test.
        intake = paths.INTAKE
        had_intake = intake.exists()
        if had_intake:
            intake.rename(intake.with_name("Intake_bak"))
        try:
            root, app = make_app(restore)
            try:
                captured = {}
                with patch.object(
                        gui.filedialog, "askopenfilename",
                        side_effect=lambda **kw: captured.update(kw) or ""):
                    app._load_file()
                check("initialdir is project root",
                      pathlib.Path(captured["initialdir"])
                      == gui.PROJECT_ROOT)
            finally:
                root.destroy()
        finally:
            if had_intake:
                intake.with_name("Intake_bak").rename(intake)
    finally:
        restore()


# ============================================================
# Issue 2: next-file suggestion logic
# ============================================================

def make_intake_files(names):
    """Create a temp Intake-like dir with the given .txt files."""
    directory = pathlib.Path(tempfile.mkdtemp())
    for name in names:
        (directory / name).write_text(f"{name}\n", encoding="utf-8")
    return directory


@test("next candidate: first use suggests first file alphabetically")
def _():
    directory = make_intake_files(["b.txt", "a.txt", "c.txt"])
    candidate = gui.next_load_file_candidate(directory, None)
    check("first file suggested", candidate.name == "a.txt")


@test("next candidate: advances to the next file after last loaded")
def _():
    directory = make_intake_files(["a.txt", "b.txt", "c.txt"])
    candidate = gui.next_load_file_candidate(directory, directory / "a.txt")
    check("next file suggested", candidate.name == "b.txt")


@test("next candidate: last file has no next")
def _():
    directory = make_intake_files(["a.txt", "b.txt", "c.txt"])
    candidate = gui.next_load_file_candidate(directory, directory / "c.txt")
    check("no next", candidate is None)


@test("next candidate: empty directory yields None")
def _():
    directory = pathlib.Path(tempfile.mkdtemp())
    candidate = gui.next_load_file_candidate(directory, None)
    check("no candidate", candidate is None)


@test("next candidate: missing previous file falls back to first")
def _():
    directory = make_intake_files(["b.txt", "a.txt"])
    candidate = gui.next_load_file_candidate(directory,
                                             directory / "ghost.txt")
    check("falls back to first", candidate.name == "a.txt")


@test("next candidate: missing directory yields None")
def _():
    candidate = gui.next_load_file_candidate(
        pathlib.Path(tempfile.mkdtemp()) / "missing", None)
    check("no candidate", candidate is None)


@test("next candidate: ignores non-txt files")
def _():
    directory = pathlib.Path(tempfile.mkdtemp())
    (directory / "a.txt").write_text("a\n", encoding="utf-8")
    (directory / "notes.md").write_text("m\n", encoding="utf-8")
    candidate = gui.next_load_file_candidate(directory, None)
    check("only txt considered", candidate.name == "a.txt")


# ============================================================
# Issue 2: picker receives the suggested initial file
# ============================================================

@test("picker: first use opens Intake and highlights first file")
def _():
    restore = sandbox()
    try:
        intake = paths.INTAKE
        intake.mkdir(parents=True, exist_ok=True)
        (intake / "ep01.txt").write_text("one\n", encoding="utf-8")
        (intake / "ep02.txt").write_text("two\n", encoding="utf-8")
        root, app = make_app(restore)
        try:
            captured = {}
            with patch.object(
                    gui.filedialog, "askopenfilename",
                    side_effect=lambda **kw: captured.update(kw) or ""):
                app._load_file()
            check("initialdir is intake",
                  pathlib.Path(captured["initialdir"]) == intake)
            check("initialfile is first file",
                  captured["initialfile"] == "ep01.txt")
        finally:
            root.destroy()
    finally:
        restore()


@test("picker: second load suggests the next file")
def _():
    restore = sandbox()
    try:
        intake = paths.INTAKE
        intake.mkdir(parents=True, exist_ok=True)
        (intake / "ep01.txt").write_text("one\n", encoding="utf-8")
        (intake / "ep02.txt").write_text("two\n", encoding="utf-8")
        root, app = make_app(restore)
        try:
            # First load picks ep01.txt.
            with patch.object(gui.filedialog, "askopenfilename",
                              return_value=str(intake / "ep01.txt")):
                app._load_file()
            check("last loaded remembered",
                  app._last_loaded_file == intake / "ep01.txt")
            # Second load should highlight ep02.txt.
            captured = {}
            with patch.object(
                    gui.filedialog, "askopenfilename",
                    side_effect=lambda **kw: captured.update(kw) or ""):
                app._load_file()
            check("initialfile is next file",
                  captured["initialfile"] == "ep02.txt")
        finally:
            root.destroy()
    finally:
        restore()


@test("picker: last file handled (no next -> normal picker)")
def _():
    restore = sandbox()
    try:
        intake = paths.INTAKE
        intake.mkdir(parents=True, exist_ok=True)
        (intake / "ep01.txt").write_text("one\n", encoding="utf-8")
        (intake / "ep02.txt").write_text("two\n", encoding="utf-8")
        root, app = make_app(restore)
        try:
            with patch.object(gui.filedialog, "askopenfilename",
                              return_value=str(intake / "ep02.txt")):
                app._load_file()
            captured = {}
            with patch.object(
                    gui.filedialog, "askopenfilename",
                    side_effect=lambda **kw: captured.update(kw) or ""):
                app._load_file()
            check("no initialfile when at last file",
                  captured.get("initialfile", "") == "")
        finally:
            root.destroy()
    finally:
        restore()


@test("picker: empty Intake handled (no initialfile)")
def _():
    restore = sandbox()
    try:
        intake = paths.INTAKE
        intake.mkdir(parents=True, exist_ok=True)
        root, app = make_app(restore)
        try:
            captured = {}
            with patch.object(
                    gui.filedialog, "askopenfilename",
                    side_effect=lambda **kw: captured.update(kw) or ""):
                app._load_file()
            check("no initialfile in empty intake",
                  captured.get("initialfile", "") == "")
        finally:
            root.destroy()
    finally:
        restore()


@test("picker: missing previous file falls back to first file")
def _():
    restore = sandbox()
    try:
        intake = paths.INTAKE
        intake.mkdir(parents=True, exist_ok=True)
        (intake / "ep01.txt").write_text("one\n", encoding="utf-8")
        (intake / "ep02.txt").write_text("two\n", encoding="utf-8")
        root, app = make_app(restore)
        try:
            app._last_loaded_file = intake / "ghost.txt"
            captured = {}
            with patch.object(
                    gui.filedialog, "askopenfilename",
                    side_effect=lambda **kw: captured.update(kw) or ""):
                app._load_file()
            check("falls back to first",
                  captured.get("initialfile", "") == "ep01.txt")
        finally:
            root.destroy()
    finally:
        restore()


@test("picker: cancel unchanged (no load, no last-file change)")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            with patch.object(gui.filedialog, "askopenfilename",
                              return_value=""):
                app._load_file()
            check("area still empty", text_area_content(app).strip() == "")
            check("last file unchanged", app._last_loaded_file is None)
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
