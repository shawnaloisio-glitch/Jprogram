#!/usr/bin/env python3
"""
test_production_manager_api.py

Tests for the Production Manager public application API (G0.1).

Verifies that the structured public functions (status, report, run_stage,
dry_run, pipeline) return the same information the CLI reports, and that
the CLI is a thin wrapper (argparse isolated; no printing in the API).

Run:
    python "Production Manager/tests/test_production_manager_api.py"
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


def setup():
    """Create isolated temp dirs and patch module globals."""
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
        "DATA_PROCESSOR": root / "Data Processor",
        "SUBTITLE_CLEANER": root / "Subtitle Cleaner",
        "TRANSCRIPT_CLEANER": root / "Transcript Cleaner",
        "LOG_PRODUCTION_MANAGER": root / "Logs" / "Production Manager",
    }
    for folder in dirs.values():
        folder.mkdir(parents=True)

    for script in ("job builder.py", "request builder.py",
                   "deepseek_client.py", "corpus_builder.py"):
        (dirs["DATA_PROCESSOR"] / script).write_text("", encoding="utf-8")
    (dirs["SUBTITLE_CLEANER"] / "clean_subtitles.py").write_text(
        "", encoding="utf-8")
    (dirs["TRANSCRIPT_CLEANER"] / "clean_transcript.py").write_text(
        "", encoding="utf-8")

    saved = {name: getattr(pm, name) for name in dirs}
    for name, folder in dirs.items():
        setattr(pm, name, folder)
    return root, dirs, saved


def restore(saved):
    for name, value in saved.items():
        setattr(pm, name, value)


def add_registered(dirs, sid=SID):
    write_json(dirs["SOURCE_REGISTRY"] / f"{sid}.json", {
        "schema_version": "1", "source_id": sid,
        "original_filename": "con.txt",
        "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        "source_type": "podcast_transcript", "format": "txt",
        "language": "ja", "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": "1.0",
    })


def add_cleaning_job(dirs, sid=SID):
    write_json(dirs["CLEANING_JOBS"] / f"{sid}.cleaning_job.json", {
        "schema_version": "1", "source_id": sid,
        "raw_path": "Raw Transcripts/con.txt",
        "source_type": "podcast_transcript",
        "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": "1.0",
        "output_path": f"Cleaned Archive/{sid}.clean.txt",
    })


def add_cleaned(dirs, sid=SID):
    add_registered(dirs, sid)
    add_cleaning_job(dirs, sid)
    write_json(dirs["CLEANING_RESULTS"] / f"{sid}.cleaning_result.json", {
        "schema_version": "1", "source_id": sid, "success": True,
        "cleaned_artifact": f"Cleaned Archive/{sid}.clean.txt",
        "statistics": {}, "errors": [],
    })
    (dirs["CLEANED_ARCHIVE"] / f"{sid}.clean.txt").write_text(
        "こんにちは。\n", encoding="utf-8")


def add_job_result(dirs, sid=SID):
    write_json(dirs["JOB_RESULTS"] / f"{sid}.job_builder_result.json", {
        "schema_version": "1", "source_id": sid, "success": True,
        "jobs_created": True, "job_count": 1, "total_characters": 10,
        "output_directory": f"jobs/{sid}", "errors": [],
    })
    write_json(dirs["JOBS"] / sid / "job_000001.json", {
        "source_id": sid, "cleaned_artifact": f"Cleaned Archive/{sid}.clean.txt",
        "job_number": 1, "characters": 10, "text": "こんにちは。",
    })


def add_request_result(dirs, sid=SID):
    write_json(dirs["REQUEST_RESULTS"] / f"{sid}.request_builder_result.json", {
        "schema_version": "1", "source_id": sid, "success": True,
        "requests_created": True, "jobs_processed": 1, "errors": [],
    })
    write_json(dirs["REQUESTS"] / sid / "request_000001.json", {
        "source_id": sid, "cleaned_artifact": f"Cleaned Archive/{sid}.clean.txt",
        "job_number": 1, "prompt_version": "1.0",
        "source_file": f"Cleaned Archive/{sid}.clean.txt",
        "source_name": sid,
        "messages": [{"role": "system", "content": "p"},
                     {"role": "user", "content": "こんにちは。"}],
    })


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("1. status() returns structured data matching state_for")
def _():
    root, dirs, saved = setup()
    try:
        add_cleaned(dirs)
        data = pm.status(SID)
        check("success true", data["success"] is True)
        check("source_id", data["source_id"] == SID)
        check("state", data["state"] == pm.state_for(SID)["state"])
        check("next_stage", data["next_stage"] == pm.state_for(SID)["next_stage"])
        check("failed_stage", data["failed_stage"] is None)
        check("stages is dict", isinstance(data["stages"], dict))
        check("evidence is dict", isinstance(data["evidence"], dict))
        check("stage statuses", data["stages"] == pm.stage_status(data["evidence"]))
    finally:
        restore(saved)


@test("2. report() equals status()")
def _():
    root, dirs, saved = setup()
    try:
        add_cleaned(dirs)
        check("report == status", pm.report(SID) == pm.status(SID))
    finally:
        restore(saved)


@test("3. dry_run() returns structured plan matching plan_stages")
def _():
    root, dirs, saved = setup()
    try:
        add_registered(dirs)
        add_cleaning_job(dirs)
        data = pm.dry_run(SID)
        plan = pm.plan_stages(SID)
        check("success true", data["success"] is True)
        check("source_id", data["source_id"] == SID)
        check("state", data["state"] == plan["state"])
        check("plan", data["plan"] == plan["plan"])
        check("boundary", data["boundary"] == plan["boundary"])
    finally:
        restore(saved)


@test("4. pipeline() structured dry-run returns exit_code 0 and plan")
def _():
    root, dirs, saved = setup()
    try:
        add_registered(dirs)
        add_cleaning_job(dirs)
        data = pm.pipeline(SID, auto=True, dry_run=True)
        check("success true", data["success"] is True)
        check("exit_code 0", data["exit_code"] == 0)
        check("state", data["state"] == "corpus_available")
        check("plan", data["plan"] == ["clean", "jobs", "requests", "api", "corpus"])
        check("no events", data["events"] == [])
    finally:
        restore(saved)


@test("5. pipeline() exit_code matches run_pipeline for complete source")
def _():
    root, dirs, saved = setup()
    try:
        add_registered(dirs)
        add_cleaning_job(dirs)
        # Scripted successful stages.
        real_run = pm.subprocess.run

        def fake(command, **kwargs):
            stage = pathlib.Path(command[1]).name
            if "--source" in command:
                sid = command[command.index("--source") + 1]
            else:
                sid = pathlib.Path(
                    command[command.index("--job") + 1]).stem.replace(
                        ".cleaning_job", "")
            if stage == "clean_transcript.py":
                write_json(dirs["CLEANING_RESULTS"] / f"{sid}.cleaning_result.json", {
                    "schema_version": "1", "source_id": sid, "success": True,
                    "cleaned_artifact": f"Cleaned Archive/{sid}.clean.txt",
                    "statistics": {}, "errors": []})
                (dirs["CLEANED_ARCHIVE"] / f"{sid}.clean.txt").write_text(
                    "こんにちは。\n", encoding="utf-8")
            elif stage == "job builder.py":
                write_json(dirs["JOB_RESULTS"] / f"{sid}.job_builder_result.json", {
                    "schema_version": "1", "source_id": sid, "success": True,
                    "jobs_created": True, "job_count": 1, "total_characters": 10,
                    "output_directory": f"jobs/{sid}", "errors": []})
                write_json(dirs["JOBS"] / sid / "job_000001.json", {
                    "source_id": sid, "cleaned_artifact": f"Cleaned Archive/{sid}.clean.txt",
                    "job_number": 1, "characters": 10, "text": "こんにちは。"})
            elif stage == "request builder.py":
                write_json(dirs["REQUEST_RESULTS"] / f"{sid}.request_builder_result.json", {
                    "schema_version": "1", "source_id": sid, "success": True,
                    "requests_created": True, "jobs_processed": 1, "errors": []})
                write_json(dirs["REQUESTS"] / sid / "request_000001.json", {
                    "source_id": sid, "cleaned_artifact": f"Cleaned Archive/{sid}.clean.txt",
                    "job_number": 1, "prompt_version": "1.0",
                    "source_file": f"Cleaned Archive/{sid}.clean.txt",
                    "source_name": sid,
                    "messages": [{"role": "system", "content": "p"},
                                 {"role": "user", "content": "こんにちは。"}]})
            elif stage == "deepseek_client.py":
                write_json(dirs["PROCESSING_RESULTS"] / f"{sid}.processing_result.json", {
                    "schema_version": "1", "source_id": sid, "model": "m",
                    "requests_processed": 1,
                    "jobs": [{"request_id": "request_000001.json", "job_number": 1,
                              "status": "completed", "prompt_tokens": 1,
                              "completion_tokens": 1, "total_tokens": 2,
                              "finish_reason": "stop", "attempts": 1,
                              "http_status": 200, "timestamp": "t"}],
                    "totals": {"prompt_tokens": 1, "completion_tokens": 1,
                               "total_tokens": 2}})
                write_json(dirs["RESPONSES"] / sid / "response_000001.json", {
                    "model": "m", "choices": [{"finish_reason": "stop",
                                               "message": {"content": "{}"}}],
                    "usage": {}})
            elif stage == "corpus_builder.py":
                write_json(dirs["CORPUS_RESULTS"] / f"{sid}.corpus_builder_result.json", {
                    "schema_version": "1", "source_id": sid, "success": True,
                    "jobs_processed": 1, "jobs_failed": 0, "records_written": 1,
                    "verified": True, "output_file": f"jsonl/{sid}.jsonl",
                    "errors": []})
                (dirs["JSONL"] / f"{sid}.jsonl").write_text(
                    '{"text": "こんにちは。"}\n', encoding="utf-8")
            return FakeCompletedProcess(returncode=0, stdout="ok")

        pm.subprocess.run = fake

        api_data = pm.pipeline(SID, auto=True)
        cli_code = pm.run_pipeline(SID, auto=True)
        check("pipeline exit_code 0", api_data["exit_code"] == 0)
        check("cli exit_code 0", cli_code == 0)
        check("exit_codes match", api_data["exit_codes"] ==
              {"clean": 0, "jobs": 0, "requests": 0, "api": 0, "corpus": 0})
        check("stages_run", api_data["stages_run"] ==
              ["clean", "jobs", "requests", "api", "corpus"])
        check("state", api_data["state"] == "corpus_available")
        check("events count", len(api_data["events"]) == 5)
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("6. run_stage() returns structured launch result with source_id")
def _():
    root, dirs, saved = setup()
    try:
        add_cleaned(dirs)
        add_job_result(dirs)
        real_run = pm.subprocess.run
        pm.subprocess.run = lambda command, **kw: FakeCompletedProcess(
            returncode=0)
        result = pm.run_stage(SID, "jobs")
        check("success true", result["success"] is True)
        check("source_id", result["source_id"] == SID)
        check("stage", result["stage"] == "jobs")
        check("exit_code", result["exit_code"] == 0)
        check("command", result["command"][-2:] == ["--source", SID])
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("7. public API functions never print")
def _():
    # The API functions must not emit console output; only render_* do.
    import io
    from contextlib import redirect_stdout

    root, dirs, saved = setup()
    try:
        add_cleaned(dirs)
        buf = io.StringIO()
        with redirect_stdout(buf):
            pm.status(SID)
            pm.report(SID)
            pm.dry_run(SID)
            pm.pipeline(SID, auto=True, dry_run=True)
        check("no output from API functions", buf.getvalue() == "")
    finally:
        restore(saved)


@test("8. CLI uses thin wrapper (argparse isolated in main)")
def _():
    import inspect
    source = pathlib.Path(PRODUCTION_MANAGER / "production_manager.py").read_text(
        encoding="utf-8")
    # argparse should appear only in the CLI entry section (main).
    import_lines = [ln for ln in source.splitlines()
                    if ln.startswith("import argparse")]
    check("argparse imported at top-level", len(import_lines) == 1)
    # main() must call the public API functions, not re-implement logic.
    main_src = source.split("def main(")[1].split("if __name__")[0]
    check("main calls status()", "status(" in main_src)
    check("main calls pipeline()", "pipeline(" in main_src)
    check("main calls run_stage()", "run_stage(" in main_src)


@test("9. structured results are JSON-serializable (GUI-friendly)")
def _():
    root, dirs, saved = setup()
    try:
        add_cleaned(dirs)
        for data in (pm.status(SID), pm.report(SID), pm.dry_run(SID)):
            json.dumps(data, ensure_ascii=False)
        check("status/report/dry_run serializable", True)
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
