#!/usr/bin/env python3
"""
test_source_template.py

Documentation consistency tests for the frozen V1.0 source template
(G0.3). These verify the template files and SOURCE_TEMPLATE_SPEC.md match
the frozen contract. They do not test pipeline behavior.

Run:
    python "Templates/tests/test_source_template.py"
"""

import pathlib
import re
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
TEMPLATES = PROJECT_ROOT / "Templates"
SPEC = PROJECT_ROOT / "SOURCE_TEMPLATE_SPEC.md"

EXPECTED_FIELDS = [
    "template_version", "source_type", "collection", "season",
    "language", "origin", "episodes", "notes",
]

MARKER = (
    "==================================================\n"
    "EPISODE\n"
    "\n"
    "episode: 0001\n"
    "\n"
    "==================================================\n"
)

TEMPLATE_FILES = ("transcript_template.txt", "subtitle_template.txt")


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


@test("template files exist")
def _():
    for name in TEMPLATE_FILES:
        check(f"{name} exists", (TEMPLATES / name).is_file())


@test("SOURCE header contains exactly the eight fields in order")
def _():
    for name in TEMPLATE_FILES:
        text = (TEMPLATES / name).read_text(encoding="utf-8")
        header = text.split("==================================================")[0]
        fields = re.findall(r"^([a-z_]+):", header, re.M)
        check(f"{name} header fields", fields == EXPECTED_FIELDS, str(fields))


@test("template_version is 1.0")
def _():
    for name in TEMPLATE_FILES:
        text = (TEMPLATES / name).read_text(encoding="utf-8")
        check(f"{name} version", "template_version: 1.0" in text)


@test("exactly 15 episode blocks with four-digit numbers")
def _():
    for name in TEMPLATE_FILES:
        text = (TEMPLATES / name).read_text(encoding="utf-8")
        nums = re.findall(r"^episode: (\d{4})$", text, re.M)
        check(f"{name} 15 blocks", len(nums) == 15, str(len(nums)))
        check(f"{name} starts 0001", nums[0] == "0001")
        check(f"{name} ends 0015", nums[-1] == "0015")
        check(f"{name} contiguous", nums ==
              ["{:04d}".format(i) for i in range(1, 16)])
        check(f"{name} all four digits",
              all(len(n) == 4 for n in nums))


@test("episode marker format is frozen")
def _():
    for name in TEMPLATE_FILES:
        text = (TEMPLATES / name).read_text(encoding="utf-8")
        check(f"{name} frozen marker present", MARKER in text)


@test("transcript and subtitle templates differ only in source_type")
def _():
    trans = (TEMPLATES / "transcript_template.txt").read_text(encoding="utf-8")
    sub = (TEMPLATES / "subtitle_template.txt").read_text(encoding="utf-8")
    check("transcript type", "source_type: podcast_transcript" in trans)
    check("subtitle type", "source_type: anime_subtitle" in sub)
    # After normalizing the source_type line, the files should be identical.
    norm_trans = trans.replace("source_type: podcast_transcript",
                               "source_type: <TYPE>")
    norm_sub = sub.replace("source_type: anime_subtitle",
                           "source_type: <TYPE>")
    check("identical apart from source_type", norm_trans == norm_sub)


@test("spec documents required topics")
def _():
    text = SPEC.read_text(encoding="utf-8")
    topics = [
        "Header Fields", "Episode Marker", "Four-Digit", "One Collection",
        "Blank Episode", "Human-Editable", "Machine-Generated",
        "Canonical Source", "No Internal IDs", "Origin", "Backward Compatibility",
    ]
    for topic in topics:
        check(f"spec covers: {topic}", topic.lower() in text.lower())


@test("spec lists the template files")
def _():
    text = SPEC.read_text(encoding="utf-8")
    check("transcript template listed", "transcript_template.txt" in text)
    check("subtitle template listed", "subtitle_template.txt" in text)


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
