#!/usr/bin/env python3
"""
import_material.py

Japanese Corpus Pipeline - Source Builder import material conversion.

Converts external source material into the plain text format Source Builder
expects. Import is a Sources function: it gathers material into the source
creation workflow. It does NOT process material, create registry entries,
create cleaning jobs, or start the pipeline.

Supported source formats:
- subtitle file   (reuses the Subtitle Importer cleaner for .srt/.vtt)
- clean text

This module is GUI-free and deterministic so it can be unit tested. It does
not duplicate parsing logic already owned by the Subtitle Importer.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Subtitle Importer"))


class ImportError(Exception):
    """Raised when imported material cannot be converted."""


# Source format identifiers shown to the user.
FORMAT_SUBTITLE = "subtitle"
FORMAT_CLEAN_TEXT = "clean_text"

SOURCE_FORMATS = (
    FORMAT_SUBTITLE,
    FORMAT_CLEAN_TEXT,
)

# Display labels for the import dialog.
FORMAT_LABELS = {
    FORMAT_SUBTITLE: "Subtitle File",
    FORMAT_CLEAN_TEXT: "Clean Text",
}


def _read_text(path):
    """Read a file as UTF-8 text (BOM tolerated)."""
    try:
        return Path(path).read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportError(
            f"file is not UTF-8 text: {path}: {exc}") from exc
    except OSError as exc:
        raise ImportError(f"cannot read file: {path}: {exc}") from exc


def _normalize_lines(text):
    """Normalize line endings and trim trailing whitespace per line."""
    lines = []
    for line in text.splitlines():
        line = line.rstrip()
        lines.append(line)
    # Drop leading/trailing blank lines.
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def convert_text(content, source_format):
    """
    Convert clean text content for a non-subtitle source format.

    Clean text is normalized: line-ending normalization only. No linguistic
    or parsing logic is applied.

    Input: content (str), source_format (one of SOURCE_FORMATS except
        subtitle).
    Output: normalized text (str).
    """
    if source_format == FORMAT_SUBTITLE:
        raise ImportError(
            "use convert_file for subtitle material")
    if source_format not in SOURCE_FORMATS:
        raise ImportError(f"unknown source format: {source_format}")
    return _normalize_lines(content)


def convert_file(path, source_format):
    """
    Convert one file into the plain text Source Builder expects.

    Subtitle files reuse the Subtitle Importer cleaner (SRT/VTT -> dialogue
    text). Clean text reads the file and normalizes line endings.

    Input: path (str or Path), source_format (one of SOURCE_FORMATS).
    Output: converted text (str).
    Raises: ImportError on unsupported/unknown format or read failure.
    """
    if source_format == FORMAT_SUBTITLE:
        import cleaner as subtitle_cleaner
        try:
            _fmt, cleaned = subtitle_cleaner.clean_file(path)
        except subtitle_cleaner.CleanError as exc:
            raise ImportError(f"cannot convert subtitle: {exc}") from exc
        if not cleaned.strip():
            raise ImportError(f"subtitle file is empty: {path}")
        return cleaned + "\n" if not cleaned.endswith("\n") else cleaned

    if source_format not in SOURCE_FORMATS:
        raise ImportError(f"unknown source format: {source_format}")
    content = _read_text(path)
    if not content.strip():
        raise ImportError(f"file is empty: {path}")
    return convert_text(content, source_format)


def convert_files(paths, source_format):
    """
    Convert multiple files and join the results.

    Each file is converted independently; converted texts are joined with a
    blank line separator so they become one body of source material.

    Input: paths (list of str|Path), source_format (one of SOURCE_FORMATS).
    Output: combined text (str).
    """
    parts = []
    for path in paths:
        converted = convert_file(path, source_format)
        parts.append(converted.rstrip("\n"))
    return "\n\n".join(parts) + "\n"


__all__ = [
    "FORMAT_SUBTITLE",
    "FORMAT_CLEAN_TEXT",
    "SOURCE_FORMATS",
    "FORMAT_LABELS",
    "ImportError",
    "convert_text",
    "convert_file",
    "convert_files",
]
