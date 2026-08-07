"""
project_config.py

Global configuration for the Japanese Corpus Pipeline.

Only place user-adjustable settings here.

All scripts should import configuration values from this file.
"""

# ==================================================
# Project Versions
# ==================================================

PROJECT_VERSION = "1.0"

JOB_FORMAT_VERSION = "1.0"

PROCESSOR_VERSION = "1.0"

# ==================================================
# Job Builder
# ==================================================

# Maximum number of Japanese characters per API job.
# (Approximate limit. Jobs are split on line boundaries.)

MAX_JOB_CHARACTERS = 10000

# Number of digits used when numbering jobs.
# Example:
# 000001
# 000002

JOB_NUMBER_DIGITS = 6

# ==================================================
# Supported File Types
# ==================================================

TRANSCRIPT_EXTENSION = ".txt"

SUBTITLE_EXTENSION = ".srt"

CLEAN_EXTENSION = ".clean.txt"

JOB_EXTENSION = ".json"

JSONL_EXTENSION = ".jsonl"

# ==================================================
# Logging
# ==================================================

LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ==================================================
# Processing
# ==================================================

# Skip files that have already been processed.

SKIP_EXISTING = True

# Ask for confirmation before processing.

CONFIRM_BEFORE_PROCESSING = True

# Copy cleaned files into the processing folder.

COPY_TO_PROCESSING = True

# ==================================================
# Validation
# ==================================================

# Verify that every generated job contains at least one line.

REQUIRE_NONEMPTY_JOB = True

# Verify that line numbering is continuous.

VERIFY_LINE_SEQUENCE = True

# ==================================================
# API
# ==================================================

# DeepSeek model used for all parser requests.

MODEL_NAME = "deepseek-v4-flash"

# DeepSeek API base URL.

API_BASE_URL = "https://api.deepseek.com"

# DeepSeek chat completions endpoint.

API_CHAT_ENDPOINT = "https://api.deepseek.com/chat/completions"

# Seconds to wait for an API response before timing out.

API_TIMEOUT = 60

# Thinking mode control: "enabled" or "disabled".
# "disabled" requests a direct response without chain-of-thought reasoning.
# Production default is non-thinking (frozen architecture).

API_THINKING_TYPE = "disabled"

# Reasoning effort when thinking mode is enabled: "low", "high", or "max".
# Frozen architecture: non-thinking mode; reasoning effort is NOT sent.

API_REASONING_EFFORT = None

# Force the API to return valid JSON (response_format json_object).
# Production default is enabled (frozen architecture).

API_JSON_RESPONSE = True

# Explicit output token cap for parser requests. Non-thinking mode defaults
# to an 8,192-token output cap; the frozen parser config requires 32768.

API_MAX_TOKENS = 32768

# Number of automatic retries for transient API failures.

API_MAX_RETRIES = 3

# Seconds between retries.

API_RETRY_DELAY = 5

# Per-model expression extraction capability.
#
# Expression extraction is enrichment data and is NOT required for
# successful corpus generation. Some models (e.g., DeepSeek Flash) produce
# unreliable expression spans. When a model is marked disabled here, the
# Request Builder instructs the parser to always emit an empty expressions
# array, and the validator/corpus builder accept empty arrays. The JSONL
# schema is unchanged.
#
# Unknown models default to enabled so a future capable model (DeepSeek
# Think, GPT, Claude, ...) re-enables expressions without any pipeline
# change.

MODEL_EXPRESSIONS_ENABLED = {
    "deepseek-v4-flash": False,
}


def expressions_enabled(model_name=None):
    """
    Return whether expression extraction is enabled for a model.

    Input: model_name (str or None); defaults to MODEL_NAME.
    Output: True when expressions are enabled for that model.
    """
    if model_name is None:
        model_name = MODEL_NAME
    return MODEL_EXPRESSIONS_ENABLED.get(model_name, True)


# ==================================================
# Source Intake
# ==================================================

# Supported source types (the intrinsic nature of the content).
# source_type is separate from cleaning_profile.

SOURCE_TYPES = frozenset({
    "anime_subtitle",
    "podcast_transcript",
})

# Supported cleaning profiles (the cleaning procedure to apply).

CLEANING_PROFILES = frozenset({
    "subtitle_standard_v1",
    "transcript_standard_v1",
})

# Processing profile mapping:
# source_type -> {"cleaning_profile": str, "cleaner": str}

PROCESSING_PROFILES = {
    "anime_subtitle": {
        "cleaning_profile": "subtitle_standard_v1",
        "cleaner": "clean_subtitles",
    },
    "podcast_transcript": {
        "cleaning_profile": "transcript_standard_v1",
        "cleaner": "clean_transcript",
    },
}

# Cleaning profile version mapping:
# cleaning_profile -> version string

CLEANER_VERSIONS = {
    "subtitle_standard_v1": "1.0",
    "transcript_standard_v1": "1.0",
}

# Source type -> raw directory name mapping.

SOURCE_TYPE_RAW_DIR = {
    "anime_subtitle": "Raw Subtitles",
    "podcast_transcript": "Raw Transcripts",
}

# Extension appended to the source_id for the cleaned artifact.

CLEANED_ARTIFACT_EXTENSION = ".clean.txt"

# Default language for registered sources.

DEFAULT_LANGUAGE = "ja"

# Material level vocabulary for per-source metadata.
# (level, display_name) pairs. This is the single source of truth for
# these rows; no other module keeps its own copy.

