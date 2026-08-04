#!/usr/bin/env python3
"""
test_cleaning_utils.py

Deterministic tests for Common/cleaning_utils.py.

Run:
    python "Common/tests/test_cleaning_utils.py"
"""

import pathlib
import sys

COMMON = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(COMMON))

import cleaning_utils as cu


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
# BOM handling
# ============================================================

@test("BOM removed from text")
def _():
    text, removed = cu.strip_bom("\ufeff日本語\nテスト")
    check("removed is True", removed is True)
    check("text has no BOM", not text.startswith("\ufeff"))
    check("content preserved", text == "日本語\nテスト")


@test("no BOM unchanged")
def _():
    text, removed = cu.strip_bom("日本語\nテスト")
    check("removed is False", removed is False)
    check("text unchanged", text == "日本語\nテスト")


@test("BOM removal is first character only")
def _():
    text, removed = cu.strip_bom("\ufeff\ufeffabc")
    check("removed is True", removed is True)
    check("one BOM removed", text == "\ufeffabc")


@test("empty string with no BOM")
def _():
    text, removed = cu.strip_bom("")
    check("removed is False", removed is False)
    check("empty", text == "")


# ============================================================
# Line trimming
# ============================================================

@test("leading and trailing whitespace removed")
def _():
    lines, count = cu.trim_lines(["  日本語  ", "テスト", "  foo  "])
    check("trimmed", lines == ["日本語", "テスト", "foo"])
    check("count", count == 2)


@test("trim count is correct")
def _():
    lines, count = cu.trim_lines(["a", "  b", "c  ", " d ", "e"])
    check("count", count == 3)
    check("ordering preserved", lines == ["a", "b", "c", "d", "e"])


@test("trim with no changes counts zero")
def _():
    lines, count = cu.trim_lines(["a", "b", "c"])
    check("count", count == 0)
    check("unchanged", lines == ["a", "b", "c"])


# ============================================================
# Blank line collapsing
# ============================================================

@test("multiple consecutive blanks collapse to one")
def _():
    lines, count = cu.collapse_blank_lines(["a", "", "", "", "b"])
    check("collapsed", lines == ["a", "", "b"])
    check("count", count == 2)


@test("single blank separator preserved")
def _():
    lines, count = cu.collapse_blank_lines(["a", "", "b"])
    check("preserved", lines == ["a", "", "b"])
    check("count", count == 0)


@test("leading and trailing blank runs")
def _():
    lines, count = cu.collapse_blank_lines(["", "", "a", "", ""])
    check("leading/trailing", lines == ["", "a", ""])
    check("count", count == 2)


@test("all blank input collapses to one blank")
def _():
    lines, count = cu.collapse_blank_lines(["", "", ""])
    check("one blank", lines == [""])
    check("count", count == 2)


@test("blank collapse is deterministic ordering")
def _():
    input_lines = ["a", "", "", "b", "", "c", "", ""]
    l1, c1 = cu.collapse_blank_lines(input_lines)
    l2, c2 = cu.collapse_blank_lines(input_lines)
    check("identical lines", l1 == l2)
    check("identical count", c1 == c2)


# ============================================================
# ASCII space collapsing
# ============================================================

@test("repeated ASCII spaces collapse")
def _():
    line, count = cu.collapse_ascii_spaces("hello   world")
    check("collapsed", line == "hello world")
    check("count", count == 1)


@test("Japanese full-width spaces unchanged")
def _():
    line, count = cu.collapse_ascii_spaces("日本語　テスト")
    check("unchanged", line == "日本語　テスト")
    check("count", count == 0)


@test("mixed ASCII and full-width spaces")
def _():
    line, count = cu.collapse_ascii_spaces("a  b　c   d　e")
    check("ascii collapsed only", line == "a b　c d　e")
    check("count", count == 2)


@test("single ASCII spaces unchanged")
def _():
    line, count = cu.collapse_ascii_spaces("a b c")
    check("unchanged", line == "a b c")
    check("count", count == 0)


@test("multiple runs counted individually")
def _():
    line, count = cu.collapse_ascii_spaces("a    b  c")
    check("collapsed", line == "a b c")
    check("count", count == 2)


# ============================================================
# Output joining
# ============================================================

@test("join with single final newline")
def _():
    output = cu.join_clean_lines(["a", "b", "c"])
    check("output", output == "a\nb\nc\n")
    check("one final newline", output.endswith("\n") and not output.endswith("\n\n"))


@test("join removes trailing whitespace")
def _():
    output = cu.join_clean_lines(["a", "b", "  "])
    check("no trailing whitespace", output == "a\nb\n")
    check("one final newline", output.endswith("\n") and not output.endswith("\n\n"))


@test("join is deterministic")
def _():
    lines = ["日本語", "テスト", "", "行"]
    o1 = cu.join_clean_lines(lines)
    o2 = cu.join_clean_lines(lines)
    check("identical output", o1 == o2)


@test("join empty list")
def _():
    output = cu.join_clean_lines([])
    check("exactly one newline", output == "\n")


# ============================================================
# Unicode preservation
# ============================================================

@test("Japanese characters unchanged through full pipeline")
def _():
    raw = "\ufeff今日は　良い天気ですね。\n\n\n次は日本語のテストです。  "
    text, _ = cu.strip_bom(raw)
    lines = text.splitlines()
    lines, _ = cu.trim_lines(lines)
    lines, _ = cu.collapse_blank_lines(lines)
    lines = [cu.collapse_ascii_spaces(line)[0] for line in lines]
    output = cu.join_clean_lines(lines)
    check("japanese text preserved",
          output == "今日は　良い天気ですね。\n\n次は日本語のテストです。\n")


@test("full-width space preserved in join")
def _():
    lines, _ = cu.collapse_blank_lines(["日本語　テスト"])
    output = cu.join_clean_lines(lines)
    check("full-width preserved", output == "日本語　テスト\n")


# ============================================================
# Repeatability
# ============================================================

@test("identical input produces identical output and statistics")
def _():
    input_lines = ["  a  ", "", "b   c", "", "", "日本語　語"]
    for fn, arg in (
        (cu.trim_lines, input_lines),
        (cu.collapse_blank_lines, input_lines),
        (cu.collapse_ascii_spaces, "a   b  c"),
        (cu.strip_bom, "\ufeffabc"),
        (cu.join_clean_lines, input_lines),
    ):
        r1 = fn(arg)
        r2 = fn(arg)
        check(f"{fn.__name__} repeatable", r1 == r2)


# ============================================================
# Boundary
# ============================================================

@test("no forbidden imports")
def _():
    source = pathlib.Path(COMMON / "cleaning_utils.py").read_text(encoding="utf-8")
    import_lines = "\n".join(
        ln for ln in source.splitlines()
        if ln.lstrip().startswith("import ") or ln.lstrip().startswith("from ")
    )
    for forbidden in ("clean_subtitles", "clean_transcript",
                      "corpus_builder", "job builder", "request builder",
                      "response_validator", "deepseek", "paths",
                      "Analysis", "schemas", "registry", "cleaning_job",
                      "cleaning_result", "source_intake", "project_config"):
        check(f"no {forbidden!r}", forbidden not in import_lines)


@test("only standard library imports")
def _():
    source = pathlib.Path(COMMON / "cleaning_utils.py").read_text(encoding="utf-8")
    lines = [ln for ln in source.splitlines() if ln.startswith("import ")
             or ln.startswith("from ")]
    check("re import only", lines == ["import re"], repr(lines))


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
