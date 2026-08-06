"""
paths.py

Central location for all project paths.

Every project script imports paths from here.

Product/repository folders stay under PROJECT_ROOT. Customer/runtime/log
folders live under WORKSPACE_ROOT (outside the repository by default; the
JPROGRAM_WORKSPACE environment variable overrides the default location).
"""

import os

from pathlib import Path


# --------------------------------------------------
# Project Information
# --------------------------------------------------

PROJECT_NAME = "Japanese Corpus Pipeline"


# --------------------------------------------------
# Project Root
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent


# --------------------------------------------------
# Workspace Root
# --------------------------------------------------
#
# Customer/runtime data lives outside the repository by default. The
# JPROGRAM_WORKSPACE environment variable overrides the default location.

WORKSPACE_ROOT = Path(
    os.environ.get(
        "JPROGRAM_WORKSPACE",
        PROJECT_ROOT.parent / "Jprogram Workspace"
    )
)


# --------------------------------------------------
# Project Folders (repository / product)
# --------------------------------------------------

ANALYSIS = PROJECT_ROOT / "Analysis"

DATA_PROCESSOR = PROJECT_ROOT / "Data Processor"

PROMPTS = PROJECT_ROOT / "Prompts"

TRANSCRIPT_CLEANER = PROJECT_ROOT / "Transcript Cleaner"


# --------------------------------------------------
# Customer / Runtime Folders (workspace)
# --------------------------------------------------

SOURCES = WORKSPACE_ROOT / "Sources"

SOURCE_REGISTRY = WORKSPACE_ROOT / "Source Registry"

CLEANING_JOBS = WORKSPACE_ROOT / "Cleaning Jobs"

CLEANING_RESULTS = WORKSPACE_ROOT / "Cleaning Results"

CLEANED_ARCHIVE = WORKSPACE_ROOT / "Cleaned Archive"

PROCESSING_RESULTS = WORKSPACE_ROOT / "Processing Results"

LOGS = WORKSPACE_ROOT / "Logs"

ANALYSIS_OUTPUTS = WORKSPACE_ROOT / "Analysis" / "outputs"

DIAGNOSTICS = WORKSPACE_ROOT / "Diagnostics"

INTAKE = WORKSPACE_ROOT / "Intake"

RAW_IMPORTS = WORKSPACE_ROOT / "Raw Imports"

# Customer/runtime configuration (workspace). Collections and origins are
# customer data; only source_types.json remains repository product config.
COLLECTIONS_CONFIG = WORKSPACE_ROOT / "Config" / "collections.json"

ORIGINS_CONFIG = WORKSPACE_ROOT / "Config" / "origins.json"


# --------------------------------------------------
# Data Processor Runtime Folders (workspace)
# --------------------------------------------------

COMPLETED = WORKSPACE_ROOT / "completed"

FAILED = WORKSPACE_ROOT / "failed"

INDEXES = WORKSPACE_ROOT / "indexes"

JOBS = WORKSPACE_ROOT / "jobs"

JOB_RESULTS = WORKSPACE_ROOT / "Job Results"

REQUESTS = WORKSPACE_ROOT / "requests"

REQUEST_RESULTS = WORKSPACE_ROOT / "Request Results"

JSONL = WORKSPACE_ROOT / "jsonl"

CORPUS_RESULTS = WORKSPACE_ROOT / "Corpus Results"

PROCESSING = WORKSPACE_ROOT / "processing"

RESPONSES = WORKSPACE_ROOT / "responses"


# --------------------------------------------------
# Log Folders (workspace)
# --------------------------------------------------

LOG_JOB_BUILDER = LOGS / "Job Builder"

LOG_SUBTITLE_CLEANER = LOGS / "Subtitle Cleaner"

LOG_TRANSCRIPT_CLEANER = LOGS / "Transcript Cleaner"

LOG_REQUEST_BUILDER = (
    LOGS / "Request Builder"
)

LOG_DEEPSEEK_CLIENT = LOGS / "DeepSeek Client"

LOG_CORPUS_BUILDER = LOGS / "Corpus Builder"

LOG_SOURCE_INTAKE = LOGS / "Source Intake"

LOG_PRODUCTION_MANAGER = LOGS / "Production Manager"


# --------------------------------------------------
# Workspace Folders (everything ensure_workspace must create)
# --------------------------------------------------

WORKSPACE_FOLDERS = (
    SOURCES,
    SOURCE_REGISTRY,
    CLEANING_JOBS,
    CLEANING_RESULTS,
    CLEANED_ARCHIVE,
    PROCESSING_RESULTS,
    LOGS,
    LOG_JOB_BUILDER,
    LOG_SUBTITLE_CLEANER,
    LOG_TRANSCRIPT_CLEANER,
    LOG_REQUEST_BUILDER,
    LOG_DEEPSEEK_CLIENT,
    LOG_CORPUS_BUILDER,
    LOG_SOURCE_INTAKE,
    LOG_PRODUCTION_MANAGER,
    ANALYSIS_OUTPUTS,
    DIAGNOSTICS,
    INTAKE,
    RAW_IMPORTS,
    COMPLETED,
    FAILED,
    INDEXES,
    JOBS,
    JOB_RESULTS,
    REQUESTS,
    REQUEST_RESULTS,
    JSONL,
    CORPUS_RESULTS,
    PROCESSING,
    RESPONSES,
)


# --------------------------------------------------
# Workspace Initialization
# --------------------------------------------------

def ensure_workspace():
    """
    Create WORKSPACE_ROOT and the workspace folders on demand.

    Idempotent (mkdir parents=True, exist_ok=True). Also invoked at
    import time so that any consumer (or test reading the real constants)
    finds the workspace folders present. Returns WORKSPACE_ROOT.
    """
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    for folder in WORKSPACE_FOLDERS:
        folder.mkdir(parents=True, exist_ok=True)
    return WORKSPACE_ROOT


# Self-initialize the workspace on import so all consumers see the
# workspace folders exist.
ensure_workspace()


# --------------------------------------------------
# Validation
# --------------------------------------------------

def verify_paths():
    """
    Verify that all required project and workspace folders exist.

    Creates the workspace folders first (ensure_workspace), then checks
    the full required set. Product folders under PROJECT_ROOT must exist;
    workspace folders are created if missing.
    """
    ensure_workspace()

    required = [
        ANALYSIS,
        DATA_PROCESSOR,
        PROMPTS,
        TRANSCRIPT_CLEANER,
        CLEANED_ARCHIVE,
        COMPLETED,
        FAILED,
        INDEXES,
        JOBS,
        JOB_RESULTS,
        JSONL,
        CORPUS_RESULTS,
        LOGS,
        LOG_JOB_BUILDER,
        LOG_REQUEST_BUILDER,
        LOG_DEEPSEEK_CLIENT,
        LOG_CORPUS_BUILDER,
        LOG_SOURCE_INTAKE,
        LOG_PRODUCTION_MANAGER,
        PROCESSING,
        REQUESTS,
        REQUEST_RESULTS,
        RESPONSES,
        PROCESSING_RESULTS,
        SOURCE_REGISTRY,
        CLEANING_JOBS,
        CLEANING_RESULTS,
        SOURCES,
        ANALYSIS_OUTPUTS,
        DIAGNOSTICS,
        INTAKE,
        RAW_IMPORTS,
    ]

    missing = [
        folder
        for folder in required
        if not folder.exists()
    ]

    if missing:

        print(f"\n{PROJECT_NAME}\n")
        print("ERROR: Missing required project items:\n")

        for folder in missing:
            print(f"  ✗ {folder}")

        raise SystemExit(1)
