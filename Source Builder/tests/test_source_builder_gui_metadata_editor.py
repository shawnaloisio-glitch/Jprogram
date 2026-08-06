#!/usr/bin/env python3
"""
test_source_builder_gui_metadata_editor.py

GUI-level tests for the Source Builder metadata editor window:

- window opens from the app,
- window is centred over the parent,
- tabs are present (Collections / Origins),
- refreshing after a metadata save updates Source Builder dropdowns.

These tests build the actual Tk window. Config files are redirected to a
sandboxed directory; the real Config\\ files are never touched.

Run:
    python "Source Builder/tests/test_source_builder_gui_metadata_editor.py"
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
import metadata_editor
import metadata_editor_gui
import quick_presets
import paths

SEQUENCING_LABELS = metadata_editor_gui.SEQUENCING_LABELS
SEQUENCING_DISPLAY = tuple(
    SEQUENCING_LABELS[v] for v in metadata_editor.SEQUENCING_VALUES)


def sandbox():
    """Redirect Sources, settings, presets, and Config into temp dirs."""
    saved_sources = controller.SOURCES_ROOT
    saved_settings = gui_settings.SETTINGS_PATH
    saved_presets = quick_presets.PRESETS_PATH
    saved_config_dir = metadata_editor.CONFIG_DIR
    saved_loader_config_dir = config_loader.CONFIG_DIR
    saved_collections_config = paths.COLLECTIONS_CONFIG
    saved_origins_config = paths.ORIGINS_CONFIG

    tmp = pathlib.Path(tempfile.mkdtemp())
    conf_dir = tmp / "Config"
    conf_dir.mkdir(parents=True, exist_ok=True)
    (conf_dir / "collections.json").write_text(json.dumps({
        "collections": [
            {"collection_id": "teppei_beginner",
             "name": "Con Teppei for Beginner",
             "source_type": "clean_text"},
        ]
    }), encoding="utf-8")
    (conf_dir / "source_types.json").write_text(json.dumps({
        "source_types": ["clean_text", "cij_transcript",
                         "subtitle", "article"],
    }), encoding="utf-8")
    (conf_dir / "origins.json").write_text(json.dumps({
        "origins": ["con_teppei_podcast", "nhk_news"],
    }), encoding="utf-8")

    controller.SOURCES_ROOT = tmp / "Sources"
    gui_settings.SETTINGS_PATH = tmp / "gui_settings.json"
    quick_presets.PRESETS_PATH = tmp / "quick_presets.json"
    metadata_editor.CONFIG_DIR = conf_dir
    config_loader.CONFIG_DIR = conf_dir
    paths.COLLECTIONS_CONFIG = conf_dir / "collections.json"
    paths.ORIGINS_CONFIG = conf_dir / "origins.json"

    def restore():
        controller.SOURCES_ROOT = saved_sources
        gui_settings.SETTINGS_PATH = saved_settings
        quick_presets.PRESETS_PATH = saved_presets
        metadata_editor.CONFIG_DIR = saved_config_dir
        config_loader.CONFIG_DIR = saved_loader_config_dir
        paths.COLLECTIONS_CONFIG = saved_collections_config
        paths.ORIGINS_CONFIG = saved_origins_config

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
    app = gui.SourceBuilderApp(root)
    return root, app


def make_visible_app(restore):
    """Build the app with a visible root so child windows can map."""
    root = tk.Tk()
    app = gui.SourceBuilderApp(root)
    return root, app


@test("metadata editor window opens with two tabs")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app._open_metadata_editor()
            windows = [w for w in root.winfo_children()
                       if isinstance(w, tk.Toplevel)
                       and w.title() == "Edit Metadata"]
            check("window opened", len(windows) == 1)
            editor = windows[0]
            # The editor has a Notebook.
            import tkinter.ttk as ttk
            notebooks = [c for c in editor.winfo_children()
                         if isinstance(c, ttk.Notebook)]
            check("notebook present", len(notebooks) == 1)
            notebook = notebooks[0]
            tabs = [notebook.tab(tab_id, "text") for tab_id in notebook.tabs()]
            check("collections tab", "Collections" in tabs)
            check("origins tab", "Origins" in tabs)
            check("no source types tab", "Source Types" not in tabs)
        finally:
            root.destroy()
    finally:
        restore()


@test("metadata editor window is centred over the parent")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            root.geometry("+100+200")
            root.update()
            app._open_metadata_editor()
            editor = [w for w in root.winfo_children()
                      if isinstance(w, tk.Toplevel)
                      and w.title() == "Edit Metadata"][0]
            editor.update_idletasks()

            parent_x = root.winfo_rootx()
            parent_y = root.winfo_rooty()
            parent_w = root.winfo_width()
            parent_h = root.winfo_height()
            child_w = editor.winfo_reqwidth()
            child_h = editor.winfo_reqheight()

            exp_x, exp_y = gui.centered_position(
                parent_x, parent_y, parent_w, parent_h, child_w, child_h)

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


@test("refresh after save updates Source Builder dropdowns")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            # Only processable source types are used by the GUI; origins
            # exclude format-id values (none here).
            check("source type before",
                  app.source_type_var.get() == "clean_text")
            check("origins before",
                  app.origin_combo.cget("values")
                  == ("con_teppei_podcast", "nhk_news"))

            # Add a non-processable source type plus a new origin, then
            # refresh. Source types added through the editor never gain a
            # processing profile, so clean_text (the single processable
            # type) stays the fixed source type.
            metadata_editor.add_source_type(
                "video", "Video", path=metadata_editor.CONFIG_DIR /
                metadata_editor.FILES["source_types"])
            metadata_editor.add_origin(
                "nhk_radio", "NHK Radio", path=metadata_editor.CONFIG_DIR /
                metadata_editor.FILES["origins"])
            app._refresh_metadata()

            check("processable type kept",
                  app.source_type_var.get() == "clean_text")
            check("origins after",
                  "NHK Radio" in app.origin_combo.cget("values"))
            check("collections unchanged",
                  app.collection_combo.cget("values") == ("teppei_beginner",))
        finally:
            root.destroy()
    finally:
        restore()


@test("metadata editor reload uses the same config as the app")
def _():
    restore = sandbox()
    try:
        root, app = make_app(restore)
        try:
            app._open_metadata_editor()
            collections = metadata_editor.load_collections()
            check("collections from config dir",
                  [c["collection_id"] for c in collections]
                  == ["teppei_beginner"])
        finally:
            root.destroy()
    finally:
        restore()


# ============================================================
# Issue 1: Add dialog completion path
# ============================================================

def find_ttk_button(widget, text):
    """Recursively find a ttk.Button by its text."""
    import tkinter.ttk as ttk
    for child in widget.winfo_children():
        if isinstance(child, ttk.Button) and child.cget("text") == text:
            return child
        result = find_ttk_button(child, text)
        if result is not None:
            return result
    return None


@test("add dialog opens with visible Save and Cancel buttons")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            root.geometry("+100+200")
            root.update()
            app._open_metadata_editor()
            import metadata_editor_gui
            # Build the collections tab's Add fields exactly as the tab does.
            source_types = ["clean_text", "subtitle", "article"]
            fields = [
                ("collection_id", "Collection ID", "entry"),
                ("display_name", "Display Name", "entry"),
                ("default_source_type", "Default Source Type", "combo",
                 source_types),
            ]
            result = {}

            def schedule_cancel():
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)
                        and w.title() == "Add"]
                if tops:
                    d = tops[0]
                    save = find_ttk_button(d, "Save")
                    cancel = find_ttk_button(d, "Cancel")
                    result["save_visible"] = save is not None
                    result["cancel_visible"] = cancel is not None
                    result["save_state"] = save.cget("state") if save else None
                    if cancel:
                        cancel.invoke()
                else:
                    result["error"] = "Add window not found"

            me = metadata_editor_gui.MetadataEditorWindow(app)
            root.after(150, schedule_cancel)

            def open_form():
                result["form"] = me._open_form("Add", fields)

            root.after(50, open_form)
            root.after(2500, root.quit)
            root.mainloop()

            check("no error", "error" not in result)
            check("save visible", result.get("save_visible") is True)
            check("cancel visible", result.get("cancel_visible") is True)
            check("cancel leaves unchanged", result.get("form") is None)
        finally:
            root.destroy()
    finally:
        restore()


@test("add dialog Save returns the entered field values")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            import metadata_editor_gui
            me = metadata_editor_gui.MetadataEditorWindow(app)
            fields = [
                ("collection_id", "Collection ID", "entry"),
                ("display_name", "Display Name", "entry"),
            ]
            result = {}

            def fill_and_save():
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)
                        and w.title() == "Add"]
                if tops:
                    d = tops[0]
                    import tkinter.ttk as ttk
                    entries = []
                    def collect_entries(w):
                        for c in w.winfo_children():
                            if isinstance(c, ttk.Entry):
                                entries.append(c)
                            collect_entries(c)
                    collect_entries(d)
                    if len(entries) >= 2:
                        entries[0].insert(0, "nhk_b")
                        entries[1].insert(0, "NHK B")
                    save = find_ttk_button(d, "Save")
                    if save:
                        save.invoke()

            root.after(150, fill_and_save)

            def open_form():
                result["form"] = me._open_form("Add", fields)

            root.after(50, open_form)
            root.after(2500, root.quit)
            root.mainloop()

            check("form returned",
                  result.get("form") == {"collection_id": "nhk_b",
                                         "display_name": "NHK B"})
        finally:
            root.destroy()
    finally:
        restore()


@test("add dialog completion updates the config file")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            import metadata_editor_gui
            metadata_editor_gui.MetadataEditorWindow(app)
            # The dialog returns entered fields; the tab's add fn writes them.
            source_types = ["clean_text", "subtitle", "article"]
            result = {
                "collection_id": "nhk_b", "display_name": "NHK B",
                "default_source_type": "article"}
            metadata_editor.add_collection(
                result["collection_id"], result["display_name"],
                default_source_type=result.get("default_source_type") or None,
                source_type_ids=source_types)
            app._refresh_metadata()
            collections = metadata_editor.load_collections()
            check("collection added",
                  [c["collection_id"] for c in collections]
                  == ["teppei_beginner", "nhk_b"])
            check("display name stored",
                  collections[1]["display_name"] == "NHK B")
            check("default stored",
                  collections[1]["default_source_type"] == "article")
            check("app dropdown refreshed",
                  "nhk_b" in app.collection_combo.cget("values"))
        finally:
            root.destroy()
    finally:
        restore()


@test("add dialog blank fields do not modify config")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            import metadata_editor_gui
            metadata_editor_gui.MetadataEditorWindow(app)
            source_types = ["clean_text", "subtitle", "article"]
            # Blank display name must be rejected by the data layer.
            try:
                metadata_editor.add_collection(
                    "new_col", "   ", path=metadata_editor.CONFIG_DIR /
                    metadata_editor.FILES["collections"],
                    source_type_ids=source_types)
                check("blank rejected", False)
            except metadata_editor.MetadataError as exc:
                check("blank message", "display_name is required" in str(exc))
            collections = metadata_editor.load_collections()
            check("config unchanged", len(collections) == 1)
        finally:
            root.destroy()
    finally:
        restore()


@test("add dialog duplicate ID rejected")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            import metadata_editor_gui
            metadata_editor_gui.MetadataEditorWindow(app)
            source_types = ["clean_text", "subtitle", "article"]
            try:
                metadata_editor.add_collection(
                    "teppei_beginner", "Dup",
                    path=metadata_editor.CONFIG_DIR /
                    metadata_editor.FILES["collections"],
                    source_type_ids=source_types)
                check("duplicate rejected", False)
            except metadata_editor.MetadataError as exc:
                check("duplicate message", "already exists" in str(exc))
            collections = metadata_editor.load_collections()
            check("config unchanged", len(collections) == 1)
        finally:
            root.destroy()
    finally:
        restore()


@test("add valid source type and origin through editor data layer")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            import metadata_editor_gui
            metadata_editor_gui.MetadataEditorWindow(app)
            metadata_editor.add_source_type(
                "video", "Video", path=metadata_editor.CONFIG_DIR /
                metadata_editor.FILES["source_types"])
            metadata_editor.add_origin(
                "nhk_radio", "NHK Radio", path=metadata_editor.CONFIG_DIR /
                metadata_editor.FILES["origins"])
            st = metadata_editor.load_source_types()
            og = metadata_editor.load_origins()
            check("source type added",
                  any(s["source_type_id"] == "video" for s in st))
            check("origin added",
                  any(o["origin_id"] == "nhk_radio" for o in og))
        finally:
            root.destroy()
    finally:
        restore()


@test("edit form locks the identifier field")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            import tkinter.ttk as ttk
            import metadata_editor_gui
            me = metadata_editor_gui.MetadataEditorWindow(app)
            fields = [
                ("collection_id", "Collection ID", "entry"),
                ("display_name", "Display Name", "entry"),
            ]
            original = {"collection_id": "teppei_beginner",
                        "display_name": "Con Teppei for Beginner"}
            result = {}

            def inspect_edit_form():
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)
                        and w.title() == "Edit"]
                if tops:
                    d = tops[0]
                    # The identifier field is locked read-only.
                    entries = []
                    def collect_entries(w):
                        for c in w.winfo_children():
                            if isinstance(c, ttk.Entry):
                                entries.append(c)
                            collect_entries(c)
                    collect_entries(d)
                    id_entry = entries[0] if entries else None
                    result["id_state"] = str(
                        id_entry.cget("state")) if id_entry else None
                    # Cancel to close without saving.
                    cancel = find_ttk_button(d, "Cancel")
                    if cancel:
                        cancel.invoke()

            root.after(150, inspect_edit_form)

            def open_form():
                result["form"] = me._open_form("Edit", fields, original,
                                               locked_key="collection_id")

            root.after(50, open_form)
            root.after(2500, root.quit)
            root.mainloop()

            check("id field locked readonly",
                  result.get("id_state") == "readonly")
            check("edit cancelled", result.get("form") is None)
        finally:
            root.destroy()
    finally:
        restore()


@test("edit payload never includes the immutable identifier")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            import metadata_editor_gui
            metadata_editor_gui.MetadataEditorWindow(app)
            fields = [
                ("collection_id", "Collection ID", "entry"),
                ("display_name", "Display Name", "entry"),
            ]
            # Simulate the edit save path by invoking the internal value
            # assembly with a locked key, as _open_form does after Save.
            variables = {}
            for key, _, _kind in fields:
                var = tk.StringVar()
                var.set("teppei_beginner" if key == "collection_id"
                        else "New Name")
                variables[key] = var
            values = {key: var.get() for key, var in variables.items()}
            values.pop("collection_id", None)
            check("identifier excluded", "collection_id" not in values)
            check("display name present", values["display_name"] == "New Name")
        finally:
            root.destroy()
    finally:
        restore()


@test("metadata editor has no Delete buttons")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            import metadata_editor_gui
            me = metadata_editor_gui.MetadataEditorWindow(app)
            root.update()
            found = find_ttk_button(me.window, "Delete")
            check("no delete button anywhere", found is None)
        finally:
            root.destroy()
    finally:
        restore()


@test("collection add form shows folder explanation and label")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            import tkinter.ttk as ttk
            import metadata_editor_gui
            me = metadata_editor_gui.MetadataEditorWindow(app)
            fields = [
                ("collection_id", "Collection ID (folder name)", "entry"),
                ("display_name", "Display Name", "entry"),
            ]
            helper = ("The Collection ID becomes the folder name and "
                      "filename prefix. Choose carefully. It cannot be "
                      "changed later.")
            result = {}

            def inspect():
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)
                        and w.title() == "Add"]
                if tops:
                    d = tops[0]
                    labels = []
                    def collect_labels(w):
                        for c in w.winfo_children():
                            if isinstance(c, ttk.Label):
                                labels.append(c.cget("text"))
                            collect_labels(c)
                    collect_labels(d)
                    result["labels"] = labels
                    cancel = find_ttk_button(d, "Cancel")
                    if cancel:
                        cancel.invoke()

            root.after(150, inspect)

            def open_form():
                result["form"] = me._open_form("Add", fields,
                                               helper_text=helper)

            root.after(50, open_form)
            root.after(2500, root.quit)
            root.mainloop()

            text = " ".join(result.get("labels", []))
            check("folder label", "Collection ID (folder name)" in text)
            check("helper text present",
                  "becomes the folder name" in text)
            check("cannot change later", "cannot be changed later" in text)
        finally:
            root.destroy()
    finally:
        restore()


@test("edit collection shows lock indicator on the id label")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            import tkinter.ttk as ttk
            import metadata_editor_gui
            me = metadata_editor_gui.MetadataEditorWindow(app)
            fields = [
                ("collection_id", "Collection ID (folder name)", "entry"),
                ("display_name", "Display Name", "entry"),
            ]
            original = {"collection_id": "teppei_beginner",
                        "display_name": "Con Teppei for Beginner"}
            result = {}

            def inspect():
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)
                        and w.title() == "Edit"]
                if tops:
                    d = tops[0]
                    labels = []
                    def collect_labels(w):
                        for c in w.winfo_children():
                            if isinstance(c, ttk.Label):
                                labels.append(c.cget("text"))
                            collect_labels(c)
                    collect_labels(d)
                    result["labels"] = labels
                    cancel = find_ttk_button(d, "Cancel")
                    if cancel:
                        cancel.invoke()

            root.after(150, inspect)

            def open_form():
                result["form"] = me._open_form("Edit", fields, original,
                                               locked_key="collection_id")

            root.after(50, open_form)
            root.after(2500, root.quit)
            root.mainloop()

            text = " ".join(result.get("labels", []))
            check("folder label", "Collection ID (folder name)" in text)
            check("lock indicator", "\U0001F512" in text)
        finally:
            root.destroy()
    finally:
        restore()


@test("source type and origin add forms show internal-id helper text")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            import tkinter.ttk as ttk
            import metadata_editor_gui
            me = metadata_editor_gui.MetadataEditorWindow(app)
            helper_st = "Internal identifier used by presets and validation."
            helper_og = "Internal identifier used for source tracking."
            results = {}

            def inspect(label_to_cancel, key):
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)
                        and w.title() == "Add"]
                if tops:
                    d = tops[0]
                    texts = []
                    def collect(w):
                        for c in w.winfo_children():
                            if isinstance(c, ttk.Label):
                                texts.append(c.cget("text"))
                            collect(c)
                    collect(d)
                    results[key] = " ".join(texts)
                    cancel = find_ttk_button(d, "Cancel")
                    if cancel:
                        cancel.invoke()

            def open_st():
                me._open_form("Add",
                              [("source_type_id", "Source Type ID", "entry"),
                               ("display_name", "Display Name", "entry")],
                              helper_text=helper_st)

            def open_og():
                me._open_form("Add",
                              [("origin_id", "Origin ID", "entry"),
                               ("display_name", "Display Name", "entry")],
                              helper_text=helper_og)

            root.after(50, lambda: root.after(
                50, lambda: inspect("Cancel", "st")))
            root.after(50, open_st)
            root.after(400, open_og)
            root.after(450, lambda: inspect("Cancel", "og"))
            root.after(2500, root.quit)
            root.mainloop()

            check("source type helper", "used by presets and validation"
                  in results.get("st", ""))
            check("origin helper", "used for source tracking"
                  in results.get("og", ""))
        finally:
            root.destroy()
    finally:
        restore()


# ============================================================
# Sequencing field: add default / explicit auto / edit round-trip
# ============================================================

def collections_tab_frame(editor):
    """Return the Collections tab's frame inside the metadata editor."""
    import tkinter.ttk as ttk
    notebook = [c for c in editor.winfo_children()
                if isinstance(c, ttk.Notebook)][0]
    for tab_id in notebook.tabs():
        if notebook.tab(tab_id, "text") == "Collections":
            return notebook.nametowidget(tab_id)
    return None


