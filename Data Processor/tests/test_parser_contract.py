#!/usr/bin/env python3
"""
test_parser_contract.py

Deterministic tests that the parser instructions (parser_prompt.md and
PARSER_OUTPUT_SPEC.md) match the authoritative downstream schema used by
the Response Validator and Corpus Builder: positional arrays for word,
chunk, and expression records, and exact source_id identity echo.

Run:
    python "Data Processor/tests/test_parser_contract.py"
"""

import pathlib
import re
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
PROMPTS = PROJECT_ROOT / "Prompts"
SPEC = PROJECT_ROOT / "PARSER_OUTPUT_SPEC.md"
DATA_PROCESSOR = PROJECT_ROOT / "Data Processor"
sys.path.insert(0, str(DATA_PROCESSOR))

import response_validator as rv


def prompt_text():
    return (PROMPTS / "parser_prompt.md").read_text(encoding="utf-8")


def spec_text():
    return SPEC.read_text(encoding="utf-8")


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("word record: instructions match validator 5-column array")
def _():
    for text, label in ((prompt_text(), "parser_prompt"),
                        (spec_text(), "PARSER_OUTPUT_SPEC")):
        check(f"{label} specifies word array",
              "[index, surface, lexical, char_start, char_end]" in text
              or "[index, surface, lexical, char_start, char_end]" in text)
        check(f"{label} word example is an array",
              "[0, " in text and '"食べました"' in text)
    # Validator expectation.
    check("validator word columns",
          "5 columns [index, surface, lexical, char_start, char_end]"
          in open_rv_source())


@test("chunk record: instructions match validator 4-column array")
def _():
    for text, label in ((prompt_text(), "parser_prompt"),
                        (spec_text(), "PARSER_OUTPUT_SPEC")):
        check(f"{label} specifies chunk array",
              "[index, text, start_word, end_word]" in text)
    check("validator chunk columns",
          "4 columns [index, text, start_word, end_word]"
          in open_rv_source())


@test("expression record: instructions match validator 5-column array")
def _():
    for text, label in ((prompt_text(), "parser_prompt"),
                        (spec_text(), "PARSER_OUTPUT_SPEC")):
        check(f"{label} specifies expression array",
              "[index, surface, start_word, end_word, pattern]" in text)
    check("validator expression columns",
          "5 columns [index, surface, start_word, end_word, pattern]"
          in open_rv_source())


@test("no object-format word examples remain in instructions")
def _():
    for text, label in ((prompt_text(), "parser_prompt"),
                        (spec_text(), "PARSER_OUTPUT_SPEC")):
        # A word record as a JSON object would contain "index": with a
        # following "surface": on its own line within braces. Ensure the
        # positional array form is used instead.
        bad_objects = re.findall(
            r'\{\s*"index":\s*integer,\s*"surface"', text)
        check(f"{label} no word object example", not bad_objects)
        check(f"{label} uses array examples", '"words": [\n  [0,' in text
              or '"words": [\n        [0,' in text or "[0, \"食べました\"" in text)


@test("no object-format chunk/expression examples remain")
def _():
    for text, label in ((prompt_text(), "parser_prompt"),
                        (spec_text(), "PARSER_OUTPUT_SPEC")):
        bad_chunk = re.findall(r'\{\s*"index":\s*integer,\s*"text"', text)
        check(f"{label} no chunk object example", not bad_chunk)
        bad_expr = re.findall(r'\{\s*"index":\s*integer,\s*"surface"', text)
        check(f"{label} no expression object example", not bad_expr)


@test("source_id identity instruction is explicit")
def _():
    p = prompt_text()
    check("prompt requires copying source_id exactly",
          "copy it EXACTLY" in p and "source_id" in p)
    check("prompt forbids inferring a title",
          "do not infer" in p.lower() and "title" in p.lower())
    s = spec_text()
    check("spec requires exact source_id echo",
          "must not infer or generate a human-readable title" in s)
    check("spec top-level uses source_name carrying source_id",
          '"source_name": string' in s and 'source_id' in s)


@test("sentence text preservation instruction present")
def _():
    p = prompt_text()
    check("prompt forbids modifying sentence text",
          "byte-for-byte" in p and "SENTENCE TEXT PRESERVATION" in p)
    check("prompt forbids inserting spaces", "insert or remove spaces" in p
          or "insert spaces" in p)
    check("prompt example ことが", "ことが" in p and "こと が" in p)
    s = spec_text()
    check("spec forbids normalization", "never insert or remove spaces" in s
          or "insert or remove spaces" in s)
    check("spec example ことが", "ことが" in s and "こと が" in s)


@test("validator still validates positional arrays as valid")
def _():
    # A valid response in the authoritative array format must pass. The
    # validator requires a top-level source_name field whose value equals
    # the request's source_id.
    response = {
        "source_name": "pod_x",
        "job_number": 1,
        "sentences": [{
            "sentence_index": 0,
            "text": "なぜか という と",
            "words": [
                [0, "なぜか", "なぜか", 0, 3],
                [1, "という", "という", 4, 7],
                [2, "と", "と", 8, 9],
            ],
            "chunks": [[0, "なぜか という と", 0, 3]],
            "expressions": [[0, "なぜか という と", 0, 3, "なぜかというと"]],
        }],
    }
    result = rv.validate_response(
        response, expected_source_name="pod_x", expected_job_number=1)
    check("valid response passes", result["valid"] is True, str(result["errors"]))


@test("validator rejects object-format words")
def _():
    response = {
        "source_name": "pod_x",
        "job_number": 1,
        "sentences": [{
            "sentence_index": 0,
            "text": "なぜか",
            "words": [
                {"index": 0, "surface": "なぜか", "lexical": "なぜか",
                 "char_start": 0, "char_end": 3},
            ],
            "chunks": [],
            "expressions": [],
        }],
    }
    result = rv.validate_response(response)
    check("object words rejected", result["valid"] is False)


@test("response_validator tests remain unchanged")
def _():
    source = pathlib.Path(DATA_PROCESSOR / "response_validator.py").read_text(
        encoding="utf-8")
    check("validator still requires 5-column words",
          "5 columns [index, surface, lexical, char_start, char_end]" in source)
    check("validator still requires 4-column chunks",
          "4 columns [index, text, start_word, end_word]" in source)
    check("validator still requires 5-column expressions",
          "5 columns [index, surface, start_word, end_word, pattern]" in source)


def open_rv_source():
    return pathlib.Path(DATA_PROCESSOR / "response_validator.py").read_text(
        encoding="utf-8")


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
