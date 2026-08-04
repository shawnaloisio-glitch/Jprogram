#!/usr/bin/env python3
"""
test_request_builder.py

Deterministic tests for the artifact-driven Request Builder.

Run:
    python "Data Processor/tests/test_request_builder.py"
"""

import importlib.util
import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_PROCESSOR = PROJECT_ROOT / "Data Processor"
sys.path.insert(0, str(DATA_PROCESSOR))

# "request builder.py" contains spaces, so load it via importlib.
_spec = importlib.util.spec_from_file_location(
    "request_builder", str(DATA_PROCESSOR / "request builder.py")
)
request_builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(request_builder)
rb = request_builder


# ============================================================
# Fixtures
# ============================================================

PROMPT_TEXT = "You are a Japanese parser."  # stand-in for parser_prompt.md


def valid_job(source_id, job_number, text, **overrides):
    return {
        "source_id": source_id,
        "cleaned_artifact": f"Cleaned Archive/{source_id}.clean.txt",
        "job_number": job_number,
        "characters": len(text),
        "text": text,
    }


def write_jobs(jobs_dir, source_id, jobs):
    job_dir = jobs_dir / source_id
    job_dir.mkdir(parents=True, exist_ok=True)
    for job in jobs:
        path = job_dir / f"job_{job['job_number']:06d}.json"
        path.write_text(
            json.dumps(job, ensure_ascii=False), encoding="utf-8"
        )
    return job_dir


def setup():
    """Create isolated temp dirs and patch Request Builder globals."""
    root = pathlib.Path(tempfile.mkdtemp())
    jobs_dir = root / "jobs"
    requests_dir = root / "requests"
    rb_results_dir = root / "Request Results"
    logs_dir = root / "logs"
    for folder in (jobs_dir, requests_dir, rb_results_dir, logs_dir):
        folder.mkdir(parents=True)

    saved = (
        rb.JOBS,
        rb.REQUESTS,
        rb.REQUEST_RESULTS,
        rb.LOG_REQUEST_BUILDER,
        rb.PROMPT_FILE,
    )
    rb.JOBS = jobs_dir
    rb.REQUESTS = requests_dir
    rb.REQUEST_RESULTS = rb_results_dir
    rb.LOG_REQUEST_BUILDER = logs_dir

    prompt_file = root / "parser_prompt.md"
    prompt_file.write_text(PROMPT_TEXT, encoding="utf-8")
    rb.PROMPT_FILE = prompt_file

    return root, jobs_dir, requests_dir, rb_results_dir, saved


def restore(saved):
    (rb.JOBS, rb.REQUESTS, rb.REQUEST_RESULTS,
     rb.LOG_REQUEST_BUILDER, rb.PROMPT_FILE) = saved


def result_path(rb_results_dir, source_id):
    return rb_results_dir / f"{source_id}.request_builder_result.json"


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("1. valid job set creates requests")
def _():
    root, jobs_dir, requests_dir, rb_results, saved = setup()
    try:
        jobs = [valid_job("pod_conteppei_ep051", 1, "あいうえお。\n"),
                valid_job("pod_conteppei_ep051", 2, "かきくけこ。\n")]
        write_jobs(jobs_dir, "pod_conteppei_ep051", jobs)

        code = rb.run("pod_conteppei_ep051")
        check("exit 0", code == 0)

        request_dir = requests_dir / "pod_conteppei_ep051"
        request_files = sorted(request_dir.glob("request_*.json"))
        check("two requests created", len(request_files) == 2)
        check("naming uses 6 digits",
              request_files[0].name == "request_000001.json")

        result = json.loads(result_path(rb_results, "pod_conteppei_ep051")
                            .read_text(encoding="utf-8"))
        check("result success", result["success"] is True)
        check("result requests_created", result["requests_created"] is True)
        check("result jobs_processed", result["jobs_processed"] == 2)
    finally:
        restore(saved)