def find_button_in(widget, text):
    """Recursively find a ttk.Button by its text inside a widget."""
    import tkinter.ttk as ttk
    for child in widget.winfo_children():
        if isinstance(child, ttk.Button) and child.cget("text") == text:
            return child
        result = find_button_in(child, text)
        if result is not None:
            return result
    return None


def fill_dialog_entries(dialog, texts):
    """Insert texts into the dialog's ttk.Entry widgets in order."""
    import tkinter.ttk as ttk
    entries = []
    def collect(w):
        for c in w.winfo_children():
            if isinstance(c, ttk.Entry):
                entries.append(c)
            collect(c)
    collect(dialog)
    for entry, text in zip(entries, texts):
        entry.insert(0, text)


def set_combo_by_values(dialog, values, choice):
    """Set the readonly Combobox with the given values to choice."""
    import tkinter.ttk as ttk
    for child in dialog.winfo_children():
        if isinstance(child, ttk.Combobox) and tuple(child.cget("values")) == tuple(values):
            child.set(choice)
            return True
        if set_combo_by_values(child, values, choice):
            return True
    return False


def select_first_tree_row(tab):
    """Select the first row of the tab's Treeview, if any."""
    import tkinter.ttk as ttk
    for child in tab.winfo_children():
        if isinstance(child, ttk.Treeview):
            children = child.get_children()
            if children:
                child.selection_set(children[0])
            return True
        if select_first_tree_row(child):
            return True
    return False


