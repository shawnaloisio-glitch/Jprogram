#!/usr/bin/env python3
"""
test_production_manager.py

Deterministic tests for the Production Manager artifact-state engine.

Run:
    python "Production Manager/tests/test_production_manager.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
PRODUCTION_MANAGER = PROJECT_ROOT / "Production Manager"
sys.path.insert(0, str(PRODUCTION_MANAGER))

import production_manager as pm


SID = "pod_conteppei_ep051"


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def write_corrupt(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ not valid json", encoding="utf-8")


def setup():
    """Create isolated temp artifact trees and patch module globals."""
    root = pathlib.Path(tempfile.mkdtemp())
    dirs = {
        "SOURCE_REGISTRY": root / "Source Registry",
        "CLEANING_JOBS": root / "Cleaning Jobs",
        "CLEANING_RESULTS": root / "Cleaning Results",
        "CLEANED_ARCHIVE": root / "Cleaned Archive",
        "JOB_RESULTS": root / "Job Results",
        "JOBS": root / "jobs",
        "REQUEST_RESULTS": root / "Request Results",
        "REQUESTS": root / "requests",
        "RESPONSES": root / "responses",
        "PROCESSING_RESULTS": root / "Processing Results",
        "CORPUS_RESULTS": root / "Corpus Results",
        "JSONL": root / "jsonl",
    }
    for folder in dirs.values():
        folder.mkdir(parents=True)

    saved = {name: getattr(pm, name) for name in dirs}
    for name, folder in dirs.items():
        setattr(pm, name, folder)
    return root, dirs, saved


def restore(saved):
    for name, value in saved.items():
        setattr(pm, name, value)


def add_registry(dirs, sid=SID):
    write_json(dirs["SOURCE_REGISTRY"] / f"{sid}.json", {
        "schema_version": "1",
        "source_id": sid,
        "original_filename": "con.txt",
        "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        "source_type": "clean_text",
        "format": "txt",
        "language": "ja",
        "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": "1.0",
    })


def add_cleaning_job(dirs, sid=SID):
    write_json(dirs["CLEANING_JOBS"] / f"{sid}.cleaning_job.json", {
        "schema_version": "1",
        "source_id": sid,
        "raw_path": "Raw Transcripts/con.txt",
        "source_type": "clean_text",
        "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": "1.0",
        "output_path": f"Cleaned Archive/{sid}.clean.txt",
    })


def add_cleaning_result(dirs, sid=SID, success=True):
    write_json(dirs["CLEANING_RESULTS"] / f"{sid}.cleaning_result.json", {
        "schema_version": "1",
        "source_id": sid,
        "success": success,
        "cleaned_artifact": f"Cleaned Archive/{sid}.clean.txt",
        "statistics": {},
        "errors": [] if success else ["cleaning failed"],
    })


def add_cleaned_artifact(dirs, sid=SID):
    path = dirs["CLEANED_ARCHIVE"] / f"{sid}.clean.txt"
    path.write_text("こんにちは。\n", encoding="utf-8")


def add_job_result(dirs, sid=SID, success=True):
    write_json(dirs["JOB_RESULTS"] / f"{sid}.job_builder_result.json", {
        "schema_version": "1",
        "source_id": sid,
        "success": success,
        "jobs_created": success,
        "job_count": 2,
        "total_characters": 100,
        "output_directory": f"jobs/{sid}",
        "errors": [] if success else ["job build failed"],
    })


def add_jobs(dirs, sid=SID, count=2):
    job_dir = dirs["JOBS"] / sid
    for i in range(1, count + 1):
        write_json(job_dir / f"job_{i:06d}.json", {
            "source_id": sid,
            "cleaned_artifact": f"Cleaned Archive/{sid}.clean.txt",
            "job_number": i,
            "characters": 50,
            "text": "text",
        })


def add_request_result(dirs, sid=SID, success=True):
    write_json(dirs["REQUEST_RESULTS"] / f"{sid}.request_builder_result.json", {
        "schema_version": "1",
        "source_id": sid,
        "success": success,
        "requests_created": success,
        "jobs_processed": 2,
        "errors": [] if success else ["request build failed"],
    })


def add_requests(dirs, sid=SID, count=2):
    request_dir = dirs["REQUESTS"] / sid
    for i in range(1, count + 1):
        write_json(request_dir / f"request_{i:06d}.json", {
            "source_id": sid,
            "cleaned_artifact": f"Cleaned Archive/{sid}.clean.txt",
            "job_number": i,
            "prompt_version": "1.0",
            "source_file": f"Cleaned Archive/{sid}.clean.txt",
            "source_name": sid,
            "messages": [
                {"role": "system", "content": "prompt"},
                {"role": "user", "content": "text"},
            ],
        })


def add_responses(dirs, sid=SID, count=2):
    response_dir = dirs["RESPONSES"] / sid
    for i in range(1, count + 1):
        write_json(response_dir / f"response_{i:06d}.json", {
            "model": "deepseek-v4-flash",
            "choices": [{"finish_reason": "stop",
                         "message": {"content": "{}"}}],
            "usage": {},
        })


def add_processing_result(dirs, sid=SID, statuses=("completed", "completed")):
    write_json(dirs["PROCESSING_RESULTS"] / f"{sid}.processing_result.json", {
        "schema_version": "1",
        "source_id": sid,
        "model": "deepseek-v4-flash",
        "requests_processed": len(statuses),
        "jobs": [
            {
                "request_id": f"request_{i:06d}.json",
                "job_number": i,
                "status": status,
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
                "finish_reason": "stop",
                "attempts": 1,
                "http_status": 200,
                "timestamp": "2026-08-01 12:00:00",
            }
            for i, status in enumerate(statuses, start=1)
        ],
        "totals": {"prompt_tokens": 20, "completion_tokens": 10,
                   "total_tokens": 30},
    })


def add_corpus_result(dirs, sid=SID, success=True):
    write_json(dirs["CORPUS_RESULTS"] / f"{sid}.corpus_builder_result.json", {
        "schema_version": "1",
        "source_id": sid,
        "success": success,
        "jobs_processed": 1,
        "jobs_failed": 0,
        "records_written": 1,
        "verified": success,
        "output_file": f"jsonl/{sid}.jsonl",
        "errors": [] if success else ["corpus failed"],
    })


def add_jsonl(dirs, sid=SID):
    (dirs["JSONL"] / f"{sid}.jsonl").write_text(
        '{"text": "こんにちは。"}\n', encoding="utf-8")


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("registered: only registry exists")
def _():
    root, dirs, saved = setup()
    try:
        add_registry(dirs)
        info = pm.state_for(SID)
        check("state", info["state"] == "registered")
        check("next stage", info["next_stage"] == "intake")
    finally:
        restore(saved)


@test("waiting_for_clean: cleaning job exists, no result")
def _():
    root, dirs, saved = setup()
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        info = pm.state_for(SID)
        check("state", info["state"] == "waiting_for_clean")
        check("next stage", info["next_stage"] == "clean")
    finally:
        restore(saved)


@test("cleaned: cleaning result success + artifact present")
def _():
    root, dirs, saved = setup()
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        add_cleaning_result(dirs)
        add_cleaned_artifact(dirs)
        info = pm.state_for(SID)
        check("state", info["state"] == "cleaned")
        check("next stage", info["next_stage"] == "jobs")
    finally:
        restore(saved)


@test("jobs_created: job result success")
def _():
    root, dirs, saved = setup()
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        add_cleaning_result(dirs)
        add_cleaned_artifact(dirs)
        add_job_result(dirs)
        add_jobs(dirs)
        info = pm.state_for(SID)
        check("state", info["state"] == "jobs_created")
        check("next stage", info["next_stage"] == "requests")
    finally:
        restore(saved)


@test("requests_created: request result success")
def _():
    root, dirs, saved = setup()
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        add_cleaning_result(dirs)
        add_cleaned_artifact(dirs)
        add_job_result(dirs)
        add_jobs(dirs)
        add_request_result(dirs)
        add_requests(dirs)
        info = pm.state_for(SID)
        check("state", info["state"] == "requests_created")
        check("next stage", info["next_stage"] == "api")
    finally:
        restore(saved)


@test("api_processing: requests exist, responses partial")
def _():
    root, dirs, saved = setup()
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        add_cleaning_result(dirs)
        add_cleaned_artifact(dirs)
        add_job_result(dirs)
        add_jobs(dirs)
        add_request_result(dirs)
        add_requests(dirs)
        add_responses(dirs, count=1)
        info = pm.state_for(SID)
        check("state", info["state"] == "api_processing")
        check("next stage", info["next_stage"] == "api")
    finally:
        restore(saved)


@test("api_complete: all responses + processing result")
def _():
    root, dirs, saved = setup()
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        add_cleaning_result(dirs)
        add_cleaned_artifact(dirs)
        add_job_result(dirs)
        add_jobs(dirs)
        add_request_result(dirs)
        add_requests(dirs)
        add_responses(dirs, count=2)
        add_processing_result(dirs)
        info = pm.state_for(SID)
        check("state", info["state"] == "api_complete")
        check("next stage", info["next_stage"] == "corpus")
    finally:
        restore(saved)


@test("corpus_available: jsonl + corpus result success")
def _():
    root, dirs, saved = setup()
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        add_cleaning_result(dirs)
        add_cleaned_artifact(dirs)
        add_job_result(dirs)
        add_jobs(dirs)
        add_request_result(dirs)
        add_requests(dirs)
        add_responses(dirs, count=2)
        add_processing_result(dirs)
        add_corpus_result(dirs)
        add_jsonl(dirs)
        info = pm.state_for(SID)
        check("state", info["state"] == "corpus_available")
        check("next stage", info["next_stage"] is None)
    finally:
        restore(saved)


@test("failed cleaner: cleaning result success=false")
def _():
    root, dirs, saved = setup()
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        add_cleaning_result(dirs, success=False)
        info = pm.state_for(SID)
        check("state", info["state"] == "failed")
        check("failed stage", info["failed_stage"] == "clean")
        check("next stage", info["next_stage"] == "clean")
    finally:
        restore(saved)


@test("failed API: processing result records a failed job")
def _():
    root, dirs, saved = setup()
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        add_cleaning_result(dirs)
        add_cleaned_artifact(dirs)
        add_job_result(dirs)
        add_jobs(dirs)
        add_request_result(dirs)
        add_requests(dirs)
        add_responses(dirs, count=2)
        add_processing_result(dirs, statuses=("completed", "failed"))
        info = pm.state_for(SID)
        check("state", info["state"] == "failed")
        check("failed stage", info["failed_stage"] == "api")
        check("next stage", info["next_stage"] == "api")
    finally:
        restore(saved)


@test("corrupted result artifact is treated as absent, not failed")
def _():
    root, dirs, saved = setup()
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        add_cleaning_result(dirs)
        add_cleaned_artifact(dirs)
        # Corrupt the job result; jobs still exist on disk.
        write_corrupt(dirs["JOB_RESULTS"] / f"{SID}.job_builder_result.json")
        add_jobs(dirs)
        info = pm.state_for(SID)
        check("state falls back to jobs_created",
              info["state"] == "jobs_created")
        check("job_result_error recorded",
              info["evidence"]["job_result_error"] is not None)
    finally:
        restore(saved)


@test("no hidden state: identical artifacts give identical states")
def _():
    root, dirs, saved = setup()
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        add_cleaning_result(dirs)
        add_cleaned_artifact(dirs)
        add_job_result(dirs)
        add_jobs(dirs)
        add_request_result(dirs)
        add_requests(dirs)
        add_responses(dirs, count=2)
        add_processing_result(dirs)
        add_corpus_result(dirs)
        add_jsonl(dirs)

        a = pm.state_for(SID)
        b = pm.state_for(SID)
        check("deterministic state", a["state"] == b["state"])
        check("deterministic evidence", a["evidence"] == b["evidence"])
    finally:
        restore(saved)


@test("no imports from pipeline stages")
def _():
    source = pathlib.Path(PRODUCTION_MANAGER / "production_manager.py").read_text(
        encoding="utf-8")
    import_lines = "\n".join(
        ln for ln in source.splitlines()
        if ln.lstrip().startswith("import ") or ln.lstrip().startswith("from ")
    )
    for forbidden in ("clean_subtitles", "clean_transcript", "job builder",
                      "request builder", "deepseek_client", "corpus_builder",
                      "source_intake", "cleaning_job", "registry", "resolver",
                      "response_validator", "Analysis", "schemas"):
        check(f"no {forbidden!r}", forbidden not in import_lines)


@test("CLI: --source reports state")
def _():
    root, dirs, saved = setup()
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        code = pm.main(["--source", SID])
        check("exit 0", code == 0)
    finally:
        restore(saved)


@test("CLI: missing --source rejected")
def _():
    root, dirs, saved = setup()
    try:
        raised = False
        try:
            pm.main([])
        except SystemExit:
            raised = True
        check("argparse rejects missing --source", raised)
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
