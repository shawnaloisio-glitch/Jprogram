#!/usr/bin/env python3
"""
diagnostics.py

Japanese Corpus Pipeline - Troubleshooting dump.

Creates a self-contained, compressed diagnostic bundle the user sends to
OC/AI. Read-only: it never modifies or deletes source artifacts.

Contents per source:
- identity (human label, source_id, collection, episode)
- Production Manager report() (state, failed stage, failure reason, evidence)
- relevant artifacts (source package, registry, cleaning job/result,
  cleaned artifact, job builder result + jobs, request builder result +
  requests, processing results, corpus result)
- logs (cleaner, job builder, request builder, API/deepseek, corpus, PM)
- environment (versions + configuration values needed for reproduction)
"""

import gzip
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Source Builder"))
sys.path.insert(0, str(PROJECT_ROOT / "Production Manager"))

import paths
import production_manager as pm

DIAGNOSTICS_DIR = paths.DIAGNOSTICS


def _read_text(path):
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None


def _read_json(path):
    text = _read_text(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _artifact_paths(source_id):
    """Return a dict of known artifact paths for a source_id."""
    return {
        "registry": pm.registry_path(source_id),
        "cleaning_job": pm.cleaning_job_path(source_id),
        "cleaning_result": pm.cleaning_result_path(source_id),
        "cleaned_artifact": pm.cleaned_artifact_path(source_id),
        "job_builder_result": pm.job_result_path(source_id),
        "request_builder_result": pm.request_result_path(source_id),
        "processing_result": pm.processing_result_path(source_id),
        "corpus_result": pm.corpus_result_path(source_id),
        "jsonl": pm.jsonl_path(source_id),
    }


def _log_paths(source_id):
    """Return candidate log paths for a source_id."""
    return {
        "cleaner": paths.LOG_TRANSCRIPT_CLEANER / f"{source_id}.cleaner.log",
        "subtitle_cleaner": paths.LOG_SUBTITLE_CLEANER / f"{source_id}.cleaner.log",
        "job_builder": paths.LOG_JOB_BUILDER / f"{source_id}.job_builder.log",
        "request_builder": paths.LOG_REQUEST_BUILDER / f"{source_id}.request_builder.log",
        "deepseek": paths.LOG_DEEPSEEK_CLIENT / f"{source_id}.deepseek_client.log",
        "corpus_builder": paths.LOG_CORPUS_BUILDER / f"{source_id}.corpus_builder.log",
        "production_manager": paths.LOG_PRODUCTION_MANAGER / f"{source_id}.production_manager.log",
    }


def collect_source_bundle(source_id, package=None):
    """
    Collect the diagnostic bundle for one source.

    Input: source_id (str), package (dict|None - source package if present).
    Output: dict (serializable).
    """
    bundle = {"source_id": source_id}

    # Identity
    identity = {"source_id": source_id}
    if package is not None:
        identity["label"] = None  # filled by caller or derived below
        identity["collection_id"] = package.get("collection_id")
        identity["episode"] = package.get("episode")
        identity["source_name"] = package.get("source_name")
        identity["canonical_path"] = package.get("canonical_path")
    bundle["identity"] = identity

    # Pipeline state
    try:
        bundle["report"] = pm.report(source_id)
    except Exception as exc:
        bundle["report"] = {"error": str(exc)}

    # Artifacts (best-effort; missing files are omitted)
    artifacts = {}
    for name, path in _artifact_paths(source_id).items():
        path = Path(path)
        if path.is_file():
            if path.suffix.lower() == ".json":
                value = _read_json(path)
            else:
                value = _read_text(path)
            artifacts[name] = value
    bundle["artifacts"] = artifacts

    # Job / request sub-folders
    jobs = {}
    jobs_dir = pm.jobs_dir(source_id)
    if jobs_dir.is_dir():
        for job_file in sorted(jobs_dir.glob("*.json")):
            jobs[job_file.name] = _read_json(job_file)
    bundle["jobs"] = jobs

    requests = {}
    requests_dir = pm.requests_dir(source_id)
    if requests_dir.is_dir():
        for request_file in sorted(requests_dir.glob("*.json")):
            requests[request_file.name] = _read_json(request_file)
    bundle["requests"] = requests

    responses = {}
    responses_dir = pm.responses_dir(source_id)
    if responses_dir.is_dir():
        for response_file in sorted(responses_dir.glob("*.json")):
            responses[response_file.name] = _read_json(response_file)
    bundle["responses"] = responses

    # Logs
    logs = {}
    for name, path in _log_paths(source_id).items():
        path = Path(path)
        if path.is_file():
            logs[name] = _read_text(path)
    bundle["logs"] = logs

    return bundle


def collect_environment():
    """Collect environment + configuration needed for reproduction."""
    try:
        import project_config as pc
        config_values = {}
        for key in ("PROJECT_VERSION", "MODEL_NAME", "API_BASE_URL",
                    "API_CHAT_ENDPOINT", "API_TIMEOUT", "API_THINKING_TYPE",
                    "API_REASONING_EFFORT", "API_JSON_RESPONSE",
                    "API_MAX_TOKENS", "API_MAX_RETRIES", "API_RETRY_DELAY",
                    "MAX_JOB_CHARACTERS", "JOB_NUMBER_DIGITS",
                    "PROCESSING_PROFILES", "CLEANER_VERSIONS",
                    "DEFAULT_LANGUAGE"):
            if hasattr(pc, key):
                config_values[key] = getattr(pc, key)
    except Exception as exc:
        config_values = {"error": str(exc)}

    import platform
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "project_root": str(PROJECT_ROOT),
        "config": config_values,
    }


def build_dump(source_ids, packages=None):
    """
    Build the full diagnostic bundle dict.

    Input:
        source_ids (list of str),
        packages (list of dict|None) - source packages aligned by source_id.

    Output: dict with "created_at", "environment", "sources".
    """
    packages_by_id = {}
    if packages:
        for package in packages:
            packages_by_id[package.get("source_id")] = package

    sources = []
    for source_id in source_ids:
        bundle = collect_source_bundle(source_id,
                                       packages_by_id.get(source_id))
        sources.append(bundle)

    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "environment": collect_environment(),
        "sources": sources,
    }


def write_dump(dump, label=""):
    """
    Write the diagnostic bundle as one gzipped JSON file.

    Input: dump (dict), label (str) - short human label for the filename.
    Output: the written Path (Diagnostics\\processing_dump_<label>_<ts>.json.gz).
    """
    DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
    safe_label = "".join(c for c in str(label) if c.isalnum() or c in "-_") or "sources"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    target = DIAGNOSTICS_DIR / f"processing_dump_{safe_label}_{timestamp}.json.gz"
    payload = json.dumps(dump, ensure_ascii=False, indent=2).encode("utf-8")
    with gzip.open(target, "wb") as file:
        file.write(payload)
    return target


__all__ = [
    "DIAGNOSTICS_DIR",
    "collect_source_bundle",
    "collect_environment",
    "build_dump",
    "write_dump",
]
