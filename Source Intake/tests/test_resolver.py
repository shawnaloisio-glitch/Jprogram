#!/usr/bin/env python3
"""
test_resolver.py

Deterministic tests for resolver.py.

Run:
    python "Source Intake/tests/test_resolver.py"
"""

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_INTAKE = PROJECT_ROOT / "Source Intake"
sys.path.insert(0, str(SOURCE_INTAKE))
sys.path.insert(0, str(PROJECT_ROOT))

import paths
import schemas
import resolver


def registry_entry():
    return {
        "schema_version": schemas.schema_version("registry"),
        "source_id": "pod_conteppei_ep051",
        "original_filename": "con.txt",
        "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        "source_type": "clean_text",
        "format": "txt",
        "language": "ja",
        "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": "1.0",
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


def raises_resolver(fn):
    try:
        fn()
        return False
    except resolver.ResolverError:
        return True


@test("raw_dir_for resolves known types")
def _():
    check("clean_text", resolver.raw_dir_for("clean_text")
          == PROJECT_ROOT / "Raw Transcripts")


@test("raw_dir_for rejects unknown type")
def _():
    check("raises ResolverError", raises_resolver(
        lambda: resolver.raw_dir_for("mystery")))


@test("cleaning_profile_for resolves known types")
def _():
    check("clean_text", resolver.cleaning_profile_for("clean_text")
          == "transcript_standard_v1")


@test("cleaning_profile_for rejects unknown type")
def _():
    check("raises ResolverError", raises_resolver(
        lambda: resolver.cleaning_profile_for("mystery")))


@test("cleaner_and_version_for resolves known profiles")
def _():
    check("transcript", resolver.cleaner_and_version_for("transcript_standard_v1")
          == ("clean_transcript", "1.0"))


@test("cleaner_and_version_for rejects unknown profile")
def _():
    check("raises ResolverError", raises_resolver(
        lambda: resolver.cleaner_and_version_for("bogus")))


@test("cleaned_output_path_for naming rule")
def _():
    path = resolver.cleaned_output_path_for("pod_conteppei_ep051")
    check("under Cleaned Archive", path.parent == paths.CLEANED_ARCHIVE)
    check("filename", path.name == "pod_conteppei_ep051.clean.txt")


@test("cleaning_job_fields reconstructs a valid job")
def _():
    entry = registry_entry()
    job = resolver.cleaning_job_fields(entry)
    check("source_id", job["source_id"] == "pod_conteppei_ep051")
    check("raw_path", job["raw_path"]
          == str(PROJECT_ROOT / "Raw Transcripts" / "con.txt"))
    check("source_type", job["source_type"] == "clean_text")
    check("cleaning_profile", job["cleaning_profile"] == "transcript_standard_v1")
    check("cleaner_version", job["cleaner_version"] == "1.0")
    check("output_path", job["output_path"]
          == str(paths.CLEANED_ARCHIVE / "pod_conteppei_ep051.clean.txt"))
    check("schema valid", schemas.validate("cleaning_job", job) == [])


@test("cleaning_job_fields registry values are authoritative")
def _():
    # A registry-recorded profile/version is preserved even if it differs
    # from the current default assignment.
    entry = registry_entry()
    entry["cleaning_profile"] = "subtitle_standard_v1"
    entry["cleaner_version"] = "0.9"
    job = resolver.cleaning_job_fields(entry)
    check("profile preserved", job["cleaning_profile"] == "subtitle_standard_v1")
    check("version preserved", job["cleaner_version"] == "0.9")


@test("cleaning_job_fields rejects missing required field")
def _():
    entry = registry_entry()
    del entry["original_filename"]
    check("raises ResolverError", raises_resolver(
        lambda: resolver.cleaning_job_fields(entry)))


@test("cleaning_job_fields rejects unknown source type")
def _():
    entry = registry_entry()
    entry["source_type"] = "mystery"
    check("raises ResolverError", raises_resolver(
        lambda: resolver.cleaning_job_fields(entry)))


@test("cleaning_job_fields rejects non-dict")
def _():
    check("raises ResolverError", raises_resolver(
        lambda: resolver.cleaning_job_fields("not-a-dict")))


@test("deterministic output")
def _():
    entry = registry_entry()
    check("raw_dir deterministic",
          resolver.raw_dir_for("clean_text") == resolver.raw_dir_for("clean_text"))
    check("job fields deterministic",
          resolver.cleaning_job_fields(entry) == resolver.cleaning_job_fields(entry))


@test("resolver module boundary (no forbidden imports)")
def _():
    source = pathlib.Path(SOURCE_INTAKE / "resolver.py").read_text(encoding="utf-8")
    for forbidden in ("import clean_transcript", "import clean_subtitles",
                      "corpus_builder", "response_validator", "deepseek_client",
                      "import duplicate_check", "import source_intake",
                      "import registry", "import cleaning_job", "import Analysis"):
        check(f"no {forbidden!r}", forbidden not in source)


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