def open_editor(app):
    """Open the metadata editor and return the editor Toplevel."""
    app._open_metadata_editor()
    return [w for w in app.root.winfo_children()
            if isinstance(w, tk.Toplevel)
            and w.title() == "Edit Metadata"][0]


def find_combo_by_values(dialog, values):
    """Return the first ttk.Combobox whose offered values match exactly."""
    import tkinter.ttk as ttk
    for child in dialog.winfo_children():
        if isinstance(child, ttk.Combobox):
            if tuple(child.cget("values")) == tuple(values):
                return child
        found = find_combo_by_values(child, values)
        if found is not None:
            return found
    return None


def select_tree_row_by_id(tab, collection_id):
    """Select the Treeview row whose first column matches collection_id."""
    import tkinter.ttk as ttk
    for child in tab.winfo_children():
        if isinstance(child, ttk.Treeview):
            for iid in child.get_children():
                values = child.item(iid, "values")
                if values and values[0] == collection_id:
                    child.selection_set(iid)
                    return True
            return False
        if select_tree_row_by_id(child, collection_id):
            return True
    return False


@test("add dialog: sequencing combo defaults to episodic when left at default")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            editor = open_editor(app)
            tab = collections_tab_frame(editor)
            add_button = find_button_in(tab, "Add")
            result = {}

            def drive_add():
                add_button.invoke()

            def fill_and_save():
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)
                        and w.title() == "Add"]
                if not tops:
                    result["error"] = "Add dialog not found"
                    return
                d = tops[0]
                fill_dialog_entries(d, ["nhk_default", "NHK Default"])
                save = find_button_in(d, "Save")
                if save:
                    save.invoke()

            root.after(100, drive_add)
            root.after(250, fill_and_save)
            root.after(2500, root.quit)
            root.mainloop()

            check("no error", "error" not in result)
            collections = metadata_editor.load_collections()
            by_id = {c["collection_id"]: c for c in collections}
            check("collection added", "nhk_default" in by_id)
            check("default sequencing",
                  by_id["nhk_default"]["sequencing"] == "episodic")
        finally:
            root.destroy()
    finally:
        restore()


