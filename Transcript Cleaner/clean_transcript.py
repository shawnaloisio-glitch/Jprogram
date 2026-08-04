#!/usr/bin/env python3
"""
clean_transcript.py

Japanese Corpus Pipeline - Transcript Cleaner (mechanical worker)

Consumes exactly one Cleaning Job artifact and produces:
    - Cleaned Artifact (job.output_path)
    - Cleaning Result (Cleaning Results\\<source_id>.cleaning_result.json)
    - Cleaner log (Logs\\Transcript Cleaner\\<source_id>.cleaner.log)

This cleaner does NOT:
    - scan folders or discover files
    - decide what is new
    - generate source IDs
    - hash for duplicate detection
    - select cleaning profiles
    - create Cleaning Jobs
    - modify the Source Registry
    - touch Data Processor folders
    - call APIs
    - know about parser, corpus, analysis, or GUI stages
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Project import convention: expose the project root, the Source Intake
# utility layer (schemas, cleaning_result), and the shared cleaning
# utilities (Common).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "Source Intake"))
sys.path.append(str(PROJECT_ROOT / "Common"))

import schemas
import cleaning_result
from cleaning_utils import (
    strip_bom,
    trim_lines,
    collapse_blank_lines,
    collapse_ascii_spaces,
)
from paths import CLEANING_RESULTS, LOG_TRANSCRIPT_CLEANER
from project_config import (
    CLEANER_VERSIONS,
    LOG_DATE_FORMAT,
    PROCESSING_PROFILES,
)

PROGRAM_NAME = "Transcript Cleaner"
PROGRAM_VERSION = CLEANER_VERSIONS.get("transcript_standard_v1", "1.0")

TRANSCRIPT_PROFILE = "transcript_standard_v1"


class CleaningError(Exception):
    """Raised when a Cleaning Job cannot be loaded."""


# ============================================================
# Job loading
# ============================================================

def load_job(job_path):
    """
    Load a Cleaning Job JSON artifact.

    Input: job_path (path or str).
    Output: (job, error) where job is the parsed JSON value or None.
    """
    job_path = Path(job_path)
    if not job_path.is_file():
        return None, f"Cleaning Job not found: {job_path}"
    try:
        job = json.loads(job_path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, f"Cleaning Job is not valid JSON: {exc}"
    return job, None


def assignment_errors(job):
    """
    Return the list of assignment errors for a Cleaning Job.

    The Cleaning Job is authoritative. This cleaner only accepts jobs
    assigned to it: the transcript source type, the transcript cleaning
    profile, and the configured cleaner version.

    Input: job (dict).
    Output: list of error strings (empty when the job is assigned here).
    """
    errors = []

    source_type = job.get("source_type")
    processing = PROCESSING_PROFILES.get(source_type)
    if processing is None:
        errors.append(f"unknown source_type: {source_type}")
    elif processing["cleaner"] != "clean_transcript":
        errors.append(
            f"source_type {source_type!r} is not assigned to the "
            f"transcript cleaner"
        )

    if job.get("cleaning_profile") != TRANSCRIPT_PROFILE:
        errors.append(
            f"cleaning_profile {job.get('cleaning_profile')!r} is not "
            f"{TRANSCRIPT_PROFILE!r}"
        )

    configured = CLEANER_VERSIONS.get(TRANSCRIPT_PROFILE)
    if job.get("cleaner_version") != configured:
        errors.append(
            f"cleaner_version {job.get('cleaner_version')!r} does not "
            f"match configured version {configured!r}"
        )

    return errors


# ============================================================
# Cleaning
# ============================================================

def clean_transcript_text(text):
    """
    Apply the transcript_standard_v1 transformation sequence.

    Exact order:
        1. Strip the UTF-8 BOM.
        2. Split into lines.
        3. Trim lines.
        4. Collapse repeated ASCII spaces only (full-width U+3000 and
           Japanese text are preserved).
        5. Collapse consecutive blank lines to one.
        6. Join output: utterances separated by one blank line, rstrip,
           exactly one final newline.

    The canonical corpus reconstruction contract (Corpus Builder) joins
    sentences with a blank line ("\\n\\n"). The transcript cleaner must
    therefore separate utterances with a single blank line so the source
    is exactly reconstructible from the parsed sentences.

    Input: raw transcript text (str).
    Output: (output_text, statistics).
    """
    text, bom_removed = strip_bom(text)
    characters_read = len(text)

    lines = text.splitlines()

    lines, trimmed_lines = trim_lines(lines)

    cleaned_lines = []
    repeated_spaces_removed = 0
    for line in lines:
        line, count = collapse_ascii_spaces(line)
        repeated_spaces_removed += count
        cleaned_lines.append(line)

    lines, blank_lines_removed = collapse_blank_lines(cleaned_lines)

    output_text = join_transcript_lines(lines)
    characters_written = len(output_text)

    statistics = {
        "characters_read": characters_read,
        "characters_written": characters_written,
        "bom_removed": bom_removed,
        "trimmed_lines": trimmed_lines,
        "repeated_spaces_removed": repeated_spaces_removed,
        "blank_lines_removed": blank_lines_removed,
    }

    return output_text, statistics


def join_transcript_lines(lines):
    """
    Join cleaned transcript lines into the canonical corpus format.

    Each non-blank line is one utterance (one sentence for the parser).
    Utterances are separated by a single blank line ("\\n\\n") so the
    clean source is exactly reconstructible by the Corpus Builder's
    reconstruction gate (which joins sentences with a blank line).

    Blank separators in the input collapse into the single blank line
    between utterances. Output ends with exactly one final newline.

    Input: lines (list of str).
    Output: str.
    """
    utterances = [line for line in lines if line != ""]
    if not utterances:
        return "\n"
    return "\n\n".join(utterances) + "\n"


# ============================================================
# Atomic writes
# ============================================================

def write_atomic_text(path, text):
    """
    Write UTF-8 text atomically (temp file, fsync, replace).

    A crash cannot leave a partial final artifact.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as file:
        file.write(text)
        file.flush()
        os.fsync(file.fileno())
    temp.replace(path)


