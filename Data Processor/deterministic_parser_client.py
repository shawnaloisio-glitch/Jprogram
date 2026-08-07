#!/usr/bin/env python3
# Run via Jprogram/.venv/Scripts/python.exe (imports deterministic_parser, which requires spacy/ginza installed in the venv).
"""
deterministic_parser_client.py

Japanese Corpus Pipeline - Deterministic Parser Client (transport layer)

Drives deterministic_parser.py through the same job-in / response-out file
contract deepseek_client.py already satisfies, so Production Manager can
later be repointed at this client with a minimal change. It is built and
tested in isolation; wiring it into the real pipeline is a separate task.

For one source_id it produces:
    - Data Processor\\responses\\<source_id>\\response_XXXX.json
    - Processing Results\\<source_id>.processing_result.json
    - Logs\\Deterministic Parser Client\\deterministic_parser_client_<timestamp>.log

This module is a TRANSPORT layer only. It:
    - reads job artifacts (jobs\\<source_id>\\job_XXXX.json)
    - runs deterministic_parser.parse_job over each job's clean text
    - saves the returned dict as the response artifact
    - records parser metadata (producer identity) without
      interpreting parser content

It does NOT:
    - modify jobs, requests, or the Source Registry
    - call APIs
    - parse or validate Japanese / parser output
    - write jsonl or analysis artifacts
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "Data Processor"))

from paths import JOBS, LOGS, PROCESSING_RESULTS, RESPONSES
from project_config import PROJECT_VERSION

import deterministic_parser
import processing_result


PROGRAM_NAME = "Deterministic Parser Client"
PROGRAM_VERSION = PROJECT_VERSION

# Producer identity recorded as corpus provenance. This producer is the
# GiNZA deterministic parser (ja_ginza model). Keep it in sync with the
# ginza/ja_ginza versions installed in Jprogram/.venv.
PRODUCER_ID = "ginza-ja_ginza-5.2.0"

# Log folder. paths.py is out of scope for this module, so the folder is
# derived from paths.LOGS here, mirroring paths.LOG_DEEPSEEK_CLIENT.
LOG_DETERMINISTIC_PARSER_CLIENT = LOGS / "Deterministic Parser Client"

JOB_PATTERN = re.compile(r"job_(\d+)\.json$")

JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"


# ============================================================
# Job discovery (single source)
# ============================================================

def job_files_for(source_id):
    """
    Return the sorted job JSON files for a source_id.

    Input: source_id (str).
    Output: sorted list of Path.
    """
    job_dir = JOBS / source_id
    if not job_dir.is_dir():
        return []
    return sorted(job_dir.glob("job_*.json"))


def load_job(job_file):
    """
    Load a job JSON file.

    Input: job_file (Path).
    Output: (job_data, None) or (None, error_message).
    """
    try:
        data = json.loads(job_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        return None, f"Malformed JSON: {exc}"
    return data, None


def job_source_id(job_data):
    """Return the source_id from a job artifact, or None."""
    if isinstance(job_data, dict):
        value = job_data.get("source_id")
        if isinstance(value, str) and value:
            return value
    return None


def job_number_from_job(job_file, job_data):
    """
    Return the job number for a job.

    The job_number field in the job artifact is authoritative.
    The number embedded in the filename is used only as a fallback.
    """
    if isinstance(job_data, dict):
        job_number = job_data.get("job_number")
        if isinstance(job_number, int) and not isinstance(job_number, bool):
            return job_number
    match = JOB_PATTERN.search(job_file.name)
    if match:
        return int(match.group(1))
    return 0


def response_path_for(source_id, job_file, job_data):
    """
    Return the expected response file path for a job.
    """
    job_number = job_number_from_job(job_file, job_data)
    return RESPONSES / source_id / f"response_{job_number:06d}.json"


# ============================================================
# Response storage
# ============================================================

def save_response_atomic(response_path, data):
    """
    Save a parsed response dict to the final response filename.

    The complete response is written to a temporary file first with
    fsync, then renamed into place, so an interrupted write never
    leaves a response file that appears complete.
    """
    response_path = Path(response_path)
    response_path.parent.mkdir(parents=True, exist_ok=True)

    text = (
        json.dumps(data, ensure_ascii=False, sort_keys=True, indent=4)
        + "\n"
    )
    temp_path = response_path.with_name(response_path.name + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(text)
        file.flush()
        os.fsync(file.fileno())
    temp_path.replace(response_path)


# ============================================================
# Logging
# ============================================================

def start_log():
    """
    Create a new Deterministic Parser Client run log.

    Returns:
        The log file path.
    """
    LOG_DETERMINISTIC_PARSER_CLIENT.mkdir(parents=True, exist_ok=True)
    log_file = (
        LOG_DETERMINISTIC_PARSER_CLIENT
        / ("deterministic_parser_client_"
           + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
           + ".log")
    )
    log_file.write_text(
        f"Program: {PROGRAM_NAME}\n"
        f"Version: {PROJECT_VERSION}\n"
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Producer: {PRODUCER_ID}\n"
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

def run(source_id, log_file=None, timestamp_fn=None):
    """
    Execute the Deterministic Parser Client for one source_id.

    Input:
        source_id (str): authoritative lineage identifier.
        log_file (Path or None): run log; created when None.
        timestamp_fn (callable or None): injectable clock for tests.

    Output: exit code (0 success, non-zero failure).
    """
    if timestamp_fn is None:
        timestamp_fn = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    source_id = str(source_id).strip()
    if not source_id:
        return 1

    job_files = job_files_for(source_id)
    if not job_files:
        return fail(source_id, log_file, [f"no jobs found for {source_id}"])

    if log_file is None:
        log_file = start_log()
        append_log(log_file, f"Run started: {timestamp_fn()}")
        append_log(log_file, f"Source: {source_id}")
        append_log(log_file, f"Pending jobs: {len(job_files)}")

    # Load and validate all jobs first; a lineage mismatch aborts.
    jobs = []
    for job_file in job_files:
        job_data, error = load_job(job_file)
        if error:
            return fail(source_id, log_file, [error])
        if job_source_id(job_data) != source_id:
            return fail(source_id, log_file, [
                f"job {job_file.name} source_id "
                f"{job_source_id(job_data)!r} does not match "
                f"requested {source_id!r}"
            ])
        response_path = response_path_for(source_id, job_file, job_data)
        job_number = job_number_from_job(job_file, job_data)
        jobs.append({
            "job_file": job_file,
            "job_id": job_file.name,
            "job_number": job_number,
            "response_path": response_path,
            "job_data": job_data,
        })

    completed = 0
    skipped = 0
    failed = 0
    entries = []

    for job in jobs:
        response_path = job["response_path"]
        if response_path.exists():
            # Resume: an existing response means this job is complete.
            completed += 1
            skipped += 1
            entry = _completed_entry_from_existing(job, timestamp_fn)
            entries.append(entry)
            append_log(log_file,
                       f"{timestamp_fn()} SKIP {job['job_id']} -> "
                       f"{response_path.name} (existing)")
            continue

        try:
            parsed = deterministic_parser.parse_job(
                job["job_data"]["source_id"],
                job["job_data"]["job_number"],
                job["job_data"]["text"],
            )
        except Exception as exc:
            failed += 1
            now = timestamp_fn()
            entry = _failed_entry(job, now)
            entries.append(entry)
            append_log(log_file,
                       f"{timestamp_fn()} FAILED {job['job_id']}: {exc}")
            continue

        save_response_atomic(response_path, parsed)
        completed += 1
        now = timestamp_fn()
        entry = _completed_entry(job, now)
        entries.append(entry)
        append_log(log_file,
                   f"{timestamp_fn()} PROCESSED {job['job_id']} -> "
                   f"{response_path.name}")

    totals = {
        "prompt_tokens": sum(e["prompt_tokens"] or 0 for e in entries),
        "completion_tokens": sum(e["completion_tokens"] or 0 for e in entries),
        "total_tokens": sum(e["total_tokens"] or 0 for e in entries),
    }

    processing = processing_result.build_result(
        source_id=source_id,
        model=PRODUCER_ID,
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
    append_log(log_file, f"Total processed: {completed}")
    append_log(log_file, f"Total skipped: {skipped}")
    append_log(log_file, f"Total failed: {failed}")

    if failed:
        return 2
    return 0


def _completed_entry(job, now):
    return processing_result.build_job_entry(
        request_id=job["job_id"],
        job_number=job["job_number"],
        status=JOB_STATUS_COMPLETED,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        finish_reason=None,
        attempts=1,
        http_status=None,
        timestamp=now,
    )


def _completed_entry_from_existing(job, timestamp_fn):
    # A pre-existing response is treated as completed. There is no token
    # metadata to re-extract for this producer, so token fields are null
    # and the response file itself remains the evidence.
    return processing_result.build_job_entry(
        request_id=job["job_id"],
        job_number=job["job_number"],
        status=JOB_STATUS_COMPLETED,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        finish_reason=None,
        attempts=0,
        http_status=None,
        timestamp=timestamp_fn(),
    )


def _failed_entry(job, now):
    return processing_result.build_job_entry(
        request_id=job["job_id"],
        job_number=job["job_number"],
        status=JOB_STATUS_FAILED,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        finish_reason=None,
        attempts=1,
        http_status=None,
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
        model=PRODUCER_ID,
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
        prog="deterministic_parser_client.py",
        description=PROGRAM_NAME,
    )
    parser.add_argument(
        "--source",
        required=True,
        help="source_id of the jobs to parse.",
    )
    args = parser.parse_args(argv)
    return run(args.source)


if __name__ == "__main__":
    sys.exit(main())
