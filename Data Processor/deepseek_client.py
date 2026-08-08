#!/usr/bin/env python3
"""
deepseek_client.py

Japanese Corpus Pipeline - DeepSeek Client (transport layer)

Consumes the request artifacts produced by the Request Builder for one
source_id and produces:
    - Data Processor\\responses\\<source_id>\\response_XXXX.json
    - Processing Results\\<source_id>.processing_result.json
    - Logs\\DeepSeek Client\\deepseek_client_<timestamp>.log

This module is a TRANSPORT layer only. It:
    - reads request artifacts
    - sends API requests
    - receives responses
    - saves raw response artifacts
    - records API metadata (usage, model, finish_reason) without
      interpreting parser content

It does NOT:
    - parse or validate Japanese / parser output
    - modify requests, jobs, or the Source Registry
    - calculate cost
    - write requests, jobs, jsonl, or analysis artifacts
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "Data Processor"))

from datetime import datetime

from paths import (
    LOG_DEEPSEEK_CLIENT,
    PROCESSING_RESULTS,
    REQUESTS,
    RESPONSES,
)

from project_config import (
    PROJECT_VERSION,
    MODEL_NAME,
    API_CHAT_ENDPOINT,
    API_TIMEOUT,
    API_MAX_RETRIES,
    API_RETRY_DELAY,
    API_THINKING_TYPE,
    API_REASONING_EFFORT,
    API_JSON_RESPONSE,
    API_MAX_TOKENS,
)

import processing_result


PROGRAM_NAME = "DeepSeek Client"
PROGRAM_VERSION = PROJECT_VERSION

REQUEST_PATTERN = re.compile(r"request_(\d+)\.json$")

JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"


class ApiAuthError(Exception):
    """Raised when the DeepSeek API rejects the API key."""


class ApiNetworkError(Exception):
    """Raised when a request cannot reach the DeepSeek API."""


# ============================================================
# Request discovery (single source)
# ============================================================

def request_files_for(source_id):
    """
    Return the sorted request JSON files for a source_id.

    Input: source_id (str).
    Output: sorted list of Path.
    """
    request_dir = REQUESTS / source_id
    if not request_dir.is_dir():
        return []
    return sorted(request_dir.glob("request_*.json"))


def load_request(request_file):
    """
    Load a request JSON file.

    Input: request_file (Path).
    Output: (request_data, None) or (None, error_message).
    """
    try:
        data = json.loads(request_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        return None, f"Malformed JSON: {exc}"
    return data, None


def request_source_id(request_data):
    """Return the source_id from a request artifact, or None."""
    if isinstance(request_data, dict):
        value = request_data.get("source_id")
        if isinstance(value, str) and value:
            return value
    return None


def job_number_from_request(request_file, request_data):
    """
    Return the job number for a request.

    The job_number field in the request artifact is authoritative.
    The number embedded in the filename is used only as a fallback.
    """
    if isinstance(request_data, dict):
        job_number = request_data.get("job_number")
        if isinstance(job_number, int) and not isinstance(job_number, bool):
            return job_number
    match = REQUEST_PATTERN.search(request_file.name)
    if match:
        return int(match.group(1))
    return 0


def response_path_for(source_id, request_file, request_data):
    """
    Return the expected response file path for a request.
    """
    job_number = job_number_from_request(request_file, request_data)
    return RESPONSES / source_id / f"response_{job_number:06d}.json"


# ============================================================
# API Key
# ============================================================

def _resolve_api_key():
    """
    Resolve the DeepSeek API key from the DEEPSEEK_API_KEY environment
    variable.

    Raises:
        EnvironmentError when the environment variable is absent or empty.
    """
    env_key = os.environ.get("DEEPSEEK_API_KEY")
    if not env_key:
        raise EnvironmentError(
            "DEEPSEEK_API_KEY environment variable is not set"
        )
    return env_key


# ============================================================
# API Communication
# ============================================================

def build_request_body(request_data, thinking=None, reasoning_effort=None,
                       json_response=None, max_tokens=None):
    """
    Build the exact JSON payload sent to the DeepSeek API.

    The messages array from the request file is used unchanged.

    Production defaults (frozen architecture):
        - thinking disabled (non-thinking)
        - no reasoning_effort sent
        - response_format json_object
        - max_tokens 32768 (explicit; non-thinking otherwise caps at 8192)

    Each parameter may be overridden per call; otherwise the project_config
    defaults apply. reasoning_effort is only added to the payload when a
    non-None value is supplied (thinking mode is enabled).
    """
    if thinking is None:
        thinking = API_THINKING_TYPE
    if reasoning_effort is None:
        reasoning_effort = API_REASONING_EFFORT
    if json_response is None:
        json_response = API_JSON_RESPONSE
    if max_tokens is None:
        max_tokens = API_MAX_TOKENS

    body = {
        "model": MODEL_NAME,
        "messages": request_data["messages"],
        "thinking": {"type": thinking},
        "max_tokens": max_tokens,
    }
    if reasoning_effort is not None:
        body["reasoning_effort"] = reasoning_effort
    if json_response:
        body["response_format"] = {"type": "json_object"}
    return body


def perform_request(api_key, payload):
    """
    Send one HTTPS POST to the DeepSeek chat endpoint.

    Returns:
        (http_status, response_text, retry_after)

    Raises:
        ApiNetworkError for network or timeout failures.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    request = urllib.request.Request(
        API_CHAT_ENDPOINT,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=API_TIMEOUT) as response:
            retry_after = response.headers.get("Retry-After")
            return (
                response.getcode(),
                response.read().decode("utf-8"),
                retry_after,
            )
    except urllib.error.HTTPError as error:
        retry_after = None
        if error.headers:
            retry_after = error.headers.get("Retry-After")
        return (
            error.code,
            error.read().decode("utf-8", errors="replace"),
            retry_after,
        )
    except (urllib.error.URLError, OSError) as error:
        raise ApiNetworkError(str(error))


