#!/usr/bin/env python3
"""
app.py

Japanese Corpus Pipeline - application shell (single user entry point).

Hosts the existing tools behind a tab container so the user does not need to
know separate launch points. This is a container foundation only: it does NOT
move, redesign, or duplicate any existing functionality. All existing launch
paths are preserved (Source Builder launcher, Production Manager CLI, etc.).

Tabs:
- Sources      -> embedded Source Builder.
- Processing   -> opens the existing Processing window.

This shell contains no pipeline logic and no artifact handling.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Source Builder"))
sys.path.insert(0, str(PROJECT_ROOT / "Production Manager"))

import tkinter as tk
from tkinter import ttk

import gui as source_builder_gui
import paths


class ApplicationShell:
    """
    Main application window with the Sources / Processing tabs.
    """

    TAB_SOURCES = "Sources"
    TAB_PROCESSING = "Processing"

    def __init__(self, root):
        self.root = root
        root.title("Japanese Corpus Pipeline")

        # Explicitly initialize the customer/runtime workspace before any
        # component that depends on workspace folders is built.
        paths.ensure_workspace()

        self._build_widgets()

    # ============================================================
    # Widgets
    # ============================================================

    def _build_widgets(self):
        root_bg = source_builder_gui.APP_BG
        if self.root.winfo_class() == "Tk":
            self.root.configure(bg=root_bg)
        style = ttk.Style()
        style.configure("TFrame", background=root_bg)
        style.configure("TNotebook", background=root_bg)
        main = ttk.Frame(self.root, padding=8)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(main)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        self._build_sources_tab()
        self._build_processing_tab()

    def _build_sources_tab(self):
        frame = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(frame, text=self.TAB_SOURCES)

        # Embed the existing Source Builder interface directly in the tab.
        # Reuses the existing GUI; no duplicate source-creation workflow.
        self.source_builder = source_builder_gui.SourceBuilderApp(frame)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

    def _build_processing_tab(self):
        frame = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(frame, text=self.TAB_PROCESSING)

        ttk.Label(frame, text="Processing",
                  font=("TkDefaultFont", 14, "bold")).pack(anchor="w")
        ttk.Label(
            frame, wraplength=460, justify="left",
            text=("Select sources and process them through to a finished "
                  "corpus.")
        ).pack(anchor="w", pady=(6, 12))

        ttk.Button(frame, text="Open Processing",
                   command=self._open_processing).pack(anchor="w")

    # ============================================================
    # Tab actions (adapters to existing functionality)
    # ============================================================

    def _open_processing(self):
        """Open the existing Processing window."""
        import processing_tab_gui
        processing_tab_gui.ProcessingTabWindow(self)

    # ============================================================
    # Child-window placement helper (used by Processing window)
    # ============================================================

    def _center_child_over_parent(self, child):
        """Position a child window centred over the shell window."""
        self.root.update_idletasks()
        x, y = source_builder_gui.centered_position(
            self.root.winfo_rootx(), self.root.winfo_rooty(),
            self.root.winfo_width(), self.root.winfo_height(),
            child.winfo_reqwidth(), child.winfo_reqheight())
        child.geometry(f"+{x}+{y}")


def main():
    root = tk.Tk()
    ApplicationShell(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