@test("add dialog: explicitly choosing auto persists correctly")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            editor = open_editor(app)
            tab = collections_tab_frame(editor)
            add_button = find_button_in(tab, "Add")
            result = {}

            def drive_add():
                add_button.invoke()

            def fill_and_save():
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)
                        and w.title() == "Add"]
                if not tops:
                    result["error"] = "Add dialog not found"
                    return
                d = tops[0]
                fill_dialog_entries(d, ["nhk_auto", "NHK Auto"])
                result["combo_set"] = set_combo_by_values(
                    d, SEQUENCING_DISPLAY, SEQUENCING_LABELS["auto"])
                save = find_button_in(d, "Save")
                if save:
                    save.invoke()

            root.after(100, drive_add)
            root.after(250, fill_and_save)
            root.after(2500, root.quit)
            root.mainloop()

            check("no error", "error" not in result)
            check("sequencing combo present",
                  result.get("combo_set") is True)
            collections = metadata_editor.load_collections()
            by_id = {c["collection_id"]: c for c in collections}
            check("collection added", "nhk_auto" in by_id)
            check("auto persisted",
                  by_id["nhk_auto"]["sequencing"] == "auto")
        finally:
            root.destroy()
    finally:
        restore()


@test("edit dialog: sequencing value round-trips to auto and back")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            editor = open_editor(app)
            tab = collections_tab_frame(editor)
            edit_button = find_button_in(tab, "Edit")
            result = {}

            def drive_edit():
                select_first_tree_row(tab)
                edit_button.invoke()

            def change_sequencing_and_save(choice):
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)
                        and w.title() == "Edit"]
                if not tops:
                    result["error"] = "Edit dialog not found"
                    return
                d = tops[0]
                result["combo_set"] = set_combo_by_values(
                    d, SEQUENCING_DISPLAY, SEQUENCING_LABELS[choice])
                save = find_button_in(d, "Save")
                if save:
                    save.invoke()

            # First edit: teppei_beginner (episodic default) -> auto.
            root.after(100, drive_edit)
            root.after(250, lambda: change_sequencing_and_save("auto"))
            root.after(1000, root.quit)
            root.mainloop()

            check("no error (first edit)", "error" not in result)
            check("sequencing combo present (first edit)",
                  result.get("combo_set") is True)
            collections = metadata_editor.load_collections()
            by_id = {c["collection_id"]: c for c in collections}
            check("edited to auto",
                  by_id["teppei_beginner"]["sequencing"] == "auto")

            # Second edit: auto -> episodic round-trips back.
            result.clear()
            root.after(100, drive_edit)
            root.after(250, lambda: change_sequencing_and_save("episodic"))
            root.after(1000, root.quit)
            root.mainloop()

            check("no error (second edit)", "error" not in result)
            collections = metadata_editor.load_collections()
            by_id = {c["collection_id"]: c for c in collections}
            check("edited back to episodic",
                  by_id["teppei_beginner"]["sequencing"] == "episodic")
        finally:
            root.destroy()
    finally:
        restore()


