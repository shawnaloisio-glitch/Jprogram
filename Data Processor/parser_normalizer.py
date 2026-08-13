#!/usr/bin/env python3
"""
parser_normalizer.py

Japanese Corpus Pipeline - Parser Output Canonicalizer.

Deterministic pipeline stage that canonicalizes parser output BEFORE
Response Validation. The cleaned source transcript is the authoritative
source of sentence text.

This stage:
    - replaces each parser sentence's "text" with the canonical sentence
      text derived from the cleaned source,
    - recalculates word character spans from the authoritative surfaces
      matched against the canonical sentence text,
    - recalculates chunk text as verbatim slices of the canonical sentence,
    - verifies that the canonical sentence texts reconstruct the clean
      source text exactly (integrity gate).

It performs NO statistics, NO interpretation, and NO repair beyond the
deterministic canonicalization described above. It never guesses and never
silently repairs an unmatchable surface.

Frozen architecture note: the Corpus Builder previously owned these
transformations. They have been moved here so the Response Validator
validates canonical records (sentence text already restored from the clean
source) rather than the raw parser text.
"""

CANONICAL_LINE_SEPARATOR = "\n\n"


class ParserNormalizerError(Exception):
    """Raised when parser output cannot be canonicalized."""


CorpusBuilderError = ParserNormalizerError


def _is_int(value):
    """True for real integers (bools are not integers for our schema)."""
    return isinstance(value, int) and not isinstance(value, bool)


# ============================================================
# Canonicalization stage functions (deterministic)
# ============================================================

def recompute_character_spans(sentence):
    """
    Deterministically recompute char_start/char_end for every word.

    Uses only the preserved sentence text and the ordered word surfaces.
    Parser-provided char_start/char_end values are ignored completely.

    Guarantees for every word:
        sentence_text[char_start:char_end] == surface

    The algorithm walks the ordered surfaces left to right and, for each
    surface, finds the first occurrence in the sentence text at or after
    the previous surface's end. Because canonicalization has replaced the
    sentence text with the authoritative clean-source text, this greedy
    match is exact for any surface that occurs in order in the canonical
    sentence.

    Raises:
        ParserNormalizerError if the reconstruction is impossible (a surface
        cannot be matched in order, or the input is structurally invalid).
        It never guesses, never silently repairs, and never continues
        with incorrect spans.

    All other sentence fields are preserved unchanged.
    """
    if not isinstance(sentence, dict):
        raise CorpusBuilderError("sentence must be a dict")

    text = sentence.get("text")
    if not isinstance(text, str) or not text:
        raise CorpusBuilderError("sentence text must be a non-empty string")

    words = sentence.get("words")
    if not isinstance(words, list):
        raise CorpusBuilderError("sentence words must be a list")

    new_words = []
    pos = 0

    for wi, word in enumerate(words):
        if not isinstance(word, list) or len(word) != 5:
            raise CorpusBuilderError(
                f"words[{wi}] must have exactly 5 columns "
                f"[index, surface, lexical, char_start, char_end]."
            )

        index, surface, lexical, _old_start, _old_end = word

        if not isinstance(surface, str) or not surface:
            raise CorpusBuilderError(
                f"words[{wi}] surface must be a non-empty string."
            )

        start = text.find(surface, pos)
        if start == -1:
            raise CorpusBuilderError(
                f"words[{wi}] surface {surface!r} cannot be matched in the "
                f"sentence text after position {pos} (impossible reconstruction)."
            )

        end = start + len(surface)
        new_words.append([index, surface, lexical, start, end])
        pos = end

    result = dict(sentence)
    result["words"] = new_words
    return result


