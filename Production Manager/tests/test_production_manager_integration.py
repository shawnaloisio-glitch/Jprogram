#!/usr/bin/env python3
"""
test_production_manager_integration.py

End-to-end integration tests for the Production Manager (M1-5).

These tests run the real Production Manager orchestration (real artifact
readers, real state engine, real pipeline loop) against sandboxed
artifact directories. Subprocess execution is mocked so no real stage
program runs and no real pipeline artifact is written.

Run:
    python "Production Manager/tests/test_production_manager_integration.py"
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


# ============================================================
# Artifact builders (schema-valid, matching the real writers)
# ============================================================

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def registry_artifact(sid=SID):
    return {
        "schema_version": "1",
        "source_id": sid,
        "original_filename": "con.txt",
        "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        "source_type": "clean_text",
        "format": "txt",
        "language": "ja",
        "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": "1.0",
    }


def cleaning_job_artifact(sid=SID):
    return {
        "schema_version": "1",
        "source_id": sid,
        "raw_path": "Raw Transcripts/con.txt",
        "source_type": "clean_text",
        "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": "1.0",
        "output_path": f"Cleaned Archive/{sid}.clean.txt",
    }


def cleaning_result_artifact(sid=SID, success=True):
    return {
        "schema_version": "1",
        "source_id": sid,
        "success": success,
        "cleaned_artifact": f"Cleaned Archive/{sid}.clean.txt",
        "statistics": {"characters_read": 10, "characters_written": 8},
        "errors": [] if success else ["cleaning failed"],
    }


def job_result_artifact(sid=SID, success=True):
    return {
        "schema_version": "1",
        "source_id": sid,
        "success": success,
        "jobs_created": success,
        "job_count": 1,
        "total_characters": 10,
        "output_directory": f"jobs/{sid}",
        "errors": [] if success else ["job build failed"],
    }


def job_artifact(sid=SID, job_number=1):
    return {
        "source_id": sid,
        "cleaned_artifact": f"Cleaned Archive/{sid}.clean.txt",
        "job_number": job_number,
        "characters": 10,
        "text": "こんにちは。\n",
    }


def request_result_artifact(sid=SID, success=True):
    return {
        "schema_version": "1",
        "source_id": sid,
        "success": success,
        "requests_created": success,
        "jobs_processed": 1,
        "errors": [] if success else ["request build failed"],
    }


def request_artifact(sid=SID, job_number=1):
    return {
        "source_id": sid,
        "cleaned_artifact": f"Cleaned Archive/{sid}.clean.txt",
        "job_number": job_number,
        "prompt_version": "1.0",
        "source_file": f"Cleaned Archive/{sid}.clean.txt",
        "source_name": sid,
        "messages": [
            {"role": "system", "content": "parser prompt"},
            {"role": "user", "content": "こんにちは。\n"},
        ],
    }


def response_artifact(sid=SID, job_number=1):
    return {
        "model": "deepseek-v4-flash",
        "choices": [{"finish_reason": "stop",
                     "message": {"content": "{}"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5,
                  "total_tokens": 15},
    }


def processing_result_artifact(sid=SID, statuses=("completed",)):
    return {
        "schema_version": "1",
        "source_id": sid,
        "model": "deepseek-v4-flash",
        "requests_processed": len(statuses),
        "jobs": [
            {"request_id": f"request_{i:06d}.json", "job_number": i,
             "status": status, "prompt_tokens": 10, "completion_tokens": 5,
             "total_tokens": 15, "finish_reason": "stop", "attempts": 1,
             "http_status": 200, "timestamp": "2026-08-01 12:00:00"}
            for i, status in enumerate(statuses, start=1)
        ],
        "totals": {"prompt_tokens": 10 * len(statuses),
                   "completion_tokens": 5 * len(statuses),
                   "total_tokens": 15 * len(statuses)},
    }


def corpus_result_artifact(sid=SID, success=True):
    return {
        "schema_version": "1",
        "source_id": sid,
        "success": success,
        "jobs_processed": 1,
        "jobs_failed": 0,
        "records_written": 1,
        "verified": success,
        "output_file": f"jsonl/{sid}.jsonl",
        "errors": [] if success else ["corpus failed"],
    }


# ============================================================
# Sandbox fixture
# ============================================================

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
                   "deepseek_client.py", "corpus_builder.py"):
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


# ============================================================
# Intake-level fixtures
# ============================================================

def add_registered(dirs, sid=SID):
    """Source Registry only (no cleaning job)."""
    write_json(dirs["SOURCE_REGISTRY"] / f"{sid}.json", registry_artifact(sid))


def add_waiting_for_clean(dirs, sid=SID):
    add_registered(dirs, sid)
    write_json(dirs["CLEANING_JOBS"] / f"{sid}.cleaning_job.json",
               cleaning_job_artifact(sid))


def add_cleaned(dirs, sid=SID):
    add_waiting_for_clean(dirs, sid)
    write_json(dirs["CLEANING_RESULTS"] / f"{sid}.cleaning_result.json",
               cleaning_result_artifact(sid))
    (dirs["CLEANED_ARCHIVE"] / f"{sid}.clean.txt").write_text(
        "こんにちは。\n", encoding="utf-8")


def add_jobs_created(dirs, sid=SID):
    add_cleaned(dirs, sid)
    write_json(dirs["JOB_RESULTS"] / f"{sid}.job_builder_result.json",
               job_result_artifact(sid))
    write_json(dirs["JOBS"] / sid / "job_000001.json", job_artifact(sid))


def add_requests_created(dirs, sid=SID):
    add_jobs_created(dirs, sid)
    write_json(dirs["REQUEST_RESULTS"] / f"{sid}.request_builder_result.json",
               request_result_artifact(sid))
    write_json(dirs["REQUESTS"] / sid / "request_000001.json",
               request_artifact(sid))


def add_api_complete(dirs, sid=SID):
    add_requests_created(dirs, sid)
    write_json(dirs["RESPONSES"] / sid / "response_000001.json",
               response_artifact(sid))
    write_json(dirs["PROCESSING_RESULTS"] / f"{sid}.processing_result.json",
               processing_result_artifact(sid))


def add_corpus_available(dirs, sid=SID):
    add_api_complete(dirs, sid)
    write_json(dirs["CORPUS_RESULTS"] / f"{sid}.corpus_builder_result.json",
               corpus_result_artifact(sid))
    (dirs["JSONL"] / f"{sid}.jsonl").write_text(
        '{"text": "こんにちは。"}\n', encoding="utf-8")


# ============================================================
# Scripted subprocess
# ============================================================

class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class StageScript:
    """Materializes a stage's artifacts as if the real stage succeeded."""

    def __init__(self, dirs):
        self.dirs = dirs

    def clean(self, source_id):
        write_json(self.dirs["CLEANING_RESULTS"] / f"{source_id}.cleaning_result.json",
                   cleaning_result_artifact(source_id))
        (self.dirs["CLEANED_ARCHIVE"] / f"{source_id}.clean.txt").write_text(
            "こんにちは。\n", encoding="utf-8")
        return FakeCompletedProcess(returncode=0, stdout="cleaned")

    def jobs(self, source_id):
        write_json(self.dirs["JOB_RESULTS"] / f"{source_id}.job_builder_result.json",
                   job_result_artifact(source_id))
        write_json(self.dirs["JOBS"] / source_id / "job_000001.json",
                   job_artifact(source_id))
        return FakeCompletedProcess(returncode=0, stdout="jobs")

    def requests(self, source_id):
        write_json(self.dirs["REQUEST_RESULTS"] / f"{source_id}.request_builder_result.json",
                   request_result_artifact(source_id))
        write_json(self.dirs["REQUESTS"] / source_id / "request_000001.json",
                   request_artifact(source_id))
        return FakeCompletedProcess(returncode=0, stdout="requests")

    def api(self, source_id):
        write_json(self.dirs["RESPONSES"] / source_id / "response_000001.json",
                   response_artifact(source_id))
        write_json(self.dirs["PROCESSING_RESULTS"] / f"{source_id}.processing_result.json",
                   processing_result_artifact(source_id))
        return FakeCompletedProcess(returncode=0, stdout="api")

    def corpus(self, source_id):
        write_json(self.dirs["CORPUS_RESULTS"] / f"{source_id}.corpus_builder_result.json",
                   corpus_result_artifact(source_id))
        (self.dirs["JSONL"] / f"{source_id}.jsonl").write_text(
            '{"text": "こんにちは。"}\n', encoding="utf-8")
        return FakeCompletedProcess(returncode=0, stdout="corpus")


