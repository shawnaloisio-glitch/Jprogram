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

Only the Sources tab is now visible. Processing UI access was intentionally
removed: its original purpose was reviewing/selecting/batching sources to time
processing runs around DeepSeek's discount off-peak API pricing, which is gone
now that the parser is the deterministic local/free GiNZA parser (no API,
nothing to time). The underlying capability (_open_processing()) is
deliberately retained, not deleted, in case it is wanted again later.

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
    Main application window (Sources tab; see module docstring for the
    retired Processing tab's status).
    """

    TAB_SOURCES = "Sources"

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

    def _build_sources_tab(self):
        frame = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(frame, text=self.TAB_SOURCES)

        # Embed the existing Source Builder interface directly in the tab.
        # Reuses the existing GUI; no duplicate source-creation workflow.
        self.source_builder = source_builder_gui.SourceBuilderApp(frame)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

    # ============================================================
    # Tab actions (adapters to existing functionality)
    # ============================================================

    # Intentionally retained, though currently unreachable from the UI: no tab
    # or button calls this as of this change (the Processing tab and the Source
    # Builder "Processing" button were removed — the batching rationale is gone
    # now that the parser is the deterministic local GiNZA parser). Kept in
    # case the Processing window is wanted again later. The
    # "tests/test_app_shell.py" "open processing instantiates the existing
    # processing window" test calls this method directly and must keep passing
    # unchanged.
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
