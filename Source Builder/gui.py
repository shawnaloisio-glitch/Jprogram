#!/usr/bin/env python3
"""
gui.py

Japanese Corpus Pipeline - Source Builder GUI (Tkinter/ttk).

Window, widgets, and user interaction only. All logic lives in controller.py,
config_loader.py, gui_settings.py, and quick_presets.py.

Guided Workflow: the Ready State Engine determines workflow state; the
Workflow Panel communicates it; the GUI prevents incomplete canonical source
creation. Workflow efficiency has priority over visual polish.
"""

import os
import sys
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# Allow imports from the project root and the Source Builder package.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import controller
import config_loader
import gui_settings
import import_material
import metadata_editor_gui
import paths
import processing_tab_gui
import quick_presets
import recent_sources
import source_package

# Human-friendly labels for the dynamic "Add Another ..." button text.
# Only source types still present in Config/source_types.json are listed.
SOURCE_TYPE_LABELS = {
    "clean_text": "Clean Text",
}


def _processable_source_types(source_types):
    """Return only source types that have an active processing profile.

    Filters the Config vocabulary to the subset the pipeline can actually
    process, so the GUI never offers a source type that cannot be handed off.
    """
    return [st for st in source_types
            if source_package.is_processable_source_type(st)]

# Solid filled button colours.
COLOR_GREY = "#9e9e9e"       # disabled / unavailable
COLOR_GREEN = "#2e7d32"      # action available
COLOR_BLUE = "#1565c0"       # saved / current saved state
COLOR_ADMIN = "#546e7a"      # administrative
COLOR_WHITE = "#ffffff"

# Main application background: the default neutral grey with a very subtle
# blue hue (barely noticeable, keeps the app feeling professional).
APP_BG = "#eef0f4"

# Workflow Panel emphasis colours.
PANEL_BG = "#eef2f7"
PANEL_TITLE_FG = "#0d2b45"
PANEL_CAPTION_FG = "#5a6a7a"
PANEL_MESSAGE_FG = "#0d2b45"

COMBOBOX_WIDTH = 38
PRESET_BUTTON_WIDTH = 16


def ready_state_visuals(state):
    """
    Map a Ready State to button visuals (pure, testable).

    Input: one of "INCOMPLETE" / "READY" / "SAVED" / "ERROR".
    Output: dict:
        {
            "save_bg": str,
            "save_enabled": bool,
            "next_bg": str,
            "next_enabled": bool,
        }

    Colour semantics: green = action available; blue = already saved/current
    saved state; grey = unavailable.
    """
    if state == "READY":
        return {
            "save_bg": COLOR_GREEN,
            "save_enabled": True,
            "next_bg": COLOR_GREY,
            "next_enabled": False,
        }
    if state == "SAVED":
        return {
            "save_bg": COLOR_BLUE,
            "save_enabled": False,
            "next_bg": COLOR_GREEN,
            "next_enabled": True,
        }
    # INCOMPLETE / ERROR
    return {
        "save_bg": COLOR_GREY,
        "save_enabled": False,
        "next_bg": COLOR_GREY,
        "next_enabled": False,
    }


def workflow_panel_blocks(status_message, filename, save_path):
    """
    Compose the Workflow Panel blocks in display order (pure, testable).

    Output: list of dicts:
        [
            {"kind": "message", "text": str},     # primary information
            {"kind": "caption", "text": "Filename"},
            {"kind": "value",    "text": str},    # secondary reference
            {"kind": "caption",  "text": "Save Location"},
            {"kind": "value",    "text": str},    # secondary reference
        ]
    """
    blocks = [{"kind": "message", "text": status_message}]
    for caption, value in (("Filename", filename),
                           ("Save Location", save_path)):
        blocks.append({"kind": "caption", "text": caption})
        blocks.append({"kind": "value", "text": value or "—"})
    return blocks


def centered_position(parent_x, parent_y, parent_w, parent_h, child_w,
                      child_h):
    """
    Compute a position that centers a child window over its parent (pure,
    testable).

    Input:
        parent_x (int), parent_y (int) - parent's top-left screen position,
        parent_w (int), parent_h (int) - parent's size in pixels,
        child_w (int), child_h (int) - child's requested size in pixels.

    Output: (x, y) top-left position for the child so that the child's
    centre aligns with the parent's centre. Coordinates are on the same
    virtual desktop (monitor) as the parent; they may be negative on a
    multi-monitor setup where the parent sits left/above the primary display.
    """
    x = parent_x + (parent_w - child_w) // 2
    y = parent_y + (parent_h - child_h) // 2
    return x, y


def next_load_file_candidate(directory, last_loaded=None):
    """
    Return the next Intake text file to highlight in the Load File picker.

    Files are listed alphabetically. If a previous file is given and still
    exists, the next file after it (alphabetically) is suggested; otherwise
    the first available file is suggested. When there is no next file (or no
    files at all), returns None so the picker behaves normally.

    Input: directory (Path), last_loaded (Path|None).
    Output: Path | None.
    """
    if directory is None:
        return None
    directory = Path(directory)
    if not directory.is_dir():
        return None
    files = sorted(p for p in directory.iterdir()
                   if p.is_file() and p.suffix.lower() == ".txt")
    if not files:
        return None
    if last_loaded is not None:
        try:
            index = files.index(Path(last_loaded))
        except ValueError:
            # Previous file no longer present: fall back to the first file.
            return files[0]
        if index < len(files) - 1:
            return files[index + 1]
        return None
    return files[0]


