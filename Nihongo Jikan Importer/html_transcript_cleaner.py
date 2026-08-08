#!/usr/bin/env python3
"""
html_transcript_cleaner.py

Japanese Corpus Pipeline - Nihongo Jikan HTML transcript cleaner.

Converts Nihongo Jikan HTML transcript files into clean text files suitable
for Source Builder. The extraction rule (verified exhaustively across the
whole transcript corpus, not guessed):

    - every real transcript sentence is a BARE <p>...</p> tag (no
      attributes); a bare <p> block contains only plain text plus
      <ruby>/<rt> markup,
    - any <p> WITH an attribute, and the entire scraped-page "Copyright
      Info" widget (wrapper tags <details>/<summary>/<svg>/<div>/<span>/<a>
      plus attributed <p class="..."> paragraphs), is widget noise and is
      discarded entirely,
    - kanji inside a bare <p> carries furigana via
      <ruby>BASE<rt>READING</rt></ruby>; only BASE is kept (readings are
      discarded by Owner decision),
    - HTML entities (&amp;, &quot;, &#x27;, ...) are unescaped to their
      literal characters.

The cleaner reuses Common/sentence_split.py's split_line for the same
sentence-boundary rule the other cleaners apply, and joins utterances with
blank lines the same way Subtitle Importer/cleaner.py's clean_text() does,
matching the Corpus Builder's reconstruction contract.

Responsibility boundary: this module ONLY converts HTML transcript content
into clean dialogue text. It does NOT assign metadata, create canonical
source filenames, interact with the Production Manager, or create JSONL.

This module is GUI-free and deterministic so it can be unit tested.
"""

import html
import re
import sys
from pathlib import Path

# Allow imports from the project root and the shared Common utility layer
# (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "Common"))

from sentence_split import split_line


class CleanError(Exception):
    """Raised when an HTML transcript file cannot be cleaned."""


# A bare <p> tag (no attributes). Attributed <p class="..."> paragraphs are
# scraped-page widget noise and never match.
_BARE_P_RE = re.compile(r"<p\s*>(.*?)</p>", re.DOTALL | re.IGNORECASE)
# <ruby>BASE<rt>READING</rt></ruby> -> BASE (furigana reading discarded).
_RUBY_RE = re.compile(
    r"<ruby>(.*?)<rt>.*?</rt></ruby>", re.DOTALL | re.IGNORECASE)
# Any remaining HTML tag.
_HTML_TAG_RE = re.compile(r"<[^>]+>")


class HtmlTranscriptParser:
    """Parser for Nihongo Jikan HTML transcript files."""

    format_name = "html"

    def parse(self, text):
        """Extract one utterance per bare <p>...</p> block."""
        utterances = []
        for block in _BARE_P_RE.findall(text or ""):
            utterance = self._clean_block(block)
            if utterance:
                utterances.append(utterance)
        return utterances

    def _clean_block(self, block):
        """Clean one bare <p> block's inner HTML to utterance text."""
        block = _RUBY_RE.sub(r"\1", block)
        block = _HTML_TAG_RE.sub("", block)
        block = html.unescape(block)
        block = block.replace("\r", "")
        lines = [line.strip() for line in block.split("\n")]
        lines = [line for line in lines if line]
        return "\n".join(lines)


def clean_text(content):
    """
    Clean Nihongo Jikan HTML transcript content into dialogue text.

    Each bare <p>...</p> block is one utterance; its text is split at
    sentence-final punctuation boundaries (。！？) via split_line, so a
    block containing two sentences becomes two separate entries, exactly
    matching the deterministic parser's sentence splitting. Entries that
    are empty after stripping are dropped; entries are joined by blank
    lines.

    Input: content (str).
    Output: cleaned dialogue text with utterances joined by blank lines.
    """
    if not isinstance(content, str):
        raise CleanError("HTML transcript content must be text")
    parser = HtmlTranscriptParser()
    utterances = parser.parse(content)
    sentences = []
    for utterance in utterances:
        for piece in split_line(utterance):
            piece = piece.strip()
            if piece:
                sentences.append(piece)
    return "\n\n".join(sentences)


def clean_file(path):
    """
    Clean an HTML transcript file into dialogue text.

    Input: path (str or Path).
    Output: (format_name, cleaned_text).
    """
    path = Path(path)
    try:
        content = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise CleanError(f"cannot read file: {path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise CleanError(f"file is not UTF-8 text: {path}: {exc}") from exc
    return HtmlTranscriptParser.format_name, clean_text(content)


__all__ = [
    "CleanError",
    "HtmlTranscriptParser",
    "clean_text",
    "clean_file",
]
