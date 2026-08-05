#!/usr/bin/env python3
"""
test_job_builder.py

Deterministic tests for the artifact-driven Job Builder.

Run:
    python "Data Processor/tests/test_job_builder.py"
"""

import importlib.util
import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_PROCESSOR = PROJECT_ROOT / "Data Processor"
SOURCE_INTAKE = PROJECT_ROOT / "Source Intake"
sys.path.insert(0, str(DATA_PROCESSOR))
sys.path.insert(0, str(SOURCE_INTAKE))

# "job builder.py" contains spaces, so load it via importlib.
_spec = importlib.util.spec_from_file_location(
    "job_builder", str(DATA_PROCESSOR / "job builder.py")
)
job_builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(job_builder)
jb = job_builder

import schemas

import hashing


# ============================================================
# Fixtures
# ============================================================

CLEAN_TEXT = "こんにちは　世界\n\nこれはテストです。\n"


def valid_result(source_id, cleaned_path, **overrides):
    result = {
        "schema_version": "1",
        "source_id": source_id,
        "success": True,
        "cleaned_artifact": str(cleaned_path),
        "statistics": {},
        "errors": [],
    }
    if pathlib.Path(cleaned_path).is_file():
        result["output_hash"] = hashing.sha256_file(cleaned_path)
    result.update(overrides)
    return result


def write_cleaning_result(results_dir, result):
    path = results_dir / f"{result['source_id']}.cleaning_result.json"
    path.write_text(
        json.dumps(result, ensure_ascii=False), encoding="utf-8"
    )
    return path


def setup():
    """Create isolated temp dirs and patch Job Builder globals."""
    root = pathlib.Path(tempfile.mkdtemp())
    results_dir = root / "Cleaning Results"
    jobs_dir = root / "jobs"
    jb_results_dir = root / "Job Results"
    logs_dir = root / "logs"
    archive = root / "Cleaned Archive"
    for folder in (results_dir, jobs_dir, jb_results_dir, logs_dir, archive):
        folder.mkdir(parents=True)

    saved = (
        jb.CLEANING_RESULTS,
        jb.JOBS,
        jb.JOB_RESULTS,
        jb.LOG_JOB_BUILDER,
    )
    jb.CLEANING_RESULTS = results_dir
    jb.JOBS = jobs_dir
    jb.JOB_RESULTS = jb_results_dir
    jb.LOG_JOB_BUILDER = logs_dir
    return root, results_dir, jobs_dir, jb_results_dir, archive, saved


def restore(saved):
    (jb.CLEANING_RESULTS, jb.JOBS, jb.JOB_RESULTS,
     jb.LOG_JOB_BUILDER) = saved


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("1. valid Cleaning Result creates jobs")
def _():
    root, results, jobs, jb_results, archive, saved = setup()
    try:
        cleaned = archive / "pod_conteppei_ep051.clean.txt"
        cleaned.write_text(CLEAN_TEXT, encoding="utf-8")
        write_cleaning_result(results, valid_result(
            "pod_conteppei_ep051", cleaned))

        code = jb.run("pod_conteppei_ep051")
        check("exit 0", code == 0)

        job_dir = jobs / "pod_conteppei_ep051"
        check("job folder exists", job_dir.is_dir())
        job_files = sorted(job_dir.glob("job_*.json"))
        check("at least one job", len(job_files) >= 1)
        job = json.loads(job_files[0].read_text(encoding="utf-8"))
        check("source_id in job", job["source_id"] == "pod_conteppei_ep051")
        check("cleaned_artifact in job",
              job["cleaned_artifact"] == str(cleaned))
        check("job_number", job["job_number"] == 1)
        check("text matches", job["text"] == CLEAN_TEXT)

        result_file = jb_results / "pod_conteppei_ep051.job_builder_result.json"
        check("result artifact exists", result_file.is_file())
        result = json.loads(result_file.read_text(encoding="utf-8"))
        check("result success", result["success"] is True)
        check("result job_count", result["job_count"] == len(job_files))
        check("result total_characters",
              result["total_characters"] == len(CLEAN_TEXT))
    finally:
        restore(saved)


@test("2. missing Cleaning Result rejected")
def _():
    root, results, jobs, jb_results, archive, saved = setup()
    try:
        code = jb.run("pod_missing_ep001")
        check("exit non-zero", code != 0)
        check("no job folder",
              not (jobs / "pod_missing_ep001").exists())

        result_file = jb_results / "pod_missing_ep001.job_builder_result.json"
        check("failure result exists", result_file.is_file())
        result = json.loads(result_file.read_text(encoding="utf-8"))
        check("success false", result["success"] is False)
        check("errors populated", len(result["errors"]) > 0)
    finally:
        restore(saved)