def send_with_retry(api_key, payload):
    """
    Send a request with retries for transient failures.

    Returns:
        Dictionary:
            success: True when a valid JSON response was received.
            text: the raw response text (when successful).
            http_status: the last HTTP status received.
            attempts: number of attempts made.
            reason: failure description (when not successful).

    Raises:
        ApiAuthError on HTTP 401/403. This stops the run.
    """
    attempt = 0

    while True:
        attempt += 1

        try:
            status, text, retry_after = perform_request(api_key, payload)
        except ApiNetworkError as ex:
            if attempt > API_MAX_RETRIES:
                return {
                    "success": False,
                    "text": None,
                    "http_status": None,
                    "attempts": attempt,
                    "reason": f"Network failure: {ex}",
                }
            time.sleep(API_RETRY_DELAY)
            continue

        if status == 200:
            try:
                json.loads(text)
            except ValueError:
                if attempt > API_MAX_RETRIES:
                    return {
                        "success": False,
                        "text": None,
                        "http_status": 200,
                        "attempts": attempt,
                        "reason": "Response was not valid JSON.",
                    }
                time.sleep(API_RETRY_DELAY)
                continue
            return {
                "success": True,
                "text": text,
                "http_status": 200,
                "attempts": attempt,
                "reason": "",
            }

        if status in (401, 403):
            raise ApiAuthError(
                f"DeepSeek API authentication failed (HTTP {status})."
            )

        if status == 429:
            if attempt > API_MAX_RETRIES:
                return {
                    "success": False,
                    "text": None,
                    "http_status": 429,
                    "attempts": attempt,
                    "reason": "Rate limit persisted.",
                }
            try:
                delay = float(retry_after)
            except (TypeError, ValueError):
                delay = API_RETRY_DELAY
            time.sleep(delay)
            continue

        if 500 <= status <= 599:
            if attempt > API_MAX_RETRIES:
                return {
                    "success": False,
                    "text": None,
                    "http_status": status,
                    "attempts": attempt,
                    "reason": f"Server error (HTTP {status}).",
                }
            time.sleep(API_RETRY_DELAY)
            continue

        # Other 4xx errors are permanent and are not retried.
        return {
            "success": False,
            "text": None,
            "http_status": status,
            "attempts": attempt,
            "reason": f"Request rejected (HTTP {status}).",
        }


# ============================================================
# Metadata extraction (recording only, never interpretation)
# ============================================================

def extract_usage(response_text):
    """
    Extract usage token counts from a raw API response.

    Records raw values only; does not interpret or calculate cost.

    Input: response_text (str).
    Output: (prompt_tokens, completion_tokens, total_tokens, finish_reason,
             model) with None for missing/invalid fields.
    """
    try:
        data = json.loads(response_text)
    except (json.JSONDecodeError, ValueError):
        return None, None, None, None, None

    usage = data.get("usage") if isinstance(data, dict) else None
    prompt_tokens = None
    completion_tokens = None
    total_tokens = None
    if isinstance(usage, dict):
        prompt_tokens = _int_or_none(usage.get("prompt_tokens"))
        completion_tokens = _int_or_none(usage.get("completion_tokens"))
        total_tokens = _int_or_none(usage.get("total_tokens"))

    finish_reason = None
    choices = data.get("choices") if isinstance(data, dict) else None
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            value = first.get("finish_reason")
            if isinstance(value, str) and value:
                finish_reason = value

    model = None
    if isinstance(data, dict):
        value = data.get("model")
        if isinstance(value, str) and value:
            model = value

    return prompt_tokens, completion_tokens, total_tokens, finish_reason, model