def recompute_chunk_text(sentence):
    """
    Deterministically rebuild canonical chunk text from the preserved
    sentence text and the recomputed character spans in the word records.

    The parser-provided chunk text is ignored completely.

    For every chunk:
        first_word = words[start_word]
        last_word  = words[end_word - 1]
        chunk_text = sentence_text[
            first_word.char_start : last_word.char_end
        ]

    This preserves exact whitespace and punctuation between the words,
    so the canonical chunk text is a verbatim slice of the original
    source evidence.

    Preserves the chunk index, start_word, and end_word; replaces only
    the chunk text field.

    Raises:
        ParserNormalizerError if the chunk is structurally invalid, the
        indices are invalid (out of range, start_word > end_word, or an
        empty chunk), the referenced words do not exist, or their char
        spans are missing or invalid. It never guesses, never silently
        repairs, and never continues with an invalid chunk.

    Returns a new sentence object with only the chunk list replaced.
    """
    if not isinstance(sentence, dict):
        raise CorpusBuilderError("sentence must be a dict")

    text = sentence.get("text")
    if not isinstance(text, str) or not text:
        raise CorpusBuilderError("sentence text must be a non-empty string")

    words = sentence.get("words")
    chunks = sentence.get("chunks")
    if not isinstance(words, list):
        raise CorpusBuilderError("sentence words must be a list")
    if not isinstance(chunks, list):
        raise CorpusBuilderError("sentence chunks must be a list")

    word_count = len(words)
    text_len = len(text)
    new_chunks = []

    for ci, chunk in enumerate(chunks):
        if not isinstance(chunk, list) or len(chunk) != 4:
            raise CorpusBuilderError(
                f"chunks[{ci}] must have exactly 4 columns "
                f"[index, text, start_word, end_word]."
            )

        index, _old_text, start_word, end_word = chunk

        if not (isinstance(start_word, int) and not isinstance(start_word, bool)):
            raise CorpusBuilderError(
                f"chunks[{ci}] start_word must be an integer."
            )
        if not (isinstance(end_word, int) and not isinstance(end_word, bool)):
            raise CorpusBuilderError(
                f"chunks[{ci}] end_word must be an integer."
            )
        if start_word < 0 or end_word > word_count:
            raise CorpusBuilderError(
                f"chunks[{ci}] start_word/end_word out of range "
                f"({start_word}, {end_word}) for {word_count} words."
            )
        if start_word > end_word:
            raise CorpusBuilderError(
                f"chunks[{ci}] start_word > end_word "
                f"({start_word} > {end_word})."
            )
        if start_word == end_word:
            raise CorpusBuilderError(
                f"chunks[{ci}] empty chunk (start_word == end_word) "
                f"cannot be reconstructed."
            )

        first_word = words[start_word]
        last_word = words[end_word - 1]

        for wi, word in ((start_word, first_word), (end_word - 1, last_word)):
            if not isinstance(word, list) or len(word) != 5:
                raise CorpusBuilderError(
                    f"words[{wi}] must have exactly 5 columns "
                    f"[index, surface, lexical, char_start, char_end]."
                )

        first_start = first_word[3]
        first_end = first_word[4]
        last_start = last_word[3]
        last_end = last_word[4]

        for label, value in (
            ("char_start", first_start), ("char_end", first_end),
        ):
            if not (isinstance(value, int) and not isinstance(value, bool)):
                raise CorpusBuilderError(
                    f"words[{start_word}] {label} must be an integer."
                )
        for label, value in (
            ("char_start", last_start), ("char_end", last_end),
        ):
            if not (isinstance(value, int) and not isinstance(value, bool)):
                raise CorpusBuilderError(
                    f"words[{end_word - 1}] {label} must be an integer."
                )

        if first_start < 0 or first_end < first_start or first_end > text_len:
            raise CorpusBuilderError(
                f"words[{start_word}] char span invalid "
                f"({first_start}, {first_end}) for text length {text_len}."
            )
        if last_start < 0 or last_end < last_start or last_end > text_len:
            raise CorpusBuilderError(
                f"words[{end_word - 1}] char span invalid "
                f"({last_start}, {last_end}) for text length {text_len}."
            )
        if text[first_start:first_end] != first_word[1]:
            raise CorpusBuilderError(
                f"words[{start_word}] char span does not match its surface."
            )
        if text[last_start:last_end] != last_word[1]:
            raise CorpusBuilderError(
                f"words[{end_word - 1}] char span does not match its surface."
            )
        if first_start > last_end:
            raise CorpusBuilderError(
                f"chunks[{ci}] first word starts after the last word ends."
            )

        chunk_text = text[first_start:last_end]
        new_chunks.append([index, chunk_text, start_word, end_word])

    result = dict(sentence)
    result["chunks"] = new_chunks
    return result