@test("2. source_id preserved through request")
def _():
    root, jobs_dir, requests_dir, rb_results, saved = setup()
    try:
        jobs = [valid_job("sub_frieren_ep001", 1, "これはテストです。\n")]
        write_jobs(jobs_dir, "sub_frieren_ep001", jobs)

        code = rb.run("sub_frieren_ep001")
        check("exit 0", code == 0)

        request = json.loads(
            (requests_dir / "sub_frieren_ep001" / "request_000001.json")
            .read_text(encoding="utf-8")
        )
        check("source_id in request",
              request["source_id"] == "sub_frieren_ep001")
        check("cleaned_artifact in request",
              request["cleaned_artifact"] == "Cleaned Archive/sub_frieren_ep001.clean.txt")
        check("compat source_name == source_id",
              request["source_name"] == "sub_frieren_ep001")
        check("compat source_file == cleaned_artifact",
              request["source_file"] == request["cleaned_artifact"])
        check("job_number", request["job_number"] == 1)
    finally:
        restore(saved)


@test("3. messages payload unchanged")
def _():
    root, jobs_dir, requests_dir, rb_results, saved = setup()
    try:
        text = "これは　日本語のテキストです。\n"
        jobs = [valid_job("pod_conteppei_ep051", 1, text)]
        write_jobs(jobs_dir, "pod_conteppei_ep051", jobs)

        code = rb.run("pod_conteppei_ep051")
        check("exit 0", code == 0)

        request = json.loads(
            (requests_dir / "pod_conteppei_ep051" / "request_000001.json")
            .read_text(encoding="utf-8")
        )
        messages = request["messages"]
        check("two messages", len(messages) == 2)
        check("system role first", messages[0]["role"] == "system")
        check("system content is effective prompt",
              messages[0]["content"] == rb.effective_prompt())
        check("user role second", messages[1]["role"] == "user")
        user_content = messages[1]["content"]
        check("user content has metadata section",
              "SOURCE METADATA:" in user_content)
        check("user content has source_id", "pod_conteppei_ep051" in user_content)
        check("user content has job_number", "1" in user_content)
        check("user content has text marker", "TEXT:\n" in user_content)
        check("user content ends with job text",
              user_content.endswith(text))
        check("user content equals user_content()",
              user_content == rb.user_content("pod_conteppei_ep051", 1, text))
    finally:
        restore(saved)


@test("4. missing --source rejected")
def _():
    root, jobs_dir, requests_dir, rb_results, saved = setup()
    try:
        raised = False
        try:
            rb.main([])
        except SystemExit:
            raised = True
        check("argparse rejects missing --source", raised)
    finally:
        restore(saved)


@test("5. missing jobs rejected")
def _():
    root, jobs_dir, requests_dir, rb_results, saved = setup()
    try:
        code = rb.run("pod_missing_ep001")
        check("exit non-zero", code != 0)
        check("no request folder",
              not (requests_dir / "pod_missing_ep001").exists())

        result = json.loads(result_path(rb_results, "pod_missing_ep001")
                            .read_text(encoding="utf-8"))
        check("success false", result["success"] is False)
        check("errors populated", len(result["errors"]) > 0)
    finally:
        restore(saved)


@test("6. invalid job rejected")
def _():
    root, jobs_dir, requests_dir, rb_results, saved = setup()
    try:
        bad = valid_job("pod_conteppei_ep051", 1, "text")
        del bad["text"]
        write_jobs(jobs_dir, "pod_conteppei_ep051", [bad])

        code = rb.run("pod_conteppei_ep051")
        check("exit non-zero", code != 0)
        check("no request created",
              not (requests_dir / "pod_conteppei_ep051").exists())

        result = json.loads(result_path(rb_results, "pod_conteppei_ep051")
                            .read_text(encoding="utf-8"))
        check("success false", result["success"] is False)
        check("errors mention text",
              any("text" in e for e in result["errors"]))
    finally:
        restore(saved)


