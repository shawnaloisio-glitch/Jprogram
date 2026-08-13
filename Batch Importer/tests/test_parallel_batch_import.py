#!/usr/bin/env python3
"""
test_parallel_batch_import.py

Deterministic tests for the parallel batch import orchestrator
(Batch Importer/parallel_batch_import.py).

Covers the pure orchestration logic (chunking, worker command building,
summary-count parsing, importable-file listing) without launching real
subprocesses or running the real GiNZA pipeline. A real, small-scale live
run (actual subprocesses, actual files) is documented separately in
DONE.md rather than automated here, matching this project's convention
of keeping the automated suite fast and GiNZA-free.

Run:
    python "Batch Importer/tests/test_parallel_batch_import.py"
"""

import json
import pathlib
import sys
import tempfile

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
import paths
import parallel_batch_import as pbi

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
    """Same sandbox pattern as test_batch_importer.py."""
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
        json.dumps({"creators": ["test_creator"]}), encoding="utf-8")
    return tmp, saved


def restore(saved):
    (controller.SOURCES_ROOT, handoff.SOURCE_REGISTRY,
     handoff.CLEANING_JOBS, paths.CREATORS_CONFIG) = saved


# ============================================================
# chunk()
# ============================================================

@test("chunk: splits evenly across n, order-preserving, round-robin")
def _():
    items = list(range(12))
    chunks = pbi.chunk(items, 4)
    check("4 chunks", len(chunks) == 4)
    check("each has 3", all(len(c) == 3 for c in chunks))
    check("round-robin order",
          chunks[0] == [0, 4, 8] and chunks[1] == [1, 5, 9])
    check("all items present, none duplicated",
          sorted(sum(chunks, [])) == items)


@test("chunk: fewer items than n produces fewer, non-empty chunks")
def _():
    chunks = pbi.chunk([1, 2, 3], 6)
    check("3 non-empty chunks, not 6", len(chunks) == 3)
    check("no empty chunks", all(len(c) > 0 for c in chunks))


@test("chunk: empty input produces no chunks")
def _():
    check("no chunks", pbi.chunk([], 6) == [])


# ============================================================
# build_worker_command()
# ============================================================

@test("build_worker_command: base command always includes --batch-mode")
def _():
    cmd = pbi.build_worker_command(
        pathlib.Path("D:/x"), "test_creator", None, None, None, None,
        None, False)
    check("has --batch-mode", "--batch-mode" in cmd)
    check("has --folder", "--folder" in cmd)
    check("no optional flags leaked in", "--style" not in cmd
          and "--topic" not in cmd and "--dry-run" not in cmd)


@test("build_worker_command: all optional flags pass through when set")
def _():
    cmd = pbi.build_worker_command(
        pathlib.Path("D:/x"), "test_creator", "1", "2", 3, 4, 60, True)
    check("style", "--style" in cmd and "1" in cmd)
    check("topic", "--topic" in cmd and "2" in cmd)
    check("episode", "--episode" in cmd and "3" in cmd)
    check("season", "--season" in cmd and "4" in cmd)
    check("stage-timeout", "--stage-timeout" in cmd and "60" in cmd)
    check("dry-run", "--dry-run" in cmd)


# ============================================================
# parse_summary_counts()
# ============================================================

@test("parse_summary_counts: reads all four counters from real "
      "batch_importer.py output")
def _():
    output = (
        "[IMPORTED] a.vtt\n[FAIL convert] b.vtt: boom\n\n"
        "Summary:\n"
        "  imported: 3\n"
        "  skipped (already imported): 2\n"
        "  skipped (unsupported format): 1\n"
        "  failed: 1\n"
    )
    counts = pbi.parse_summary_counts(output)
    check("imported", counts["imported"] == 3)
    check("skipped_already", counts["skipped_already"] == 2)
    check("skipped_unsupported", counts["skipped_unsupported"] == 1)
    check("failed", counts["failed"] == 1)


@test("parse_summary_counts: missing/garbled output defaults to zeros, "
      "does not raise")
def _():
    counts = pbi.parse_summary_counts("some crash traceback, no summary")
    check("all zero", counts == {
        "imported": 0, "skipped_already": 0,
        "skipped_unsupported": 0, "failed": 0,
    })


# ============================================================
# list_importable_files()
# ============================================================

@test("list_importable_files: excludes already-imported and unsupported, "
      "keeps only real work")
def _():
    tmp, saved = setup()
    try:
        folder = tmp / "Beginner"
        folder.mkdir()
        (folder / "A id00001.vtt").write_text("dummy", encoding="utf-8")
        (folder / "B id00002.vtt").write_text("dummy", encoding="utf-8")
        (folder / "C id00003.txt").write_text("dummy", encoding="utf-8")  # unsupported

        # Pre-mark A as already imported.
        controller.SOURCES_ROOT.mkdir(parents=True, exist_ok=True)
        (controller.SOURCES_ROOT / "A id00001.txt").write_text(
            "x", encoding="utf-8")

        todo = pbi.list_importable_files(folder)
        names = [p.name for p in todo]
        check("only B remains", names == ["B id00002.vtt"], names)
    finally:
        restore(saved)


# ============================================================
# CLI validation (no real subprocess launched)
# ============================================================

@test("main: rejects --workers 0")
def _():
    tmp, saved = setup()
    try:
        folder = tmp / "Beginner"
        folder.mkdir()
        code = pbi.main(["--folder", str(folder), "--creator", "test_creator",
                          "--workers", "0"])
        check("exit 1", code == 1)
    finally:
        restore(saved)


@test("main: missing folder fails clearly")
def _():
    code = pbi.main(["--folder", "Z:/does/not/exist", "--creator", "x"])
    check("exit 1", code == 1)


@test("main: unknown creator fails before any staging happens")
def _():
    tmp, saved = setup()
    try:
        folder = tmp / "Beginner"
        folder.mkdir()
        code = pbi.main(["--folder", str(folder), "--creator", "nonexistent"])
        check("exit 1", code == 1)
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
