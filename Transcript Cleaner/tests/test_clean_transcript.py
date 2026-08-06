#!/usr/bin/env python3
"""
test_clean_transcript.py

Deterministic tests for the artifact-driven transcript cleaner.

Run:
    python "Transcript Cleaner/tests/test_clean_transcript.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
TRANSCRIPT_CLEANER = PROJECT_ROOT / "Transcript Cleaner"
SOURCE_INTAKE = PROJECT_ROOT / "Source Intake"
sys.path.insert(0, str(TRANSCRIPT_CLEANER))
sys.path.insert(0, str(SOURCE_INTAKE))

import clean_transcript as ct
import schemas
import hashing


# ============================================================
# Fixtures
# ============================================================

TRANSCRIPT = (
    "こんにちは　世界\n"
    "\n"
    "これは  テストです。\n"
    "今日は良い天気です。\n"
)


def valid_job(raw_path, output_path, **overrides):
    job = {
        "schema_version": "1",
        "source_id": "pod_conteppei_ep051",
        "raw_path": str(raw_path),
        "source_type": "clean_text",
        "cleaning_profile": "transcript_standard_v1",
        "cleaner_version": ct.PROGRAM_VERSION,
        "output_path": str(output_path),
    }
    job.update(overrides)
    return job


def write_job(tmp, job):
    job_file = tmp / f"{job['source_id']}.cleaning_job.json"
    job_file.write_text(
        json.dumps(job, ensure_ascii=False), encoding="utf-8"
    )
    return job_file


def write_registry_entry(registry_dir, job, raw_path):
    """
    Write a matching Source Registry fixture entry for a job.

    Computes the sha256 of the raw file the test already wrote, so the
    registry hash always matches the raw content unless a test tampers
    with one of them afterwards.
    """
    registry_dir = pathlib.Path(registry_dir)
    registry_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "schema_version": "1",
        "source_id": job["source_id"],
        "original_filename": pathlib.Path(raw_path).name,
        "sha256": hashing.sha256_file(raw_path),
        "source_type": job.get("source_type", "clean_text"),
        "format": pathlib.Path(raw_path).suffix.lstrip("."),
        "language": "ja",
        "cleaning_profile": job.get("cleaning_profile", "transcript_standard_v1"),
        "cleaner_version": job.get("cleaner_version", ct.PROGRAM_VERSION),
    }
    registry_file = registry_dir / f"{job['source_id']}.json"
    registry_file.write_text(
        json.dumps(entry, ensure_ascii=False), encoding="utf-8"
    )
    return registry_file


def run_cleaner(job_file, results_dir, logs_dir):
    ct.CLEANING_RESULTS = results_dir
    ct.LOG_TRANSCRIPT_CLEANER = logs_dir
    job = json.loads(job_file.read_text(encoding="utf-8"))
    registry_dir = job_file.parent / "Source Registry"
    ct.SOURCE_REGISTRY = registry_dir
    raw_path = pathlib.Path(job["raw_path"])
    if raw_path.is_file():
        write_registry_entry(registry_dir, job, raw_path)
    return ct.run(job_file)


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("1. valid transcript cleaning job")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.txt"
    out = tmp / "out" / "pod_conteppei_ep051.clean.txt"
    raw.write_text(TRANSCRIPT, encoding="utf-8")

    job = valid_job(raw, out)
    job_file = write_job(tmp, job)

    code = run_cleaner(job_file, results, logs)

    check("exit code 0", code == 0)
    check("output exists", out.is_file())

    result_file = results / "pod_conteppei_ep051.cleaning_result.json"
    check("result exists", result_file.is_file())
    result = json.loads(result_file.read_text(encoding="utf-8"))
    check("result valid schema",
          schemas.validate("cleaning_result", result) == [])
    check("success true", result["success"] is True)
    check("errors empty", result["errors"] == [])

    log_file = logs / "pod_conteppei_ep051.cleaner.log"
    check("log exists", log_file.is_file())


@test("2. BOM removal")
def _():
    text = "\ufeffこんにちは\nテスト"
    out, stats = ct.clean_transcript_text(text)
    check("bom_removed true", stats["bom_removed"] is True)
    check("no bom in output", "\ufeff" not in out)
    check("content preserved", out == "こんにちは\n\nテスト\n")


@test("3. line trimming")
def _():
    text = "  こんにちは  \n テスト  \n"
    out, stats = ct.clean_transcript_text(text)
    check("trimmed_lines", stats["trimmed_lines"] == 2)
    check("trimmed output", out == "こんにちは\n\nテスト\n")


@test("3b. utterances separated by a blank line (canonical corpus format)")
def _():
    # The Corpus Builder reconstruction gate joins sentences with "\n\n".
    # The transcript cleaner must therefore separate utterances with a
    # single blank line so the clean source is exactly reconstructible.
    out, _ = ct.clean_transcript_text("a\nb\nc")
    check("blank-line separated", out == "a\n\nb\n\nc\n")
    check("exactly one final newline",
          out.endswith("\n") and not out.endswith("\n\n"))


@test("4. ASCII repeated-space collapse")
def _():
    text = "hello   world"
    out, stats = ct.clean_transcript_text(text)
    check("collapsed", out == "hello world\n")
    check("count", stats["repeated_spaces_removed"] == 1)


@test("5. full-width Japanese space preservation")
def _():
    text = "こんにちは　世界　テスト"
    out, stats = ct.clean_transcript_text(text)
    check("full-width preserved", out == "こんにちは　世界　テスト\n")
    check("no collapse counted", stats["repeated_spaces_removed"] == 0)


@test("6. blank line collapse")
def _():
    text = "a\n\n\n\nb"
    out, stats = ct.clean_transcript_text(text)
    check("collapsed to one blank", out == "a\n\nb\n")
    check("blank_lines_removed", stats["blank_lines_removed"] == 2)


@test("7. statistics correctness")
def _():
    out, stats = ct.clean_transcript_text(TRANSCRIPT)
    check("characters_read", stats["characters_read"] == len(TRANSCRIPT))
    check("characters_written", stats["characters_written"] == len(out))
    check("bom_removed false", stats["bom_removed"] is False)
    check("trimmed_lines zero", stats["trimmed_lines"] == 0)
    check("repeated_spaces", stats["repeated_spaces_removed"] == 1)
    check("blank_lines", stats["blank_lines_removed"] == 0)
    check("all keys present",
          set(stats) == {
              "characters_read", "characters_written", "bom_removed",
              "trimmed_lines", "repeated_spaces_removed",
              "blank_lines_removed",
          })


@test("8. cleaning result creation")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.txt"
    out = tmp / "out" / "pod_conteppei_ep051.clean.txt"
    raw.write_text(TRANSCRIPT, encoding="utf-8")

    job = valid_job(raw, out)
    job_file = write_job(tmp, job)

    code = run_cleaner(job_file, results, logs)
    check("exit code 0", code == 0)

    result = json.loads(
        (results / "pod_conteppei_ep051.cleaning_result.json")
        .read_text(encoding="utf-8")
    )
    check("valid schema", schemas.validate("cleaning_result", result) == [])
    check("source_id", result["source_id"] == "pod_conteppei_ep051")
    check("cleaned_artifact", result["cleaned_artifact"] == str(out))
    check("cleaner_version", result["cleaner_version"] == ct.PROGRAM_VERSION)
    check("output_hash present", bool(result.get("output_hash")))
    check("completion_time present", bool(result.get("completion_time")))


@test("9. invalid schema rejection")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.txt"
    out = tmp / "out" / "pod_conteppei_ep051.clean.txt"
    raw.write_text(TRANSCRIPT, encoding="utf-8")

    job = valid_job(raw, out)
    del job["cleaning_profile"]
    job_file = write_job(tmp, job)

    code = run_cleaner(job_file, results, logs)
    check("exit code non-zero", code != 0)
    check("no artifact", not out.exists())

    result = json.loads(
        (results / "pod_conteppei_ep051.cleaning_result.json")
        .read_text(encoding="utf-8")
    )
    check("success false", result["success"] is False)
    check("errors populated", len(result["errors"]) > 0)
    check("no cleaned artifact", result["cleaned_artifact"] is None)


@test("10. wrong cleaner version rejection")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.txt"
    out = tmp / "out" / "pod_conteppei_ep051.clean.txt"
    raw.write_text(TRANSCRIPT, encoding="utf-8")

    job = valid_job(raw, out, cleaner_version="9.9.9")
    job_file = write_job(tmp, job)

    code = run_cleaner(job_file, results, logs)
    check("exit code non-zero", code != 0)
    check("no artifact", not out.exists())

    result = json.loads(
        (results / "pod_conteppei_ep051.cleaning_result.json")
        .read_text(encoding="utf-8")
    )
    check("success false", result["success"] is False)
    check("version error reported",
          any("cleaner_version" in e for e in result["errors"]))


@test("11. missing raw file handling")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    missing_raw = tmp / "does_not_exist.txt"
    out = tmp / "out" / "pod_conteppei_ep051.clean.txt"

    job = valid_job(missing_raw, out)
    job_file = write_job(tmp, job)

    code = run_cleaner(job_file, results, logs)
    check("exit code non-zero", code != 0)
    check("no artifact", not out.exists())

    result = json.loads(
        (results / "pod_conteppei_ep051.cleaning_result.json")
        .read_text(encoding="utf-8")
    )
    check("success false", result["success"] is False)
    check("raw not found reported",
          any("raw file not found" in e for e in result["errors"]))


@test("12. deterministic repeat execution")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    raw = tmp / "raw.txt"
    raw.write_text(TRANSCRIPT, encoding="utf-8")

    out1, stats1 = ct.clean_transcript_text(raw.read_text(encoding="utf-8"))
    out2, stats2 = ct.clean_transcript_text(raw.read_text(encoding="utf-8"))
    check("identical output", out1 == out2)
    check("identical statistics", stats1 == stats2)

    res_a = tmp / "ra"
    res_b = tmp / "rb"
    log_a = tmp / "la"
    log_b = tmp / "lb"
    out_a = tmp / "oa" / "pod_conteppei_ep051.clean.txt"
    out_b = tmp / "ob" / "pod_conteppei_ep051.clean.txt"

    job_a = valid_job(raw, out_a)
    job_b = valid_job(raw, out_b)
    code_a = run_cleaner(write_job(tmp, job_a), res_a, log_a)
    code_b = run_cleaner(write_job(tmp, job_b), res_b, log_b)

    check("both succeed", code_a == 0 and code_b == 0)
    check("byte-identical artifacts",
          out_a.read_bytes() == out_b.read_bytes())


@test("13. output-path authority")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.txt"
    custom_out = tmp / "custom" / "different_name.txt"
    raw.write_text(TRANSCRIPT, encoding="utf-8")

    job = valid_job(raw, custom_out)
    job_file = write_job(tmp, job)

    code = run_cleaner(job_file, results, logs)
    check("exit code 0", code == 0)
    check("writes to job output_path", custom_out.is_file())

    result = json.loads(
        (results / "pod_conteppei_ep051.cleaning_result.json")
        .read_text(encoding="utf-8")
    )
    check("result honors output_path",
          result["cleaned_artifact"] == str(custom_out))


@test("14. atomic write failure behavior")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.txt"
    blocker = tmp / "blocker"
    blocker.write_text("i am a file", encoding="utf-8")
    impossible_out = blocker / "sub" / "pod_conteppei_ep051.clean.txt"
    raw.write_text(TRANSCRIPT, encoding="utf-8")

    job = valid_job(raw, impossible_out)
    job_file = write_job(tmp, job)

    code = run_cleaner(job_file, results, logs)
    check("exit code non-zero", code != 0)
    check("no artifact", not impossible_out.exists())

    result_file = results / "pod_conteppei_ep051.cleaning_result.json"
    check("failure result exists", result_file.is_file())
    result = json.loads(result_file.read_text(encoding="utf-8"))
    check("success false", result["success"] is False)
    check("errors populated", len(result["errors"]) > 0)
    check("no success result without artifact",
          result["cleaned_artifact"] is None)


@test("15. forbidden writes")
def _():
    import paths as project_paths

    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.txt"
    out = tmp / "out" / "pod_conteppei_ep051.clean.txt"
    raw.write_text(TRANSCRIPT, encoding="utf-8")

    job = valid_job(raw, out)
    job_file = write_job(tmp, job)

    before_registry = sorted(x.name for x in project_paths.SOURCE_REGISTRY.iterdir())
    before_jobs = sorted(x.name for x in project_paths.CLEANING_JOBS.iterdir())
    before_dp = sorted(x.name for x in project_paths.DATA_PROCESSOR.iterdir())

    code = run_cleaner(job_file, results, logs)
    check("exit code 0", code == 0)

    after_registry = sorted(x.name for x in project_paths.SOURCE_REGISTRY.iterdir())
    after_jobs = sorted(x.name for x in project_paths.CLEANING_JOBS.iterdir())
    after_dp = sorted(x.name for x in project_paths.DATA_PROCESSOR.iterdir())

    check("no registry write", after_registry == before_registry)
    check("no cleaning jobs write", after_jobs == before_jobs)
    check("no Data Processor write", after_dp == before_dp)


@test("16. forbidden imports")
def _():
    source = pathlib.Path(ct.__file__).read_text(encoding="utf-8")
    for forbidden in ("response_validator", "corpus_builder",
                      "deepseek_client", "request builder", "job builder",
                      "process_file", "import Analysis", "from Analysis",
                      "import corpus", "import analysis",
                      "clean_subtitles"):
        check(f"no {forbidden!r}", forbidden not in source)


@test("17. missing Source Registry entry fails closed")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.txt"
    out = tmp / "out" / "pod_conteppei_ep051.clean.txt"
    raw.write_text(TRANSCRIPT, encoding="utf-8")

    job = valid_job(raw, out)
    job_file = write_job(tmp, job)

    ct.CLEANING_RESULTS = results
    ct.LOG_TRANSCRIPT_CLEANER = logs
    ct.SOURCE_REGISTRY = tmp / "Source Registry"

    code = ct.run(job_file)
    check("exit code non-zero", code != 0)
    check("no artifact", not out.exists())

    result_file = results / "pod_conteppei_ep051.cleaning_result.json"
    check("failure result exists", result_file.is_file())
    result = json.loads(result_file.read_text(encoding="utf-8"))
    check("success false", result["success"] is False)
    check("registry error reported",
          any("Source Registry" in e for e in result["errors"]))


@test("18. invalid Source Registry JSON fails closed")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.txt"
    out = tmp / "out" / "pod_conteppei_ep051.clean.txt"
    raw.write_text(TRANSCRIPT, encoding="utf-8")

    job = valid_job(raw, out)
    job_file = write_job(tmp, job)

    ct.CLEANING_RESULTS = results
    ct.LOG_TRANSCRIPT_CLEANER = logs
    registry_dir = tmp / "Source Registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    ct.SOURCE_REGISTRY = registry_dir
    (registry_dir / "pod_conteppei_ep051.json").write_text(
        "not json", encoding="utf-8"
    )

    code = ct.run(job_file)
    check("exit code non-zero", code != 0)
    check("no artifact", not out.exists())

    result = json.loads(
        (results / "pod_conteppei_ep051.cleaning_result.json")
        .read_text(encoding="utf-8")
    )
    check("success false", result["success"] is False)
    check("registry error reported",
          any("Source Registry" in e for e in result["errors"]))


@test("19. Source Registry entry missing sha256 fails closed")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.txt"
    out = tmp / "out" / "pod_conteppei_ep051.clean.txt"
    raw.write_text(TRANSCRIPT, encoding="utf-8")

    job = valid_job(raw, out)
    job_file = write_job(tmp, job)

    ct.CLEANING_RESULTS = results
    ct.LOG_TRANSCRIPT_CLEANER = logs
    registry_dir = tmp / "Source Registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    ct.SOURCE_REGISTRY = registry_dir
    (registry_dir / "pod_conteppei_ep051.json").write_text(
        json.dumps({"source_id": "pod_conteppei_ep051"}),
        encoding="utf-8",
    )

    code = ct.run(job_file)
    check("exit code non-zero", code != 0)
    check("no artifact", not out.exists())

    result = json.loads(
        (results / "pod_conteppei_ep051.cleaning_result.json")
        .read_text(encoding="utf-8")
    )
    check("success false", result["success"] is False)
    check("sha256 missing reported",
          any("sha256" in e for e in result["errors"]))


@test("20. raw content changed after registry hash fails closed")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.txt"
    out = tmp / "out" / "pod_conteppei_ep051.clean.txt"
    raw.write_text(TRANSCRIPT, encoding="utf-8")

    job = valid_job(raw, out)
    job_file = write_job(tmp, job)

    ct.CLEANING_RESULTS = results
    ct.LOG_TRANSCRIPT_CLEANER = logs
    registry_dir = tmp / "Source Registry"
    ct.SOURCE_REGISTRY = registry_dir
    write_registry_entry(registry_dir, job, raw)
    raw.write_text(TRANSCRIPT + "tampered\n", encoding="utf-8")

    code = ct.run(job_file)
    check("exit code non-zero", code != 0)
    check("no artifact", not out.exists())

    result = json.loads(
        (results / "pod_conteppei_ep051.cleaning_result.json")
        .read_text(encoding="utf-8")
    )
    check("success false", result["success"] is False)
    check("hash mismatch reported",
          any("sha256" in e and "match" in e for e in result["errors"]))


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