@test("6b. mismatched source_id job rejected")
def _():
    root, jobs_dir, requests_dir, rb_results, saved = setup()
    try:
        bad = valid_job("pod_other_ep999", 1, "text")
        write_jobs(jobs_dir, "pod_conteppei_ep051", [bad])

        code = rb.run("pod_conteppei_ep051")
        check("exit non-zero", code != 0)
        check("no request created",
              not (requests_dir / "pod_conteppei_ep051").exists())
        result = json.loads(result_path(rb_results, "pod_conteppei_ep051")
                            .read_text(encoding="utf-8"))
        check("errors mention source_id mismatch",
              any("source_id" in e for e in result["errors"]))
    finally:
        restore(saved)


@test("7. deterministic repeat produces byte-identical requests")
def _():
    root, jobs_dir, requests_dir, rb_results, saved = setup()
    try:
        jobs = [valid_job("pod_conteppei_ep051", 1, "あいうえお。\n"),
                valid_job("pod_conteppei_ep051", 2, "かきくけこ。\n")]
        write_jobs(jobs_dir, "pod_conteppei_ep051", jobs)

        code_a = rb.run("pod_conteppei_ep051")
        request_dir = requests_dir / "pod_conteppei_ep051"
        snapshot = {
            p.name: p.read_bytes()
            for p in sorted(request_dir.glob("request_*.json"))
        }

        code_b = rb.run("pod_conteppei_ep051")
        after = {
            p.name: p.read_bytes()
            for p in sorted(request_dir.glob("request_*.json"))
        }

        check("both exit 0", code_a == 0 and code_b == 0)
        check("same request files", set(snapshot) == set(after))
        check("byte-identical requests", snapshot == after)
    finally:
        restore(saved)


@test("8. atomic write failure handled")
def _():
    root, jobs_dir, requests_dir, rb_results, saved = setup()
    try:
        jobs = [valid_job("pod_conteppei_ep051", 1, "text")]
        write_jobs(jobs_dir, "pod_conteppei_ep051", jobs)

        # Block the request folder with a file so writing fails.
        blocker = requests_dir / "pod_conteppei_ep051"
        blocker.write_text("i am a file", encoding="utf-8")

        code = rb.run("pod_conteppei_ep051")
        check("exit non-zero", code != 0)

        result = json.loads(result_path(rb_results, "pod_conteppei_ep051")
                            .read_text(encoding="utf-8"))
        check("success false", result["success"] is False)
        check("errors populated", len(result["errors"]) > 0)
        check("no corrupt request",
              not requests_dir.joinpath("pod_conteppei_ep051", "request_000001.json").exists())
    finally:
        restore(saved)


@test("9. forbidden writes")
def _():
    import paths as project_paths

    root, jobs_dir, requests_dir, rb_results, saved = setup()
    try:
        jobs = [valid_job("pod_conteppei_ep051", 1, "text")]
        write_jobs(jobs_dir, "pod_conteppei_ep051", jobs)

        before_registry = sorted(x.name for x in project_paths.SOURCE_REGISTRY.iterdir())
        before_jobs_intake = sorted(x.name for x in project_paths.CLEANING_JOBS.iterdir())
        before_clean_results = sorted(
            x.name for x in project_paths.CLEANING_RESULTS.iterdir())
        before_archive = sorted(
            x.name for x in project_paths.CLEANED_ARCHIVE.iterdir())

        code = rb.run("pod_conteppei_ep051")
        check("exit 0", code == 0)

        after_registry = sorted(x.name for x in project_paths.SOURCE_REGISTRY.iterdir())
        after_jobs_intake = sorted(x.name for x in project_paths.CLEANING_JOBS.iterdir())
        after_clean_results = sorted(
            x.name for x in project_paths.CLEANING_RESULTS.iterdir())
        after_archive = sorted(
            x.name for x in project_paths.CLEANED_ARCHIVE.iterdir())

        check("no registry write", after_registry == before_registry)
        check("no Cleaning Jobs write", after_jobs_intake == before_jobs_intake)
        check("no Cleaning Results write",
              after_clean_results == before_clean_results)
        check("no Cleaned Archive write", after_archive == before_archive)
    finally:
        restore(saved)


