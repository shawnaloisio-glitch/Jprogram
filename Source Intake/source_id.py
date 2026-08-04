#!/usr/bin/env python3
"""
source_id.py

Japanese Corpus Pipeline - Source Intake (utility layer)

Slug creation, sequence handling, and deterministic source_id creation.

Format: {type}_{slug}_{sequence}

Examples:
    sub_sousou-no-frieren_ep001
    pod_conteppei_ep051
    manga_one-piece_ch012

Deterministic: identical inputs produce identical output.
This module does not read files, hash files, or write artifacts.
"""

import re
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))


def slugify(title):
    """
    Convert a title into a normalized slug.

    Lowercases the input, replaces every run of non-word characters
    (including underscores) with a single hyphen, and strips leading or
    trailing hyphens. Unicode letters and digits (including Japanese)
    are preserved.

    Input: title (string).
    Output: normalized slug (string).
    """
    text = str(title).strip().lower()
    text = re.sub(r"[\W_]+", "-", text)
    return text.strip("-")


def format_sequence(sequence, prefix, width=3):
    """
    Format a numeric sequence with a prefix and zero-padding.

    Input:
        sequence: non-negative integer.
        prefix: string (e.g., "ep", "ch").
        width: zero-pad width (default 3).

    Output:
        String (e.g., "ep001", "ch012").
    """
    return f"{prefix}{sequence:0{width}d}"


def generate(source_type, slug, sequence=None):
    """
    Create a deterministic source_id.

    Input:
        source_type: string (e.g., "sub", "pod", "manga").
        slug: normalized slug (see slugify).
        sequence: optional sequence token (see format_sequence).

    Output:
        "{source_type}_{slug}" or "{source_type}_{slug}_{sequence}".
    """
    base = f"{source_type}_{slug}"
    if sequence is None:
        return base
    return f"{base}_{sequence}"


__all__ = ["slugify", "format_sequence", "generate"]