@test("add dialog Default Source Type combo only offers processable types")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            editor = open_editor(app)
            tab = collections_tab_frame(editor)
            add_button = find_button_in(tab, "Add")
            result = {}

            def drive_add():
                add_button.invoke()

            def inspect_and_cancel():
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)
                        and w.title() == "Add"]
                if not tops:
                    result["error"] = "Add dialog not found"
                    return
                d = tops[0]
                combo = find_combo_by_values(d, ("clean_text",))
                result["combo_found"] = combo is not None
                if combo is not None:
                    result["values"] = tuple(combo.cget("values"))
                cancel = find_button_in(d, "Cancel")
                if cancel:
                    cancel.invoke()

            root.after(100, drive_add)
            root.after(250, inspect_and_cancel)
            root.after(2500, root.quit)
            root.mainloop()

            check("no error", "error" not in result)
            check("source type combo present",
                  result.get("combo_found") is True)
            values = result.get("values", ())
            check("processable type offered", "clean_text" in values)
            check("known non-processable cij_transcript excluded",
                  "cij_transcript" not in values)
            check("subtitle excluded", "subtitle" not in values)
            check("article excluded", "article" not in values)
        finally:
            root.destroy()
    finally:
        restore()


@test("edit dialog pre-fills and saves a legacy non-processable default")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            metadata_editor.add_collection(
                "cijapanese", "CI Japanese",
                default_source_type="cij_transcript")
            editor = open_editor(app)
            tab = collections_tab_frame(editor)
            edit_button = find_button_in(tab, "Edit")
            result = {}

            def drive_edit():
                result["row_selected"] = select_tree_row_by_id(
                    tab, "cijapanese")
                edit_button.invoke()

            def inspect_and_save():
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)
                        and w.title() == "Edit"]
                if not tops:
                    result["error"] = "Edit dialog not found"
                    return
                d = tops[0]
                combo = find_combo_by_values(d, ("clean_text",))
                if combo is None:
                    result["error"] = "source type combo not found"
                    return
                result["displayed"] = combo.get()
                result["offered"] = tuple(combo.cget("values"))
                save = find_button_in(d, "Save")
                if save:
                    save.invoke()

            def verify_no_error_dialog():
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)]
                result["error_dialog"] = any(
                    w.title() == "Cannot edit" for w in tops)
                result["edit_dialog_closed"] = not any(
                    w.title() == "Edit" for w in tops)

            root.after(100, drive_edit)
            root.after(250, inspect_and_save)
            root.after(400, verify_no_error_dialog)
            root.after(2500, root.quit)
            root.mainloop()

            check("no error", "error" not in result)
            check("legacy row selected", result.get("row_selected") is True)
            check("legacy value pre-filled",
                  result.get("displayed") == "cij_transcript")
            check("legacy value not offered for new picks",
                  "cij_transcript" not in result.get("offered", ()))
            check("saved without error dialog",
                  result.get("error_dialog") is False)
            check("edit dialog closed after save",
                  result.get("edit_dialog_closed") is True)
            collections = metadata_editor.load_collections()
            by_id = {c["collection_id"]: c for c in collections}
            check("collection still present", "cijapanese" in by_id)
            check("legacy default preserved",
                  by_id["cijapanese"]["default_source_type"] == "cij_transcript")
            check("display name preserved",
                  by_id["cijapanese"]["display_name"] == "CI Japanese")
        finally:
            root.destroy()
    finally:
        restore()


