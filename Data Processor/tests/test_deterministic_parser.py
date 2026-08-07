#!/usr/bin/env python3
"""
test_deterministic_parser.py

Deterministic tests for the GiNZA/spaCy deterministic parser.

Run (must use the project venv; spacy/ginza are not installed globally):
    "Jprogram/.venv/Scripts/python.exe" "Data Processor/tests/test_deterministic_parser.py"
"""

import json
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_PROCESSOR = PROJECT_ROOT / "Data Processor"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(DATA_PROCESSOR))

import deterministic_parser as dp
import response_validator as rv


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


def parse(text, source_name="test-source", job_number=1):
    return dp.parse_job(source_name, job_number, text)


@test("split_sentences: punctuation marks boundaries, punctuation attached")
def _():
    check("splits at 。",
          dp.split_sentences("これはテストです。次にこれです。")
          == ["これはテストです。", "次にこれです。"])
    check("splits at ！？",
          dp.split_sentences("本当に？本当だ！")
          == ["本当に？", "本当だ！"])


@test("split_sentences: no punctuation means whole line is one sentence")
def _():
    check("single line",
          dp.split_sentences("これはテストです") == ["これはテストです"])
    check("multiple lines",
          dp.split_sentences("これはテストです\n\nあいうえお\n")
          == ["これはテストです", "あいうえお"])


@test("split_sentences: mixed punctuation and punctuation-free lines")
def _():
    check("mixed", dp.split_sentences("A。B。\n\nC") == ["A。", "B。", "C"])


@test("split_sentences: section marker lines are not sentences")
def _():
    check("markers removed",
          dp.split_sentences("===== Episode 1 =====\n\nあいうえお\n\nかきくけこ\n")
          == ["あいうえお", "かきくけこ"])


@test("split_sentences: consecutive sentence-final punctuation coalesced")
def _():
    check("本当に？！", dp.split_sentences("本当に？！") == ["本当に？！"])
    check("two ！！", dp.split_sentences("すごい！！") == ["すごい！！"])


@test("split_sentences: empty input gives empty list")
def _():
    check("empty", dp.split_sentences("") == [])


@test("PART1: 食べました/食べません/食べて/食べる each ONE word, lexical 食べる")
def _():
    result = parse("食べました。\n\n食べません。\n\n食べて。\n\n食べる。\n")
    sents = result["sentences"]
    check("four sentences", len(sents) == 4, str(len(sents)))
    expected_surfaces = ["食べました", "食べません", "食べて", "食べる"]
    for s, exp in zip(sents, expected_surfaces):
        check("one merged word", len(s["words"]) == 1, str(s["words"]))
        check("surface " + exp, s["words"][0][1] == exp, str(s["words"][0]))
        check("lexical 食べる", s["words"][0][2] == "食べる", str(s["words"][0]))


@test("PART2: 勉強する merges into ONE word")
def _():
    result = parse("勉強する。\n")
    s = result["sentences"][0]
    check("one word", len(s["words"]) == 1, str(s["words"]))
    check("surface 勉強する", s["words"][0][1] == "勉強する", str(s["words"][0]))
    check("lexical 勉強", s["words"][0][2] == "勉強", str(s["words"][0]))
    check("span", s["text"][s["words"][0][3]:s["words"][0][4]] == "勉強する")


@test("PART3: ついて merges into ONE word, lexical つく")
def _():
    result = parse("ついて。\n")
    s = result["sentences"][0]
    check("one word", len(s["words"]) == 1, str(s["words"]))
    check("surface ついて", s["words"][0][1] == "ついて", str(s["words"][0]))
    check("lexical つく", s["words"][0][2] == "つく", str(s["words"][0]))
    check("span", s["text"][s["words"][0][3]:s["words"][0][4]] == "ついて")


@test("PART4: simple noun+particle+verb needs no merge")
def _():
    result = parse("犬が走る。\n")
    s = result["sentences"][0]
    surfaces = [w[1] for w in s["words"]]
    check("per-token words", surfaces == ["犬", "が", "走る"], str(surfaces))
    check("lexicals", [w[2] for w in s["words"]] == ["犬", "が", "走る"])


@test("PART5: every word satisfies text[char_start:char_end] == surface")
def _():
    clean = (
        "犬が走る。\n\n食べてください。\n\nコーヒー を 飲んでます。\n\n"
        "勉強しています。\n\nついて。\n\n食べました。\n\n本当に？\n"
    )
    result = parse(clean)
    for s in result["sentences"]:
        text = s["text"]
        for w in s["words"]:
            check("span equals surface",
                  text[w[3]:w[4]] == w[1],
                  f"{w[1]!r} vs {text[w[3]:w[4]]!r} in {text!r}")
            check("span within bounds", 0 <= w[3] <= w[4] <= len(text))


@test("PART6: chunk mapping references post-merge word indices")
def _():
    result = parse("犬が走る。\n")
    s = result["sentences"][0]
    chunks = s["chunks"]
    check("two chunks", len(chunks) == 2, str(chunks))
    check("chunk0 犬が words 0-2",
          chunks[0][1] == "犬が" and chunks[0][2] == 0 and chunks[0][3] == 2,
          str(chunks[0]))
    check("chunk1 走る words 2-3",
          chunks[1][1] == "走る" and chunks[1][2] == 2 and chunks[1][3] == 3,
          str(chunks[1]))
    check("chunk text verbatim",
          s["text"][s["words"][chunks[0][2]][3]:s["words"][chunks[0][3] - 1][4]]
          == chunks[0][1])


