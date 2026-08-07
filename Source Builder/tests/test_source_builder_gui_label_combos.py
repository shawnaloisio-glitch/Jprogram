#!/usr/bin/env python3
"""
test_source_builder_gui_label_combos.py

GUI-level tests for friendly display names in the Source Builder:

- the source type has no visible field anymore: it is tracked internally as
  a raw id from Config (single real value), which downstream save logic
  persists raw (never the display label),
- the Origin dropdown shows display names, not raw ids,
- the origin id var keeps holding the raw id through every round trip,
- a saved source persists the raw ids (never the display labels),
- display names that equal the id still show the id, and unknown/legacy ids
  display as-is without blanking or crashing.

The sandboxed Config includes a source type and an origin whose display_name
differs from their id, so the label behaviour is actually exercised (the real
Config data is never touched).

Run:
    python "Source Builder/tests/test_source_builder_gui_label_combos.py"
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
import tkinter.ttk as ttk

import config_loader
import controller
import gui
import gui_settings
import metadata_editor
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
        metadata_editor.CONFIG_DIR,
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
    # clean_text (the only processable type; label != id), article
    # (non-processable, label == id, hidden from the dropdown).
    (config_dir / "source_types.json").write_text(json.dumps({
        "source_types": [
            {"source_type_id": "clean_text",
             "display_name": "Clean Text"},
            {"source_type_id": "article",
             "display_name": "article"},
        ],
    }), encoding="utf-8")
    # cijsub (label != id), nhk_news (label == id).
    (config_dir / "origins.json").write_text(json.dumps({
        "origins": [
            {"origin_id": "cijsub", "display_name": "CiJapanese Subs"},
            {"origin_id": "nhk_news", "display_name": "nhk_news"},
        ],
    }), encoding="utf-8")
    (config_dir / "styles.json").write_text(json.dumps({
        "styles": [
            {"style_id": 1, "display_name": "Documentary"},
            {"style_id": 2, "display_name": "Podcast"},
        ],
    }), encoding="utf-8")

    controller.SOURCES_ROOT = tmp / "Sources"
    gui_settings.SETTINGS_PATH = tmp / "gui_settings.json"
    quick_presets.PRESETS_PATH = tmp / "quick_presets.json"
    config_loader.CONFIG_DIR = config_dir
    metadata_editor.CONFIG_DIR = config_dir
    paths.COLLECTIONS_CONFIG = config_dir / "collections.json"
    paths.ORIGINS_CONFIG = config_dir / "origins.json"

    def restore():
        (controller.SOURCES_ROOT, gui_settings.SETTINGS_PATH,
         quick_presets.PRESETS_PATH, config_loader.CONFIG_DIR,
         metadata_editor.CONFIG_DIR, paths.COLLECTIONS_CONFIG,
         paths.ORIGINS_CONFIG) = saved

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


def make_visible_app(restore):
    """Build the app with a visible root so child windows can map."""
    root = tk.Tk()
    app = gui.SourceBuilderApp(root)
    return root, app


def find_combo_by_values(widget, values):
    """Return the first ttk.Combobox whose offered values match exactly."""
    for child in widget.winfo_children():
        if isinstance(child, ttk.Combobox):
            if tuple(child.cget("values")) == tuple(values):
                return child
        found = find_combo_by_values(child, values)
        if found is not None:
            return found
    return None


@test("source type id comes from config; origin combo shows display names")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            check("source type id from config",
                  app.source_type_var.get() == "clean_text")

            og_values = app.origin_combo.cget("values")
            check("origin labels shown",
                  og_values == ("CiJapanese Subs", "nhk_news"))
            check("origin raw id hidden", "cijsub" not in og_values)
        finally:
            root.destroy()
    finally:
        restore()


@test("programmatic id set keeps the raw source type id and origin label")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            # Same pattern settings/snapshot/preset restore use.
            app.source_type_var.set("clean_text")
            app.origin_var.set("cijsub")
            check("source type id retained",
                  app.source_type_var.get() == "clean_text")
            check("origin label shown",
                  app.origin_display_var.get() == "CiJapanese Subs")
            check("origin combo shows label",
                  app.origin_combo.get() == "CiJapanese Subs")
            check("origin id retained",
                  app.origin_var.get() == "cijsub")
        finally:
            root.destroy()
    finally:
        restore()


@test("origin label selection maps back to the raw id in the id var")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            # Simulate picking a label from the origin dropdown (the
            # <<ComboboxSelected>> handler reads the shown label and maps it
            # back to the id). The source type has no visible field, so
            # there is nothing to select for it.
            app.origin_combo.set("CiJapanese Subs")
            app._on_origin_selected()
            check("origin id from label",
                  app.origin_var.get() == "cijsub")
            check("display stays the label",
                  app.origin_display_var.get() == "CiJapanese Subs")
        finally:
            root.destroy()
    finally:
        restore()


@test("persisted settings restore keeps the raw source type id and origin label")
def _():
    restore = sandbox()
    try:
        # Pre-seed the settings file exactly as a prior session would have
        # written it: raw ids.
        gui_settings.save_settings(
            {"source_type": "clean_text", "origin": "cijsub"})
        root, app = make_app(restore)
        try:
            check("source type id restored",
                  app.source_type_var.get() == "clean_text")
            check("origin id restored",
                  app.origin_var.get() == "cijsub")
            check("origin label shown",
                  app.origin_combo.get() == "CiJapanese Subs")
        finally:
            root.destroy()
    finally:
        restore()


@test("saved source persists raw ids, never the display labels")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("teppei_beginner")
            app.episode_var.set("70")
            app.source_type_var.set("clean_text")
            app.origin_var.set("cijsub")
            app.material_level_var.set("1")
            app.text_area.insert("1.0", "こんにちは。\n元気です。\n")
            app._on_text_changed()
            app._refresh_ready_state()
            check("ready", app._current_state == "READY")
            app.on_save()
            check("saved", app._current_state == "SAVED")
            package_path = source_package.package_path_for(app._saved_path)
            data = json.loads(package_path.read_text(encoding="utf-8"))
            check("package source type is the raw id",
                  data["source_type"] == "clean_text")
            check("package origin is the raw id",
                  data["origin"] == "cijsub")
            check("no display label leaked into source type",
                  data["source_type"] != "Clean Text")
            check("no display label leaked into origin",
                  data["origin"] != "CiJapanese Subs")
            # Settings persisted during the save also hold raw ids.
            persisted = gui_settings.load_settings()
            check("settings source type raw",
                  persisted["source_type"] == "clean_text")
            check("settings origin raw",
                  persisted["origin"] == "cijsub")
        finally:
            root.destroy()
    finally:
        restore()


@test("display names equal to the id show the id")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            # nhk_news is configured with display_name == id and is shown
            # as-is in the origin dropdown.
            app.origin_var.set("nhk_news")
            check("origin shows id",
                  app.origin_combo.get() == "nhk_news")
        finally:
            root.destroy()
    finally:
        restore()


@test("unknown stored ids display as-is without blanking or crashing")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.source_type_var.set("obsolete_type")
            app.origin_var.set("stale_origin")
            check("unknown source type id retained",
                  app.source_type_var.get() == "obsolete_type")
            check("unknown origin shows as-is",
                  app.origin_combo.get() == "stale_origin")
            check("unknown origin id retained",
                  app.origin_var.get() == "stale_origin")
        finally:
            root.destroy()
    finally:
        restore()


@test("preset editor origin combo shows labels and stores raw ids")
def _():
    restore = sandbox()
    try:
        quick_presets.save_slot(
            1, "Subs Preset", "standalone",
            source_type="clean_text", origin="cijsub")
        root, app = make_visible_app(restore)
        try:
            app._open_preset_editor()
            editor = [w for w in root.winfo_children()
                      if isinstance(w, tk.Toplevel)][0]
            og_combo = find_combo_by_values(
                editor, ("CiJapanese Subs", "nhk_news"))
            check("origin combo shows labels", og_combo is not None)
            if og_combo is not None:
                check("origin label loaded",
                      og_combo.get() == "CiJapanese Subs")
        finally:
            root.destroy()
    finally:
        restore()


# ============================================================
# Material Level / Style / Duration form fields
# ============================================================

@test("material level combo offers all configured levels by display name")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            values = app.material_level_combo.cget("values")
            check("five levels in order", values == (
                "Ungraded", "Absolute Beginner", "Beginner",
                "Intermediate", "Advanced"))
            check("raw level hidden", "1" not in values)
        finally:
            root.destroy()
    finally:
        restore()


@test("material level selection maps the label back to the level id")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.material_level_combo.set("Absolute Beginner")
            app._apply_label_to_id(
                app.material_level_display_var, app.material_level_id_map,
                app.material_level_var)
            check("level id", app.material_level_var.get() == "1")
            check("display stays the label",
                  app.material_level_display_var.get() == "Absolute Beginner")
        finally:
            root.destroy()
    finally:
        restore()


@test("style combo shows (none) leading entry before style labels")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            values = app.style_combo.cget("values")
            check("leading none", values[0] == "(none)")
            check("styles offered",
                  "Documentary" in values and "Podcast" in values)
            check("raw ids hidden", "1" not in values)
        finally:
            root.destroy()
    finally:
        restore()


@test("style selection maps label to id; (none) maps to blank")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.style_combo.set("Documentary")
            app._apply_label_to_id(
                app.style_display_var, app.style_id_map, app.style_id_var)
            check("style id", app.style_id_var.get() == "1")

            app.style_combo.set("(none)")
            app._apply_label_to_id(
                app.style_display_var, app.style_id_map, app.style_id_var)
            check("none -> blank", app.style_id_var.get() == "")
        finally:
            root.destroy()
    finally:
        restore()


@test("save passes material level, style id, and duration to the package")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("teppei_beginner")
            app.episode_var.set("80")
            app.source_type_var.set("clean_text")
            app.origin_var.set("cijsub")
            app.material_level_var.set("1")
            app.style_combo.set("Documentary")
            app._apply_label_to_id(
                app.style_display_var, app.style_id_map, app.style_id_var)
            app.duration_var.set("90")
            app.text_area.insert("1.0", "本文。\n")
            app._on_text_changed()
            app._refresh_ready_state()
            check("ready", app._current_state == "READY")
            app.on_save()
            check("saved", app._current_state == "SAVED")
            package = json.loads(source_package.package_path_for(
                app._saved_path).read_text(encoding="utf-8"))
            check("material level int", package["material_level"] == 1)
            check("style id int", package["style_id"] == 1)
            check("duration int", package["duration_seconds"] == 90)
        finally:
            root.destroy()
    finally:
        restore()


@test("no style selected saves style_id None (not the blank string)")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("teppei_beginner")
            app.episode_var.set("81")
            app.source_type_var.set("clean_text")
            app.origin_var.set("cijsub")
            app.material_level_var.set("2")
            # Style left at the default "(none)" entry.
            app.text_area.insert("1.0", "本文。\n")
            app._on_text_changed()
            app.on_save()
            check("saved", app._current_state == "SAVED")
            package = json.loads(source_package.package_path_for(
                app._saved_path).read_text(encoding="utf-8"))
            check("style none -> null", package["style_id"] is None)
        finally:
            root.destroy()
    finally:
        restore()


@test("blank duration saves None")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("teppei_beginner")
            app.episode_var.set("82")
            app.source_type_var.set("clean_text")
            app.origin_var.set("cijsub")
            app.material_level_var.set("2")
            app.text_area.insert("1.0", "本文。\n")
            app._on_text_changed()
            app.on_save()
            package = json.loads(source_package.package_path_for(
                app._saved_path).read_text(encoding="utf-8"))
            check("duration none", package["duration_seconds"] is None)
        finally:
            root.destroy()
    finally:
        restore()


@test("invalid duration blocks the save with a plain message")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("teppei_beginner")
            app.episode_var.set("83")
            app.source_type_var.set("clean_text")
            app.origin_var.set("cijsub")
            app.material_level_var.set("2")
            app.text_area.insert("1.0", "本文。\n")
            app.duration_var.set("abc")
            app._on_text_changed()
            app._refresh_ready_state()
            # Duration is non-blocking in the engine; the save itself rejects it.
            app.on_save()
            check("not saved", app._current_state != "SAVED")
            check("no canonical file", app._saved_path is None)
            check("plain message",
                  "Duration must be a non-negative number."
                  in app.status_var.get())
        finally:
            root.destroy()
    finally:
        restore()


@test("negative duration also blocks the save")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("teppei_beginner")
            app.episode_var.set("84")
            app.source_type_var.set("clean_text")
            app.origin_var.set("cijsub")
            app.material_level_var.set("2")
            app.text_area.insert("1.0", "本文。\n")
            app.duration_var.set("-5")
            app._on_text_changed()
            app.on_save()
            check("not saved", app._current_state != "SAVED")
            check("plain message",
                  "Duration must be a non-negative number."
                  in app.status_var.get())
        finally:
            root.destroy()
    finally:
        restore()


@test("material level restores from persisted settings when valid")
def _():
    restore = sandbox()
    try:
        gui_settings.save_settings({"material_level": "3"})
        root, app = make_app(restore)
        try:
            check("level restored", app.material_level_var.get() == "3")
            check("label shown",
                  app.material_level_combo.get() == "Intermediate")
        finally:
            root.destroy()
    finally:
        restore()


@test("material level restore ignores an invalid stored level")
def _():
    restore = sandbox()
    try:
        gui_settings.save_settings({"material_level": "99"})
        root, app = make_app(restore)
        try:
            check("invalid level not restored",
                  app.material_level_var.get() == "")
        finally:
            root.destroy()
    finally:
        restore()


@test("Add Another retains material level and style, resets duration")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app.collection_var.set("teppei_beginner")
            app.episode_var.set("85")
            app.source_type_var.set("clean_text")
            app.origin_var.set("cijsub")
            app.material_level_var.set("1")
            app.style_combo.set("Documentary")
            app._apply_label_to_id(
                app.style_display_var, app.style_id_map, app.style_id_var)
            app.duration_var.set("60")
            app.text_area.insert("1.0", "本文。\n")
            app._on_text_changed()
            app.on_save()
            check("saved", app._current_state == "SAVED")
            app.on_next_source()
            check("material level retained",
                  app.material_level_var.get() == "1")
            check("style retained", app.style_id_var.get() == "1")
            check("duration reset", app.duration_var.get() == "")
            check("episode incremented", app.episode_var.get() == "86")
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
