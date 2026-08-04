#!/usr/bin/env python3
"""
test_distribution_analyzer.py

Deterministic tests for distribution_analyzer.

Run:
    python Analysis/tests/test_distribution_analyzer.py
"""

import copy
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ANALYSIS = PROJECT_ROOT / "Analysis"
sys.path.insert(0, str(ANALYSIS))

import distribution_analyzer as da


def make_record(sentence_id, source, section, text, words):
    """Build a canonical-style record with the given words."""
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


def item_of(result, key):
    return result["distribution"].get(key)


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


@test("single occurrence produces no gap metrics")
def _():
    records = [make_record(0, "src1", "sec1", "あ",
                           [[0, "あ", "X", 0, 1]])]
    result = da.analyze(records)
    item = item_of(result, "X")
    check("item exists", item is not None)
    for metric in ("word_distance", "character_distance", "sentence_distance"):
        check(f"{metric} gap_count 0", item[metric]["gap_count"] == 0)
        check(f"{metric} min None", item[metric]["min"] is None)
        check(f"{metric} max None", item[metric]["max"] is None)
        check(f"{metric} mean None", item[metric]["mean"] is None)
        check(f"{metric} median None", item[metric]["median"] is None)
        check(f"{metric} stddev None", item[metric]["stddev"] is None)
    check("occurrences count", len(item["occurrences"]) == 1)


@test("multiple occurrences calculate correct word distances")
def _():
    text = "A B C D E F G"
    words = [
        [0, "A", "A", 0, 1],
        [1, "B", "X", 2, 3],
        [2, "C", "C", 4, 5],
        [3, "D", "X", 6, 7],
        [4, "E", "E", 8, 9],
        [5, "F", "F", 10, 11],
        [6, "G", "X", 12, 13],
    ]
    records = [make_record(0, "src1", "sec1", text, words)]
    result = da.analyze(records)
    item = item_of(result, "X")
    wd = item["word_distance"]
    check("gaps [2,3]", wd["min"] == 2 and wd["max"] == 3
          and wd["gap_count"] == 2)
    check("mean 2.5", approx(wd["mean"], 2.5))
    check("median 2.5", approx(wd["median"], 2.5))
    check("word positions recorded",
          [o["global_word_index"] for o in item["occurrences"]] == [1, 3, 6])


@test("character distances calculate correctly")
def _():
    # X at [0,2) in sentence 0 (len 5); X at [2,3) in sentence 1 (len 3).
    r0 = make_record(0, "src1", "sec1", "あいうえお", [[0, "あい", "X", 0, 2]])
    r1 = make_record(1, "src1", "sec1", "かきく", [[0, "く", "X", 2, 3]])
    result = da.analyze([r0, r1])
    item = item_of(result, "X")
    cd = item["character_distance"]
    check("char gap 5", cd["gap_count"] == 1 and cd["min"] == 5)
    check("word gap 1", item["word_distance"]["min"] == 1)
    check("sentence gap 1", item["sentence_distance"]["min"] == 1)


@test("sentence distances calculate correctly")
def _():
    records = [
        make_record(0, "src1", "sec1", "あ", [[0, "あ", "X", 0, 1]]),
        make_record(1, "src1", "sec1", "い", [[0, "い", "Y", 0, 1]]),
        make_record(2, "src1", "sec1", "う", [[0, "う", "Y", 0, 1]]),
        make_record(3, "src1", "sec1", "え", [[0, "え", "X", 0, 1]]),
    ]
    result = da.analyze(records)
    item = item_of(result, "X")
    sd = item["sentence_distance"]
    check("sentence gap 3", sd["gap_count"] == 1 and sd["min"] == 3)
    check("word gap 3", item["word_distance"]["min"] == 3)


@test("mean/median/min/max calculations correct")
def _():
    text = "abcdefgh"
    words = [
        [0, "a", "X", 0, 1],
        [1, "b", "O", 1, 2],
        [2, "c", "X", 2, 3],
        [3, "d", "O", 3, 4],
        [4, "e", "O", 4, 5],
        [5, "f", "O", 5, 6],
        [6, "g", "X", 6, 7],
        [7, "h", "X", 7, 8],
    ]
    result = da.analyze([make_record(0, "src1", "sec1", text, words)])
    wd = item_of(result, "X")["word_distance"]
    check("gaps [2,4,1]", wd["gap_count"] == 3 and wd["min"] == 1 and wd["max"] == 4)
    check("mean 7/3", approx(wd["mean"], 7 / 3))
    check("median 2", approx(wd["median"], 2))
    check("stddev pstdev([2,4,1])", approx(wd["stddev"], 1.247219128924647))
    # even-count median
    text2 = "abcdef"
    words2 = [
        [0, "a", "X", 0, 1],
        [1, "b", "O", 1, 2],
        [2, "c", "O", 2, 3],
        [3, "d", "X", 3, 4],
        [4, "e", "O", 4, 5],
        [5, "f", "X", 5, 6],
    ]
    result2 = da.analyze([make_record(0, "src1", "sec1", text2, words2)])
    wd2 = item_of(result2, "X")["word_distance"]
    check("even gaps [3,2]", wd2["gap_count"] == 2 and wd2["min"] == 2 and wd2["max"] == 3)
    check("even median 2.5", approx(wd2["median"], 2.5))


@test("multiple sources handled correctly")
def _():
    r0 = make_record(0, "src1", "sec1", "abcde", [[0, "a", "X", 0, 1]])
    r1 = make_record(0, "src2", "sec1", "vwxyz", [[0, "v", "X", 0, 1]])
    result = da.analyze([r0, r1])
    item = item_of(result, "X")
    occs = item["occurrences"]
    check("sources recorded", [o["source"] for o in occs] == ["src1", "src2"])
    check("global word index continues", [o["global_word_index"] for o in occs] == [0, 1])
    check("word gap 1", item["word_distance"]["min"] == 1)
    check("char gap 4", item["character_distance"]["min"] == 4)  # (5-1) + 0


@test("multiple surfaces sharing a lexical item handled correctly")
def _():
    text = "食べました食べない"
    words = [
        [0, "食べました", "食べる", 0, 5],
        [1, "食べない", "食べる", 5, 9],
    ]
    result = da.analyze([make_record(0, "src1", "sec1", text, words)])
    item = item_of(result, "食べる")
    check("grouped together", len(item["occurrences"]) == 2)
    check("word gap 1", item["word_distance"]["gap_count"] == 1
          and item["word_distance"]["min"] == 1)


@test("repeated runs produce identical output")
def _():
    records = [
        make_record(0, "src1", "sec1", "あいうえお", [[0, "あ", "X", 0, 1]]),
        make_record(1, "src1", "sec1", "かきくけこ", [[0, "か", "X", 0, 1]]),
    ]
    one = da.analyze(records)
    two = da.analyze(records)
    check("identical", one == two)


@test("corpus records unchanged")
def _():
    records = [
        make_record(0, "src1", "sec1", "あいうえお", [[0, "あ", "X", 0, 1]]),
        make_record(1, "src2", "sec2", "かきくけこ", [[0, "か", "X", 0, 1]]),
    ]
    snapshot = copy.deepcopy(records)
    da.analyze(records)
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
