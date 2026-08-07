#!/usr/bin/env python3
"""
test_subtitle_importer_cleaner.py

Deterministic tests for the Subtitle Importer cleaner:

- srt timestamp removal
- vtt timestamp removal
- numbering removal
- markup removal
- Japanese text preservation
- output filename generation
- empty subtitle handling
- malformed subtitle handling

Run:
    python "Subtitle Importer/tests/test_subtitle_importer_cleaner.py"
"""

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SUBTITLE_IMPORTER = PROJECT_ROOT / "Subtitle Importer"
sys.path.insert(0, str(SUBTITLE_IMPORTER))

import cleaner

SAMPLE_SRT = """1
00:00:01,000 --> 00:00:03,500
こんにちは。お元気ですか。

2
00:00:04,000 --> 00:00:06,500
はい、元気です。
"""

SAMPLE_VTT = """WEBVTT

00:00:01.000 --> 00:00:03.500
こんにちは。お元気ですか。

00:00:04.000 --> 00:00:06.500
はい、元気です。
"""


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
# SRT
# ============================================================

@test("srt: timestamps and numbering removed, Japanese preserved")
def _():
    cleaned = cleaner.clean_text(SAMPLE_SRT, "srt")
    check("no timestamp", "00:00" not in cleaned)
    check("no sequence number 1", "1\nこんにちは" not in cleaned)
    check("keeps dialogue 1a", "こんにちは。" in cleaned)
    check("keeps dialogue 1b", "お元気ですか。" in cleaned)
    check("keeps dialogue 2", "はい、元気です。" in cleaned)
    check("exact output",
          cleaned == "こんにちは。\n\nお元気ですか。\n\nはい、元気です。")


@test("srt: markup tags removed")
def _():
    content = """1
00:00:01,000 --> 00:00:02,000
<i>おはよう。</i>
"""
    cleaned = cleaner.clean_text(content, "srt")
    check("no i tag", "<i>" not in cleaned and "</i>" not in cleaned)
    check("keeps text", "おはよう。" in cleaned)


@test("srt: positioning markers removed")
def _():
    content = """1
00:00:01,000 --> 00:00:02,000
{\\an8}こんにちは。
"""
    cleaned = cleaner.clean_text(content, "srt")
    check("no positioning marker", "{\\an8}" not in cleaned)
    check("keeps text", "こんにちは。" in cleaned)


@test("srt: multi-line cue with two full sentences splits into two cues")
def _():
    content = """1
00:00:01,000 --> 00:00:02,000
これは一行目。
これは二行目。
"""
    cleaned = cleaner.clean_text(content, "srt")
    check("line one", "これは一行目。" in cleaned)
    check("line two", "これは二行目。" in cleaned)
    check("separate cues", cleaned == "これは一行目。\n\nこれは二行目。")


@test("srt: two sentences in one cue split into two separate cues")
def _():
    content = """1
00:00:01,000 --> 00:00:02,000
通りません。はい。
"""
    cleaned = cleaner.clean_text(content, "srt")
    check("split into two cues", cleaned == "通りません。\n\nはい。")


@test("srt: one sentence wrapped across two display lines stays one entry")
def _():
    content = """1
00:00:01,000 --> 00:00:02,000
これは長い一つの
文です。
"""
    cleaned = cleaner.clean_text(content, "srt")
    check("single entry", cleaned == "これは長い一つの\n文です。")
    check("no leading/trailing newline artifact",
          not cleaned.startswith("\n") and not cleaned.endswith("\n"))
    check("not fragmented into two entries", "\n\n" not in cleaned)


# ============================================================
# VTT
# ============================================================

@test("vtt: timestamps removed, Japanese preserved")
def _():
    cleaned = cleaner.clean_text(SAMPLE_VTT, "vtt")
    check("no timestamp", "00:00" not in cleaned)
    check("no webvtt header", "WEBVTT" not in cleaned)
    check("keeps dialogue 1a", "こんにちは。" in cleaned)
    check("keeps dialogue 1b", "お元気ですか。" in cleaned)
    check("keeps dialogue 2", "はい、元気です。" in cleaned)


