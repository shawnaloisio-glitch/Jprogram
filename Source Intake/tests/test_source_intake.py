#!/usr/bin/env python3
"""
test_source_intake.py

Deterministic tests for source_intake.py (coordinator).

Run:
    python "Source Intake/tests/test_source_intake.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_INTAKE = PROJECT_ROOT / "Source Intake"
sys.path.insert(0, str(SOURCE_INTAKE))

import resolver
import schemas
import source_intake as si


def fixture():
    """Set up temp raw/registry/jobs/logs dirs and patch module globals."""
    root = pathlib.Path(tempfile.mkdtemp())
    raw_dir = root / "raw"
    registry_dir = root / "registry"
    jobs_dir = root / "jobs"
    logs_dir = root / "logs"
    raw_dir.mkdir()
    registry_dir.mkdir()
    jobs_dir.mkdir()
    logs_dir.mkdir()

    saved = (
        si.SOURCE_REGISTRY,
        si.CLEANING_JOBS,
        si.LOG_SOURCE_INTAKE,
        resolver.SOURCE_TYPE_RAW_DIR,
    )
    si.SOURCE_REGISTRY = registry_dir
    si.CLEANING_JOBS = jobs_dir
    si.LOG_SOURCE_INTAKE = logs_dir
    resolver.SOURCE_TYPE_RAW_DIR = {"clean_text": str(raw_dir)}
    return root, raw_dir, registry_dir, jobs_dir, saved


def restore(saved):
    (si.SOURCE_REGISTRY, si.CLEANING_JOBS,
     si.LOG_SOURCE_INTAKE, resolver.SOURCE_TYPE_RAW_DIR) = saved


def make_raw(raw_dir, name, content):
    path = raw_dir / name
    path.write_bytes(content)
    return path


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("full registration creates valid artifacts")
def _():
    root, raw, reg, jobs, saved = fixture()
    try:
        raw_file = make_raw(raw, "con.txt", b"podcast content")
        result = si.register_source(str(raw_file), "clean_text",
                                    "ja", "Con Teppei", "ep051")
        sid = "clean_text_con-teppei_ep051"
        check("action", result["action"] == "registered")
        check("source_id", result["source_id"] == sid)
        reg_file = reg / f"{sid}.json"
        job_file = jobs / f"{sid}.cleaning_job.json"
        check("registry created", reg_file.is_file())
        check("job created", job_file.is_file())
        entry = json.loads(reg_file.read_text(encoding="utf-8"))
        job = json.loads(job_file.read_text(encoding="utf-8"))
        check("registry valid", schemas.validate("registry", entry) == [])
        check("job valid", schemas.validate("cleaning_job", job) == [])
        check("job raw_path correct",
              job["raw_path"] == str(raw_file.resolve()))
    finally:
        restore(saved)


@test("duplicate: same hash, different source_id, no new artifacts")
def _():
    root, raw, reg, jobs, saved = fixture()
    try:
        raw_file = make_raw(raw, "a.txt", b"same content")
        si.register_source(str(raw_file), "clean_text", "ja", "Alpha", "ep001")
        before_reg = sorted(p.name for p in reg.iterdir())
        before_jobs = sorted(p.name for p in jobs.iterdir())
        raw_file2 = make_raw(raw, "b.txt", b"same content")
        result = si.register_source(str(raw_file2), "clean_text", "ja", "Beta", "ep001")
        check("action duplicate", result["action"] == "duplicate")
        check("duplicate id reported", result["duplicate_source_id"]
              == "clean_text_alpha_ep001")
        check("registry unchanged", sorted(p.name for p in reg.iterdir()) == before_reg)
        check("jobs unchanged", sorted(p.name for p in jobs.iterdir()) == before_jobs)
    finally:
        restore(saved)


@test("already complete: registry and job exist, no writes")
def _():
    root, raw, reg, jobs, saved = fixture()
    try:
        raw_file = make_raw(raw, "con.txt", b"content")
        si.register_source(str(raw_file), "clean_text", "ja", "Con Teppei", "ep051")
        sid = "clean_text_con-teppei_ep051"
        reg_snapshot = (reg / f"{sid}.json").read_bytes()
        job_snapshot = (jobs / f"{sid}.cleaning_job.json").read_bytes()
        result = si.register_source(str(raw_file), "clean_text", "ja", "Con Teppei", "ep051")
        check("action already_complete", result["action"] == "already_complete")
        check("registry unchanged", (reg / f"{sid}.json").read_bytes() == reg_snapshot)
        check("job unchanged", (jobs / f"{sid}.cleaning_job.json").read_bytes() == job_snapshot)
    finally:
        restore(saved)


@test("resume: registry exists, job missing -> only job created")
def _():
    root, raw, reg, jobs, saved = fixture()
    try:
        raw_file = make_raw(raw, "con.txt", b"content")
        si.register_source(str(raw_file), "clean_text", "ja", "Con Teppei", "ep051")
        sid = "clean_text_con-teppei_ep051"
        reg_snapshot = (reg / f"{sid}.json").read_bytes()
        (jobs / f"{sid}.cleaning_job.json").unlink()
        result = si.register_source(str(raw_file), "clean_text", "ja", "Con Teppei", "ep051")
        check("action resumed", result["action"] == "resumed")
        check("registry unchanged", (reg / f"{sid}.json").read_bytes() == reg_snapshot)
        job_file = jobs / f"{sid}.cleaning_job.json"
        check("job recreated", job_file.is_file())
        check("job valid", schemas.validate(
            "cleaning_job", json.loads(job_file.read_text(encoding="utf-8"))) == [])
    finally:
        restore(saved)


@test("invalid metadata rejected")
def _():
    root, raw, reg, jobs, saved = fixture()
    try:
        raw_file = make_raw(raw, "con.txt", b"content")
        cases = [
            ("clean_text", "ja", "", "ep051"),      # empty title
            ("clean_text", "", "Con", "ep051"),     # empty language
            ("mystery", "ja", "Con", "ep051"),              # bad source type
        ]
        for st, lang, title, seq in cases:
            raised = False
            try:
                si.register_source(str(raw_file), st, lang, title, seq)
            except si.SourceIntakeError:
                raised = True
            check(f"rejects ({st},{lang},{title!r})", raised)
        # missing file
        raised = False
        try:
            si.register_source(str(raw / "missing.txt"), "clean_text",
                               "ja", "Con", "ep051")
        except si.SourceIntakeError:
            raised = True
        check("rejects missing file", raised)
        # invalid extension
        bad = make_raw(raw, "video.mp4", b"x")
        raised = False
        try:
            si.register_source(str(bad), "clean_text", "ja", "Con", "ep051")
        except si.SourceIntakeError:
            raised = True
        check("rejects invalid extension", raised)
    finally:
        restore(saved)


@test("determinism: same input produces identical artifacts")
def _():
    # One shared raw location; two independent registry/jobs output dirs,
    # so raw_path is identical and the artifacts must be byte-identical.
    raw_dir = pathlib.Path(tempfile.mkdtemp()) / "raw"
    raw_dir.mkdir()
    raw_file = raw_dir / "con.txt"
    raw_file.write_bytes(b"content")

    artifacts = []
    for _ in range(2):
        root = pathlib.Path(tempfile.mkdtemp())
        reg = root / "registry"
        jobs = root / "jobs"
        logs = root / "logs"
        reg.mkdir()
        jobs.mkdir()
        logs.mkdir()
        saved = (si.SOURCE_REGISTRY, si.CLEANING_JOBS,
                 si.LOG_SOURCE_INTAKE, resolver.SOURCE_TYPE_RAW_DIR)
        si.SOURCE_REGISTRY = reg
        si.CLEANING_JOBS = jobs
        si.LOG_SOURCE_INTAKE = logs
        resolver.SOURCE_TYPE_RAW_DIR = {"clean_text": str(raw_dir)}
        try:
            si.register_source(str(raw_file), "clean_text",
                               "ja", "Con Teppei", "ep051")
            sid = "clean_text_con-teppei_ep051"
            artifacts.append((
                (reg / f"{sid}.json").read_bytes(),
                (jobs / f"{sid}.cleaning_job.json").read_bytes(),
            ))
        finally:
            restore(saved)

    check("registry byte-identical", artifacts[0][0] == artifacts[1][0])
    check("job byte-identical", artifacts[0][1] == artifacts[1][1])


@test("boundary imports: no downstream modules imported")
def _():
    source = pathlib.Path(SOURCE_INTAKE / "source_intake.py").read_text(
        encoding="utf-8")
    forbidden = (
        "import clean_transcript", "from clean_transcript",
        "import clean_subtitles", "from clean_subtitles",
        "corpus_builder", "response_validator", "deepseek_client",
        "import Analysis", "from Analysis", "urllib", "openai",
    )
    for item in forbidden:
        check(f"no {item!r}", item not in source)


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
