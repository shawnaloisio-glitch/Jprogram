#!/usr/bin/env python3
"""
test_paths.py

Deterministic tests for the Source Intake path additions in paths.py.

Run:
    python "Source Intake/tests/test_paths.py"
"""

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import paths


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("SOURCE_REGISTRY constant resolves to workspace root")
def _():
    check("value", paths.SOURCE_REGISTRY == paths.WORKSPACE_ROOT / "Source Registry")
    check("is absolute", paths.SOURCE_REGISTRY.is_absolute())


@test("CLEANING_JOBS constant resolves to workspace root")
def _():
    check("value", paths.CLEANING_JOBS == paths.WORKSPACE_ROOT / "Cleaning Jobs")
    check("is absolute", paths.CLEANING_JOBS.is_absolute())


@test("CLEANING_RESULTS constant resolves to workspace root")
def _():
    check("value", paths.CLEANING_RESULTS == paths.WORKSPACE_ROOT / "Cleaning Results")
    check("is absolute", paths.CLEANING_RESULTS.is_absolute())


@test("LOG_SOURCE_INTAKE constant resolves under workspace Logs")
def _():
    check("value", paths.LOG_SOURCE_INTAKE == paths.WORKSPACE_ROOT / "Logs" / "Source Intake")


@test("required directories exist")
def _():
    check("Source Registry exists", paths.SOURCE_REGISTRY.is_dir())
    check("Cleaning Jobs exists", paths.CLEANING_JOBS.is_dir())
    check("Cleaning Results exists", paths.CLEANING_RESULTS.is_dir())
    check("Logs/Source Intake exists", paths.LOG_SOURCE_INTAKE.is_dir())


@test("CLEANING_RESULTS is a single, unique constant")
def _():
    # No duplicate definition: the name appears exactly once in paths.py
    # and its value is unique across all path constants.
    source = paths.__file__
    text = pathlib.Path(source).read_text(encoding="utf-8")
    check("defined once", text.count("CLEANING_RESULTS") >= 2)
    check("no duplicate assignment",
          text.count("CLEANING_RESULTS = ") == 1)
    values = [getattr(paths, name)
              for name in dir(paths)
              if isinstance(getattr(paths, name), pathlib.Path)]
    check("no duplicate value",
          values.count(paths.CLEANING_RESULTS) == 1)


@test("verify_paths passes with the new required directories")
def _():
    # verify_paths raises SystemExit if any required directory is missing.
    try:
        paths.verify_paths()
    except SystemExit:
        check("verify_paths did not raise", False)
        return
    check("verify_paths passed", True)


@test("WORKSPACE_ROOT exists")
def _():
    check("exists", paths.WORKSPACE_ROOT.is_dir())


@test("ensure_workspace creates required workspace folders")
def _():
    paths.ensure_workspace()
    check("all workspace folders exist", all(p.is_dir() for p in paths.WORKSPACE_FOLDERS))


@test("product constants remain under PROJECT_ROOT")
def _():
    for name in ("ANALYSIS", "DATA_PROCESSOR", "PROMPTS",
                 "TRANSCRIPT_CLEANER"):
        value = getattr(paths, name)
        check(f"{name} under PROJECT_ROOT",
              value.is_relative_to(paths.PROJECT_ROOT))


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