def _is_section_marker_line(line):
    """True if the line is a section/header marker such as ===== Episode 51 =====."""
    stripped = line.strip()
    return stripped.startswith("=====") and stripped.endswith("=====")


def _expected_content(expected_text):
    """
    Build the expected reconstruction content from the clean source text.

    Deterministically removes known section/header marker lines and strips
    a trailing file-terminator newline. The clean text separates content
    lines with the canonical line separator ("\\n\\n").
    """
    if not expected_text:
        return ""
    parts = expected_text.split(CANONICAL_LINE_SEPARATOR)
    kept = [part for part in parts if not _is_section_marker_line(part)]
    content = CANONICAL_LINE_SEPARATOR.join(kept)
    if content.endswith("\n"):
        content = content[:-1]
    return content


def canonical_sentence_texts(expected_text):
    """
    Return the canonical sentence texts from the clean source text.

    The cleaned transcript is the authoritative source of sentence text.
    Sentences are the non-marker content lines split by the canonical line
    separator ("\\n\\n"). This is deterministic and never trusts the parser.

    Input: expected_text (str) - the cleaned source text.
    Output: list of canonical sentence strings.
    """
    if not expected_text:
        return []
    parts = expected_text.split(CANONICAL_LINE_SEPARATOR)
    kept = [part for part in parts if not _is_section_marker_line(part)]
    if kept and kept[-1].endswith("\n"):
        kept[-1] = kept[-1][:-1]
    # Drop empty blocks: split_line("") yields zero sentences in
    # split_sentences(), most commonly for the trailing block left when
    # Job Builder cuts a source at an internal "\n\n" boundary.
    return [part for part in kept if part != ""]


def restore_sentence_text(records, canonical_texts):
    """
    Move sentence text ownership from the parser to the canonicalizer.

    Replaces every record's "text" with the canonical sentence text from
    the cleaned source, then recomputes word character spans and chunk
    text against that canonical sentence. The parser's own "text" field is
    ignored.

    Offset verification is preserved: word surfaces must exactly partition
    the canonical sentence and recomputed char spans must match. If a
    surface cannot be matched in the canonical text, ParserNormalizerError
    is raised. Offsets are never silently repaired.

    Input:
        records (list of dict) - sentence records from the parser output.
        canonical_texts (list of str) - canonical sentence texts, one per
            record, in order.

    Output: records with authoritative "text" and recomputed spans.

    Raises:
        ParserNormalizerError if the record count does not match the
        canonical sentence count, or if a word surface cannot be matched in
        the canonical sentence.
    """
    if len(canonical_texts) != len(records):
        raise CorpusBuilderError(
            f"canonical sentence count {len(canonical_texts)} does not "
            f"match record count {len(records)}"
        )

    restored = []
    for record, canonical_text in zip(records, canonical_texts):
        sentence = dict(record)
        sentence["text"] = canonical_text
        sentence = recompute_character_spans(sentence)
        sentence = recompute_chunk_text(sentence)
        restored.append(sentence)
    return restored


def _first_diff_index(first, second):
    """Return the index of the first differing character (or the shorter length)."""
    limit = min(len(first), len(second))
    for i in range(limit):
        if first[i] != second[i]:
            return i
    return limit


