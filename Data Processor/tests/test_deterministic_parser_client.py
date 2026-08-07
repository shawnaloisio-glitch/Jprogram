#!/usr/bin/env python3
"""
test_deterministic_parser_client.py

Deterministic tests for the Deterministic Parser Client (the transport
module that drives deterministic_parser.py through the job-in /
response-out contract). All path globals are sandboxed into temp dirs;
the real workspace is never touched.

Run (must use the project venv; spacy/ginza are not installed globally):
    "Jprogram/.venv/Scripts/python.exe" "Data Processor/tests/test_deterministic_parser_client.py"
"""

import json
import pathlib
import shutil
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_PROCESSOR = PROJECT_ROOT / "Data Processor"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(DATA_PROCESSOR))

import deterministic_parser as dp
import deterministic_parser_client as dpc
import processing_result as pr
import response_validator as rv

SOURCE = "pod_conteppei_ep051"


def job_data(source_id, job_number, text):
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
        path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    return job_dir


def setup():
    """Create isolated temp dirs and patch Deterministic Parser Client globals."""
    root = pathlib.Path(tempfile.mkdtemp())
    jobs_dir = root / "jobs"
    responses_dir = root / "responses"
    processing_dir = root / "Processing Results"
    logs_dir = root / "logs"
    for folder in (jobs_dir, responses_dir, processing_dir, logs_dir):
        folder.mkdir(parents=True)

    saved = (
        dpc.JOBS,
        dpc.RESPONSES,
        dpc.PROCESSING_RESULTS,
        dpc.LOG_DETERMINISTIC_PARSER_CLIENT,
    )
    dpc.JOBS = jobs_dir
    dpc.RESPONSES = responses_dir
    dpc.PROCESSING_RESULTS = processing_dir
    dpc.LOG_DETERMINISTIC_PARSER_CLIENT = logs_dir
    return root, jobs_dir, responses_dir, processing_dir, saved


def restore(saved):
    (dpc.JOBS, dpc.RESPONSES, dpc.PROCESSING_RESULTS,
     dpc.LOG_DETERMINISTIC_PARSER_CLIENT) = saved


def result_path(processing_dir, source_id):
    return processing_dir / f"{source_id}.processing_result.json"


def load_result(processing_dir, source_id):
    return json.loads(
        result_path(processing_dir, source_id).read_text(encoding="utf-8")
    )


def response_path(responses_dir, source_id, job_number):
    return responses_dir / source_id / f"response_{job_number:06d}.json"


def sample_jobs():
    return [
        job_data(SOURCE, 1, "犬が走る。\n"),
        job_data(SOURCE, 2, "食べてください。\n"),
    ]


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("1. --source CLI invocation")
def _():
    root, jobs_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_jobs(jobs_dir, SOURCE, sample_jobs())

        code = dpc.main(["--source", SOURCE])
        check("exit 0", code == 0)
        check("response 1 created", response_path(responses_dir, SOURCE, 1).is_file())
        check("response 2 created", response_path(responses_dir, SOURCE, 2).is_file())
        check("processing result created",
              result_path(processing_dir, SOURCE).is_file())
    finally:
        restore(saved)


@test("1b. missing --source rejected")
def _():
    root, jobs_dir, responses_dir, processing_dir, saved = setup()
    try:
        raised = False
        try:
            dpc.main([])
        except SystemExit:
            raised = True
        check("argparse rejects missing --source", raised)
    finally:
        restore(saved)


@test("2. job discovery is deterministic")
def _():
    root, jobs_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_jobs(jobs_dir, SOURCE,
                   [job_data(SOURCE, 2, "B。\n"), job_data(SOURCE, 1, "A。\n")])
        files = dpc.job_files_for(SOURCE)
        names = [f.name for f in files]
        check("sorted deterministically",
              names == ["job_000001.json", "job_000002.json"], str(names))
        check("missing source returns empty", dpc.job_files_for("nope") == [])
    finally:
        restore(saved)


