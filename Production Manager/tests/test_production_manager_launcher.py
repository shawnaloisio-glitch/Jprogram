#!/usr/bin/env python3
"""
test_production_manager_launcher.py

Deterministic tests for the Production Manager stage launcher (M1-3).

Uses sandboxed paths and mocked subprocess execution. No real stage
program is launched and no real pipeline artifact is written.

Run:
    python "Production Manager/tests/test_production_manager_launcher.py"
"""

import json
import pathlib
import subprocess
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
PRODUCTION_MANAGER = PROJECT_ROOT / "Production Manager"
sys.path.insert(0, str(PRODUCTION_MANAGER))

import production_manager as pm


SID = "pod_conteppei_ep051"


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


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

    # Placeholder stage executables so the sandbox has real script paths.
    for script in ("job builder.py", "request builder.py",
                   "deepseek_client.py", "corpus_builder.py",
                   "deterministic_parser_client.py"):
        (dirs["DATA_PROCESSOR"] / script).write_text("", encoding="utf-8")
    (dirs["TRANSCRIPT_CLEANER"] / "clean_transcript.py").write_text(
        "", encoding="utf-8")

    saved = {name: getattr(pm, name) for name in dirs}
    for name, folder in dirs.items():
        setattr(pm, name, folder)
    return root, dirs, saved


def restore(saved):
    for name, value in saved.items():
        setattr(pm, name, value)


def add_cleaning_job(dirs, sid=SID, source_type="clean_text"):
    write_json(dirs["CLEANING_JOBS"] / f"{sid}.cleaning_job.json", {
        "schema_version": "1",
        "source_id": sid,
        "raw_path": "Raw Transcripts/con.txt",
        "source_type": source_type,
        "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": "1.0",
        "output_path": f"Cleaned Archive/{sid}.clean.txt",
    })


def add_job_result(dirs, sid=SID, success=True):
    write_json(dirs["JOB_RESULTS"] / f"{sid}.job_builder_result.json", {
        "schema_version": "1",
        "source_id": sid,
        "success": success,
        "jobs_created": success,
        "job_count": 1,
        "total_characters": 10,
        "output_directory": f"jobs/{sid}",
        "errors": [] if success else ["failed"],
    })


def add_processing_result(dirs, sid=SID, statuses=("completed",)):
    write_json(dirs["PROCESSING_RESULTS"] / f"{sid}.processing_result.json", {
        "schema_version": "1",
        "source_id": sid,
        "model": "deepseek-v4-flash",
        "requests_processed": len(statuses),
        "jobs": [
            {"request_id": f"request_{i:06d}.json", "job_number": i,
             "status": status, "prompt_tokens": 1, "completion_tokens": 1,
             "total_tokens": 2, "finish_reason": "stop", "attempts": 1,
             "http_status": 200, "timestamp": "t"}
            for i, status in enumerate(statuses, start=1)
        ],
        "totals": {"prompt_tokens": 1, "completion_tokens": 1,
                   "total_tokens": 2},
    })


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("1. each stage builds the correct subprocess command")
def _():
    root, dirs, saved = setup()
    try:
        add_cleaning_job(dirs)
        cmd = pm.build_command("clean", SID)
        check("clean uses --job",
              cmd[-2:] == ["--job", str(dirs["CLEANING_JOBS"] / f"{SID}.cleaning_job.json")])
        check("clean uses transcript cleaner",
              str(dirs["TRANSCRIPT_CLEANER"]) in cmd[1])

        for stage, script_name in (("jobs", "job builder.py"),
                                   ("requests", "request builder.py"),
                                   ("api", "deterministic_parser_client.py"),
                                   ("corpus", "corpus_builder.py")):
            cmd = pm.build_command(stage, SID)
            check(f"{stage} script", cmd[1].endswith(script_name))
            check(f"{stage} args", cmd[2:] == ["--source", SID])
    finally:
        restore(saved)


@test("1b. api stage uses the venv interpreter; other stages use sys.executable")
def _():
    root, dirs, saved = setup()
    try:
        add_cleaning_job(dirs)
        expected_venv = str(pm.PROJECT_ROOT / ".venv" / "Scripts" / "python.exe")
        cmd = pm.build_command("api", SID)
        check("api uses venv python", cmd[0] == expected_venv)
        check("api script is deterministic_parser_client.py",
              cmd[1].endswith("deterministic_parser_client.py"))
        check("api args unchanged", cmd[2:] == ["--source", SID])
        for stage in ("clean", "jobs", "requests", "corpus"):
            cmd = pm.build_command(stage, SID)
            check(f"{stage} still uses sys.executable", cmd[0] == sys.executable)
    finally:
        restore(saved)


@test("2. invalid stage rejected")
def _():
    root, dirs, saved = setup()
    try:
        raised = False
        try:
            pm.build_command("bogus", SID)
        except pm.ManagerError as exc:
            raised = "bogus" in str(exc)
        check("unknown stage rejected", raised)
    finally:
        restore(saved)


@test("3. missing source rejected")
def _():
    root, dirs, saved = setup()
    try:
        raised = False
        try:
            pm.main(["--run", "jobs"])
        except SystemExit:
            raised = True
        check("--run without --source rejected", raised)
    finally:
        restore(saved)


