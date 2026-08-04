#!/usr/bin/env python3
"""
processing_tab_gui.py

Japanese Corpus Pipeline - Processing tab window.

A child window opened from Source Builder. It lists source packages with
human labels and drives the existing pipeline through the Production Manager
functions (sequential, no parallelism). It never exposes source_ids, artifact
paths, JSON files, folders, or individual pipeline stages to the user.

Actions:
- [ Process Selected ] - run the pipeline for the selected sources.
- [ Retry Failed ] - run sources whose status is Failed.
- [ Export Diagnostics ] - write a diagnostic bundle to Diagnostics\\.

The window opens centred over the Source Builder window using the same
child-window placement helper as other dialogs.
"""

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import diagnostics
import processing_tab
import gui as source_builder_gui


class ProcessingTabWindow:
    """Source list + status + actions for the existing pipeline."""

    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.window = tk.Toplevel(parent_app.root)
        self.window.title("Processing")
        self.window.transient(parent_app.root)
        self.window.configure(bg=source_builder_gui.APP_BG)
        self.window.geometry("640x420")
        self.window.minsize(520, 320)

        self.rows = []  # list of dicts {label, source_id, package, var, status_var}
        self._busy = False

        self._build_widgets()
        parent_app._center_child_over_parent(self.window)
        self.refresh()

    # ============================================================
    # Widgets
    # ============================================================

    def _build_widgets(self):
        main = ttk.Frame(self.window, padding=10)
        main.grid(row=0, column=0, sticky="nsew")
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)

        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Sources").pack(side="left")
        self.refresh_button = ttk.Button(header, text="Refresh",
                                         command=self.refresh)
        self.refresh_button.pack(side="right")
        ttk.Separator(main, orient="horizontal").grid(
            row=1, column=0, sticky="ew", pady=6)

        # Source list (columns: check, label, status).
        columns = ("check", "label", "status")
        self.tree = ttk.Treeview(main, columns=columns, show="headings",
                                 selectmode="extended", height=12)
        self.tree.heading("check", text="✓")
        self.tree.heading("label", text="Source")
        self.tree.heading("status", text="Status")
        self.tree.column("check", anchor="center", width=34, stretch=False)
        self.tree.column("label", anchor="w", width=360)
        self.tree.column("status", anchor="w", width=140)
        scroll = ttk.Scrollbar(main, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=2, column=0, sticky="nsew")
        scroll.grid(row=2, column=1, sticky="ns")
        main.rowconfigure(2, weight=1)
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        self.error_label = ttk.Label(main, text="", foreground="#c62828")
        self.error_label.grid(row=3, column=0, columnspan=2, sticky="w",
                              pady=(4, 0))

        actions = ttk.Frame(main)
        actions.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.process_button = ttk.Button(
            actions, text="Process Selected", command=self._on_process_selected)
        self.process_button.pack(side="left")
        self.retry_button = ttk.Button(
            actions, text="Retry Failed", command=self._on_retry_failed)
        self.retry_button.pack(side="left", padx=(8, 0))
        self.analysis_button = ttk.Button(
            actions, text="Run Analysis", command=self._on_run_analysis)
        self.analysis_button.pack(side="left", padx=(8, 0))
        self.dump_button = ttk.Button(
            actions, text="Export Diagnostics",
            command=self._on_dump)
        self.dump_button.pack(side="right")

        self.progress_var = tk.StringVar(value="")
        ttk.Label(main, textvariable=self.progress_var).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

        ttk.Button(main, text="Close",
                   command=self.window.destroy).grid(
            row=6, column=0, columnspan=2, sticky="e", pady=(8, 0))

    # ============================================================
    # Source list
    # ============================================================

    def refresh(self):
        """Reload the source list from disk packages."""
        self.tree.delete(*self.tree.get_children())
        self.rows = []
        packages = processing_tab.discover_packages()
        for package in packages:
            row = processing_tab.package_to_row(package)
            label, failed_message = processing_tab.simple_status(package)
            row["status"] = label
            row["failed_message"] = failed_message
            row["var"] = tk.BooleanVar(value=False)
            self.rows.append(row)
            self.tree.insert("", "end", iid=row["source_id"],
                             values=(" ", row["label"], label))
        self._reset_busy()

    # ============================================================
    # Selection helpers
    # ============================================================

    def _on_tree_click(self, event):
        """Toggle a row in the selection when the check column is clicked."""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        column = self.tree.identify_column(event.x)
        if column != "#1":  # the check column
            return
        item = self.tree.identify_row(event.y)
        if not item or not self.tree.exists(item):
            return
        if item in self.tree.selection():
            self.tree.selection_remove(item)
        else:
            self.tree.selection_add(item)
        return "break"

    def _on_tree_select(self, _event=None):
        """Keep the checkbox column and var in sync with the selection."""
        selected = set(self.tree.selection())
        for row in self.rows:
            checked = row["source_id"] in selected
            row["var"].set(checked)
            if self.tree.exists(row["source_id"]):
                self.tree.set(row["source_id"], "check",
                              "✓" if checked else " ")

    def _selected_rows(self):
        selected = set(self.tree.selection())
        return [row for row in self.rows if row["source_id"] in selected]

    def _row_by_source_id(self, source_id):
        for row in self.rows:
            if row["source_id"] == source_id:
                return row
        return None

    def _set_row_status(self, source_id, label, failed_message=""):
        row = self._row_by_source_id(source_id)
        if row is None:
            return
        row["status"] = label
        row["failed_message"] = failed_message
        if self.tree.exists(source_id):
            check = "✓" if row["var"].get() else " "
            self.tree.item(source_id, values=(check, row["label"], label))

    # ============================================================
    # Actions
    # ============================================================

    def _on_process_selected(self):
        if self._busy:
            return
        rows = self._selected_rows()
        if not rows:
            messagebox.showinfo("No selection",
                                "Select one or more sources first.",
                                parent=self.window)
            return
        self._run_sources(rows)

    def _on_retry_failed(self):
        if self._busy:
            return
        failed = [row for row in self.rows if row["status"]
                  == processing_tab.STATUS_FAILED]
        if not failed:
            messagebox.showinfo("Nothing to retry",
                                "No failed sources to retry.",
                                parent=self.window)
            return
        self._run_sources(failed)

    def _run_sources(self, rows):
        """Run the pipeline sequentially for the given rows."""
        self._set_busy(True)
        packages = [row["package"] for row in rows]

        def worker():
            try:
                results = processing_tab.process_sources(packages)
                self.window.after(0, lambda: self._apply_results(results))
            except Exception as exc:
                self.window.after(
                    0, lambda: self._show_run_error(str(exc)))
            finally:
                self.window.after(0, self._reset_busy)

        threading.Thread(target=worker, daemon=True).start()

    def _apply_results(self, results):
        for result in results:
            state_info = {"state": result.get("state")}
            label, failed_message = processing_tab.simple_status(
                {}, state_info)
            self._set_row_status(result["source_id"], label, failed_message)
        self._reset_busy()

    def _show_run_error(self, message):
        self.error_label.configure(text=message)
        self._reset_busy()

    def _on_run_analysis(self):
        if self._busy:
            return
        rows = self._selected_rows()
        if not rows:
            messagebox.showinfo("No selection",
                                "Select one or more sources first.",
                                parent=self.window)
            return
        results = []
        for row in rows:
            try:
                analysis = processing_tab.run_analysis(row["package"])
                results.append(f"{row['label']}:\n  {analysis['output_path']}")
            except processing_tab.ProcessingTabError as exc:
                results.append(f"{row['label']}:\n  {exc}")
        messagebox.showinfo("Analysis",
                            "\n\n".join(results), parent=self.window)

    def _on_dump(self):
        if self._busy:
            return
        rows = self._selected_rows() or self.rows
        source_ids = [row["source_id"] for row in rows]
        packages = [row["package"] for row in rows]
        try:
            dump = diagnostics.build_dump(source_ids, packages)
            target = diagnostics.write_dump(dump, label="sources")
        except Exception as exc:
            messagebox.showerror("Dump failed", str(exc), parent=self.window)
            return
        self.progress_var.set(f"Troubleshooting data saved to:\n{target}")
        messagebox.showinfo("Troubleshooting data",
                            f"Saved to:\n{target}\n\nSend this file to "
                            f"OC/AI for diagnosis.", parent=self.window)

    # ============================================================
    # Busy state
    # ============================================================

    def _set_busy(self, busy):
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.process_button.configure(state=state)
        self.retry_button.configure(state=state)
        self.dump_button.configure(state=state)
        self.refresh_button.configure(state=state)
        self.progress_var.set("Processing selected sources…" if busy else "")

    def _reset_busy(self):
        self._busy = False
        self.process_button.configure(state="normal")
        self.retry_button.configure(state="normal")
        self.dump_button.configure(state="normal")
        self.refresh_button.configure(state="normal")
