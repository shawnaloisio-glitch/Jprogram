#!/usr/bin/env python3
"""
test_source_id.py

Deterministic tests for source_id.py.

Run:
    python "Source Intake/tests/test_source_id.py"
"""

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_INTAKE = PROJECT_ROOT / "Source Intake"
sys.path.insert(0, str(SOURCE_INTAKE))

import source_id


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("slug normalization")
def _():
    check("lowercase", source_id.slugify("Sousou no Frieren") == "sousou-no-frieren")
    check("spaces to hyphens", source_id.slugify("Con Teppei Beginner") == "con-teppei-beginner")
    check("punctuation to hyphens", source_id.slugify("Let's Go!") == "let-s-go")
    check("underscores to hyphens", source_id.slugify("a_b_c") == "a-b-c")
    check("strip whitespace", source_id.slugify("  Hello World  ") == "hello-world")
    check("strip hyphens", source_id.slugify("-x-") == "x")


@test("japanese text preserved in slug")
def _():
    check("kanji/kana kept", source_id.slugify("折り紙でゴミ箱を作ろう") == "折り紙でゴミ箱を作ろう")


@test("sequence formatting")
def _():
    check("ep001", source_id.format_sequence(1, "ep") == "ep001")
    check("ep051", source_id.format_sequence(51, "ep") == "ep051")
    check("ch012", source_id.format_sequence(12, "ch", 3) == "ch012")
    check("custom width", source_id.format_sequence(7, "ep", 2) == "ep07")


@test("source_id generation examples")
def _():
    check("sub example",
          source_id.generate("sub", "sousou-no-frieren", "ep001")
          == "sub_sousou-no-frieren_ep001")
    check("pod example",
          source_id.generate("pod", "conteppei", "ep051")
          == "pod_conteppei_ep051")
    check("manga example",
          source_id.generate("manga", "one-piece", "ch012")
          == "manga_one-piece_ch012")


@test("source_id without sequence")
def _():
    check("no sequence", source_id.generate("pod", "conteppei") == "pod_conteppei")


@test("deterministic output")
def _():
    args = ("pod", "conteppei", "ep051")
    check("identical", source_id.generate(*args) == source_id.generate(*args))
    check("slugify identical", source_id.slugify("Con Teppei") == source_id.slugify("Con Teppei"))


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
