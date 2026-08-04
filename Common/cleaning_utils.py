#!/usr/bin/env python3
"""
cleaning_utils.py

Japanese Corpus Pipeline - shared cleaning utilities (mechanical only).

Deterministic text transformation primitives extracted from the
original cleaner logic. They receive data and return data/statistics.

These utilities must NOT know:
    - source types
    - cleaning jobs
    - source registry
    - cleaning profiles
    - GUI
    - pipeline stages

They contain only mechanical operations. All linguistic rules, Japanese
token handling, normalization, transliteration, and furigana logic remain
in the cleaner implementations.

This module imports only the standard library.
"""

import re


# ============================================================
# BOM handling
# ============================================================

def strip_bom(text):
    """
    Remove a leading UTF-8 BOM character if present.

    Input: text (str).
    Output: (cleaned_text, removed_bool) where removed_bool is True
    when a BOM was removed. No other normalization is performed.
    """
    if text.startswith("\ufeff"):
        return text[1:], True
    return text, False


# ============================================================
# Line trimming
# ============================================================

def trim_lines(lines):
    """
    Trim each line with str.strip().

    Input: lines (list of str).
    Output: (lines, count) where count is the number of lines whose
    value changed. Line ordering is preserved.
    """
    cleaned = []
    count = 0
    for line in lines:
        trimmed = line.strip()
        if trimmed != line:
            count += 1
        cleaned.append(trimmed)
    return cleaned, count


# ============================================================
# Blank line collapsing
# ============================================================

def collapse_blank_lines(lines):
    """
    Collapse consecutive blank lines into a single blank line.

    Input: lines (list of str).
    Output: (lines, count) where count is the number of blank lines
    removed. Intentional single blank separators are preserved and
    ordering is deterministic.
    """
    cleaned = []
    count = 0
    previous_blank = False
    for line in lines:
        if line == "":
            if previous_blank:
                count += 1
                continue
            previous_blank = True
            cleaned.append("")
        else:
            previous_blank = False
            cleaned.append(line)
    return cleaned, count


# ============================================================
# Repeated ASCII space collapsing
# ============================================================

def collapse_ascii_spaces(line):
    """
    Collapse runs of two or more ASCII spaces (U+0020) into one.

    Input: line (str).
    Output: (line, count) where count is the number of runs collapsed.

    Only ASCII spaces are collapsed. Japanese full-width space
    (U+3000), Japanese text, and punctuation are left unchanged.
    """
    count = len(re.findall(r" {2,}", line))
    line = re.sub(r" {2,}", " ", line)
    return line, count


# ============================================================
# Output joining
# ============================================================

def join_clean_lines(lines):
    """
    Join cleaned lines into a single output string.

    Matches the original cleaner behavior:
        - join lines with "\n"
        - remove trailing whitespace from the joined text
        - end with exactly one final newline

    Input: lines (list of str).
    Output: str.
    """
    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "strip_bom",
    "trim_lines",
    "collapse_blank_lines",
    "collapse_ascii_spaces",
    "join_clean_lines",
]