def write_result(result):
    """
    Validate and atomically write a Cleaning Result artifact.

    Input: result (dict).
    Output: the written path.
    Raises: cleaning_result.CleaningResultError on invalid schema.
    """
    path = CLEANING_RESULTS / f"{result['source_id']}.cleaning_result.json"
    cleaning_result.write_result(path, result)
    return path


def write_log(job_path, source_id, status, details):
    """
    Write the cleaner log for a Cleaning Job.

    Deterministic content; only the timestamp varies.
    """
    folder = LOG_TRANSCRIPT_CLEANER
    folder.mkdir(parents=True, exist_ok=True)
    log_file = folder / f"{source_id}.cleaner.log"
    lines = [
        f"Program: {PROGRAM_NAME}",
        f"Version: {PROGRAM_VERSION}",
        f"Date: {datetime.now().strftime(LOG_DATE_FORMAT)}",
        f"Job: {job_path}",
        f"Source: {source_id}",
        f"Status: {status}",
    ]
    lines.extend(details)
    write_atomic_text(log_file, "\n".join(lines) + "\n")
    return log_file


# ============================================================
# Job execution
# ============================================================

def run(job_path):
    """
    Execute one Cleaning Job end to end.

    Input: job_path (path or str) to a Cleaning Job JSON artifact.
    Output: exit code (0 success, non-zero failure).
    """
    job_path = Path(job_path)

    job, error = load_job(job_path)
    if error:
        write_log(job_path, "unknown", "FAILED", [error])
        return 1
    if not isinstance(job, dict):
        write_log(job_path, "unknown", "FAILED",
                  ["Cleaning Job must be a JSON object"])
        return 1

    source_id = job.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        write_log(job_path, "unknown", "FAILED",
                  ["Cleaning Job missing source_id"])
        return 1

    schema_errors = schemas.validate("cleaning_job", job)
    if schema_errors:
        return fail(job_path, source_id, schema_errors)

    errors = assignment_errors(job)
    if errors:
        return fail(job_path, source_id, errors)

    raw_path = Path(job["raw_path"])
    if not raw_path.is_file():
        return fail(job_path, source_id,
                    [f"raw file not found: {raw_path}"])

    try:
        text = raw_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        return fail(job_path, source_id,
                    [f"cannot read raw file: {exc}"])

    output_text, statistics = clean_transcript_text(text)

    output_path = Path(job["output_path"])
    try:
        write_atomic_text(output_path, output_text)
    except OSError as exc:
        return fail(job_path, source_id,
                    [f"cannot write cleaned artifact: {exc}"])

    output_hash = hashlib.sha256(
        output_text.encode("utf-8")
    ).hexdigest()

    result = cleaning_result.build_result(
        source_id=source_id,
        success=True,
        cleaned_artifact=str(output_path),
        statistics=statistics,
        errors=[],
        cleaner_version=job["cleaner_version"],
        completion_time=datetime.now().strftime(LOG_DATE_FORMAT),
        output_hash=output_hash,
    )
    write_result(result)

    write_log(job_path, source_id, "SUCCESS", [
        f"Input: {raw_path}",
        f"Cleaned Artifact: {output_path}",
        f"Cleaning Result: {result['cleaned_artifact']}",
    ])

    return 0


def fail(job_path, source_id, errors):
    """
    Write a failure Cleaning Result and log.

    Failure before artifact creation always produces a Cleaning Result
    with success=false and errors populated. A success result is never
    created without a valid artifact.
    """
    result = cleaning_result.build_result(
        source_id=source_id,
        success=False,
        cleaned_artifact=None,
        statistics={},
        errors=list(errors),
    )
    write_result(result)
    write_log(job_path, source_id, "FAILED", list(errors))
    return 1


# ============================================================
# Entry point
# ============================================================

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="clean_transcript.py",
        description=PROGRAM_NAME,
    )
    parser.add_argument(
        "--job",
        required=True,
        help="Path to a Cleaning Job JSON artifact.",
    )
    args = parser.parse_args(argv)
    return run(args.job)


if __name__ == "__main__":
    sys.exit(main())