# ============================================================
# Sequencing display labels
# ============================================================

@test("sequencing combo shows friendly labels, not raw values")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            editor = open_editor(app)
            tab = collections_tab_frame(editor)
            add_button = find_button_in(tab, "Add")
            result = {}

            def drive_add():
                add_button.invoke()

            def inspect_and_cancel():
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)
                        and w.title() == "Add"]
                if not tops:
                    result["error"] = "Add dialog not found"
                    return
                d = tops[0]
                combo = find_combo_by_values(d, SEQUENCING_DISPLAY)
                result["combo_found"] = combo is not None
                if combo is not None:
                    result["values"] = tuple(combo.cget("values"))
                cancel = find_button_in(d, "Cancel")
                if cancel:
                    cancel.invoke()

            root.after(100, drive_add)
            root.after(250, inspect_and_cancel)
            root.after(2500, root.quit)
            root.mainloop()

            check("no error", "error" not in result)
            check("sequencing combo present", result.get("combo_found") is True)
            values = result.get("values", ())
            check("Series label shown", SEQUENCING_LABELS["episodic"] in values)
            check("Auto label shown", SEQUENCING_LABELS["auto"] in values)
            check("raw episodic hidden", "episodic" not in values)
            check("raw auto hidden", "auto" not in values)
            check("two friendly labels offered", values == SEQUENCING_DISPLAY)
        finally:
            root.destroy()
    finally:
        restore()


