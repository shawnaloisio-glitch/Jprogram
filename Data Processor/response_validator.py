#!/usr/bin/env python3
"""
response_validator.py

Japanese Corpus Pipeline - Response Validator

Deterministic gate for ONE DeepSeek parser response (ONE job).

It determines whether a parser response is structurally valid and
whether it preserves the source evidence sufficiently for the
Corpus Builder to accept it. It never repairs parser output.

Frozen architecture (TASK 20):

The LLM's character offsets are known to be unreliable on Japanese.
They are validated and reported, but they are NOT authoritative.
The ordered word surfaces are authoritative because they exactly
partition each sentence. The Corpus Builder deterministically
recomputes character spans and chunk text.

The validator is a gate, not a repair system. It normalizes nothing
and corrects nothing. It only validates and reports.

Result structure:

{
    "valid": true/false,
    "errors": [
        {
            "code": str,
            "message": str,
            "sentence_index": int or null,
            "record_type": str or null,
            "record_index": int or null,
            "fatal": true/false
        }
    ],
    "warnings": [ { "code": str, "message": str, ... } ],
    "summary": { ... counts ... }
}

Char-span mismatches are reported as errors with fatal=false because
the Corpus Builder deterministically recomputes them from the
authoritative ordered word surfaces. Every other problem is fatal.
"""

import json
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

PROGRAM_NAME = "Response Validator"

# ------------------------------------------------------------
# Error codes
# ------------------------------------------------------------

INVALID_JSON = "INVALID_JSON"
INVALID_TOP_LEVEL_STRUCTURE = "INVALID_TOP_LEVEL_STRUCTURE"
MISSING_TOP_LEVEL_FIELD = "MISSING_TOP_LEVEL_FIELD"
INVALID_TOP_LEVEL_TYPE = "INVALID_TOP_LEVEL_TYPE"
SOURCE_IDENTITY_MISMATCH = "SOURCE_IDENTITY_MISMATCH"
INVALID_SENTENCE_RECORD = "INVALID_SENTENCE_RECORD"
INVALID_SENTENCE_INDEX = "INVALID_SENTENCE_INDEX"
EMPTY_SENTENCE = "EMPTY_SENTENCE"
INVALID_SENTENCE_FIELD = "INVALID_SENTENCE_FIELD"
INVALID_WORD_RECORD = "INVALID_WORD_RECORD"
INVALID_WORD_INDEX = "INVALID_WORD_INDEX"
WORD_CHAR_SPAN_MISMATCH = "WORD_CHAR_SPAN_MISMATCH"
WORD_SURFACE_PARTITION_MISMATCH = "WORD_SURFACE_PARTITION_MISMATCH"
INVALID_CHUNK_RECORD = "INVALID_CHUNK_RECORD"
INVALID_CHUNK_INDEX = "INVALID_CHUNK_INDEX"
INVALID_CHUNK_SPAN = "INVALID_CHUNK_SPAN"
CHUNK_OVERLAP = "CHUNK_OVERLAP"
CHUNK_TEXT_MISMATCH = "CHUNK_TEXT_MISMATCH"
INVALID_EXPRESSION_RECORD = "INVALID_EXPRESSION_RECORD"
INVALID_EXPRESSION_INDEX = "INVALID_EXPRESSION_INDEX"
INVALID_EXPRESSION_SPAN = "INVALID_EXPRESSION_SPAN"
EXPRESSION_SURFACE_MISMATCH = "EXPRESSION_SURFACE_MISMATCH"

