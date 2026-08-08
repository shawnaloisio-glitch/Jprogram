#!/usr/bin/env python3
"""
test_diagnostics.py

Deterministic tests for the Source Builder diagnostics bundle:

- _read_text handles missing/undecodable files and utf-8-sig text,
- _read_json parses JSON and falls back to raw text on bad JSON,
- _artifact_paths and _log_paths return the expected key sets,
- collect_source_bundle includes only artifacts that exist on disk
  (missing ones are omitted, never an error),
- write_dump writes a gzip file that round-trips and matches the
  processing_dump_<label>_<ts>.json.gz filename pattern.

Workspace paths are redirected to a sandboxed directory; real workspace
data is never touched.

Run:
    python "Source Builder/tests/test_diagnostics.py"
"""

import gzip
import json
import pathlib
import re
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))
sys.path.insert(0, str(PROJECT_ROOT))

import diagnostics
import paths
import production_manager as pm


def patch_workspace_paths():
    """
    Point pm + paths directory constants at a fresh sandbox tree.

    Returns (tmp, restore). production_manager binds the workspace
    constants at import time, so both copies must be patched for
    diagnostics to see the sandbox.
    """
    tmp = pathlib.Path(tempfile.mkdtemp())

    pm_folders = {
        "SOURCE_REGISTRY": "Source Registry",
        "CLEANING_JOBS": "Cleaning Jobs",
        "CLEANING_RESULTS": "Cleaning Results",
        "CLEANED_ARCHIVE": "Cleaned Archive",
        "JOB_RESULTS": "Job Results",
        "REQUEST_RESULTS": "Request Results",
        "PROCESSING_RESULTS": "Processing Results",
        "CORPUS_RESULTS": "Corpus Results",
        "JSONL": "jsonl",
        "JOBS": "jobs",
        "REQUESTS": "requests",
        "RESPONSES": "responses",
    }
    log_folders = {
        "LOG_TRANSCRIPT_CLEANER": ("Logs", "Transcript Cleaner"),
        "LOG_SUBTITLE_CLEANER": ("Logs", "Subtitle Cleaner"),
        "LOG_JOB_BUILDER": ("Logs", "Job Builder"),
        "LOG_REQUEST_BUILDER": ("Logs", "Request Builder"),
        "LOG_DEEPSEEK_CLIENT": ("Logs", "DeepSeek Client"),
        "LOG_CORPUS_BUILDER": ("Logs", "Corpus Builder"),
        "LOG_PRODUCTION_MANAGER": ("Logs", "Production Manager"),
    }

    saved_pm = {}
    for name, sub in pm_folders.items():
        saved_pm[name] = getattr(pm, name)
        setattr(pm, name, tmp / sub)

    saved_paths = {}
    for name, sub in log_folders.items():
        saved_paths[name] = getattr(paths, name)
        setattr(paths, name, tmp.joinpath(*sub))

    def restore():
        for name, value in saved_pm.items():
            setattr(pm, name, value)
        for name, value in saved_paths.items():
            setattr(paths, name, value)

    return tmp, restore


def patch_diagnostics_dir():
    """Point diagnostics.DIAGNOSTICS_DIR at a sandbox dir; return (tmp, restore)."""
    saved = diagnostics.DIAGNOSTICS_DIR
    tmp = pathlib.Path(tempfile.mkdtemp()) / "Diagnostics"
    diagnostics.DIAGNOSTICS_DIR = tmp

    def restore():
        diagnostics.DIAGNOSTICS_DIR = saved

    return tmp, restore


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("_read_text: missing and undecodable files return None")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    check("missing returns None",
          diagnostics._read_text(tmp / "nope.txt") is None)
    bad = tmp / "bad.bin"
    bad.write_bytes(b"\xff\xfe\xfa\x01")
    check("undecodable returns None",
          diagnostics._read_text(bad) is None)


@test("_read_text: utf-8-sig file returns decoded text")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    plain = tmp / "plain.txt"
    plain.write_text("hello\n", encoding="utf-8")
    check("plain text", diagnostics._read_text(plain) == "hello\n")

    bom = tmp / "bom.txt"
    bom.write_text("﻿こんにちは\n", encoding="utf-8")
    check("BOM stripped", diagnostics._read_text(bom) == "こんにちは\n")


@test("_read_json: valid json parses")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    path = tmp / "data.json"
    path.write_text(json.dumps({"ok": True, "items": [1, 2]}), encoding="utf-8")
    value = diagnostics._read_json(path)
    check("parsed dict", value == {"ok": True, "items": [1, 2]})
    check("is dict", isinstance(value, dict))


@test("_read_json: invalid json falls back to raw text")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    path = tmp / "data.json"
    raw = "not json at all {"
    path.write_text(raw, encoding="utf-8")
    check("raw fallback", diagnostics._read_json(path) == raw)


@test("_read_json: missing file returns None")
def _():
    check("missing returns None",
          diagnostics._read_json(pathlib.Path(tempfile.mkdtemp()) / "nope.json") is None)


