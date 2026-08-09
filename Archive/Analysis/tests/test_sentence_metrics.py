#!/usr/bin/env python3
"""
test_sentence_metrics.py

Deterministic tests for sentence_metrics.

Run:
    python Analysis/tests/test_sentence_metrics.py
"""

import copy
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ANALYSIS = PROJECT_ROOT / "Analysis"
sys.path.insert(0, str(ANALYSIS))

import sentence_metrics as sm


def make_record(sentence_id, source, section, text, word_count,
                chunk_count=0, expression_count=0):
    """Build a canonical-style record with the given counts."""
    words = [[i, f"w{i}", f"w{i}", i, i + 1] for i in range(word_count)]
    chunks = [
        [i, f"c{i}", i, i + 1] for i in range(chunk_count)
    ] if chunk_count else []
    expressions = [
        [i, f"e{i}", i, i + 1, f"pat{i}"] for i in range(expression_count)
    ] if expression_count else []
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
        "expressions": expressions,
    }


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


@test("basic sentence metrics")
def _():
    records = [make_record(0, "src1", "sec1", "あいうえお", 3)]
    result = sm.analyze(records)
    m = result["sentences"][0]["metrics"]
    check("character_count", m["character_count"] == 5)
    check("word_count", m["word_count"] == 3)
    check("chunk_count", m["chunk_count"] == 0)
    check("expression_count", m["expression_count"] == 0)
    check("identity", result["sentences"][0]["source"] == "src1"
          and result["sentences"][0]["section"] == "sec1"
          and result["sentences"][0]["sentence_id"] == 0)


@test("character counting")
def _():
    records = [make_record(0, "src1", "sec1", "これは、テストです。", 2)]
    result = sm.analyze(records)
    check("character_count 10", result["sentences"][0]["metrics"]["character_count"] == 10)


@test("word/chunk/expression counts")
def _():
    records = [make_record(0, "src1", "sec1", "あいうえお", 4, chunk_count=2,
                           expression_count=1)]
    m = sm.analyze(records)["sentences"][0]["metrics"]
    check("word_count", m["word_count"] == 4)
    check("chunk_count", m["chunk_count"] == 2)
    check("expression_count", m["expression_count"] == 1)


@test("density calculations")
def _():
    records = [make_record(0, "src1", "sec1", "あいうえお", 4, chunk_count=2,
                           expression_count=1)]
    m = sm.analyze(records)["sentences"][0]["metrics"]
    check("chunks_per_word 0.5", approx(m["chunks_per_word"], 0.5))
    check("expressions_per_word 0.25", approx(m["expressions_per_word"], 0.25))


@test("multiple sentences preserve order")
def _():
    records = [
        make_record(0, "src1", "sec1", "あ", 1),
        make_record(1, "src1", "sec1", "いい", 2),
        make_record(2, "src1", "sec1", "ううう", 3),
    ]
    result = sm.analyze(records)
    ids = [s["sentence_id"] for s in result["sentences"]]
    check("order preserved", ids == [0, 1, 2])
    check("character counts in order",
          [s["metrics"]["character_count"] for s in result["sentences"]]
          == [1, 2, 3])


@test("source grouping")
def _():
    records = [
        make_record(0, "src1", "sec1", "あ", 1),
        make_record(0, "src2", "sec1", "い", 2),
    ]
    result = sm.analyze(records)
    bs = result["by_source"]
    check("two sources", set(bs.keys()) == {"src1", "src2"})
    check("src1 sentences", bs["src1"]["sentences"] == 1)
    check("src2 sentences", bs["src2"]["sentences"] == 1)
    check("src2 words", bs["src2"]["words"] == 2)


@test("section grouping")
def _():
    records = [
        make_record(0, "src1", "episode-1", "あ", 1),
        make_record(1, "src1", "episode-2", "いい", 2),
    ]
    result = sm.analyze(records)
    bs = result["by_section"]
    entries = [(e["source"], e["section"]) for e in bs]
    check("two sections", ("src1", "episode-1") in entries
          and ("src1", "episode-2") in entries)
    ep2 = [e for e in bs if e["section"] == "episode-2"][0]
    check("episode-2 characters", ep2["characters"] == 2)


@test("repeated runs produce identical output")
def _():
    records = [
        make_record(0, "src1", "sec1", "あ", 1),
        make_record(1, "src2", "sec2", "いい", 2),
    ]
    one = sm.analyze(records)
    two = sm.analyze(records)
    check("identical", one == two)


@test("corpus records unchanged")
def _():
    records = [
        make_record(0, "src1", "sec1", "あ", 1),
        make_record(1, "src2", "sec2", "いい", 2),
    ]
    snapshot = copy.deepcopy(records)
    sm.analyze(records)
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
