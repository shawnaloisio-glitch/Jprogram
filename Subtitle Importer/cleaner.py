#!/usr/bin/env python3
"""
cleaner.py

Japanese Corpus Pipeline - Subtitle Importer cleaner.

Converts subtitle files (.srt, .vtt) into clean text files suitable for
Source Builder. The cleaner is format-agnostic: each supported format has a
parser that yields dialogue blocks, and the shared cleaning rules strip
subtitle noise from them.

Responsibility boundary: this module ONLY converts subtitle content into
clean dialogue text. It does NOT assign metadata, create canonical source
filenames, interact with the Production Manager, or create JSONL.

This module is GUI-free and deterministic so it can be unit tested.
"""

import re
from pathlib import Path

import sys

# Allow imports from the project root and the shared Common utility layer
# (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "Common"))

import paths
from sentence_split import split_line

# Output directory for cleaned text files.
INTAKE_DIR = paths.INTAKE

# Markup / positioning noise removed from cue text.
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_POSITIONING_RE = re.compile(r"\{\\(an|pos|a|fad|fade)\d*\}")
_COLOR_TAG_RE = re.compile(r"\{\\c&H[0-9A-Fa-f]+&?\}")
_NEWLINE_TAG_RE = re.compile(r"\{\\n\}")


class CleanError(Exception):
    """Raised when a subtitle file cannot be cleaned."""


class SubtitleParser:
    """Base parser interface. Subclasses parse a format into dialogue blocks."""

    format_name = "base"

    def parse(self, text):
        raise NotImplementedError

    def _clean_cue_text(self, cue):
        """Apply shared cleaning rules to a single dialogue cue."""
        cue = _NEWLINE_TAG_RE.sub("", cue)
        cue = _POSITIONING_RE.sub("", cue)
        cue = _COLOR_TAG_RE.sub("", cue)
        cue = _HTML_TAG_RE.sub("", cue)
        cue = cue.replace("\r", "")
        lines = [line.strip() for line in cue.split("\n")]
        lines = [line for line in lines if line]
        return "\n".join(lines)


class SrtParser(SubtitleParser):
    """Parser for SubRip (.srt) files."""

    format_name = "srt"

    def parse(self, text):
        blocks = _split_srt_blocks(text)
        cues = []
        for block in blocks:
            cue = self._cue_from_block(block)
            if cue is not None:
                cues.append(cue)
        return cues

    def _cue_from_block(self, block):
        lines = block.split("\n")
        if not lines:
            return None
        # Skip an optional leading sequence number.
        if _SRT_INDEX_RE.match(lines[0].strip()):
            lines = lines[1:]
        if not lines:
            return None
        # Skip the timestamp line.
        if _SRT_TIMESTAMP_RE.search(lines[0]):
            lines = lines[1:]
        cue = "\n".join(lines)
        return self._clean_cue_text(cue)


class VttParser(SubtitleParser):
    """Parser for WebVTT (.vtt) files."""

    format_name = "vtt"

    def parse(self, text):
        text = text.replace("\ufeff", "")
        lines = text.split("\n")
        # Drop leading blank lines.
        while lines and lines[0].strip() == "":
            lines.pop(0)
        # Drop the WebVTT header block: the WEBVTT line plus every
        # metadata line after it (X-TIMESTAMP-MAP, NOTE, STYLE, REGION,
        # custom X-* headers, ...) up to the first blank line, which ends
        # the header per the WebVTT spec. The skip also stops at a cue
        # timestamp, so a malformed file with no blank line after the
        # header cannot lose its first cue.
        if lines and lines[0].strip().startswith("WEBVTT"):
            lines.pop(0)
            while lines:
                stripped = lines[0].strip()
                if stripped == "" or _VTT_TIMESTAMP_RE.match(stripped):
                    break
                lines.pop(0)
        return self._parse_cues(lines)

    def _parse_cues(self, lines):
        cues = []
        buffer = []
        i = 0
        n = len(lines)
        while i < n:
            stripped = lines[i].strip()
            if _VTT_TIMESTAMP_RE.match(stripped):
                # A timestamp line: flush any pending cue, start a new one.
                cue = self._clean_cue_text("\n".join(buffer))
                if cue:
                    cues.append(cue)
                buffer = []
                i += 1
                continue
            if stripped == "":
                # Blank line separates cues; flush pending text.
                cue = self._clean_cue_text("\n".join(buffer))
                if cue:
                    cues.append(cue)
                buffer = []
                i += 1
                continue
            if not buffer and _VTT_BLOCK_START_RE.match(stripped):
                # A WebVTT block construct (NOTE comment or STYLE block)
                # between cues: skip to the next blank line, which ends it.
                i += 1
                while i < n and lines[i].strip() != "":
                    i += 1
                continue
            # Skip a bare sequence number that precedes a cue.
            if _SRT_INDEX_RE.match(stripped) and not buffer:
                i += 1
                continue
            buffer.append(lines[i])
            i += 1
        cue = self._clean_cue_text("\n".join(buffer))
        if cue:
            cues.append(cue)
        return cues


