#!/usr/bin/env python3
"""
test_corpus_loader.py

Deterministic tests for corpus_loader.

Run:
    python Analysis/tests/test_corpus_loader.py
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ANALYSIS = PROJECT_ROOT / "Analysis"
sys.path.insert(0, str(ANALYSIS))

import corpus_loader as cl


def make_record(sentence_id, text):
    """A canonical-style record matching the Corpus Builder output."""
    return {
        "text": text,
        "ids": {"sentence_id": sentence_id},
        "provenance": {
            "source": "test-source",
            "source_file": "test-source.clean.txt",
            "job_number": 1,
            "model": "deepseek-v4-flash",
            "prompt_version": "1.0",
            "sentence_id": sentence_id,
            "sentence_position": sentence_id,
        },
        "section": "default",
        "words": [],
        "chunks": [],
        "expressions": [],
    }


def write_fixture(records, path):
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("valid JSONL loads correctly")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "corpus.jsonl"
    records = [make_record(0, "こんにちは。"), make_record(1, "ありがとう。")]
    write_fixture(records, path)
    loaded = cl.load_all(path)
    check("count", len(loaded) == 2)
    check("text 0", loaded[0]["text"] == "こんにちは。")
    check("text 1", loaded[1]["text"] == "ありがとう。")


@test("ordering preserved")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "corpus.jsonl"
    records = [make_record(5, "五"), make_record(2, "二"), make_record(9, "九")]
    write_fixture(records, path)
    loaded = cl.load_all(path)
    ids = [r["ids"]["sentence_id"] for r in loaded]
    check("order exactly as file", ids == [5, 2, 9], str(ids))


@test("repeated loads produce identical results")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "corpus.jsonl"
    records = [make_record(0, "a"), make_record(1, "b"), make_record(2, "c")]
    write_fixture(records, path)
    one = cl.load_all(path)
    two = cl.load_all(path)
    check("identical", one == two)


@test("invalid JSON raises")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "corpus.jsonl"
    path.write_text('{"text": "ok"}\nnot json\n', encoding="utf-8")
    raised = False
    message = ""
    try:
        cl.load_all(path)
    except cl.CorpusLoadError as ex:
        raised = True
        message = str(ex)
    check("raises CorpusLoadError", raised)
    check("reports line number", "line 2" in message, message)


@test("malformed record (non-object) raises")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "corpus.jsonl"
    path.write_text('{"text": "ok"}\n[1, 2, 3]\n', encoding="utf-8")
    raised = False
    try:
        cl.load_all(path)
    except cl.CorpusLoadError:
        raised = True
    check("raises CorpusLoadError", raised)


@test("missing file raises")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "missing.jsonl"
    raised = False
    try:
        cl.load_all(path)
    except FileNotFoundError:
        raised = True
    check("raises FileNotFoundError", raised)


@test("records are not modified")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "corpus.jsonl"
    records = [make_record(0, "元のテキスト。")]
    write_fixture(records, path)
    loaded = cl.load_all(path)
    check("text intact", loaded[0]["text"] == "元のテキスト。")
    check("ids intact", loaded[0]["ids"]["sentence_id"] == 0)
    check("no extra keys", set(loaded[0].keys()) == set(records[0].keys()))
    # two loads produce independent objects (no shared mutation)
    again = cl.load_all(path)
    check("independent objects", again[0] is not loaded[0])


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
