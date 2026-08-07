#!/usr/bin/env python3
"""
test_sentence_split.py

Deterministic tests for Common/sentence_split.py.

Run:
    python "Common/tests/test_sentence_split.py"
"""

import pathlib
import sys

COMMON = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(COMMON))

import sentence_split as ss


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


# ============================================================
# split_line
# ============================================================

@test("single sentence with no punctuation is one whole sentence")
def _():
    check("no punctuation", ss.split_line("こんにちは") == ["こんにちは"])
    check("romanized no punctuation", ss.split_line("hello world")
          == ["hello world"])


@test("line with exactly one sentence stays one item")
def _():
    check("kana with 。", ss.split_line("これはテストです。")
          == ["これはテストです。"])
    check("with ！", ss.split_line("本当だ！") == ["本当だ！"])
    check("with ？", ss.split_line("本当に？") == ["本当に？"])


@test("two sentences with no separator split into two items")
def _():
    check("通りません。はい。", ss.split_line("通りません。はい。")
          == ["通りません。", "はい。"])
    check("three sentences", ss.split_line("A。B。C。") == ["A。", "B。", "C。"])


@test("punctuation stays attached to the preceding sentence")
def _():
    check("。 attached", ss.split_line("行きます。行きません。")
          == ["行きます。", "行きません。"])
    check("！ attached", ss.split_line("待って！本当？")
          == ["待って！", "本当？"])


@test("consecutive sentence-final punctuation coalesces into one boundary")
def _():
    check("本当に？！", ss.split_line("本当に？！") == ["本当に？！"])
    check("two ！！", ss.split_line("すごい！！") == ["すごい！！"])
    check("mixed run then sentence",
          ss.split_line("すごい！！次。") == ["すごい！！", "次。"])


@test("empty line returns empty list")
def _():
    check("empty", ss.split_line("") == [])
    check("whitespace only is one item",
          ss.split_line(" ") == [" "])


@test("split_line is pure and repeatable")
def _():
    for arg in ("通りません。はい。", "こんにちは", "すごい！！", ""):
        check(f"repeatable {arg!r}", ss.split_line(arg) == ss.split_line(arg))


@test("SENTENCE_FINAL_PUNCT is a frozenset of the three boundaries")
def _():
    check("exact set", ss.SENTENCE_FINAL_PUNCT == frozenset("。！？"))
    check("frozenset", isinstance(ss.SENTENCE_FINAL_PUNCT, frozenset))


# ============================================================
# Boundary / dependency guard
# ============================================================

@test("module is dependency-free (no imports at all)")
def _():
    source = pathlib.Path(COMMON / "sentence_split.py").read_text(
        encoding="utf-8"
    )
    import_lines = "\n".join(
        ln for ln in source.splitlines()
        if ln.lstrip().startswith("import ")
        or ln.lstrip().startswith("from ")
    )
    check("no imports", import_lines == "", repr(import_lines))


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
