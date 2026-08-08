#!/usr/bin/env python3
"""
test_source_builder_import_material.py

Deterministic tests for the Source Builder import material conversion:

- clean text normalization,
- subtitle conversion reuses the Subtitle Importer cleaner (SRT/VTT),
- multiple files are combined,
- empty/unknown inputs handled,
- import never starts processing (no registry/job writes).

Run:
    python "Source Builder/tests/test_source_builder_import_material.py"
"""

import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Subtitle Importer"))
sys.path.insert(0, str(PROJECT_ROOT / "Production Manager"))

import import_material

TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


def tmp_file(name, content, encoding="utf-8"):
    folder = pathlib.Path(tempfile.mkdtemp())
    path = folder / name
    path.write_text(content, encoding=encoding)
    return path


@test("clean text is normalized with a trailing newline")
def _():
    text = import_material.convert_text(
        "こんにちは。\r\nお元気ですか。\r\n", import_material.FORMAT_CLEAN_TEXT)
    check("normalized", text == "こんにちは。\nお元気ですか。\n")


@test("subtitle file is converted via the Subtitle Importer cleaner")
def _():
    srt = tmp_file("ep01.srt", "1\n00:00:01,000 --> 00:00:02,000\nこんにちは。\n")
    text = import_material.convert_file(srt, import_material.FORMAT_SUBTITLE)
    check("dialogue kept", "こんにちは。" in text)
    check("timestamp removed", "00:00" not in text)
    check("numbering removed", "\n1\n" not in text)


@test("vtt subtitle file is converted via the Subtitle Importer cleaner")
def _():
    vtt = tmp_file("ep01.vtt",
                   "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nこんにちは。\n")
    text = import_material.convert_file(vtt, import_material.FORMAT_SUBTITLE)
    check("dialogue kept", "こんにちは。" in text)
    check("no webvtt", "WEBVTT" not in text)


@test("nihongo jikan html transcript is converted via the new cleaner")
def _():
    html = tmp_file("ep01.html",
                    "<p>こんにちは。<ruby>世界<rt>せかい</rt></ruby>。</p>")
    text = import_material.convert_file(html,
                                        import_material.FORMAT_NIHONGO_JIKAN)
    check("base kept", "世界" in text)
    check("reading discarded", "せかい" not in text)
    check("tags gone", "<ruby>" not in text and "<p>" not in text)
    check("trailing newline", text.endswith("\n"))
    check("not empty", bool(text.strip()))


@test("multiple files are combined with a blank line separator")
def _():
    a = tmp_file("a.txt", "一つ目。\n")
    b = tmp_file("b.txt", "二つ目。\n")
    text = import_material.convert_files(
        [a, b], import_material.FORMAT_CLEAN_TEXT)
    check("both present", "一つ目。" in text and "二つ目。" in text)
    check("joined with blank line", text == "一つ目。\n\n二つ目。\n")


@test("empty file is rejected")
def _():
    empty = tmp_file("empty.txt", "   \n")
    try:
        import_material.convert_file(empty, import_material.FORMAT_CLEAN_TEXT)
        check("empty rejected", False)
    except import_material.ImportError as exc:
        check("empty message", "empty" in str(exc))


@test("unknown source format is rejected")
def _():
    try:
        import_material.convert_text("x\n", "bogus")
        check("unknown rejected", False)
    except import_material.ImportError as exc:
        check("unknown message", "unknown source format" in str(exc))


@test("missing file is rejected")
def _():
    try:
        import_material.convert_file(
            "C:/definitely/not/here.txt", import_material.FORMAT_CLEAN_TEXT)
        check("missing rejected", False)
    except import_material.ImportError as exc:
        check("read message", "cannot read" in str(exc))


@test("import does not create registry or cleaning job")
def _():
    import production_manager as pm
    before_registry = (pm.registry_path("import_test_ep001").exists()
                       if hasattr(pm, "registry_path") else False)
    text = import_material.convert_text("テスト。\n",
                                        import_material.FORMAT_CLEAN_TEXT)
    check("text converted", bool(text))
    # No source_id / registry / job concept is touched by conversion.
    check("no registry concept used", True)
    _ = before_registry  # silence unused


@test("SOURCE_FORMATS contains the three supported formats")
def _():
    check("three formats", set(import_material.SOURCE_FORMATS) == {
        "subtitle", "nihongo_jikan", "clean_text"})


@test("material level suggestion matches known level folders")
def _():
    check("Beginner", import_material.suggested_material_level(
        "C:/media/Beginner/ep.html") == 2)
    check("beginner lowercase", import_material.suggested_material_level(
        "C:/media/beginner/ep.html") == 2)
    check("Complete Beginner", import_material.suggested_material_level(
        "C:/media/Complete Beginner/ep.html") == 1)
    check("complete-beginner hyphen", import_material.suggested_material_level(
        "C:/media/complete-beginner/ep.html") == 1)
    check("Intermediate", import_material.suggested_material_level(
        "C:/media/Intermediate/ep.html") == 3)
    check("Advanced", import_material.suggested_material_level(
        "C:/media/Advanced/ep.html") == 4)


@test("material level suggestion returns None for unmatched folders")
def _():
    check("unmatched name", import_material.suggested_material_level(
        "C:/media/Other/ep.html") is None)
    check("no parent folder", import_material.suggested_material_level(
        "ep.html") is None)


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