@test("_artifact_paths: returns dict with expected keys")
def _():
    artifact_keys = {
        "registry", "cleaning_job", "cleaning_result", "cleaned_artifact",
        "job_builder_result", "request_builder_result", "processing_result",
        "corpus_result", "jsonl",
    }
    result = diagnostics._artifact_paths("src_1")
    check("key set", set(result) == artifact_keys)
    check("values are paths",
          all(isinstance(p, pathlib.Path) for p in result.values()))


@test("_log_paths: returns dict with expected keys")
def _():
    log_keys = {
        "cleaner", "subtitle_cleaner", "job_builder", "request_builder",
        "deepseek", "corpus_builder", "production_manager",
    }
    result = diagnostics._log_paths("src_1")
    check("key set", set(result) == log_keys)
    check("values are paths",
          all(isinstance(p, pathlib.Path) for p in result.values()))


@test("collect_source_bundle: existing artifacts included, missing omitted")
def _():
    tmp, restore = patch_workspace_paths()
    try:
        source_id = "src_1"

        # Existing artifacts: two JSON + one plain-text.
        registry = tmp / "Source Registry" / f"{source_id}.json"
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_text(
            json.dumps({"source_id": source_id, "status": "registered"}),
            encoding="utf-8")

        cleaning_job = tmp / "Cleaning Jobs" / f"{source_id}.cleaning_job.json"
        cleaning_job.parent.mkdir(parents=True, exist_ok=True)
        cleaning_job.write_text(
            json.dumps({"job": "clean", "done": True}), encoding="utf-8")

        cleaned = tmp / "Cleaned Archive" / f"{source_id}.clean.txt"
        cleaned.parent.mkdir(parents=True, exist_ok=True)
        cleaned.write_text("cleaned content", encoding="utf-8")

        # A log file in one of the log folders.
        log = tmp / "Logs" / "Job Builder" / f"{source_id}.job_builder.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("job builder log line", encoding="utf-8")

        # A job file in the jobs subfolder.
        job_file = tmp / "jobs" / source_id / "job_0001.json"
        job_file.parent.mkdir(parents=True, exist_ok=True)
        job_file.write_text(json.dumps({"job_id": 1}), encoding="utf-8")

        bundle = diagnostics.collect_source_bundle(source_id)

        check("source_id", bundle["source_id"] == source_id)
        check("identity source_id", bundle["identity"]["source_id"] == source_id)
        check("report is dict", isinstance(bundle["report"], dict))

        artifacts = bundle["artifacts"]
        check("registry included",
              artifacts.get("registry") == {"source_id": source_id,
                                            "status": "registered"})
        check("cleaning_job included",
              artifacts.get("cleaning_job") == {"job": "clean", "done": True})
        check("cleaned_artifact included",
              artifacts.get("cleaned_artifact") == "cleaned content")
        for missing in ("cleaning_result", "job_builder_result",
                        "request_builder_result", "processing_result",
                        "corpus_result", "jsonl"):
            check(f"missing {missing} omitted", missing not in artifacts)

        check("jobs collected",
              bundle["jobs"] == {"job_0001.json": {"job_id": 1}})
        check("requests empty", bundle["requests"] == {})
        check("responses empty", bundle["responses"] == {})

        logs = bundle["logs"]
        check("job_builder log included",
              logs.get("job_builder") == "job builder log line")
        check("missing cleaner log omitted", "cleaner" not in logs)
        check("missing deepseek log omitted", "deepseek" not in logs)
    finally:
        restore()


@test("collect_source_bundle: package populates identity")
def _():
    tmp, restore = patch_workspace_paths()
    try:
        bundle = diagnostics.collect_source_bundle(
            "src_2",
            package={"source_id": "src_2", "collection_id": "col_x",
                     "episode": 3, "source_name": "Some Show"})
        identity = bundle["identity"]
        check("collection_id", identity["collection_id"] == "col_x")
        check("episode", identity["episode"] == 3)
        check("source_name", identity["source_name"] == "Some Show")
        check("report is dict", isinstance(bundle["report"], dict))
    finally:
        restore()


@test("write_dump: gzip round-trip and filename pattern")
def _():
    tmp, restore = patch_diagnostics_dir()
    try:
        dump = {"source_id": "src_1", "nested": {"a": [1, 2, 3]},
                "label": "テスト"}
        target = diagnostics.write_dump(dump, label="test_run")

        check("target is file", target.is_file())
        pattern = (r"^processing_dump_test_run_"
                   r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.json\.gz$")
        check("filename pattern", re.match(pattern, target.name) is not None)

        with gzip.open(target, "rt", encoding="utf-8") as file:
            loaded = json.load(file)
        check("round-trip", loaded == dump)
    finally:
        restore()


@test("write_dump: label sanitized in filename")
def _():
    tmp, restore = patch_diagnostics_dir()
    try:
        target = diagnostics.write_dump({"a": 1}, label="My Test!")
        check("sanitized name", "My Test!" not in target.name)
        check("no spaces", " " not in target.name)
        check("still json.gz", target.name.endswith(".json.gz"))
    finally:
        restore()


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