@test("3. success=false rejected")
def _():
    root, results, jobs, jb_results, archive, saved = setup()
    try:
        cleaned = archive / "pod_conteppei_ep051.clean.txt"
        cleaned.write_text(CLEAN_TEXT, encoding="utf-8")
        result = valid_result("pod_conteppei_ep051", cleaned)
        result["success"] = False
        write_cleaning_result(results, result)

        code = jb.run("pod_conteppei_ep051")
        check("exit non-zero", code != 0)
        check("no job folder",
              not (jobs / "pod_conteppei_ep051").exists())

        result_file = jb_results / "pod_conteppei_ep051.job_builder_result.json"
        result = json.loads(result_file.read_text(encoding="utf-8"))
        check("success false", result["success"] is False)
        check("errors mention success",
              any("success" in e for e in result["errors"]))
    finally:
        restore(saved)


@test("4. missing cleaned artifact rejected")
def _():
    root, results, jobs, jb_results, archive, saved = setup()
    try:
        missing = archive / "does_not_exist.clean.txt"
        write_cleaning_result(results, valid_result(
            "pod_conteppei_ep051", missing))

        code = jb.run("pod_conteppei_ep051")
        check("exit non-zero", code != 0)
        check("no job folder",
              not (jobs / "pod_conteppei_ep051").exists())

        result_file = jb_results / "pod_conteppei_ep051.job_builder_result.json"
        result = json.loads(result_file.read_text(encoding="utf-8"))
        check("success false", result["success"] is False)
        check("errors mention artifact",
              any("artifact" in e for e in result["errors"]))
    finally:
        restore(saved)


@test("5. source_id naming verified")
def _():
    root, results, jobs, jb_results, archive, saved = setup()
    try:
        cleaned = archive / "sub_frieren_ep001.clean.txt"
        cleaned.write_text(CLEAN_TEXT, encoding="utf-8")
        write_cleaning_result(results, valid_result(
            "sub_frieren_ep001", cleaned))

        code = jb.run("sub_frieren_ep001")
        check("exit 0", code == 0)

        job_dir = jobs / "sub_frieren_ep001"
        check("folder named by source_id", job_dir.is_dir())
        job_files = sorted(job_dir.glob("job_*.json"))
        for job_file in job_files:
            job = json.loads(job_file.read_text(encoding="utf-8"))
            check(f"job metadata source_id {job_file.name}",
                  job["source_id"] == "sub_frieren_ep001")
    finally:
        restore(saved)


@test("5b. --source CLI invocation works")
def _():
    root, results, jobs, jb_results, archive, saved = setup()
    try:
        cleaned = archive / "pod_cli_ep001.clean.txt"
        cleaned.write_text(CLEAN_TEXT, encoding="utf-8")
        write_cleaning_result(results, valid_result(
            "pod_cli_ep001", cleaned))

        code = jb.main(["--source", "pod_cli_ep001"])
        check("exit 0", code == 0)
        job_dir = jobs / "pod_cli_ep001"
        check("job folder exists", job_dir.is_dir())
        check("jobs created", len(list(job_dir.glob("job_*.json"))) >= 1)
    finally:
        restore(saved)


@test("5c. missing --source rejected by CLI")
def _():
    root, results, jobs, jb_results, archive, saved = setup()
    try:
        raised = False
        try:
            jb.main([])
        except SystemExit:
            raised = True
        check("argparse rejects missing --source", raised)
        check("no job subfolder created",
              not any(p.is_dir() for p in jobs.iterdir()))
    finally:
        restore(saved)


@test("7. output-path authority (consumes artifact path from result)")
def _():
    root, results, jobs, jb_results, archive, saved = setup()
    try:
        # The artifact lives in a non-default location and has a name
        # unrelated to the source_id. Job Builder must consume exactly
        # the path recorded in the Cleaning Result.
        custom_artifact = root / "elsewhere" / "custom_clean.txt"
        custom_artifact.parent.mkdir(parents=True)
        custom_artifact.write_text(CLEAN_TEXT, encoding="utf-8")
        write_cleaning_result(results, valid_result(
            "pod_conteppei_ep051", custom_artifact))

        code = jb.run("pod_conteppei_ep051")
        check("exit 0", code == 0)

        job_dir = jobs / "pod_conteppei_ep051"
        job_files = sorted(job_dir.glob("job_*.json"))
        check("jobs created", len(job_files) >= 1)
        job = json.loads(job_files[0].read_text(encoding="utf-8"))
        check("cleaned_artifact from result",
              job["cleaned_artifact"] == str(custom_artifact))
        check("text from custom artifact", job["text"] == CLEAN_TEXT)
    finally:
        restore(saved)


