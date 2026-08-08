#!/usr/bin/env python3
"""
test_batch_importer.py

Deterministic tests for the Batch Importer CLI (Batch Importer/batch_importer.py).

Covers the parts of the batch script that do NOT require the real
GiNZA/production pipeline to run:

- format detection/routing (.html vs .vtt/.srt vs unsupported),
- the idempotency check (already-imported files are skipped, never
  re-processed, including re-runs after more files are added),
- --dry-run classification with no real side effects,
- --creator validation (unknown creator fails clearly, does not proceed),
- failure isolation (one bad file never aborts the batch),
- the pipeline subprocess command shape (venv python, --timeout passthrough),
- material level suggestion pass-through to the source package.

The production_manager.py subprocess call and the analysis step are mocked;
the pipeline stages themselves are tested elsewhere and are out of scope
here. All writes are sandboxed to temporary directories (Sources, Source
Registry, Cleaning Jobs, and the creators config) — the real workspace and
Config/creators.json are never touched.

Run:
    python "Batch Importer/tests/test_batch_importer.py"
"""

import contextlib
import io
import json
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
import import_material
import paths
import source_package

TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


def setup():
    """Patch Sources, Registry, Cleaning Jobs, and creators config into temp dirs."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    saved = (
        controller.SOURCES_ROOT,
        handoff.SOURCE_REGISTRY,
        handoff.CLEANING_JOBS,
        paths.CREATORS_CONFIG,
    )
    controller.SOURCES_ROOT = tmp / "Sources"
    handoff.SOURCE_REGISTRY = tmp / "Source Registry"
    handoff.CLEANING_JOBS = tmp / "Cleaning Jobs"
    config_dir = tmp / "Config"
    config_dir.mkdir(parents=True, exist_ok=True)
    paths.CREATORS_CONFIG = config_dir / "creators.json"
    paths.CREATORS_CONFIG.write_text(
        json.dumps({"creators": ["test_creator", "nhk_news"]}),
        encoding="utf-8")
    return tmp, saved


def restore(saved):
    (controller.SOURCES_ROOT, handoff.SOURCE_REGISTRY,
     handoff.CLEANING_JOBS, paths.CREATORS_CONFIG) = saved


def run_cli(args, tmp, saved):
    """Run the batch importer CLI against a sandbox; capture combined output."""
    _ = (tmp, saved)  # sandbox already applied by setup()
    buf = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        code = batch_importer.main(args)
    return code, buf.getvalue(), err.getvalue()


# ============================================================
# Format detection / routing
# ============================================================

@test("format routing detects html/vtt/srt and rejects everything else")
def _():
    check("html", batch_importer.format_for_path("x.html")
          == import_material.FORMAT_NIHONGO_JIKAN)
    check("vtt", batch_importer.format_for_path("x.vtt")
          == import_material.FORMAT_SUBTITLE)
    check("srt", batch_importer.format_for_path("x.srt")
          == import_material.FORMAT_SUBTITLE)
    check("uppercase html", batch_importer.format_for_path("x.HTML")
          == import_material.FORMAT_NIHONGO_JIKAN)
    check("uppercase vtt", batch_importer.format_for_path("x.VTT")
          == import_material.FORMAT_SUBTITLE)
    check("txt unsupported", batch_importer.format_for_path("x.txt") is None)
    check("mp4 unsupported", batch_importer.format_for_path("x.mp4") is None)
    check("no extension unsupported", batch_importer.format_for_path("x") is None)
    check("hidden html", batch_importer.format_for_path(".html") is None
          or batch_importer.format_for_path(".html")
          == import_material.FORMAT_NIHONGO_JIKAN)


@test("classify: supported without canonical -> import")
def _():
    tmp, saved = setup()
    try:
        input_dir = tmp / "input"
        input_dir.mkdir()
        f = input_dir / "A id00001.html"
        f.write_text("<p>こんにちは。</p>", encoding="utf-8")
        kind, fmt = batch_importer.classify(f)
        check("kind import", kind == batch_importer.KIND_IMPORT)
        check("fmt nihongo_jikan", fmt == import_material.FORMAT_NIHONGO_JIKAN)
    finally:
        restore(saved)


@test("classify: already-imported canonical exists -> skip_already")
def _():
    tmp, saved = setup()
    try:
        controller.SOURCES_ROOT.mkdir(parents=True, exist_ok=True)
        input_dir = tmp / "input"
        input_dir.mkdir()
        f = input_dir / "A id00001.html"
        f.write_text("<p>こんにちは。</p>", encoding="utf-8")
        (controller.SOURCES_ROOT / "A id00001.txt").write_text(
            "こんにちは。\n", encoding="utf-8")
        kind, _fmt = batch_importer.classify(f)
        check("kind skip_already", kind == batch_importer.KIND_SKIP_ALREADY)
    finally:
        restore(saved)


@test("classify: unsupported extension -> skip_unsupported")
def _():
    tmp, saved = setup()
    try:
        input_dir = tmp / "input"
        input_dir.mkdir()
        f = input_dir / "C notes.txt"
        f.write_text("not a source", encoding="utf-8")
        kind, _fmt = batch_importer.classify(f)
        check("kind skip_unsupported", kind == batch_importer.KIND_SKIP_UNSUPPORTED)
    finally:
        restore(saved)


# ============================================================
# Idempotency
# ============================================================

@test("already-imported file is skipped and never re-processed")
def _():
    tmp, saved = setup()
    try:
        controller.SOURCES_ROOT.mkdir(parents=True, exist_ok=True)
        input_dir = tmp / "input"
        input_dir.mkdir()
        f = input_dir / "A id00001.html"
        f.write_text("<p>こんにちは。</p>", encoding="utf-8")
        canonical = controller.SOURCES_ROOT / "A id00001.txt"
        canonical.write_text("こんにちは。\n", encoding="utf-8")

        with mock.patch("batch_importer.subprocess.run") as run:
            code, out, _err = run_cli(
                ["--folder", str(input_dir), "--creator", "test_creator"],
                tmp, saved)

        check("exit 0", code == 0)
        check("logged skip", "[SKIP already-imported] A id00001.html" in out)
        check("summary skip count", "skipped (already imported): 1" in out)
        check("no pipeline run", not run.called)
        check("canonical untouched",
              canonical.read_text(encoding="utf-8") == "こんにちは。\n")
    finally:
        restore(saved)


@test("re-run after adding more files imports only the new files")
def _():
    tmp, saved = setup()
    try:
        input_dir = tmp / "Beginner"  # level-named folder so import succeeds
        input_dir.mkdir()
        a = input_dir / "A id00001.html"
        a.write_text("<p>こんにちは。</p>", encoding="utf-8")

        pipeline_ok = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch("batch_importer.subprocess.run",
                        return_value=pipeline_ok) as run, \
             mock.patch("batch_importer.processing_tab.run_analysis",
                        return_value={}) as analysis:
            code, _out, _err = run_cli(
                ["--folder", str(input_dir), "--creator", "test_creator"],
                tmp, saved)
            check("first run exit 0", code == 0)
            check("first run imported",
                  (controller.SOURCES_ROOT / "A id00001.txt").is_file())

            # Add a new file and re-run the same folder.
            b = input_dir / "B id00002.srt"
            b.write_text(
                "1\n00:00:01,000 --> 00:00:02,000\nお元気ですか。\n",
                encoding="utf-8")
            run.reset_mock()
            analysis.reset_mock()
            code, out, _err = run_cli(
                ["--folder", str(input_dir), "--creator", "test_creator"],
                tmp, saved)

            check("second run exit 0", code == 0)
            check("A skipped as already imported",
                  "[SKIP already-imported] A id00001.html" in out)
            check("B imported", "[IMPORTED] B id00002.srt" in out)
            check("pipeline ran once (only for B)", run.call_count == 1)
            check("analysis ran once (only for B)", analysis.call_count == 1)
            check("B canonical exists",
                  (controller.SOURCES_ROOT / "B id00002.txt").is_file())
    finally:
        restore(saved)


# ============================================================
# --dry-run
# ============================================================

@test("dry-run classifies correctly without creating or running anything")
def _():
    tmp, saved = setup()
    try:
        controller.SOURCES_ROOT.mkdir(parents=True, exist_ok=True)
        input_dir = tmp / "input"
        input_dir.mkdir()
        (input_dir / "A id00001.html").write_text(
            "<p>こんにちは。</p>", encoding="utf-8")
        (input_dir / "B id00002.srt").write_text(
            "1\n00:00:01,000 --> 00:00:02,000\nお元気ですか。\n",
            encoding="utf-8")
        (input_dir / "C notes.txt").write_text("not a source", encoding="utf-8")
        (controller.SOURCES_ROOT / "B id00002.txt").write_text(
            "お元気ですか。\n", encoding="utf-8")

        with mock.patch("batch_importer.subprocess.run") as run, \
             mock.patch("batch_importer.processing_tab.run_analysis") as analysis:
            code, out, _err = run_cli(
                ["--folder", str(input_dir), "--creator", "test_creator",
                 "--dry-run"],
                tmp, saved)

        check("exit 0", code == 0)
        check("would-import html",
              "[WOULD-IMPORT nihongo_jikan] A id00001.html" in out)
        check("would-skip already",
              "[WOULD-SKIP already-imported] B id00002.srt" in out)
        check("would-skip unsupported",
              "[WOULD-SKIP unsupported-format] C notes.txt" in out)
        check("no pipeline run", not run.called)
        check("no analysis run", not analysis.called)
        # Nothing new was written: only the pre-existing canonical file exists.
        check("only pre-existing canonical",
              sorted(p.name for p in controller.SOURCES_ROOT.iterdir())
              == ["B id00002.txt"])
        check("A not created", not (controller.SOURCES_ROOT / "A id00001.txt").exists())
    finally:
        restore(saved)


# ============================================================
# Creator validation
# ============================================================

@test("unknown creator fails clearly and does not proceed")
def _():
    tmp, saved = setup()
    try:
        input_dir = tmp / "input"
        input_dir.mkdir()
        (input_dir / "A id00001.html").write_text(
            "<p>こんにちは。</p>", encoding="utf-8")

        with mock.patch("batch_importer.subprocess.run") as run:
            code, out, err = run_cli(
                ["--folder", str(input_dir), "--creator", "nobody_here"],
                tmp, saved)

        check("non-zero exit", code == 1)
        check("clear error on stderr",
              "unknown creator_id" in err and "nobody_here" in err)
        check("no import started", "[IMPORTED]" not in out)
        check("no canonical created",
              not (controller.SOURCES_ROOT / "A id00001.txt").exists())
        check("no pipeline run", not run.called)
    finally:
        restore(saved)


@test("missing creators config fails clearly for any creator")
def _():
    tmp, saved = setup()
    try:
        # Remove the creators config: load_creators() -> [].
        paths.CREATORS_CONFIG.unlink()
        input_dir = tmp / "input"
        input_dir.mkdir()
        (input_dir / "A id00001.html").write_text(
            "<p>こんにちは。</p>", encoding="utf-8")

        with mock.patch("batch_importer.subprocess.run") as run:
            code, _out, err = run_cli(
                ["--folder", str(input_dir), "--creator", "test_creator"],
                tmp, saved)

        check("non-zero exit", code == 1)
        check("clear error on stderr",
              "unknown creator_id" in err and "none configured" in err)
        check("no pipeline run", not run.called)
    finally:
        restore(saved)


@test("missing folder fails clearly")
def _():
    tmp, saved = setup()
    try:
        code, _out, err = run_cli(
            ["--folder", str(tmp / "does-not-exist"), "--creator", "test_creator"],
            tmp, saved)
        check("non-zero exit", code == 1)
        check("clear error on stderr", "folder not found" in err)
    finally:
        restore(saved)


# ============================================================
# End-to-end orchestration (pipeline + analysis mocked)
# ============================================================

@test("valid creator imports a file end-to-end with mocked pipeline")
def _():
    tmp, saved = setup()
    try:
        input_dir = tmp / "Beginner"  # level-named folder so import succeeds
        input_dir.mkdir()
        (input_dir / "A id00001.html").write_text(
            "<p>こんにちは。</p>", encoding="utf-8")

        pipeline_ok = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch("batch_importer.subprocess.run",
                        return_value=pipeline_ok) as run, \
             mock.patch("batch_importer.processing_tab.run_analysis",
                        return_value={"output_path": "x", "summary": {}}) as analysis:
            code, out, _err = run_cli(
                ["--folder", str(input_dir), "--creator", "test_creator"],
                tmp, saved)

        check("exit 0", code == 0)
        check("imported line", "[IMPORTED] A id00001.html" in out)
        check("summary imported 1", "imported: 1" in out)
        check("canonical created", (controller.SOURCES_ROOT / "A id00001.txt").is_file())
        check("package created",
              source_package.package_path_for(
                  controller.SOURCES_ROOT / "A id00001.txt").is_file())
        check("registry created",
              (handoff.SOURCE_REGISTRY / "clean_text_a-id00001.json").is_file())
        check("pipeline ran once", run.call_count == 1)
        check("analysis ran once", analysis.call_count == 1)
    finally:
        restore(saved)


@test("a failing file does not abort the batch")
def _():
    tmp, saved = setup()
    try:
        input_dir = tmp / "Beginner"  # level-named folder so import succeeds
        input_dir.mkdir()
        (input_dir / "A id00001.html").write_text(
            "<p>こんにちは。</p>", encoding="utf-8")
        # Empty file -> conversion fails (no utterances).
        (input_dir / "B id00002.html").write_text("", encoding="utf-8")

        pipeline_ok = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch("batch_importer.subprocess.run",
                        return_value=pipeline_ok) as run, \
             mock.patch("batch_importer.processing_tab.run_analysis",
                        return_value={}) as analysis:
            code, out, _err = run_cli(
                ["--folder", str(input_dir), "--creator", "test_creator"],
                tmp, saved)

        check("exit 1 (failures present)", code == 1)
        check("A still imported", "[IMPORTED] A id00001.html" in out)
        check("B failed at convert", "[FAIL convert] B id00002.html" in out)
        check("summary failed 1", "failed: 1" in out)
        check("pipeline ran once (only for A)", run.call_count == 1)
        check("analysis ran once", analysis.call_count == 1)
    finally:
        restore(saved)


@test("non-zero pipeline exit is logged as a pipeline failure")
def _():
    tmp, saved = setup()
    try:
        input_dir = tmp / "Beginner"  # level-named folder so import succeeds
        input_dir.mkdir()
        (input_dir / "A id00001.html").write_text(
            "<p>こんにちは。</p>", encoding="utf-8")

        pipeline_fail = mock.Mock(returncode=1, stdout="",
                                  stderr="boom from pipeline")
        with mock.patch("batch_importer.subprocess.run",
                        return_value=pipeline_fail) as run, \
             mock.patch("batch_importer.processing_tab.run_analysis") as analysis:
            code, out, _err = run_cli(
                ["--folder", str(input_dir), "--creator", "test_creator"],
                tmp, saved)

        check("exit 1", code == 1)
        check("failed at pipeline", "[FAIL pipeline] A id00001.html" in out)
        check("exit code in message", "exit code 1" in out)
        check("stderr tail in message", "boom from pipeline" in out)
        check("no analysis after pipeline failure", not analysis.called)
        check("pipeline ran once", run.call_count == 1)
    finally:
        restore(saved)


@test("material level suggestion is passed through to the source package")
def _():
    tmp, saved = setup()
    try:
        # A "Beginner" folder suggests level 2 (see import_material mapping).
        input_dir = tmp / "Beginner"
        input_dir.mkdir()
        (input_dir / "A id00001.html").write_text(
            "<p>こんにちは。</p>", encoding="utf-8")

        pipeline_ok = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch("batch_importer.subprocess.run",
                        return_value=pipeline_ok), \
             mock.patch("batch_importer.processing_tab.run_analysis",
                        return_value={}):
            code, _out, _err = run_cli(
                ["--folder", str(input_dir), "--creator", "test_creator"],
                tmp, saved)

        check("exit 0", code == 0)
        package = json.loads(
            source_package.package_path_for(
                controller.SOURCES_ROOT / "A id00001.txt")
            .read_text(encoding="utf-8"))
        check("material level 2 (Beginner)", package.get("material_level") == 2)
    finally:
        restore(saved)


@test("unmatched level folder reports a clear create-stage failure")
def _():
    tmp, saved = setup()
    try:
        input_dir = tmp / "unmatched-folder"
        input_dir.mkdir()
        (input_dir / "A id00001.html").write_text(
            "<p>こんにちは。</p>", encoding="utf-8")

        with mock.patch("batch_importer.subprocess.run") as run:
            code, out, _err = run_cli(
                ["--folder", str(input_dir), "--creator", "test_creator"],
                tmp, saved)

        check("exit 1", code == 1)
        check("failed at create", "[FAIL create] A id00001.html" in out)
        check("package reason", "source package was not written" in out)
        check("no pipeline", not run.called)
    finally:
        restore(saved)


# ============================================================
# Pipeline command shape
# ============================================================

@test("pipeline command uses the venv python and passes --timeout through")
def _():
    cmd = batch_importer.build_pipeline_command("clean_text_a-id00001")
    check("venv python", cmd[0].endswith((".venv/Scripts/python.exe",
                                          ".venv\\Scripts\\python.exe")))
    check("production manager script",
          pathlib.Path(cmd[1]).name == "production_manager.py")
    check("pipeline args",
          cmd[2:6] == ["--source", "clean_text_a-id00001", "--pipeline", "--auto"])
    check("no timeout by default", "--timeout" not in cmd)

    cmd2 = batch_importer.build_pipeline_command(
        "clean_text_a-id00001", stage_timeout=120)
    check("timeout passed", "--timeout" in cmd2)
    check("timeout value", cmd2[cmd2.index("--timeout") + 1] == "120")


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
