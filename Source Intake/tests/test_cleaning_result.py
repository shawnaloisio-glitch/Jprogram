#!/usr/bin/env python3
"""
test_cleaning_result.py

Deterministic tests for cleaning_result.py.

Run:
    python "Source Intake/tests/test_cleaning_result.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_INTAKE = PROJECT_ROOT / "Source Intake"
sys.path.insert(0, str(SOURCE_INTAKE))

import cleaning_result


def result_args():
    return {
        "source_id": "pod_conteppei_ep051",
        "success": True,
        "cleaned_artifact": "Cleaned Archive/pod_conteppei_ep051.clean.txt",
        "statistics": {
            "characters_read": 1840,
            "characters_written": 1831,
            "lines_trimmed": 3,
            "blank_lines_removed": 2,
        },
        "errors": [],
        "cleaner_version": "1.2.0",
        "completion_time": "2026-08-01 12:00:00",
        "output_hash": (
            "9f86d081884c7d659a2feaa0c55ad015"
            "a3bf4f1b2b0b822cd15d6c15b0f00a08"
        ),
    }


def expected_bytes(result):
    return (
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=4)
        + "\n"
    ).encode("utf-8")


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("valid result creation")
def _():
    result = cleaning_result.build_result(**result_args())
    check("schema_version", result["schema_version"] == "1")
    check("source_id", result["source_id"] == "pod_conteppei_ep051")
    check("success", result["success"] is True)
    check("errors", result["errors"] == [])
    check("cleaner_version", result["cleaner_version"] == "1.2.0")
    check("output_hash present", "output_hash" in result)
    path = pathlib.Path(tempfile.mkdtemp()) / "pod_conteppei_ep051.cleaning_result.json"
    cleaning_result.write_result(path, result)
    check("file exists", path.is_file())
    check("round-trips", json.loads(path.read_text(encoding="utf-8")) == result)


@test("schema validation on write")
def _():
    result = cleaning_result.build_result(**result_args())
    result["success"] = "true"
    path = pathlib.Path(tempfile.mkdtemp()) / "x.json"
    raised = False
    try:
        cleaning_result.write_result(path, result)
    except cleaning_result.CleaningResultError:
        raised = True
    check("invalid success raises", raised)
    check("no file written", not path.exists())


@test("validate_result returns error list")
def _():
    good = cleaning_result.build_result(**result_args())
    check("valid returns empty", cleaning_result.validate_result(good) == [])
    bad = cleaning_result.build_result(**result_args())
    del bad["source_id"]
    errors = cleaning_result.validate_result(bad)
    check("invalid returns errors", len(errors) > 0)
    check("reports source_id", any("source_id" in e for e in errors))


@test("missing required field rejection")
def _():
    result = cleaning_result.build_result(**result_args())
    del result["statistics"]
    path = pathlib.Path(tempfile.mkdtemp()) / "x.json"
    raised = False
    message = ""
    try:
        cleaning_result.write_result(path, result)
    except cleaning_result.CleaningResultError as ex:
        raised = True
        message = str(ex)
    check("missing field raises", raised)
    check("reports field", "statistics" in message, message)
    check("no file written", not path.exists())


@test("failed result with null cleaned artifact is valid")
def _():
    result = cleaning_result.build_result(
        source_id="pod_conteppei_ep051",
        success=False,
        cleaned_artifact=None,
        statistics={},
        errors=["raw file missing"],
        cleaner_version="1.2.0",
    )
    check("schema valid", cleaning_result.validate_result(result) == [])
    path = pathlib.Path(tempfile.mkdtemp()) / "pod_conteppei_ep051.cleaning_result.json"
    cleaning_result.write_result(path, result)
    check("file exists", path.is_file())


@test("optional fields omitted when not supplied")
def _():
    result = cleaning_result.build_result(
        source_id="pod_conteppei_ep051",
        success=True,
        cleaned_artifact="x.txt",
        statistics={},
        errors=[],
    )
    check("no cleaner_version", "cleaner_version" not in result)
    check("no completion_time", "completion_time" not in result)
    check("no output_hash", "output_hash" not in result)
    check("schema valid", cleaning_result.validate_result(result) == [])


@test("deterministic byte output")
def _():
    result = cleaning_result.build_result(**result_args())
    p1 = pathlib.Path(tempfile.mkdtemp()) / "a.json"
    p2 = pathlib.Path(tempfile.mkdtemp()) / "b.json"
    cleaning_result.write_result(p1, result)
    cleaning_result.write_result(p2, result)
    check("byte-identical", p1.read_bytes() == p2.read_bytes())
    check("matches expected bytes", p1.read_bytes() == expected_bytes(result))


@test("atomic write behavior (no temp leftover)")
def _():
    result = cleaning_result.build_result(**result_args())
    path = pathlib.Path(tempfile.mkdtemp()) / "pod_conteppei_ep051.cleaning_result.json"
    cleaning_result.write_result(path, result)
    check("final file exists", path.is_file())
    check("no .tmp leftover", not path.with_name(path.name + ".tmp").exists())
    check("valid json", json.loads(path.read_text(encoding="utf-8")) == result)


@test("cleaning_result module boundary (no forbidden imports)")
def _():
    source = pathlib.Path(SOURCE_INTAKE / "cleaning_result.py").read_text(encoding="utf-8")
    for forbidden in ("import cleaning_job", "from cleaning_job",
                      "import registry", "from registry",
                      "import clean_transcript", "import clean_subtitles",
                      "corpus_builder", "response_validator", "deepseek_client",
                      "import paths", "from paths", "import Analysis",
                      "import project_config", "from project_config"):
        check(f"no {forbidden!r}", forbidden not in source)


@test("cleaning_result writer is independent of other writers")
def _():
    src = pathlib.Path(SOURCE_INTAKE / "cleaning_result.py").read_text(encoding="utf-8")
    check("does not import registry", "import registry" not in src
          and "from registry" not in src)
    check("does not import cleaning_job", "import cleaning_job" not in src
          and "from cleaning_job" not in src)


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
