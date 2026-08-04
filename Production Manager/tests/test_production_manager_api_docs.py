#!/usr/bin/env python3
"""
test_production_manager_api_docs.py

Documentation consistency tests for the Production Manager public API
freeze (G0.2).

These tests verify that the frozen documentation matches the actual code.
They are contract checks only; they do not test pipeline behavior.

Run:
    python "Production Manager/tests/test_production_manager_api_docs.py"
"""

import pathlib
import re
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
PRODUCTION_MANAGER = PROJECT_ROOT / "Production Manager"
sys.path.insert(0, str(PRODUCTION_MANAGER))

import production_manager as pm

GUI_API = PRODUCTION_MANAGER / "GUI_API.md"
API_VERSION = PRODUCTION_MANAGER / "API_VERSION.md"
GUI_ARCH = PROJECT_ROOT / "Daily Handoff" / "GUI_ARCHITECTURE.md"

PUBLIC_API = ("status", "report", "dry_run", "run_stage", "pipeline")

GUARANTEED = {
    "status": {"success", "source_id", "state", "failed_stage",
               "next_stage", "stages", "evidence"},
    "report": {"success", "source_id", "state", "failed_stage",
               "next_stage", "stages", "evidence"},
    "dry_run": {"success", "source_id", "state", "plan", "boundary"},
    "run_stage": {"stage", "source_id", "command", "exit_code", "stdout",
                  "stderr", "success", "error"},
    "pipeline": {"success", "exit_code", "source_id", "state",
                 "failed_stage", "next_stage", "stages_run", "exit_codes",
                 "boundary", "events"},
}


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


@test("every documented public function exists")
def _():
    for fn in PUBLIC_API:
        check(f"{fn} exists", hasattr(pm, fn))


@test("GUI_API documents every public function")
def _():
    text = GUI_API.read_text(encoding="utf-8")
    for fn in PUBLIC_API:
        check(f"{fn} documented", f"## {fn}(" in text)


@test("every documented return field exists in code")
def _():
    for fn in PUBLIC_API:
        func = getattr(pm, fn)
        # Inspect the function's return statement keys by calling where safe.
        # status/report/dry_run are read-only and safe on an unknown source.
        if fn in ("status", "report", "dry_run"):
            data = func("__doc_consistency_missing__")
            for field in GUARANTEED[fn]:
                check(f"{fn}.{field} present", field in data)
        elif fn == "run_stage":
            # run_stage is a thin wrapper over launch_stage; its fields are
            # produced by launch_stage. Inspect both.
            combined = _function_source(func) + "\n" + \
                _function_source(pm.launch_stage)
            for field in GUARANTEED[fn]:
                check(f"{fn} produces '{field}'", f"\"{field}\"" in combined
                      or f"'{field}'" in combined)
        elif fn == "pipeline":
            src = _function_source(func)
            for field in GUARANTEED[fn]:
                check(f"{fn} produces '{field}'", f"\"{field}\"" in src
                      or f"'{field}'" in src)


def _function_source(func):
    import inspect
    return inspect.getsource(func)


@test("API_VERSION file present and frozen")
def _():
    text = API_VERSION.read_text(encoding="utf-8")
    check("version 1.0", "API Version: 1.0" in text)
    check("status frozen", "Frozen" in text)
    check("breaking changes guarded",
          "Not permitted without explicit architectural approval" in text)


@test("GUI_API references only public functions")
def _():
    text = GUI_API.read_text(encoding="utf-8")
    # Every backticked function call documented should be a public one.
    documented = set(re.findall(r"`(\w+)\(\)`", text))
    check("only public functions referenced", documented <= set(PUBLIC_API))
    # Public functions must appear in GUI_API.
    for fn in PUBLIC_API:
        check(f"{fn} in GUI_API", fn in text)


@test("GUI_ARCHITECTURE present with boundaries")
def _():
    check("file exists", GUI_ARCH.is_file())
    text = GUI_ARCH.read_text(encoding="utf-8")
    check("must not perform pipeline logic",
          "Perform pipeline logic" in text or "pipeline logic" in text)
    check("must not inspect artifacts directly",
          "Inspect artifacts directly" in text)
    check("must not import stage modules",
          "Import stage modules" in text)
    check("must not execute subprocesses",
          "Execute subprocesses" in text)
    check("must not modify JSONL", "Modify JSONL" in text)


@test("documented stages match STAGE_NAMES")
def _():
    text = GUI_API.read_text(encoding="utf-8")
    for stage in pm.STAGE_NAMES:
        check(f"stage {stage} documented", stage in text)


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
