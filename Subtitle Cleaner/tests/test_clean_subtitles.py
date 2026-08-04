#!/usr/bin/env python3
"""
test_clean_subtitles.py

Deterministic tests for the artifact-driven subtitle cleaner.

Run:
    python "Subtitle Cleaner/tests/test_clean_subtitles.py"
"""

import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SUBTITLE_CLEANER = PROJECT_ROOT / "Subtitle Cleaner"
SOURCE_INTAKE = PROJECT_ROOT / "Source Intake"
sys.path.insert(0, str(SUBTITLE_CLEANER))
sys.path.insert(0, str(SOURCE_INTAKE))

import clean_subtitles as cs
import schemas


# ============================================================
# Fixtures
# ============================================================

SRT = (
    "1\n"
    "00:00:00,000 --> 00:00:02,000\n"
    "こんにちは世界\n"
    "\n"
    "2\n"
    "00:00:02,500 --> 00:00:05,000\n"
    "これはテストです。\n"
    "\n"
    "3\n"
    "00:00:05,500 --> 00:00:08,000\n"
    "ありがとう。\n"
)

SRT_EXPECTED = (
    "こんにちは世界\n"
    "\n"
    "これはテストです。\n"
    "\n"
    "ありがとう。\n"
)


def valid_job(raw_path, output_path, **overrides):
    job = {
        "schema_version": "1",
        "source_id": "sub_conteppei_ep051",
        "raw_path": str(raw_path),
        "source_type": "anime_subtitle",
        "cleaning_profile": "subtitle_standard_v1",
        "cleaner_version": cs.PROGRAM_VERSION,
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


def run_cleaner(job_file, results_dir, logs_dir):
    cs.CLEANING_RESULTS = results_dir
    cs.LOG_SUBTITLE_CLEANER = logs_dir
    return cs.run(job_file)


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("1. valid subtitle cleaning job")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.srt"
    out = tmp / "out" / "sub_conteppei_ep051.clean.txt"
    raw.write_text(SRT, encoding="utf-8")

    job = valid_job(raw, out)
    job_file = write_job(tmp, job)

    code = run_cleaner(job_file, results, logs)

    check("exit code 0", code == 0)
    check("output exists", out.is_file())
    check("output correct", out.read_text(encoding="utf-8") == SRT_EXPECTED)

    result_file = results / "sub_conteppei_ep051.cleaning_result.json"
    check("result exists", result_file.is_file())
    result = json.loads(result_file.read_text(encoding="utf-8"))
    check("result valid schema", schemas.validate("cleaning_result", result) == [])
    check("success true", result["success"] is True)
    check("errors empty", result["errors"] == [])

    log_file = logs / "sub_conteppei_ep051.cleaner.log"
    check("log exists", log_file.is_file())


@test("2. BOM handling")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "bom.srt"
    out = tmp / "out" / "sub_conteppei_ep051.clean.txt"
    raw.write_text("\ufeff" + SRT, encoding="utf-8")

    job = valid_job(raw, out)
    job_file = write_job(tmp, job)

    code = run_cleaner(job_file, results, logs)
    check("exit code 0", code == 0)
    check("output correct", out.read_text(encoding="utf-8") == SRT_EXPECTED)

    result = json.loads(
        (results / "sub_conteppei_ep051.cleaning_result.json")
        .read_text(encoding="utf-8")
    )
    check("bom_removed true", result["statistics"]["bom_removed"] is True)


@test("3. subtitle number removal")
def _():
    out, stats = cs.clean_subtitle_text(SRT)
    check("numbers removed", stats["subtitle_numbers_removed"] == 3)
    check("no number lines in output", "1\n" not in out)
    check("no timecodes in output", "-->" not in out)


@test("4. timecode removal")
def _():
    out, stats = cs.clean_subtitle_text(SRT)
    check("timecodes removed", stats["timecodes_removed"] == 3)
    check("no arrow in output", "-->" not in out)
    check("dot timecode handled", stats["timecodes_removed"] == 3)


@test("5. blank collapse")
def _():
    srt_extra_blanks = SRT.replace("\n\n2\n", "\n\n\n2\n")
    out, stats = cs.clean_subtitle_text(srt_extra_blanks)
    check("blank_lines_removed", stats["blank_lines_removed"] == 1)
    check("single separator preserved", "\n\n" in out and "\n\n\n" not in out)


@test("6. statistics correctness")
def _():
    out, stats = cs.clean_subtitle_text(SRT)
    check("characters_read", stats["characters_read"] == len(SRT))
    check("characters_written", stats["characters_written"] == len(out))
    check("bom_removed false", stats["bom_removed"] is False)
    check("trimmed_lines zero", stats["trimmed_lines"] == 0)
    check("numbers", stats["subtitle_numbers_removed"] == 3)
    check("timecodes", stats["timecodes_removed"] == 3)
    check("blanks", stats["blank_lines_removed"] == 0)
    check("all keys present",
          set(stats) == {
              "characters_read", "characters_written", "bom_removed",
              "trimmed_lines", "subtitle_numbers_removed",
              "timecodes_removed", "blank_lines_removed",
          })


@test("7. cleaning result creation")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.srt"
    out = tmp / "out" / "sub_conteppei_ep051.clean.txt"
    raw.write_text(SRT, encoding="utf-8")

    job = valid_job(raw, out)
    job_file = write_job(tmp, job)

    code = run_cleaner(job_file, results, logs)
    check("exit code 0", code == 0)

    result = json.loads(
        (results / "sub_conteppei_ep051.cleaning_result.json")
        .read_text(encoding="utf-8")
    )
    check("valid schema", schemas.validate("cleaning_result", result) == [])
    check("source_id", result["source_id"] == "sub_conteppei_ep051")
    check("cleaned_artifact", result["cleaned_artifact"] == str(out))
    check("cleaner_version", result["cleaner_version"] == cs.PROGRAM_VERSION)
    check("output_hash present", bool(result.get("output_hash")))
    check("completion_time present", bool(result.get("completion_time")))


@test("8. invalid job schema")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.srt"
    out = tmp / "out" / "sub_conteppei_ep051.clean.txt"
    raw.write_text(SRT, encoding="utf-8")

    job = valid_job(raw, out)
    del job["cleaning_profile"]
    job_file = write_job(tmp, job)

    code = run_cleaner(job_file, results, logs)
    check("exit code non-zero", code != 0)
    check("no artifact", not out.exists())

    result_file = results / "sub_conteppei_ep051.cleaning_result.json"
    check("failure result exists", result_file.is_file())
    result = json.loads(result_file.read_text(encoding="utf-8"))
    check("success false", result["success"] is False)
    check("errors populated", len(result["errors"]) > 0)
    check("no cleaned artifact", result["cleaned_artifact"] is None)


@test("9. wrong cleaner version")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.srt"
    out = tmp / "out" / "sub_conteppei_ep051.clean.txt"
    raw.write_text(SRT, encoding="utf-8")

    job = valid_job(raw, out, cleaner_version="9.9.9")
    job_file = write_job(tmp, job)

    code = run_cleaner(job_file, results, logs)
    check("exit code non-zero", code != 0)
    check("no artifact", not out.exists())

    result = json.loads(
        (results / "sub_conteppei_ep051.cleaning_result.json")
        .read_text(encoding="utf-8")
    )
    check("success false", result["success"] is False)
    check("version error reported",
          any("cleaner_version" in e for e in result["errors"]))


@test("10. missing raw file")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    missing_raw = tmp / "does_not_exist.srt"
    out = tmp / "out" / "sub_conteppei_ep051.clean.txt"

    job = valid_job(missing_raw, out)
    job_file = write_job(tmp, job)

    code = run_cleaner(job_file, results, logs)
    check("exit code non-zero", code != 0)
    check("no artifact", not out.exists())

    result = json.loads(
        (results / "sub_conteppei_ep051.cleaning_result.json")
        .read_text(encoding="utf-8")
    )
    check("success false", result["success"] is False)
    check("raw not found reported",
          any("raw file not found" in e for e in result["errors"]))


@test("11. deterministic repeat execution")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    raw = tmp / "raw.srt"
    raw.write_text(SRT, encoding="utf-8")

    out1, stats1 = cs.clean_subtitle_text(raw.read_text(encoding="utf-8"))
    out2, stats2 = cs.clean_subtitle_text(raw.read_text(encoding="utf-8"))
    check("identical output", out1 == out2)
    check("identical statistics", stats1 == stats2)

    # Full artifact run twice produces identical output bytes.
    code_a = 0
    code_b = 0
    res_a = tmp / "ra"
    res_b = tmp / "rb"
    log_a = tmp / "la"
    log_b = tmp / "lb"
    out_a = tmp / "oa" / "sub_conteppei_ep051.clean.txt"
    out_b = tmp / "ob" / "sub_conteppei_ep051.clean.txt"

    job_a = valid_job(raw, out_a)
    job_b = valid_job(raw, out_b)
    code_a = run_cleaner(write_job(tmp, job_a), res_a, log_a)
    code_b = run_cleaner(write_job(tmp, job_b), res_b, log_b)

    check("both succeed", code_a == 0 and code_b == 0)
    check("byte-identical artifacts",
          out_a.read_bytes() == out_b.read_bytes())


@test("12. output path authority")
def _():
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.srt"
    custom_out = tmp / "custom" / "different_name.txt"
    raw.write_text(SRT, encoding="utf-8")

    job = valid_job(raw, custom_out)
    job_file = write_job(tmp, job)

    code = run_cleaner(job_file, results, logs)
    check("exit code 0", code == 0)
    check("writes to job output_path", custom_out.is_file())
    check("content correct",
          custom_out.read_text(encoding="utf-8") == SRT_EXPECTED)

    result = json.loads(
        (results / "sub_conteppei_ep051.cleaning_result.json")
        .read_text(encoding="utf-8")
    )
    check("result honors output_path",
          result["cleaned_artifact"] == str(custom_out))


@test("13. atomic write failure behavior")
def _():
    # output_path points into a directory that cannot be created
    # (parent path is a file), forcing the artifact write to fail.
    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.srt"
    blocker = tmp / "blocker"
    blocker.write_text("i am a file", encoding="utf-8")
    impossible_out = blocker / "sub" / "sub_conteppei_ep051.clean.txt"
    raw.write_text(SRT, encoding="utf-8")

    job = valid_job(raw, impossible_out)
    job_file = write_job(tmp, job)

    code = run_cleaner(job_file, results, logs)
    check("exit code non-zero", code != 0)
    check("no artifact", not impossible_out.exists())

    result_file = results / "sub_conteppei_ep051.cleaning_result.json"
    check("failure result exists", result_file.is_file())
    result = json.loads(result_file.read_text(encoding="utf-8"))
    check("success false", result["success"] is False)
    check("errors populated", len(result["errors"]) > 0)
    check("no success result without artifact", result["cleaned_artifact"] is None)


@test("14. forbidden writes")
def _():
    import paths as project_paths

    tmp = pathlib.Path(tempfile.mkdtemp())
    results = tmp / "results"
    logs = tmp / "logs"
    raw = tmp / "raw.srt"
    out = tmp / "out" / "sub_conteppei_ep051.clean.txt"
    raw.write_text(SRT, encoding="utf-8")

    job = valid_job(raw, out)
    job_file = write_job(tmp, job)

    before = {
        p: sorted(x.name for x in project_paths.SOURCE_REGISTRY.iterdir())
        for p in (project_paths.SOURCE_REGISTRY,)
    }
    before_jobs = sorted(x.name for x in project_paths.CLEANING_JOBS.iterdir())
    before_dp = sorted(
        x.name for x in project_paths.DATA_PROCESSOR.iterdir()
    )

    code = run_cleaner(job_file, results, logs)
    check("exit code 0", code == 0)

    after = sorted(x.name for x in project_paths.SOURCE_REGISTRY.iterdir())
    after_jobs = sorted(x.name for x in project_paths.CLEANING_JOBS.iterdir())
    after_dp = sorted(x.name for x in project_paths.DATA_PROCESSOR.iterdir())

    check("no registry write", after == list(before.values())[0])
    check("no cleaning jobs write", after_jobs == before_jobs)
    check("no Data Processor write", after_dp == before_dp)


@test("15. forbidden imports")
def _():
    source = pathlib.Path(cs.__file__).read_text(encoding="utf-8")
    for forbidden in ("response_validator", "corpus_builder",
                      "deepseek_client", "request builder", "job builder",
                      "process_file", "import Analysis", "from Analysis",
                      "import corpus", "import analysis"):
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