def _int_or_none(value):
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


# ============================================================
# Response storage
# ============================================================

def save_response_atomic(response_path, response_text):
    """
    Save a raw API response to the final response filename.

    The complete response is written to a temporary file first with
    fsync, then renamed into place, so an interrupted write never
    leaves a response file that appears complete.
    """
    response_path = Path(response_path)
    response_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = response_path.with_name(response_path.name + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(response_text)
        file.flush()
        os.fsync(file.fileno())
    temp_path.replace(response_path)


# ============================================================
# Logging
# ============================================================

def start_log():
    """
    Create a new DeepSeek Client run log.

    Returns:
        The log file path.
    """
    LOG_DEEPSEEK_CLIENT.mkdir(parents=True, exist_ok=True)
    log_file = (
        LOG_DEEPSEEK_CLIENT
        / ("deepseek_client_"
           + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
           + ".log")
    )
    log_file.write_text(
        f"Program: {PROGRAM_NAME}\n"
        f"Version: {PROJECT_VERSION}\n"
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Model: {MODEL_NAME}\n"
        f"Endpoint: {API_CHAT_ENDPOINT}\n"
        "\n",
        encoding="utf-8",
    )
    return log_file


def append_log(log_file, line):
    """Append one line to the run log."""
    with log_file.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


# ============================================================
# Source execution
# ============================================================

def run(source_id, api_key=None, log_file=None, timestamp_fn=None):
    """
    Execute the DeepSeek Client for one source_id.

    Input:
        source_id (str): authoritative lineage identifier.
        api_key (str or None): API key; loaded from the DEEPSEEK_API_KEY
            environment variable when None.
        log_file (Path or None): run log; created when None.
        timestamp_fn (callable or None): injectable clock for tests.

    Output: exit code (0 success, non-zero failure).
    """
    if timestamp_fn is None:
        timestamp_fn = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    source_id = str(source_id).strip()
    if not source_id:
        return 1

    request_files = request_files_for(source_id)
    if not request_files:
        return fail(source_id, log_file, [f"no requests found for {source_id}"])

    if api_key is None:
        try:
            api_key = _resolve_api_key()
        except EnvironmentError as exc:
            return fail(source_id, log_file, [str(exc)])

    if log_file is None:
        log_file = start_log()
        append_log(log_file, f"Run started: {timestamp_fn()}")
        append_log(log_file, f"Source: {source_id}")
        append_log(log_file, f"Pending requests: {len(request_files)}")

    # Load and validate all requests first; a lineage mismatch aborts.
    jobs = []
    for request_file in request_files:
        request_data, error = load_request(request_file)
        if error:
            return fail(source_id, log_file, [error])
        if request_source_id(request_data) != source_id:
            return fail(source_id, log_file, [
                f"request {request_file.name} source_id "
                f"{request_source_id(request_data)!r} does not match "
                f"requested {source_id!r}"
            ])
        response_path = response_path_for(source_id, request_file, request_data)
        job_number = job_number_from_request(request_file, request_data)
        jobs.append({
            "request_file": request_file,
            "request_id": request_file.name,
            "job_number": job_number,
            "response_path": response_path,
            "request_data": request_data,
        })

    completed = 0
    failed = 0
    entries = []

    try:
        for job in jobs:
            response_path = job["response_path"]
            if response_path.exists():
                # Resume: an existing response means this request is complete.
                completed += 1
                entry = _completed_entry_from_existing(job, timestamp_fn)
                entries.append(entry)
                append_log(log_file,
                           f"{timestamp_fn()} SKIP {job['request_id']} -> "
                           f"{response_path.name} (existing)")
                continue

            payload = build_request_body(job["request_data"])
            result = send_with_retry(api_key, payload)
            now = timestamp_fn()

            if result["success"]:
                save_response_atomic(response_path, result["text"])
                completed += 1
                entry = _completed_entry(job, result, now)
                entries.append(entry)
                append_log(log_file,
                           f"{timestamp_fn()} SENT {job['request_id']} -> "
                           f"{response_path.name} HTTP {result['http_status']} "
                           f"attempts {result['attempts']}")
            else:
                failed += 1
                entry = _failed_entry(job, result, now)
                entries.append(entry)
                append_log(log_file,
                           f"{timestamp_fn()} FAILED {job['request_id']} HTTP "
                           f"{result['http_status']} attempts "
                           f"{result['attempts']}: {result['reason']}")
    except ApiAuthError as exc:
        # Auth failure aborts the run. Write the partial processing result
        # so the state is visible and recoverable.
        append_log(log_file, f"RUN-ABORTED: {exc}")
        totals = {
            "prompt_tokens": sum(e["prompt_tokens"] or 0 for e in entries),
            "completion_tokens": sum(e["completion_tokens"] or 0 for e in entries),
            "total_tokens": sum(e["total_tokens"] or 0 for e in entries),
        }
        processing = processing_result.build_result(
            source_id=source_id,
            model=MODEL_NAME,
            requests_processed=len(entries),
            jobs=entries,
            totals=totals,
            completion_time=timestamp_fn(),
        )
        try:
            processing_result.write_result(
                PROCESSING_RESULTS / f"{source_id}.processing_result.json",
                processing,
            )
        except processing_result.ProcessingResultError:
            pass
        return 1

    totals = {
        "prompt_tokens": sum(e["prompt_tokens"] or 0 for e in entries),
        "completion_tokens": sum(e["completion_tokens"] or 0 for e in entries),
        "total_tokens": sum(e["total_tokens"] or 0 for e in entries),
    }

    processing = processing_result.build_result(
        source_id=source_id,
        model=MODEL_NAME,
        requests_processed=len(entries),
        jobs=entries,
        totals=totals,
        completion_time=timestamp_fn(),
    )
    try:
        processing_result.write_result(
            PROCESSING_RESULTS / f"{source_id}.processing_result.json",
            processing,
        )
    except processing_result.ProcessingResultError as exc:
        return fail(source_id, log_file,
                    [f"cannot write processing result: {exc}"])

    append_log(log_file, f"Run ended: {timestamp_fn()}")
    append_log(log_file, f"Total sent: {completed}")
    append_log(log_file, f"Total failed: {failed}")

    if failed:
        return 2
    return 0


def _completed_entry(job, result, now):
    (prompt_tokens, completion_tokens, total_tokens,
     finish_reason, model) = extract_usage(result["text"])
    return processing_result.build_job_entry(
        request_id=job["request_id"],
        job_number=job["job_number"],
        status=JOB_STATUS_COMPLETED,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        finish_reason=finish_reason,
        attempts=result["attempts"],
        http_status=result["http_status"],
        timestamp=now,
    )


def _completed_entry_from_existing(job, timestamp_fn):
    # A pre-existing response is treated as completed. Usage metadata is
    # re-extracted from the saved raw response so the processing result
    # is complete and deterministic regardless of how the response was
    # produced. The response file itself remains the raw evidence.
    response_path = job["response_path"]
    try:
        text = response_path.read_text(encoding="utf-8")
    except OSError:
        text = None
    if text is not None:
        (prompt_tokens, completion_tokens, total_tokens,
         finish_reason, _model) = extract_usage(text)
    else:
        prompt_tokens = completion_tokens = total_tokens = None
        finish_reason = None
    return processing_result.build_job_entry(
        request_id=job["request_id"],
        job_number=job["job_number"],
        status=JOB_STATUS_COMPLETED,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        finish_reason=finish_reason,
        attempts=0,
        http_status=None,
        timestamp=timestamp_fn(),
    )


def _failed_entry(job, result, now):
    return processing_result.build_job_entry(
        request_id=job["request_id"],
        job_number=job["job_number"],
        status=JOB_STATUS_FAILED,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        finish_reason=None,
        attempts=result["attempts"],
        http_status=result.get("http_status"),
        timestamp=now,
    )


def fail(source_id, log_file, errors):
    """
    Write a failure Processing Result and log.

    A failure never creates response artifacts. The result artifact is
    written when possible so the manager and resume detection can see
    the state.
    """
    if log_file is None:
        log_file = start_log()
    for error in errors:
        append_log(log_file, f"FAILED: {error}")

    processing = processing_result.build_result(
        source_id=source_id,
        model=MODEL_NAME,
        requests_processed=0,
        jobs=[],
        totals={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    )
    try:
        processing_result.write_result(
            PROCESSING_RESULTS / f"{source_id}.processing_result.json",
            processing,
        )
    except processing_result.ProcessingResultError:
        pass
    return 1


# ============================================================
# Entry point
# ============================================================

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="deepseek_client.py",
        description=PROGRAM_NAME,
    )
    parser.add_argument(
        "--source",
        required=True,
        help="source_id of the requests to send.",
    )
    args = parser.parse_args(argv)
    return run(args.source)


if __name__ == "__main__":
    sys.exit(main())
