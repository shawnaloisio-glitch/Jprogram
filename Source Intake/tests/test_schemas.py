#!/usr/bin/env python3
"""
test_schemas.py

Deterministic tests for schemas.py.

Run:
    python "Source Intake/tests/test_schemas.py"
"""

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_INTAKE = PROJECT_ROOT / "Source Intake"
sys.path.insert(0, str(SOURCE_INTAKE))

import schemas


def valid_registry():
    return {
        "schema_version": "1",
        "source_id": "pod_conteppei_ep051",
        "original_filename": "con.txt",
        "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        "source_type": "podcast_transcript",
        "format": "txt",
        "language": "ja",
        "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": "1.2.0",
    }


def valid_cleaning_job():
    return {
        "schema_version": "1",
        "source_id": "pod_conteppei_ep051",
        "raw_path": "Raw Transcripts/con.txt",
        "source_type": "podcast_transcript",
        "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": "1.2.0",
        "output_path": "Cleaned Archive/pod_conteppei_ep051.clean.txt",
    }


def valid_cleaning_result():
    return {
        "schema_version": "1",
        "source_id": "pod_conteppei_ep051",
        "success": True,
        "cleaned_artifact": "pod_conteppei_ep051.clean.txt",
        "statistics": {"characters_read": 1840, "characters_written": 1831},
        "errors": [],
    }


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("valid artifacts pass")
def _():
    check("registry", schemas.validate("registry", valid_registry()) == [])
    check("cleaning_job", schemas.validate("cleaning_job", valid_cleaning_job()) == [])
    check("cleaning_result", schemas.validate("cleaning_result", valid_cleaning_result()) == [])


@test("unknown artifact name rejected")
def _():
    errors = schemas.validate("unknown", {})
    check("error present", len(errors) == 1 and "unknown" in errors[0])


@test("non-object artifact rejected")
def _():
    errors = schemas.validate("registry", [1, 2])
    check("error present", len(errors) == 1 and "JSON object" in errors[0])


@test("missing required field")
def _():
    data = valid_registry()
    del data["sha256"]
    errors = schemas.validate("registry", data)
    check("missing sha256 flagged",
          any("sha256" in e and "missing" in e for e in errors))


@test("invalid sha256 value")
def _():
    data = valid_registry()
    data["sha256"] = "not-a-hash"
    errors = schemas.validate("registry", data)
    check("sha256 invalid flagged",
          any("sha256" in e for e in errors))
    data["sha256"] = "ABCDEF"  # uppercase not allowed
    errors = schemas.validate("registry", data)
    check("uppercase rejected",
          any("sha256" in e for e in errors))


@test("wrong type rejected")
def _():
    data = valid_cleaning_result()
    data["success"] = "true"  # must be boolean
    errors = schemas.validate("cleaning_result", data)
    check("bool type enforced",
          any("success" in e for e in errors))
    data2 = valid_cleaning_job()
    data2["priority"] = "high"  # optional field, must be int when present
    errors2 = schemas.validate("cleaning_job", data2)
    check("optional int type enforced",
          any("priority" in e for e in errors2))


@test("schema_version validated")
def _():
    data = valid_registry()
    del data["schema_version"]
    errors = schemas.validate("registry", data)
    check("missing version flagged",
          any("schema_version" in e and "missing" in e for e in errors))
    data["schema_version"] = "2"
    errors = schemas.validate("registry", data)
    check("mismatch flagged",
          any("schema_version" in e and "mismatch" in e for e in errors))


@test("optional fields allowed and validated")
def _():
    data = valid_registry()
    data["cleaned_artifact"] = "pod_conteppei_ep051.clean.txt"
    data["parser_version"] = None
    check("null optional ok", schemas.validate("registry", data) == [])
    data["cleaned_artifact"] = 123
    errors = schemas.validate("registry", data)
    check("wrong optional type flagged",
          any("cleaned_artifact" in e for e in errors))


@test("artifact names and versions")
def _():
    check("three artifacts", schemas.artifact_names() == [
        "cleaning_job", "cleaning_result", "registry"])
    check("registry version", schemas.schema_version("registry") == "1")
    check("unknown version", schemas.schema_version("nope") is None)


@test("deterministic validation result")
def _():
    good = valid_registry()
    check("identical results",
          schemas.validate("registry", good) == schemas.validate("registry", good))
    bad = valid_registry()
    del bad["source_type"]
    check("identical error lists",
          schemas.validate("registry", bad) == schemas.validate("registry", bad))


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