class ScriptedRun:
    """subprocess.run mock dispatching by script filename."""

    SCRIPT_TO_STAGE = {
        "clean_transcript.py": "clean",
        "job builder.py": "jobs",
        "request builder.py": "requests",
        "deepseek_client.py": "api",
        "corpus_builder.py": "corpus",
    }

    # When a stage is set to fail, write its failure result artifact so the
    # state engine correctly reports the failed stage.
    FAILURE_RESULT = {
        "clean": ("CLEANING_RESULTS", ".cleaning_result.json",
                  cleaning_result_artifact),
        "jobs": ("JOB_RESULTS", ".job_builder_result.json",
                 job_result_artifact),
        "requests": ("REQUEST_RESULTS", ".request_builder_result.json",
                     request_result_artifact),
        "api": ("PROCESSING_RESULTS", ".processing_result.json",
                lambda sid, success=False: processing_result_artifact(
                    sid, statuses=("failed",))),
        "corpus": ("CORPUS_RESULTS", ".corpus_builder_result.json",
                   corpus_result_artifact),
    }

    def __init__(self, script):
        self.script = script
        self.calls = []
        self.fail_on = None  # stage name to make fail

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

        if stage == self.fail_on:
            folder_name, suffix, builder = self.FAILURE_RESULT[stage]
            folder = self.script.dirs[folder_name]
            artifact = builder(source_id, success=False)
            write_json(folder / f"{source_id}{suffix}", artifact)
            return FakeCompletedProcess(returncode=5, stderr="boom")

        method = getattr(self.script, stage, None)
        if method is None:
            return FakeCompletedProcess(returncode=1, stderr="no handler")
        return method(source_id)


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


