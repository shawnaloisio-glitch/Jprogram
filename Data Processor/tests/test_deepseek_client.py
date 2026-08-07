#!/usr/bin/env python3
"""
test_deepseek_client.py

Deterministic tests for the single-source artifact-driven DeepSeek Client.

The API transport is mocked; no real network call is made.

Run:
    python "Data Processor/tests/test_deepseek_client.py"
"""

import importlib.util
import json
import os
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_PROCESSOR = PROJECT_ROOT / "Data Processor"
sys.path.insert(0, str(DATA_PROCESSOR))

_spec = importlib.util.spec_from_file_location(
    "deepseek_client", str(DATA_PROCESSOR / "deepseek_client.py")
)
deepseek_client = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(deepseek_client)
dsc = deepseek_client


PROMPT = "parser prompt"
FIXED_TIME = "2026-08-01 12:00:00"


def valid_request(source_id, job_number, text="text"):
    return {
        "source_id": source_id,
        "cleaned_artifact": f"Cleaned Archive/{source_id}.clean.txt",
        "job_number": job_number,
        "prompt_version": "1.0",
        "source_file": f"Cleaned Archive/{source_id}.clean.txt",
        "source_name": source_id,
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": text},
        ],
    }


def write_requests(requests_dir, source_id, requests):
    request_dir = requests_dir / source_id
    request_dir.mkdir(parents=True, exist_ok=True)
    for request in requests:
        path = request_dir / f"request_{request['job_number']:06d}.json"
        path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
    return request_dir