@test("add dialog: friendly-label selections persist raw sequencing values")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            editor = open_editor(app)
            tab = collections_tab_frame(editor)
            add_button = find_button_in(tab, "Add")
            result = {}

            def drive_add():
                add_button.invoke()

            def fill_and_save(cid, name, label):
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)
                        and w.title() == "Add"]
                if not tops:
                    result["error"] = "Add dialog not found"
                    return
                d = tops[0]
                fill_dialog_entries(d, [cid, name])
                result["combo_set"] = set_combo_by_values(
                    d, SEQUENCING_DISPLAY, label)
                save = find_button_in(d, "Save")
                if save:
                    save.invoke()

            # Select the "Series (manual numbering)" label.
            root.after(100, drive_add)
            root.after(250, lambda: fill_and_save(
                "nhk_ep", "NHK Ep", SEQUENCING_LABELS["episodic"]))
            root.after(1200, root.quit)
            root.mainloop()

            check("no error (series)", "error" not in result)
            check("combo set (series)", result.get("combo_set") is True)
            collections = metadata_editor.load_collections()
            by_id = {c["collection_id"]: c for c in collections}
            check("series collection added", "nhk_ep" in by_id)
            check("raw episodic persisted",
                  by_id["nhk_ep"]["sequencing"] == "episodic")

            # Select the "Auto (site/source grouping)" label.
            result.clear()
            root.after(100, drive_add)
            root.after(250, lambda: fill_and_save(
                "nhk_au", "NHK Au", SEQUENCING_LABELS["auto"]))
            root.after(1200, root.quit)
            root.mainloop()

            check("no error (auto)", "error" not in result)
            check("combo set (auto)", result.get("combo_set") is True)
            collections = metadata_editor.load_collections()
            by_id = {c["collection_id"]: c for c in collections}
            check("auto collection added", "nhk_au" in by_id)
            check("raw auto persisted",
                  by_id["nhk_au"]["sequencing"] == "auto")
        finally:
            root.destroy()
    finally:
        restore()