MATERIAL_LEVELS = (
    (0, "Ungraded"),
    (1, "Absolute Beginner"),
    (2, "Beginner"),
    (3, "Intermediate"),
    (4, "Advanced"),
)

# ==================================================
# Cleaning Transformations
# ==================================================

# Per-profile enabled transformation flags.
#
# Configuration controls which deterministic mechanical transformations
# apply to each cleaning profile. It does NOT contain linguistic rules,
# Japanese token handling, normalization rules, transliteration, or
# furigana logic - those remain in the cleaner implementation.

CLEANING_TRANSFORMS = {
    "subtitle_standard_v1": {
        "strip_bom": True,
        "trim_lines": True,
        "remove_subtitle_numbers": True,
        "remove_timecodes": True,
        "collapse_blank_lines": True,
        "collapse_repeated_spaces": False,
    },
    "transcript_standard_v1": {
        "strip_bom": True,
        "trim_lines": True,
        "remove_subtitle_numbers": False,
        "remove_timecodes": False,
        "collapse_blank_lines": True,
        "collapse_repeated_spaces": True,
    },
}


def validate_cleaning_transforms(cleaning_profiles=None,
                                 cleaning_transforms=None):
    """
    Validate the internal consistency of the cleaning transformation config.

    Checks that:
        - every cleaning profile has a transformation table,
        - every transformation value is a boolean.

    Parameters default to the module constants so the real configuration
    is validated; alternate tables can be passed for testing.

    Returns:
        True when valid.

    Raises:
        ValueError describing the first inconsistency found.
    """
    if cleaning_profiles is None:
        cleaning_profiles = CLEANING_PROFILES
    if cleaning_transforms is None:
        cleaning_transforms = CLEANING_TRANSFORMS

    for cleaning_profile in sorted(cleaning_profiles):

        transforms = cleaning_transforms.get(cleaning_profile)

        if transforms is None:
            raise ValueError(
                f"CLEANING_TRANSFORMS missing table for cleaning profile: "
                f"{cleaning_profile}"
            )

        if not isinstance(transforms, dict):
            raise ValueError(
                f"CLEANING_TRANSFORMS[{cleaning_profile}] must be a dict"
            )

        for flag, enabled in sorted(transforms.items()):

            if not isinstance(enabled, bool):
                raise ValueError(
                    f"CLEANING_TRANSFORMS[{cleaning_profile}][{flag}] "
                    f"must be a boolean"
                )

    for cleaning_profile in sorted(cleaning_transforms):

        if cleaning_profile not in cleaning_profiles:
            raise ValueError(
                f"CLEANING_TRANSFORMS references unknown cleaning profile: "
                f"{cleaning_profile}"
            )

    return True


def validate_source_intake_config(
    source_types=None,
    cleaning_profiles=None,
    processing_profiles=None,
    cleaner_versions=None,
    source_type_raw_dir=None,
):
    """
    Validate the internal consistency of the Source Intake configuration.

    Checks that:
        - every PROCESSING_PROFILES profile is a known cleaning profile,
        - every PROCESSING_PROFILES profile has a cleaner version,
        - every source type in PROCESSING_PROFILES has a raw directory
          mapping,
        - every PROCESSING_PROFILES source type is a known source type,
        - every cleaning profile has a cleaner version.

    Parameters default to the module constants so the real configuration
    is validated; alternate tables can be passed for testing.

    Returns:
        True when valid.

    Raises:
        ValueError describing the first inconsistency found.
    """
    if source_types is None:
        source_types = SOURCE_TYPES
    if cleaning_profiles is None:
        cleaning_profiles = CLEANING_PROFILES
    if processing_profiles is None:
        processing_profiles = PROCESSING_PROFILES
    if cleaner_versions is None:
        cleaner_versions = CLEANER_VERSIONS
    if source_type_raw_dir is None:
        source_type_raw_dir = SOURCE_TYPE_RAW_DIR

    for source_type, profile in sorted(processing_profiles.items()):

        if source_type not in source_types:
            raise ValueError(
                f"PROCESSING_PROFILES references unknown source type: "
                f"{source_type}"
            )

        cleaning_profile = profile["cleaning_profile"]

        if cleaning_profile not in cleaning_profiles:
            raise ValueError(
                f"PROCESSING_PROFILES references unknown cleaning profile: "
                f"{cleaning_profile}"
            )

        if cleaning_profile not in cleaner_versions:
            raise ValueError(
                f"CLEANER_VERSIONS missing version for cleaning profile: "
                f"{cleaning_profile}"
            )

        if source_type not in source_type_raw_dir:
            raise ValueError(
                f"SOURCE_TYPE_RAW_DIR missing mapping for source type: "
                f"{source_type}"
            )

    for cleaning_profile in sorted(cleaning_profiles):

        if cleaning_profile not in cleaner_versions:
            raise ValueError(
                f"CLEANER_VERSIONS missing version for cleaning profile: "
                f"{cleaning_profile}"
            )

    return True


# Validate the Source Intake configuration at import time (fail fast).

validate_source_intake_config()

# Validate the cleaning transformation configuration at import time
# (fail fast).

validate_cleaning_transforms()

# ==================================================
# Future Options
# ==================================================

# Reserved for future configuration settings.
#
# Examples:
#
# TEMPERATURE
# TOKEN_LIMIT
# MAX_OUTPUT_TOKENS
# etc.