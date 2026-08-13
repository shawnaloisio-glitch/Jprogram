#!/usr/bin/env python3
"""
test_production_manager_inprocess.py

Deterministic tests for the in-process pipeline execution path
(launch_stage_inprocess / pipeline(..., launcher=launch_stage_inprocess)).

Uses sandboxed artifact trees and scripted run_inprocess stubs that
materialize each stage's expected result artifact, mirroring
test_production_manager_pipeline.py's approach for the subprocess path.
No real stage module and no real ja_ginza model is loaded here -- see
DONE.md for the separate real-source manual verification that covers
that ground.

Run:
    python "Production Manager/tests/test_production_manager_inprocess.py"
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
        "TRANSCRIPT_CLEANER": root / "Transcript Cleaner",
        "LOG_PRODUCTION_MANAGER": root / "Logs" / "Production Manager",
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


def add_cleaning_result(dirs, sid=SID):
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


def add_processing_result(dirs, sid=SID):
    write_json(dirs["PROCESSING_RESULTS"] / f"{sid}.processing_result.json", {
        "schema_version": "1", "source_id": sid, "model": "deepseek-v4-flash",
        "requests_processed": 1,
        "jobs": [{"request_id": "request_000001.json", "job_number": 1,
                  "status": "completed", "prompt_tokens": 1,
                  "completion_tokens": 1, "total_tokens": 2,
                  "finish_reason": "stop", "attempts": 1,
                  "http_status": 200, "timestamp": "t"}],
        "totals": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    })
    write_json(dirs["RESPONSES"] / sid / "response_000001.json", {
        "model": "deepseek-v4-flash",
        "choices": [{"finish_reason": "stop",
                     "message": {"content": "{}"}}],
        "usage": {},
    })


def add_corpus_result(dirs, sid=SID):
    write_json(dirs["CORPUS_RESULTS"] / f"{sid}.corpus_builder_result.json", {
        "schema_version": "1", "source_id": sid, "success": True,
        "jobs_processed": 1, "jobs_failed": 0, "records_written": 1,
        "verified": True, "output_file": f"jsonl/{sid}.jsonl", "errors": [],
    })
    (dirs["JSONL"] / f"{sid}.jsonl").write_text(
        '{"text": "こんにちは。"}\n', encoding="utf-8")


PM_DIRS = None

MATERIALIZE = {
    "clean": add_cleaning_result,
    "jobs": add_job_result,
    "requests": add_request_result,
    "api": add_processing_result,
    "corpus": add_corpus_result,
}


def succeed_inprocess(stage):
    def run(source_id):
        MATERIALIZE[stage](PM_DIRS, source_id)
        return 0
    return run


def fail_inprocess(source_id):
    return 5


def raise_inprocess(source_id):
    raise RuntimeError("boom -- unexpected exception mid-stage")


def patch_run_inprocess(effects):
    """Patch STAGES[stage]['run_inprocess'] for each stage; return the
    original callables so the caller can restore them."""
    saved = {}
    for stage, fn in effects.items():
        saved[stage] = pm.STAGES[stage]["run_inprocess"]
        pm.STAGES[stage]["run_inprocess"] = fn
    return saved


def unpatch_run_inprocess(saved):
    for stage, fn in saved.items():
        pm.STAGES[stage]["run_inprocess"] = fn


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("1. launch_stage_inprocess: success path materializes state and result")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        saved_run = patch_run_inprocess({"clean": succeed_inprocess("clean")})
        result = pm.launch_stage_inprocess("clean", SID)
        check("success True", result["success"] is True, result)
        check("exit_code 0", result["exit_code"] == 0)
        check("error is None", result["error"] is None)
        check("state populated", result["state"] is not None)
        unpatch_run_inprocess(saved_run)
    finally:
        restore(saved)


@test("2. launch_stage_inprocess: non-zero exit code is a failure, no validate call")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        saved_run = patch_run_inprocess({"clean": fail_inprocess})
        result = pm.launch_stage_inprocess("clean", SID)
        check("success False", result["success"] is False)
        check("exit_code 5", result["exit_code"] == 5)
        check("error mentions exit code", "exited with code 5" in result["error"])
        unpatch_run_inprocess(saved_run)
    finally:
        restore(saved)


@test("3. launch_stage_inprocess: exit 0 but missing result artifact is a failure")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)

        def run_no_artifact(source_id):
            return 0  # exit 0 but never writes the cleaning_result.json

        saved_run = patch_run_inprocess({"clean": run_no_artifact})
        result = pm.launch_stage_inprocess("clean", SID)
        check("success False", result["success"] is False)
        check("error mentions missing artifact",
              "missing or unreadable" in result["error"], result["error"])
        unpatch_run_inprocess(saved_run)
    finally:
        restore(saved)


@test("4. launch_stage_inprocess: an unexpected exception is caught, not raised")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        saved_run = patch_run_inprocess({"clean": raise_inprocess})
        result = pm.launch_stage_inprocess("clean", SID)  # must not raise
        check("success False", result["success"] is False)
        check("error mentions the exception",
              "boom" in result["error"], result["error"])
        unpatch_run_inprocess(saved_run)
    finally:
        restore(saved)


@test("5. launch_stage_inprocess: unknown stage is a clean failure, not a crash")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        result = pm.launch_stage_inprocess("not_a_real_stage", SID)
        check("success False", result["success"] is False)
        check("error mentions unknown stage", "unknown stage" in result["error"])
    finally:
        restore(saved)


@test("6. pipeline(launcher=launch_stage_inprocess): full auto run, all 5 stages")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        effects = {stage: succeed_inprocess(stage) for stage in MATERIALIZE}
        saved_run = patch_run_inprocess(effects)

        confirm_fn = lambda _p: (_ for _ in ()).throw(
            AssertionError("no confirmations expected in auto mode"))
        data = pm.pipeline(SID, auto=True, confirm_fn=confirm_fn,
                            launcher=pm.launch_stage_inprocess)
        check("success True", data["success"] is True, data)
        check("exit_code 0", data["exit_code"] == 0)
        check("all five stages ran",
              data["stages_run"] == ["clean", "jobs", "requests", "api", "corpus"],
              data["stages_run"])
        check("state corpus_available", data["state"] == "corpus_available")
        unpatch_run_inprocess(saved_run)
    finally:
        restore(saved)


@test("7. pipeline(launcher=launch_stage_inprocess): a mid-batch stage failure "
      "stops that source cleanly, matching launch_stage's own failure shape")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        effects = {
            "clean": succeed_inprocess("clean"),
            "jobs": succeed_inprocess("jobs"),
            "requests": raise_inprocess,  # fails here
            "api": succeed_inprocess("api"),
            "corpus": succeed_inprocess("corpus"),
        }
        saved_run = patch_run_inprocess(effects)
        data = pm.pipeline(SID, auto=True, launcher=pm.launch_stage_inprocess)
        check("success False", data["success"] is False)
        check("failed_stage requests", data["failed_stage"] == "requests")
        check("stopped before api/corpus",
              "api" not in data["stages_run"] and "corpus" not in data["stages_run"],
              data["stages_run"])
        unpatch_run_inprocess(saved_run)
    finally:
        restore(saved)


@test("8. pipeline() with no launcher argument still goes through subprocess.run "
      "(the pre-existing path is genuinely unchanged, not just aliased)")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)

        # Empty stage scripts so build_command() finds a real file to launch;
        # subprocess.run itself is mocked below so their content never runs.
        for script in ("job builder.py", "request builder.py",
                       "corpus_builder.py", "deterministic_parser_client.py"):
            (dirs["DATA_PROCESSOR"] / script).write_text("", encoding="utf-8")
        (dirs["TRANSCRIPT_CLEANER"] / "clean_transcript.py").write_text(
            "", encoding="utf-8")

        class FakeCompletedProcess:
            def __init__(self, returncode=0, stdout="", stderr=""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        materialize = MATERIALIZE
        calls = []

        def scripted_run(command, **kwargs):
            calls.append(command)
            script = pathlib.Path(command[1]).name
            stage = {
                "clean_transcript.py": "clean", "job builder.py": "jobs",
                "request builder.py": "requests",
                "deterministic_parser_client.py": "api",
                "corpus_builder.py": "corpus",
            }[script]
            source_id = command[command.index("--source") + 1] \
                if "--source" in command else SID
            materialize[stage](dirs, source_id)
            return FakeCompletedProcess(returncode=0)

        real_run = pm.subprocess.run
        pm.subprocess.run = scripted_run
        try:
            data = pm.pipeline(SID, auto=True)  # no launcher argument at all
            check("success True", data["success"] is True, data)
            check("subprocess.run was actually invoked", len(calls) == 5,
                  f"expected 5 subprocess calls, got {len(calls)}")
        finally:
            pm.subprocess.run = real_run
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
