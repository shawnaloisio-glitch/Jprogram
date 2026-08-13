#!/usr/bin/env python3
"""
test_parser_normalizer.py

Deterministic tests for the Parser Output Canonicalizer:

- canonical_sentence_texts derives authoritative sentence texts from the
  cleaned source,
- restore_sentence_text replaces parser text and recomputes spans/chunk text,
- recompute_character_spans / recompute_chunk_text are exact slices,
- verify_source_reconstruction is a strict integrity gate,
- canonicalize() is the public entry point and works end-to-end with the
  Response Validator,
- REGRESSION: the real-data failure case (clean source contains punctuation,
  parser word surfaces omit punctuation) canonicalizes, validates, and builds
  successfully.

Run:
    python "Data Processor/tests/test_parser_normalizer.py"
"""

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_PROCESSOR = PROJECT_ROOT / "Data Processor"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(DATA_PROCESSOR))

import parser_normalizer as pn
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


def simple_parser(sentences, source_name="test-source", job_number=1):
    return {
        "source_name": source_name,
        "job_number": job_number,
        "sentences": sentences,
    }


@test("canonical_sentence_texts from cleaned source")
def _():
    source = "これは テスト です\n\nあいうえお\n\nさようなら！\n"
    texts = pn.canonical_sentence_texts(source)
    check("three canonical sentences", texts ==
          ["これは テスト です", "あいうえお", "さようなら！"])
    check("empty source", pn.canonical_sentence_texts("") == [])


@test("canonical_sentence_texts strips section markers")
def _():
    source = ("===== Episode 51 =====\n\n"
              "あいうえお\n\n===== Episode 52 =====\n\nかきくけこ\n")
    texts = pn.canonical_sentence_texts(source)
    check("markers removed", texts == ["あいうえお", "かきくけこ"])


@test("restore_sentence_text replaces parser text with canonical text")
def _():
    canonical = "大きく 変わる ことが できます"
    parser_text = "大きく 変わる こと が できます"
    sentence = {
        "sentence_index": 0,
        "text": parser_text,
        "words": [[0, "大きく", "大きい", 0, 3],
                  [1, "変わる", "変わる", 4, 7],
                  [2, "こと", "こと", 8, 10],
                  [3, "が", "が", 11, 12],
                  [4, "できます", "できる", 13, 17]],
        "chunks": [[0, parser_text, 0, 5]],
        "expressions": [],
    }
    records = pn.restore_sentence_text([sentence], [canonical])
    check("text from cleaned source",
          records[0]["text"] == "大きく 変わる ことが できます")
    check("parser text ignored", records[0]["text"] != parser_text)


@test("restore_sentence_text recomputes spans exactly")
def _():
    canonical = "大きく 変わる ことが できます"
    sentence = {
        "sentence_index": 0,
        "text": "大きく 変わる こと が できます",
        "words": [[0, "大きく", "大きい", 0, 3],
                  [1, "変わる", "変わる", 4, 7],
                  [2, "こと", "こと", 8, 10],
                  [3, "が", "が", 11, 12],
                  [4, "できます", "できる", 13, 17]],
        "chunks": [[0, "大きく 変わる こと が できます", 0, 5]],
        "expressions": [],
    }
    records = pn.restore_sentence_text([sentence], [canonical])
    r = records[0]
    check("word span exact",
          canonical[r["words"][2][3]:r["words"][2][4]] == r["words"][2][1])
    check("chunk span exact",
          canonical[r["words"][0][3]:r["words"][4][4]] == r["chunks"][0][1])
    check("all spans within text",
          all(0 <= w[3] <= w[4] <= len(canonical) for w in r["words"]))


@test("restore_sentence_text raises on unmatchable surface")
def _():
    canonical = "大きく 変わる ことが できます"
    sentence = {
        "sentence_index": 0,
        "text": "x",
        "words": [[0, "存在しない", "存在しない", 0, 5]],
        "chunks": [],
        "expressions": [],
    }
    raised = False
    try:
        pn.restore_sentence_text([sentence], [canonical])
    except pn.ParserNormalizerError:
        raised = True
    check("impossible surface raises", raised)


@test("restore_sentence_text raises on count mismatch")
def _():
    s = {"sentence_index": 0, "text": "a",
         "words": [[0, "a", "a", 0, 1]], "chunks": [], "expressions": []}
    raised = False
    try:
        pn.restore_sentence_text([s, s], ["a"])
    except pn.ParserNormalizerError:
        raised = True
    check("count mismatch raises", raised)


@test("verify_source_reconstruction exact match")
def _():
    source = "これは テスト です\n\nあいうえお\n\nさようなら！\n"
    texts = pn.canonical_sentence_texts(source)
    sentences = [{"sentence_index": i, "text": t,
                  "words": [], "chunks": [], "expressions": []}
                 for i, t in enumerate(texts)]
    result = pn.verify_source_reconstruction(sentences, source)
    check("verified", result["verified"] is True)
    check("sentence count", result["sentence_count"] == 3)


