#!/usr/bin/env python3
"""
test_hashing.py

Deterministic tests for hashing.py.

Run:
    python "Source Intake/tests/test_hashing.py"
"""

import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_INTAKE = PROJECT_ROOT / "Source Intake"
sys.path.insert(0, str(SOURCE_INTAKE))

import hashing


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("known file hash")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "a.txt"
    path.write_bytes(b"abc")
    expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    check("sha256 of 'abc'", hashing.sha256_file(path) == expected)


@test("changed content produces changed hash")
def _():
    d = pathlib.Path(tempfile.mkdtemp())
    a = d / "a.txt"
    a.write_bytes(b"abc")
    b = d / "b.txt"
    b.write_bytes(b"abcd")
    check("different hashes", hashing.sha256_file(a) != hashing.sha256_file(b))


@test("deterministic for identical content")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "a.txt"
    path.write_text("こんにちは。", encoding="utf-8")
    check("same hash twice", hashing.sha256_file(path) == hashing.sha256_file(path))


@test("returns 64 lowercase hex characters")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "a.txt"
    path.write_bytes(b"japanese corpus pipeline")
    digest = hashing.sha256_file(path)
    check("length 64", len(digest) == 64)
    check("hex only", all(c in "0123456789abcdef" for c in digest))


@test("missing file raises")
def _():
    path = pathlib.Path(tempfile.mkdtemp()) / "missing.txt"
    raised = False
    try:
        hashing.sha256_file(path)
    except FileNotFoundError:
        raised = True
    check("raises FileNotFoundError", raised)


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
