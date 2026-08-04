#!/usr/bin/env python3
"""
test_source_builder_gui_settings.py

Deterministic tests for the Source Builder GUI settings persistence
(persistent metadata: source_type, origin, language).

Collection is intentionally NOT persisted.

Run:
    python "Source Builder/tests/test_source_builder_gui_settings.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))

import gui_settings


def temp_path():
    root = pathlib.Path(tempfile.mkdtemp())
    return root / "gui_settings.json"


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("missing settings file yields empty defaults")
def _():
    settings = gui_settings.load_settings(temp_path())
    check("defaults", settings == {"source_type": "", "origin": ""})


@test("save then load round-trips persisted keys")
def _():
    path = temp_path()
    gui_settings.save_settings(
        {"source_type": "subtitle", "origin": "nhk_news"},
        path=path)
    settings = gui_settings.load_settings(path)
    check("source_type", settings["source_type"] == "subtitle")
    check("origin", settings["origin"] == "nhk_news")


@test("empty values are not persisted")
def _():
    path = temp_path()
    gui_settings.save_settings({"source_type": "", "origin": ""},
                               path=path)
    check("file empty keys",
          json.loads(path.read_text(encoding="utf-8")) == {})
    settings = gui_settings.load_settings(path)
    check("loads empty", settings == {"source_type": "", "origin": ""})


@test("corrupt settings file yields empty defaults")
def _():
    path = temp_path()
    path.write_text("{ not json", encoding="utf-8")
    settings = gui_settings.load_settings(path)
    check("corrupt handled", settings == {"source_type": "", "origin": ""})


@test("non-dict settings file yields empty defaults")
def _():
    path = temp_path()
    path.write_text("[1, 2, 3]", encoding="utf-8")
    settings = gui_settings.load_settings(path)
    check("non-dict handled",
          settings == {"source_type": "", "origin": ""})


@test("non-string persisted values are ignored")
def _():
    path = temp_path()
    path.write_text(json.dumps({"source_type": 5, "origin": None}),
                    encoding="utf-8")
    settings = gui_settings.load_settings(path)
    check("source_type ignored", settings["source_type"] == "")
    check("origin ignored", settings["origin"] == "")


@test("unknown persisted keys are ignored (e.g. legacy language)")
def _():
    path = temp_path()
    path.write_text(json.dumps({"source_type": "article", "origin": "nhk_news",
                                "language": "ja"}),
                    encoding="utf-8")
    settings = gui_settings.load_settings(path)
    check("source_type", settings["source_type"] == "article")
    check("origin", settings["origin"] == "nhk_news")
    check("no language key", "language" not in settings)


@test("atomic write: no temp leftover after save")
def _():
    path = temp_path()
    gui_settings.save_settings({"source_type": "article"}, path=path)
    check("no .tmp", not path.with_name(path.name + ".tmp").exists())


@test("persisted keys constant matches documented scope")
def _():
    check("keys", gui_settings.PERSISTED_KEYS == ("source_type", "origin"))


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