@test("10. forbidden imports")
def _():
    source = pathlib.Path(DATA_PROCESSOR / "request builder.py").read_text(
        encoding="utf-8")
    import_lines = "\n".join(
        ln for ln in source.splitlines()
        if ln.lstrip().startswith("import ") or ln.lstrip().startswith("from ")
    )
    for forbidden in ("deepseek_client", "corpus_builder",
                      "response_validator", "process_file", "job builder",
                      "Analysis", "corpus", "analysis", "urllib", "http",
                      "requests"):
        check(f"no {forbidden!r}", forbidden not in import_lines)


@test("10b. request_builder_result writer boundary")
def _():
    source = pathlib.Path(DATA_PROCESSOR / "request_builder_result.py").read_text(
        encoding="utf-8")
    import_lines = "\n".join(
        ln for ln in source.splitlines()
        if ln.lstrip().startswith("import ") or ln.lstrip().startswith("from ")
    )
    for forbidden in ("deepseek_client", "corpus_builder",
                      "response_validator", "Analysis", "schemas", "paths",
                      "project_config", "request builder", "urllib", "http"):
        check(f"no {forbidden!r}", forbidden not in import_lines)


@test("11. resume: valid existing request preserved")
def _():
    root, jobs_dir, requests_dir, rb_results, saved = setup()
    try:
        text = "これはテストです。\n"
        jobs = [valid_job("pod_conteppei_ep051", 1, text)]
        write_jobs(jobs_dir, "pod_conteppei_ep051", jobs)

        code = rb.run("pod_conteppei_ep051")
        check("first run exit 0", code == 0)
        request_path = requests_dir / "pod_conteppei_ep051" / "request_000001.json"
        first_bytes = request_path.read_bytes()

        code = rb.run("pod_conteppei_ep051")
        check("second run exit 0", code == 0)
        check("request preserved byte-identical",
              request_path.read_bytes() == first_bytes)

        result = json.loads(result_path(rb_results, "pod_conteppei_ep051")
                            .read_text(encoding="utf-8"))
        check("result success", result["success"] is True)
        check("requests_created true (present)",
              result["requests_created"] is True)
    finally:
        restore(saved)


@test("12. invalid existing request rebuilt")
def _():
    root, jobs_dir, requests_dir, rb_results, saved = setup()
    try:
        text = "これはテストです。\n"
        jobs = [valid_job("pod_conteppei_ep051", 1, text)]
        write_jobs(jobs_dir, "pod_conteppei_ep051", jobs)

        # Write a corrupted request artifact with wrong lineage.
        request_dir = requests_dir / "pod_conteppei_ep051"
        request_dir.mkdir(parents=True)
        bad_request = {
            "source_id": "pod_wrong_ep999",
            "job_number": 7,
            "messages": [{"role": "system", "content": "x"},
                         {"role": "user", "content": "WRONG"}],
        }
        (request_dir / "request_000001.json").write_text(
            json.dumps(bad_request, ensure_ascii=False), encoding="utf-8")

        code = rb.run("pod_conteppei_ep051")
        check("exit 0", code == 0)

        rebuilt = json.loads(
            (request_dir / "request_000001.json")
            .read_text(encoding="utf-8")
        )
        check("rebuilt source_id", rebuilt["source_id"] == "pod_conteppei_ep051")
        check("rebuilt job_number", rebuilt["job_number"] == 1)
        check("rebuilt text",
              rebuilt["messages"][1]["content"]
              == rb.user_content("pod_conteppei_ep051", 1, text))
    finally:
        restore(saved)


@test("12b. request_builder_result schema round-trip")
def _():
    import request_builder_result as rbr
    result = rbr.build_result(
        source_id="pod_conteppei_ep051",
        success=True,
        requests_created=True,
        jobs_processed=2,
        errors=[],
        completion_time="2026-08-01 12:00:00",
    )
    check("valid", rbr.validate_result(result) == [])
    path = pathlib.Path(tempfile.mkdtemp()) / "x.json"
    rbr.write_result(path, result)
    check("round-trips",
          json.loads(path.read_text(encoding="utf-8")) == result)

    bad = rbr.build_result(
        source_id="pod_conteppei_ep051",
        success=True,
        requests_created=True,
        jobs_processed="two",
        errors=[],
    )
    check("invalid rejected", rbr.validate_result(bad) != [])


