#!/usr/bin/env python3
"""
metadata_editor_gui.py

Japanese Corpus Pipeline - Source Builder metadata editor window.

A child window opened from Source Builder -> Edit Metadata... It manages the
controlled vocabularies (Collections, Source Types, Origins) that populate
Source Builder dropdowns and Quick Presets.

This window only presents and drives metadata_editor.py; it contains no
business logic of its own.

The window opens centred over the Source Builder window using the same
child-window placement helper as other dialogs.
"""

import tkinter as tk
from tkinter import messagebox, ttk

import metadata_editor

SEQUENCING_LABELS = {
    "episodic": "Series (manual numbering)",
    "auto": "Auto (site/source grouping)",
}


def _combo_display_values(field):
    """Display values for a combo field, applying an optional label map."""
    values = list(field[3] if len(field) > 3 else [])
    label_map = field[4] if len(field) > 4 else None
    if label_map:
        return [label_map.get(v, v) for v in values]
    return values


def _display_value(field, raw):
    """Map a stored raw value to its display form for a form field."""
    label_map = field[4] if len(field) > 4 else None
    value = str(raw)
    if label_map:
        return label_map.get(value, value)
    return value


def _raw_value(field, display):
    """Map a chosen display label back to its raw value for a combo field."""
    label_map = field[4] if len(field) > 4 else None
    if label_map:
        inverse = {label: raw for raw, label in label_map.items()}
        return inverse.get(display, display)
    return display