@test("PART6: merged words make one chunk across post-merge words")
def _():
    result = parse("食べてください。\n")
    s = result["sentences"][0]
    check("two post-merge words", len(s["words"]) == 2, str(s["words"]))
    check("word surfaces", [w[1] for w in s["words"]] == ["食べて", "ください"])
    chunks = s["chunks"]
    check("one chunk spanning both words",
          len(chunks) == 1
          and chunks[0][1] == "食べてください"
          and chunks[0][2] == 0
          and chunks[0][3] == 2,
          str(chunks))


@test("PART7: whitespace-delimited input preserves space units exactly")
def _():
    result = parse("コーヒー を 飲んでます。\n")
    s = result["sentences"][0]
    surfaces = [w[1] for w in s["words"]]
    check("surfaces match space units",
          surfaces == ["コーヒー", "を", "飲んでます"], str(surfaces))
    check("lexicals", [w[2] for w in s["words"]] == ["コーヒー", "を", "飲む"])
    check("offsets", [w[3:5] for w in s["words"]] == [[0, 4], [5, 6], [7, 12]],
          str(s["words"]))


@test("PART7: whitespace units are never re-segmented across spaces")
def _():
    result = parse("テキスト を 書いて おきます。\n")
    s = result["sentences"][0]
    surfaces = [w[1] for w in s["words"]]
    check("units preserved", surfaces == ["テキスト", "を", "書いて", "おきます"],
          str(surfaces))


@test("aux chain: 食べている is two words 食べて+いる with correct lemmas")
def _():
    result = parse("食べている。\n")
    s = result["sentences"][0]
    words = s["words"]
    check("two words", len(words) == 2, str(words))
    check("surfaces", [w[1] for w in words] == ["食べて", "いる"], str(words))
    check("lemmas", [w[2] for w in words] == ["食べる", "いる"], str(words))
    chunks = s["chunks"]
    check("one bunsetu chunk spanning both words",
          len(chunks) == 1
          and chunks[0][1] == "食べている"
          and chunks[0][2] == 0
          and chunks[0][3] == 2,
          str(chunks))


@test("aux chain: 持ってきた is two words 持って+きた with correct lemmas")
def _():
    result = parse("持ってきた。\n")
    s = result["sentences"][0]
    words = s["words"]
    check("two words", len(words) == 2, str(words))
    check("surfaces", [w[1] for w in words] == ["持って", "きた"], str(words))
    check("lemmas", [w[2] for w in words] == ["持つ", "くる"], str(words))
    chunks = s["chunks"]
    check("two bunsetu chunks (持って / きた)",
          len(chunks) == 2
          and chunks[0] == [0, "持って", 0, 1]
          and chunks[1] == [1, "きた", 1, 2],
          str(chunks))


@test("aux chain: 書いてしまった is two words 書いて+しまった")
def _():
    result = parse("書いてしまった。\n")
    s = result["sentences"][0]
    words = s["words"]
    check("two words", len(words) == 2, str(words))
    check("surfaces", [w[1] for w in words] == ["書いて", "しまった"], str(words))
    check("lemmas", [w[2] for w in words] == ["書く", "しまう"], str(words))
    chunks = s["chunks"]
    check("one bunsetu chunk spanning both words",
          len(chunks) == 1
          and chunks[0][1] == "書いてしまった"
          and chunks[0][2] == 0
          and chunks[0][3] == 2,
          str(chunks))


@test("parse_job returns full contract-shaped dict")
def _():
    result = dp.parse_job("podcast_test_ep001", 3, "犬が走る。\n\n食べています。\n")
    check("source_name", result["source_name"] == "podcast_test_ep001")
    check("job_number", result["job_number"] == 3)
    check("sentence_index 0-based",
          [s["sentence_index"] for s in result["sentences"]] == [0, 1])
    check("expressions always empty",
          all(s["expressions"] == [] for s in result["sentences"]))
    check("words are 5-column arrays",
          all(len(w) == 5 for s in result["sentences"] for w in s["words"]))
    check("chunks are 4-column arrays",
          all(len(c) == 4 for s in result["sentences"] for c in s["chunks"]))


@test("output is JSON-serializable")
def _():
    result = dp.parse_job("src", 1, "犬が走る。\n\nコーヒー を 飲んでます。\n")
    dumped = json.dumps(result, ensure_ascii=False)
    loaded = json.loads(dumped)
    check("round-trip", loaded == result)


@test("chunks are flat, non-overlapping, and ordered in every sentence")
def _():
    clean = (
        "犬が走る。\n\n食べてください。\n\nコーヒー を 飲んでます。\n\n"
        "勉強しています。\n\nついて。\n\n雨が降るでしょう。\n"
    )
    result = parse(clean)
    for s in result["sentences"]:
        chunks = s["chunks"]
        prev_end = -1
        for c in chunks:
            check("chunk span valid",
                  c[2] >= 0 and c[3] > c[2] and c[3] <= len(s["words"]),
                  str(c))
            check("chunk ordered", c[2] >= prev_end, str(c))
            prev_end = c[3]


@test("module output passes response_validator")
def _():
    result = dp.parse_job(
        "src", 1,
        "犬が走る。\n\n食べてください。\n\nコーヒー を 飲んでます。\n\n"
        "勉強しています。\n",
    )
    v = rv.validate_response(result, expected_source_name="src", expected_job_number=1)
    check("valid", v["valid"] is True, str(v["errors"]))
    check("no partition mismatch", v["summary"]["partition_mismatches"] == 0)
    check("no char span errors", v["summary"]["char_span_errors"] == 0)
    check("no fatal errors", v["summary"]["fatal_errors"] == 0)


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
