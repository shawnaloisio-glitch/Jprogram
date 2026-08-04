#!/usr/bin/env python3
"""
test_registry.py

Deterministic tests for registry.py.

Run:
    python "Source Intake/tests/test_registry.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_INTAKE = PROJECT_ROOT / "Source Intake"
sys.path.insert(0, str(SOURCE_INTAKE))

import registry


def entry_args():
    return {
        "source_id": "pod_conteppei_ep051",
        "original_filename": "con.txt",
        "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        "source_type": "podcast_transcript",
        "format": "txt",
        "language": "ja",
        "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": "1.2.0",
    }


def expected_bytes(entry):
    return (
        json.dumps(entry, ensure_ascii=False, sort_keys=True, indent=4) + "\n"
    ).encode("utf-8")


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("valid registry creation")
def _():
    entry = registry.build_entry(**entry_args())
    check("schema_version", entry["schema_version"] == "1")
    check("source_id", entry["source_id"] == "pod_conteppei_ep051")
    check("field count", len(entry) == 9)
    path = pathlib.Path(tempfile.mkdtemp()) / "pod_conteppei_ep051.json"
    registry.write_registry(path, entry)
    check("file exists", path.is_file())
    parsed = json.loads(path.read_text(encoding="utf-8"))
    check("round-trips", parsed == entry)


@test("schema validation on write")
def _():
    entry = registry.build_entry(**entry_args())
    entry["sha256"] = "not-a-hash"
    path = pathlib.Path(tempfile.mkdtemp()) / "x.json"
    raised = False
    try:
        registry.write_registry(path, entry)
    except registry.RegistryError:
        raised = True
    check("invalid sha256 raises", raised)
    check("no file written", not path.exists())


@test("deterministic byte output")
def _():
    entry = registry.build_entry(**entry_args())
    p1 = pathlib.Path(tempfile.mkdtemp()) / "a.json"
    p2 = pathlib.Path(tempfile.mkdtemp()) / "b.json"
    registry.write_registry(p1, entry)
    registry.write_registry(p2, entry)
    check("byte-identical", p1.read_bytes() == p2.read_bytes())
    check("matches expected bytes", p1.read_bytes() == expected_bytes(entry))


@test("atomic write behavior (no temp leftover)")
def _():
    entry = registry.build_entry(**entry_args())
    path = pathlib.Path(tempfile.mkdtemp()) / "pod_conteppei_ep051.json"
    registry.write_registry(path, entry)
    check("final file exists", path.is_file())
    check("no .tmp leftover", not path.with_name(path.name + ".tmp").exists())
    check("valid json", json.loads(path.read_text(encoding="utf-8")) == entry)


@test("missing required field rejection")
def _():
    entry = registry.build_entry(**entry_args())
    del entry["language"]
    path = pathlib.Path(tempfile.mkdtemp()) / "x.json"
    raised = False
    message = ""
    try:
        registry.write_registry(path, entry)
    except registry.RegistryError as ex:
        raised = True
        message = str(ex)
    check("missing field raises", raised)
    check("reports field", "language" in message, message)
    check("no file written", not path.exists())


@test("registry module boundary (no forbidden imports)")
def _():
    source = pathlib.Path(SOURCE_INTAKE / "registry.py").read_text(encoding="utf-8")
    for forbidden in ("import cleaning_job", "from cleaning_job",
                      "import clean_transcript", "import clean_subtitles",
                      "corpus_builder", "response_validator", "deepseek_client",
                      "import paths", "from paths", "import Analysis"):
        check(f"no {forbidden!r}", forbidden not in source)


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