@test("vtt: two sentences in one cue split into two separate cues")
def _():
    content = """WEBVTT

00:00:01.000 --> 00:00:02.000
通りません。はい。
"""
    cleaned = cleaner.clean_text(content, "vtt")
    check("split into two cues", cleaned == "通りません。\n\nはい。")


@test("vtt: one sentence wrapped across two display lines stays one entry")
def _():
    content = """WEBVTT

00:00:01.000 --> 00:00:02.000
これは長い一つの
文です。
"""
    cleaned = cleaner.clean_text(content, "vtt")
    check("single entry", cleaned == "これは長い一つの\n文です。")
    check("no leading/trailing newline artifact",
          not cleaned.startswith("\n") and not cleaned.endswith("\n"))
    check("not fragmented into two entries", "\n\n" not in cleaned)


@test("vtt: html tags and cue settings removed")
def _():
    content = """WEBVTT

00:00:01.000 --> 00:00:02.000 align:middle position:50%
<b>おはよう。</b>
"""
    cleaned = cleaner.clean_text(content, "vtt")
    check("no b tag", "<b>" not in cleaned)
    check("no cue settings", "align:middle" not in cleaned)
    check("keeps text", "おはよう。" in cleaned)


# ============================================================
# Shared cleaning rules
# ============================================================

@test("clean_text: empty content yields empty string")
def _():
    check("empty srt", cleaner.clean_text("", "srt") == "")
    check("empty vtt", cleaner.clean_text("", "vtt") == "")
    check("only whitespace", cleaner.clean_text("   \n\n ", "srt") == "")


@test("clean_text: malformed srt tolerates stray blocks")
def _():
    content = """1
00:00:01,000 --> 00:00:02,000
こんにちは。

この行は数字だけでない。
"""
    cleaned = cleaner.clean_text(content, "srt")
    check("keeps first cue", "こんにちは。" in cleaned)
    check("tolerates stray text", "この行は数字だけでない。" in cleaned)


@test("clean_text: unsupported format rejected")
def _():
    try:
        cleaner.clean_text("x", "ass")
        check("unsupported rejected", False)
    except cleaner.CleanError:
        pass


@test("detect_format: known and unknown extensions")
def _():
    check("srt", cleaner.detect_format("episode01.srt") == "srt")
    check("vtt", cleaner.detect_format("episode01.vtt") == "vtt")
    check("uppercase ok", cleaner.detect_format("EP.SRT") == "srt")
    try:
        cleaner.detect_format("episode01.ass")
        check("unknown rejected", False)
    except cleaner.CleanError:
        pass


@test("supported_formats lists srt and vtt")
def _():
    check("formats", cleaner.supported_formats() == ["srt", "vtt"])


# ============================================================
# Output filename generation
# ============================================================

@test("output filename: preserves base name, changes extension")
def _():
    check("srt to txt", cleaner.output_filename("episode01.srt")
          == "episode01.txt")
    check("vtt to txt", cleaner.output_filename("episode01.vtt")
          == "episode01.txt")
    check("path input", cleaner.output_filename("C:/x/episode01.srt")
          == "episode01.txt")


@test("output path: under Intake dir")
def _():
    path = cleaner.output_path("episode01.srt")
    check("under intake", str(path.parent).endswith("Intake"))
    check("name", path.name == "episode01.txt")


@test("save_clean_text writes Intake file with atomic write")
def _():
    import tempfile
    out_dir = pathlib.Path(tempfile.mkdtemp())
    target = cleaner.save_clean_text("episode01.srt", "こんにちは。\n",
                                     output_dir=out_dir)
    check("target name", target.name == "episode01.txt")
    check("file exists", target.is_file())
    check("content", target.read_text(encoding="utf-8") == "こんにちは。\n")
    check("no .tmp", not target.with_name(target.name + ".tmp").exists())


@test("clean_file reads a real file")
def _():
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp())
    src = tmp / "episode01.srt"
    src.write_text(SAMPLE_SRT, encoding="utf-8")
    fmt, cleaned = cleaner.clean_file(src)
    check("format", fmt == "srt")
    check("cleaned", "こんにちは。" in cleaned)


@test("clean_file: missing file raises CleanError")
def _():
    try:
        cleaner.clean_file("C:/definitely/not/here.srt")
        check("missing file rejected", False)
    except cleaner.CleanError:
        pass


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