_SRT_INDEX_RE = re.compile(r"^\d+$")
_SRT_TIMESTAMP_RE = re.compile(
    r"^\s*\d{1,2}:\d{2}:\d{2}[,.]\d{1,3}\s*-->")
# WebVTT timestamps use HH:MM:SS.mmm (hours optional); cue settings may
# follow the arrow.
_VTT_TIMESTAMP_RE = re.compile(
    r"^\d{1,2}:\d{2}(:\d{2})?\.\d{3}\s*-->\s*"
    r"\d{1,2}:\d{2}(:\d{2})?\.\d{3}")

# WebVTT block constructs that appear between cues: a NOTE comment line
# (optionally followed by comment text) or a STYLE block keyword on its
# own line. Both run to the next blank line and are not dialogue.
_VTT_BLOCK_START_RE = re.compile(r"^(NOTE(?: |$)|STYLE$)")


def _split_srt_blocks(text):
    """Split SRT text into blocks separated by blank lines."""
    text = text.replace("\r", "")
    blocks = []
    current = []
    for line in text.split("\n"):
        if line.strip() == "":
            if current:
                blocks.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


# ============================================================
# Format registry
# ============================================================

PARSERS = {
    "srt": SrtParser,
    "vtt": VttParser,
}


def supported_formats():
    """Return the list of supported subtitle formats."""
    return sorted(PARSERS)


def detect_format(path):
    """
    Detect the subtitle format from a file's extension.

    Returns a format name (e.g. "srt") or raises CleanError for unknown
    extensions.
    """
    suffix = Path(path).suffix.lower().lstrip(".")
    if suffix not in PARSERS:
        raise CleanError(
            f"unsupported subtitle format: {suffix or '(none)'}")
    return suffix


def clean_text(content, fmt):
    """
    Clean subtitle content into dialogue text (single string).

    Each cue's full text is split at sentence-final punctuation
    boundaries (。！？), so a cue containing two sentences becomes two
    separate cues, exactly matching the deterministic parser's sentence
    splitting. A single sentence that wraps across display lines within
    one cue stays one piece: only whitespace around a split boundary is
    removed, never newlines embedded inside an un-split sentence, and
    pieces that are empty after stripping are dropped.

    Input: content (str), fmt (str: "srt" or "vtt").
    Output: cleaned dialogue text with cues joined by blank lines.
    """
    if not isinstance(content, str):
        raise CleanError("subtitle content must be text")
    if fmt not in PARSERS:
        raise CleanError(f"unsupported subtitle format: {fmt}")
    parser = PARSERS[fmt]()
    cues = parser.parse(content)
    sentences = []
    for cue in cues:
        for piece in split_line(cue):
            piece = piece.strip()
            if piece:
                sentences.append(piece)
    return "\n\n".join(sentences)


def clean_file(path):
    """
    Clean a subtitle file into dialogue text.

    Input: path (str or Path).
    Output: (format_name, cleaned_text).
    """
    path = Path(path)
    fmt = detect_format(path)
    try:
        content = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise CleanError(f"cannot read file: {path}: {exc}") from exc
    return fmt, clean_text(content, fmt)


# ============================================================
# Output filename
# ============================================================

def output_filename(input_path):
    """
    Generate the clean text output filename for an input subtitle file.

    Preserves the original base name and changes the extension to .txt.
    """
    return Path(input_path).stem + ".txt"


def output_path(input_path, output_dir=None):
    """Return the full output path under Intake\\ (or a custom directory)."""
    directory = Path(output_dir) if output_dir else INTAKE_DIR
    return directory / output_filename(input_path)


def save_clean_text(input_path, cleaned_text, output_dir=None):
    """
    Write cleaned text to Intake\\<original_stem>.txt (atomic write).

    Returns the output path written.
    """
    target = output_path(input_path, output_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as file:
        file.write(cleaned_text)
        file.flush()
        import os
        os.fsync(file.fileno())
    temp.replace(target)
    return target


__all__ = [
    "INTAKE_DIR",
    "CleanError",
    "SrtParser",
    "VttParser",
    "PARSERS",
    "supported_formats",
    "detect_format",
    "clean_text",
    "clean_file",
    "output_filename",
    "output_path",
    "save_clean_text",
]