@test("6. deterministic repeat execution")
def _():
    root, results, jobs, jb_results, archive, saved = setup()
    try:
        cleaned = archive / "pod_conteppei_ep051.clean.txt"
        text = ("あ" * 4000) + "\n" + ("い" * 4000) + "\n" + ("う" * 4000) + "\n"
        cleaned.write_text(text, encoding="utf-8")
        write_cleaning_result(results, valid_result(
            "pod_conteppei_ep051", cleaned))

        code_a = jb.run("pod_conteppei_ep051")
        job_dir = jobs / "pod_conteppei_ep051"
        snapshot = {
            p.name: p.read_bytes()
            for p in sorted(job_dir.glob("job_*.json"))
        }

        code_b = jb.run("pod_conteppei_ep051")
        after = {
            p.name: p.read_bytes()
            for p in sorted(job_dir.glob("job_*.json"))
        }

        check("both exit 0", code_a == 0 and code_b == 0)
        check("same job files", set(snapshot) == set(after))
        check("byte-identical jobs", snapshot == after)
    finally:
        restore(saved)


@test("7. atomic write failure behavior")
def _():
    root, results, jobs, jb_results, archive, saved = setup()
    try:
        cleaned = archive / "pod_conteppei_ep051.clean.txt"
        cleaned.write_text(CLEAN_TEXT, encoding="utf-8")
        write_cleaning_result(results, valid_result(
            "pod_conteppei_ep051", cleaned))

        # Make the job folder impossible to create: a file blocks it.
        blocker = jobs / "pod_conteppei_ep051"
        blocker.write_text("i am a file", encoding="utf-8")

        code = jb.run("pod_conteppei_ep051")
        check("exit non-zero", code != 0)

        result_file = jb_results / "pod_conteppei_ep051.job_builder_result.json"
        check("failure result exists", result_file.is_file())
        result = json.loads(result_file.read_text(encoding="utf-8"))
        check("success false", result["success"] is False)
        check("errors populated", len(result["errors"]) > 0)
        check("no partial job file",
              not blocker.with_name("job_000001.json").exists())
    finally:
        restore(saved)


@test("8. forbidden writes")
def _():
    import paths as project_paths

    root, results, jobs, jb_results, archive, saved = setup()
    try:
        cleaned = archive / "pod_conteppei_ep051.clean.txt"
        cleaned.write_text(CLEAN_TEXT, encoding="utf-8")
        write_cleaning_result(results, valid_result(
            "pod_conteppei_ep051", cleaned))

        before_registry = sorted(x.name for x in project_paths.SOURCE_REGISTRY.iterdir())
        before_jobs_intake = sorted(x.name for x in project_paths.CLEANING_JOBS.iterdir())
        before_clean_results = sorted(
            x.name for x in project_paths.CLEANING_RESULTS.iterdir())
        before_raw = sorted(
            x.name for x in project_paths.RAW_SUBTITLES.iterdir()
        ) + sorted(x.name for x in project_paths.RAW_TRANSCRIPTS.iterdir())

        code = jb.run("pod_conteppei_ep051")
        check("exit 0", code == 0)

        after_registry = sorted(x.name for x in project_paths.SOURCE_REGISTRY.iterdir())
        after_jobs_intake = sorted(x.name for x in project_paths.CLEANING_JOBS.iterdir())
        after_clean_results = sorted(
            x.name for x in project_paths.CLEANING_RESULTS.iterdir())
        after_raw = sorted(
            x.name for x in project_paths.RAW_SUBTITLES.iterdir()
        ) + sorted(x.name for x in project_paths.RAW_TRANSCRIPTS.iterdir())

        check("no registry write", after_registry == before_registry)
        check("no Cleaning Jobs write", after_jobs_intake == before_jobs_intake)
        check("no Cleaning Results write",
              after_clean_results == before_clean_results)
        check("no Raw folder write", after_raw == before_raw)
    finally:
        restore(saved)


