#!/usr/bin/env python3
"""
gui.py

Japanese Corpus Pipeline - Subtitle Importer GUI (Tkinter/ttk).

Window, widgets, and user interaction only. All logic lives in cleaner.py.

V1 scope: select a subtitle file (.srt/.vtt), preview the cleaned text, and
save the clean text to Intake\\<original_stem>.txt.
"""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# Allow imports from the Subtitle Importer package.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cleaner


class SubtitleImporterApp:
    """Main Subtitle Importer window."""

    def __init__(self, root):
        self.root = root
        root.title("Subtitle Importer")

        self.selected_path = None
        self.preview_text = ""

        self.file_var = tk.StringVar(value="")
        self.output_var = tk.StringVar(value="")
        self.preview_var = tk.StringVar(value="")

        self._build_widgets()

    def _build_widgets(self):
        main = ttk.Frame(self.root, padding=12)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        ttk.Label(main, text="Subtitle Importer").grid(
            row=0, column=0, columnspan=3, sticky="w")

        row = 1
        ttk.Label(main, text="Input File:").grid(row=row, column=0, sticky="w")
        self.select_button = ttk.Button(
            main, text="Select Subtitle File", command=self._select_file)
        self.select_button.grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Label(main, text="Selected File:").grid(
            row=row, column=0, sticky="w")
        ttk.Label(main, textvariable=self.file_var).grid(
            row=row, column=1, columnspan=2, sticky="w")
        row += 1

        ttk.Separator(main, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=6)
        row += 1

        ttk.Label(main, text="Preview:").grid(row=row, column=0, sticky="w")
        row += 1
        self.preview_area = tk.Text(main, height=14, width=70, wrap="word")
        self.preview_area.grid(row=row, column=0, columnspan=3, sticky="nsew")
        self.preview_area.configure(state="disabled")
        row += 1

        ttk.Separator(main, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=6)
        row += 1

        ttk.Label(main, text="Output:").grid(row=row, column=0, sticky="w")
        ttk.Label(main, textvariable=self.output_var).grid(
            row=row, column=1, columnspan=2, sticky="w")
        row += 1

        self.clean_button = ttk.Button(
            main, text="Clean Preview", command=self._clean_preview)
        self.clean_button.grid(row=row, column=0, sticky="w", pady=(8, 0))
        self.save_button = ttk.Button(
            main, text="Save Clean Text", command=self._save_clean_text,
            state="disabled")
        self.save_button.grid(row=row, column=1, sticky="w", pady=(8, 0))
        row += 1

        main.columnconfigure(2, weight=1)
        main.rowconfigure(4, weight=1)

    def _select_file(self):
        path = filedialog.askopenfilename(
            parent=self.root, title="Select Subtitle File",
            filetypes=[("Subtitle files", "*.srt *.vtt"),
                       ("All files", "*.*")])
        if not path:
            return
        self.selected_path = Path(path)
        self.file_var.set(str(self.selected_path))
        self._reset_preview()

    def _reset_preview(self):
        self.preview_text = ""
        self._set_preview("")
        self.output_var.set("")
        self.save_button.configure(state="disabled")

    def _set_preview(self, text):
        self.preview_area.configure(state="normal")
        self.preview_area.delete("1.0", "end")
        self.preview_area.insert("1.0", text)
        self.preview_area.configure(state="disabled")

    def _clean_preview(self):
        if self.selected_path is None:
            messagebox.showinfo("No file", "Select a subtitle file first.",
                                parent=self.root)
            return
        try:
            fmt, cleaned = cleaner.clean_file(self.selected_path)
        except cleaner.CleanError as exc:
            messagebox.showerror("Cannot clean", str(exc), parent=self.root)
            return
        self.preview_text = cleaned
        self._set_preview(cleaned)
        self.output_var.set(str(cleaner.output_path(self.selected_path)))
        self.save_button.configure(state="normal")

    def _save_clean_text(self):
        if not self.preview_text:
            return
        try:
            target = cleaner.save_clean_text(self.selected_path,
                                             self.preview_text)
        except cleaner.CleanError as exc:
            messagebox.showerror("Cannot save", str(exc), parent=self.root)
            return
        self.output_var.set(str(target))
        messagebox.showinfo("Saved",
                            f"Clean text saved:\n\n{target}",
                            parent=self.root)


def main():
    root = tk.Tk()
    SubtitleImporterApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