def verify_source_reconstruction(sentences, expected_text):
    """
    Deterministically verify that the canonical sentence texts, in order,
    reconstruct the original clean source text exactly.

    This is a mandatory integrity gate before canonical corpus output.
    It detects dropped characters, added characters, reordered sentences,
    and changed whitespace or punctuation.

    Algorithm:
        1. Build the expected content: the source text with known
           section/header marker lines deterministically removed and a
           trailing file-terminator newline stripped.
        2. Build the actual reconstruction: the sentence texts joined in
           order with the canonical line separator ("\\n\\n").
        3. Require an EXACT string match. Whitespace and punctuation are
           evidence and are never normalized away.

    Raises:
        ParserNormalizerError if the source text is missing/empty, a
        sentence record is invalid, or the reconstruction differs. The
        error reports the first differing character position and
        surrounding context. The stage does NOT repair or continue on
        failure.

    Returns:
        {"verified": True, "sentence_count": N, "source_length": N}
    """
    if not isinstance(sentences, list):
        raise CorpusBuilderError("sentences must be a list")
    if not isinstance(expected_text, str):
        raise CorpusBuilderError("expected source text must be a string")
    if not expected_text.strip():
        raise CorpusBuilderError("expected source text is empty")

    actual_texts = []
    for si, sentence in enumerate(sentences):
        if not isinstance(sentence, dict):
            raise CorpusBuilderError(f"sentences[{si}] must be a dict")
        text = sentence.get("text")
        if not isinstance(text, str):
            raise CorpusBuilderError(f"sentences[{si}] text must be a string")
        actual_texts.append(text)

    expected = _expected_content(expected_text)
    actual = CANONICAL_LINE_SEPARATOR.join(actual_texts)

    if actual != expected:
        index = _first_diff_index(actual, expected)
        expected_snippet = expected[max(0, index - 20):index + 20]
        actual_snippet = actual[max(0, index - 20):index + 20]
        raise CorpusBuilderError(
            f"source reconstruction failed at character {index}: "
            f"expected ...{expected_snippet!r}... but reconstructed "
            f"...{actual_snippet!r}..."
        )

    return {
        "verified": True,
        "sentence_count": len(sentences),
        "source_length": len(expected),
    }


# ============================================================
# Public entry point
# ============================================================

def canonicalize(parser_data, cleaned_source_text):
    """
    Canonicalize a parser response against the cleaned source text.

    This is the public entry point of the Parser Output Canonicalizer
    stage. It runs BEFORE Response Validation.

    Steps:
        1. Derive the canonical sentence texts from the cleaned source.
        2. Replace each parser sentence's "text" with its canonical text
           and recompute character spans and chunk text.
        3. Verify that the canonical sentence texts reconstruct the clean
           source text exactly.

    Input:
        parser_data (dict) - the parsed parser output
            ({"source_name": str, "job_number": int,
              "sentences": [sentence, ...]}).
        cleaned_source_text (str) - the authoritative cleaned source text
            for the job.

    Output: a new parser output dict with canonicalized sentences
        ({"source_name": ..., "job_number": ..., "sentences": [...]}).

    Raises:
        ParserNormalizerError if the input is structurally invalid, the
        canonical sentence count does not match the record count, a word
        surface cannot be matched in the canonical text, or source
        reconstruction fails. It never silently repairs.
    """
    if not isinstance(parser_data, dict):
        raise CorpusBuilderError("parser_data must be a dict")

    sentences = parser_data.get("sentences")
    if not isinstance(sentences, list):
        raise CorpusBuilderError("parser_data must contain a 'sentences' list")

    canonical_texts = canonical_sentence_texts(cleaned_source_text)
    restored = restore_sentence_text(sentences, canonical_texts)
    verify_source_reconstruction(restored, cleaned_source_text)

    result = dict(parser_data)
    result["sentences"] = restored
    return result


__all__ = [
    "CANONICAL_LINE_SEPARATOR",
    "ParserNormalizerError",
    "CorpusBuilderError",
    "canonicalize",
    "canonical_sentence_texts",
    "restore_sentence_text",
    "recompute_character_spans",
    "recompute_chunk_text",
    "verify_source_reconstruction",
    "_expected_content",
    "_is_section_marker_line",
    "_first_diff_index",
]
