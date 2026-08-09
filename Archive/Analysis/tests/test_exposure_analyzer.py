#!/usr/bin/env python3
"""
test_exposure_analyzer.py

Deterministic tests for exposure_analyzer.

Run:
    python Analysis/tests/test_exposure_analyzer.py
"""

import copy
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ANALYSIS = PROJECT_ROOT / "Analysis"
sys.path.insert(0, str(ANALYSIS))

import exposure_analyzer as ea


def make_record(sentence_id, source, section, words):
    """Build a canonical-style record with the given word records."""
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
        "expressions": [],
    }


def word(index, surface, lexical):
    return [index, surface, lexical, 0, len(surface)]


def item_of(result, key):
    return result["exposure"].get(key)


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


@test("basic exposure counting")
def _():
    records = [make_record(0, "src1", "sec1", [word(0, "コーヒー", "コーヒー")])]
    result = ea.analyze(records)
    item = item_of(result, "コーヒー")
    check("item exists", item is not None)
    check("occurrences", item["occurrences"] == 1)
    check("sentences", item["sentences"] == 1)
    check("sources", item["sources"] == 1)
    check("sections", item["sections"] == 1)
    check("single occurrence no gaps",
          item["distribution"]["word_distance"]["gap_count"] == 0
          and item["distribution"]["word_distance"]["min"] is None)


@test("first occurrence tracking")
def _():
    records = [make_record(0, "src1", "episode-3", [
        word(0, "a", "A"),
        word(1, "b", "B"),
        word(2, "x", "X"),
    ])]
    result = ea.analyze(records)
    fs = item_of(result, "X")["first_seen"]
    check("source", fs["source"] == "src1")
    check("section", fs["section"] == "episode-3")
    check("sentence_id", fs["sentence_id"] == 0)
    check("word_position", fs["word_position"] == 2)
    check("global_word_index", fs["global_word_index"] == 2)


@test("multiple encounters")
def _():
    records = [
        make_record(0, "src1", "sec1", [word(0, "x", "X")]),
        make_record(1, "src1", "sec1", [word(0, "x", "X")]),
    ]
    result = ea.analyze(records)
    item = item_of(result, "X")
    check("occurrences", item["occurrences"] == 2)
    check("first_seen sentence 0", item["first_seen"]["sentence_id"] == 0)
    check("locations count", len(item["locations"]) == 2)
    check("locations order", [l["global_word_index"] for l in item["locations"]] == [0, 1])


@test("surface variation tracking")
def _():
    records = [make_record(0, "src1", "sec1", [
        word(0, "食べました", "食べる"),
        word(1, "食べない", "食べる"),
    ])]
    result = ea.analyze(records)
    item = item_of(result, "食べる")
    check("surfaces", item["surfaces"] == {"食べました": 1, "食べない": 1})
    check("occurrences", item["occurrences"] == 2)


@test("source/section coverage")
def _():
    records = [
        make_record(0, "src1", "episode-1", [word(0, "x", "X")]),
        make_record(1, "src1", "episode-2", [word(0, "x", "X")]),
        make_record(0, "src2", "episode-1", [word(0, "x", "X")]),
    ]
    result = ea.analyze(records)
    item = item_of(result, "X")
    check("occurrences", item["occurrences"] == 3)
    check("sentences", item["sentences"] == 3)
    check("sources", item["sources"] == 2)
    check("sections", item["sections"] == 3)


@test("word-index distance calculation")
def _():
    records = [
        make_record(0, "src1", "sec1", [word(0, "x", "X")]),
        make_record(1, "src1", "sec1", [word(0, "x", "X")]),
    ]
    result = ea.analyze(records)
    wd = item_of(result, "X")["distribution"]["word_distance"]
    check("word gap 1", wd["gap_count"] == 1 and wd["min"] == 1)


@test("sentence-distance calculation")
def _():
    records = [
        make_record(0, "src1", "sec1", [word(0, "x", "X")]),
        make_record(1, "src1", "sec1", [word(0, "y", "Y")]),
        make_record(2, "src1", "sec1", [word(0, "x", "X")]),
    ]
    result = ea.analyze(records)
    sd = item_of(result, "X")["distribution"]["sentence_distance"]
    check("sentence gap 2", sd["gap_count"] == 1 and sd["min"] == 2)


@test("statistics calculation")
def _():
    records = [
        make_record(0, "src1", "sec1", [word(0, "x", "X")]),
        make_record(1, "src1", "sec1", [word(0, "x", "X")]),
        make_record(2, "src1", "sec1", [word(0, "x", "X")]),
    ]
    result = ea.analyze(records)
    wd = item_of(result, "X")["distribution"]["word_distance"]
    # global word indices 0,1,2 -> gaps [1,1]
    check("gap_count 2", wd["gap_count"] == 2)
    check("min/max", wd["min"] == 1 and wd["max"] == 1)
    check("mean 1", approx(wd["mean"], 1.0))
    check("median 1", approx(wd["median"], 1.0))
    check("stddev 0", approx(wd["stddev"], 0.0))


@test("repeated runs produce identical output")
def _():
    records = [
        make_record(0, "src1", "sec1", [word(0, "コーヒー", "コーヒー")]),
        make_record(1, "src2", "sec2", [word(0, "テスト", "テスト")]),
    ]
    one = ea.analyze(records)
    two = ea.analyze(records)
    check("identical", one == two)


@test("corpus records unchanged")
def _():
    records = [
        make_record(0, "src1", "sec1", [word(0, "コーヒー", "コーヒー")]),
        make_record(1, "src2", "sec2", [word(0, "テスト", "テスト")]),
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
