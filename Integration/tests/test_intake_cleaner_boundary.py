#!/usr/bin/env python3
"""
test_intake_cleaner_boundary.py

Integration tests for the complete artifact workflow:

    Source Intake -> Cleaning Job -> Cleaner -> Cleaning Result

These tests exercise the real modules together in isolated temporary
directories. They do not replace existing unit tests and do not modify
cleaner behavior.

Run:
    python "Integration/tests/test_intake_cleaner_boundary.py"
"""

import json
import pathlib
import subprocess
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_INTAKE = PROJECT_ROOT / "Source Intake"
TRANSCRIPT_CLEANER = PROJECT_ROOT / "Transcript Cleaner"
sys.path.insert(0, str(SOURCE_INTAKE))
sys.path.insert(0, str(TRANSCRIPT_CLEANER))

import hashing
import resolver
import schemas
import source_intake as si

import clean_transcript as ct

TRANSCRIPT = "こんにちは　世界\n\nこれは  テストです。\n"

TRANSCRIPT_ALT = "おはようございます\n\n今日もいい天気です。\n"


def fixture():
    """
    Set up isolated temp directories for a full pipeline run and patch
    the module globals so every program writes only into the sandbox.
    """
    root = pathlib.Path(tempfile.mkdtemp())

    raw_trans = root / "Raw Transcripts"
    registry_dir = root / "Source Registry"
    jobs_dir = root / "Cleaning Jobs"
    results_dir = root / "Cleaning Results"
    logs_trans = root / "Logs" / "Transcript Cleaner"
    archive = root / "Cleaned Archive"

    for folder in (raw_trans, registry_dir, jobs_dir,
                   results_dir, logs_trans, archive):
        folder.mkdir(parents=True)

    saved = (
        si.SOURCE_REGISTRY,
        si.CLEANING_JOBS,
        si.LOG_SOURCE_INTAKE,
        resolver.SOURCE_TYPE_RAW_DIR,
        resolver.CLEANED_ARCHIVE,
        ct.CLEANING_RESULTS,
        ct.LOG_TRANSCRIPT_CLEANER,
        ct.SOURCE_REGISTRY,
    )

    si.SOURCE_REGISTRY = registry_dir
    si.CLEANING_JOBS = jobs_dir
    si.LOG_SOURCE_INTAKE = root / "Logs" / "Source Intake"
    si.LOG_SOURCE_INTAKE.mkdir(parents=True)
    resolver.SOURCE_TYPE_RAW_DIR = {
        "clean_text": str(raw_trans),
    }
    resolver.CLEANED_ARCHIVE = archive
    ct.CLEANING_RESULTS = results_dir
    ct.LOG_TRANSCRIPT_CLEANER = logs_trans
    ct.SOURCE_REGISTRY = registry_dir

    return root, saved


def restore(saved):
    (si.SOURCE_REGISTRY, si.CLEANING_JOBS,
     si.LOG_SOURCE_INTAKE, resolver.SOURCE_TYPE_RAW_DIR,
     resolver.CLEANED_ARCHIVE, ct.CLEANING_RESULTS,
     ct.LOG_TRANSCRIPT_CLEANER, ct.SOURCE_REGISTRY) = saved


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


