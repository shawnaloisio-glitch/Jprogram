#!/usr/bin/env python3
"""
test_comparison_analyzer.py

Deterministic tests for comparison_analyzer.

Run:
    python Analysis/tests/test_comparison_analyzer.py
"""

import copy
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ANALYSIS = PROJECT_ROOT / "Analysis"
sys.path.insert(0, str(ANALYSIS))

import comparison_analyzer as ca


def make_record(sentence_id, text, words, chunks=(), expressions=()):
    """Build a canonical-style record."""
    return {
        "text": text,
        "ids": {"sentence_id": sentence_id},
        "provenance": {
            "source": "ignored-in-comparison",  # grouping uses the sources dict keys
            "source_file": "x.clean.txt",
            "job_number": 1,
            "model": "deepseek-v4-flash",
            "prompt_version": "1.0",
            "sentence_id": sentence_id,
            "sentence_position": sentence_id,
        },
        "section": "default",
        "words": list(words),
        "chunks": list(chunks),
        "expressions": list(expressions),
    }


def word(index, surface, lexical):
    return [index, surface, lexical, 0, len(surface)]


def chunk(index, text, start_word, end_word):
    return [index, text, start_word, end_word]


def expr(index, surface, start_word, end_word, pattern):
    return [index, surface, start_word, end_word, pattern]


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


def src_a_records():
    return [
        make_record(0, "テキストA", [
            word(0, "a", "X"),
            word(1, "y", "Y"),
        ], chunks=[
            chunk(0, "cA", 0, 1),
            chunk(1, "sharedC", 0, 2),
        ], expressions=[
            expr(0, "eA", 0, 1, "PAT_A"),
            expr(1, "sharedE", 0, 2, "PAT"),
        ]),
    ]


def src_b_records():
    return [
        make_record(0, "テキストB", [
            word(0, "a", "X"),
            word(1, "z", "Z"),
        ], chunks=[
            chunk(0, "cB", 0, 1),
            chunk(1, "sharedC", 0, 2),
        ], expressions=[
            expr(0, "eB", 0, 1, "PAT_B"),
            expr(1, "sharedE", 0, 2, "PAT"),
        ]),
    ]


@test("basic two-corpus comparison")
def _():
    result = ca.analyze({"src_a": src_a_records(), "src_b": src_b_records()})
    check("sources sorted", result["comparison"]["sources"] == ["src_a", "src_b"])
    check("summary sources", result["summary"]["sources_compared"] == 2)
    check("records processed", result["summary"]["records_processed"] == 2)


@test("shared vocabulary detection")
def _():
    result = ca.analyze({"src_a": src_a_records(), "src_b": src_b_records()})
    shared = result["comparison"]["vocabulary"]["shared"]
    check("X shared", "X" in shared)
    check("only X shared", shared == ["X"], str(shared))


@test("unique vocabulary detection")
def _():
    result = ca.analyze({"src_a": src_a_records(), "src_b": src_b_records()})
    unique = result["comparison"]["vocabulary"]["unique"]
    check("Y only in src_a", unique["src_a"] == ["Y"], str(unique["src_a"]))
    check("Z only in src_b", unique["src_b"] == ["Z"], str(unique["src_b"]))


@test("surface variation handling")
def _():
    a = [make_record(0, "a", [word(0, "食べました", "食べる")])]
    b = [make_record(0, "b", [word(0, "食べない", "食べる")])]
    result = ca.analyze({"src_a": a, "src_b": b})
    item = result["comparison"]["vocabulary"]["by_item"]["食べる"]
    check("shared", "食べる" in result["comparison"]["vocabulary"]["shared"])
    check("occurrence counts", item["src_a"]["occurrences"] == 1
          and item["src_b"]["occurrences"] == 1)
    check("surface counts", item["src_a"]["surfaces"] == 1
          and item["src_b"]["surfaces"] == 1)


@test("expression comparison")
def _():
    result = ca.analyze({"src_a": src_a_records(), "src_b": src_b_records()})
    e = result["comparison"]["expressions"]
    check("shared PAT", e["shared"] == ["PAT"], str(e["shared"]))
    check("unique", e["unique"]["src_a"] == ["PAT_A"]
          and e["unique"]["src_b"] == ["PAT_B"])


@test("chunk comparison")
def _():
    result = ca.analyze({"src_a": src_a_records(), "src_b": src_b_records()})
    c = result["comparison"]["chunks"]
    check("shared chunk", c["shared"] == ["sharedC"], str(c["shared"]))
    check("unique chunks", c["unique"]["src_a"] == ["cA"]
          and c["unique"]["src_b"] == ["cB"])


@test("sentence structure comparison")
def _():
    result = ca.analyze({"src_a": src_a_records(), "src_b": src_b_records()})
    by_source = result["comparison"]["sentence_metrics"]["by_source"]
    sa = by_source["src_a"]
    check("src_a sentences", sa["sentences"] == 1)
    check("src_a words", sa["words"] == 2)
    check("src_a characters", sa["characters"] == len("テキストA"))
    check("src_a chunks", sa["chunks"] == 2)
    check("src_a expressions", sa["expressions"] == 2)


@test("repeated runs produce identical output")
def _():
    sources = {"src_a": src_a_records(), "src_b": src_b_records()}
    one = ca.analyze(sources)
    two = ca.analyze(sources)
    check("identical", one == two)


@test("corpus records unchanged")
def _():
    a = src_a_records()
    b = src_b_records()
    snapshot_a = copy.deepcopy(a)
    snapshot_b = copy.deepcopy(b)
    ca.analyze({"src_a": a, "src_b": b})
    check("records unchanged", a == snapshot_a and b == snapshot_b)


@test("no analyzer output files are required")
def _():
    # Independence: the module must not import other analyzer modules.
    source = pathlib.Path(ANALYSIS / "comparison_analyzer.py").read_text(
        encoding="utf-8")
    for forbidden in ("frequency_analyzer", "distribution_analyzer",
                      "exposure_analyzer", "expression_analyzer",
                      "chunk_analyzer", "sentence_metrics", "output_writer"):
        check(f"does not import {forbidden}", forbidden + " import" not in source)
    # And it runs purely from in-memory canonical records (no file I/O).
    result = ca.analyze({"src_a": src_a_records(), "src_b": src_b_records()})
    check("runs from records only", result["summary"]["sources_compared"] == 2)


@test("at least two sources required")
def _():
    raised = False
    try:
        ca.analyze({"src_a": src_a_records()})
    except ValueError:
        raised = True
    check("single source raises", raised)


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
