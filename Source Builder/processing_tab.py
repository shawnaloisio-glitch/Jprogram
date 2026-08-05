#!/usr/bin/env python3
"""
processing_tab.py

Japanese Corpus Pipeline - Processing tab (GUI support layer).

Presents source packages as human-labeled rows and drives the existing
pipeline through the Production Manager's public functions. It never exposes
source_ids, artifact paths, JSON files, folders, or individual pipeline
stages to the user.

Responsibilities ONLY:
- enumerate source packages (Sources\\collections\\*\\*.source.json and
  Sources\\standalone\\*.source.json),
- build human labels (collection display name + episode / standalone name),
- map Production Manager state to one simple status label,
- run the existing pipeline sequentially for selected sources,
- retry failed sources.

It does NOT:
- modify Cleaner / Job Builder / Processor / schemas,
- create duplicate pipeline logic,
- redesign any stage,
- write artifacts other than through the existing pipeline functions.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Source Builder"))
sys.path.insert(0, str(PROJECT_ROOT / "Production Manager"))

import config_loader
import paths
import production_manager as pm


class ProcessingTabError(Exception):
    """Raised when the processing tab cannot enumerate or run sources."""


# Simple status labels shown to the user (never raw stage names).
STATUS_PENDING = "Pending"        # package exists, not yet sent/registered
STATUS_READY = "Ready"            # registered; pipeline not run to completion
STATUS_PROCESSING = "Processing"
STATUS_COMPLETE = "Complete"      # corpus_available
STATUS_FAILED = "Failed"


def _display_name_for_collection(collection_id):
    """Return the human display name for a collection_id, or the id."""
    try:
        for collection in config_loader.load_collections():
            if collection["collection_id"] == collection_id:
                return collection.get("name") or collection_id
    except Exception:
        pass
    return collection_id


def human_label(package):
    """
    Return a human-readable label for a source package.

    Collection: "<collection display name> — Episode <N>"
    Standalone: "<source_name>"

    Input: package (dict, validated source package).
    Output: str.
    """
    collection_id = package.get("collection_id")
    if collection_id:
        name = _display_name_for_collection(collection_id)
        episode = package.get("episode")
        if episode is not None:
            return f"{name} — Episode {episode}"
        return name
    source_name = package.get("source_name")
    if source_name:
        return str(source_name)
    return package.get("source_id", "Unknown")


def _episode_number(package):
    """Return a package's numeric episode, or 0 when missing/invalid."""
    try:
        return int(package.get("episode", 0))
    except (TypeError, ValueError):
        return 0


def _sort_key(package):
    """Sort packages by collection, then numeric episode, then label."""
    return (
        package.get("collection_id") or "",
        _episode_number(package),
        human_label(package),
        package.get("source_id", ""),
    )


def discover_packages(sources_root=None):
    """
    Enumerate all source packages on disk.

    Input: sources_root (Path|None, default the canonical Sources\\ store).
    Output: list of package dicts (validated), grouped by collection and
    ordered by numeric episode within a collection.
    """
    if sources_root is not None:
        root = Path(sources_root)
    else:
        import controller as _controller
        root = _controller.SOURCES_ROOT
    packages = []
    for pattern in ("collections", "standalone"):
        base = root / pattern
        if not base.is_dir():
            continue
        # Collection packages live one level deep (<collection>/<file>);
        # standalone packages live directly in the folder.
        search = base.rglob("*.source.json") if pattern == "collections" \
            else base.glob("*.source.json")
        for package_file in search:
            try:
                package = json.loads(package_file.read_text(encoding="utf-8-sig"))
            except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                continue
            if isinstance(package, dict) and package.get("source_id"):
                packages.append(package)
    packages.sort(key=_sort_key)
    return packages


def completed_corpora(sources_root=None):
    """
    Return the source packages that have a completed corpus (JSONL exists).

    Reuses discover_packages and the Production Manager jsonl path. Used by
    the Analysis tab to list available corpora.

    Input: sources_root (Path|None, default the canonical Sources\\ store).
    Output: list of package dicts with a corpus, sorted by label.
    """
    completed = []
    for package in discover_packages(sources_root):
        source_id = package.get("source_id", "")
        if not source_id:
            continue
        if pm.jsonl_path(source_id).is_file():
            completed.append(package)
    return completed


def package_to_row(package):
    """
    Build a display row for a source package.

    Input: package (dict).
    Output: dict:
        {
            "label": str,
            "source_id": str,   # internal; never displayed
            "package": package,
        }
    """
    return {
        "label": human_label(package),
        "source_id": package.get("source_id", ""),
        "package": package,
    }