def register_and_run(root, raw_file, source_type, title, sequence,
                     cleaner):
    """
    Run the full Source Intake -> Cleaner flow for one raw file.

    Returns a dict of artifact paths and parsed content.
    """
    result = si.register_source(
        str(raw_file), source_type, "ja", title, sequence
    )
    sid = result["source_id"]
    job_path = pathlib.Path(result["cleaning_job_path"])
    registry_path = root / "Source Registry" / f"{sid}.json"
    results_dir = root / "Cleaning Results"
    result_path = results_dir / f"{sid}.cleaning_result.json"

    exit_code = cleaner.run(job_path)

    return {
        "result": result,
        "sid": sid,
        "job_path": job_path,
        "registry_path": registry_path,
        "result_path": result_path,
        "exit_code": exit_code,
    }


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def cli_command(cleaner_dir, module_name, results_dir, log_attr, logs_dir,
                registry_dir, job_path):
    """
    Build a subprocess command that runs the cleaner's real main() CLI
    entry point with --job while keeping output directories isolated.

    The cleaner module reads CLEANING_RESULTS, its log folder, and the
    Source Registry from paths at import time; a thin wrapper patches
    those module globals to the sandbox before calling the real
    main(argv). This is a genuine CLI invocation of the program's entry
    point with real argument parsing and exit codes.
    """
    wrapper = pathlib.Path(tempfile.mkdtemp()) / "cli_runner.py"
    wrapper.write_text(
        "import pathlib\n"
        "import sys\n"
        f"sys.path.insert(0, {str(cleaner_dir)!r})\n"
        f"import {module_name} as cleaner\n"
        f"cleaner.CLEANING_RESULTS = pathlib.Path({str(results_dir)!r})\n"
        f"cleaner.{log_attr} = pathlib.Path({str(logs_dir)!r})\n"
        f"cleaner.SOURCE_REGISTRY = pathlib.Path({str(registry_dir)!r})\n"
        "sys.exit(cleaner.main(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    return [sys.executable, str(wrapper), "--job", str(job_path)]


# ============================================================
# Complete flows
# ============================================================

@test("1. complete clean_text flow")
def _():
    root, saved = fixture()
    try:
        raw_file = root / "Raw Transcripts" / "con.txt"
        raw_file.write_text(TRANSCRIPT, encoding="utf-8")

        flow = register_and_run(
            root, raw_file, "clean_text", "Con Teppei", "ep051",
            ct,
        )
        sid = flow["sid"]

        check("intake registered", flow["result"]["action"] == "registered")
        check("cleaner exit 0", flow["exit_code"] == 0)

        check("registry exists", flow["registry_path"].is_file())
        check("job exists", flow["job_path"].is_file())

        output_path = pathlib.Path(
            load_json(flow["job_path"])["output_path"]
        )
        check("cleaned artifact exists", output_path.is_file())
        check("result exists", flow["result_path"].is_file())

        result = load_json(flow["result_path"])
        check("success true", result["success"] is True)
        check("source_id", result["source_id"] == sid)
        check("errors empty", result["errors"] == [])

        output_hash = result["output_hash"]
        artifact_bytes = output_path.read_bytes()
        check("output_hash matches artifact",
              output_hash == hashing.sha256_file(output_path))
        check("artifact non-empty", len(artifact_bytes) > 0)

        text = output_path.read_text(encoding="utf-8")
        check("full-width space preserved", "　" in text)
        check("ascii spaces collapsed", "   " not in text)
    finally:
        restore(saved)


@test("2. multiple clean_text sources coexist independently")
def _():
    root, saved = fixture()
    try:
        trans_a = root / "Raw Transcripts" / "con_a.txt"
        trans_a.write_text(TRANSCRIPT, encoding="utf-8")
        trans_b = root / "Raw Transcripts" / "con_b.txt"
        trans_b.write_text(TRANSCRIPT_ALT, encoding="utf-8")

        first = register_and_run(
            root, trans_a, "clean_text", "Con Teppei", "ep051", ct
        )
        second = register_and_run(
            root, trans_b, "clean_text", "Another Show", "ep002", ct
        )

        check("both registered",
              first["result"]["action"] == "registered"
              and second["result"]["action"] == "registered")
        check("distinct source ids", first["sid"] != second["sid"])
        check("both results exist",
              first["result_path"].is_file()
              and second["result_path"].is_file())
        check("both results success",
              load_json(first["result_path"])["success"] is True
              and load_json(second["result_path"])["success"] is True)
    finally:
        restore(saved)


# ============================================================
# Failure recovery
# ============================================================

@test("3. cleaning job exists but raw file missing")
def _():
    root, saved = fixture()
    try:
        raw_file = root / "Raw Transcripts" / "con.txt"
        raw_file.write_text(TRANSCRIPT, encoding="utf-8")

        flow = register_and_run(
            root, raw_file, "clean_text", "Con Teppei", "ep051",
            ct,
        )
        check("intake registered", flow["result"]["action"] == "registered")

        # Delete the raw file so the cleaner fails.
        raw_file.unlink()
        exit_code = ct.run(flow["job_path"])
        check("cleaner exit non-zero", exit_code != 0)

        check("failure result exists", flow["result_path"].is_file())
        result = load_json(flow["result_path"])
        check("success false", result["success"] is False)
        check("cleaned_artifact null",
              result["cleaned_artifact"] is None)
        check("errors populated", len(result["errors"]) > 0)

        # Recoverable from artifacts: restore the raw file and re-run.
        raw_file.write_text(TRANSCRIPT, encoding="utf-8")
        exit_code = ct.run(flow["job_path"])
        check("re-run exit 0", exit_code == 0)
        result = load_json(flow["result_path"])
        check("recovered success true", result["success"] is True)

        output_path = pathlib.Path(
            load_json(flow["job_path"])["output_path"]
        )
        check("artifact exists after recovery", output_path.is_file())
    finally:
        restore(saved)


@test("4B. cleaning job exists but no cleaning result")
def _():
    root, saved = fixture()
    try:
        raw_file = root / "Raw Transcripts" / "con.txt"
        raw_file.write_text(TRANSCRIPT, encoding="utf-8")

        result = si.register_source(
            str(raw_file), "clean_text", "ja",
            "Con Teppei", "ep052"
        )
        sid = result["source_id"]
        job_path = pathlib.Path(result["cleaning_job_path"])
        result_path = root / "Cleaning Results" / f"{sid}.cleaning_result.json"

        check("job exists", job_path.is_file())
        check("result does not exist", not result_path.is_file())

        # State is identifiable as pending/incomplete from artifacts.
        state = "pending" if (job_path.is_file()
                              and not result_path.is_file()) else "complete"
        check("state is pending", state == "pending")

        # Run the cleaner to complete it.
        exit_code = ct.run(job_path)
        check("cleaner exit 0", exit_code == 0)
        check("result now exists", result_path.is_file())
        check("success true",
              load_json(result_path)["success"] is True)
    finally:
        restore(saved)


# ============================================================
# Duplicate / resume behavior
# ============================================================

@test("4. existing successful cleaning does not create conflicts")
def _():
    root, saved = fixture()
    try:
        raw_file = root / "Raw Transcripts" / "con.txt"
        raw_file.write_text(TRANSCRIPT, encoding="utf-8")

        flow = register_and_run(
            root, raw_file, "clean_text", "Con Teppei", "ep051", ct
        )
        output_path = pathlib.Path(
            load_json(flow["job_path"])["output_path"]
        )
        first_artifact = output_path.read_bytes()
        first_result = load_json(flow["result_path"])

        # Re-register: must be already_complete, no new artifacts.
        before = {
            p: sorted(x.name for x in p.iterdir())
            for p in (root / "Source Registry", root / "Cleaning Jobs",
                      root / "Cleaning Results")
        }
        result = si.register_source(
            str(raw_file), "clean_text", "ja", "Con Teppei", "ep051"
        )
        check("re-register is already_complete",
              result["action"] == "already_complete")
        check("no new registry entries",
              sorted(x.name for x in (root / "Source Registry").iterdir())
              == before[root / "Source Registry"])
        check("no new jobs",
              sorted(x.name for x in (root / "Cleaning Jobs").iterdir())
              == before[root / "Cleaning Jobs"])
        check("no new results",
              sorted(x.name for x in (root / "Cleaning Results").iterdir())
              == before[root / "Cleaning Results"])

        # Re-run cleaner on same job: deterministic overwrite.
        exit_code = ct.run(flow["job_path"])
        check("re-run exit 0", exit_code == 0)
        check("artifact byte-identical",
              output_path.read_bytes() == first_artifact)
        check("result still success",
              load_json(flow["result_path"])["success"] is True)
        check("result statistics identical",
              load_json(flow["result_path"])["statistics"]
              == first_result["statistics"])
    finally:
        restore(saved)


@test("5b. resume path reconstructs a valid job")
def _():
    root, saved = fixture()
    try:
        raw_file = root / "Raw Transcripts" / "con.txt"
        raw_file.write_text(TRANSCRIPT, encoding="utf-8")

        first = si.register_source(
            str(raw_file), "clean_text", "ja",
            "Con Teppei", "ep051"
        )
        sid = first["source_id"]
        job_path = pathlib.Path(first["cleaning_job_path"])

        # Simulate a lost cleaning job (registry still present).
        job_path.unlink()
        result = si.register_source(
            str(raw_file), "clean_text", "ja",
            "Con Teppei", "ep051"
        )
        check("resume action", result["action"] == "resumed")
        check("job recreated", job_path.is_file())
        job = load_json(job_path)
        check("job valid",
              schemas.validate("cleaning_job", job) == [])
        check("job source_id", job["source_id"] == sid)

        # Run the reconstructed job through the cleaner.
        exit_code = ct.run(job_path)
        check("cleaner exit 0", exit_code == 0)
        check("result exists",
              (root / "Cleaning Results" / f"{sid}.cleaning_result.json")
              .is_file())
    finally:
        restore(saved)


# ============================================================
# Artifact ownership
# ============================================================

@test("6. artifact ownership is clean")
def _():
    root, saved = fixture()
    try:
        trans_a = root / "Raw Transcripts" / "con_a.txt"
        trans_a.write_text(TRANSCRIPT, encoding="utf-8")
        trans_b = root / "Raw Transcripts" / "con_b.txt"
        trans_b.write_text(TRANSCRIPT_ALT, encoding="utf-8")

        first = register_and_run(
            root, trans_a, "clean_text", "Con Teppei", "ep051", ct
        )
        second = register_and_run(
            root, trans_b, "clean_text", "Another Show", "ep002", ct
        )

        # Source Intake wrote only registry + jobs.
        registry_dir = root / "Source Registry"
        jobs_dir = root / "Cleaning Jobs"
        check("registry contains only two entries",
              sorted(x.name for x in registry_dir.iterdir())
              == sorted([f"{first['sid']}.json", f"{second['sid']}.json"]))
        check("jobs contains only two jobs",
              sorted(x.name for x in jobs_dir.iterdir())
              == sorted([f"{first['sid']}.cleaning_job.json",
                         f"{second['sid']}.cleaning_job.json"]))

        # The cleaner wrote only artifacts + results + logs.
        results_dir = root / "Cleaning Results"
        check("results contains only two results",
              sorted(x.name for x in results_dir.iterdir())
              == sorted([f"{first['sid']}.cleaning_result.json",
                         f"{second['sid']}.cleaning_result.json"]))

        trans_logs = root / "Logs" / "Transcript Cleaner"
        check("transcript cleaner logs",
              sorted(x.name for x in trans_logs.iterdir())
              == sorted([f"{first['sid']}.cleaner.log",
                         f"{second['sid']}.cleaner.log"]))

        archive = root / "Cleaned Archive"
        check("archive contains two artifacts",
              len([x for x in archive.iterdir()
                   if x.suffix == ".txt"]) == 2)

        # No cross-ownership: registry/jobs untouched by the cleaner.
        for entry in registry_dir.iterdir():
            check(f"registry entry is json: {entry.name}",
                  entry.suffix == ".json")
        for entry in jobs_dir.iterdir():
            check(f"job entry is json: {entry.name}",
                  entry.suffix == ".json")
    finally:
        restore(saved)


# ============================================================
# Standalone CLI execution
# ============================================================

@test("7. transcript cleaner CLI invocation")
def _():
    root, saved = fixture()
    try:
        raw_file = root / "Raw Transcripts" / "con.txt"
        raw_file.write_text(TRANSCRIPT, encoding="utf-8")

        result = si.register_source(
            str(raw_file), "clean_text", "ja",
            "Con Teppei", "ep051"
        )
        job_path = pathlib.Path(result["cleaning_job_path"])
        sid = result["source_id"]
        output_path = pathlib.Path(load_json(job_path)["output_path"])

        cmd = cli_command(
            TRANSCRIPT_CLEANER, "clean_transcript",
            root / "Cleaning Results", "LOG_TRANSCRIPT_CLEANER",
            root / "Logs" / "Transcript Cleaner",
            root / "Source Registry", job_path,
        )
        completed = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
        )

        check("CLI exit 0", completed.returncode == 0,
              completed.stdout + completed.stderr)
        check("artifact exists", output_path.is_file())
        result_path = root / "Cleaning Results" / f"{sid}.cleaning_result.json"
        check("result exists", result_path.is_file())
        check("result success",
              load_json(result_path)["success"] is True)
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
