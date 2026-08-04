#!/usr/bin/env python3
"""
request builder.py

Japanese Corpus Pipeline - Request Builder (mechanical transformer)

Consumes the job artifacts produced by the Job Builder for one source_id
and produces:
    - Data Processor\\requests\\<source_id>\\request_XXXX.json
    - Data Processor\\Request Results\\<source_id>.request_builder_result.json
    - Logs\\Request Builder\\<source_id>.request_builder.log

This stage does NOT:
    - scan folders or discover sources
    - derive identity from filenames
    - call APIs
    - parse or validate parser output
    - modify jobs, cleaning artifacts, or the Source Registry
    - perform analysis or calculate cost

source_id is the authoritative lineage identifier.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Project import convention: expose the project root and the Data Processor
# utility layer (request_builder_result).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "Data Processor"))

import request_builder_result
from paths import (
    JOBS,
    LOG_REQUEST_BUILDER,
    PROMPTS,
    REQUEST_RESULTS,
    REQUESTS,
)
from project_config import (
    JOB_EXTENSION,
    LOG_DATE_FORMAT,
    MODEL_NAME,
    PROJECT_VERSION,
    expressions_enabled,
)

PROGRAM_NAME = "Request Builder"
PROGRAM_VERSION = PROJECT_VERSION

PROMPT_FILE = PROMPTS / "parser_prompt.md"

# Instruction appended to the parser prompt when the configured model has
# expression extraction disabled (model capability policy). The parser is
# told to always emit an empty expressions array; sentence/word/chunk
# extraction is unchanged. The JSONL schema is unchanged.

EXPRESSIONS_DISABLED_DIRECTIVE = (
    "\n\n## EXPRESSION EXTRACTION: DISABLED\n"
    "Expression extraction is disabled for this model. For every sentence, "
    'always output exactly: "expressions": [] (an empty array). Do not emit '
    "any expression records. All other fields (sentence text, words, chunks) "
    "are unchanged."
)

JOB_REQUIRED_FIELDS = (
    "source_id",
    "cleaned_artifact",
    "job_number",
    "characters",
    "text",
)


class RequestBuilderError(Exception):
    """Raised when a Request Builder run cannot be completed."""


# ============================================================
# Prompt loading
# ============================================================

def load_prompt():
    """
    Load the current parser prompt.

    The prompt wording and content are frozen and must not be altered.
    """
    if not PROMPT_FILE.is_file():
        raise RequestBuilderError(f"missing parser prompt: {PROMPT_FILE}")
    prompt = PROMPT_FILE.read_text(encoding="utf-8").strip()
    if not prompt:
        raise RequestBuilderError(f"parser prompt is empty: {PROMPT_FILE}")
    return prompt


def effective_prompt():
    """
    Load the parser prompt with the configured model's capability applied.

    When expression extraction is disabled for the configured model, an
    explicit directive is appended instructing the parser to always emit
    an empty expressions array. When expressions are enabled, the base
    prompt is returned unchanged (future capable models need no change).
    """
    prompt = load_prompt()
    if not expressions_enabled(MODEL_NAME):
        return prompt + EXPRESSIONS_DISABLED_DIRECTIVE
    return prompt


# ============================================================
# Job loading
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
    return sorted(job_dir.glob(f"*{JOB_EXTENSION}"))


def load_job(job_file):
    """
    Load one job artifact.

    Input: job_file (Path).
    Output: (job, error) where job is the parsed dict or None.
    """
    try:
        job = json.loads(job_file.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return None, f"job not readable: {exc}"
    if not isinstance(job, dict):
        return None, f"job must be a JSON object: {job_file.name}"
    return job, None


def job_errors(job, requested_source_id):
    """
    Validate one job artifact and its lineage.

    Checks required fields and that the requested source_id matches the
    job's source_id. The job's source_id is authoritative.

    Input: job (dict), requested_source_id (str).
    Output: list of error strings (empty when valid).
    """
    errors = []
    for field in JOB_REQUIRED_FIELDS:
        if field not in job:
            errors.append(f"job missing required field: {field}")
            continue
        value = job[field]
        if field in ("job_number", "characters"):
            if not (isinstance(value, int) and not isinstance(value, bool)):
                errors.append(f"job field '{field}' must be an integer")
        elif not isinstance(value, str) or not value:
            errors.append(f"job field '{field}' must be a non-empty string")

    job_source_id = job.get("source_id")
    if job_source_id != requested_source_id:
        errors.append(
            f"job source_id {job_source_id!r} does not match requested "
            f"source_id {requested_source_id!r}"
        )

    return errors


# ============================================================
# Request construction
# ============================================================

def user_content(source_id, job_number, text):
    """
    Build the parser user payload with a clearly separated metadata section.

    The parser prompt requires the model to echo source_id and job_number,
    but those values must be given to the model. They are placed in a
    metadata section before the job text:

        SOURCE METADATA:
        source_id: <id>
        job_number: <number>

        TEXT:
        <job text>

    Input: source_id (str), job_number (int), text (str).
    Output: the user message content string.
    """
    return (
        "SOURCE METADATA:\n"
        f"source_id: {source_id}\n"
        f"job_number: {job_number}\n"
        "\n"
        "TEXT:\n"
        f"{text}"
    )


def build_request(job, prompt):
    """
    Build a DeepSeek request from one job artifact.

    The messages payload is preserved exactly:
        system: parser prompt
        user:   source metadata section + job text

    source_id is authoritative. Compatibility fields (source_file,
    source_name) are populated from the job data, never from filenames.

    Input: job (dict), prompt (str).
    Output: request dict.
    """
    cleaned_artifact = job["cleaned_artifact"]
    return {
        "source_id": job["source_id"],
        "cleaned_artifact": cleaned_artifact,
        "job_number": job["job_number"],
        "prompt_version": PROGRAM_VERSION,
        "source_file": cleaned_artifact,
        "source_name": job["source_id"],
        "messages": [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": user_content(
                    job["source_id"], job["job_number"], job["text"]),
            },
        ],
    }


def request_file_for(source_id, job_number):
    """Return the deterministic request path for a job_number."""
    return REQUESTS / source_id / f"request_{job_number:06}.json"


def load_existing_request(request_file):
    """
    Load an existing request artifact for resume detection.

    Input: request_file (Path).
    Output: (request, error) where request is the parsed dict or None.
    """
    if not request_file.is_file():
        return None, None
    try:
        request = json.loads(request_file.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return None, f"existing request not readable: {exc}"
    return request, None


def existing_request_errors(request, job):
    """
    Check whether an existing request is valid for the job.

    A valid existing request preserves lineage (source_id, job_number)
    and the parser payload (source_id + job text in the user message).

    Input: request (dict), job (dict).
    Output: list of error strings (empty when valid).
    """
    errors = []
    if not isinstance(request, dict):
        return ["existing request is not a JSON object"]
    if request.get("source_id") != job["source_id"]:
        errors.append("existing request source_id does not match job")
    if request.get("job_number") != job["job_number"]:
        errors.append("existing request job_number does not match job")
    messages = request.get("messages")
    if not isinstance(messages, list) or len(messages) != 2:
        errors.append("existing request messages structure invalid")
    else:
        try:
            user_content_value = messages[1].get("content")
        except (AttributeError, IndexError):
            user_content_value = None
        expected = user_content(job["source_id"], job["job_number"],
                                job["text"])
        if user_content_value != expected:
            errors.append("existing request text does not match job")
    return errors


# ============================================================
# Atomic writes
# ============================================================

def write_atomic_text(path, text):
    """
    Write UTF-8 text atomically (temp file, fsync, replace).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as file:
        file.write(text)
        file.flush()
        os.fsync(file.fileno())
    temp.replace(path)