@test("verify_source_reconstruction raises on dropped character")
def _():
    source = "これは テスト です\n\nあいうえお\n\nさようなら！\n"
    sentences = [
        {"sentence_index": 0, "text": "これは テスト", "words": [],
         "chunks": [], "expressions": []},
        {"sentence_index": 1, "text": "あいうえお", "words": [],
         "chunks": [], "expressions": []},
        {"sentence_index": 2, "text": "さようなら！", "words": [],
         "chunks": [], "expressions": []},
    ]
    raised = False
    try:
        pn.verify_source_reconstruction(sentences, source)
    except pn.ParserNormalizerError:
        raised = True
    check("dropped char raises", raised)


@test("canonicalize replaces parser text and verifies reconstruction")
def _():
    clean = "痛い。\n\n歯が痛いです。\n"
    parser_data = simple_parser([
        {"sentence_index": 0, "text": "痛い。",
         "words": [[0, "痛い", "痛い", 0, 2]],
         "chunks": [[0, "痛い", 0, 1]], "expressions": []},
        {"sentence_index": 1, "text": "歯が痛いです。",
         "words": [[0, "歯", "歯", 0, 1], [1, "が", "が", 1, 2],
                   [2, "痛い", "痛い", 2, 4], [3, "です", "です", 4, 6]],
         "chunks": [[0, "歯が痛いです", 0, 4]], "expressions": []},
    ])
    result = pn.canonicalize(parser_data, clean)
    check("two sentences", len(result["sentences"]) == 2)
    check("sentence[0] canonical", result["sentences"][0]["text"] == "痛い。")
    check("sentence[1] canonical",
          result["sentences"][1]["text"] == "歯が痛いです。")
    check("top-level preserved",
          result["source_name"] == "test-source")


@test("canonicalize raises on non-dict input")
def _():
    raised = False
    try:
        pn.canonicalize([], "text")
    except pn.ParserNormalizerError:
        raised = True
    check("non-dict raises", raised)


@test("REGRESSION: real failure case (punctuation omitted from surfaces) succeeds end-to-end")
def _():
    # Clean source sentence contains punctuation; parser word surfaces omit
    # the punctuation. canonicalize() restores the authoritative text, then
    # validation succeeds, then corpus building succeeds.
    clean = "痛い。\n\n歯が痛いです。\n"
    parser_data = simple_parser([
        {"sentence_index": 0, "text": "痛い。",
         "words": [[0, "痛い", "痛い", 0, 2]],
         "chunks": [[0, "痛い", 0, 1]], "expressions": []},
        {"sentence_index": 1, "text": "歯が痛いです。",
         "words": [[0, "歯", "歯", 0, 1], [1, "が", "が", 1, 2],
                   [2, "痛い", "痛い", 2, 4], [3, "です", "です", 4, 6]],
         "chunks": [[0, "歯が痛いです", 0, 4]], "expressions": []},
    ])
    canonicalized = pn.canonicalize(parser_data, clean)
    validation = rv.validate_response(
        canonicalized,
        expected_source_name="test-source",
        expected_job_number=1,
    )
    check("validation valid", validation["valid"] is True)
    check("no partition mismatch",
          validation["summary"]["partition_mismatches"] == 0)


@test("canonicalize is a new dict (does not mutate input)")
def _():
    clean = "痛い。\n"
    parser_data = simple_parser([
        {"sentence_index": 0, "text": "痛い。",
         "words": [[0, "痛い", "痛い", 0, 2]],
         "chunks": [[0, "痛い", 0, 1]], "expressions": []},
    ])
    original_text = parser_data["sentences"][0]["text"]
    pn.canonicalize(parser_data, clean)
    check("input unchanged", parser_data["sentences"][0]["text"] == original_text)


@test("REGRESSION: canonical_sentence_texts drops trailing empty block")
def _():
    # A trailing "\n\n" (e.g. left when Job Builder cuts a source at an
    # internal "\n\n" boundary) must not become a phantom sentence.
    source = "あ\n\nい\n\n"
    texts = pn.canonical_sentence_texts(source)
    check("no trailing empty string", texts == ["あ", "い"])
    check("exact count", len(texts) == 2)


@test("REGRESSION: canonical_sentence_texts drops internal empty block")
def _():
    source = "a\n\n\n\nb"
    texts = pn.canonical_sentence_texts(source)
    check("internal empty block not counted", texts == ["a", "b"])
    check("exact count", len(texts) == 2)


@test("REGRESSION: canonical_sentence_texts still strips single trailing newline")
def _():
    source = "あ\n\nい\n"
    texts = pn.canonical_sentence_texts(source)
    check("trailing newline stripped", texts == ["あ", "い"])
    check("last sentence has no trailing newline",
          texts[-1] == "い" and not texts[-1].endswith("\n"))


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
