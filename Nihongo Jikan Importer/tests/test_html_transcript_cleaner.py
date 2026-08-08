#!/usr/bin/env python3
"""
test_html_transcript_cleaner.py

Deterministic tests for the Nihongo Jikan HTML transcript cleaner:

- bare <p> with ruby keeps base, discards furigana reading,
- attributed <p class="..."> is discarded (widget noise),
- HTML entity unescaping,
- a file mixing real content and a trailing Copyright Info widget,
- sentence splitting reuses Common/sentence_split.py,
- empty / malformed input handling,
- clean_file reads a real file; missing file raises CleanError.

Fixtures are constructed inline; no real files are copied into the repo.

Run:
    python "Nihongo Jikan Importer/tests/test_html_transcript_cleaner.py"
"""

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
NIHONGO_JIKAN = PROJECT_ROOT / "Nihongo Jikan Importer"
sys.path.insert(0, str(NIHONGO_JIKAN))

import html_transcript_cleaner as cleaner


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("bare p with ruby keeps base text and discards the reading")
def _():
    content = ("<html><body>"
               "<p><ruby>世界<rt>せかい</rt></ruby>へ行きます。</p>"
               "</body></html>")
    cleaned = cleaner.clean_text(content)
    check("base kept", "世界" in cleaned)
    check("reading discarded", "せかい" not in cleaned)
    check("ruby tags gone", "<ruby>" not in cleaned and "<rt>" not in cleaned)
    check("exact output", cleaned == "世界へ行きます。")


@test("attributed p is discarded entirely")
def _():
    content = ("<p>本物の文です。</p>\n"
               "<p class=\"copyright\">Copyright 2026</p>")
    cleaned = cleaner.clean_text(content)
    check("real kept", "本物の文です。" in cleaned)
    check("widget discarded", "Copyright 2026" not in cleaned)
    check("exact output", cleaned == "本物の文です。")


@test("html entities are unescaped")
def _():
    content = ("<p>Fish &amp; Chips &quot; quoted &#x27;single&#x27; "
               "&euro;10</p>")
    cleaned = cleaner.clean_text(content)
    check("amp", "Fish & Chips" in cleaned)
    check("quot", '" quoted' in cleaned)
    check("apos", "'single'" in cleaned)
    check("named numeric", "\u20ac10" in cleaned)


@test("file mixing real content and a trailing Copyright Info widget")
def _():
    content = """<!DOCTYPE html>
<html>
<head><title>Episode 01</title></head>
<body>
<p>今朝はいい天気ですね。</p>
<p><ruby>神社<rt>じんじゃ</rt></ruby>へ行きます。</p>
<div class="copyright-info">
  <details>
    <summary>Credits</summary>
    <p class="credit">Video: <a href="#">source</a></p>
    <p class="credit">Image by <span>someone</span></p>
    <svg width="10" height="10"><circle cx="5" cy="5" r="4"/></svg>
  </details>
</div>
</body>
</html>"""
    cleaned = cleaner.clean_text(content)
    check("sentence one", "今朝はいい天気ですね。" in cleaned)
    check("sentence two", "神社へ行きます。" in cleaned)
    check("reading discarded", "じんじゃ" not in cleaned)
    check("widget text discarded", "Credits" not in cleaned)
    check("widget credit discarded", "Image by" not in cleaned)
    check("no svg", "circle" not in cleaned and "svg" not in cleaned)
    check("no link", "source" not in cleaned)
    check("exact output",
          cleaned == "今朝はいい天気ですね。\n\n神社へ行きます。")


@test("two sentences inside one bare p split into separate entries")
def _():
    content = "<p>通りません。はい。</p>"
    cleaned = cleaner.clean_text(content)
    check("split", cleaned == "通りません。\n\nはい。")


@test("one sentence wrapped across two lines stays one entry")
def _():
    content = "<p>これは長い一つの\n文です。</p>"
    cleaned = cleaner.clean_text(content)
    check("single entry", cleaned == "これは長い一つの\n文です。")
    check("not fragmented", "\n\n" not in cleaned)


@test("empty content yields empty string")
def _():
    check("empty", cleaner.clean_text("") == "")
    check("only whitespace", cleaner.clean_text("   \n\n  ") == "")
    check("no bare p", cleaner.clean_text("<html><body></body></html>") == "")


@test("non-string content is rejected")
def _():
    try:
        cleaner.clean_text(None)
        check("non-string rejected", False)
    except cleaner.CleanError:
        pass


@test("clean_file reads a real html file")
def _():
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp())
    src = tmp / "episode01.html"
    src.write_text("<p>こんにちは。</p>", encoding="utf-8")
    fmt, cleaned = cleaner.clean_file(src)
    check("format", fmt == "html")
    check("cleaned", cleaned == "こんにちは。")


@test("clean_file: missing file raises CleanError")
def _():
    try:
        cleaner.clean_file("C:/definitely/not/here.html")
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
