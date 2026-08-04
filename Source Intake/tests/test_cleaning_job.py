#!/usr/bin/env python3
"""
test_cleaning_job.py

Deterministic tests for cleaning_job.py.

Run:
    python "Source Intake/tests/test_cleaning_job.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_INTAKE = PROJECT_ROOT / "Source Intake"
sys.path.insert(0, str(SOURCE_INTAKE))

import cleaning_job


def job_args():
    return {
        "source_id": "pod_conteppei_ep051",
        "raw_path": "Raw Transcripts/con.txt",
        "source_type": "podcast_transcript",
        "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": "1.2.0",
        "output_path": "Cleaned Archive/pod_conteppei_ep051.clean.txt",
    }


def expected_bytes(job):
    return (
        json.dumps(job, ensure_ascii=False, sort_keys=True, indent=4) + "\n"
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


@test("valid job creation")
def _():
    job = cleaning_job.build_job(**job_args())
    check("schema_version", job["schema_version"] == "1")
    check("source_id", job["source_id"] == "pod_conteppei_ep051")
    check("output_path", job["output_path"] == "Cleaned Archive/pod_conteppei_ep051.clean.txt")
    check("field count", len(job) == 7)
    path = pathlib.Path(tempfile.mkdtemp()) / "pod_conteppei_ep051.cleaning_job.json"
    cleaning_job.write_job(path, job)
    check("file exists", path.is_file())
    check("round-trips", json.loads(path.read_text(encoding="utf-8")) == job)


@test("schema validation on write")
def _():
    job = cleaning_job.build_job(**job_args())
    job["raw_path"] = ""
    path = pathlib.Path(tempfile.mkdtemp()) / "x.json"
    raised = False
    try:
        cleaning_job.write_job(path, job)
    except cleaning_job.CleaningJobError:
        raised = True
    check("empty raw_path raises", raised)
    check("no file written", not path.exists())


@test("deterministic byte output")
def _():
    job = cleaning_job.build_job(**job_args())
    p1 = pathlib.Path(tempfile.mkdtemp()) / "a.json"
    p2 = pathlib.Path(tempfile.mkdtemp()) / "b.json"
    cleaning_job.write_job(p1, job)
    cleaning_job.write_job(p2, job)
    check("byte-identical", p1.read_bytes() == p2.read_bytes())
    check("matches expected bytes", p1.read_bytes() == expected_bytes(job))


@test("atomic write behavior (no temp leftover)")
def _():
    job = cleaning_job.build_job(**job_args())
    path = pathlib.Path(tempfile.mkdtemp()) / "pod_conteppei_ep051.cleaning_job.json"
    cleaning_job.write_job(path, job)
    check("final file exists", path.is_file())
    check("no .tmp leftover", not path.with_name(path.name + ".tmp").exists())
    check("valid json", json.loads(path.read_text(encoding="utf-8")) == job)


@test("missing required field rejection")
def _():
    job = cleaning_job.build_job(**job_args())
    del job["cleaning_profile"]
    path = pathlib.Path(tempfile.mkdtemp()) / "x.json"
    raised = False
    message = ""
    try:
        cleaning_job.write_job(path, job)
    except cleaning_job.CleaningJobError as ex:
        raised = True
        message = str(ex)
    check("missing field raises", raised)
    check("reports field", "cleaning_profile" in message, message)
    check("no file written", not path.exists())


@test("cleaning_job module boundary (no forbidden imports)")
def _():
    source = pathlib.Path(SOURCE_INTAKE / "cleaning_job.py").read_text(encoding="utf-8")
    for forbidden in ("import registry", "from registry",
                      "import clean_transcript", "import clean_subtitles",
                      "corpus_builder", "response_validator", "deepseek_client",
                      "import paths", "from paths", "import Analysis"):
        check(f"no {forbidden!r}", forbidden not in source)


@test("registry and cleaning_job are independent")
def _():
    reg_src = pathlib.Path(SOURCE_INTAKE / "registry.py").read_text(encoding="utf-8")
    job_src = pathlib.Path(SOURCE_INTAKE / "cleaning_job.py").read_text(encoding="utf-8")
    check("registry does not import cleaning_job", "import cleaning_job" not in reg_src
          and "from cleaning_job" not in reg_src)
    check("cleaning_job does not import registry", "import registry" not in job_src
          and "from registry" not in job_src)


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