@test("3. normal run produces exactly 2 responses matching parse_job")
def _():
    root, jobs_dir, responses_dir, processing_dir, saved = setup()
    try:
        jobs = sample_jobs()
        write_jobs(jobs_dir, SOURCE, jobs)

        code = dpc.run(SOURCE, timestamp_fn=lambda: "2026-08-01 12:00:00")
        check("exit 0", code == 0)

        response_dir = responses_dir / SOURCE
        names = sorted(p.name for p in response_dir.iterdir())
        check("exactly two response files",
              names == ["response_000001.json", "response_000002.json"], str(names))

        for job in jobs:
            parsed = dp.parse_job(job["source_id"], job["job_number"], job["text"])
            saved_text = response_path(responses_dir, SOURCE,
                                       job["job_number"]).read_text(encoding="utf-8")
            check(f"response {job['job_number']} matches parse_job directly",
                  json.loads(saved_text) == parsed)
    finally:
        restore(saved)


@test("4. processing result is correctly shaped")
def _():
    root, jobs_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_jobs(jobs_dir, SOURCE, sample_jobs())

        code = dpc.run(SOURCE, timestamp_fn=lambda: "2026-08-01 12:00:00")
        check("exit 0", code == 0)

        result = load_result(processing_dir, SOURCE)
        check("schema valid", pr.validate_result(result) == [],
              str(pr.validate_result(result)))
        check("requests_processed", result["requests_processed"] == 2)
        check("producer identity recorded", result["model"] == dpc.PRODUCER_ID)
        check("not the deepseek model", result["model"] != "deepseek-chat")
        check("totals all int zero", result["totals"] ==
              {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            check(f"totals.{key} is an int not None",
                  isinstance(result["totals"][key], int)
                  and not isinstance(result["totals"][key], bool))
        check("two job entries", len(result["jobs"]) == 2)
        for entry in result["jobs"]:
            check("per-job status completed", entry["status"] == "completed")
            check("per-job tokens null", entry["prompt_tokens"] is None
                  and entry["completion_tokens"] is None
                  and entry["total_tokens"] is None)
            check("per-job job_number present",
                  entry["job_number"] in (1, 2))
    finally:
        restore(saved)


@test("5. resume skips a pre-existing response without overwriting")
def _():
    root, jobs_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_jobs(jobs_dir, SOURCE, sample_jobs())
        # Pre-existing (stale) response for job 1.
        stale = json.dumps({"stale": True}, ensure_ascii=False)
        response_path(responses_dir, SOURCE, 1).parent.mkdir(parents=True)
        response_path(responses_dir, SOURCE, 1).write_text(stale, encoding="utf-8")

        code = dpc.run(SOURCE, timestamp_fn=lambda: "2026-08-01 12:00:00")
        check("exit 0", code == 0)

        check("existing response not overwritten",
              response_path(responses_dir, SOURCE, 1).read_text(encoding="utf-8")
              == stale)
        check("missing response created",
              response_path(responses_dir, SOURCE, 2).is_file())

        result = load_result(processing_dir, SOURCE)
        check("two completed entries", len(result["jobs"]) == 2
              and all(e["status"] == "completed" for e in result["jobs"]))
        check("skipped entry attempts 0",
              result["jobs"][0]["attempts"] == 0)

        log_dir = dpc.LOG_DETERMINISTIC_PARSER_CLIENT
        logs = list(log_dir.glob("deterministic_parser_client_*.log"))
        check("log written", len(logs) >= 1)
        log_text = logs[-1].read_text(encoding="utf-8")
        check("log records skip of job 1", "SKIP job_000001.json" in log_text)
        check("log records process of job 2", "PROCESSED job_000002.json" in log_text)
    finally:
        restore(saved)


@test("6. every response passes response_validator with zero fatal errors")
def _():
    root, jobs_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_jobs(jobs_dir, SOURCE, sample_jobs())

        code = dpc.run(SOURCE, timestamp_fn=lambda: "2026-08-01 12:00:00")
        check("exit 0", code == 0)

        for job_number in (1, 2):
            response = json.loads(
                response_path(responses_dir, SOURCE, job_number).read_text(
                    encoding="utf-8")
            )
            v = rv.validate_response(
                response,
                expected_source_name=SOURCE,
                expected_job_number=job_number,
            )
            check(f"response {job_number} valid", v["valid"] is True, str(v["errors"]))
            check(f"response {job_number} no fatal errors",
                  v["summary"]["fatal_errors"] == 0, str(v["errors"]))
            check(f"response {job_number} no identity mismatches",
                  v["summary"]["identity_mismatches"] == 0)
            check(f"response {job_number} no partition mismatches",
                  v["summary"]["partition_mismatches"] == 0)
    finally:
        restore(saved)


@test("7. zero job files returns a non-zero exit code")
def _():
    root, jobs_dir, responses_dir, processing_dir, saved = setup()
    try:
        code = dpc.run("pod_unknown_source")
        check("exit non-zero", code != 0)
        check("no responses dir created", not (responses_dir / "pod_unknown_source").exists())
        result = load_result(processing_dir, "pod_unknown_source")
        check("failure recorded", result["requests_processed"] == 0)
        check("failure totals int zero", result["totals"] ==
              {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    finally:
        restore(saved)


@test("7b. missing source_id returns non-zero without writing artifacts")
def _():
    root, jobs_dir, responses_dir, processing_dir, saved = setup()
    try:
        code = dpc.run("   ")
        check("exit non-zero", code != 0)
        check("no processing result", not result_path(processing_dir, SOURCE).exists())
    finally:
        restore(saved)


@test("8. malformed job JSON fails")
def _():
    root, jobs_dir, responses_dir, processing_dir, saved = setup()
    try:
        job_dir = jobs_dir / SOURCE
        job_dir.mkdir(parents=True)
        (job_dir / "job_000001.json").write_text("{not json", encoding="utf-8")

        code = dpc.run(SOURCE)
        check("exit non-zero", code != 0)
        check("no response created", not (responses_dir / SOURCE).exists())
        result = load_result(processing_dir, SOURCE)
        check("failure recorded", result["requests_processed"] == 0)
    finally:
        restore(saved)


@test("9. source_id lineage mismatch rejected")
def _():
    root, jobs_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_jobs(jobs_dir, SOURCE, [job_data("pod_wrong_ep999", 1, "犬が走る。\n")])
        code = dpc.run(SOURCE)
        check("exit non-zero", code != 0)
        check("no response created", not (responses_dir / SOURCE).exists())
        result = load_result(processing_dir, SOURCE)
        check("failure recorded", result["requests_processed"] == 0)
    finally:
        restore(saved)


@test("10. atomic writes leave no temp files")
def _():
    root, jobs_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_jobs(jobs_dir, SOURCE, sample_jobs())

        code = dpc.run(SOURCE)
        check("exit 0", code == 0)

        response_dir = responses_dir / SOURCE
        check("no response .tmp",
              not any(p.name.endswith(".tmp") for p in response_dir.iterdir()))
        check("no result .tmp",
              not result_path(processing_dir, SOURCE).with_name(
                  result_path(processing_dir, SOURCE).name + ".tmp").exists())
    finally:
        restore(saved)


@test("11. deterministic output with fixed timestamp")
def _():
    root, jobs_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_jobs(jobs_dir, SOURCE, sample_jobs())

        results = []
        for _ in range(2):
            code = dpc.run(SOURCE, timestamp_fn=lambda: "2026-08-01 12:00:00")
            check("run exit 0", code == 0)
            results.append(
                result_path(processing_dir, SOURCE).read_bytes()
            )
            shutil.rmtree(responses_dir / SOURCE)
            result_path(processing_dir, SOURCE).unlink()

        check("byte-identical with fixed timestamp", results[0] == results[1])
    finally:
        restore(saved)


@test("12. forbidden imports")
def _():
    source = pathlib.Path(DATA_PROCESSOR / "deterministic_parser_client.py").read_text(
        encoding="utf-8")
    import_lines = "\n".join(
        ln for ln in source.splitlines()
        if ln.lstrip().startswith("import ") or ln.lstrip().startswith("from ")
    )
    for forbidden in ("corpus_builder", "response_validator",
                      "deepseek_client", "production_manager",
                      "job builder", "request builder", "Analysis",
                      "openai", "requests", "urllib"):
        check(f"no {forbidden!r}", forbidden not in import_lines)


@test("13. no writes to the real workspace")
def _():
    import paths as project_paths

    root, jobs_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_jobs(jobs_dir, SOURCE, sample_jobs())

        before = {
            p: sorted(x.name for x in p.iterdir())
            for p in (project_paths.SOURCE_REGISTRY,
                      project_paths.CLEANING_JOBS,
                      project_paths.CLEANING_RESULTS,
                      project_paths.CLEANED_ARCHIVE,
                      project_paths.JSONL,
                      project_paths.REQUESTS,
                      project_paths.JOB_RESULTS)
        }
        code = dpc.run(SOURCE)
        check("exit 0", code == 0)
        after = {
            p: sorted(x.name for x in p.iterdir())
            for p in before
        }
        for folder in before:
            check(f"no write to {folder.name}", after[folder] == before[folder])
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