# Warning codes
SEGMENTATION_WARNING = "SEGMENTATION_WARNING"
DUPLICATE_EXPRESSION_WARNING = "DUPLICATE_EXPRESSION_WARNING"


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _is_int(value):
    """True for real integers (bools are not integers for our schema)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _add_error(errors, code, message, sentence_index=None,
               record_type=None, record_index=None, fatal=True):
    errors.append({
        "code": code,
        "message": message,
        "sentence_index": sentence_index,
        "record_type": record_type,
        "record_index": record_index,
        "fatal": fatal,
    })


def _add_warning(warnings, code, message, sentence_index=None,
                 record_type=None, record_index=None):
    warnings.append({
        "code": code,
        "message": message,
        "sentence_index": sentence_index,
        "record_type": record_type,
        "record_index": record_index,
    })


# Punctuation treated as separators in evidence comparisons. Word units
# never include the punctuation that separates them (PARSER_OUTPUT_SPEC §3);
# punctuation preservation in sentence text is enforced by the canonicalizer's
# source-reconstruction gate, not by word-surface partition.
_PUNCTUATION = frozenset("。、，．！？!?…；：,.;:()（）「」『』\u301C\uFF5E\u30FB\u2015\u2014")

# A separator is whitespace or punctuation; both are excluded from word
# surfaces and must be ignored when comparing surfaces against sentence text.
_SEPARATOR = lambda ch: ch.isspace() or ch in _PUNCTUATION


def _normalize(text):
    """Remove whitespace and punctuation. Used for evidence comparisons only.

    Word surfaces never include the spaces or punctuation that separate
    them; the canonicalizer preserves punctuation in the authoritative
    sentence text, so the partition comparison compares surfaces against
    the separator-free sentence content.
    """
    return "".join(ch for ch in text if not _SEPARATOR(ch))


def _build_result(errors, warnings, summary):
    fatal_count = sum(1 for e in errors if e.get("fatal"))
    summary["fatal_errors"] = fatal_count
    summary["total_errors"] = len(errors)
    summary["total_warnings"] = len(warnings)
    return {
        "valid": fatal_count == 0,
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
    }


# ------------------------------------------------------------
# Word validation
# ------------------------------------------------------------

def _validate_words(text, words, sentence_index, errors, summary):
    """
    Validate word records and return the list of surfaces in order.

    char-span problems are non-fatal because the Corpus Builder
    recomputes spans from the authoritative ordered surfaces.
    """
    surfaces = []
    prev_index = -1
    span_error_count = 0

    for wi, word in enumerate(words):
        if not isinstance(word, list) or len(word) != 5:
            _add_error(
                errors, INVALID_WORD_RECORD,
                f"sentence {sentence_index} words[{wi}] must have exactly "
                f"5 columns [index, surface, lexical, char_start, char_end].",
                sentence_index=sentence_index, record_type="word", record_index=wi)
            continue

        idx, surface, lexical, char_start, char_end = word

        if not _is_int(idx):
            _add_error(
                errors, INVALID_WORD_RECORD,
                f"sentence {sentence_index} words[{wi}] index must be an integer.",
                sentence_index=sentence_index, record_type="word", record_index=wi)
        elif idx < 0:
            _add_error(
                errors, INVALID_WORD_INDEX,
                f"sentence {sentence_index} words[{wi}] index must be 0-based (>= 0).",
                sentence_index=sentence_index, record_type="word", record_index=wi)
        elif idx <= prev_index:
            _add_error(
                errors, INVALID_WORD_INDEX,
                f"sentence {sentence_index} words[{wi}] index is not strictly increasing.",
                sentence_index=sentence_index, record_type="word", record_index=wi)
        if _is_int(idx) and idx >= 0:
            prev_index = idx

        if not isinstance(surface, str):
            _add_error(
                errors, INVALID_WORD_RECORD,
                f"sentence {sentence_index} words[{wi}] surface must be a string.",
                sentence_index=sentence_index, record_type="word", record_index=wi)
        else:
            surfaces.append(surface)

        if lexical is not None and not isinstance(lexical, str):
            _add_error(
                errors, INVALID_WORD_RECORD,
                f"sentence {sentence_index} words[{wi}] lexical must be a string or null.",
                sentence_index=sentence_index, record_type="word", record_index=wi)

        if not _is_int(char_start) or not _is_int(char_end):
            _add_error(
                errors, INVALID_WORD_RECORD,
                f"sentence {sentence_index} words[{wi}] char_start/char_end "
                f"must be integers.",
                sentence_index=sentence_index, record_type="word", record_index=wi)
            continue

        span_ok = (char_start >= 0
                   and char_end >= char_start
                   and char_end <= len(text))
        if not span_ok:
            _add_error(
                errors, WORD_CHAR_SPAN_MISMATCH,
                f"sentence {sentence_index} words[{wi}] char span out of range "
                f"({char_start}, {char_end}) for sentence length {len(text)}.",
                sentence_index=sentence_index, record_type="word", record_index=wi,
                fatal=False)
            span_error_count += 1
        elif isinstance(surface, str) and text[char_start:char_end] != surface:
            _add_error(
                errors, WORD_CHAR_SPAN_MISMATCH,
                f"sentence {sentence_index} words[{wi}] text[char_start:char_end] "
                f"does not equal surface.",
                sentence_index=sentence_index, record_type="word", record_index=wi,
                fatal=False)
            span_error_count += 1

    summary["char_span_errors"] += span_error_count
    return surfaces


# ------------------------------------------------------------
# Word-surface partition validation
# ------------------------------------------------------------

def _validate_partition(text, surfaces, sentence_index, errors, warnings, summary):
    """
    The ordered word surfaces must reconstruct the sentence's
    non-whitespace, non-punctuation content characters in order. This is
    the critical evidence-preservation test. Word units never include the
    spaces or punctuation that separate them (PARSER_OUTPUT_SPEC §3);
    punctuation preservation in sentence text is enforced by the
    canonicalizer's source-reconstruction gate. Span errors and partition
    errors are deliberately kept separate.
    """
    expected = _normalize(text)
    actual = "".join(_normalize(s) for s in surfaces)
    if actual != expected:
        _add_error(
            errors, WORD_SURFACE_PARTITION_MISMATCH,
            f"sentence {sentence_index} ordered word surfaces do not reconstruct "
            f"the sentence text (whitespace/punctuation-normalized comparison).",
            sentence_index=sentence_index)
        summary["partition_mismatches"] += 1
        return

    # Advisory segmentation check for whitespace-delimited sources.
    if " " in text:
        joined = " ".join(surfaces)
        if joined != text:
            _add_warning(
                warnings, SEGMENTATION_WARNING,
                f"sentence {sentence_index} surfaces joined by single spaces do "
                f"not reproduce the sentence text; segmentation may differ from "
                f"the source whitespace-delimited units.",
                sentence_index=sentence_index)


# ------------------------------------------------------------
# Chunk validation
# ------------------------------------------------------------

def _validate_chunks(words, chunks, sentence_index, errors):
    """
    Validate chunk records. Because LLM char offsets are unreliable,
    chunk text is compared against the word-span surfaces, not the
    supplied char offsets.
    """
    word_count = len(words)
    surface_by_word = [
        w[1] if (isinstance(w, list) and len(w) == 5 and isinstance(w[1], str))
        else "" for w in words
    ]
    prev_end = -1

    for ci, chunk in enumerate(chunks):
        if not isinstance(chunk, list) or len(chunk) != 4:
            _add_error(
                errors, INVALID_CHUNK_RECORD,
                f"sentence {sentence_index} chunks[{ci}] must have exactly "
                f"4 columns [index, text, start_word, end_word].",
                sentence_index=sentence_index, record_type="chunk", record_index=ci)
            continue

        idx, ctext, start_word, end_word = chunk

        if not _is_int(idx):
            _add_error(
                errors, INVALID_CHUNK_RECORD,
                f"sentence {sentence_index} chunks[{ci}] index must be an integer.",
                sentence_index=sentence_index, record_type="chunk", record_index=ci)
        elif idx < 0:
            _add_error(
                errors, INVALID_CHUNK_INDEX,
                f"sentence {sentence_index} chunks[{ci}] index must be 0-based (>= 0).",
                sentence_index=sentence_index, record_type="chunk", record_index=ci)

        if not isinstance(ctext, str):
            _add_error(
                errors, INVALID_CHUNK_RECORD,
                f"sentence {sentence_index} chunks[{ci}] text must be a string.",
                sentence_index=sentence_index, record_type="chunk", record_index=ci)

        if not _is_int(start_word) or not _is_int(end_word):
            _add_error(
                errors, INVALID_CHUNK_RECORD,
                f"sentence {sentence_index} chunks[{ci}] start_word/end_word "
                f"must be integers.",
                sentence_index=sentence_index, record_type="chunk", record_index=ci)
            continue

        if start_word < 0 or end_word > word_count or start_word >= end_word:
            _add_error(
                errors, INVALID_CHUNK_SPAN,
                f"sentence {sentence_index} chunks[{ci}] invalid word span "
                f"({start_word}, {end_word}) for {word_count} words.",
                sentence_index=sentence_index, record_type="chunk", record_index=ci)
            continue

        if prev_end >= 0 and start_word < prev_end:
            _add_error(
                errors, CHUNK_OVERLAP,
                f"sentence {sentence_index} chunks[{ci}] overlaps the previous chunk.",
                sentence_index=sentence_index, record_type="chunk", record_index=ci)
        prev_end = end_word

        if isinstance(ctext, str):
            span_text = "".join(surface_by_word[start_word:end_word])
            if _normalize(ctext) != _normalize(span_text):
                _add_error(
                    errors, CHUNK_TEXT_MISMATCH,
                    f"sentence {sentence_index} chunks[{ci}] text does not match "
                    f"the surface text of its word span.",
                    sentence_index=sentence_index, record_type="chunk", record_index=ci)


# ------------------------------------------------------------
# Expression validation
# ------------------------------------------------------------

def _validate_expressions(words, expressions, sentence_index, errors, warnings):
    """
    Validate expression records. Expressions are an overlapping
    evidence layer and are NOT chunks: no flat-partition rule applies.
    """
    word_count = len(words)
    surface_by_word = [
        w[1] if (isinstance(w, list) and len(w) == 5 and isinstance(w[1], str))
        else "" for w in words
    ]
    spans = []

    for ei, expr in enumerate(expressions):
        if not isinstance(expr, list) or len(expr) != 5:
            _add_error(
                errors, INVALID_EXPRESSION_RECORD,
                f"sentence {sentence_index} expressions[{ei}] must have exactly "
                f"5 columns [index, surface, start_word, end_word, pattern].",
                sentence_index=sentence_index, record_type="expression", record_index=ei)
            continue

        idx, surface, start_word, end_word, pattern = expr

        if not _is_int(idx):
            _add_error(
                errors, INVALID_EXPRESSION_RECORD,
                f"sentence {sentence_index} expressions[{ei}] index must be an integer.",
                sentence_index=sentence_index, record_type="expression", record_index=ei)
        elif idx < 0:
            _add_error(
                errors, INVALID_EXPRESSION_INDEX,
                f"sentence {sentence_index} expressions[{ei}] index must be 0-based (>= 0).",
                sentence_index=sentence_index, record_type="expression", record_index=ei)

        if not isinstance(surface, str):
            _add_error(
                errors, INVALID_EXPRESSION_RECORD,
                f"sentence {sentence_index} expressions[{ei}] surface must be a string.",
                sentence_index=sentence_index, record_type="expression", record_index=ei)

        if pattern is not None and not isinstance(pattern, str):
            _add_error(
                errors, INVALID_EXPRESSION_RECORD,
                f"sentence {sentence_index} expressions[{ei}] pattern must be a string or null.",
                sentence_index=sentence_index, record_type="expression", record_index=ei)

        if not _is_int(start_word) or not _is_int(end_word):
            _add_error(
                errors, INVALID_EXPRESSION_RECORD,
                f"sentence {sentence_index} expressions[{ei}] start_word/end_word "
                f"must be integers.",
                sentence_index=sentence_index, record_type="expression", record_index=ei)
            continue

        if start_word < 0 or end_word > word_count or start_word >= end_word:
            _add_error(
                errors, INVALID_EXPRESSION_SPAN,
                f"sentence {sentence_index} expressions[{ei}] invalid word span "
                f"({start_word}, {end_word}) for {word_count} words.",
                sentence_index=sentence_index, record_type="expression", record_index=ei)
            continue

        if isinstance(surface, str):
            span_text = "".join(surface_by_word[start_word:end_word])
            if _normalize(surface) != _normalize(span_text):
                _add_error(
                    errors, EXPRESSION_SURFACE_MISMATCH,
                    f"sentence {sentence_index} expressions[{ei}] surface does not "
                    f"match the surface text of its word span.",
                    sentence_index=sentence_index, record_type="expression", record_index=ei)

        spans.append((ei, start_word, end_word, surface if isinstance(surface, str) else ""))

    # Obviously invalid duplicates (identical span and identical surface).
    # The longest-complete-expression rule is now enforced by
    # deterministic_parser.py's detect_expressions() via explicit overlap
    # resolution, not a prompt; only obvious duplicates are flagged, as
    # warnings.
    for i in range(len(spans)):
        for j in range(len(spans)):
            if i == j:
                continue
            ei, a, b, s_a = spans[i]
            ej, c, d, s_c = spans[j]
            if s_a and a == c and b == d and s_a == s_c:
                _add_warning(
                    warnings, DUPLICATE_EXPRESSION_WARNING,
                    f"sentence {sentence_index} expressions[{ei}] duplicates "
                    f"expressions[{ej}] (identical span and surface).",
                    sentence_index=sentence_index, record_type="expression",
                    record_index=ei)
                break


# ------------------------------------------------------------
# Sentence validation
# ------------------------------------------------------------

def _validate_sentence(sentence, position, prev_index, errors, warnings, summary):
    if not isinstance(sentence, dict):
        _add_error(
            errors, INVALID_SENTENCE_RECORD,
            f"sentences[{position}] is not an object.",
            sentence_index=position)
        return

    idx = sentence.get("sentence_index")
    report_index = idx if _is_int(idx) else position

    if not _is_int(idx):
        _add_error(
            errors, INVALID_SENTENCE_INDEX,
            f"sentences[{position}] sentence_index must be an integer.",
            sentence_index=position)
    else:
        if idx < 0:
            _add_error(
                errors, INVALID_SENTENCE_INDEX,
                f"sentences[{position}] sentence_index must be 0-based (>= 0).",
                sentence_index=report_index)
        if idx <= prev_index:
            _add_error(
                errors, INVALID_SENTENCE_INDEX,
                f"sentences[{position}] sentence_index is not strictly increasing.",
                sentence_index=report_index)

    text = sentence.get("text")
    if not isinstance(text, str):
        _add_error(
            errors, INVALID_SENTENCE_FIELD,
            f"sentences[{position}] text must be a string.",
            sentence_index=report_index)
        text = ""
    elif not text:
        _add_error(
            errors, EMPTY_SENTENCE,
            f"sentences[{position}] text is empty.",
            sentence_index=report_index)

    for field in ("words", "chunks", "expressions"):
        value = sentence.get(field)
        if not isinstance(value, list):
            _add_error(
                errors, INVALID_SENTENCE_FIELD,
                f"sentences[{position}] {field} must be an array.",
                sentence_index=report_index)
            return

    words = sentence["words"]
    chunks = sentence["chunks"]
    expressions = sentence["expressions"]

    summary["words"] += len(words)
    summary["chunks"] += len(chunks)
    summary["expressions"] += len(expressions)

    surfaces = _validate_words(text, words, report_index, errors, summary)
    _validate_partition(text, surfaces, report_index, errors, warnings, summary)
    _validate_chunks(words, chunks, report_index, errors)
    _validate_expressions(words, expressions, report_index, errors, warnings)


# ------------------------------------------------------------
# Top-level validation
# ------------------------------------------------------------

def validate_response(response, expected_source_name=None, expected_job_number=None):
    """
    Validate one parser response for one job.

    Args:
        response: JSON string or already-parsed Python object.
        expected_source_name: optional authoritative source name from the
            request metadata. The parser's echoed value is not authoritative.
        expected_job_number: optional authoritative job number.

    Returns:
        Deterministic result dictionary:
            valid, errors, warnings, summary
    """
    errors = []
    warnings = []
    summary = {
        "sentences": 0,
        "words": 0,
        "chunks": 0,
        "expressions": 0,
        "char_span_errors": 0,
        "partition_mismatches": 0,
        "identity_mismatches": 0,
    }

    if isinstance(response, str):
        try:
            data = json.loads(response)
        except (json.JSONDecodeError, ValueError) as ex:
            _add_error(
                errors, INVALID_JSON,
                f"Response is not valid JSON: {ex}")
            return _build_result(errors, warnings, summary)
    else:
        data = response

    if not isinstance(data, dict):
        _add_error(
            errors, INVALID_TOP_LEVEL_STRUCTURE,
            "Top-level value is not a JSON object.")
        return _build_result(errors, warnings, summary)

    for field in ("source_name", "job_number", "sentences"):
        if field not in data:
            _add_error(
                errors, MISSING_TOP_LEVEL_FIELD,
                f"Missing top-level field: {field}.")

    if "source_name" in data and not isinstance(data["source_name"], str):
        _add_error(
            errors, INVALID_TOP_LEVEL_TYPE,
            "source_name must be a string.")

    if "job_number" in data and not _is_int(data["job_number"]):
        _add_error(
            errors, INVALID_TOP_LEVEL_TYPE,
            "job_number must be an integer.")

    if "sentences" in data and not isinstance(data["sentences"], list):
        _add_error(
            errors, INVALID_TOP_LEVEL_TYPE,
            "sentences must be an array.")

    # Source identity. The request metadata is authoritative. The parser's
    # echoed values are reported as evidence; a mismatch is non-fatal because
    # the Corpus Builder uses the request metadata as the source of truth.
    if expected_source_name is not None and data.get("source_name") != expected_source_name:
        _add_error(
            errors, SOURCE_IDENTITY_MISMATCH,
            f"source_name '{data.get('source_name')}' does not match the "
            f"request metadata '{expected_source_name}'.",
            fatal=False)
        summary["identity_mismatches"] += 1

    if expected_job_number is not None and data.get("job_number") != expected_job_number:
        _add_error(
            errors, SOURCE_IDENTITY_MISMATCH,
            f"job_number {data.get('job_number')} does not match the "
            f"request metadata {expected_job_number}.",
            fatal=False)
        summary["identity_mismatches"] += 1

    sentences = data.get("sentences")
    if isinstance(sentences, list):
        summary["sentences"] = len(sentences)
        prev_index = -1
        for position, sentence in enumerate(sentences):
            _validate_sentence(sentence, position, prev_index, errors, warnings, summary)
            if isinstance(sentence, dict) and _is_int(sentence.get("sentence_index")):
                prev_index = sentence["sentence_index"]

    return _build_result(errors, warnings, summary)


# ------------------------------------------------------------
# Command-line entry point
# ------------------------------------------------------------

def main():
    """
    Validate a saved response file.

    Usage:
        python response_validator.py <response_file> [request_file]

    The request file supplies the authoritative source_name/job_number.
    """

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = sys.argv[1:]

    if not args:
        print(f"{PROGRAM_NAME}")
        print("Usage: python response_validator.py <response_file> [request_file]")
        return

    response_file = Path(args[0])
    if not response_file.is_file():
        print(f"ERROR: response file not found: {response_file}")
        return

    response = response_file.read_text(encoding="utf-8")

    expected_source_name = None
    expected_job_number = None

    if len(args) > 1:
        request_file = Path(args[1])
        if not request_file.is_file():
            print(f"ERROR: request file not found: {request_file}")
            return
        try:
            request = json.loads(request_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError) as ex:
            print(f"ERROR: request file is not valid JSON: {ex}")
            return
        expected_source_name = request.get("source_name")
        expected_job_number = request.get("job_number")

    result = validate_response(
        response,
        expected_source_name,
        expected_job_number,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