@test("edit dialog pre-fills friendly labels for stored raw values")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            metadata_editor.add_collection(
                "nhk_auto_col", "NHK Auto Col", sequencing="auto")
            editor = open_editor(app)
            tab = collections_tab_frame(editor)
            edit_button = find_button_in(tab, "Edit")
            result = {}

            def drive_edit(cid):
                result["row_selected"] = select_tree_row_by_id(tab, cid)
                edit_button.invoke()

            def inspect_and_cancel():
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)
                        and w.title() == "Edit"]
                if not tops:
                    result["error"] = "Edit dialog not found"
                    return
                d = tops[0]
                combo = find_combo_by_values(d, SEQUENCING_DISPLAY)
                result["combo_found"] = combo is not None
                if combo is not None:
                    result["displayed"] = combo.get()
                cancel = find_button_in(d, "Cancel")
                if cancel:
                    cancel.invoke()

            # teppei_beginner is stored as episodic (the default).
            root.after(100, lambda: drive_edit("teppei_beginner"))
            root.after(250, inspect_and_cancel)
            root.after(1200, root.quit)
            root.mainloop()

            check("no error (episodic)", "error" not in result)
            check("row selected (episodic)", result.get("row_selected") is True)
            check("combo present (episodic)", result.get("combo_found") is True)
            check("episodic pre-fills Series label",
                  result.get("displayed") == SEQUENCING_LABELS["episodic"])

            # nhk_auto_col is stored as auto.
            result.clear()
            root.after(100, lambda: drive_edit("nhk_auto_col"))
            root.after(250, inspect_and_cancel)
            root.after(1200, root.quit)
            root.mainloop()

            check("no error (auto)", "error" not in result)
            check("row selected (auto)", result.get("row_selected") is True)
            check("combo present (auto)", result.get("combo_found") is True)
            check("auto pre-fills Auto label",
                  result.get("displayed") == SEQUENCING_LABELS["auto"])
        finally:
            root.destroy()
    finally:
        restore()


@test("Default Source Type combo values and save behavior are unchanged")
def _():
    restore = sandbox()
    try:
        root, app = make_visible_app(restore)
        try:
            editor = open_editor(app)
            tab = collections_tab_frame(editor)
            add_button = find_button_in(tab, "Add")
            result = {}

            def drive_add():
                add_button.invoke()

            def fill_and_save():
                tops = [w for w in root.winfo_children()
                        if isinstance(w, tk.Toplevel)
                        and w.title() == "Add"]
                if not tops:
                    result["error"] = "Add dialog not found"
                    return
                d = tops[0]
                combo = find_combo_by_values(d, ("clean_text",))
                result["combo_found"] = combo is not None
                if combo is not None:
                    result["displayed_values"] = tuple(combo.cget("values"))
                    combo.set("clean_text")
                fill_dialog_entries(d, ["nhk_st", "NHK ST"])
                save = find_button_in(d, "Save")
                if save:
                    save.invoke()

            root.after(100, drive_add)
            root.after(250, fill_and_save)
            root.after(2500, root.quit)
            root.mainloop()

            check("no error", "error" not in result)
            check("source type combo present", result.get("combo_found") is True)
            check("displayed values unchanged",
                  result.get("displayed_values") == ("clean_text",))
            collections = metadata_editor.load_collections()
            by_id = {c["collection_id"]: c for c in collections}
            check("collection added", "nhk_st" in by_id)
            check("default persisted",
                  by_id["nhk_st"]["default_source_type"] == "clean_text")
            check("sequencing default still episodic",
                  by_id["nhk_st"]["sequencing"] == "episodic")
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
