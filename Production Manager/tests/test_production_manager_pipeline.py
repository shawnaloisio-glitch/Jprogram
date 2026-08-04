#!/usr/bin/env python3
"""
test_production_manager_pipeline.py

Deterministic tests for the Production Manager pipeline orchestration
(M1-4 guided/auto modes).

Uses sandboxed artifact trees and a scripted subprocess mock that
materializes each stage's expected result artifact. No real stage is run
and no real pipeline artifact is written.

Run:
    python "Production Manager/tests/test_production_manager_pipeline.py"
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


def add_registry(dirs, sid=SID):
    write_json(dirs["SOURCE_REGISTRY"] / f"{sid}.json", {
        "schema_version": "1",
        "source_id": sid,
        "original_filename": "con.txt",
        "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        "source_type": "podcast_transcript",
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
        "source_type": "podcast_transcript",
        "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": "1.0",
        "output_path": f"Cleaned Archive/{sid}.clean.txt",
    })


def add_cleaning_result(dirs, sid=SID):
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


class ScriptedRun:
    """
    Scripted subprocess.run mock.

    Each stage maps to a callback that materializes the stage's result
    artifact (as if the stage had succeeded), or returns a failure.
    Stage detection uses the script filename in argv[1].
    """

    SCRIPT_TO_STAGE = {
        "clean_subtitles.py": "clean",
        "clean_transcript.py": "clean",
        "job builder.py": "jobs",
        "request builder.py": "requests",
        "deepseek_client.py": "api",
        "corpus_builder.py": "corpus",
    }

    def __init__(self, effects):
        self.effects = effects
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append(command)
        script = pathlib.Path(command[1]).name
        stage = self.SCRIPT_TO_STAGE.get(script)
        source_id = None
        if "--source" in command:
            source_id = command[command.index("--source") + 1]
        elif "--job" in command:
            job_path = command[command.index("--job") + 1]
            source_id = pathlib.Path(job_path).stem.replace(
                ".cleaning_job", "")
        effect = self.effects.get(stage)
        if effect is None:
            return FakeCompletedProcess(returncode=1, stderr="no effect")
        return effect(source_id)


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def succeed_stage(materialize):
    def run(source_id):
        materialize(PM_DIRS, source_id)
        return FakeCompletedProcess(returncode=0, stdout="ok")
    return run


def fail_stage(source_id=None):
    return FakeCompletedProcess(returncode=5, stderr="boom")


PM_DIRS = None


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("1. guided pipeline registered -> corpus_available, pauses at each stage")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)

        real_run = pm.subprocess.run
        effects = {
            "clean": succeed_stage(add_cleaning_result),
            "jobs": succeed_stage(add_job_result),
            "requests": succeed_stage(add_request_result),
            "api": succeed_stage(add_processing_result),
            "corpus": succeed_stage(add_corpus_result),
        }
        scripted = ScriptedRun(effects)
        pm.subprocess.run = scripted

        confirmations = ["y", "y", "y", "y"]
        code = pm.run_pipeline(SID, auto=False,
                               confirm_fn=lambda _p: confirmations.pop(0))
        check("exit 0", code == 0)
        check("all five stages launched",
              [pathlib.Path(c[1]).name for c in scripted.calls]
              == ["clean_transcript.py", "job builder.py",
                  "request builder.py", "deepseek_client.py",
                  "corpus_builder.py"])
        check("four confirmations", len(confirmations) == 0)
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("1b. auto pipeline runs without confirmations")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)

        real_run = pm.subprocess.run
        effects = {
            "clean": succeed_stage(add_cleaning_result),
            "jobs": succeed_stage(add_job_result),
            "requests": succeed_stage(add_request_result),
            "api": succeed_stage(add_processing_result),
            "corpus": succeed_stage(add_corpus_result),
        }
        scripted = ScriptedRun(effects)
        pm.subprocess.run = scripted

        confirm_fn = lambda _p: (_ for _ in ()).throw(
            AssertionError("no confirmations expected in auto mode"))
        code = pm.run_pipeline(SID, auto=True, confirm_fn=confirm_fn)
        check("exit 0", code == 0)
        check("all five stages launched", len(scripted.calls) == 5)
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("2. pipeline resumes from each intermediate state")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        add_cleaning_result(dirs)   # start at cleaned

        real_run = pm.subprocess.run
        effects = {
            "jobs": succeed_stage(add_job_result),
            "requests": succeed_stage(add_request_result),
            "api": succeed_stage(add_processing_result),
            "corpus": succeed_stage(add_corpus_result),
        }
        scripted = ScriptedRun(effects)
        pm.subprocess.run = scripted

        code = pm.run_pipeline(SID, auto=True)
        check("exit 0", code == 0)
        check("resumes from jobs",
              [pathlib.Path(c[1]).name for c in scripted.calls]
              == ["job builder.py", "request builder.py",
                  "deepseek_client.py", "corpus_builder.py"])
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("3. failed stage stops pipeline")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)

        real_run = pm.subprocess.run
        effects = {
            "clean": succeed_stage(add_cleaning_result),
            "jobs": fail_stage,
            "requests": succeed_stage(add_request_result),
            "api": succeed_stage(add_processing_result),
            "corpus": succeed_stage(add_corpus_result),
        }
        scripted = ScriptedRun(effects)
        pm.subprocess.run = scripted

        code = pm.run_pipeline(SID, auto=True)
        check("exit non-zero", code == 1)
        check("stopped after jobs failure", len(scripted.calls) == 2)
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("4. completed corpus does not rerun")
def _():
    root, dirs, saved = setup()
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        add_cleaning_result(dirs)
        add_job_result(dirs)
        add_request_result(dirs)
        add_processing_result(dirs)
        add_corpus_result(dirs)   # fully complete

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


@test("5. partial API resumes correctly")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        add_cleaning_result(dirs)
        add_job_result(dirs)
        add_request_result(dirs)
        add_processing_result(dirs)   # api already complete

        real_run = pm.subprocess.run
        effects = {"corpus": succeed_stage(add_corpus_result)}
        scripted = ScriptedRun(effects)
        pm.subprocess.run = scripted

        code = pm.run_pipeline(SID, auto=True)
        check("exit 0", code == 0)
        check("only corpus launched",
              [pathlib.Path(c[1]).name for c in scripted.calls]
              == ["corpus_builder.py"])
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("6. guided mode pauses when user declines")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)

        real_run = pm.subprocess.run
        effects = {"clean": succeed_stage(add_cleaning_result)}
        scripted = ScriptedRun(effects)
        pm.subprocess.run = scripted

        confirm_fn = lambda _p: "n"
        code = pm.run_pipeline(SID, auto=False, confirm_fn=confirm_fn)
        check("exit 2 (paused)", code == 2)
        check("only clean launched", len(scripted.calls) == 1)
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("7. intake boundary stops (unregistered)")
def _():
    root, dirs, saved = setup()
    try:
        code = pm.run_pipeline("pod_unknown_ep999", auto=True)
        check("exit 1", code == 1)
    finally:
        restore(saved)


@test("8. no forbidden pipeline writes")
def _():
    import paths as project_paths

    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)

        real_run = pm.subprocess.run
        effects = {
            "clean": succeed_stage(add_cleaning_result),
            "jobs": succeed_stage(add_job_result),
            "requests": succeed_stage(add_request_result),
            "api": succeed_stage(add_processing_result),
            "corpus": succeed_stage(add_corpus_result),
        }
        pm.subprocess.run = ScriptedRun(effects)

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


@test("9. no stage imports in pipeline code")
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


@test("10. deterministic decisions from same artifacts")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        add_cleaning_result(dirs)   # start at cleaned

        real_run = pm.subprocess.run
        effects = {
            "jobs": succeed_stage(add_job_result),
            "requests": succeed_stage(add_request_result),
            "api": succeed_stage(add_processing_result),
            "corpus": succeed_stage(add_corpus_result),
        }

        sequences = []
        for _ in range(2):
            # Reset to the same starting state (safe deletion helpers).
            for folder in (dirs["JOBS"], dirs["REQUESTS"], dirs["RESPONSES"]):
                for child in list(folder.iterdir()):
                    if child.is_dir():
                        import shutil
                        shutil.rmtree(child)
                    else:
                        child.unlink()
            for path in (
                dirs["JOB_RESULTS"] / f"{SID}.job_builder_result.json",
                dirs["REQUEST_RESULTS"] / f"{SID}.request_builder_result.json",
                dirs["PROCESSING_RESULTS"] / f"{SID}.processing_result.json",
                dirs["CORPUS_RESULTS"] / f"{SID}.corpus_builder_result.json",
                dirs["JSONL"] / f"{SID}.jsonl",
            ):
                if path.exists():
                    path.unlink()

            scripted = ScriptedRun(effects)
            pm.subprocess.run = scripted
            code = pm.run_pipeline(SID, auto=True)
            check("exit 0", code == 0)
            sequences.append([pathlib.Path(c[1]).name for c in scripted.calls])

        check("identical stage sequences", sequences[0] == sequences[1])
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("11. no-progress guard stops")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)

        real_run = pm.subprocess.run
        # clean "succeeds" but produces no state change (no materialization).
        effects = {
            "clean": succeed_stage(lambda d, s: None),
            "jobs": succeed_stage(add_job_result),
        }
        scripted = ScriptedRun(effects)
        pm.subprocess.run = scripted

        code = pm.run_pipeline(SID, auto=True)
        check("exit 1 (no progress)", code == 1)
        check("stopped after clean", len(scripted.calls) == 1)
        pm.subprocess.run = real_run
    finally:
        restore(saved)


@test("12. corrupted artifacts do not crash the pipeline")
def _():
    global PM_DIRS
    root, dirs, saved = setup()
    PM_DIRS = dirs
    try:
        add_registry(dirs)
        add_cleaning_job(dirs)
        # Corrupt cleaning result: treated as absent -> still waiting_for_clean.
        path = dirs["CLEANING_RESULTS"] / f"{SID}.cleaning_result.json"
        path.write_text("{ not valid", encoding="utf-8")

        real_run = pm.subprocess.run
        effects = {
            "clean": succeed_stage(add_cleaning_result),
            "jobs": succeed_stage(add_job_result),
            "requests": succeed_stage(add_request_result),
            "api": succeed_stage(add_processing_result),
            "corpus": succeed_stage(add_corpus_result),
        }
        scripted = ScriptedRun(effects)
        pm.subprocess.run = scripted

        code = pm.run_pipeline(SID, auto=True)
        check("exit 0", code == 0)
        check("clean relaunched after corrupt result", len(scripted.calls) == 5)
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
