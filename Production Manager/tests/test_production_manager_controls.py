#!/usr/bin/env python3
"""
test_production_manager_controls.py

Deterministic tests for Production Manager user-control features (M1-6):
    - enhanced status report matches artifact state
    - stage toggles (--enable / --disable) disable stage launching
    - dry-run pipeline mode produces no writes

Uses sandboxed artifact directories and a scripted subprocess mock. No
real stage runs and no real pipeline artifact is written.

Run:
    python "Production Manager/tests/test_production_manager_controls.py"
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


def add_registered(dirs, sid=SID):
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


def add_cleaned(dirs, sid=SID):
    add_registered(dirs, sid)
    add_cleaning_job(dirs, sid)
    write_json(dirs["CLEANING_RESULTS"] / f"{sid}.cleaning_result.json", {
        "schema_version": "1",
        "source_id": sid,
        "success": True,
        "cleaned_artifact": f"Cleaned Archive/{sid}.clean.txt",
        "statistics": {},
        "errors": [],
    })
    (dirs["CLEANED_ARCHIVE"] / f"{sid}.clean.txt").write_text(
        "こんにちは。\n", encoding="utf-8")


def add_job_result(dirs, sid=SID):
    write_json(dirs["JOB_RESULTS"] / f"{sid}.job_builder_result.json", {
        "schema_version": "1",
        "source_id": sid,
        "success": True,
        "jobs_created": True,
        "job_count": 1,
        "total_characters": 10,
        "output_directory": f"jobs/{sid}",
        "errors": [],
    })
    write_json(dirs["JOBS"] / sid / "job_000001.json", {
        "source_id": sid, "cleaned_artifact": f"Cleaned Archive/{sid}.clean.txt",
        "job_number": 1, "characters": 10, "text": "こんにちは。",
    })


def add_request_result(dirs, sid=SID):
    write_json(dirs["REQUEST_RESULTS"] / f"{sid}.request_builder_result.json", {
        "schema_version": "1",
        "source_id": sid,
        "success": True,
        "requests_created": True,
        "jobs_processed": 1,
        "errors": [],
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
        "schema_version": "1",
        "source_id": sid,
        "model": "deepseek-v4-flash",
        "requests_processed": 1,
        "jobs": [{"request_id": "request_000001.json", "job_number": 1,
                  "status": "completed", "prompt_tokens": 1,
                  "completion_tokens": 1, "total_tokens": 2,
                  "finish_reason": "stop", "attempts": 1,
                  "http_status": 200, "timestamp": "t"}],
        "totals": {"prompt_tokens": 1, "completion_tokens": 1,
                   "total_tokens": 2},
    })
    write_json(dirs["RESPONSES"] / sid / "response_000001.json", {
        "model": "deepseek-v4-flash",
        "choices": [{"finish_reason": "stop",
                     "message": {"content": "{}"}}],
        "usage": {},
    })


def add_corpus_result(dirs, sid=SID):
    write_json(dirs["CORPUS_RESULTS"] / f"{sid}.corpus_builder_result.json", {
        "schema_version": "1",
        "source_id": sid,
        "success": True,
        "jobs_processed": 1,
        "jobs_failed": 0,
        "records_written": 1,
        "verified": True,
        "output_file": f"jsonl/{sid}.jsonl",
        "errors": [],
    })
    (dirs["JSONL"] / f"{sid}.jsonl").write_text(
        '{"text": "こんにちは。"}\n', encoding="utf-8")


def add_full(dirs, sid=SID):
    add_cleaned(dirs, sid)
    add_job_result(dirs, sid)
    add_request_result(dirs, sid)
    add_processing_result(dirs, sid)
    add_corpus_result(dirs, sid)


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class ScriptedRun:
    """subprocess.run mock dispatching by script filename."""

    SCRIPT_TO_STAGE = {
        "clean_transcript.py": "clean",
        "job builder.py": "jobs",
        "request builder.py": "requests",
        "deterministic_parser_client.py": "api",
        "corpus_builder.py": "corpus",
    }

    def __init__(self, dirs):
        self.dirs = dirs
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append(command)
        script_name = pathlib.Path(command[1]).name
        stage = self.SCRIPT_TO_STAGE.get(script_name)
        source_id = None
        if "--source" in command:
            source_id = command[command.index("--source") + 1]
        elif "--job" in command:
            job_path = command[command.index("--job") + 1]
            source_id = pathlib.Path(job_path).stem.replace(
                ".cleaning_job", "")
        if stage == "clean":
            self._materialize_clean(source_id)
        elif stage == "jobs":
            self._materialize_jobs(source_id)
        elif stage == "requests":
            self._materialize_requests(source_id)
        elif stage == "api":
            self._materialize_api(source_id)
        elif stage == "corpus":
            self._materialize_corpus(source_id)
        return FakeCompletedProcess(returncode=0, stdout="ok")

    def _materialize_clean(self, source_id):
        write_json(self.dirs["CLEANING_RESULTS"] / f"{source_id}.cleaning_result.json", {
            "schema_version": "1", "source_id": source_id, "success": True,
            "cleaned_artifact": f"Cleaned Archive/{source_id}.clean.txt",
            "statistics": {}, "errors": [],
        })
        (self.dirs["CLEANED_ARCHIVE"] / f"{source_id}.clean.txt").write_text(
            "こんにちは。\n", encoding="utf-8")

    def _materialize_jobs(self, source_id):
        write_json(self.dirs["JOB_RESULTS"] / f"{source_id}.job_builder_result.json", {
            "schema_version": "1", "source_id": source_id, "success": True,
            "jobs_created": True, "job_count": 1, "total_characters": 10,
            "output_directory": f"jobs/{source_id}", "errors": [],
        })
        write_json(self.dirs["JOBS"] / source_id / "job_000001.json",
                   {"source_id": source_id,
                    "cleaned_artifact": f"Cleaned Archive/{source_id}.clean.txt",
                    "job_number": 1, "characters": 10, "text": "こんにちは。"})

    def _materialize_requests(self, source_id):
        write_json(self.dirs["REQUEST_RESULTS"] / f"{source_id}.request_builder_result.json", {
            "schema_version": "1", "source_id": source_id, "success": True,
            "requests_created": True, "jobs_processed": 1, "errors": [],
        })
        write_json(self.dirs["REQUESTS"] / source_id / "request_000001.json",
                   {"source_id": source_id,
                    "cleaned_artifact": f"Cleaned Archive/{source_id}.clean.txt",
                    "job_number": 1, "prompt_version": "1.0",
                    "source_file": f"Cleaned Archive/{source_id}.clean.txt",
                    "source_name": source_id,
                    "messages": [{"role": "system", "content": "p"},
                                 {"role": "user", "content": "こんにちは。"}]})

    def _materialize_api(self, source_id):
        write_json(self.dirs["PROCESSING_RESULTS"] / f"{source_id}.processing_result.json", {
            "schema_version": "1", "source_id": source_id,
            "model": "deepseek-v4-flash", "requests_processed": 1,
            "jobs": [{"request_id": "request_000001.json", "job_number": 1,
                      "status": "completed", "prompt_tokens": 1,
                      "completion_tokens": 1, "total_tokens": 2,
                      "finish_reason": "stop", "attempts": 1,
                      "http_status": 200, "timestamp": "t"}],
            "totals": {"prompt_tokens": 1, "completion_tokens": 1,
                       "total_tokens": 2},
        })
        write_json(self.dirs["RESPONSES"] / source_id / "response_000001.json",
                   {"model": "deepseek-v4-flash",
                    "choices": [{"finish_reason": "stop",
                                 "message": {"content": "{}"}}],
                    "usage": {}})

    def _materialize_corpus(self, source_id):
        write_json(self.dirs["CORPUS_RESULTS"] / f"{source_id}.corpus_builder_result.json", {
            "schema_version": "1", "source_id": source_id, "success": True,
            "jobs_processed": 1, "jobs_failed": 0, "records_written": 1,
            "verified": True, "output_file": f"jsonl/{source_id}.jsonl",
            "errors": [],
        })
        (self.dirs["JSONL"] / f"{source_id}.jsonl").write_text(
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


@test("1. status report matches artifact state")
def _():
    root, dirs, saved = setup()
    try:
        add_cleaned(dirs)
        info = pm.state_for(SID)
        report = pm.format_report(SID, info)
        check("state in report", "cleaned" in report)
        check("stages section", "Stages:" in report)
        check("clean done", "clean     done" in report)
        check("jobs NEXT", "jobs      NEXT" in report)
        check("corpus pending", "corpus    pending" in report)

        add_full(dirs)
        info = pm.state_for(SID)
        report = pm.format_report(SID, info)
        check("corpus_available", "corpus_available" in report)
        check("corpus done", "corpus    done" in report)
    finally:
        restore(saved)


@test("1b. status report reflects disabled stages")
def _():
    root, dirs, saved = setup()
    try:
        add_cleaned(dirs)
        info = pm.state_for(SID)
        report = pm.format_report(SID, info, enabled=set(("clean", "jobs")))
        check("api disabled", "api       DISABLED" in report)
        check("corpus disabled", "corpus    DISABLED" in report)
    finally:
        restore(saved)


@test("2. disabled stages are not launched")
def _():
    root, dirs, saved = setup()
    try:
        add_registered(dirs)
        add_cleaning_job(dirs)
        scripted = ScriptedRun(dirs)
        real_run = pm.subprocess.run
        pm.subprocess.run = scripted

        # Only clean and jobs enabled: api/corpus/requests disabled.
        enabled = set(("clean", "jobs"))
        code = pm.run_pipeline(SID, auto=True, enabled=enabled)
        check("exit 0 (stopped at disabled boundary)", code == 0)
        check("only clean and jobs launched",
              [pathlib.Path(c[1]).name for c in scripted.calls]
              == ["clean_transcript.py", "job builder.py"])
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("2b. disabling clean prevents any launch")
def _():
    root, dirs, saved = setup()
    try:
        add_registered(dirs)
        add_cleaning_job(dirs)
        scripted = ScriptedRun(dirs)
        real_run = pm.subprocess.run
        pm.subprocess.run = scripted

        enabled = set(("jobs", "requests", "api", "corpus"))  # clean disabled
        code = pm.run_pipeline(SID, auto=True, enabled=enabled)
        check("exit 0", code == 0)
        check("no launches", len(scripted.calls) == 0)
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("3. dry run produces no writes")
def _():
    root, dirs, saved = setup()
    try:
        add_registered(dirs)
        add_cleaning_job(dirs)

        import paths as project_paths
        real = (project_paths.SOURCE_REGISTRY,
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
        before_real = {f: sorted(x.name for x in f.iterdir()) for f in real}

        scripted = ScriptedRun(dirs)
        real_run = pm.subprocess.run
        pm.subprocess.run = scripted

        code = pm.run_pipeline(SID, auto=True, dry_run=True)
        check("exit 0", code == 0)
        check("no subprocess launched", len(scripted.calls) == 0)
        check("no sandbox artifact materialized",
              not (dirs["CLEANING_RESULTS"] / f"{SID}.cleaning_result.json").exists())
        check("no manager log written",
              not (dirs["LOG_PRODUCTION_MANAGER"] / "manager.log").exists())

        after_real = {f: sorted(x.name for x in f.iterdir()) for f in real}
        for folder in real:
            check(f"real {folder.name} unchanged", after_real[folder] == before_real[folder])
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("3b. dry run reports the planned stages")
def _():
    root, dirs, saved = setup()
    try:
        add_registered(dirs)
        add_cleaning_job(dirs)
        plan = pm.plan_stages(SID)
        check("plan full pipeline",
              plan["plan"] == ["clean", "jobs", "requests", "api", "corpus"])
        check("boundary none", plan["boundary"] is None)

        # Disabled api: plan stops before api.
        plan = pm.plan_stages(SID, enabled=set(("clean", "jobs", "requests")))
        check("plan stops before api", plan["plan"] == ["clean", "jobs", "requests"])
        check("boundary disabled api", plan["boundary"] == "disabled:api")
    finally:
        restore(saved)


@test("4. CLI toggle parsing")
def _():
    root, dirs, saved = setup()
    try:
        check("enable", pm.resolve_enabled("clean,jobs", None) == {"clean", "jobs"})
        check("disable", pm.resolve_enabled(None, "api") ==
              {"clean", "jobs", "requests", "corpus"})
        check("both", pm.resolve_enabled("clean,jobs,requests", "requests") ==
              {"clean", "jobs"})
        raised = False
        try:
            pm.resolve_enabled("bogus", None)
        except pm.ManagerError:
            raised = True
        check("unknown stage rejected", raised)
    finally:
        restore(saved)


@test("5. status report CLI mode reflects artifact state")
def _():
    root, dirs, saved = setup()
    try:
        add_cleaned(dirs)
        code = pm.main(["--source", SID, "--enable", "clean,jobs"])
        check("exit 0", code == 0)
    finally:
        restore(saved)


@test("6. dry-run CLI produces no writes")
def _():
    root, dirs, saved = setup()
    try:
        add_registered(dirs)
        add_cleaning_job(dirs)
        scripted = ScriptedRun(dirs)
        real_run = pm.subprocess.run
        pm.subprocess.run = scripted

        code = pm.main(["--pipeline", "--dry-run", "--auto",
                        "--source", SID])
        check("exit 0", code == 0)
        check("no launches", len(scripted.calls) == 0)
        check("no manager log",
              not (dirs["LOG_PRODUCTION_MANAGER"] / "manager.log").exists())
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
