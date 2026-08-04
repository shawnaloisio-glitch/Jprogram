#!/usr/bin/env python3
"""
analysis_tab_gui.py

Japanese Corpus Pipeline - Analysis tab window.

A minimal user-facing report surface:
- list available completed corpora (human labels only),
- Run Analysis for a selected corpus (reuses the existing analysis workflow
  used by the Processing tab; no duplicated logic),
- Open Reports (opens the existing Analysis outputs folder).

This window exposes no source_ids, paths, JSON names, artifact names, or
internal folders.
"""

import os
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import processing_tab
import gui as source_builder_gui
import paths


class AnalysisTabWindow:
    """Completed-corpus list + Run Analysis + Open Reports."""

    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.window = tk.Toplevel(parent_app.root)
        self.window.title("Analysis")
        self.window.transient(parent_app.root)
        self.window.configure(bg=source_builder_gui.APP_BG)
        self.window.geometry("560x360")
        self.window.minsize(460, 280)

        self.rows = []  # {label, source_id, package}
        self._build_widgets()
        parent_app._center_child_over_parent(self.window)
        self.refresh()

    def _build_widgets(self):
        main = ttk.Frame(self.window, padding=10)
        main.grid(row=0, column=0, sticky="nsew")
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)

        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Completed Corpora").pack(side="left")
        ttk.Button(header, text="Refresh",
                   command=self.refresh).pack(side="right")
        ttk.Separator(main, orient="horizontal").grid(
            row=1, column=0, sticky="ew", pady=6)

        self.tree = ttk.Treeview(main, columns=("label",),
                                 show="headings", selectmode="browse",
                                 height=10)
        self.tree.heading("label", text="Source")
        self.tree.column("label", anchor="w", width=400)
        scroll = ttk.Scrollbar(main, orient="vertical",
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=2, column=0, sticky="nsew")
        scroll.grid(row=2, column=1, sticky="ns")
        main.rowconfigure(2, weight=1)

        self.status_var = tk.StringVar(value="")
        ttk.Label(main, textvariable=self.status_var).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

        actions = ttk.Frame(main)
        actions.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.run_button = ttk.Button(actions, text="Run Analysis",
                                     command=self._on_run)
        self.run_button.pack(side="left")
        self.open_button = ttk.Button(actions, text="Open Reports",
                                      command=self._on_open_reports)
        self.open_button.pack(side="left", padx=(8, 0))

        ttk.Button(main, text="Close",
                   command=self.window.destroy).grid(
            row=5, column=0, columnspan=2, sticky="e", pady=(8, 0))

    def refresh(self):
        """Reload the completed-corpus list from packages."""
        self.tree.delete(*self.tree.get_children())
        self.rows = []
        for package in processing_tab.completed_corpora():
            label = processing_tab.human_label(package)
            self.rows.append({
                "label": label,
                "source_id": package.get("source_id", ""),
                "package": package,
            })
            self.tree.insert("", "end", iid=package.get("source_id", ""),
                             values=(label,))

    def _selected_row(self):
        selection = self.tree.selection()
        if not selection:
            return None
        source_id = selection[0]
        for row in self.rows:
            if row["source_id"] == source_id:
                return row
        return None

    def _on_run(self):
        """Run the existing analysis workflow for the selected corpus."""
        row = self._selected_row()
        if row is None:
            messagebox.showinfo("No selection",
                                "Select a completed corpus first.",
                                parent=self.window)
            return
        self.status_var.set("Running analysis…")
        self.run_button.configure(state="disabled")
        try:
            self.parent_app.root.update_idletasks()
            analysis = processing_tab.run_analysis(row["package"])
            self.status_var.set(
                f"Analysis complete: {analysis['output_path']}")
            self.run_button.configure(state="normal")
            messagebox.showinfo(
                "Analysis complete",
                f"Analysis complete for {row['label']}.",
                parent=self.window)
        except processing_tab.ProcessingTabError as exc:
            self.status_var.set("Analysis could not be completed")
            self.run_button.configure(state="normal")
            messagebox.showerror(
                "Analysis could not be completed",
                f"Analysis could not be completed for {row['label']}.",
                parent=self.window)
        except Exception:
            self.status_var.set("Analysis could not be completed")
            self.run_button.configure(state="normal")
            messagebox.showerror(
                "Analysis could not be completed",
                f"Analysis could not be completed for {row['label']}.",
                parent=self.window)

    def _on_open_reports(self):
        """Open the existing Analysis outputs folder."""
        outputs_dir = paths.ANALYSIS_OUTPUTS
        outputs_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(outputs_dir))
        except OSError as exc:
            messagebox.showerror("Cannot open reports",
                                 str(exc), parent=self.window)
