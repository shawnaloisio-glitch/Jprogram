#!/usr/bin/env python3
"""
test_output_writer.py

Deterministic tests for output_writer.

Run:
    python Analysis/tests/test_output_writer.py
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ANALYSIS = PROJECT_ROOT / "Analysis"
sys.path.insert(0, str(ANALYSIS))

import output_writer as ow


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("JSON output written correctly")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "out.json"
    data = {"b": 2, "a": 1, "nested": {"z": 26, "y": 25}}
    ow.write_json(path, data)
    parsed = json.loads(path.read_text(encoding="utf-8"))
    check("data round-trips", parsed == data)


@test("JSONL output written correctly")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "out.jsonl"
    records = [{"a": 1}, {"b": 2}, {"c": 3}]
    ow.write_jsonl(path, records)
    lines = path.read_text(encoding="utf-8").splitlines()
    check("three lines", len(lines) == 3)
    check("each line valid JSON",
          [json.loads(line) for line in lines] == records)


@test("Japanese characters preserved")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "out.json"
    data = {"sentence": "折り紙でゴミ箱を作ろう", "words": ["折り紙", "ゴミ箱"]}
    ow.write_json(path, data)
    raw = path.read_text(encoding="utf-8")
    check("characters present", "折り紙でゴミ箱を作ろう" in raw)
    check("no ascii escapes", "\\u" not in raw)
    path2 = pathlib.Path(tempfile.mkdtemp()) / "out.jsonl"
    ow.write_jsonl(path2, [data])
    raw2 = path2.read_text(encoding="utf-8")
    check("jsonl characters present", "折り紙でゴミ箱を作ろう" in raw2)
    check("jsonl no ascii escapes", "\\u" not in raw2)


@test("key ordering stable")
def _():
    data = {"z": 1, "a": 2, "m": 3}
    path = pathlib.Path(tempfile.mkdtemp()) / "out.json"
    ow.write_json(path, data)
    expected = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=4) + "\n"
    check("json keys sorted", path.read_text(encoding="utf-8") == expected)

    path2 = pathlib.Path(tempfile.mkdtemp()) / "out.jsonl"
    records = [{"b": 1, "a": 2}]
    ow.write_jsonl(path2, records)
    line = path2.read_text(encoding="utf-8").strip()
    expected_line = json.dumps(records[0], ensure_ascii=False, sort_keys=True)
    check("jsonl keys sorted", line == expected_line)


@test("repeated writes produce byte-identical files")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "out.json"
    data = {"key": "value", "n": 1}
    ow.write_json(path, data)
    first = path.read_bytes()
    ow.write_json(path, data)  # overwrite
    second = path.read_bytes()
    check("overwrite byte-identical", first == second)

    path2 = pathlib.Path(tempfile.mkdtemp()) / "out2.json"
    ow.write_json(path2, data)
    check("separate files identical", first == path2.read_bytes())


@test("input ordering preserved")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "out.jsonl"
    records = [{"id": 5}, {"id": 2}, {"id": 9}]
    ow.write_jsonl(path, records)
    lines = path.read_text(encoding="utf-8").splitlines()
    ids = [json.loads(line)["id"] for line in lines]
    check("order preserved", ids == [5, 2, 9], str(ids))


@test("invalid serialization raises clear error")
def _():
    bad_data = {"set": {1, 2}}  # set is not JSON-serializable
    path = pathlib.Path(tempfile.mkdtemp()) / "out.json"
    raised = False
    message = ""
    try:
        ow.write_json(path, bad_data)
    except ow.OutputWriteError as ex:
        raised = True
        message = str(ex)
    check("json raises", raised)
    check("clear message", "serializable" in message, message)

    path2 = pathlib.Path(tempfile.mkdtemp()) / "out.jsonl"
    raised2 = False
    message2 = ""
    try:
        ow.write_jsonl(path2, [{"ok": 1}, {"bad": {1, 2}}])
    except ow.OutputWriteError as ex:
        raised2 = True
        message2 = str(ex)
    check("jsonl raises", raised2)
    check("jsonl reports record index", "record 1" in message2, message2)


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