@test("13. Flash model disables expression extraction in the prompt")
def _():
    import project_config as pc
    check("flash expressions disabled",
          pc.expressions_enabled("deepseek-v4-flash") is False)
    prompt = rb.effective_prompt()
    check("directive appended for flash",
          "EXPRESSION EXTRACTION: DISABLED" in prompt)
    check("base expressions section retained",
          "## EXPRESSIONS" in prompt)


@test("13b. capable models keep expressions enabled without change")
def _():
    import project_config as pc
    check("future model enabled by default",
          pc.expressions_enabled("deepseek-reasoner") is True)
    check("gpt enabled by default",
          pc.expressions_enabled("gpt-5") is True)
    check("claude enabled by default",
          pc.expressions_enabled("claude-4") is True)


@test("13c. request carries the disabled directive for flash")
def _():
    root, jobs_dir, requests_dir, rb_results, saved = setup()
    try:
        jobs = [valid_job("pod_conteppei_ep051", 1, "text")]
        write_jobs(jobs_dir, "pod_conteppei_ep051", jobs)
        code = rb.run("pod_conteppei_ep051")
        check("exit 0", code == 0)
        request = json.loads(
            (requests_dir / "pod_conteppei_ep051" / "request_000001.json")
            .read_text(encoding="utf-8")
        )
        system = request["messages"][0]["content"]
        check("directive present", "EXPRESSION EXTRACTION: DISABLED" in system)
        check("empty-array instruction present", '"expressions": []' in system)
    finally:
        restore(saved)


@test("14. user payload contains source_id and job_number")
def _():
    content = rb.user_content("pod_conteppei_ep051", 1, "これは　本文。\n")
    check("metadata header", "SOURCE METADATA:" in content)
    check("source_id present", "source_id: pod_conteppei_ep051" in content)
    check("job_number present", "job_number: 1" in content)
    check("text marker", "TEXT:\n" in content)
    check("text preserved", content.endswith("これは　本文。\n"))
    # Metadata section appears before the text.
    check("metadata before text",
          content.index("source_id:") < content.index("TEXT:"))


@test("15. user_content is used in the built request")
def _():
    root, jobs_dir, requests_dir, rb_results, saved = setup()
    try:
        text = "これは　日本語のテキストです。\n"
        jobs = [valid_job("pod_conteppei_ep051", 1, text)]
        write_jobs(jobs_dir, "pod_conteppei_ep051", jobs)
        code = rb.run("pod_conteppei_ep051")
        check("exit 0", code == 0)
        request = json.loads(
            (requests_dir / "pod_conteppei_ep051" / "request_000001.json")
            .read_text(encoding="utf-8")
        )
        user_content = request["messages"][1]["content"]
        check("user content matches user_content()",
              user_content == rb.user_content("pod_conteppei_ep051", 1, text))
        check("payload has source_id line",
              f"source_id: pod_conteppei_ep051" in user_content)
        check("payload has job_number line", "job_number: 1" in user_content)
    finally:
        restore(saved)


@test("16. request top-level metadata fields unchanged")
def _():
    root, jobs_dir, requests_dir, rb_results, saved = setup()
    try:
        text = "これは　日本語のテキストです。\n"
        jobs = [valid_job("pod_conteppei_ep051", 1, text)]
        write_jobs(jobs_dir, "pod_conteppei_ep051", jobs)
        code = rb.run("pod_conteppei_ep051")
        check("exit 0", code == 0)
        request = json.loads(
            (requests_dir / "pod_conteppei_ep051" / "request_000001.json")
            .read_text(encoding="utf-8")
        )
        check("source_id", request["source_id"] == "pod_conteppei_ep051")
        check("job_number", request["job_number"] == 1)
        check("source_name", request["source_name"] == "pod_conteppei_ep051")
        check("source_file",
              request["source_file"] == "Cleaned Archive/pod_conteppei_ep051.clean.txt")
        check("cleaned_artifact",
              request["cleaned_artifact"] == request["source_file"])
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