def api_response(model="deepseek-v4-flash", prompt_tokens=10,
                 completion_tokens=5, total_tokens=15,
                 finish_reason="stop"):
    return json.dumps({
        "model": model,
        "choices": [{"finish_reason": finish_reason,
                     "message": {"content": "{}"}}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
    })


class FakeSender:
    """Replaces send_with_retry with a scripted, successful sender."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, api_key, payload):
        self.calls.append(payload)
        text = self.responses.pop(0)
        return {
            "success": True,
            "text": text,
            "http_status": 200,
            "attempts": 1,
            "reason": "",
        }


class FakeFailSender:
    def __init__(self, result):
        self.result = result

    def __call__(self, api_key, payload):
        return dict(self.result)


class RaisingSender:
    def __init__(self, exc):
        self.exc = exc

    def __call__(self, api_key, payload):
        raise self.exc


class KeyRecordingSender:
    """Replaces send_with_retry and records the api_key it was given."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.keys = []

    def __call__(self, api_key, payload):
        self.keys.append(api_key)
        text = self.responses.pop(0)
        return {
            "success": True,
            "text": text,
            "http_status": 200,
            "attempts": 1,
            "reason": "",
        }


def setup():
    """Create isolated temp dirs and patch DeepSeek Client globals."""
    root = pathlib.Path(tempfile.mkdtemp())
    requests_dir = root / "requests"
    responses_dir = root / "responses"
    processing_dir = root / "Processing Results"
    logs_dir = root / "logs"
    for folder in (requests_dir, responses_dir, processing_dir, logs_dir):
        folder.mkdir(parents=True)

    saved = (
        dsc.REQUESTS,
        dsc.RESPONSES,
        dsc.PROCESSING_RESULTS,
        dsc.LOG_DEEPSEEK_CLIENT,
    )
    dsc.REQUESTS = requests_dir
    dsc.RESPONSES = responses_dir
    dsc.PROCESSING_RESULTS = processing_dir
    dsc.LOG_DEEPSEEK_CLIENT = logs_dir
    return root, requests_dir, responses_dir, processing_dir, saved


def restore(saved):
    (dsc.REQUESTS, dsc.RESPONSES, dsc.PROCESSING_RESULTS,
     dsc.LOG_DEEPSEEK_CLIENT) = saved


def result_path(processing_dir, source_id):
    return processing_dir / f"{source_id}.processing_result.json"


def load_result(processing_dir, source_id):
    return json.loads(
        result_path(processing_dir, source_id).read_text(encoding="utf-8")
    )


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
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_requests(requests_dir, "pod_conteppei_ep051",
                       [valid_request("pod_conteppei_ep051", 1)])
        real_send = dsc.send_with_retry
        dsc.send_with_retry = FakeSender([api_response()])

        code = dsc.main(["--source", "pod_conteppei_ep051"])
        check("exit 0", code == 0)
        check("response created",
              (responses_dir / "pod_conteppei_ep051" / "response_000001.json").is_file())
        check("processing result created",
              result_path(processing_dir, "pod_conteppei_ep051").is_file())
        dsc.send_with_retry = real_send
    finally:
        restore(saved)


@test("1b. missing --source rejected")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        raised = False
        try:
            dsc.main([])
        except SystemExit:
            raised = True
        check("argparse rejects missing --source", raised)
    finally:
        restore(saved)


@test("2. source_id lineage")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_requests(requests_dir, "pod_conteppei_ep051",
                       [valid_request("pod_conteppei_ep051", 1)])
        real_send = dsc.send_with_retry
        sender = FakeSender([api_response()])
        dsc.send_with_retry = sender

        code = dsc.run("pod_conteppei_ep051", api_key="k",
                       timestamp_fn=lambda: FIXED_TIME)
        check("exit 0", code == 0)
        check("payload messages from request",
              sender.calls[0]["messages"][0]["content"] == PROMPT)

        result = load_result(processing_dir, "pod_conteppei_ep051")
        check("result source_id", result["source_id"] == "pod_conteppei_ep051")
        check("job source_id lineage", result["jobs"][0]["job_number"] == 1)
        dsc.send_with_retry = real_send
    finally:
        restore(saved)


@test("2b. source_id mismatch rejected")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_requests(requests_dir, "pod_conteppei_ep051",
                       [valid_request("pod_wrong_ep999", 1)])
        code = dsc.run("pod_conteppei_ep051", api_key="k")
        check("exit non-zero", code != 0)
        check("no response created",
              not (responses_dir / "pod_conteppei_ep051").exists())
        result = load_result(processing_dir, "pod_conteppei_ep051")
        check("failure recorded", result["requests_processed"] == 0)
    finally:
        restore(saved)


@test("3. request discovery is deterministic")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_requests(requests_dir, "pod_conteppei_ep051",
                       [valid_request("pod_conteppei_ep051", 2),
                        valid_request("pod_conteppei_ep051", 1)])
        files = dsc.request_files_for("pod_conteppei_ep051")
        names = [f.name for f in files]
        check("sorted deterministically",
              names == ["request_000001.json", "request_000002.json"])
        check("missing source returns empty", dsc.request_files_for("nope") == [])
    finally:
        restore(saved)


@test("4. partial resume")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_requests(requests_dir, "pod_conteppei_ep051",
                       [valid_request("pod_conteppei_ep051", 1),
                        valid_request("pod_conteppei_ep051", 2)])
        # Pre-existing response for job 1.
        responses_dir.joinpath("pod_conteppei_ep051").mkdir(parents=True)
        (responses_dir / "pod_conteppei_ep051" / "response_000001.json").write_text(
            api_response(prompt_tokens=99), encoding="utf-8")

        real_send = dsc.send_with_retry
        sender = FakeSender([api_response(prompt_tokens=11)])
        dsc.send_with_retry = sender

        code = dsc.run("pod_conteppei_ep051", api_key="k")
        check("exit 0", code == 0)
        check("only missing request sent", len(sender.calls) == 1)
        check("response 2 created",
              (responses_dir / "pod_conteppei_ep051" / "response_000002.json").is_file())
        dsc.send_with_retry = real_send
    finally:
        restore(saved)


@test("5. mocked API response saved verbatim")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_requests(requests_dir, "pod_conteppei_ep051",
                       [valid_request("pod_conteppei_ep051", 1)])
        raw = api_response(prompt_tokens=7, completion_tokens=3, total_tokens=10)
        real_send = dsc.send_with_retry
        dsc.send_with_retry = FakeSender([raw])

        code = dsc.run("pod_conteppei_ep051", api_key="k")
        check("exit 0", code == 0)
        saved_text = (responses_dir / "pod_conteppei_ep051" / "response_000001.json").read_text(encoding="utf-8")
        check("response preserved verbatim",
              json.loads(saved_text) == json.loads(raw))
        dsc.send_with_retry = real_send
    finally:
        restore(saved)


@test("6. usage extraction")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_requests(requests_dir, "pod_conteppei_ep051",
                       [valid_request("pod_conteppei_ep051", 1)])
        real_send = dsc.send_with_retry
        dsc.send_with_retry = FakeSender(
            [api_response(prompt_tokens=10, completion_tokens=5,
                          total_tokens=15, finish_reason="stop")])

        code = dsc.run("pod_conteppei_ep051", api_key="k",
                       timestamp_fn=lambda: FIXED_TIME)
        check("exit 0", code == 0)
        result = load_result(processing_dir, "pod_conteppei_ep051")
        job = result["jobs"][0]
        check("prompt_tokens", job["prompt_tokens"] == 10)
        check("completion_tokens", job["completion_tokens"] == 5)
        check("total_tokens", job["total_tokens"] == 15)
        check("finish_reason", job["finish_reason"] == "stop")
        check("model", result["model"] == "deepseek-v4-flash")
        check("totals", result["totals"] ==
              {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})
        dsc.send_with_retry = real_send
    finally:
        restore(saved)


@test("7. processing result creation")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_requests(requests_dir, "pod_conteppei_ep051",
                       [valid_request("pod_conteppei_ep051", 1)])
        real_send = dsc.send_with_retry
        dsc.send_with_retry = FakeSender([api_response()])

        code = dsc.run("pod_conteppei_ep051", api_key="k")
        check("exit 0", code == 0)

        import processing_result as pr
        result = load_result(processing_dir, "pod_conteppei_ep051")
        check("schema valid", pr.validate_result(result) == [])
        check("requests_processed", result["requests_processed"] == 1)
        check("job status", result["jobs"][0]["status"] == "completed")
        dsc.send_with_retry = real_send
    finally:
        restore(saved)


@test("8. atomic writes (no temp leftover)")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_requests(requests_dir, "pod_conteppei_ep051",
                       [valid_request("pod_conteppei_ep051", 1)])
        real_send = dsc.send_with_retry
        dsc.send_with_retry = FakeSender([api_response()])

        code = dsc.run("pod_conteppei_ep051", api_key="k")
        check("exit 0", code == 0)

        response_dir = responses_dir / "pod_conteppei_ep051"
        check("no response .tmp",
              not (response_dir / "response_000001.json.tmp").exists())
        check("no result .tmp",
              not (processing_dir / "pod_conteppei_ep051.processing_result.json.tmp").exists())
        dsc.send_with_retry = real_send
    finally:
        restore(saved)


@test("9. deterministic output with fixed timestamp")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_requests(requests_dir, "pod_conteppei_ep051",
                       [valid_request("pod_conteppei_ep051", 1)])
        real_send = dsc.send_with_retry

        # Two independent fresh runs with identical starting state and a
        # fixed timestamp must produce byte-identical processing results.
        results = []
        for _ in range(2):
            dsc.send_with_retry = FakeSender([api_response()])
            code = dsc.run("pod_conteppei_ep051", api_key="k",
                           timestamp_fn=lambda: FIXED_TIME)
            check("run exit 0", code == 0)
            results.append(
                (processing_dir / "pod_conteppei_ep051.processing_result.json")
                .read_bytes()
            )
            # Reset output state so both runs start identically.
            for folder in (responses_dir / "pod_conteppei_ep051",):
                import shutil
                if folder.exists():
                    shutil.rmtree(folder)
            (processing_dir / "pod_conteppei_ep051.processing_result.json").unlink()

        check("byte-identical with fixed timestamp", results[0] == results[1])
        dsc.send_with_retry = real_send
    finally:
        restore(saved)


@test("10. forbidden writes")
def _():
    import paths as project_paths

    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_requests(requests_dir, "pod_conteppei_ep051",
                       [valid_request("pod_conteppei_ep051", 1)])
        real_send = dsc.send_with_retry
        dsc.send_with_retry = FakeSender([api_response()])

        before = {
            p: sorted(x.name for x in p.iterdir())
            for p in (project_paths.SOURCE_REGISTRY,
                      project_paths.CLEANING_JOBS,
                      project_paths.CLEANING_RESULTS,
                      project_paths.CLEANED_ARCHIVE,
                      project_paths.JSONL)
        }
        code = dsc.run("pod_conteppei_ep051", api_key="k")
        check("exit 0", code == 0)
        after = {
            p: sorted(x.name for x in p.iterdir())
            for p in before
        }
        for folder in before:
            check(f"no write to {folder.name}", after[folder] == before[folder])
        dsc.send_with_retry = real_send
    finally:
        restore(saved)


@test("11. forbidden imports")
def _():
    source = pathlib.Path(DATA_PROCESSOR / "deepseek_client.py").read_text(
        encoding="utf-8")
    import_lines = "\n".join(
        ln for ln in source.splitlines()
        if ln.lstrip().startswith("import ") or ln.lstrip().startswith("from ")
    )
    for forbidden in ("corpus_builder", "response_validator",
                      "request builder", "job builder", "Analysis",
                      "process_file", "clean_subtitles", "clean_transcript",
                      "openai", "requests"):
        check(f"no {forbidden!r}", forbidden not in import_lines)


@test("11b. processing_result writer boundary")
def _():
    source = pathlib.Path(DATA_PROCESSOR / "processing_result.py").read_text(
        encoding="utf-8")
    import_lines = "\n".join(
        ln for ln in source.splitlines()
        if ln.lstrip().startswith("import ") or ln.lstrip().startswith("from ")
    )
    for forbidden in ("corpus_builder", "response_validator",
                      "deepseek_client", "request builder", "Analysis",
                      "schemas", "paths", "project_config", "urllib"):
        check(f"no {forbidden!r}", forbidden not in import_lines)


@test("12. failed request handling")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_requests(requests_dir, "pod_conteppei_ep051",
                       [valid_request("pod_conteppei_ep051", 1)])
        real_send = dsc.send_with_retry
        dsc.send_with_retry = FakeFailSender({
            "success": False,
            "text": None,
            "http_status": 500,
            "attempts": 4,
            "reason": "Server error (HTTP 500).",
        })

        code = dsc.run("pod_conteppei_ep051", api_key="k")
        check("exit non-zero (partial failure)", code != 0)
        check("no response artifact",
              not (responses_dir / "pod_conteppei_ep051").exists())
        result = load_result(processing_dir, "pod_conteppei_ep051")
        check("job failed", result["jobs"][0]["status"] == "failed")
        check("http_status recorded", result["jobs"][0]["http_status"] == 500)
        check("attempts recorded", result["jobs"][0]["attempts"] == 4)
        dsc.send_with_retry = real_send
    finally:
        restore(saved)


@test("13. auth failure aborts")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_requests(requests_dir, "pod_conteppei_ep051",
                       [valid_request("pod_conteppei_ep051", 1)])
        real_send = dsc.send_with_retry
        dsc.send_with_retry = RaisingSender(dsc.ApiAuthError("auth failed"))

        code = dsc.run("pod_conteppei_ep051", api_key="k")
        check("exit non-zero", code != 0)
        check("no response artifact",
              not (responses_dir / "pod_conteppei_ep051").exists())
        check("failure result exists",
              result_path(processing_dir, "pod_conteppei_ep051").is_file())
        dsc.send_with_retry = real_send
    finally:
        restore(saved)


@test("13b. processing_result schema round-trip")
def _():
    import processing_result as pr
    result = pr.build_result(
        source_id="pod_conteppei_ep051",
        model="deepseek-v4-flash",
        requests_processed=1,
        jobs=[pr.build_job_entry(
            "request_000001.json", 1, "completed", 10, 5, 15,
            "stop", 1, 200, "2026-08-01 12:00:00")],
        totals=pr.build_totals(10, 5, 15),
        completion_time="2026-08-01 12:00:00",
    )
    check("valid", pr.validate_result(result) == [])
    path = pathlib.Path(tempfile.mkdtemp()) / "x.json"
    pr.write_result(path, result)
    check("round-trips",
          json.loads(path.read_text(encoding="utf-8")) == result)

    bad = pr.build_result(
        source_id="pod_conteppei_ep051",
        model="m",
        requests_processed=1,
        jobs=[pr.build_job_entry("r", 1, "completed", 10, 5, 15,
                                 "stop", 1, 200, "t")],
        totals=pr.build_totals(10, 5, "bad"),
    )
    check("invalid rejected", pr.validate_result(bad) != [])


@test("config: payload thinking is disabled by default")
def _():
    import project_config as pc
    check("config default", pc.API_THINKING_TYPE == "disabled")
    body = dsc.build_request_body(valid_request("pod_x", 1))
    check("thinking type", body["thinking"] == {"type": "disabled"})


@test("config: payload max_tokens is 32768")
def _():
    body = dsc.build_request_body(valid_request("pod_x", 1))
    check("max_tokens", body["max_tokens"] == 32768)


@test("config: payload response_format is json_object")
def _():
    body = dsc.build_request_body(valid_request("pod_x", 1))
    check("response_format", body["response_format"] == {"type": "json_object"})


@test("config: no reasoning effort added by default")
def _():
    body = dsc.build_request_body(valid_request("pod_x", 1))
    check("reasoning_effort absent", "reasoning_effort" not in body)


@test("config: reasoning effort only added when explicitly supplied")
def _():
    body = dsc.build_request_body(valid_request("pod_x", 1),
                                  reasoning_effort="high")
    check("present when supplied", body.get("reasoning_effort") == "high")


@test("config: overrides still respected")
def _():
    body = dsc.build_request_body(valid_request("pod_x", 1),
                                  thinking="enabled",
                                  json_response=False,
                                  max_tokens=1000)
    check("thinking override", body["thinking"] == {"type": "enabled"})
    check("response_format override", "response_format" not in body)
    check("max_tokens override", body["max_tokens"] == 1000)


@test("14. api key: DEEPSEEK_API_KEY env var is used")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        os.environ["DEEPSEEK_API_KEY"] = "env-key-value"
        try:
            key = dsc._resolve_api_key()
        finally:
            del os.environ["DEEPSEEK_API_KEY"]
        check("env value returned", key == "env-key-value")
    finally:
        restore(saved)


@test("14b. api key: run resolves key from env var")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_requests(requests_dir, "pod_conteppei_ep051",
                       [valid_request("pod_conteppei_ep051", 1)])
        real_send = dsc.send_with_retry
        sender = KeyRecordingSender([api_response()])
        dsc.send_with_retry = sender

        os.environ["DEEPSEEK_API_KEY"] = "env-key"
        try:
            code = dsc.run("pod_conteppei_ep051")
        finally:
            del os.environ["DEEPSEEK_API_KEY"]

        check("exit 0 with env key", code == 0)
        check("resolved env key reached the API call", sender.keys == ["env-key"])
        check("response created",
              (responses_dir / "pod_conteppei_ep051" / "response_000001.json").is_file())
        dsc.send_with_retry = real_send
    finally:
        restore(saved)


@test("15. api key: error when env var unset")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        os.environ.pop("DEEPSEEK_API_KEY", None)
        raised = False
        try:
            dsc._resolve_api_key()
        except EnvironmentError as exc:
            raised = True
            check("clear message", str(exc) ==
                  "DEEPSEEK_API_KEY environment variable is not set")
        check("EnvironmentError raised", raised)
    finally:
        restore(saved)


@test("15b. api key: run fails cleanly when env var unset")
def _():
    root, requests_dir, responses_dir, processing_dir, saved = setup()
    try:
        write_requests(requests_dir, "pod_conteppei_ep051",
                       [valid_request("pod_conteppei_ep051", 1)])
        os.environ.pop("DEEPSEEK_API_KEY", None)
        code = dsc.run("pod_conteppei_ep051")
        check("clean failure return", code == 1)
        check("failure result written",
              result_path(processing_dir, "pod_conteppei_ep051").is_file())
        result = load_result(processing_dir, "pod_conteppei_ep051")
        check("no jobs processed", result["requests_processed"] == 0)
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