class SourceBuilderApp:
    """Main Source Builder window (collection + standalone workflow)."""

    def __init__(self, root):
        self.root = root
        if hasattr(root, "title"):
            root.title("Source Builder")

        self.source_type_var = tk.StringVar()
        self._load_config()

        self.identity_var = tk.StringVar(value="collection")
        self.collection_var = tk.StringVar()
        self.source_name_var = tk.StringVar()
        self.creator_var = tk.StringVar()
        self.creator_display_var = tk.StringVar()
        self.material_level_var = tk.StringVar()
        self.style_id_var = tk.StringVar()
        self.topic_id_var = tk.StringVar()
        self.duration_var = tk.StringVar()
        # Display-only vars bound to the new combos; they hold the friendly
        # display names while material_level_var/style_id_var keep the raw ids.
        self.material_level_display_var = tk.StringVar()
        self.style_display_var = tk.StringVar()
        self.topic_display_var = tk.StringVar()
        self.episode_var = tk.StringVar()
        self.episode_number_var = tk.StringVar(value="1")
        self.season_number_var = tk.StringVar(value="1")
        self.status_var = tk.StringVar(value="")
        self.filename_var = tk.StringVar(value="")
        self.path_var = tk.StringVar(value="")
        self.engine = controller.ReadyStateEngine()
        self._current_state = None
        self._load_file_dir = None
        self._import_material_dir = None
        self._last_loaded_file = None
        self._saved_path = None
        self._last_saved_episode_number = None

        self._restore_persisted_metadata()

        self._build_widgets()
        self._bind_events()
        self._apply_mode()
        self._refresh_ready_state()
        self._refresh_presets()
        self._refresh_recent_sources()

    def _restore_persisted_metadata(self):
        """Restore saved source_type/creator/material_level if still valid."""
        settings = gui_settings.load_settings()
        if settings["source_type"] in self.source_types:
            self.source_type_var.set(settings["source_type"])
        if settings["creator"] in self.creators:
            self.creator_var.set(settings["creator"])
        if settings["material_level"] in self.material_level_label_map:
            self.material_level_var.set(settings["material_level"])

    def _load_config(self):
        """Load controlled vocabulary; disable the window on config errors."""
        self.collections = []
        self.source_types = []
        self.creators = []
        self.styles = []
        self.topics = []
        self.creator_label_map = {}
        self.creator_id_map = {}
        self.material_level_label_map = {}
        self.material_level_id_map = {}
        self.style_label_map = {}
        self.style_id_map = {}
        self.topic_label_map = {}
        self.topic_id_map = {}
        try:
            self.collections = config_loader.load_collections()
            self.source_types = _processable_source_types(
                config_loader.load_source_types())
            self.creators = config_loader.load_creators()
            self.styles = config_loader.load_styles()
            self.topics = config_loader.load_topics()
            self._build_vocab_maps()
            self.config_error = None
            # The source type is a fixed, single value from the Config
            # vocabulary. The GUI offers no way to change it, so
            # source_type_var always follows the Config (never hardcoded);
            # downstream save logic reads it unchanged.
            if self.source_types:
                self.source_type_var.set(self.source_types[0])
            else:
                self.source_type_var.set("")
        except config_loader.ConfigError as exc:
            self.config_error = str(exc)

    def _build_vocab_maps(self):
        """Build the id<->display-label maps for the form combos.

        self.creators stays the raw id list used for membership and logic;
        the map is used only to show friendly display names in the form.

        Material level ids and style ids are integers; both maps store their
        ids as strings so the StringVar-backed combos translate cleanly.
        """
        self.creator_label_map = {}
        self.creator_id_map = {}
        for entry in config_loader.load_creators_full():
            vid = entry["creator_id"]
            label = entry["display_name"]
            self.creator_label_map[vid] = label
            self.creator_id_map[label] = vid
        self.material_level_label_map = {}
        self.material_level_id_map = {}
        for entry in config_loader.load_material_levels_full():
            level = str(entry["level"])
            label = entry["display_name"]
            self.material_level_label_map[level] = label
            self.material_level_id_map[label] = level
        self.style_label_map = {}
        self.style_id_map = {}
        # Style is optional: the leading "(none)" entry represents
        # no-style-selected (id "" maps back to None at save time).
        self.style_label_map[""] = "(none)"
        self.style_id_map["(none)"] = ""
        for entry in config_loader.load_styles_full():
            style_id = str(entry["style_id"])
            label = entry["display_name"]
            self.style_label_map[style_id] = label
            self.style_id_map[label] = style_id
        self.topic_label_map = {}
        self.topic_id_map = {}
        # Topic is optional: the leading "(none)" entry represents
        # no-topic-selected (id "" maps back to None at save time).
        self.topic_label_map[""] = "(none)"
        self.topic_id_map["(none)"] = ""
        for entry in config_loader.load_topics_full():
            topic_id = str(entry["topic_id"])
            label = entry["display_name"]
            self.topic_label_map[topic_id] = label
            self.topic_id_map[label] = topic_id

    def _build_widgets(self):
        main = ttk.Frame(self.root, padding=12)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Two independent columns: the form (body) and the right-side panels
        # (side). Keeping them in separate grid containers prevents the tall
        # right panels from inflating the form's metadata row heights.
        self.body = ttk.Frame(main)
        self.body.grid(row=0, column=0, sticky="nsew")
        self.side = ttk.Frame(main)
        self.side.grid(row=0, column=1, sticky="ns", padx=(14, 0))
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)
        main.columnconfigure(1, weight=0)

        body = self.body

        # Fonts.
        self.button_font = tkfont.Font(size=11, weight="bold")
        self.admin_font = tkfont.Font(size=10)
        self.combo_font = tkfont.Font(size=11)
        self.panel_title_font = tkfont.Font(size=11, weight="bold")
        self.workflow_font = tkfont.Font(size=13, weight="bold")
        self.caption_font = tkfont.Font(size=9, weight="bold")
        self.value_font = tkfont.Font(size=10)
        self.preset_font = tkfont.Font(size=10, weight="bold")

        # Combobox style (fixed width handled per-widget).
        style = ttk.Style()
        style.configure("SB.TCombobox", font=self.combo_font, padding=(8, 8))

        # Subtle blue-tinted main background surfaces.
        if self.root.winfo_class() == "Tk":
            self.root.configure(bg=APP_BG)
        style.configure("TFrame", background=APP_BG)
        style.configure("TLabelFrame", background=APP_BG)
        style.configure("TNotebook", background=APP_BG)

        row = 0

        # Identity type selection
        self.collection_radio = ttk.Radiobutton(
        body, text="Collection", variable=self.identity_var,
            value="collection", command=self._on_identity_change)
        self.collection_radio.grid(row=row, column=0, sticky="w")
        self.standalone_radio = ttk.Radiobutton(
        body, text="Standalone", variable=self.identity_var,
            value="standalone", command=self._on_identity_change)
        self.standalone_radio.grid(row=row, column=1, sticky="w")
        row += 1

        # Collection mode fields
        self.collection_label = ttk.Label(body, text="Collection:")
        self.collection_label.grid(row=row, column=0, sticky="w")
        self.collection_combo = ttk.Combobox(
        body, textvariable=self.collection_var,
            values=[c["collection_id"] for c in self.collections],
            state="readonly", style="SB.TCombobox", width=COMBOBOX_WIDTH)
        self.collection_combo.grid(row=row, column=1, sticky="w")
        self._collection_row = row
        row += 1

        # Shared metadata
        self.creator_label = ttk.Label(body, text="Creator:")
        self.creator_label.grid(row=row, column=0, sticky="w")
        self.creator_combo = ttk.Combobox(
            body, textvariable=self.creator_display_var,
            state="readonly", style="SB.TCombobox", width=COMBOBOX_WIDTH)
        self.creator_combo.grid(row=row, column=1, sticky="w")
        self._wire_label_combo(
            self.creator_combo, self.creator_var, self.creator_display_var,
            "creator_label_map", "creator_id_map")
        row += 1

        # Episode (collection mode field)
        self.episode_label = ttk.Label(body, text="Episode:")
        self.episode_label.grid(row=row, column=0, sticky="w")
        self.episode_entry = ttk.Entry(body, textvariable=self.episode_var,
                                       width=10, font=self.combo_font)
        self.episode_entry.grid(row=row, column=1, sticky="w")
        self._episode_row = row
        row += 1

        # Standalone mode field
        self.source_name_label = ttk.Label(body, text="Source name:")
        self.source_name_label.grid(row=row, column=0, sticky="w")
        self.source_name_entry = ttk.Entry(body,
                                           textvariable=self.source_name_var,
                                           width=COMBOBOX_WIDTH,
                                           font=self.combo_font)
        self.source_name_entry.grid(row=row, column=1, sticky="w")
        self._source_name_row = row
        row += 1

        # Material Level (mandatory)
        self.material_level_label = ttk.Label(body, text="Material Level:")
        self.material_level_label.grid(row=row, column=0, sticky="w")
        self.material_level_combo = ttk.Combobox(
            body, textvariable=self.material_level_display_var,
            state="readonly", style="SB.TCombobox", width=COMBOBOX_WIDTH)
        self.material_level_combo.grid(row=row, column=1, sticky="w")
        self._wire_label_combo(
            self.material_level_combo, self.material_level_var,
            self.material_level_display_var, "material_level_label_map",
            "material_level_id_map")
        row += 1

        # Style (optional; leading "(none)" entry)
        self.style_label = ttk.Label(body, text="Style:")
        self.style_label.grid(row=row, column=0, sticky="w")
        self.style_combo = ttk.Combobox(
            body, textvariable=self.style_display_var,
            state="readonly", style="SB.TCombobox", width=COMBOBOX_WIDTH)
        self.style_combo.grid(row=row, column=1, sticky="w")
        self._wire_label_combo(
            self.style_combo, self.style_id_var, self.style_display_var,
            "style_label_map", "style_id_map")
        row += 1

        # Topic (optional; leading "(none)" entry)
        self.topic_label = ttk.Label(body, text="Topic:")
        self.topic_label.grid(row=row, column=0, sticky="w")
        self.topic_combo = ttk.Combobox(
            body, textvariable=self.topic_display_var,
            state="readonly", style="SB.TCombobox", width=COMBOBOX_WIDTH)
        self.topic_combo.grid(row=row, column=1, sticky="w")
        self._wire_label_combo(
            self.topic_combo, self.topic_id_var, self.topic_display_var,
            "topic_label_map", "topic_id_map")
        row += 1

        # Duration (optional, seconds; validated at save time)
        self.duration_label = ttk.Label(body, text="Duration (seconds):")
        self.duration_label.grid(row=row, column=0, sticky="w")
        self.duration_entry = ttk.Entry(body, textvariable=self.duration_var,
                                        width=10, font=self.combo_font)
        self.duration_entry.grid(row=row, column=1, sticky="w")
        row += 1

        # Episode# (optional, cosmetic user metadata; session-scoped counter)
        self.episode_number_label = ttk.Label(body, text="Episode#:")
        self.episode_number_label.grid(row=row, column=0, sticky="w")
        self.episode_number_entry = ttk.Entry(
            body, textvariable=self.episode_number_var,
            width=10, font=self.combo_font)
        self.episode_number_entry.grid(row=row, column=1, sticky="w")
        row += 1

        # Season# (optional, cosmetic user metadata; never auto-advanced)
        self.season_number_label = ttk.Label(body, text="Season#:")
        self.season_number_label.grid(row=row, column=0, sticky="w")
        self.season_number_entry = ttk.Entry(
            body, textvariable=self.season_number_var,
            width=10, font=self.combo_font)
        self.season_number_entry.grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Separator(body, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=6)
        row += 1

        ttk.Label(body, text="Source text (paste below):").grid(
            row=row, column=0, sticky="w")
        source_actions = ttk.Frame(main)
        source_actions.grid(row=row, column=1, sticky="e")
        self.import_button = self._solid_button(
            source_actions, text="Import Material",
            command=self._import_material,
            bg=COLOR_ADMIN, font=self.admin_font, padding=(14, 9))
        self.import_button.pack(side="left")
        self.load_button = self._solid_button(
            source_actions, text="Load File", command=self._load_file,
            bg=COLOR_ADMIN, font=self.admin_font, padding=(14, 9))
        self.load_button.pack(side="left", padx=(8, 0))
        row += 1

        self.text_area = tk.Text(body, height=18, width=70, wrap="none")
        self.text_area.grid(row=row, column=0, columnspan=2, sticky="nsew")
        self._text_row = row
        row += 1

        ttk.Separator(body, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=6)
        row += 1

        # Action row: workflow buttons grouped left, administrative right.
        # Aligned with the main form grid: workflow group under the label
        # column, administrative group under the field column (right edge).
        self.actions_frame = ttk.Frame(body)
        self.actions_frame.grid(row=row, column=0, columnspan=2, sticky="ew",
                                pady=(8, 0))
        self.actions_frame.columnconfigure(1, weight=1)

        # Workflow group: Save Source + Create Next (side by side).
        self.workflow_actions = ttk.Frame(self.actions_frame)
        self.workflow_actions.grid(row=0, column=0, sticky="w")
        self.save_button = self._solid_button(
            self.workflow_actions, text="Save Source", command=self.on_save,
            bg=COLOR_GREY, font=self.button_font, padding=(26, 14))
        self.save_button.pack(side="left")
        self.next_button = self._solid_button(
            self.workflow_actions, text="Add Another",
            command=self.on_next_source, bg=COLOR_GREY, font=self.button_font,
            padding=(26, 14))
        self.next_button.pack(side="left", padx=(8, 0))

        # Administrative group: Open Folder + Edit Metadata (far right).
        self.admin_actions = ttk.Frame(self.actions_frame)
        self.admin_actions.grid(row=0, column=1, sticky="e")
        self.open_folder_button = self._solid_button(
            self.admin_actions, text="Open Folder",
            command=self._open_folder, bg=COLOR_ADMIN, font=self.admin_font,
            padding=(14, 9))
        self.open_folder_button.pack(side="left")
        self.metadata_button = self._solid_button(
            self.admin_actions, text="Edit Metadata...",
            command=self._open_metadata_editor, bg=COLOR_ADMIN,
            font=self.admin_font, padding=(14, 9))
        self.metadata_button.pack(side="left", padx=(8, 0))
        row += 1

        # Status Panel (primary feedback; visually dominant).
        self.status_frame = tk.LabelFrame(
        body, text="Status", font=self.panel_title_font, bg=PANEL_BG,
            fg=PANEL_TITLE_FG, padx=10, pady=8, bd=1, relief="groove")
        self.status_frame.grid(row=row, column=0, columnspan=2, sticky="ew",
                               pady=(10, 0))
        self.status_frame.columnconfigure(0, weight=1)

        self.status_label = tk.Label(
            self.status_frame, textvariable=self.status_var,
            font=self.workflow_font, bg=PANEL_BG, fg=PANEL_MESSAGE_FG,
            anchor="w", justify="left", wraplength=760)
        self.status_label.grid(row=0, column=0, sticky="w")

        self.filename_caption = tk.Label(
            self.status_frame, text="Filename", font=self.caption_font,
            bg=PANEL_BG, fg=PANEL_CAPTION_FG, anchor="w")
        self.filename_caption.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.filename_value = tk.Label(
            self.status_frame, textvariable=self.filename_var,
            font=self.value_font, bg=PANEL_BG, fg=PANEL_MESSAGE_FG,
            anchor="w", justify="left", wraplength=760)
        self.filename_value.grid(row=2, column=0, sticky="w")

        self.path_caption = tk.Label(
            self.status_frame, text="Save Location", font=self.caption_font,
            bg=PANEL_BG, fg=PANEL_CAPTION_FG, anchor="w")
        self.path_caption.grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.path_value = tk.Label(
            self.status_frame, textvariable=self.path_var,
            font=self.value_font, bg=PANEL_BG, fg=PANEL_MESSAGE_FG,
            anchor="w", justify="left", wraplength=760)
        self.path_value.grid(row=4, column=0, sticky="w")
        row += 1

        body.columnconfigure(1, weight=1)
        body.rowconfigure(self._text_row, weight=1)

        # Quick Presets panel (right-side dead space).
        self._build_presets_panel(self.side)

        if self.config_error is not None:
            self.status_var.set(f"Config error: {self.config_error}")
            self.filename_var.set("")
            self.path_var.set("")
            self.save_button.configure(state="disabled")
            self.next_button.configure(state="disabled")
            self.open_folder_button.configure(state="disabled")
            self.metadata_button.configure(state="disabled")
            self.edit_presets_button.configure(state="disabled")
            for button in self.preset_buttons.values():
                button.configure(state="disabled")

    def _solid_button(self, parent, text, command, bg, font, padding):
        """Create a solid filled tk.Button with white text."""
        button = tk.Button(
            parent, text=text, command=command, bg=bg, fg=COLOR_WHITE,
            activebackground=bg, activeforeground=COLOR_WHITE,
            disabledforeground=COLOR_WHITE, font=font,
            padx=padding[0], pady=padding[1], bd=0, relief="flat",
            highlightthickness=0)
        return button

    def _build_presets_panel(self, side):
        """Build the Quick Presets + Recent Sources panels in the right-side
        dead space. Both are packed vertically inside a dedicated `side`
        container so they never inflate the form's grid row heights."""
        self.presets_frame = ttk.LabelFrame(side, text="Templates",
                                            padding=8)
        self.presets_frame.pack(side="top", fill="x")

        self.preset_buttons = {}
        for slot in range(1, quick_presets.SLOT_COUNT + 1):
            button = self._solid_button(
                self.presets_frame, text=quick_presets.EMPTY_SLOT_NAME,
                command=lambda s=slot: self._on_preset_click(s),
                bg=COLOR_ADMIN, font=self.preset_font, padding=(12, 9))
            button.configure(width=PRESET_BUTTON_WIDTH)
            button.grid(row=(slot - 1) // 2, column=(slot - 1) % 2,
                        sticky="ew", padx=4, pady=4)
            self.preset_buttons[slot] = button

        self.edit_presets_button = self._solid_button(
            self.presets_frame, text="Edit Presets...",
            command=self._open_preset_editor, bg=COLOR_ADMIN,
            font=self.admin_font, padding=(12, 9))
        self.edit_presets_button.grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=4,
            pady=(12, 4))

        self.presets_frame.columnconfigure(0, weight=1)
        self.presets_frame.columnconfigure(1, weight=1)

        # Recent Sources display below Quick Presets.
        self.recent_frame = ttk.LabelFrame(side, text="Recent Sources",
                                           padding=8)
        self.recent_frame.pack(side="top", fill="x", pady=(14, 0))
        self.recent_list = tk.Listbox(
            self.recent_frame, height=10, width=PRESET_BUTTON_WIDTH + 6,
            activestyle="none", exportselection=False)
        self.recent_list.pack(fill="x")

    def _refresh_recent_sources(self):
        """Relabel the Recent Sources list from the latest packages."""
        labels = recent_sources.recent_labels()
        self.recent_list.delete(0, "end")
        for label in labels:
            self.recent_list.insert("end", label)

    def _refresh_presets(self):
        """Relabel preset buttons from stored presets."""
        presets = quick_presets.load_presets()
        for slot, button in self.preset_buttons.items():
            preset = presets.get(slot)
            if preset is None:
                button.configure(text=quick_presets.EMPTY_SLOT_NAME)
            else:
                button.configure(text=preset.get("display_name")
                                 or quick_presets.EMPTY_SLOT_NAME)

    def _wire_label_combo(self, combo, id_var, display_var, label_map_name,
                          id_map_name):
        """Wire a readonly combo to show friendly display names while its
        paired id var keeps the raw id.

        label_map_name / id_map_name are attribute names on self, resolved
        at call time so a vocabulary reload (which rebuilds the maps) stays
        in sync with the trace and selection binding.

        - combo values come from the label map (insertion order preserved).
        - selecting a label maps it back to the id via the id map, so id_var
          always holds the raw id (never a display name).
        - setting id_var programmatically (settings/snapshot/preset restore)
          updates the shown label via a trace on id_var.
        """
        combo.configure(textvariable=display_var,
                        values=list(getattr(self, label_map_name).values()))
        combo.bind("<<ComboboxSelected>>",
                   lambda e: self._apply_label_to_id(
                       display_var, getattr(self, id_map_name), id_var))

        def _sync(*args):
            label_map = getattr(self, label_map_name)
            display_var.set(label_map.get(id_var.get(), id_var.get()))

        id_var.trace_add("write", _sync)
        # Reflect any value already set on the id var (e.g. restored before
        # the widgets were built).
        display_var.set(getattr(self, label_map_name).get(
            id_var.get(), id_var.get()))

    @staticmethod
    def _apply_label_to_id(display_var, id_map, id_var):
        """Translate a chosen display label back into its raw id."""
        label = display_var.get()
        id_var.set(id_map.get(label, label))

    def _sync_creator_display(self, *args):
        """Show the display label for the current creator id."""
        raw = self.creator_var.get()
        self.creator_display_var.set(self.creator_label_map.get(raw, raw))

    def _on_creator_selected(self, event=None):
        """Translate the picked creator label back into its id."""
        self._apply_label_to_id(
            self.creator_display_var, self.creator_id_map, self.creator_var)

    def _bind_events(self):
        for var, callback in (
            (self.source_name_var, self._on_metadata_changed),
            (self.episode_var, self._on_metadata_changed),
            (self.source_type_var, self._on_metadata_changed),
            (self.creator_var, self._on_metadata_changed),
            (self.material_level_var, self._on_metadata_changed),
            (self.style_id_var, self._on_metadata_changed),
            (self.topic_id_var, self._on_metadata_changed),
            (self.duration_var, self._on_metadata_changed),
            (self.episode_number_var, self._on_metadata_changed),
            (self.season_number_var, self._on_metadata_changed),
        ):
            var.trace_add("write", callback)
        # The collection selection changes the hidden episode value as well
        # as metadata, so it gets its own handler.
        self.collection_var.trace_add("write", self._on_collection_changed)
        self.text_area.bind("<<Modified>>", self._on_text_changed)

    def _on_text_changed(self, *args):
        if not self.text_area.edit_modified():
            return
        self.text_area.edit_modified(False)
        self._on_metadata_changed()

    def _on_metadata_changed(self, *args):
        self._update_next_button_label()
        self._persist_metadata()
        self._refresh_ready_state()

    def _on_collection_changed(self, *args):
        """React to a collection selection change.

        Re-computes the hidden episode value (every collection now uses a
        hidden auto-incrementing episode) and keeps metadata effects intact.
        """
        self._apply_mode()
        self._refresh_hidden_episode()
        self._on_metadata_changed()

    def _update_next_button_label(self):
        """Set the Add Another button label from the current source type."""
        source_type = self.source_type_var.get()
        label = SOURCE_TYPE_LABELS.get(source_type, source_type)
        text = f"Add Another {label}" if label else "Add Another"
        self.next_button.configure(text=text)

    def _persist_metadata(self):
        """Save current source_type/creator/material_level for the next
        session."""
        if self.config_error is not None:
            return
        try:
            gui_settings.save_settings({
                "source_type": self.source_type_var.get(),
                "creator": self.creator_var.get(),
                "material_level": self.material_level_var.get(),
            })
        except gui_settings.SettingsError:
            pass

    def _current_material_level(self):
        """Return the selected material level as int, or None when blank."""
        raw = self.material_level_var.get()
        if raw == "":
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def _current_style_id(self):
        """Return the selected style id as int, or None when no style."""
        raw = self.style_id_var.get()
        if raw == "":
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def _current_topic_id(self):
        """Return the selected topic id as int, or None when no topic."""
        raw = self.topic_id_var.get()
        if raw == "":
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def _current_duration_seconds(self):
        """Return the duration as a non-negative number, or None when blank
        or not a non-negative number."""
        raw = self.duration_var.get().strip()
        if raw == "":
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        if value < 0:
            return None
        if value.is_integer():
            return int(value)
        return value

    def _current_episode_number(self):
        """Return the Episode# as an int, or None when blank/invalid."""
        raw = self.episode_number_var.get().strip()
        if raw == "":
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def _current_season_number(self):
        """Return the Season# as an int, or None when blank/invalid."""
        raw = self.season_number_var.get().strip()
        if raw == "":
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def _next_episode_number_suggestion(self):
        """Return the suggested next Episode#.

        Previous value + 1 when the previous value is a valid integer,
        else "1".
        """
        raw = self.episode_number_var.get().strip()
        if raw == "":
            return "1"
        try:
            previous = int(raw)
        except (TypeError, ValueError):
            return "1"
        return str(previous + 1)

    def _current_form(self):
        """Collect the current form values for the ready-state engine."""
        return {
            "identity_type": self.identity_var.get(),
            "collection_id": self.collection_var.get(),
            "source_name": self.source_name_var.get(),
            "episode": self.episode_var.get(),
            "source_type": self.source_type_var.get(),
            "creator": self.creator_var.get(),
            "source_text": self.text_area.get("1.0", "end"),
            "material_level": self._current_material_level(),
            "style_id": self._current_style_id(),
            "topic_id": self._current_topic_id(),
            "duration_seconds": self._current_duration_seconds(),
            "episode_number": self.episode_number_var.get(),
            "season_number": self.season_number_var.get(),
        }

    def _refresh_ready_state(self):
        """Ask the controller for the workflow state; apply it to the GUI."""
        if self.config_error is not None:
            return
        form = self._current_form()
        result = self.engine.evaluate(**form)
        self._current_state = result["state"]
        self.status_var.set(result["message"])
        self._update_workflow_panel_secondary(result)
        self._apply_state_visuals(result["state"])

    def _update_workflow_panel_secondary(self, result):
        """Populate the secondary filename / save location references."""
        filename, save_path = self._current_filename_and_path()
        self.filename_var.set(filename or "")
        self.path_var.set(save_path or "")

    def _apply_state_visuals(self, state):
        """Set button enabled/disabled + colour from the controller state."""
        visuals = ready_state_visuals(state)
        self._set_button_visual(self.save_button, visuals["save_bg"],
                                visuals["save_enabled"])
        self._set_button_visual(self.next_button, visuals["next_bg"],
                                visuals["next_enabled"])

    def _set_button_visual(self, button, bg, enabled):
        """Paint a solid button and set its enabled state."""
        button.configure(bg=bg, activebackground=bg,
                         state="normal" if enabled else "disabled")

    def _refresh_hidden_episode(self):
        """Fill the hidden episode field with the live next sequence number.

        Collection sources always use a hidden auto-incrementing episode.
        The field stays hidden but the ReadyStateEngine and controller
        validation still require a valid episode value, so the next live
        sequence (max+1) is computed silently whenever a collection is
        selected.
        """
        if self.identity_var.get() == "collection":
            self.episode_var.set(str(controller.next_auto_sequence(
                self.collection_var.get())))

    def _apply_mode(self):
        """Show the active identity path's fields and hide the others.

        Collection mode: the Episode field is never shown (episode is a
        hidden auto-incrementing system identifier for every collection);
        the collection combo stays visible.
        Standalone mode: the collection combo is hidden; the source name
        field is shown.
        """
        is_collection = self.identity_var.get() == "collection"

        # Collection fields
        self.collection_label.grid() if is_collection else self.collection_label.grid_remove()
        self.collection_combo.grid() if is_collection else self.collection_combo.grid_remove()
        self.episode_label.grid_remove()
        self.episode_entry.grid_remove()

        # Standalone field
        if is_collection:
            self.source_name_label.grid_remove()
            self.source_name_entry.grid_remove()
        else:
            self.source_name_label.grid()
            self.source_name_entry.grid()

    def _on_identity_change(self):
        self._apply_mode()
        self._refresh_ready_state()

    def _current_source_id(self):
        """Derive the pipeline source_id for the current form (or '')."""
        is_collection = self.identity_var.get() == "collection"
        if is_collection:
            return controller.source_id_for(
                source_type=self.source_type_var.get(),
                collection_id=self.collection_var.get(),
                episode=self._current_episode_value())
        return controller.source_id_for(
            source_type=self.source_type_var.get(),
            source_name=self.source_name_var.get())

    def _current_episode_value(self):
        try:
            return int(self.episode_var.get())
        except (TypeError, ValueError):
            return None

    def _current_filename_and_path(self):
        """
        Derive the current canonical filename and save path from the form.

        Returns (filename, save_path) or (None, None) when not derivable.
        """
        is_collection = self.identity_var.get() == "collection"
        if is_collection:
            collection_id = self.collection_var.get()
            episode = self.episode_var.get()
            if not collection_id or episode == "":
                return None, None
            try:
                episode_value = int(episode)
            except (TypeError, ValueError):
                return None, None
            if episode_value < 0:
                return None, None
            filename = controller.generate_filename(collection_id, episode_value)
            save_path = controller.source_path(collection_id, episode_value)
            return filename, str(save_path)
        else:
            source_name = self.source_name_var.get()
            if not source_name:
                return None, None
            filename = controller.generate_standalone_filename(source_name)
            save_path = controller.standalone_source_path(source_name)
            return filename, str(save_path)

    def _load_default_dir(self):
        """
        Resolve the Load File dialog's default folder.

        Priority:
        1. previously used Load File folder (session only),
        2. C:\\Jprogram\\Intake\\,
        3. project root fallback.
        """
        if self._load_file_dir is not None:
            return self._load_file_dir
        intake = paths.INTAKE
        if intake.is_dir():
            return intake
        return PROJECT_ROOT

    def _import_default_dir(self):
        """
        Resolve the Import Material dialog's default folder.

        Priority:
        1. previously used Import Material folder (session only),
        2. Raw Imports folder (paths.RAW_IMPORTS),
        3. project root fallback.
        """
        if self._import_material_dir is not None:
            return self._import_material_dir
        raw_imports = paths.RAW_IMPORTS
        if raw_imports.is_dir():
            return raw_imports
        return PROJECT_ROOT

    def _load_file(self):
        """
        Load a prepared text file into the source text area.

        Opens a file picker, reads the selected text file, and places its
        contents into the paste area. Does NOT save, create a source file, or
        modify metadata. The ReadyStateEngine re-evaluates the form normally.
        """
        if self.config_error is not None:
            return
        default_dir = self._load_default_dir()
        candidate = next_load_file_candidate(default_dir, self._last_loaded_file)
        path = filedialog.askopenfilename(
            parent=self.root, title="Load Prepared Text File",
            initialdir=default_dir,
            initialfile=candidate.name if candidate else "",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        # Remember this folder for the rest of the session.
        self._load_file_dir = Path(path).parent
        try:
            content = Path(path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            messagebox.showerror(
                "Cannot load file",
                "The selected file is not UTF-8 text.", parent=self.root)
            return
        except OSError as exc:
            messagebox.showerror(
                "Cannot load file", f"Cannot read the file:\n\n{exc}",
                parent=self.root)
            return
        if content.strip() == "":
            messagebox.showerror(
                "Cannot load file", "The selected file is empty.",
                parent=self.root)
            return
        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", content)
        self._last_loaded_file = Path(path)
        self._on_text_changed()
        self.status_var.set(f"Loaded: {Path(path).name}\n"
                            f"{self.status_var.get()}")

    def _import_material(self):
        """Open the Import Material dialog (Sources gathering, not processing)."""
        if self.config_error is not None:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Import Material")
        dialog.transient(self.root)
        dialog.resizable(False, False)

        format_var = tk.StringVar(value=import_material.FORMAT_SUBTITLE)
        paths_var = tk.StringVar(value="")
        feedback_var = tk.StringVar()

        body = ttk.Frame(dialog, padding=12)
        body.grid(row=0, column=0, sticky="nsew")

        row = 0
        ttk.Label(body, text="Source Format:").grid(row=row, column=0,
                                                    sticky="w")
        row += 1
        for key in import_material.SOURCE_FORMATS:
            label = import_material.FORMAT_LABELS[key]
            ttk.Radiobutton(body, text=label, variable=format_var,
                            value=key).grid(row=row, column=0, sticky="w")
            row += 1

        ttk.Label(body, text="Select file(s):").grid(row=row, column=0,
                                                     sticky="w", pady=(8, 0))
        row += 1

        file_row = ttk.Frame(body)
        file_row.grid(row=row, column=0, sticky="ew")
        ttk.Label(file_row, textvariable=paths_var, width=50,
                  anchor="w").pack(side="left")

        def browse():
            default_dir = self._import_default_dir()
            selected = filedialog.askopenfilenames(
                parent=dialog, title="Select Material Files",
                initialdir=default_dir,
                filetypes=[("All files", "*.*")])
            if selected:
                # Remember this folder for the rest of the session.
                self._import_material_dir = Path(selected[0]).parent
                paths_var.set("; ".join(selected))
        ttk.Button(file_row, text="Browse",
                   command=browse).pack(side="left", padx=(8, 0))
        row += 1

        feedback_label = ttk.Label(body, textvariable=feedback_var,
                                   foreground="#c62828")
        feedback_label.grid(row=row, column=0, sticky="w", pady=(8, 0))
        row += 1

        buttons = ttk.Frame(body)
        buttons.grid(row=row, column=0, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel",
                   command=dialog.destroy).pack(side="left", padx=4)
        ttk.Button(buttons, text="Import",
                   command=lambda: self._do_import(
                       dialog, format_var, paths_var, feedback_var)).pack(
            side="left", padx=4)

        self._center_child_over_parent(dialog)
        dialog.grab_set()
        self.root.wait_window(dialog)

    def _do_import(self, dialog, format_var, paths_var, feedback_var):
        """Convert selected material and place it in the source text area."""
        source_format = format_var.get()
        raw = paths_var.get().strip()
        if not raw:
            feedback_var.set("Select at least one file.")
            return
        paths = [Path(p) for p in raw.split("; ") if p]
        try:
            combined = import_material.convert_files(paths, source_format)
        except import_material.ImportError as exc:
            feedback_var.set(str(exc))
            return
        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", combined)
        self._on_text_changed()
        # Material Level suggestion from the first selected file's parent
        # folder (a known level-named folder). Suggestion only — the
        # dropdown stays editable, exactly like the Episode# suggestion.
        if paths:
            suggested = import_material.suggested_material_level(paths[0])
            if suggested is not None:
                self.material_level_var.set(str(suggested))
        self.status_var.set(
            f"Imported {len(paths)} file(s) as "
            f"{import_material.FORMAT_LABELS.get(source_format, source_format)}."
            f"\n{self.status_var.get()}")
        if dialog is not None:
            dialog.destroy()

    def on_save(self):
        """Create the canonical source file only when the state is READY."""
        if self.config_error is not None:
            return
        if self._current_state != "READY":
            self._refresh_ready_state()
            return
        if not source_package.is_processable_source_type(
                self.source_type_var.get()):
            self.status_var.set(
                "That source type is not currently available for processing.")
            return
        source_text = self.text_area.get("1.0", "end")
        is_collection = self.identity_var.get() == "collection"

        material_level = self._current_material_level()
        style_id = self._current_style_id()
        topic_id = self._current_topic_id()
        duration_seconds = self._current_duration_seconds()
        if self.duration_var.get().strip() != "" and duration_seconds is None:
            self.status_var.set("Duration must be a non-negative number.")
            return

        episode_number = self._current_episode_number()
        season_number = self._current_season_number()

        try:
            if is_collection:
                # Recompute the hidden sequence live at save time so a source
                # added to the collection since the field was last filled
                # is never overwritten by a stale cached number.
                self.episode_var.set(str(controller.next_auto_sequence(
                    self.collection_var.get())))
                result = controller.create_collection_source(
                    collection_id=self.collection_var.get(),
                    episode=self.episode_var.get(),
                    source_type=self.source_type_var.get(),
                    creator=self.creator_var.get(),
                    source_text=source_text,
                    overwrite=False,
                    material_level=material_level,
                    style_id=style_id,
                    topic_id=topic_id,
                    duration_seconds=duration_seconds,
                    episode_number=episode_number,
                    season_number=season_number,
                )
            else:
                result = controller.create_standalone_source(
                    source_name=self.source_name_var.get(),
                    source_type=self.source_type_var.get(),
                    creator=self.creator_var.get(),
                    source_text=source_text,
                    overwrite=False,
                    material_level=material_level,
                    style_id=style_id,
                    topic_id=topic_id,
                    duration_seconds=duration_seconds,
                    episode_number=episode_number,
                    season_number=season_number,
                )
        except Exception as exc:
            self.engine.set_error(f"Unexpected error: {exc}")
            self._refresh_ready_state()
            messagebox.showerror("Unexpected error", str(exc))
            return

        if result["success"]:
            self._saved_path = Path(result["path"])
            # Suggest the next Episode# for the next entry; Season# is
            # never auto-advanced. The snapshot records the advanced value
            # so the form still matches it in the SAVED state.
            self._last_saved_episode_number = self.episode_number_var.get()
            self.episode_number_var.set(self._next_episode_number_suggestion())
            self.engine.mark_saved({
                "identity_type": self.identity_var.get(),
                "collection_id": self.collection_var.get(),
                "source_name": self.source_name_var.get(),
                "episode": self.episode_var.get(),
                "source_type": self.source_type_var.get(),
                "creator": self.creator_var.get(),
                "source_text": source_text,
                "filename": result["filename"],
                "material_level": material_level,
                "style_id": style_id,
                "topic_id": topic_id,
                "duration_seconds": duration_seconds,
                "episode_number": self.episode_number_var.get(),
                "season_number": self.season_number_var.get(),
            })
            self._refresh_ready_state()
            self._refresh_recent_sources()
            source_id = self._current_source_id()
            message = f"Saved successfully.\nSource ID: {source_id}"
            if result.get("package_error"):
                message += (f"\nPackage warning: {result['package_error']}")
            self.status_var.set(message)
        else:
            errors = "\n".join(f"• {e}" for e in result["errors"])
            self.engine.set_error(errors)
            self._refresh_ready_state()

    def on_next_source(self):
        """Prepare the next source form. No file is created or saved."""
        if self.config_error is not None:
            return
        if self._current_state != "SAVED":
            self._refresh_ready_state()
            return
        state = controller.next_source_state(
            identity_type=self.identity_var.get(),
            collection_id=self.collection_var.get(),
            episode=self.episode_var.get(),
            source_type=self.source_type_var.get(),
            creator=self.creator_var.get(),
            material_level=self._current_material_level(),
            style_id=self._current_style_id(),
            topic_id=self._current_topic_id(),
            episode_number=self._last_saved_episode_number,
            season_number=self.season_number_var.get(),
        )
        # Apply the prepared state.
        self.identity_var.set(state["identity_type"])
        self.collection_var.set(state["collection_id"])
        self.source_name_var.set(state["source_name"])
        self.episode_var.set(state["episode"])
        self.source_type_var.set(state["source_type"])
        self.creator_var.set(state["creator"])
        self.material_level_var.set(
            "" if state["material_level"] is None
            else str(state["material_level"]))
        self.style_id_var.set(
            "" if state["style_id"] is None else str(state["style_id"]))
        self.topic_id_var.set(
            "" if state["topic_id"] is None else str(state["topic_id"]))
        self.duration_var.set(state["duration_seconds"])
        self.episode_number_var.set(state["episode_number"])
        season_number = state["season_number"]
        self.season_number_var.set(
            "" if season_number is None else str(season_number))
        self.text_area.delete("1.0", "end")
        self.engine.reset()
        self._apply_mode()
        self._refresh_ready_state()

    def _on_preset_click(self, slot):
        """Apply a quick preset once; it has no further control over form."""
        if self.config_error is not None:
            return
        preset = quick_presets.load_slot(slot)
        if preset is None:
            self.status_var.set("Empty Slot — edit presets to define it.")
            return
        updates = quick_presets.preset_population(
            preset,
            [c["collection_id"] for c in self.collections],
            self.source_types,
            self.creators,
        )
        if not updates:
            self.status_var.set("Preset has no valid values to apply.")
            return
        if updates.get("identity_type") == "standalone":
            self.identity_var.set("standalone")
        else:
            self.identity_var.set("collection")
        self._apply_mode()
        if "collection_id" in updates:
            self.collection_var.set(updates["collection_id"])
        if "source_name" in updates:
            self.source_name_var.set(updates["source_name"])
        if "source_type" in updates:
            self.source_type_var.set(updates["source_type"])
        if "creator" in updates:
            self.creator_var.set(updates["creator"])
        self._refresh_ready_state()
        self.status_var.set(
            f"Preset loaded: {preset.get('display_name')}\n"
            f"{self.status_var.get()}")

    def _center_child_over_parent(self, child):
        """
        Position a child Toplevel centred over the Source Builder window.

        Uses the parent's actual on-screen geometry so the child appears on
        the same monitor as the application in multi-monitor setups.
        """
        self.root.update_idletasks()
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_w = self.root.winfo_width()
        parent_h = self.root.winfo_height()
        child.update_idletasks()
        child_w = child.winfo_reqwidth()
        child_h = child.winfo_reqheight()
        x, y = centered_position(parent_x, parent_y, parent_w, parent_h,
                                 child_w, child_h)
        child.geometry(f"+{x}+{y}")

    def _open_preset_editor(self):
        """Open the preset editor window (separate window)."""
        editor = tk.Toplevel(self.root)
        editor.title("Edit Templates")
        editor.transient(self.root)
        editor.resizable(False, False)

        collection_ids = [c["collection_id"] for c in self.collections]

        slot_var = tk.StringVar(value="1")
        name_var = tk.StringVar()
        identity_var = tk.StringVar(value="collection")
        collection_var = tk.StringVar()
        source_type_var = tk.StringVar()
        creator_var = tk.StringVar()
        creator_display_var = tk.StringVar()
        feedback_var = tk.StringVar()

        body = ttk.Frame(editor, padding=12)
        body.grid(row=0, column=0, sticky="nsew")

        row = 0
        ttk.Label(body, text="Preset slot:").grid(row=row, column=0, sticky="w")
        slot_combo = ttk.Combobox(
            body, textvariable=slot_var,
            values=[str(i) for i in range(1, quick_presets.SLOT_COUNT + 1)],
            state="readonly", width=6)
        slot_combo.grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Label(body, text="Display Name:").grid(row=row, column=0, sticky="w")
        name_entry = ttk.Entry(body, textvariable=name_var, width=30)
        name_entry.grid(row=row, column=1, sticky="w")
        row += 1

        identity_frame = ttk.Frame(body)
        identity_frame.grid(row=row, column=1, sticky="w")
        ttk.Radiobutton(identity_frame, text="Collection",
                        variable=identity_var, value="collection",
                        command=self._apply_preset_editor_mode).pack(side="left")
        ttk.Radiobutton(identity_frame, text="Standalone",
                        variable=identity_var, value="standalone",
                        command=self._apply_preset_editor_mode).pack(
            side="left", padx=(8, 0))
        row += 1

        # Editor-local identity + collection field.
        self._preset_editor_identity_var = identity_var
        collection_label = ttk.Label(body, text="Collection:")
        collection_label.grid(row=row, column=0, sticky="w")
        collection_combo = ttk.Combobox(
            body, textvariable=collection_var, values=collection_ids,
            state="readonly", width=30)
        collection_combo.grid(row=row, column=1, sticky="w")
        self._preset_editor_collection = (collection_label, collection_combo)
        row += 1

        ttk.Label(body, text="Creator:").grid(row=row, column=0, sticky="w")
        creator_combo = ttk.Combobox(
            body, textvariable=creator_display_var,
            state="readonly", width=30)
        creator_combo.grid(row=row, column=1, sticky="w")
        self._wire_label_combo(
            creator_combo, creator_var, creator_display_var,
            "creator_label_map", "creator_id_map")
        row += 1

        feedback_label = ttk.Label(body, textvariable=feedback_var,
                                   foreground="#c62828")
        feedback_label.grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        buttons = ttk.Frame(body)
        buttons.grid(row=row, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Cancel",
                   command=editor.destroy).pack(side="left", padx=4)
        ttk.Button(buttons, text="Save Preset",
                   command=lambda: self._save_preset_from_editor(
                       editor, slot_var, name_var, identity_var,
                       collection_var, source_type_var, creator_var,
                       feedback_var)).pack(
            side="left", padx=4)

        def load_current():
            """Load the selected slot's preset into the editor fields."""
            try:
                slot = int(slot_var.get())
            except (TypeError, ValueError):
                return
            preset = quick_presets.load_slot(slot)
            if preset is None:
                name_var.set("")
                identity_var.set("collection")
                collection_var.set("")
                source_type_var.set("")
                creator_var.set("")
            else:
                name_var.set(preset.get("display_name", ""))
                identity_var.set(preset.get("identity_type", "collection"))
                collection_var.set(preset.get("collection_id", ""))
                source_type_var.set(preset.get("source_type", ""))
                creator_var.set(preset.get("creator", ""))
            self._apply_preset_editor_mode()

        slot_combo.bind("<<ComboboxSelected>>", lambda e: load_current())
        load_current()
        self._apply_preset_editor_mode()
        # Centre over the parent only after the editor is fully built so the
        # requested size is accurate.
        self._center_child_over_parent(editor)

    def _apply_preset_editor_mode(self):
        """Show or hide the collection field in the preset editor.

        The collection field is shown only for collection presets. There is
        no source_name field in this editor: presets are reusable templates
        (source_type/creator), never pinned to a specific source name.
        """
        if not hasattr(self, "_preset_editor_collection"):
            return
        identity_var = getattr(self, "_preset_editor_identity_var", None)
        is_collection = True
        if identity_var is not None and identity_var.get() == "standalone":
            is_collection = False
        collection_label, collection_combo = self._preset_editor_collection
        if is_collection:
            collection_label.grid()
            collection_combo.grid()
        else:
            collection_label.grid_remove()
            collection_combo.grid_remove()

    def _save_preset_from_editor(self, editor, slot_var, name_var,
                                 identity_var, collection_var, source_type_var,
                                 creator_var, feedback_var):
        """Validate and save the preset; refresh the panel on success."""
        try:
            slot = int(slot_var.get())
        except (TypeError, ValueError):
            feedback_var.set("Invalid slot.")
            return
        try:
            quick_presets.save_slot(
                slot, name_var.get(), identity_var.get(),
                collection_id=collection_var.get(),
                source_type=source_type_var.get(),
                creator=creator_var.get())
        except quick_presets.PresetError as exc:
            feedback_var.set(str(exc))
            return
        self._refresh_presets()
        editor.destroy()

    def _open_folder(self):
        """Open the save folder for the current metadata in Explorer."""
        if self.config_error is not None:
            return
        is_collection = self.identity_var.get() == "collection"
        if is_collection:
            collection_id = self.collection_var.get()
            if not collection_id:
                self._refresh_ready_state()
                return
            folder = controller.collection_dir(collection_id)
        else:
            folder = controller.standalone_dir()
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(str(folder))

    def _open_metadata_editor(self):
        """Launch the metadata editor window (Collections/Creators/Styles)."""
        metadata_editor_gui.MetadataEditorWindow(self)

    # Intentionally retained, though currently unreachable from the UI: no
    # button calls this as of this change (the "Processing" button in the
    # admin actions row was removed — the batching rationale is gone now that
    # the parser is the deterministic local GiNZA parser). Kept in case the
    # Processing window is wanted again later. The module-level
    # `import processing_tab_gui` below remains required by this method.
    def _open_processing(self):
        """Launch the Processing tab window."""
        processing_tab_gui.ProcessingTabWindow(self)

    def _refresh_metadata(self):
        """Reload config vocabularies and refresh dropdowns + presets."""
        self._load_config()
        self._refresh_dropdowns()
        self._refresh_presets()
        self._refresh_ready_state()

    def _refresh_dropdowns(self):
        """Update combobox value lists from the freshly loaded config."""
        self.collection_combo.configure(
            values=[c["collection_id"] for c in self.collections])
        self.creator_combo.configure(
            values=[self.creator_label_map[o] for o in self.creators])
        self.material_level_combo.configure(
            values=list(self.material_level_label_map.values()))
        self.style_combo.configure(
            values=list(self.style_label_map.values()))
        self.topic_combo.configure(
            values=list(self.topic_label_map.values()))
        # The vocabulary may have changed; re-show the current ids' labels.
        self._sync_creator_display()
        self.material_level_display_var.set(
            self.material_level_label_map.get(
                self.material_level_var.get(), self.material_level_var.get()))
        self.style_display_var.set(
            self.style_label_map.get(self.style_id_var.get(),
                                     self.style_id_var.get()))
        self.topic_display_var.set(
            self.topic_label_map.get(self.topic_id_var.get(),
                                     self.topic_id_var.get()))
        self._apply_mode()
        # The metadata editor may have changed the collection list; ensure
        # the hidden episode value is still valid for the selected
        # collection.
        self._refresh_hidden_episode()


def main():
    root = tk.Tk()
    SourceBuilderApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