def write_atomic_json(path, data):
    """
    Write JSON deterministically and atomically.
    """
    text = (
        json.dumps(data, ensure_ascii=False, sort_keys=True, indent=4)
        + "\n"
    )
    write_atomic_text(path, text)


def write_result(result):
    """
    Validate and atomically write a Request Builder Result artifact.
    """
    path = REQUEST_RESULTS / f"{result['source_id']}.request_builder_result.json"
    request_builder_result.write_result(path, result)
    return path


def write_log(source_id, status, details):
    """
    Write the Request Builder log for a source.

    Deterministic content; only the timestamp varies.
    """
    folder = LOG_REQUEST_BUILDER
    folder.mkdir(parents=True, exist_ok=True)
    log_file = folder / f"{source_id}.request_builder.log"
    lines = [
        f"Program: {PROGRAM_NAME}",
        f"Version: {PROGRAM_VERSION}",
        f"Date: {datetime.now().strftime(LOG_DATE_FORMAT)}",
        f"Source: {source_id}",
        f"Status: {status}",
    ]
    lines.extend(details)
    write_atomic_text(log_file, "\n".join(lines) + "\n")
    return log_file


# ============================================================
# Job execution
# ============================================================

def run(source_id):
    """
    Execute the Request Builder for one source_id.

    Input: source_id (str).
    Output: exit code (0 success, non-zero failure).
    """
    source_id = str(source_id).strip()
    if not source_id:
        write_log("unknown", "FAILED", ["missing source_id"])
        return 1

    job_files = job_files_for(source_id)
    if not job_files:
        return fail(source_id, [f"no jobs found for source_id: {source_id}"])

    try:
        prompt = effective_prompt()
    except RequestBuilderError as exc:
        return fail(source_id, [str(exc)])

    loaded_jobs = []
    for job_file in job_files:
        job, error = load_job(job_file)
        if error:
            return fail(source_id, [error])
        errors = job_errors(job, source_id)
        if errors:
            return fail(source_id, errors)
        loaded_jobs.append((job_file, job))

    # Build all requests first; any invalid job fails the whole build
    # before any request file is created.
    requests = []
    for job_file, job in loaded_jobs:
        request_file = request_file_for(source_id, job["job_number"])
        request = build_request(job, prompt)

        existing, error = load_existing_request(request_file)
        if error:
            return fail(source_id, [error])
        if existing is not None:
            errors = existing_request_errors(existing, job)
            if not errors:
                # Valid existing request: preserve it.
                requests.append((job_file, request_file, None))
                continue

        requests.append((job_file, request_file, request))

    created = []
    for job_file, request_file, request in requests:
        if request is None:
            created.append(request_file)
            continue
        try:
            write_atomic_json(request_file, request)
            created.append(request_file)
        except OSError as exc:
            return fail(source_id, [f"cannot write request file: {exc}"])

    result = request_builder_result.build_result(
        source_id=source_id,
        success=True,
        requests_created=len(created) > 0,
        jobs_processed=len(loaded_jobs),
        errors=[],
        completion_time=datetime.now().strftime(LOG_DATE_FORMAT),
    )
    try:
        write_result(result)
    except request_builder_result.RequestBuilderResultError as exc:
        return fail(source_id, [f"cannot write request builder result: {exc}"])

    write_log(source_id, "SUCCESS", [
        f"Jobs Processed: {len(loaded_jobs)}",
        f"Requests Present: {len(created)}",
    ])

    return 0


def fail(source_id, errors):
    """
    Write a failure Request Builder Result and log.

    A failure never creates request files. The result artifact is written
    when possible so the manager and resume detection can see the state.
    """
    result = request_builder_result.build_result(
        source_id=source_id,
        success=False,
        requests_created=False,
        jobs_processed=0,
        errors=list(errors),
    )
    try:
        write_result(result)
    except request_builder_result.RequestBuilderResultError:
        pass
    write_log(source_id, "FAILED", list(errors))
    return 1


# ============================================================
# Entry point
# ============================================================

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="request builder.py",
        description=PROGRAM_NAME,
    )
    parser.add_argument(
        "--source",
        required=True,
        help="source_id of the jobs to build requests for.",
    )
    args = parser.parse_args(argv)
    return run(args.source)


if __name__ == "__main__":
    sys.exit(main())