@test("4. missing executable handled")
def _():
    root, dirs, saved = setup()
    try:
        # Point jobs at a non-existent script directory.
        old = pm.STAGES["jobs"]["script"]
        pm.STAGES["jobs"]["script"] = lambda sid: dirs["DATA_PROCESSOR"] / "nope.py"
        result = pm.launch_stage("jobs", SID)
        check("success false", result["success"] is False)
        check("error mentions executable", "executable" in result["error"])
        pm.STAGES["jobs"]["script"] = old
    finally:
        restore(saved)


@test("5. non-zero subprocess handled")
def _():
    root, dirs, saved = setup()
    try:
        real_run = pm.subprocess.run
        pm.subprocess.run = lambda *a, **k: FakeCompletedProcess(
            returncode=3, stdout="out", stderr="boom")
        result = pm.launch_stage("jobs", SID)
        check("success false", result["success"] is False)
        check("exit code captured", result["exit_code"] == 3)
        check("stderr captured", "boom" in result["stderr"])
        check("error mentions exit", "3" in result["error"])
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("6. result artifact success=false handled")
def _():
    root, dirs, saved = setup()
    try:
        add_job_result(dirs, success=False)
        real_run = pm.subprocess.run
        pm.subprocess.run = lambda *a, **k: FakeCompletedProcess(
            returncode=0)
        result = pm.launch_stage("jobs", SID)
        check("success false despite exit 0", result["success"] is False)
        check("error mentions failure",
              "failure" in result["error"])
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("7. successful launch refreshes state")
def _():
    root, dirs, saved = setup()
    try:
        add_job_result(dirs, success=True)
        real_run = pm.subprocess.run
        pm.subprocess.run = lambda *a, **k: FakeCompletedProcess(
            returncode=0)
        result = pm.launch_stage("jobs", SID)
        check("success true", result["success"] is True)
        check("state refreshed", result["state"] is not None)
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("7b. api stage validates processing result")
def _():
    root, dirs, saved = setup()
    try:
        add_processing_result(dirs, statuses=("completed",))
        real_run = pm.subprocess.run
        pm.subprocess.run = lambda *a, **k: FakeCompletedProcess(
            returncode=0)
        result = pm.launch_stage("api", SID)
        check("api success", result["success"] is True)
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("7c. api stage fails when a job failed")
def _():
    root, dirs, saved = setup()
    try:
        add_processing_result(dirs, statuses=("failed",))
        real_run = pm.subprocess.run
        pm.subprocess.run = lambda *a, **k: FakeCompletedProcess(
            returncode=0)
        result = pm.launch_stage("api", SID)
        check("api reports failure", result["success"] is False)
        check("error mentions failure",
              "failure" in result["error"])
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("8. forbidden pipeline writes")
def _():
    import paths as project_paths

    root, dirs, saved = setup()
    try:
        real_run = pm.subprocess.run
        pm.subprocess.run = lambda *a, **k: FakeCompletedProcess(
            returncode=0)

        before = {
            p: sorted(x.name for x in p.iterdir())
            for p in (project_paths.SOURCE_REGISTRY,
                      project_paths.CLEANING_JOBS,
                      project_paths.CLEANING_RESULTS,
                      project_paths.CLEANED_ARCHIVE,
                      project_paths.JOBS,
                      project_paths.JOB_RESULTS,
                      project_paths.REQUESTS,
                      project_paths.REQUEST_RESULTS,
                      project_paths.RESPONSES,
                      project_paths.PROCESSING_RESULTS,
                      project_paths.CORPUS_RESULTS,
                      project_paths.JSONL)
        }

        # Force an "executable missing" path so nothing actually launches.
        old = pm.STAGES["jobs"]["script"]
        pm.STAGES["jobs"]["script"] = lambda sid: dirs["DATA_PROCESSOR"] / "nope.py"
        result = pm.launch_stage("jobs", SID)
        check("reported failure", result["success"] is False)
        pm.STAGES["jobs"]["script"] = old

        after = {
            p: sorted(x.name for x in p.iterdir())
            for p in before
        }
        for folder in before:
            check(f"no write to {folder.name}", after[folder] == before[folder])
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("9. forbidden imports")
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
    check("subprocess is the only executor",
          "import subprocess" in import_lines)


@test("10. timeout handling")
def _():
    root, dirs, saved = setup()
    try:
        real_run = pm.subprocess.run
        def raise_timeout(*a, **k):
            raise subprocess.TimeoutExpired(cmd=a[0], timeout=5)
        pm.subprocess.run = raise_timeout
        result = pm.launch_stage("jobs", SID, timeout=5)
        check("success false", result["success"] is False)
        check("error mentions timeout", "timed out" in result["error"])
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("10b. OSError handled")
def _():
    root, dirs, saved = setup()
    try:
        real_run = pm.subprocess.run
        pm.subprocess.run = lambda *a, **k: (_ for _ in ()).throw(OSError("no"))
        result = pm.launch_stage("jobs", SID)
        check("success false", result["success"] is False)
        check("error mentions launch", "failed to launch" in result["error"])
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("10c. manager log written only to manager folder")
def _():
    root, dirs, saved = setup()
    try:
        log_file = pm.log_manager_entry(SID, "jobs", ["python", "x.py"],
                                        0, True, error=None)
        check("log in manager folder",
              dirs["LOG_PRODUCTION_MANAGER"] in log_file.parents)
        check("log exists", log_file.is_file())
        content = log_file.read_text(encoding="utf-8")
        check("log has source", SID in content)
        check("log has stage", "jobs" in content)
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
