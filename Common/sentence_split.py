#!/usr/bin/env python3
"""
sentence_split.py

Japanese Corpus Pipeline - shared sentence-splitting utility (mechanical only).

A pure, dependency-free function that splits one content line at
sentence-final punctuation boundaries, implementing exactly the sentence
splitting rule the deterministic parser applies. Both the Transcript
Cleaner and the Subtitle Importer reuse this rule so their "one input
line/cue equals one sentence" assumption can never drift out of
agreement with what the parser actually does.

Rule:
    - Sentence-final punctuation (。！？) marks a boundary and stays
      attached to the preceding sentence.
    - Consecutive sentence-final punctuation characters coalesce into
      one boundary.
    - A line with no such punctuation is one whole sentence.

This module is pure and imports only the standard library (nothing at
all, in fact). It contains only mechanical operations.
"""

SENTENCE_FINAL_PUNCT = frozenset("。！？")


# ============================================================
# Sentence splitting
# ============================================================

def split_line(line):
    """
    Split one content line at sentence-final punctuation boundaries.

    Input: line (str).
    Output: list of str.

    An empty line returns an empty list. A line with no sentence-final
    punctuation returns a single-item list containing the whole line.
    Sentence-final punctuation marks a boundary and stays attached to
    the preceding sentence. Consecutive sentence-final punctuation
    characters coalesce into one boundary.
    """
    if not line:
        return []
    if not any(ch in SENTENCE_FINAL_PUNCT for ch in line):
        return [line]
    result = []
    start = 0
    i = 0
    n = len(line)
    while i < n:
        if line[i] in SENTENCE_FINAL_PUNCT:
            j = i
            while j < n and line[j] in SENTENCE_FINAL_PUNCT:
                j += 1
            result.append(line[start:j])
            start = j
            i = j
        else:
            i += 1
    if start < n:
        result.append(line[start:])
    return result


__all__ = [
    "SENTENCE_FINAL_PUNCT",
    "split_line",
]
