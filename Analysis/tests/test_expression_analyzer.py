#!/usr/bin/env python3
"""
test_expression_analyzer.py

Deterministic tests for expression_analyzer.

Run:
    python Analysis/tests/test_expression_analyzer.py
"""

import copy
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ANALYSIS = PROJECT_ROOT / "Analysis"
sys.path.insert(0, str(ANALYSIS))

import expression_analyzer as ea


def make_record(sentence_id, source, section, word_count, expressions):
    """Build a canonical-style record with the given number of words."""
    words = [[i, f"w{i}", f"w{i}", i, i + 1] for i in range(word_count)]
    text = " ".join(w[1] for w in words)
    return {
        "text": text,
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
        "expressions": expressions,
    }


def expr(index, surface, start_word, end_word, pattern):
    return [index, surface, start_word, end_word, pattern]


def item_of(result, key):
    return result["expressions"].get(key)


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


def approx(actual, expected, tol=1e-9):
    return actual is not None and abs(actual - expected) < tol


@test("basic expression counting")
def _():
    records = [make_record(0, "src1", "sec1", 3,
                           [expr(0, "なぜかというと", 0, 3, "なぜかというと")])]
    result = ea.analyze(records)
    item = item_of(result, "なぜかというと")
    check("item exists", item is not None)
    check("occurrences", item["occurrences"] == 1)
    check("sentences", item["sentences"] == 1)
    check("sources", item["sources"] == 1)
    check("sections", item["sections"] == 1)


@test("multiple occurrences")
def _():
    records = [
        make_record(0, "src1", "sec1", 3,
                    [expr(0, "なぜかというと", 0, 3, "なぜかというと")]),
        make_record(1, "src1", "sec1", 3,
                    [expr(0, "なぜかというと", 0, 3, "なぜかというと")]),
    ]
    result = ea.analyze(records)
    item = item_of(result, "なぜかというと")
    check("occurrences", item["occurrences"] == 2)
    check("sentences", item["sentences"] == 2)


@test("surface variations sharing a pattern")
def _():
    records = [make_record(0, "src1", "sec1", 3, [
        expr(0, "なぜか という と", 0, 3, "なぜかというと"),
        expr(1, "なぜか というと", 0, 3, "なぜかというと"),
    ])]
    result = ea.analyze(records)
    item = item_of(result, "なぜかというと")
    check("grouped", item["occurrences"] == 2)
    check("surface breakdown", item["surfaces"] == {
        "なぜか という と": 1, "なぜか というと": 1})


@test("sentence/source/section coverage")
def _():
    records = [
        make_record(0, "src1", "episode-1", 2,
                    [expr(0, "p1", 0, 2, "PAT")]),
        make_record(1, "src1", "episode-2", 2,
                    [expr(0, "p1", 0, 2, "PAT")]),
        make_record(0, "src2", "episode-1", 2,
                    [expr(0, "p1", 0, 2, "PAT")]),
    ]
    result = ea.analyze(records)
    item = item_of(result, "PAT")
    check("occurrences", item["occurrences"] == 3)
    check("sentences", item["sentences"] == 3)
    check("sources", item["sources"] == 2)
    check("sections", item["sections"] == 3)


@test("word span tracking")
def _():
    records = [make_record(0, "src1", "sec1", 5,
                           [expr(0, "expr", 1, 4, "PAT")])]
    result = ea.analyze(records)
    item = item_of(result, "PAT")
    loc = item["locations"][0]
    check("start_word", loc["start_word"] == 1)
    check("end_word", loc["end_word"] == 4)
    check("sentence_id", loc["sentence_id"] == 0)
    check("source", loc["source"] == "src1")
    check("section", loc["section"] == "sec1")


@test("distribution calculations")
def _():
    # Two records, 3 words each; expression at start_word 1.
    records = [
        make_record(0, "src1", "sec1", 3,
                    [expr(0, "e1", 1, 3, "PAT")]),
        make_record(1, "src1", "sec1", 3,
                    [expr(0, "e1", 1, 3, "PAT")]),
    ]
    result = ea.analyze(records)
    item = item_of(result, "PAT")
    # word indices: record0 starts at 0 -> 0+1=1; record1 starts at 3 -> 3+1=4.
    wd = item["word_distance"]
    check("word gap 3", wd["gap_count"] == 1 and wd["min"] == 3
          and wd["max"] == 3)
    sd = item["sentence_distance"]
    check("sentence gap 1", sd["gap_count"] == 1 and sd["min"] == 1)


@test("repeated runs produce identical output")
def _():
    records = [
        make_record(0, "src1", "sec1", 3,
                    [expr(0, "e1", 0, 3, "PAT")]),
        make_record(1, "src2", "sec2", 4,
                    [expr(0, "e2", 1, 4, "PAT2")]),
    ]
    one = ea.analyze(records)
    two = ea.analyze(records)
    check("identical", one == two)


@test("corpus records unchanged")
def _():
    records = [
        make_record(0, "src1", "sec1", 3,
                    [expr(0, "e1", 0, 3, "PAT")]),
    ]
    snapshot = copy.deepcopy(records)
    ea.analyze(records)
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
