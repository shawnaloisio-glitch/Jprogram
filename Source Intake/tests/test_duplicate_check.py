#!/usr/bin/env python3
"""
test_duplicate_check.py

Deterministic tests for duplicate_check.py.

Run:
    python "Source Intake/tests/test_duplicate_check.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_INTAKE = PROJECT_ROOT / "Source Intake"
sys.path.insert(0, str(SOURCE_INTAKE))

import duplicate_check
import schemas

HASH_A = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
HASH_B = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a09"


def valid_entry(source_id, sha256):
    return {
        "schema_version": schemas.schema_version("registry"),
        "source_id": source_id,
        "original_filename": f"{source_id}.txt",
        "sha256": sha256,
        "source_type": "clean_text",
        "format": "txt",
        "language": "ja",
        "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": "1.0",
    }


def write_registry_entry(registry_dir, entry):
    path = registry_dir / f"{entry['source_id']}.json"
    path.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("empty registry (directory missing)")
def _():
    root = pathlib.Path(tempfile.mkdtemp())
    v = duplicate_check.check(HASH_A, "pod_conteppei_ep051",
                              root / "registry", root / "jobs")
    check("no duplicate by hash", v["duplicate_by_hash"] is False)
    check("no duplicate id", v["duplicate_source_id"] is None)
    check("no match by id", v["match_by_source_id"] is False)
    check("registry not exists", v["registry_exists"] is False)
    check("job not exists", v["job_exists"] is False)
    check("no malformed", v["malformed_entries"] == [])


@test("empty registry (directory exists, no files)")
def _():
    root = pathlib.Path(tempfile.mkdtemp())
    registry_dir = root / "registry"
    registry_dir.mkdir()
    v = duplicate_check.check(HASH_A, "pod_conteppei_ep051",
                              registry_dir, root / "jobs")
    check("no duplicate", v["duplicate_by_hash"] is False
          and v["match_by_source_id"] is False)
    check("registry not exists", v["registry_exists"] is False)
    check("no malformed", v["malformed_entries"] == [])


@test("hash match detected")
def _():
    root = pathlib.Path(tempfile.mkdtemp())
    registry_dir = root / "registry"
    registry_dir.mkdir()
    write_registry_entry(registry_dir, valid_entry("pod_other_ep001", HASH_A))
    v = duplicate_check.check(HASH_A, "pod_conteppei_ep051",
                              registry_dir, root / "jobs")
    check("duplicate by hash", v["duplicate_by_hash"] is True)
    check("duplicate id reported", v["duplicate_source_id"] == "pod_other_ep001")
    check("no match by id", v["match_by_source_id"] is False)


@test("source_id match detected")
def _():
    root = pathlib.Path(tempfile.mkdtemp())
    registry_dir = root / "registry"
    registry_dir.mkdir()
    write_registry_entry(registry_dir, valid_entry("pod_conteppei_ep051", HASH_B))
    v = duplicate_check.check(HASH_A, "pod_conteppei_ep051",
                              registry_dir, root / "jobs")
    check("match by id", v["match_by_source_id"] is True)
    check("registry exists", v["registry_exists"] is True)
    check("no duplicate by hash", v["duplicate_by_hash"] is False)


@test("registry exists / job exists combinations")
def _():
    root = pathlib.Path(tempfile.mkdtemp())
    registry_dir = root / "registry"
    jobs_dir = root / "jobs"
    registry_dir.mkdir()
    jobs_dir.mkdir()
    write_registry_entry(registry_dir, valid_entry("pod_conteppei_ep051", HASH_A))
    v = duplicate_check.check(HASH_A, "pod_conteppei_ep051",
                              registry_dir, jobs_dir)
    check("registry exists, job missing", v["registry_exists"] is True
          and v["job_exists"] is False)
    (jobs_dir / "pod_conteppei_ep051.cleaning_job.json").write_text(
        "{}", encoding="utf-8")
    v2 = duplicate_check.check(HASH_A, "pod_conteppei_ep051",
                               registry_dir, jobs_dir)
    check("both exist", v2["registry_exists"] is True and v2["job_exists"] is True)


@test("malformed registry entries surfaced, valid entries still matched")
def _():
    root = pathlib.Path(tempfile.mkdtemp())
    registry_dir = root / "registry"
    registry_dir.mkdir()
    write_registry_entry(registry_dir, valid_entry("pod_conteppei_ep051", HASH_A))
    (registry_dir / "bad_json.json").write_text("not json", encoding="utf-8")
    bad_schema = valid_entry("pod_bad_ep001", HASH_B)
    del bad_schema["language"]
    write_registry_entry(registry_dir, bad_schema)
    v = duplicate_check.check(HASH_A, "pod_conteppei_ep051",
                              registry_dir, root / "jobs")
    check("malformed listed", sorted(v["malformed_entries"]) == [
        "bad_json.json", "pod_bad_ep001.json"])
    check("valid entry still matched", v["duplicate_by_hash"] is True
          and v["match_by_source_id"] is True)


@test("deterministic results")
def _():
    root = pathlib.Path(tempfile.mkdtemp())
    registry_dir = root / "registry"
    registry_dir.mkdir()
    write_registry_entry(registry_dir, valid_entry("pod_other_ep001", HASH_A))
    v1 = duplicate_check.check(HASH_A, "pod_conteppei_ep051",
                               registry_dir, root / "jobs")
    v2 = duplicate_check.check(HASH_A, "pod_conteppei_ep051",
                               registry_dir, root / "jobs")
    check("identical verdicts", v1 == v2)


@test("invalid inputs raise")
def _():
    root = pathlib.Path(tempfile.mkdtemp())
    raised = False
    try:
        duplicate_check.check("", "id", root, root)
    except duplicate_check.DuplicateCheckError:
        raised = True
    check("empty sha256 raises", raised)
    raised = False
    try:
        duplicate_check.check(HASH_A, "", root, root)
    except duplicate_check.DuplicateCheckError:
        raised = True
    check("empty source_id raises", raised)


@test("read-only: no artifacts written by the query")
def _():
    root = pathlib.Path(tempfile.mkdtemp())
    registry_dir = root / "registry"
    jobs_dir = root / "jobs"
    registry_dir.mkdir()
    jobs_dir.mkdir()
    write_registry_entry(registry_dir, valid_entry("pod_conteppei_ep051", HASH_A))
    before = sorted(p.name for p in registry_dir.iterdir())
    duplicate_check.check(HASH_A, "pod_conteppei_ep051", registry_dir, jobs_dir)
    after = sorted(p.name for p in registry_dir.iterdir())
    check("registry unchanged", before == after)
    check("jobs dir still empty", sorted(p.name for p in jobs_dir.iterdir()) == [])


@test("module boundary (no forbidden imports)")
def _():
    source = pathlib.Path(SOURCE_INTAKE / "duplicate_check.py").read_text(
        encoding="utf-8")
    for forbidden in ("import clean_transcript", "import clean_subtitles",
                      "corpus_builder", "response_validator", "deepseek_client",
                      "import resolver", "import source_intake",
                      "import registry", "import cleaning_job", "import Analysis"):
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
