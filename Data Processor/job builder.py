#!/usr/bin/env python3
"""
job builder.py

Japanese Corpus Pipeline - Job Builder (mechanical worker)

Consumes exactly one successful Cleaning Result and produces:
    - Data Processor\\jobs\\<source_id>\\job_XXXX.json
    - Data Processor\\Job Results\\<source_id>.job_builder_result.json
    - Logs\\Job Builder\\<source_id>.job_builder.log

This stage does NOT:
    - scan the processing folder
    - discover sources or clean files
    - derive identity from filenames
    - write the Source Registry or Cleaning Jobs
    - touch Raw folders
    - call APIs
    - know about parser, corpus, analysis, or GUI stages
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Project import convention: expose the project root and the Source Intake
# utility layer (schemas for Cleaning Result validation).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "Source Intake"))
sys.path.append(str(PROJECT_ROOT / "Data Processor"))

import schemas
import job_builder_result
import hashing
from paths import CLEANING_RESULTS, JOBS, JOB_RESULTS, LOG_JOB_BUILDER
from project_config import (
    JOB_NUMBER_DIGITS,
    LOG_DATE_FORMAT,
    MAX_JOB_CHARACTERS,
    PROJECT_VERSION,
)

PROGRAM_NAME = "Job Builder"
PROGRAM_VERSION = PROJECT_VERSION


class JobBuilderError(Exception):
    """Raised when a Job Builder run cannot be completed."""


# ============================================================
# Cleaning Result loading
# ============================================================

def load_cleaning_result(source_id):
    """
    Load and schema-validate the Cleaning Result for a source_id.

    Input: source_id (str).
    Output: (result, error) where result is the parsed dict or None.
    """
    path = CLEANING_RESULTS / f"{source_id}.cleaning_result.json"
    if not path.is_file():
        return None, f"Cleaning Result not found: {path}"
    try:
        result = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, f"Cleaning Result is not valid JSON: {exc}"
    if not isinstance(result, dict):
        return None, "Cleaning Result must be a JSON object"
    errors = schemas.validate("cleaning_result", result)
    if errors:
        return None, "; ".join(errors)
    return result, None


def cleaning_result_errors(result):
    """
    Confirm the Cleaning Result is complete and usable.

    Checks: success is true, cleaned_artifact is present, the cleaned
    artifact exists on disk, and the artifact's sha256 matches the
    recorded output_hash.

    Input: result (dict).
    Output: list of error strings (empty when usable).
    """
    errors = []
    if result.get("success") is not True:
        errors.append("Cleaning Result success is not true")
    cleaned_artifact = result.get("cleaned_artifact")
    if not isinstance(cleaned_artifact, str) or not cleaned_artifact:
        errors.append("Cleaning Result has no cleaned_artifact path")
    else:
        artifact = Path(cleaned_artifact)
        if not artifact.is_file():
            errors.append(f"cleaned artifact not found: {artifact}")
        else:
            output_hash = result.get("output_hash")
            if not isinstance(output_hash, str) or not output_hash:
                errors.append("Cleaning Result has no output_hash")
            else:
                try:
                    fresh_hash = hashing.sha256_file(artifact)
                except OSError as exc:
                    errors.append(f"cannot hash cleaned artifact: {exc}")
                else:
                    if fresh_hash != output_hash:
                        errors.append(
                            f"cleaned artifact sha256 does not match "
                            f"output_hash: {fresh_hash} != {output_hash}"
                        )
    return errors


# ============================================================
# Job batching
# ============================================================

def build_job_batches(text):
    """
    Divide cleaned text into character-based batches.

    Lines are kept intact. A new job begins before adding a line that
    would exceed MAX_JOB_CHARACTERS. Deterministic ordering.

    Input: text (str).
    Output: list of {"job_number", "text", "characters"} dicts.
    """
    lines = text.splitlines(keepends=True)
    jobs = []
    current_lines = []
    current_characters = 0

    for line in lines:
        line_characters = len(line)
        if current_lines and current_characters + line_characters > MAX_JOB_CHARACTERS:
            jobs.append({
                "job_number": len(jobs) + 1,
                "text": "".join(current_lines),
                "characters": current_characters,
            })
            current_lines = []
            current_characters = 0
        current_lines.append(line)
        current_characters += line_characters

    if current_lines:
        jobs.append({
            "job_number": len(jobs) + 1,
            "text": "".join(current_lines),
            "characters": current_characters,
        })

    return jobs


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


def job_output_dir(source_id):
    """Return the deterministic job folder for a source_id."""
    return JOBS / source_id


def write_job_files(source_id, cleaned_artifact, jobs):
    """
    Write every job batch as job_XXXX.json under jobs\\<source_id>\\.

    Job metadata: source_id, source artifact path, job_number,
    characters, text.

    Input: source_id (str), cleaned_artifact (path/str), jobs (list).
    Output: list of written job file paths.
    """
    output_dir = job_output_dir(source_id)
    written = []
    for job in jobs:
        job_number = job["job_number"]
        job_file = output_dir / f"job_{job_number:0{JOB_NUMBER_DIGITS}d}.json"
        job_data = {
            "source_id": source_id,
            "cleaned_artifact": str(cleaned_artifact),
            "job_number": job_number,
            "characters": job["characters"],
            "text": job["text"],
        }
        write_atomic_json(job_file, job_data)
        written.append(job_file)
    return written


def write_result(result):
    """
    Validate and atomically write a Job Builder Result artifact.
    """
    path = JOB_RESULTS / f"{result['source_id']}.job_builder_result.json"
    job_builder_result.write_result(path, result)
    return path


def write_log(source_id, status, details):
    """
    Write the Job Builder log for a source.

    Deterministic content; only the timestamp varies.
    """
    folder = LOG_JOB_BUILDER
    folder.mkdir(parents=True, exist_ok=True)
    log_file = folder / f"{source_id}.job_builder.log"
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
    Execute the Job Builder for one source_id.

    Input: source_id (str).
    Output: exit code (0 success, non-zero failure).
    """
    source_id = str(source_id).strip()
    if not source_id:
        write_log("unknown", "FAILED", ["missing source_id"])
        return 1

    result, error = load_cleaning_result(source_id)
    if error:
        return fail(source_id, [error])

    errors = cleaning_result_errors(result)
    if errors:
        return fail(source_id, errors)

    cleaned_artifact = Path(result["cleaned_artifact"])

    try:
        text = cleaned_artifact.read_text(encoding="utf-8-sig")
    except (UnicodeDecodeError, OSError) as exc:
        return fail(source_id, [f"cannot read cleaned artifact: {exc}"])

    jobs = build_job_batches(text)
    total_characters = sum(job["characters"] for job in jobs)

    try:
        job_files = write_job_files(source_id, cleaned_artifact, jobs)
    except OSError as exc:
        return fail(source_id, [f"cannot write job files: {exc}"])

    output_dir = job_output_dir(source_id)

    jb_result = job_builder_result.build_result(
        source_id=source_id,
        success=True,
        jobs_created=len(job_files) > 0,
        job_count=len(job_files),
        total_characters=total_characters,
        output_directory=str(output_dir),
        errors=[],
        completion_time=datetime.now().strftime(LOG_DATE_FORMAT),
    )
    try:
        write_result(jb_result)
    except job_builder_result.JobBuilderResultError as exc:
        return fail(source_id, [f"cannot write job builder result: {exc}"])

    write_log(source_id, "SUCCESS", [
        f"Cleaned Artifact: {cleaned_artifact}",
        f"Jobs Created: {len(job_files)}",
        f"Total Characters: {total_characters}",
        f"Output Directory: {output_dir}",
    ])

    return 0


def fail(source_id, errors):
    """
    Write a failure Job Builder Result and log.

    A failure never creates job files. The result artifact is written
    when possible so the manager and resume detection can see the state.
    """
    jb_result = job_builder_result.build_result(
        source_id=source_id,
        success=False,
        jobs_created=False,
        job_count=0,
        total_characters=0,
        output_directory=str(job_output_dir(source_id)),
        errors=list(errors),
    )
    try:
        write_result(jb_result)
    except job_builder_result.JobBuilderResultError:
        pass
    write_log(source_id, "FAILED", list(errors))
    return 1


# ============================================================
# Entry point
# ============================================================

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="job builder.py",
        description=PROGRAM_NAME,
    )
    parser.add_argument(
        "--source",
        required=True,
        help="source_id of the completed cleaning to build jobs for.",
    )
    args = parser.parse_args(argv)
    return run(args.source)


if __name__ == "__main__":
    sys.exit(main())