def simple_status(package, state_info=None):
    """
    Map Production Manager state to one simple status label.

    Input:
        package (dict),
        state_info (dict|None) - result of ProductionManager.state_for, or
        None to compute it.

    Output: (label, failed_message) where label is one of STATUS_* and
    failed_message is a plain-language explanation when failed.
    """
    if state_info is None:
        state_info = pm.state_for(package.get("source_id", ""))
    state = state_info.get("state")

    if state == "corpus_available":
        return STATUS_COMPLETE, ""
    if state == "failed":
        message = friendly_failure_message(state_info)
        return STATUS_FAILED, message
    if state == "unregistered":
        return STATUS_PENDING, ""
    # registered / waiting_for_clean / cleaned / jobs_created /
    # requests_created / api_processing / api_complete
    return STATUS_READY, ""


def friendly_failure_message(state_info):
    """
    Build a plain-language failure message (no technical stage names).

    Input: state_info (dict from ProductionManager.state_for).
    Output: str like "Failed during AI processing".
    """
    failed_stage = state_info.get("failed_stage")
    if failed_stage == "api":
        return "Failed during AI processing"
    if failed_stage == "corpus":
        return "Failed while producing the final output"
    if failed_stage == "requests":
        return "Failed while preparing the request"
    if failed_stage == "jobs":
        return "Failed while preparing the work"
    if failed_stage == "clean":
        return "Failed while preparing the source"
    return "Failed during processing"


def process_sources(packages, timeout=None):
    """
    Run the existing pipeline sequentially for each source package.

    For each package, if it has no Source Registry / Cleaning Job yet, the
    existing Source Builder handoff is run first (creates Registry + Cleaning
    Job), then the Production Manager pipeline runs clean -> jobs -> requests
    -> api -> corpus. Sequential only; no parallelism.

    Input: packages (list of dicts - source packages), timeout (int|None).
    Output: list of dicts:
        [{"source_id": str, "success": bool, "state": str,
          "failed_stage": str|None, "message": str}, ...]
    """
    results = []
    for package in packages:
        source_id = package.get("source_id", "")
        _ensure_registered(package)
        result = pm.pipeline(
            source_id,
            auto=True,
            timeout=timeout,
            confirm_fn=lambda _prompt: "y",
            collect_events=False,
        )
        state_info = pm.state_for(source_id)
        label, failed_message = simple_status({}, state_info)
        results.append({
            "source_id": source_id,
            "success": bool(result.get("success")),
            "state": result.get("state") or state_info.get("state"),
            "failed_stage": result.get("failed_stage"),
            "message": failed_message if not result.get("success")
            else "",
        })
    return results


def _ensure_registered(package):
    """
    Run the Source Builder handoff when a package has no registry entry.

    This is additive orchestration: it reuses the existing handoff module to
    create the Registry entry + Cleaning Job, then the pipeline proceeds. It
    does not modify any pipeline contract.
    """
    source_id = package.get("source_id", "")
    if not source_id:
        return
    registry_exists = pm.registry_path(source_id).is_file()
    if registry_exists:
        return
    import handoff as _handoff
    _handoff.handoff(package)


def failed_sources(packages):
    """
    Return the subset of packages whose pipeline state is failed.

    Input: packages (list of dicts).
    Output: list of package dicts.
    """
    failed = []
    for package in packages:
        state_info = pm.state_for(package.get("source_id", ""))
        label, _ = simple_status(package, state_info)
        if label == STATUS_FAILED:
            failed.append(package)
    return failed


def run_analysis(package, output_dir=None):
    """
    Run a basic analysis for a corpus-ready source.

    Reads the canonical JSONL (existing corpus output), runs the frequency
    analyzer, and writes a JSON report. Analysis is independent; no
    processing artifact is modified.

    Input:
        package (dict),
        output_dir (Path|None, default Analysis\\outputs).

    Output: dict {"output_path": str, "summary": dict}.
    Raises: ProcessingTabError when the source has no corpus or analysis
    fails.
    """
    source_id = package.get("source_id", "")
    jsonl_path = pm.jsonl_path(source_id)
    if not jsonl_path.is_file():
        raise ProcessingTabError(
            f"No corpus available for {source_id}.")

    sys.path.insert(0, str(PROJECT_ROOT / "Analysis"))
    try:
        import corpus_loader
        from frequency_analyzer import analyze
    except ImportError as exc:
        raise ProcessingTabError(f"Analysis tools unavailable: {exc}")

    try:
        records = corpus_loader.load_all(jsonl_path)
        result = analyze(records)
    except Exception as exc:
        raise ProcessingTabError(f"Analysis failed: {exc}")

    if output_dir is None:
        output_dir = paths.ANALYSIS_OUTPUTS
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{source_id}.frequency.json"

    import json as _json
    _json.dump(result, output_path.open("w", encoding="utf-8"),
               ensure_ascii=False, indent=2)
    summary = result.get("summary", {})
    return {"output_path": str(output_path), "summary": summary}


__all__ = [
    "ProcessingTabError",
    "STATUS_PENDING",
    "STATUS_READY",
    "STATUS_PROCESSING",
    "STATUS_COMPLETE",
    "STATUS_FAILED",
    "human_label",
    "discover_packages",
    "completed_corpora",
    "package_to_row",
    "simple_status",
    "friendly_failure_message",
    "process_sources",
    "failed_sources",
    "run_analysis",
]
