#!/usr/bin/env python3
"""
test_frequency_analyzer.py

Deterministic tests for frequency_analyzer.

Run:
    python Analysis/tests/test_frequency_analyzer.py
"""

import copy
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ANALYSIS = PROJECT_ROOT / "Analysis"
sys.path.insert(0, str(ANALYSIS))

import frequency_analyzer as fa


def make_record(sentence_id, source, section, words):
    """Build a canonical-style record with the given words."""
    return {
        "text": " ".join(w[1] for w in words),
        "ids": {"sentence_id": sentence_id},
        "provenance": {
            "source": source,
            "source_file": f"{source}.clean.txt",
            "job_number": 1,
            "model": "deepseek-v4-flash",
            "prompt_version": "1.0",
            "sentence_id": sentence_id,
            "sentence_position": sentence_id,
        },
        "section": section,
        "words": words,
        "chunks": [],
        "expressions": [],
    }


def word(index, surface, lexical):
    return [index, surface, lexical, 0, len(surface)]


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


def freq_of(result, key):
    return result["frequency"].get(key)


@test("basic word counting")
def _():
    records = [make_record(0, "src1", "sec1", [word(0, "コーヒー", "コーヒー")])]
    result = fa.analyze(records)
    item = freq_of(result, "コーヒー")
    check("item exists", item is not None)
    check("occurrences", item["occurrences"] == 1)
    check("sentences", item["sentences"] == 1)
    check("sources", item["sources"] == 1)
    check("sections", item["sections"] == 1)
    check("summary", result["summary"]["total_occurrences"] == 1)


@test("multiple occurrences in one sentence")
def _():
    records = [make_record(0, "src1", "sec1", [
        word(0, "食べました", "食べる"),
        word(1, "食べない", "食べる"),
    ])]
    result = fa.analyze(records)
    item = freq_of(result, "食べる")
    check("occurrences", item["occurrences"] == 2)
    check("one sentence", item["sentences"] == 1)


@test("sentence coverage counting")
def _():
    records = [
        make_record(0, "src1", "sec1", [word(0, "テスト", "テスト")]),
        make_record(1, "src1", "sec1", [word(0, "テスト", "テスト")]),
    ]
    result = fa.analyze(records)
    item = freq_of(result, "テスト")
    check("occurrences", item["occurrences"] == 2)
    check("sentences", item["sentences"] == 2)
    check("sources", item["sources"] == 1)


@test("source coverage counting")
def _():
    records = [
        make_record(0, "src1", "sec1", [word(0, "テスト", "テスト")]),
        make_record(0, "src2", "sec1", [word(0, "テスト", "テスト")]),
    ]
    result = fa.analyze(records)
    item = freq_of(result, "テスト")
    check("occurrences", item["occurrences"] == 2)
    check("sources", item["sources"] == 2)
    check("sentences", item["sentences"] == 2)  # distinct (source, sentence_id)


@test("section coverage counting")
def _():
    records = [
        make_record(0, "src1", "episode-1", [word(0, "テスト", "テスト")]),
        make_record(1, "src1", "episode-2", [word(0, "テスト", "テスト")]),
    ]
    result = fa.analyze(records)
    item = freq_of(result, "テスト")
    check("sections", item["sections"] == 2)


@test("multiple surfaces sharing a lexical item")
def _():
    records = [make_record(0, "src1", "sec1", [
        word(0, "食べました", "食べる"),
        word(1, "食べない", "食べる"),
        word(2, "食べて", "食べる"),
    ])]
    result = fa.analyze(records)
    item = freq_of(result, "食べる")
    check("surfaces", item["surfaces"] == {
        "食べました": 1, "食べない": 1, "食べて": 1})
    check("occurrences", item["occurrences"] == 3)


@test("repeated runs produce identical output")
def _():
    records = [
        make_record(0, "src1", "sec1", [word(0, "コーヒー", "コーヒー")]),
        make_record(1, "src1", "sec1", [word(0, "テスト", "テスト")]),
    ]
    one = fa.analyze(records)
    two = fa.analyze(records)
    check("identical", one == two)


@test("no corpus records modified")
def _():
    records = [
        make_record(0, "src1", "sec1", [word(0, "コーヒー", "コーヒー")]),
        make_record(1, "src2", "sec2", [word(0, "テスト", "テスト")]),
    ]
    snapshot = copy.deepcopy(records)
    fa.analyze(records)
    check("records unchanged", records == snapshot)


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
