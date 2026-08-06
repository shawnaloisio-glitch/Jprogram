#!/usr/bin/env python3
"""
production_manager.py

Japanese Corpus Pipeline - Production Manager (artifact-state reader only)

Reads pipeline artifacts and reports each source's pipeline state. This
module does NOT launch stages, import pipeline stage modules, clean text,
build jobs/requests, call APIs, parse responses, or build the corpus.

State is derived exclusively from artifact evidence. There is no hidden
database or in-memory state.

Supported states:
    unregistered
    registered
    waiting_for_clean
    cleaned
    jobs_created
    requests_created
    api_processing
    api_complete
    corpus_available
    failed
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

from paths import (
    CLEANED_ARCHIVE,
    CLEANING_JOBS,
    CLEANING_RESULTS,
    CORPUS_RESULTS,
    DATA_PROCESSOR,
    JOB_RESULTS,
    JOBS,
    JSONL,
    LOG_PRODUCTION_MANAGER,
    PROCESSING_RESULTS,
    PROJECT_ROOT,
    REQUEST_RESULTS,
    REQUESTS,
    RESPONSES,
    SOURCE_REGISTRY,
    TRANSCRIPT_CLEANER,
)

from project_config import (
    PROCESSING_PROFILES,
)

STATES = (
    "unregistered",
    "registered",
    "waiting_for_clean",
    "cleaned",
    "jobs_created",
    "requests_created",
    "api_processing",
    "api_complete",
    "corpus_available",
    "failed",
)

# state -> next action name (for the "Next stage" report).
NEXT_STAGE = {
    "unregistered": "intake",
    "registered": "intake",
    "waiting_for_clean": "clean",
    "cleaned": "jobs",
    "jobs_created": "requests",
    "requests_created": "api",
    "api_processing": "api",
    "api_complete": "corpus",
    "corpus_available": None,
    "failed": None,
}

STAGE_NAMES = ("clean", "jobs", "requests", "api", "corpus")


# ============================================================
# Artifact path helpers
# ============================================================

def registry_path(source_id):
    return SOURCE_REGISTRY / f"{source_id}.json"


def cleaning_job_path(source_id):
    return CLEANING_JOBS / f"{source_id}.cleaning_job.json"


def cleaning_result_path(source_id):
    return CLEANING_RESULTS / f"{source_id}.cleaning_result.json"


def cleaned_artifact_path(source_id):
    return CLEANED_ARCHIVE / f"{source_id}.clean.txt"


def job_result_path(source_id):
    return JOB_RESULTS / f"{source_id}.job_builder_result.json"


def jobs_dir(source_id):
    return JOBS / source_id


def request_result_path(source_id):
    return REQUEST_RESULTS / f"{source_id}.request_builder_result.json"


def requests_dir(source_id):
    return REQUESTS / source_id


def responses_dir(source_id):
    return RESPONSES / source_id


def processing_result_path(source_id):
    return PROCESSING_RESULTS / f"{source_id}.processing_result.json"


def corpus_result_path(source_id):
    return CORPUS_RESULTS / f"{source_id}.corpus_builder_result.json"


def jsonl_path(source_id):
    return JSONL / f"{source_id}.jsonl"


# ============================================================
# Read helpers
# ============================================================

def _read_json(path):
    """
    Read a JSON artifact.

    Returns:
        (data, error) where data is the parsed value or None, and error
        is None when the file is absent or a description of the problem.
    """
    path = Path(path)
    if not path.is_file():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return None, f"unreadable: {exc}"
    if not isinstance(data, dict):
        return None, "not a JSON object"
    return data, None


def _count_files(folder, pattern):
    folder = Path(folder)
    if not folder.is_dir():
        return 0
    return len(list(folder.glob(pattern)))


def _bool_or_none(data, field):
    if not isinstance(data, dict):
        return None
    value = data.get(field)
    if isinstance(value, bool):
        return value
    return None


# ============================================================
# Stage dispatch table
# ============================================================
# One source of truth for launching pipeline stages. Each entry defines:
#   script(source_id)   -> absolute path of the stage executable
#   args(source_id)     -> argv list (never a shell string)
#   result_path(source_id) -> expected result artifact path
#   validate(data)      -> True when the result artifact confirms success
# The manager executes this table; it contains no stage logic.

def _source_args(source_id):
    return ["--source", str(source_id)]


def _cleaner_script(source_id):
    """
    Select the cleaner executable from the Cleaning Job metadata.

    The manager reads the job, resolves the cleaner name via
    PROCESSING_PROFILES, and maps it to the script path. It does not
    contain cleaning logic.
    """
    job, error = _read_json(cleaning_job_path(source_id))
    if job is None:
        raise ManagerError(
            f"cannot determine cleaner: cleaning job not readable "
            f"({error or 'missing'})"
        )
    source_type = job.get("source_type")
    profile = PROCESSING_PROFILES.get(source_type)
    if profile is None:
        raise ManagerError(
            f"cannot determine cleaner: unknown source_type "
            f"{source_type!r}"
        )
    cleaner = profile.get("cleaner")
    if cleaner == "clean_transcript":
        return TRANSCRIPT_CLEANER / "clean_transcript.py"
    raise ManagerError(f"cannot determine cleaner: unknown cleaner {cleaner!r}")


def _clean_args(source_id):
    return ["--job", str(cleaning_job_path(source_id))]


def _job_script(source_id):
    return DATA_PROCESSOR / "job builder.py"


def _request_script(source_id):
    return DATA_PROCESSOR / "request builder.py"


def _api_script(source_id):
    return DATA_PROCESSOR / "deepseek_client.py"


def _corpus_script(source_id):
    return DATA_PROCESSOR / "corpus_builder.py"


def _validate_result_true(data):
    return isinstance(data, dict) and data.get("success") is True


def _validate_api(data):
    if not isinstance(data, dict):
        return False
    for job in data.get("jobs", []):
        if isinstance(job, dict) and job.get("status") == "failed":
            return False
    return True


STAGES = {
    "clean": {
        "script": _cleaner_script,
        "args": _clean_args,
        "result_path": cleaning_result_path,
        "validate": _validate_result_true,
    },
    "jobs": {
        "script": _job_script,
        "args": _source_args,
        "result_path": job_result_path,
        "validate": _validate_result_true,
    },
    "requests": {
        "script": _request_script,
        "args": _source_args,
        "result_path": request_result_path,
        "validate": _validate_result_true,
    },
    "api": {
        "script": _api_script,
        "args": _source_args,
        "result_path": processing_result_path,
        "validate": _validate_api,
    },
    "corpus": {
        "script": _corpus_script,
        "args": _source_args,
        "result_path": corpus_result_path,
        "validate": _validate_result_true,
    },
}


class ManagerError(Exception):
    """Raised when the Production Manager cannot perform an operation."""


# ============================================================
# Stage launching
# ============================================================

def build_command(stage, source_id):
    """
    Build the argv list for a stage.

    Input: stage (str), source_id (str).
    Output: list of strings.
    Raises: ManagerError for an unknown stage.
    """
    if stage not in STAGES:
        raise ManagerError(f"unknown stage: {stage}")
    entry = STAGES[stage]
    script = entry["script"](source_id)
    args = entry["args"](source_id)
    return [sys.executable, str(script)] + list(args)


def launch_stage(stage, source_id, timeout=None):
    """
    Launch one pipeline stage as an isolated subprocess.

    Returns a result dict:
        {
            "stage": str,
            "source_id": str,
            "command": list,
            "exit_code": int or None,
            "stdout": str,
            "stderr": str,
            "success": bool,
            "error": str or None,
            "state": refreshed state info or None,
        }

    Success requires BOTH a zero exit code AND a valid result artifact
    (per the dispatch table's validate rule). Exit code alone is never
    sufficient.
    """
    result = {
        "stage": stage,
        "source_id": source_id,
        "command": [],
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "success": False,
        "error": None,
        "state": None,
    }

    try:
        command = build_command(stage, source_id)
    except ManagerError as exc:
        result["error"] = str(exc)
        return result
    result["command"] = command

    script = command[1]
    if not Path(script).is_file():
        result["error"] = f"executable not found: {script}"
        return result

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(PROJECT_ROOT),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        result["error"] = f"timed out after {timeout}s"
        if exc.stdout:
            result["stdout"] = str(exc.stdout)
        if exc.stderr:
            result["stderr"] = str(exc.stderr)
        return result
    except OSError as exc:
        result["error"] = f"failed to launch: {exc}"
        return result

    result["exit_code"] = completed.returncode
    result["stdout"] = completed.stdout or ""
    result["stderr"] = completed.stderr or ""

    if completed.returncode != 0:
        result["error"] = f"stage exited with code {completed.returncode}"
        return result

    # Exit code is not enough: verify the result artifact.
    entry = STAGES[stage]
    result_path = entry["result_path"](source_id)
    data, error = _read_json(result_path)
    if data is None:
        result["error"] = (
            f"stage completed but result artifact missing or unreadable: "
            f"{result_path} ({error or 'missing'})"
        )
        return result
    if not entry["validate"](data):
        result["error"] = f"stage result artifact reports failure: {result_path}"
        return result

    result["success"] = True
    result["state"] = state_for(source_id)
    return result


# ============================================================
# Manager logging
# ============================================================

def log_manager_entry(source_id, stage, command, exit_code, success,
                      error=None):
    """
    Append one entry to the Production Manager log.

    Allowed write target: Logs\\Production Manager\\ only.
    """
    LOG_PRODUCTION_MANAGER.mkdir(parents=True, exist_ok=True)
    log_file = LOG_PRODUCTION_MANAGER / "manager.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    command_text = " ".join(str(part) for part in command)
    line = (
        f"{timestamp} source={source_id} stage={stage} "
        f"exit={exit_code} success={success} "
        f"command={command_text}"
    )
    if error:
        line += f" error={error}"
    with log_file.open("a", encoding="utf-8") as file:
        file.write(line + "\n")
    return log_file


# ============================================================
# Evidence collection
# ============================================================

def collect_evidence(source_id):
    """
    Collect artifact evidence for a source.

    Returns a dict of booleans/counts describing the on-disk artifacts.
    Never raises for missing or malformed artifacts; problems are
    recorded as error strings and ignored for state decisions.
    """
    registry, registry_error = _read_json(registry_path(source_id))
    cleaning_job, job_error = _read_json(cleaning_job_path(source_id))
    cleaning_result, cr_error = _read_json(cleaning_result_path(source_id))
    job_result, jr_error = _read_json(job_result_path(source_id))
    request_result, rr_error = _read_json(request_result_path(source_id))
    processing_result, pr_error = _read_json(processing_result_path(source_id))
    corpus_result, corr_error = _read_json(corpus_result_path(source_id))

    jsonl = jsonl_path(source_id)
    jsonl_exists = jsonl.is_file()
    jsonl_nonempty = jsonl_exists and jsonl.stat().st_size > 0

    requests_count = _count_files(requests_dir(source_id), "request_*.json")
    responses_count = _count_files(responses_dir(source_id), "response_*.json")
    jobs_count = _count_files(jobs_dir(source_id), "job_*.json")

    processing_statuses = []
    if isinstance(processing_result, dict):
        for job in processing_result.get("jobs", []):
            if isinstance(job, dict) and isinstance(job.get("status"), str):
                processing_statuses.append(job["status"])

    evidence = {
        "registry_exists": registry is not None or registry_error is not None,
        "registry_error": registry_error,
        "cleaning_job_exists": cleaning_job is not None or job_error is not None,
        "cleaning_job_error": job_error,
        "cleaning_result_exists": cleaning_result is not None or cr_error is not None,
        "cleaning_result_error": cr_error,
        "cleaning_success": _bool_or_none(cleaning_result, "success"),
        "cleaned_artifact_exists": cleaned_artifact_path(source_id).is_file(),
        "job_result_exists": job_result is not None or jr_error is not None,
        "job_result_error": jr_error,
        "job_builder_success": _bool_or_none(job_result, "success"),
        "jobs_count": jobs_count,
        "request_result_exists": request_result is not None or rr_error is not None,
        "request_result_error": rr_error,
        "request_builder_success": _bool_or_none(request_result, "success"),
        "requests_count": requests_count,
        "responses_count": responses_count,
        "processing_result_exists": processing_result is not None or pr_error is not None,
        "processing_result_error": pr_error,
        "processing_statuses": processing_statuses,
        "corpus_result_exists": corpus_result is not None or corr_error is not None,
        "corpus_result_error": corr_error,
        "corpus_success": _bool_or_none(corpus_result, "success"),
        "jsonl_exists": jsonl_exists,
        "jsonl_nonempty": jsonl_nonempty,
    }
    return evidence


# ============================================================
# Failure detection
# ============================================================

def failure_reason(evidence):
    """
    Return the failing stage name from evidence, or None.

    A stage is failed when its result artifact declares success=false
    (cleaner / job builder / request builder / corpus builder) or when
    the Processing Result records a failed job (API stage).
    """
    if evidence["cleaning_result_exists"] \
            and evidence["cleaning_success"] is False:
        return "clean"
    if evidence["job_result_exists"] \
            and evidence["job_builder_success"] is False:
        return "jobs"
    if evidence["request_result_exists"] \
            and evidence["request_builder_success"] is False:
        return "requests"
    if evidence["processing_result_exists"] \
            and any(status == "failed" for status in evidence["processing_statuses"]):
        return "api"
    if evidence["corpus_result_exists"] \
            and evidence["corpus_success"] is False:
        return "corpus"
    return None


# ============================================================
# State resolution
# ============================================================

def state_for(source_id):
    """
    Determine the pipeline state for a source_id from artifacts only.

    Returns a dict:
        {
            "state": str,
            "failed_stage": str or None,
            "next_stage": str or None,
            "evidence": dict,
        }
    """
    evidence = collect_evidence(source_id)

    failed_stage = failure_reason(evidence)
    if failed_stage is not None:
        return {
            "state": "failed",
            "failed_stage": failed_stage,
            "next_stage": failed_stage,
            "evidence": evidence,
        }

    # Terminal: a validated corpus exists.
    if evidence["jsonl_nonempty"] and evidence["corpus_success"] is True:
        state = "corpus_available"
    # API complete: every request has a response and the Processing
    # Result exists with no failed jobs.
    elif (evidence["requests_count"] > 0
          and evidence["responses_count"] >= evidence["requests_count"]
          and evidence["processing_result_exists"]
          and evidence["processing_statuses"]
          and all(status == "completed" for status in evidence["processing_statuses"])):
        state = "api_complete"
    # API processing: some responses exist but the set is incomplete.
    elif (evidence["requests_count"] > 0
          and evidence["responses_count"] > 0
          and evidence["responses_count"] < evidence["requests_count"]):
        state = "api_processing"
    # Requests created: requests exist but the API stage has not started.
    elif evidence["requests_count"] > 0:
        state = "requests_created"
    # Jobs created: job result success (or job files exist).
    elif (evidence["job_result_exists"]
          and evidence["job_builder_success"] is True) \
            or evidence["jobs_count"] > 0:
        state = "jobs_created"
    # Cleaned: cleaning result success (and cleaned artifact present).
    elif (evidence["cleaning_result_exists"]
          and evidence["cleaning_success"] is True
          and evidence["cleaned_artifact_exists"]):
        state = "cleaned"
    # Waiting for clean: a cleaning job exists without a success result.
    elif evidence["cleaning_job_exists"]:
        state = "waiting_for_clean"
    # Registered: only the Source Registry entry exists.
    elif evidence["registry_exists"]:
        state = "registered"
    else:
        state = "unregistered"

    return {
        "state": state,
        "failed_stage": None,
        "next_stage": NEXT_STAGE.get(state),
        "evidence": evidence,
    }


# ============================================================
# Reporting
# ============================================================

def stage_status(evidence):
    """
    Compute a per-stage status from artifact evidence.

    Returns a dict mapping each stage name to one of:
        "done", "failed", "pending"
    """
    status = {}
    if evidence["cleaning_result_exists"]:
        status["clean"] = "done" if evidence["cleaning_success"] is True else "failed"
    else:
        status["clean"] = "pending"
    if evidence["job_result_exists"]:
        status["jobs"] = "done" if evidence["job_builder_success"] is True else "failed"
    else:
        status["jobs"] = "pending"
    if evidence["request_result_exists"]:
        status["requests"] = "done" if evidence["request_builder_success"] is True else "failed"
    else:
        status["requests"] = "pending"
    if evidence["processing_result_exists"]:
        api_done = bool(evidence["processing_statuses"]) and all(
            s == "completed" for s in evidence["processing_statuses"])
        status["api"] = "done" if api_done else "failed"
    else:
        status["api"] = "pending"
    if evidence["corpus_result_exists"]:
        status["corpus"] = "done" if evidence["corpus_success"] is True else "failed"
    else:
        status["corpus"] = "pending"
    return status


def format_report(source_id, info, enabled=None):
    """
    Format a human-readable state report.

    Input: source_id (str), info (dict from state_for),
        enabled (set of stage names or None).
    Output: str.
    """
    if enabled is None:
        enabled = set(STAGE_NAMES)

    lines = [
        f"Source: {source_id}",
        f"State: {info['state']}",
    ]
    if info["failed_stage"]:
        lines.append(f"Failed stage: {info['failed_stage']}")

    lines.append("Stages:")
    status = stage_status(info["evidence"])
    next_stage = info["next_stage"]
    for stage in STAGE_NAMES:
        marker = status.get(stage, "pending")
        if stage == next_stage:
            marker = "NEXT"
        if stage not in enabled:
            marker = "DISABLED"
        lines.append(f"  {stage:<9} {marker}")

    lines.append("Evidence:")
    for key in sorted(info["evidence"]):
        lines.append(f"  {key}: {info['evidence'][key]}")

    if info["failed_stage"]:
        lines.append(f"Next stage: retry {info['failed_stage']}")
    else:
        lines.append(f"Next stage: {info['next_stage']}")
    return "\n".join(lines)


# ============================================================
# Stage toggles and pipeline planning
# ============================================================

def parse_stage_list(text):
    """
    Parse a comma-separated stage list.

    Input: text (str or None).
    Output: list of stage names.
    Raises: ManagerError for an unknown stage name.
    """
    if not text:
        return []
    names = []
    for part in str(text).split(","):
        name = part.strip()
        if not name:
            continue
        if name not in STAGE_NAMES:
            raise ManagerError(f"unknown stage: {name}")
        names.append(name)
    return names


def resolve_enabled(enable=None, disable=None):
    """
    Resolve the enabled stage set from toggle flags.

    All stages are enabled by default. `enable` restricts to the given
    list; `disable` removes the given stages.

    Input: enable (str or None), disable (str or None).
    Output: set of stage names.
    """
    enabled = set(STAGE_NAMES)
    if enable:
        enabled &= set(parse_stage_list(enable))
    if disable:
        enabled -= set(parse_stage_list(disable))
    return enabled


# Simulated state after a successful stage (for dry-run planning only).
_SIMULATED_SUCCESS = {
    "clean": "cleaned",
    "jobs": "jobs_created",
    "requests": "requests_created",
    "api": "api_complete",
    "corpus": "corpus_available",
}


def plan_stages(source_id, enabled=None):
    """
    Compute the ordered list of stages the pipeline would attempt.

    Uses artifact evidence only; assumes each planned stage succeeds.
    Stops at the first disabled stage, the intake boundary, a failure,
    or the terminal state.

    Input: source_id (str), enabled (set or None).
    Output: dict {"state", "plan" (list), "boundary" (str or None)}.
    """
    if enabled is None:
        enabled = set(STAGE_NAMES)

    info = state_for(source_id)
    state = info["state"]
    plan = []

    if state == "corpus_available":
        return {"state": state, "plan": plan, "boundary": None}
    if state == "failed":
        return {"state": state, "plan": plan,
                "boundary": f"failed:{info['failed_stage']}"}
    if state in ("unregistered", "registered"):
        return {"state": state, "plan": plan, "boundary": "intake"}

    seen = set()
    while state != "corpus_available":
        next_stage = NEXT_STAGE.get(state)
        if next_stage is None or next_stage not in STAGES:
            return {"state": state, "plan": plan, "boundary": next_stage}
        if next_stage not in enabled:
            return {"state": state, "plan": plan,
                    "boundary": f"disabled:{next_stage}"}
        if next_stage in seen:
            return {"state": state, "plan": plan, "boundary": "cycle"}
        seen.add(next_stage)
        plan.append(next_stage)
        state = _SIMULATED_SUCCESS[next_stage]

    return {"state": "corpus_available", "plan": plan, "boundary": None}


# ============================================================
# Public application API
# ============================================================
# These functions return structured dictionaries. The CLI renders them;
# the future GUI consumes them directly. No function here prints to the
# console and none imports argparse.

def status(source_id, enabled=None):
    """
    Return the pipeline status for a source as structured data.

    Input: source_id (str), enabled (set of stage names or None).
    Output: dict:
        {
            "success": True,
            "source_id": str,
            "state": str,
            "failed_stage": str or None,
            "next_stage": str or None,
            "stages": {stage: status},
            "evidence": {...},
        }
    """
    info = state_for(source_id)
    return {
        "success": True,
        "source_id": source_id,
        "state": info["state"],
        "failed_stage": info["failed_stage"],
        "next_stage": info["next_stage"],
        "stages": stage_status(info["evidence"]),
        "evidence": info["evidence"],
    }


def report(source_id, enabled=None):
    """
    Return a structured report for a source.

    Equivalent to status() but focused on the human-relevant fields.

    Input: source_id (str), enabled (set of stage names or None).
    Output: dict (same as status()).
    """
    return status(source_id, enabled=enabled)


def dry_run(source_id, enabled=None):
    """
    Return the planned pipeline stages without launching anything.

    Input: source_id (str), enabled (set of stage names or None).
    Output: dict:
        {
            "success": True,
            "source_id": str,
            "state": str,
            "plan": [stage, ...],
            "boundary": str or None,
        }
    """
    plan = plan_stages(source_id, enabled=enabled)
    return {
        "success": True,
        "source_id": source_id,
        "state": plan["state"],
        "plan": plan["plan"],
        "boundary": plan["boundary"],
    }


def run_stage(source_id, stage, timeout=None, enabled=None):
    """
    Run one stage and return structured result data.

    Input:
        source_id (str), stage (str), timeout (int or None),
        enabled (set of stage names or None).
    Output: dict from launch_stage, plus "source_id" and "stage".
    """
    result = launch_stage(stage, source_id, timeout=timeout)
    result["source_id"] = source_id
    result["stage"] = stage
    return result


def pipeline(source_id, auto=False, timeout=None, confirm_fn=None,
             enabled=None, dry_run=False, collect_events=True):
    """
    Execute the pipeline and return structured result data.

    This is the non-printing engine behind the CLI. It performs the full
    pipeline loop (observe -> select -> launch -> verify -> observe) and
    returns a structured dict. It never prints and never imports argparse.

    The confirmation callback (confirm_fn) is used only in guided mode
    (auto=False). It receives the prompt text and returns a string; the
    caller decides how to present it (CLI uses input(), GUI uses its own
    UI). For a non-interactive caller, pass confirm_fn that returns "y".

    Input:
        source_id (str), auto (bool), timeout (int or None),
        confirm_fn (callable or None), enabled (set or None),
        dry_run (bool), collect_events (bool).

    Output: dict:
        {
            "success": bool,
            "exit_code": int,
            "state": str,
            "failed_stage": str or None,
            "next_stage": str or None,
            "stages_run": [stage, ...],
            "exit_codes": {stage: code},
            "boundary": str or None,
            "events": [ {stage, command, exit_code, success, ...}, ... ],
        }
    """
    if confirm_fn is None:
        confirm_fn = input
    if enabled is None:
        enabled = set(STAGE_NAMES)

    info = state_for(source_id)
    events = []

    # Dry run: plan and report without launching or writing.
    if dry_run:
        plan = plan_stages(source_id, enabled=enabled)
        return {
            "success": True,
            "exit_code": 0,
            "source_id": source_id,
            "state": plan["state"],
            "failed_stage": None,
            "next_stage": None,
            "stages_run": [],
            "exit_codes": {},
            "plan": plan["plan"],
            "boundary": plan["boundary"],
            "events": [],
        }

    # Already complete: do not rerun anything.
    if info["state"] == "corpus_available":
        return {
            "success": True,
            "exit_code": 0,
            "source_id": source_id,
            "state": "corpus_available",
            "failed_stage": None,
            "next_stage": None,
            "stages_run": [],
            "exit_codes": {},
            "boundary": None,
            "events": events,
        }

    # Failed: no automatic retry; stop and report.
    if info["state"] == "failed":
        return {
            "success": False,
            "exit_code": 1,
            "source_id": source_id,
            "state": "failed",
            "failed_stage": info["failed_stage"],
            "next_stage": info["failed_stage"],
            "stages_run": [],
            "exit_codes": {},
            "boundary": f"failed:{info['failed_stage']}",
            "events": events,
        }

    # Intake is not automated.
    if info["state"] in ("unregistered", "registered"):
        return {
            "success": False,
            "exit_code": 1,
            "source_id": source_id,
            "state": info["state"],
            "failed_stage": None,
            "next_stage": None,
            "stages_run": [],
            "exit_codes": {},
            "boundary": "intake",
            "events": events,
        }

    stages_run = []
    exit_codes = {}

    while True:
        info = state_for(source_id)
        state = info["state"]

        if state == "corpus_available":
            boundary = None
            break

        if state == "failed":
            return {
                "success": False,
                "exit_code": 1,
                "source_id": source_id,
                "state": "failed",
                "failed_stage": info["failed_stage"],
                "next_stage": info["failed_stage"],
                "stages_run": stages_run,
                "exit_codes": exit_codes,
                "boundary": f"failed:{info['failed_stage']}",
                "events": events,
            }

        next_stage = NEXT_STAGE.get(state)
        if next_stage is None:
            boundary = "stopped"
            break
        if next_stage not in STAGES:
            boundary = f"unsupported:{next_stage}"
            return {
                "success": False,
                "exit_code": 1,
                "source_id": source_id,
                "state": state,
                "failed_stage": None,
                "next_stage": None,
                "stages_run": stages_run,
                "exit_codes": exit_codes,
                "boundary": boundary,
                "events": events,
            }

        # Stage toggle: a disabled stage is never launched.
        if next_stage not in enabled:
            boundary = f"disabled:{next_stage}"
            return {
                "success": True,
                "exit_code": 0,
                "source_id": source_id,
                "state": state,
                "failed_stage": None,
                "next_stage": next_stage,
                "stages_run": stages_run,
                "exit_codes": exit_codes,
                "boundary": boundary,
                "events": events,
            }

        # Guided mode: after the first stage, pause before the next one.
        if not auto and stages_run:
            answer = confirm_fn(
                f"Proceed to run stage '{next_stage}' for {source_id}? (Y/N): "
            ).strip().lower()
            if answer != "y":
                boundary = "paused"
                return {
                    "success": True,
                    "exit_code": 2,
                    "source_id": source_id,
                    "state": state,
                    "failed_stage": None,
                    "next_stage": next_stage,
                    "stages_run": stages_run,
                    "exit_codes": exit_codes,
                    "boundary": boundary,
                    "events": events,
                }

        result = launch_stage(next_stage, source_id, timeout=timeout)
        log_manager_entry(
            source_id,
            result["stage"],
            result["command"],
            result["exit_code"],
            result["success"],
            error=result["error"],
        )
        events.append(result)

        if not result["success"]:
            boundary = f"failed:{result['stage']}"
            return {
                "success": False,
                "exit_code": 1,
                "source_id": source_id,
                "state": "failed",
                "failed_stage": result["stage"],
                "next_stage": result["stage"],
                "stages_run": stages_run,
                "exit_codes": exit_codes,
                "boundary": boundary,
                "events": events,
            }

        stages_run.append(result["stage"])
        exit_codes[result["stage"]] = result["exit_code"]

        # No-progress guard: a successful launch must advance the state.
        after = state_for(source_id)
        if after["state"] == state and after["state"] != "corpus_available":
            boundary = "no_progress"
            return {
                "success": False,
                "exit_code": 1,
                "source_id": source_id,
                "state": state,
                "failed_stage": result["stage"],
                "next_stage": result["stage"],
                "stages_run": stages_run,
                "exit_codes": exit_codes,
                "boundary": boundary,
                "events": events,
            }

    return {
        "success": True,
        "exit_code": 0,
        "source_id": source_id,
        "state": "corpus_available",
        "failed_stage": None,
        "next_stage": None,
        "stages_run": stages_run,
        "exit_codes": exit_codes,
        "boundary": boundary,
        "events": events,
    }


# ============================================================
# Rendering (centralized console output)
# ============================================================
# All user-facing console formatting lives here. The public API functions
# return structured data; these functions convert that data to text. The
# GUI will not use these; it consumes the structured data directly.

def render_status_line(source_id, data):
    """Render one line from a structured status/report dict."""
    return f"Source: {source_id}\nState: {data['state']}"


def render_dry_run(source_id, data):
    """Render a dry-run result (structured dict from dry_run())."""
    lines = [f"Source: {source_id}", f"State: {data['state']}"]
    if data["boundary"]:
        lines.append(f"Boundary: {data['boundary']}")
    if data["plan"]:
        lines.append(f"Would run: {', '.join(data['plan'])}")
    else:
        lines.append("Would run: (none)")
    lines.append("(dry run — no stages launched, no artifacts written)")
    return "\n".join(lines)


def render_stage_event(source_id, event):
    """Render one stage event (from a pipeline run)."""
    lines = [f"\nStage: {event['stage']}"]
    cmd = " ".join(event["command"]) if event["command"] else "(none)"
    lines.append(f"Command: {cmd}")
    lines.append(f"Exit code: {event['exit_code']}")
    lines.append(f"Success: {event['success']}")
    if event.get("stderr"):
        for line in event["stderr"].splitlines():
            lines.append(f"  stderr: {line}")
    if event.get("error"):
        lines.append(f"Error: {event['error']}")
    return "\n".join(lines)


def render_pipeline(source_id, data):
    """Render a structured pipeline result to console text."""
    lines = []
    for event in data["events"]:
        lines.append(render_stage_event(source_id, event))
    if data["state"] == "corpus_available":
        lines.append("Result: CORPUS_AVAILABLE")
    elif data["boundary"] == "paused":
        lines.append("Pipeline paused by user.")
        lines.append(f"Paused after: {', '.join(data['stages_run']) or '(start)'}")
    elif data["state"] == "failed":
        lines.append("Result: FAILED")
        lines.append("Recovery: fix the cause, then re-run --run <stage> "
                     "or --pipeline.")
    elif data["boundary"] == "no_progress":
        lines.append(f"No state change after '{data['failed_stage']}'; stopping.")
        lines.append("Result: STOPPED")
    elif data["boundary"] == "stopped":
        lines.append("Result: STOPPED")
    elif data["boundary"] == "disabled:" + (data.get("next_stage") or ""):
        lines.append(f"Result: STOPPED (stage '{data.get('next_stage')}' is disabled)")
    elif data["boundary"] and data["boundary"].startswith("unsupported:"):
        lines.append(f"Result: STOPPED (next action '{data['boundary'].split(':',1)[1]}' "
                     f"is not an automated stage)")
    if data["stages_run"]:
        lines.append(f"\nStages run: {', '.join(data['stages_run'])}")
    if data["exit_codes"]:
        lines.append(f"Exit codes: {data['exit_codes']}")
    return "\n".join(lines)


def render_run_stage(source_id, stage, result, after_info):
    """Render a manual --run stage result plus the refreshed status."""
    lines = [f"Source: {source_id}", f"Stage: {stage}"]
    cmd = " ".join(result["command"]) if result["command"] else "(none)"
    lines.append(f"Command: {cmd}")
    lines.append(f"Exit code: {result['exit_code']}")
    lines.append(f"Success: {result['success']}")
    if result.get("stderr"):
        lines.append("stderr:")
        for line in result["stderr"].splitlines():
            lines.append(f"  {line}")
    if result.get("error"):
        lines.append(f"Error: {result['error']}")
    if result.get("stdout"):
        lines.append("stdout (last lines):")
        for line in result["stdout"].splitlines()[-20:]:
            lines.append(f"  {line}")
    lines.append("")
    lines.append(format_report(source_id, after_info))
    return "\n".join(lines)


# ============================================================
# CLI-facing pipeline wrapper
# ============================================================
# run_pipeline is retained for backward compatibility: it delegates to the
# structured pipeline() engine and prints the rendered output, returning
# the exit code. New callers (GUI) should use pipeline() directly.

def run_pipeline(source_id, auto=False, timeout=None, confirm_fn=None,
                 enabled=None, dry_run=False):
    """
    Run the processing pipeline for one source to a validated corpus.

    Thin CLI wrapper around pipeline(). Executes the pipeline engine and
    prints the rendered output.

    Returns:
        int exit code:
            0  corpus_available reached (or already complete)
            1  failure / intake boundary / no progress
            2  paused by user (guided mode)
    """
    data = pipeline(
        source_id,
        auto=auto,
        timeout=timeout,
        confirm_fn=confirm_fn,
        enabled=enabled,
        dry_run=dry_run,
    )
    if dry_run:
        print(render_dry_run(source_id, data))
    else:
        print(render_pipeline(source_id, data))
    return data["exit_code"]


# ============================================================
# Entry point
# ============================================================

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="production_manager.py",
        description="Japanese Corpus Pipeline - Production Manager "
                    "(state reader, stage launcher, pipeline orchestrator)",
    )
    parser.add_argument(
        "--source",
        required=True,
        help="source_id to report pipeline state for.",
    )
    parser.add_argument(
        "--run",
        choices=STAGE_NAMES,
        default=None,
        help="run one stage for the source (clean, jobs, requests, api, corpus).",
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="run the pipeline for the source to a validated corpus.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="with --pipeline, run all remaining stages without pauses.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="optional subprocess timeout in seconds.",
    )
    parser.add_argument(
        "--enable",
        default=None,
        help="comma-separated stages allowed to run (e.g. clean,jobs).",
    )
    parser.add_argument(
        "--disable",
        default=None,
        help="comma-separated stages to skip (e.g. api).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="with --pipeline, print the planned stages without launching.",
    )
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        enabled = resolve_enabled(args.enable, args.disable)
    except ManagerError as exc:
        print(f"Error: {exc}")
        return 1

    if args.pipeline:
        data = pipeline(
            args.source,
            auto=args.auto,
            timeout=args.timeout,
            enabled=enabled,
            dry_run=args.dry_run,
        )
        if args.dry_run:
            print(render_dry_run(args.source, data))
        else:
            print(render_pipeline(args.source, data))
        return data["exit_code"]

    if args.run is None:
        data = status(args.source, enabled=enabled)
        print(format_report(args.source, {
            "state": data["state"],
            "failed_stage": data["failed_stage"],
            "next_stage": data["next_stage"],
            "evidence": data["evidence"],
        }, enabled=enabled))
        return 0

    # Manual stage execution (no pipeline automation).
    result = run_stage(args.source, args.run, timeout=args.timeout,
                       enabled=enabled)
    log_manager_entry(
        args.source,
        result["stage"],
        result["command"],
        result["exit_code"],
        result["success"],
        error=result["error"],
    )

    after_info = state_for(args.source)
    print(render_run_stage(args.source, args.run, result, after_info))

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