@test("9. forbidden imports")
def _():
    source = pathlib.Path(DATA_PROCESSOR / "job builder.py").read_text(
        encoding="utf-8")
    for forbidden in ("response_validator", "corpus_builder",
                      "deepseek_client", "request builder", "process_file",
                      "import Analysis", "from Analysis", "import corpus",
                      "import analysis", "clean_subtitles", "clean_transcript"):
        check(f"no {forbidden!r}", forbidden not in source)


@test("9b. job_builder_result writer boundary")
def _():
    source = pathlib.Path(DATA_PROCESSOR / "job_builder_result.py").read_text(
        encoding="utf-8")
    for forbidden in ("response_validator", "corpus_builder",
                      "deepseek_client", "import Analysis", "from Analysis",
                      "import schemas", "import paths", "import project_config",
                      "clean_subtitles", "clean_transcript"):
        check(f"no {forbidden!r}", forbidden not in source)


@test("9c. job_builder_result schema round-trip")
def _():
    import job_builder_result as jbr
    result = jbr.build_result(
        source_id="pod_conteppei_ep051",
        success=True,
        jobs_created=True,
        job_count=3,
        total_characters=15000,
        output_directory="jobs/pod_conteppei_ep051",
        errors=[],
        completion_time="2026-08-01 12:00:00",
    )
    check("valid", jbr.validate_result(result) == [])
    path = pathlib.Path(tempfile.mkdtemp()) / "x.json"
    jbr.write_result(path, result)
    check("round-trips",
          json.loads(path.read_text(encoding="utf-8")) == result)

    bad = jbr.build_result(
        source_id="pod_conteppei_ep051",
        success=True,
        jobs_created=True,
        job_count="three",
        total_characters=0,
        output_directory="x",
        errors=[],
    )
    check("invalid rejected", jbr.validate_result(bad) != [])


@test("10. cleaning_result_errors catches output_hash mismatch")
def _():
    root, results, jobs, jb_results, archive, saved = setup()
    try:
        cleaned = archive / "pod_conteppei_ep051.clean.txt"
        cleaned.write_text(CLEAN_TEXT, encoding="utf-8")
        result = valid_result("pod_conteppei_ep051", cleaned)
        cleaned.write_text(CLEAN_TEXT + "tampered\n", encoding="utf-8")

        errors = jb.cleaning_result_errors(result)
        check("hash mismatch error returned",
              any("output_hash" in e and "match" in e for e in errors))
    finally:
        restore(saved)


@test("11. cleaning_result_errors passes when output_hash matches")
def _():
    root, results, jobs, jb_results, archive, saved = setup()
    try:
        cleaned = archive / "pod_conteppei_ep051.clean.txt"
        cleaned.write_text(CLEAN_TEXT, encoding="utf-8")
        result = valid_result("pod_conteppei_ep051", cleaned)

        errors = jb.cleaning_result_errors(result)
        check("no errors", errors == [])
    finally:
        restore(saved)


@test("12. cleaning_result_errors catches missing output_hash")
def _():
    root, results, jobs, jb_results, archive, saved = setup()
    try:
        cleaned = archive / "pod_conteppei_ep051.clean.txt"
        cleaned.write_text(CLEAN_TEXT, encoding="utf-8")
        result = valid_result("pod_conteppei_ep051", cleaned)
        del result["output_hash"]

        errors = jb.cleaning_result_errors(result)
        check("missing output_hash error",
              any("output_hash" in e for e in errors))
    finally:
        restore(saved)


@test("13. run fails closed when cleaned artifact does not match output_hash")
def _():
    root, results, jobs, jb_results, archive, saved = setup()
    try:
        cleaned = archive / "pod_conteppei_ep051.clean.txt"
        cleaned.write_text(CLEAN_TEXT, encoding="utf-8")
        result = valid_result("pod_conteppei_ep051", cleaned)
        write_cleaning_result(results, result)
        cleaned.write_text(CLEAN_TEXT + "tampered\n", encoding="utf-8")

        code = jb.run("pod_conteppei_ep051")
        check("exit non-zero", code != 0)
        check("no job folder",
              not (jobs / "pod_conteppei_ep051").exists())

        result_file = jb_results / "pod_conteppei_ep051.job_builder_result.json"
        check("failure result exists", result_file.is_file())
        result = json.loads(result_file.read_text(encoding="utf-8"))
        check("success false", result["success"] is False)
        check("hash mismatch reported",
              any("output_hash" in e for e in result["errors"]))
    finally:
        restore(saved)


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