def launched_names(scripted):
    return [pathlib.Path(c[1]).name for c in scripted.calls]


@test("1. full pipeline state progression (registered -> corpus_available)")
def _():
    root, dirs, saved = setup()
    try:
        add_waiting_for_clean(dirs)
        stage_script = StageScript(dirs)
        scripted = ScriptedRun(stage_script)
        real_run = pm.subprocess.run
        pm.subprocess.run = scripted

        code = pm.run_pipeline(SID, auto=True)
        check("exit 0", code == 0)
        check("five stages launched",
              launched_names(scripted)
              == ["clean_transcript.py", "job builder.py",
                  "request builder.py", "deepseek_client.py",
                  "corpus_builder.py"])
        check("state is corpus_available",
              pm.state_for(SID)["state"] == "corpus_available")

        # Verify real artifact readers see a complete chain.
        ev = pm.collect_evidence(SID)
        check("cleaning result", ev["cleaning_success"] is True)
        check("job result", ev["job_builder_success"] is True)
        check("request result", ev["request_builder_success"] is True)
        check("processing result", ev["processing_result_exists"] is True)
        check("corpus result", ev["corpus_success"] is True)
        check("jsonl", ev["jsonl_nonempty"] is True)
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("2. guided pause/resume behavior")
def _():
    root, dirs, saved = setup()
    try:
        add_waiting_for_clean(dirs)
        stage_script = StageScript(dirs)
        scripted = ScriptedRun(stage_script)
        real_run = pm.subprocess.run
        pm.subprocess.run = scripted

        confirmations = ["n"]  # pause before jobs (only clean ran)
        code = pm.run_pipeline(SID, auto=False,
                               confirm_fn=lambda _p: confirmations.pop(0))
        check("exit 2 (paused)", code == 2)
        check("paused after clean",
              launched_names(scripted) == ["clean_transcript.py"])
        check("state is cleaned", pm.state_for(SID)["state"] == "cleaned")

        # Resume: continue from cleaned with confirmation for each stage.
        confirmations = ["y", "y", "y", "y"]
        code = pm.run_pipeline(SID, auto=False,
                               confirm_fn=lambda _p: confirmations.pop(0))
        check("resume exit 0", code == 0)
        check("resume launched remaining four",
              launched_names(scripted)
              == ["clean_transcript.py", "job builder.py",
                  "request builder.py", "deepseek_client.py",
                  "corpus_builder.py"])
        check("state is corpus_available",
              pm.state_for(SID)["state"] == "corpus_available")
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("3. auto pipeline completion")
def _():
    root, dirs, saved = setup()
    try:
        add_waiting_for_clean(dirs)
        stage_script = StageScript(dirs)
        scripted = ScriptedRun(stage_script)
        real_run = pm.subprocess.run
        pm.subprocess.run = scripted

        # No confirmations allowed in auto mode.
        confirm_fn = lambda _p: (_ for _ in ()).throw(
            AssertionError("no confirmations expected"))
        code = pm.run_pipeline(SID, auto=True, confirm_fn=confirm_fn)
        check("exit 0", code == 0)
        check("all five launched", len(scripted.calls) == 5)
        check("corpus_available", pm.state_for(SID)["state"] == "corpus_available")
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("4. resume from api_processing")
def _():
    root, dirs, saved = setup()
    try:
        add_api_complete(dirs)   # requests + response + processing result
        stage_script = StageScript(dirs)
        scripted = ScriptedRun(stage_script)
        real_run = pm.subprocess.run
        pm.subprocess.run = scripted

        code = pm.run_pipeline(SID, auto=True)
        check("exit 0", code == 0)
        check("only corpus launched",
              launched_names(scripted) == ["corpus_builder.py"])
        check("corpus_available", pm.state_for(SID)["state"] == "corpus_available")
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("5. failure stops pipeline")
def _():
    root, dirs, saved = setup()
    try:
        add_waiting_for_clean(dirs)
        stage_script = StageScript(dirs)
        scripted = ScriptedRun(stage_script)
        scripted.fail_on = "jobs"
        real_run = pm.subprocess.run
        pm.subprocess.run = scripted

        code = pm.run_pipeline(SID, auto=True)
        check("exit 1", code == 1)
        check("stopped after jobs failure",
              launched_names(scripted)
              == ["clean_transcript.py", "job builder.py"])
        check("state is failed", pm.state_for(SID)["state"] == "failed")
        check("failed stage is jobs", pm.state_for(SID)["failed_stage"] == "jobs")
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("6. corpus_available skips execution")
def _():
    root, dirs, saved = setup()
    try:
        add_corpus_available(dirs)
        real_run = pm.subprocess.run
        calls = []
        pm.subprocess.run = lambda command, **kw: calls.append(command) \
            or FakeCompletedProcess(returncode=0)
        code = pm.run_pipeline(SID, auto=True)
        check("exit 0", code == 0)
        check("no launches", len(calls) == 0)
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("7. no forbidden artifact writes")
def _():
    import paths as project_paths

    root, dirs, saved = setup()
    try:
        add_waiting_for_clean(dirs)
        stage_script = StageScript(dirs)
        scripted = ScriptedRun(stage_script)
        real_run = pm.subprocess.run
        pm.subprocess.run = scripted

        forbidden = (project_paths.SOURCE_REGISTRY,
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
        before = {p: sorted(x.name for x in p.iterdir()) for p in forbidden}

        code = pm.run_pipeline(SID, auto=True)
        check("exit 0", code == 0)

        after = {p: sorted(x.name for x in p.iterdir()) for p in forbidden}
        for folder in forbidden:
            check(f"no write to {folder.name}", after[folder] == before[folder])
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("8. deterministic decisions from identical artifact trees")
def _():
    root, dirs, saved = setup()
    try:
        add_cleaned(dirs)   # start state is deterministic across runs
        stage_script = StageScript(dirs)
        real_run = pm.subprocess.run
        pm.subprocess.run = ScriptedRun(stage_script)

        sequences = []
        for _ in range(2):
            pm.subprocess.run = ScriptedRun(stage_script)
            code = pm.run_pipeline(SID, auto=True)
            check("exit 0", code == 0)
            sequences.append(pm.state_for(SID)["state"])
        check("same terminal state", sequences[0] == sequences[1]
              == "corpus_available")
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("9. manager writes only its own logs")
def _():
    root, dirs, saved = setup()
    try:
        add_waiting_for_clean(dirs)
        stage_script = StageScript(dirs)
        scripted = ScriptedRun(stage_script)
        real_run = pm.subprocess.run
        pm.subprocess.run = scripted

        # The real project dirs must be unchanged (compare before/after).
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
        before = {f: sorted(x.name for x in f.iterdir()) for f in real}

        code = pm.run_pipeline(SID, auto=True)
        check("exit 0", code == 0)

        manager_dir = dirs["LOG_PRODUCTION_MANAGER"]
        check("manager log exists",
              (manager_dir / "manager.log").is_file())

        after = {f: sorted(x.name for x in f.iterdir()) for f in real}
        for folder in real:
            check(f"no change in real {folder.name}",
                  after[folder] == before[folder])
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
