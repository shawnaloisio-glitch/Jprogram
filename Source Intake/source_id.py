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

COUNTER_ID_PATTERN = re.compile(r"^[a-z]{2,}_(\d+)$")


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


def generate_counter_id(prefix, counter, width=6):
    """
    Create a global-counter source_id (DECIDED 2026-08-14: replaces
    title-slug identity project-wide -- avoids the real title-slug
    collision bug confirmed in production, e.g. two titles differing only
    in trailing punctuation collapsing to the same slug and silently
    overwriting each other's Registry/corpus entry, see TODO.md). This is
    the sole authoritative identity field; every other registry field is
    metadata. Ported from MandarinCorpus's source_id.py (2026-08-14 design).

    Input:
        prefix: string (e.g. "ja" for this project -- single-language
            installation, self-describing).
        counter: non-negative integer, assigned by next_counter() --
            global across the whole corpus, never per-creator/per-collection
            and never reused.
        width: zero-pad width (default 6 -- ample headroom; this project
            alone already exceeds 3,000 real sources).

    Output: "{prefix}_{counter:0{width}d}", e.g. "ja_000001".
    """
    return f"{prefix}_{counter:0{width}d}"


def next_counter(registry_dir, prefix):
    """
    Return the next global counter value for a source_id prefix.

    Scans registry_dir for existing "{prefix}_<digits>.json" filenames and
    returns the highest counter found, plus one (1 if none exist). A live
    scan every call, not a persisted counter -- deterministic and
    recoverable from filesystem state alone, same convention as
    next_auto_sequence(). Gaps (e.g. a manually deleted registry entry) are
    never filled; the result is always max + 1.

    NOT SAFE FOR CONCURRENT CALLS across processes (the scan-then-write is
    not atomic) -- callers registering in parallel must retry on a
    collision at the write step (see Source Builder/handoff.py's
    register_standalone_source / register_collection_source).

    Input: registry_dir (Path), prefix (string, e.g. "ja").
    Output: int (the next counter value, always >= 1).
    """
    directory = Path(registry_dir)
    if not directory.is_dir():
        return 1
    highest = 0
    for path in directory.glob(f"{prefix}_*.json"):
        match = COUNTER_ID_PATTERN.match(path.stem)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


__all__ = [
    "slugify", "format_sequence", "generate",
    "generate_counter_id", "next_counter",
]