class MetadataEditorWindow:
    """Tabs: Collections / Source Types / Origins."""

    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.window = tk.Toplevel(parent_app.root)
        self.window.title("Edit Metadata")
        self.window.transient(parent_app.root)
        import gui as source_builder_gui
        self.window.configure(bg=source_builder_gui.APP_BG)
        self.window.resizable(False, False)

        self.notebook = ttk.Notebook(self.window, padding=8)
        self.notebook.pack(fill="both", expand=True)

        self._build_collections_tab()
        self._build_source_types_tab()
        self._build_origins_tab()

        ttk.Button(self.window, text="Close",
                   command=self.window.destroy).pack(pady=(8, 8))

        # Centre over the parent only after the window is fully built so the
        # requested size is accurate.
        parent_app._center_child_over_parent(self.window)

    # ============================================================
    # Shared helpers
    # ============================================================

    def _build_tree_tab(self, title, columns, display_fn, load_fn,
                        add_fn, edit_fn, form_fields, helper_text=None):
        """Build a generic tree tab with Add / Edit actions."""
        id_key = form_fields[0][0]  # first field is the id
        frame = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(frame, text=title)

        tree = ttk.Treeview(frame, columns=[c for c, _ in columns],
                            show="headings", selectmode="browse", height=12)
        for column, heading in columns:
            tree.heading(column, text=heading)
            tree.column(column, anchor="w", width=220)
        scroll = ttk.Scrollbar(frame, orient="vertical",
                               command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        actions = ttk.Frame(frame)
        actions.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(actions, text="Add",
                   command=lambda: self._add_action(
                       tree, load_fn, add_fn, form_fields,
                       display_fn, helper_text)).pack(side="left")
        ttk.Button(actions, text="Edit",
                   command=lambda: self._edit_action(
                       tree, load_fn, edit_fn, form_fields,
                       display_fn, id_key, helper_text)).pack(
            side="left", padx=(8, 0))

        self._reload_tree(tree, load_fn, display_fn)
        return frame, tree

    def _reload_tree(self, tree, load_fn, display_fn):
        tree.delete(*tree.get_children())
        for item in load_fn():
            tree.insert("", "end", values=display_fn(item))

    def _selected_index(self, tree, load_fn):
        selection = tree.selection()
        if not selection:
            messagebox.showinfo("No selection",
                                "Select an item in the list first.",
                                parent=self.window)
            return None
        row = tree.index(selection[0])
        return row

    # ============================================================
    # Add / Edit actions
    # ============================================================

    def _add_action(self, tree, load_fn, add_fn, form_fields, display_fn,
                    helper_text=None):
        result = self._open_form("Add", form_fields, helper_text=helper_text)
        if result is None:
            return
        try:
            add_fn(**result)
        except metadata_editor.MetadataError as exc:
            messagebox.showerror("Cannot add", str(exc), parent=self.window)
            return
        self._reload_tree(tree, load_fn, display_fn)
        self.parent_app._refresh_metadata()

    def _edit_action(self, tree, load_fn, edit_fn, form_fields, display_fn,
                     id_key, helper_text=None):
        row = self._selected_index(tree, load_fn)
        if row is None:
            return
        items = load_fn()
        original = items[row]
        result = self._open_form("Edit", form_fields, original,
                                 locked_key=id_key, helper_text=helper_text)
        if result is None:
            return
        try:
            edit_fn(original[id_key], **result)
        except metadata_editor.MetadataError as exc:
            messagebox.showerror("Cannot edit", str(exc), parent=self.window)
            return
        self._reload_tree(tree, load_fn, display_fn)
        self.parent_app._refresh_metadata()

    # ============================================================
    # Form dialog
    # ============================================================

    def _open_form(self, title, fields, original=None, locked_key=None,
                   helper_text=None):
        """
        Open a small form dialog for the given fields.

        fields: list of (key, label, kind) where kind is "entry" or "combo"
        plus an optional "values" key for combos and an optional "labels"
        dict mapping each raw value to a friendly display label (combos only).
        When labels are present the combo shows the friendly labels and the
        raw value is passed back on save, unchanged.
        locked_key (str|None): when editing, this identifier field is shown
        read-only (with a lock indicator) and is not returned, keeping it
        immutable after creation.
        helper_text (str|None): explanatory text shown at the bottom of the
        dialog.
        Returns a dict {key: value} or None on cancel.
        """
        dialog = tk.Toplevel(self.parent_app.root)
        dialog.title(title)
        dialog.transient(self.parent_app.root)
        dialog.resizable(False, False)
        dialog.minsize(360, 180)

        variables = {}
        widgets = {}
        labels = {}
        field_by_key = {field[0]: field for field in fields}
        body = ttk.Frame(dialog, padding=12)
        body.grid(row=0, column=0, sticky="nsew")

        combos = {}
        for row, field in enumerate(fields):
            key, label, kind = field[0], field[1], field[2]
            if original is not None and locked_key == key:
                label = f"{label} 🔒"
            label_widget = ttk.Label(body, text=label)
            label_widget.grid(row=row, column=0, sticky="w", pady=2)
            labels[key] = label_widget
            if kind == "combo":
                var = tk.StringVar()
                combo = ttk.Combobox(body, textvariable=var,
                                     values=_combo_display_values(field),
                                     state="readonly", width=28)
                combo.grid(row=row, column=1, sticky="w", pady=2)
                variables[key] = var
                widgets[key] = combo
                combos[key] = combo
            else:
                var = tk.StringVar()
                entry = ttk.Entry(body, textvariable=var, width=30)
                entry.grid(row=row, column=1, sticky="w", pady=2)
                variables[key] = var
                widgets[key] = entry

        # Pre-fill for edit.
        if original is not None:
            for key, var in variables.items():
                if key in original and original[key]:
                    var.set(_display_value(field_by_key[key], original[key]))
            # Lock the identifier field so it cannot be changed after creation.
            if locked_key and locked_key in widgets:
                widgets[locked_key].configure(state="readonly")

        row = len(fields)
        if helper_text:
            ttk.Label(body, text=helper_text, foreground="#5a6a7a",
                      wraplength=340, justify="left").grid(
                row=row, column=0, columnspan=2, sticky="w", pady=(6, 0))
            row += 1

        buttons = ttk.Frame(body)
        buttons.grid(row=row, column=0, columnspan=2, sticky="e",
                     pady=(12, 0))
        result = {"cancelled": True}
        ttk.Button(buttons, text="Cancel",
                   command=dialog.destroy).pack(side="left", padx=4)
        ttk.Button(buttons, text="Save",
                   command=lambda: self._form_save(dialog, variables,
                                                   result)).pack(
            side="left", padx=4)

        parent_app = self.parent_app
        parent_app._center_child_over_parent(dialog)
        dialog.grab_set()
        parent_app.root.wait_window(dialog)
        if result["cancelled"]:
            return None
        values = {key: var.get() for key, var in variables.items()}
        for key, var in variables.items():
            field = field_by_key.get(key)
            if (field and field[2] == "combo"
                    and len(field) > 4 and field[4]):
                values[key] = _raw_value(field, values[key])
        if original is not None and locked_key:
            # The immutable identifier is never part of an edit payload.
            values.pop(locked_key, None)
        return values

    def _form_save(self, dialog, variables, result):
        result["cancelled"] = False
        dialog.destroy()

    # ============================================================
    # Tab builders
    # ============================================================

    def _build_collections_tab(self):
        source_types = [s["source_type_id"]
                        for s in metadata_editor.load_source_types()]
        processable_source_types = [
            s for s in source_types if metadata_editor.is_processable(s)]

        def display(item):
            return (item["collection_id"], item["display_name"],
                    item.get("default_source_type") or "")

        def add(**kw):
            return metadata_editor.add_collection(
                kw["collection_id"], kw["display_name"],
                default_source_type=kw.get("default_source_type") or None,
                source_type_ids=source_types,
                sequencing=kw.get("sequencing") or None)

        def edit(original_id, **kw):
            return metadata_editor.edit_collection(
                original_id, kw["display_name"],
                default_source_type=kw.get("default_source_type") or None,
                source_type_ids=source_types,
                sequencing=kw.get("sequencing") or None)

        fields = [
            ("collection_id", "Collection ID (folder name)", "entry"),
            ("display_name", "Display Name", "entry"),
            ("default_source_type", "Default Source Type", "combo",
             processable_source_types),
            ("sequencing", "Sequencing", "combo",
             metadata_editor.SEQUENCING_VALUES, SEQUENCING_LABELS),
        ]
        helper = ("The Collection ID becomes the folder name and filename "
                  "prefix. Choose carefully. It cannot be changed later.")
        self._build_tree_tab(
            "Collections",
            [("col_id", "Collection ID"), ("display_name", "Display Name"),
             ("default", "Default Source Type")],
            display, metadata_editor.load_collections, add, edit, fields,
            helper_text=helper)

    def _build_source_types_tab(self):
        def display(item):
            return (item["source_type_id"], item["display_name"])

        def add(**kw):
            return metadata_editor.add_source_type(kw["source_type_id"],
                                                   kw["display_name"])

        def edit(original_id, **kw):
            return metadata_editor.edit_source_type(
                original_id, kw["display_name"])

        fields = [
            ("source_type_id", "Source Type ID", "entry"),
            ("display_name", "Display Name", "entry"),
        ]
        helper = "Internal identifier used by presets and validation."
        self._build_tree_tab(
            "Source Types",
            [("col_id", "Source Type ID"), ("display_name", "Display Name")],
            display, metadata_editor.load_source_types, add, edit, fields,
            helper_text=helper)

    def _build_origins_tab(self):
        def display(item):
            return (item["origin_id"], item["display_name"])

        def add(**kw):
            return metadata_editor.add_origin(kw["origin_id"],
                                              kw["display_name"])

        def edit(original_id, **kw):
            return metadata_editor.edit_origin(
                original_id, kw["display_name"])

        fields = [
            ("origin_id", "Origin ID", "entry"),
            ("display_name", "Display Name", "entry"),
        ]
        helper = "Internal identifier used for source tracking."
        self._build_tree_tab(
            "Origins",
            [("col_id", "Origin ID"), ("display_name", "Display Name")],
            display, metadata_editor.load_origins, add, edit, fields,
            helper_text=helper)
