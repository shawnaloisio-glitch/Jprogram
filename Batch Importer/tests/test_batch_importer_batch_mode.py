#!/usr/bin/env python3
"""
test_batch_importer_batch_mode.py

Deterministic tests for the Batch Importer's --batch-mode flag
(import_one_inprocess / production_manager.pipeline(launcher=
launch_stage_inprocess)).

Mirrors test_batch_importer.py's end-to-end orchestration tests, but mocks
production_manager.pipeline instead of subprocess.run -- --batch-mode never
calls subprocess.run at all, which several tests here confirm directly.
Real pipeline stage behavior (including the real GiNZA model) is out of
scope here, same as the existing subprocess-path tests.

Run:
    python "Batch Importer/tests/test_batch_importer_batch_mode.py"
"""

import contextlib
import io
import pathlib
import sys
import tempfile
from unittest import mock

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
BATCH_IMPORTER = PROJECT_ROOT / "Batch Importer"
sys.path.insert(0, str(BATCH_IMPORTER))
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Source Builder"))
sys.path.insert(0, str(PROJECT_ROOT / "Source Intake"))
sys.path.insert(0, str(PROJECT_ROOT / "Production Manager"))

import batch_importer
import controller
import handoff
import source_package

# Reuse test_batch_importer.py's exact sandbox helpers so both files patch
# the same module globals the same way.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_batch_importer as base

TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


def run_cli(args, tmp, saved):
    _ = (tmp, saved)
    buf = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        code = batch_importer.main(args)
    return code, buf.getvalue(), err.getvalue()


def success_result():
    return {
        "success": True, "exit_code": 0, "state": "corpus_available",
        "failed_stage": None, "next_stage": None,
        "stages_run": ["clean", "jobs", "requests", "api", "corpus"],
        "exit_codes": {}, "boundary": None, "events": [],
    }


def failure_result(failed_stage, error_message):
    return {
        "success": False, "exit_code": 1, "state": "failed",
        "failed_stage": failed_stage, "next_stage": failed_stage,
        "stages_run": ["clean"], "exit_codes": {},
        "boundary": f"failed:{failed_stage}",
        "events": [{"stage": failed_stage, "error": error_message}],
    }


@test("--batch-mode imports a file end-to-end via production_manager.pipeline, "
      "never touching subprocess.run")
def _():
    tmp, saved = base.setup()
    try:
        input_dir = tmp / "Beginner"
        input_dir.mkdir()
        (input_dir / "A id00001.html").write_text(
            "<p>こんにちは。</p>", encoding="utf-8")

        with mock.patch("batch_importer.production_manager.pipeline",
                        return_value=success_result()) as pipeline, \
             mock.patch("batch_importer.subprocess.run") as run:
            code, out, _err = run_cli(
                ["--folder", str(input_dir), "--creator", "test_creator",
                 "--batch-mode"],
                tmp, saved)

        check("exit 0", code == 0)
        check("imported line", "[IMPORTED] A id00001.html" in out)
        check("summary imported 1", "imported: 1" in out)
        check("canonical created", (controller.SOURCES_ROOT / "A id00001.txt").is_file())
        check("package created",
              source_package.package_path_for(
                  controller.SOURCES_ROOT / "A id00001.txt").is_file())
        check("registry created",
              any(handoff.SOURCE_REGISTRY.glob("ja_*.json")))
        check("pipeline() called once", pipeline.call_count == 1)
        check("launcher passed was launch_stage_inprocess",
              pipeline.call_args.kwargs.get("launcher")
              is batch_importer.production_manager.launch_stage_inprocess)
        check("subprocess.run never called", run.call_count == 0)
    finally:
        base.restore(saved)


@test("--batch-mode: a failing file's pipeline() result is reported and "
      "does not abort the batch")
def _():
    tmp, saved = base.setup()
    try:
        input_dir = tmp / "Beginner"
        input_dir.mkdir()
        (input_dir / "A id00001.html").write_text(
            "<p>こんにちは。</p>", encoding="utf-8")
        (input_dir / "B id00002.html").write_text(
            "<p>おはよう。</p>", encoding="utf-8")

        results = [
            failure_result("api", "parser exploded"),
            success_result(),
        ]
        with mock.patch("batch_importer.production_manager.pipeline",
                        side_effect=results):
            code, out, _err = run_cli(
                ["--folder", str(input_dir), "--creator", "test_creator",
                 "--batch-mode"],
                tmp, saved)

        check("exit 1 (failures present)", code == 1)
        check("A failed with detail",
              "[FAIL pipeline] A id00001.html: parser exploded" in out, out)
        check("B still imported", "[IMPORTED] B id00002.html" in out)
        check("summary imported 1 failed 1",
              "imported: 1" in out and "failed: 1" in out)
    finally:
        base.restore(saved)


@test("--batch-mode: an exception raised inside pipeline() is caught, "
      "matching the subprocess path's own failure isolation")
def _():
    tmp, saved = base.setup()
    try:
        input_dir = tmp / "Beginner"
        input_dir.mkdir()
        (input_dir / "A id00001.html").write_text(
            "<p>こんにちは。</p>", encoding="utf-8")
        (input_dir / "B id00002.html").write_text(
            "<p>おはよう。</p>", encoding="utf-8")

        def side_effect(*args, **kwargs):
            if not side_effect.called:
                side_effect.called = True
                raise RuntimeError("boom")
            return success_result()
        side_effect.called = False

        with mock.patch("batch_importer.production_manager.pipeline",
                        side_effect=side_effect):
            code, out, _err = run_cli(
                ["--folder", str(input_dir), "--creator", "test_creator",
                 "--batch-mode"],
                tmp, saved)

        check("exit 1 (failures present)", code == 1)
        check("A failed as unexpected",
              "[FAIL unexpected] A id00001.html: boom" in out, out)
        check("B still imported despite A's exception",
              "[IMPORTED] B id00002.html" in out)
    finally:
        base.restore(saved)


@test("without --batch-mode, subprocess.run is used and "
      "production_manager.pipeline is never called")
def _():
    tmp, saved = base.setup()
    try:
        input_dir = tmp / "Beginner"
        input_dir.mkdir()
        (input_dir / "A id00001.html").write_text(
            "<p>こんにちは。</p>", encoding="utf-8")

        pipeline_ok = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch("batch_importer.subprocess.run",
                        return_value=pipeline_ok) as run, \
             mock.patch("batch_importer.production_manager.pipeline") as pipeline:
            code, out, _err = run_cli(
                ["--folder", str(input_dir), "--creator", "test_creator"],
                tmp, saved)

        check("exit 0", code == 0)
        check("subprocess.run used", run.call_count == 1)
        check("pipeline() never called", pipeline.call_count == 0)
    finally:
        base.restore(saved)


@test("--batch-mode passes --stage-timeout through as pipeline()'s timeout=")
def _():
    tmp, saved = base.setup()
    try:
        input_dir = tmp / "Beginner"
        input_dir.mkdir()
        (input_dir / "A id00001.html").write_text(
            "<p>こんにちは。</p>", encoding="utf-8")

        with mock.patch("batch_importer.production_manager.pipeline",
                        return_value=success_result()) as pipeline:
            code, _out, _err = run_cli(
                ["--folder", str(input_dir), "--creator", "test_creator",
                 "--batch-mode", "--stage-timeout", "42"],
                tmp, saved)

        check("exit 0", code == 0)
        check("timeout passed through",
              pipeline.call_args.kwargs.get("timeout") == 42,
              pipeline.call_args)
    finally:
        base.restore(saved)


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
