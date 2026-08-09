#!/usr/bin/env python3
"""
test_chunk_analyzer.py

Deterministic tests for chunk_analyzer.

Run:
    python Analysis/tests/test_chunk_analyzer.py
"""

import copy
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ANALYSIS = PROJECT_ROOT / "Analysis"
sys.path.insert(0, str(ANALYSIS))

import chunk_analyzer as ca


def make_record(sentence_id, source, section, word_count, chunks):
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
        "chunks": chunks,
        "expressions": [],
    }


def chunk(index, text, start_word, end_word):
    return [index, text, start_word, end_word]


def item_of(result, key):
    return result["chunks"].get(key)


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


@test("basic chunk counting")
def _():
    records = [make_record(0, "src1", "sec1", 3,
                           [chunk(0, "コーヒー を 飲んでます", 0, 3)])]
    result = ca.analyze(records)
    item = item_of(result, "コーヒー を 飲んでます")
    check("item exists", item is not None)
    check("occurrences", item["occurrences"] == 1)
    check("sentences", item["sentences"] == 1)
    check("sources", item["sources"] == 1)
    check("sections", item["sections"] == 1)


@test("multiple occurrences")
def _():
    records = [
        make_record(0, "src1", "sec1", 3, [chunk(0, "X", 0, 3)]),
        make_record(1, "src1", "sec1", 3, [chunk(0, "X", 0, 3)]),
    ]
    result = ca.analyze(records)
    item = item_of(result, "X")
    check("occurrences", item["occurrences"] == 2)
    check("sentences", item["sentences"] == 2)


@test("sentence/source/section coverage")
def _():
    records = [
        make_record(0, "src1", "episode-1", 3, [chunk(0, "X", 0, 3)]),
        make_record(1, "src1", "episode-2", 3, [chunk(0, "X", 0, 3)]),
        make_record(0, "src2", "episode-1", 3, [chunk(0, "X", 0, 3)]),
    ]
    result = ca.analyze(records)
    item = item_of(result, "X")
    check("occurrences", item["occurrences"] == 3)
    check("sentences", item["sentences"] == 3)
    check("sources", item["sources"] == 2)
    check("sections", item["sections"] == 3)


@test("location tracking")
def _():
    records = [make_record(0, "src1", "sec1", 5,
                           [chunk(0, "X", 1, 4)])]
    result = ca.analyze(records)
    item = item_of(result, "X")
    loc = item["locations"][0]
    check("start_word", loc["start_word"] == 1)
    check("end_word", loc["end_word"] == 4)
    check("sentence_id", loc["sentence_id"] == 0)
    check("source", loc["source"] == "src1")
    check("section", loc["section"] == "sec1")


@test("word-index distance calculation")
def _():
    # Two records, 3 words each; chunk at start_word 1.
    records = [
        make_record(0, "src1", "sec1", 3, [chunk(0, "X", 1, 3)]),
        make_record(1, "src1", "sec1", 3, [chunk(0, "X", 1, 3)]),
    ]
    result = ca.analyze(records)
    wd = item_of(result, "X")["distribution"]["word_distance"]
    # record0 starts at 0 -> 0+1=1; record1 starts at 3 -> 3+1=4.
    check("word gap 3", wd["gap_count"] == 1 and wd["min"] == 3
          and wd["max"] == 3)


@test("sentence distance calculation")
def _():
    records = [
        make_record(0, "src1", "sec1", 2, [chunk(0, "X", 0, 2)]),
        make_record(1, "src1", "sec1", 2, [chunk(0, "Y", 0, 2)]),
        make_record(2, "src1", "sec1", 2, [chunk(0, "X", 0, 2)]),
    ]
    result = ca.analyze(records)
    sd = item_of(result, "X")["distribution"]["sentence_distance"]
    check("sentence gap 2", sd["gap_count"] == 1 and sd["min"] == 2)


@test("statistics calculation")
def _():
    # Three records, 5 words each; chunks at start_word 0, 3 in r0;
    # start_word 1 in r1; start_word 4 in r2.
    records = [
        make_record(0, "src1", "sec1", 5,
                    [chunk(0, "X", 0, 2), chunk(1, "X", 3, 5)]),
        make_record(1, "src1", "sec1", 5, [chunk(0, "X", 1, 3)]),
        make_record(2, "src1", "sec1", 5, [chunk(0, "X", 4, 5)]),
    ]
    result = ca.analyze(records)
    wd = item_of(result, "X")["distribution"]["word_distance"]
    # word indices: 0, 3, 5+1=6, 10+4=14 -> gaps [3, 3, 8]
    check("gap_count 3", wd["gap_count"] == 3)
    check("min 3", wd["min"] == 3)
    check("max 8", wd["max"] == 8)
    check("mean 14/3", approx(wd["mean"], 14 / 3))
    check("median 3", approx(wd["median"], 3))
    check("stddev sqrt(50/9)", approx(wd["stddev"], (50 / 9) ** 0.5))


@test("repeated runs produce identical output")
def _():
    records = [
        make_record(0, "src1", "sec1", 3, [chunk(0, "X", 0, 3)]),
        make_record(1, "src2", "sec2", 4, [chunk(0, "Y", 1, 4)]),
    ]
    one = ca.analyze(records)
    two = ca.analyze(records)
    check("identical", one == two)


@test("corpus records unchanged")
def _():
    records = [
        make_record(0, "src1", "sec1", 3, [chunk(0, "X", 0, 3)]),
    ]
    snapshot = copy.deepcopy(records)
    ca.analyze(records)
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
