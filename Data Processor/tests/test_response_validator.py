#!/usr/bin/env python3
"""
test_response_validator.py

Deterministic unit tests for the Response Validator (response_validator.py),
focused on the punctuation-aware evidence comparisons backed by _normalize():
the sentence-reconstruction partition check, the chunk-text check, and the
expression-surface check.

TASK 13 added wave-dash (U+301C / U+FF5E), interpunct (U+30FB),
horizontal-bar (U+2015), and em-dash (U+2014) to _PUNCTUATION so that
genuinely correct parser output containing those separators no longer fails
the partition check with a fatal WORD_SURFACE_PARTITION_MISMATCH, while
genuinely malformed output still does.

Run:
    python "Data Processor/tests/test_response_validator.py"
"""

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_PROCESSOR = PROJECT_ROOT / "Data Processor"
sys.path.insert(0, str(DATA_PROCESSOR))

import response_validator as rv


def response(text, words, chunks=None, expressions=None,
             source_name="pod_x", job_number=1):
    return {
        "source_name": source_name,
        "job_number": job_number,
        "sentences": [{
            "sentence_index": 0,
            "text": text,
            "words": words,
            "chunks": chunks if chunks is not None else [],
            "expressions": expressions if expressions is not None else [],
        }],
    }


def validate(text, words, chunks=None, expressions=None):
    return rv.validate_response(
        response(text, words, chunks, expressions),
        expected_source_name="pod_x", expected_job_number=1)


def has_error(result, code):
    return any(e["code"] == code for e in result["errors"])


def fatal_error(result, code):
    return any(e["code"] == code and e["fatal"] for e in result["errors"])


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("wave dash U+301C is a separator: correct response passes")
def _():
    # Mirrors the parser_prompt worked example "〜と思います": the wave
    # dash separates the words and must not appear in any word surface.
    # Pre-fix this sentence produced a fatal WORD_SURFACE_PARTITION_MISMATCH.
    text = "そう〜と思います。"
    words = [
        [0, "そう", "そう", 0, 2],
        [1, "と思います", "と思う", 3, 8],
    ]
    chunks = [[0, "そう〜と思います。", 0, 2]]
    result = validate(text, words, chunks)
    check("valid", result["valid"] is True, str(result["errors"]))
    check("no partition mismatch",
          not has_error(result, rv.WORD_SURFACE_PARTITION_MISMATCH),
          str(result["errors"]))
    check("no chunk text mismatch",
          not has_error(result, rv.CHUNK_TEXT_MISMATCH),
          str(result["errors"]))
    check("no char span errors",
          not has_error(result, rv.WORD_CHAR_SPAN_MISMATCH),
          str(result["errors"]))


@test("fullwidth tilde U+FF5E is a separator: correct response passes")
def _():
    text = "はい～と思います。"
    words = [
        [0, "はい", "はい", 0, 2],
        [1, "と思います", "と思う", 3, 8],
    ]
    result = validate(text, words)
    check("valid", result["valid"] is True, str(result["errors"]))
    check("no partition mismatch",
          not has_error(result, rv.WORD_SURFACE_PARTITION_MISMATCH),
          str(result["errors"]))


@test("interpunct U+30FB is a separator: correct response passes")
def _():
    text = "カタカナ・ひらがな。"
    words = [
        [0, "カタカナ", "カタカナ", 0, 4],
        [1, "ひらがな", "ひらがな", 5, 9],
    ]
    expressions = [[0, "カタカナ・ひらがな", 0, 2, "カタカナ・ひらがな"]]
    result = validate(text, words, expressions=expressions)
    check("valid", result["valid"] is True, str(result["errors"]))
    check("no partition mismatch",
          not has_error(result, rv.WORD_SURFACE_PARTITION_MISMATCH),
          str(result["errors"]))
    check("no expression surface mismatch",
          not has_error(result, rv.EXPRESSION_SURFACE_MISMATCH),
          str(result["errors"]))


@test("em dash U+2014 is a separator: correct response passes")
def _():
    text = "それは—本当です。"
    words = [
        [0, "それは", "それは", 0, 3],
        [1, "本当", "本当", 4, 6],
        [2, "です", "です", 6, 8],
    ]
    result = validate(text, words)
    check("valid", result["valid"] is True, str(result["errors"]))
    check("no partition mismatch",
          not has_error(result, rv.WORD_SURFACE_PARTITION_MISMATCH),
          str(result["errors"]))


@test("horizontal bar U+2015 is a separator: correct response passes")
def _():
    text = "結果は―良好です。"
    words = [
        [0, "結果は", "結果", 0, 3],
        [1, "良好", "良好", 4, 6],
        [2, "です", "です", 6, 8],
    ]
    result = validate(text, words)
    check("valid", result["valid"] is True, str(result["errors"]))
    check("no partition mismatch",
          not has_error(result, rv.WORD_SURFACE_PARTITION_MISMATCH),
          str(result["errors"]))


@test("malformed surfaces still fail with fatal WORD_SURFACE_PARTITION_MISMATCH")
def _():
    # The word surfaces contain an extra ね that no separator-normalization
    # can remove: the sentence cannot be reconstructed, so the check must
    # still fire. The fix only extended what counts as a separator.
    text = "これはテストです。"
    words = [
        [0, "これは", "これ", 0, 3],
        [1, "テスト", "テスト", 3, 6],
        [2, "です", "です", 6, 8],
        [3, "ね", "ね", 8, 9],
    ]
    result = validate(text, words)
    check("invalid", result["valid"] is False)
    check("fatal partition mismatch",
          fatal_error(result, rv.WORD_SURFACE_PARTITION_MISMATCH),
          str(result["errors"]))


@test("new separators are members of _PUNCTUATION and are normalized away")
def _():
    for ch, label in (
            ("\u301C", "wave dash U+301C"),
            ("\uFF5E", "fullwidth tilde U+FF5E"),
            ("\u30FB", "interpunct U+30FB"),
            ("\u2015", "horizontal bar U+2015"),
            ("\u2014", "em dash U+2014")):
        check(f"{label} in _PUNCTUATION", ch in rv._PUNCTUATION)
    check("normalize strips every new separator",
          rv._normalize("\u301C\uFF5E\u30FB\u2015\u2014") == "")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    passed = 0
    failed = 0
    failures = []
    for name, fn in TESTS:
        try:
            fn()
            passed += 1
            print(f"  PASS  {name}")
        except AssertionError as ex:
            failed += 1
            failures.append((name, str(ex)))
            print(f"  FAIL  {name}: {ex}")
        except Exception as ex:
            failed += 1
            failures.append((name, f"{type(ex).__name__}: {ex}"))
            print(f"  FAIL  {name}: {type(ex).__name__}: {ex}")

    print()
    print(f"Tests: {len(TESTS)}  Passed: {passed}  Failed: {failed}")
    if failures:
        print("Failures:")
        for name, detail in failures:
            print(f"  - {name}: {detail}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
