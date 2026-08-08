#!/usr/bin/env python3
"""
corpus_builder.py

Japanese Corpus Pipeline - Corpus Builder

Deterministic stage that turns validated parser responses into the
canonical sentence-per-line JSONL corpus.

Pipeline flow for one source_id:
    - load jobs from jobs\\<source_id>\\, load the matching
      raw responses from responses\\<source_id>\\
    - verify job["source_id"] matches the requested source_id
    - extract the parser data from the response (choices[0].message.content
      for the DeepSeek path; the parsed dict directly for the deterministic
      path) and parse it
    - validate with response_validator (failures are logged and counted)
    - recompute character spans and chunk text from authoritative surfaces
    - assign canonical global IDs, sections, and provenance
    - verify exact source reconstruction (integrity gate)
    - write the canonical named sentence-per-line JSONL corpus atomically
    - write a Corpus Builder Result artifact (completion signal)

Frozen architecture (TASK 20 / TASK 21):
    - The LLM's character offsets are unreliable on Japanese; they are
      validated but NOT authoritative. Ordered word surfaces are
      authoritative because they exactly partition each sentence.
    - The Response Validator is a gate and never repairs output.
    - The Corpus Builder deterministically recomputes what the parser is
      demonstrably bad at calculating, and the job metadata is the
      authoritative source of identity.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "Data Processor"))

from datetime import datetime

from common import (
    ensure_folder,
    timestamp,
)

from paths import (
    CORPUS_RESULTS,
    JSONL,
    JOBS,
    LOG_CORPUS_BUILDER,
    PROCESSING_RESULTS,
    REQUESTS,
    RESPONSES,
)

from project_config import (
    MODEL_NAME,
    PROJECT_VERSION,
)

import corpus_builder_result
import response_validator

# Re-export canonicalization functions from the parser normalizer for
# backward compatibility (previously owned by this module).
from parser_normalizer import (
    CorpusBuilderError,
    canonicalize,
    canonical_sentence_texts,
    restore_sentence_text,
    verify_source_reconstruction,
    _expected_content,
)


PROGRAM_NAME = "Corpus Builder"
PROGRAM_VERSION = PROJECT_VERSION

RESPONSE_PREFIX = "response_"
REQUEST_PREFIX = "request_"
JOB_PREFIX = "job_"

DEFAULT_SECTION_ID = "default"

REQUIRED_PROVENANCE_FIELDS = (
    "source_id",
    "source",
    "source_file",
    "job_number",
    "model",
    "prompt_version",
)

def _is_int(value):
    """True for real integers (bools are not integers for our schema)."""
    return isinstance(value, int) and not isinstance(value, bool)


# ============================================================
# Builder Stage Functions (deterministic)
# ============================================================

def assign_global_ids(sentence, global_index):
    """
    Assign deterministic, canonical global IDs.

    Uses only canonical processing order:
        - global_index: the per-source sentence counter (next sentence id).
        - sentence order within the source (threaded counter).
        - word order within each sentence.
        - chunk order within each sentence.
        - expression order within each sentence.

    Parser-provided local indexes are preserved but never used as
    canonical identity.

    ID scheme (unique within a source; composite child IDs trace back to
    their parent sentence):
        sentence_id   = integer (the threaded global_index)
        word_id       = f"{sentence_id}.{word_position}"
        chunk_id      = f"{sentence_id}.c{chunk_position}"
        expression_id = f"{sentence_id}.e{expression_position}"

    Attaches the IDs to the returned sentence under the "ids" key:
        {
            "sentence_id": int,
            "word_ids": [str, ...],
            "chunk_ids": [str, ...],
            "expression_ids": [str, ...],
        }

    Verifies rather than trusts:
        - no duplicate IDs within the sentence
        - every child ID belongs to this sentence
        - every chunk/expression word span references a valid parent word

    Raises:
        CorpusBuilderError if the structure is invalid, the sentence
        already carries IDs (duplicate assignment), IDs would not be
        unique, or a referenced object has no valid parent.

    Returns:
        (global_index + 1, sentence with ids attached)
    """
    if not isinstance(sentence, dict):
        raise CorpusBuilderError("sentence must be a dict")

    if not (isinstance(global_index, int) and not isinstance(global_index, bool)):
        raise CorpusBuilderError("global_index must be an integer")
    if global_index < 0:
        raise CorpusBuilderError("global_index must be non-negative")

    if "ids" in sentence:
        raise CorpusBuilderError(
            "sentence already carries ids (duplicate assignment)."
        )

    text = sentence.get("text")
    if not isinstance(text, str) or not text:
        raise CorpusBuilderError("sentence text must be a non-empty string")

    words = sentence.get("words")
    chunks = sentence.get("chunks")
    expressions = sentence.get("expressions")
    for field, value in (
        ("words", words),
        ("chunks", chunks),
        ("expressions", expressions),
    ):
        if not isinstance(value, list):
            raise CorpusBuilderError(f"sentence {field} must be a list")

    word_count = len(words)
    chunk_count = len(chunks)
    expression_count = len(expressions)

    for wi, word in enumerate(words):
        if not isinstance(word, list) or len(word) != 5:
            raise CorpusBuilderError(
                f"words[{wi}] must be a 5-column record."
            )
    for ci, chunk in enumerate(chunks):
        if not isinstance(chunk, list) or len(chunk) != 4:
            raise CorpusBuilderError(
                f"chunks[{ci}] must be a 4-column record."
            )
        if not (_is_int(chunk[2]) and _is_int(chunk[3])):
            raise CorpusBuilderError(
                f"chunks[{ci}] start_word/end_word must be integers."
            )
        if chunk[2] < 0 or chunk[3] > word_count or chunk[2] >= chunk[3]:
            raise CorpusBuilderError(
                f"chunks[{ci}] word span does not reference valid words."
            )
    for ei, expression in enumerate(expressions):
        if not isinstance(expression, list) or len(expression) != 5:
            raise CorpusBuilderError(
                f"expressions[{ei}] must be a 5-column record."
            )
        if not (_is_int(expression[2]) and _is_int(expression[3])):
            raise CorpusBuilderError(
                f"expressions[{ei}] start_word/end_word must be integers."
            )
        if expression[2] < 0 or expression[3] > word_count or expression[2] >= expression[3]:
            raise CorpusBuilderError(
                f"expressions[{ei}] word span does not reference valid words."
            )

    sentence_id = global_index
    word_ids = [f"{sentence_id}.{wi}" for wi in range(word_count)]
    chunk_ids = [f"{sentence_id}.c{ci}" for ci in range(chunk_count)]
    expression_ids = [f"{sentence_id}.e{ei}" for ei in range(expression_count)]

    # Verification: no duplicate IDs; every child belongs to this sentence.
    all_ids = [sentence_id] + word_ids + chunk_ids + expression_ids
    if len(set(all_ids)) != len(all_ids):
        raise CorpusBuilderError(
            f"duplicate IDs assigned within sentence {sentence_id}."
        )
    for child_id in word_ids + chunk_ids + expression_ids:
        if not child_id.startswith(f"{sentence_id}."):
            raise CorpusBuilderError(
                f"child id {child_id!r} does not belong to sentence {sentence_id}."
            )

    result = dict(sentence)
    result["ids"] = {
        "sentence_id": sentence_id,
        "word_ids": word_ids,
        "chunk_ids": chunk_ids,
        "expression_ids": expression_ids,
    }
    return global_index + 1, result


def assign_sections(sentence, section_state):
    """
    Deterministically assign a section to a sentence.

    Uses only canonical processing order and preserved source metadata.
    Parser-generated section identifiers (if present) are ignored and
    replaced with the deterministic assignment.

    Section boundaries:
        section_state["boundaries"] is an optional, explicit, ordered list
        of boundary definitions:
            [ {"section": <section_id>, "start": <canonical sentence ordinal>}, ... ]
        Each boundary marks the canonical sentence ordinal where a section
        begins. A sentence belongs to the boundary with the largest
        "start" <= its canonical ordinal. Sentences before the first
        boundary belong to the first boundary's section.

    Default behavior (the current pipeline data carries no explicit
    boundaries):
        If boundaries is None or empty, the entire source is assigned a
        single deterministic default section (DEFAULT_SECTION_ID). The
        Builder does NOT invent semantic sections.

    Section IDs are unique, stable across repeated runs, and independent
    of parser numbering.

    Attaches the section to the returned sentence under the "section" key.

    Raises:
        CorpusBuilderError if the structure is invalid, a boundary is
        malformed or has a duplicate section id, boundary starts are not
        strictly increasing, the canonical sentence order regresses, or
        boundaries is not a list.

    Returns:
        (updated section_state, sentence with section attached)
    """
    if not isinstance(sentence, dict):
        raise CorpusBuilderError("sentence must be a dict")
    if not isinstance(section_state, dict):
        raise CorpusBuilderError("section_state must be a dict")

    text = sentence.get("text")
    if not isinstance(text, str) or not text:
        raise CorpusBuilderError("sentence text must be a non-empty string")

    boundaries = section_state.get("boundaries")
    if boundaries is None:
        boundaries = []
    if not isinstance(boundaries, list):
        raise CorpusBuilderError("section boundaries must be a list")

    if boundaries and not section_state.get("validated", False):
        seen_ids = set()
        prev_start = -1
        for boundary in boundaries:
            if not isinstance(boundary, dict) or "section" not in boundary or "start" not in boundary:
                raise CorpusBuilderError(
                    "each section boundary must have 'section' and 'start'."
                )
            section_id = boundary["section"]
            start = boundary["start"]
            if not (isinstance(start, int) and not isinstance(start, bool)):
                raise CorpusBuilderError(
                    f"boundary start must be an integer (section {section_id!r})."
                )
            if start < 0:
                raise CorpusBuilderError(
                    f"boundary start must be non-negative (section {section_id!r})."
                )
            if section_id in seen_ids:
                raise CorpusBuilderError(
                    f"duplicate section id: {section_id!r}."
                )
            seen_ids.add(section_id)
            if start <= prev_start:
                raise CorpusBuilderError(
                    "boundary starts must be strictly increasing."
                )
            prev_start = start
        section_state["validated"] = True

    # Canonical sentence ordinal.
    ids = sentence.get("ids")
    if isinstance(ids, dict) and isinstance(ids.get("sentence_id"), int) \
            and not isinstance(ids.get("sentence_id"), bool):
        ordinal = ids["sentence_id"]
    else:
        ordinal = section_state.get("ordinal", 0)

    # Ordering is preserved.
    last_ordinal = section_state.get("last_ordinal", -1)
    if ordinal < last_ordinal:
        raise CorpusBuilderError(
            f"sentence canonical order regressed ({ordinal} < {last_ordinal})."
        )

    current = section_state.get("current")

    if not boundaries:
        # Deterministic default: the whole source is one section.
        if current is None:
            current = DEFAULT_SECTION_ID
    else:
        # Assign to the boundary with the largest start <= ordinal.
        applicable = None
        for boundary in boundaries:
            if boundary["start"] <= ordinal:
                applicable = boundary["section"]
        if applicable is None:
            applicable = boundaries[0]["section"]
        current = applicable

    result = dict(sentence)
    result["section"] = current

    section_state["current"] = current
    section_state["last_ordinal"] = ordinal
    section_state["ordinal"] = ordinal + 1
    return section_state, result


def new_section_state(boundaries=None):
    """
    Create the initial section state for a source.

    boundaries: optional explicit ordered list of section boundary
    definitions (see assign_sections). None means the source has no
    explicit boundaries and uses the deterministic default section.
    """
    return {
        "boundaries": boundaries,
        "current": None,
        "last_ordinal": -1,
        "ordinal": 0,
        "validated": False,
    }


def stamp_provenance(sentence, provenance):
    """
    Deterministically attach provenance metadata to a sentence record.

    Uses only existing pipeline metadata (source/project, source file,
    job number, model, prompt version) plus the sentence's canonical id
    and position. Parser-provided provenance fields (if present) are
    ignored and replaced with Builder-controlled provenance.

    Provenance answers: which source, which job, which parser response,
    and which position in the source produced this record.

    Child objects (words, chunks, expressions) trace back to this
    sentence through their composite IDs (which embed the sentence_id),
    so no per-child provenance duplication is added.

    Required provenance fields: source, source_file, job_number, model
    (all supplied by the pipeline) plus prompt_version (best-effort; None
    for a producer with no prompt), plus sentence_id and
    sentence_position (the canonical ordinal, equal to the sentence_id).

    Raises:
        CorpusBuilderError if the structure is invalid or any required
        provenance field is missing or invalid. Never guesses or repairs.

    Returns:
        A new sentence record carrying the provenance metadata.
        Linguistic evidence fields are unchanged.
    """
    if not isinstance(sentence, dict):
        raise CorpusBuilderError("sentence must be a dict")
    if not isinstance(provenance, dict):
        raise CorpusBuilderError("provenance must be a dict")

    text = sentence.get("text")
    if not isinstance(text, str) or not text:
        raise CorpusBuilderError("sentence text must be a non-empty string")

    ids = sentence.get("ids")
    if not isinstance(ids, dict):
        raise CorpusBuilderError(
            "sentence ids are missing (run assign_global_ids first)."
        )
    sentence_id = ids.get("sentence_id")
    if not (isinstance(sentence_id, int) and not isinstance(sentence_id, bool)) \
            or sentence_id < 0:
        raise CorpusBuilderError(
            "sentence ids must carry a valid non-negative sentence_id."
        )

    for field in REQUIRED_PROVENANCE_FIELDS:
        value = provenance.get(field)
        if field == "job_number":
            if not (isinstance(value, int) and not isinstance(value, bool)):
                raise CorpusBuilderError(
                    "provenance field 'job_number' must be an integer."
                )
        elif field == "prompt_version":
            # Best-effort: the deterministic producer has no prompt
            # concept, so its provenance carries prompt_version None.
            if value is not None and (not isinstance(value, str) or not value):
                raise CorpusBuilderError(
                    "provenance field 'prompt_version' must be a "
                    "non-empty string or None."
                )
        else:
            if not isinstance(value, str) or not value:
                raise CorpusBuilderError(
                    f"provenance field '{field}' must be a non-empty string."
                )

    result = dict(sentence)
    result["provenance"] = {
        "source_id": provenance["source_id"],
        "source": provenance["source"],
        "source_file": provenance["source_file"],
        "job_number": provenance["job_number"],
        "model": provenance["model"],
        "prompt_version": provenance["prompt_version"],
        "sentence_id": sentence_id,
        "sentence_position": sentence_id,
    }
    return result


def jsonl_writer_state():
    """Initial writer state for one canonical JSONL output stream."""
    return {"seen_ids": set(), "count": 0}


def canonical_output_path(source_id):
    """
    Deterministic canonical JSONL output path for a source.

    Uses the source_id naming convention: jsonl\\<source_id>.jsonl.
    """
    return JSONL / f"{source_id}.jsonl"


def write_jsonl_record(record, output_path, state):
    """
    Deterministically write one canonical record as one JSONL line.

    Args:
        record: canonical sentence record (after all Builder stages).
        output_path: canonical JSONL output file path.
        state: writer state dict with "seen_ids" (set) and "count" (int).

    Validates before writing:
        - record is a dict
        - required fields: text (non-empty string), ids.sentence_id
          (valid non-negative integer), provenance (dict)
        - sentence_id is not already present in the output stream

    Serialization:
        - UTF-8, newline-delimited JSON
        - stable key ordering (json.dumps sort_keys=True)
        - ensure_ascii=False so Japanese text is preserved as UTF-8
        - byte-for-byte reproducible for identical input

    Raises:
        CorpusBuilderError on an invalid record or a duplicate
        sentence_id. Corrupted records are never written.

    Returns:
        The updated writer state.
    """
    if not isinstance(state, dict):
        raise CorpusBuilderError("writer state must be a dict")
    if not isinstance(record, dict):
        raise CorpusBuilderError("record must be a dict")

    text = record.get("text")
    if not isinstance(text, str) or not text:
        raise CorpusBuilderError("record text must be a non-empty string")

    ids = record.get("ids")
    if not isinstance(ids, dict):
        raise CorpusBuilderError("record ids are missing")
    sentence_id = ids.get("sentence_id")
    if not (isinstance(sentence_id, int) and not isinstance(sentence_id, bool)) \
            or sentence_id < 0:
        raise CorpusBuilderError(
            "record ids must carry a valid non-negative sentence_id."
        )

    provenance = record.get("provenance")
    if not isinstance(provenance, dict):
        raise CorpusBuilderError("record provenance is missing")

    seen = state.setdefault("seen_ids", set())
    if sentence_id in seen:
        raise CorpusBuilderError(
            f"duplicate sentence_id in output stream: {sentence_id}."
        )
    seen.add(sentence_id)

    output_path = Path(output_path)
    ensure_folder(output_path.parent)

    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with output_path.open("a", encoding="utf-8") as file:
        file.write(line + "\n")

    state["count"] = state.get("count", 0) + 1
    return state


# ============================================================
# Job / Response Loading
# ============================================================

def job_files_for(source_id):
    """Return the sorted job_*.json files for a source_id."""
    job_dir = JOBS / source_id
    if not job_dir.is_dir():
        return []
    return sorted(job_dir.glob(f"{JOB_PREFIX}*.json"))


def load_job(job_file):
    """
    Load a job JSON file.

    Returns:
        (job_data, None) or (None, error_message).
    """
    try:
        data = json.loads(job_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, OSError) as ex:
        return None, f"job not valid JSON: {ex}"
    return data, None


def request_file_for(source_id, job_number):
    """Return the deterministic request path for a job_number."""
    return REQUESTS / source_id / f"{REQUEST_PREFIX}{job_number:06d}.json"


def load_request(request_file):
    """
    Load a request JSON file (optional provenance enrichment only).

    Returns:
        (request_data, None) or (None, error_message).
    """
    try:
        data = json.loads(request_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, OSError) as ex:
        return None, f"request not valid JSON: {ex}"
    return data, None


def request_prompt_version(source_id, job_data):
    """
    Best-effort prompt_version provenance from a matching request file.

    Request files are optional enrichment only. The DeepSeek path still
    has them (Request Builder runs there); the deterministic path has no
    prompt concept and none. Returns the request's prompt_version when a
    matching, readable request file carries a non-empty string value,
    otherwise None.
    """
    job_number = job_data.get("job_number")
    if not (isinstance(job_number, int) and not isinstance(job_number, bool)):
        return None
    request_file = request_file_for(source_id, job_number)
    if not request_file.is_file():
        return None
    request_data, error = load_request(request_file)
    if error:
        return None
    if not isinstance(request_data, dict):
        return None
    value = request_data.get("prompt_version")
    if isinstance(value, str) and value:
        return value
    return None


def model_for_source(source_id):
    """
    Read the actual producer identity for a source from its Processing
    Result artifact (read once per source; the value is identical for
    every job in one source's run).

    The processing result's "model" field records which producer actually
    generated the responses ("deepseek-v4-flash" for the DeepSeek path,
    "ginza-ja_ginza-5.2.0" for the deterministic path). When the artifact
    is missing, unreadable, or its "model" field is absent/invalid, the
    project MODEL_NAME constant is returned as a safe fallback so the
    corpus still builds.
    """
    path = PROCESSING_RESULTS / f"{source_id}.processing_result.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return MODEL_NAME
    if not isinstance(data, dict):
        return MODEL_NAME
    value = data.get("model")
    if isinstance(value, str) and value:
        return value
    return MODEL_NAME


def response_path_for(source_id, job_file, job_data):
    """
    Compute the expected response file path for a job.

    Uses the job's job_number; falls back to the number embedded in
    the job filename. The response naming convention is
    responses\\<source_id>\\response_<job_number:06d>.json.
    """
    job_number = job_data.get("job_number")
    if not (isinstance(job_number, int) and not isinstance(job_number, bool)):
        stem = job_file.stem
        digits = stem.rsplit("_", 1)[-1]
        try:
            job_number = int(digits)
        except ValueError:
            job_number = 0
    return RESPONSES / source_id / f"{RESPONSE_PREFIX}{job_number:06d}.json"


def load_response(response_file):
    """
    Load a raw parser response JSON file (either producer's response
    artifact).

    Returns:
        (response_data, None) or (None, error_message).
    """
    if not response_file.is_file():
        return None, f"response file not found: {response_file.name}"
    try:
        data = json.loads(response_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, OSError) as ex:
        return None, f"response not valid JSON: {ex}"
    return data, None


def extract_parser_content(raw_response):
    """
    Extract the parser data from a raw response file, for either producer.

    DeepSeek path: the parser JSON is embedded as a JSON string in
    choices[0].message.content, which is parsed here.

    Deterministic path: the parser client writes its parsed dict
    ({"source_name", "job_number", "sentences"}) directly as the response
    artifact, so the dict itself is the parser data.

    Returns:
        (parser_data, None) or (None, error_message).
    """
    if isinstance(raw_response, dict) and isinstance(
            raw_response.get("sentences"), list):
        return raw_response, None
    try:
        choices = raw_response["choices"]
        content = choices[0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as ex:
        return None, f"parser content missing: {ex}"
    if not isinstance(content, str) or not content:
        return None, "parser content is empty or not a string"
    return parse_parser_content(content)


def parse_parser_content(content):
    """
    Parse the parser JSON string into a Python object.

    Returns:
        (parser_data, None) or (None, error_message).
    """
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError) as ex:
        return None, f"parser output is not valid JSON: {ex}"
    return data, None


# ============================================================
# Validation
# ============================================================

def validate_parser_output(parser_data, request_data):
    """
    Validate one parser response against the request metadata.

    The request metadata supplies the authoritative source_id and
    job_number. Returns the response_validator result dictionary.
    """
    return response_validator.validate_response(
        parser_data,
        expected_source_name=request_data.get("source_id"),
        expected_job_number=request_data.get("job_number"),
    )


# ============================================================
# Logging
# ============================================================

def start_log():
    """
    Create a new Corpus Builder run log.

    Returns:
        The log file path.
    """
    ensure_folder(LOG_CORPUS_BUILDER)
    log_file = (
        LOG_CORPUS_BUILDER
        / (
            "corpus_builder_"
            + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            + ".log"
        )
    )
    log_file.write_text(
        f"Program: {PROGRAM_NAME}\n"
        f"Version: {PROJECT_VERSION}\n"
        f"Date: {timestamp()}\n"
        "\n",
        encoding="utf-8",
    )
    return log_file


def append_log(log_file, line):
    """Append one line to the run log."""
    with log_file.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


# ============================================================
# Job Processing (framework)
# ============================================================

def process_job(source_id, job_file, job_data,
                response_file, log_file, job_stats, global_index,
                section_state, model, prompt_version):
    """
    Process one job through the framework.

    Loads the response, extracts and parses the parser JSON, validates
    it with response_validator, and on success runs the Builder stage
    functions. global_index threads the per-source sentence counter and
    section_state threads the per-source section state across jobs so
    canonical sentence IDs and section assignments remain consistent
    per source.

    model is the per-source producer identity (read once per source).
    prompt_version is the per-job best-effort provenance enrichment.

    Returns:
        (job_result dict, records list, global_index, section_state)
        records is the list of sentence records produced for this job.
    """
    result = {
        "job_file": job_file.name,
        "response_file": response_file.name,
        "loaded": False,
        "parsed": False,
        "valid": False,
        "processed": False,
        "sentence_count": 0,
        "errors": [],
    }

    raw_response, error = load_response(response_file)
    if error:
        result["errors"].append(error)
        append_log(log_file, f"{timestamp()} LOAD-FAILED {job_file.name}: {error}")
        job_stats["failed"] += 1
        return result, [], global_index, section_state
    result["loaded"] = True

    parser_data, error = extract_parser_content(raw_response)
    if error:
        result["errors"].append(error)
        append_log(log_file, f"{timestamp()} EXTRACT-FAILED {job_file.name}: {error}")
        job_stats["failed"] += 1
        return result, [], global_index, section_state
    result["parsed"] = True

    # ---- Parser Output Canonicalizer (runs BEFORE validation) ----
    # The cleaned source text is authoritative for sentence text. The
    # normalizer replaces parser sentence text, recomputes spans/chunk
    # text, and verifies reconstruction so the validator validates
    # canonical records.
    job_text = job_data.get("text")
    if not isinstance(job_text, str) or not job_text:
        result["errors"].append("job text not found in job")
        append_log(log_file,
                   f"{timestamp()} CANONICALIZE-FAILED {job_file.name}: "
                   f"job text not found in job")
        job_stats["failed"] += 1
        return result, [], global_index, section_state
    try:
        canonicalized = canonicalize(parser_data, job_text)
    except CorpusBuilderError as exc:
        result["errors"].append(str(exc))
        append_log(log_file,
                   f"{timestamp()} CANONICALIZE-FAILED {job_file.name}: {exc}")
        job_stats["failed"] += 1
        return result, [], global_index, section_state

    validation = validate_parser_output(canonicalized, job_data)
    if not validation["valid"]:
        result["errors"].extend(
            e["message"] for e in validation["errors"]
        )
        append_log(
            log_file,
            f"{timestamp()} VALIDATION-FAILED {job_file.name}: "
            f"{len(validation['errors'])} error(s)",
        )
        for error in validation["errors"][:10]:
            append_log(log_file, f"    {error['code']}: {error['message']}")
        job_stats["failed"] += 1
        return result, [], global_index, section_state

    result["valid"] = True

    # ---- Builder stages (deterministic recomputation) ----
    provenance = {
        "source_id": job_data.get("source_id"),
        "source": job_data.get("source_id"),
        "source_file": job_data.get("cleaned_artifact"),
        "job_number": job_data.get("job_number"),
        "model": model,
        "prompt_version": prompt_version,
    }
    records = []

    # Sentence text, character spans, and chunk text were canonicalized by
    # the Parser Output Canonicalizer; the builder assigns identity,
    # sections, and provenance only.
    for sentence in canonicalized.get("sentences", []):
        global_index, sentence = assign_global_ids(sentence, global_index)
        section_state, sentence = assign_sections(sentence, section_state)
        sentence = stamp_provenance(sentence, provenance)
        records.append(sentence)

    result["processed"] = True
    result["sentence_count"] = len(records)
    job_stats["processed"] += 1

    append_log(
        log_file,
        f"{timestamp()} PROCESSED {job_file.name} "
        f"sentences={result['sentence_count']}",
    )
    return result, records, global_index, section_state


# ============================================================
# Project Processing (framework)
# ============================================================

def process_source(source_id, log_file, source_stats):
    """
    Process every job for one source_id through the framework.

    Returns:
        (source_stats dict, records list)
        records is the accumulated list of sentence records.
    """
    job_files = job_files_for(source_id)
    records = []
    global_index = 0
    section_state = new_section_state()
    expected_parts = []
    model = model_for_source(source_id)

    for job_file in job_files:
        job_data, error = load_job(job_file)
        if error:
            source_stats["failed"] += 1
            append_log(log_file, f"{timestamp()} JOB-FAILED {job_file.name}: {error}")
            continue

        # Lineage verification: the job's source_id must match the
        # requested source_id (verify over trust).
        if job_data.get("source_id") != source_id:
            source_stats["failed"] += 1
            append_log(log_file, f"{timestamp()} LINEAGE-FAILED {job_file.name}")
            continue

        job_text = job_data.get("text")
        if isinstance(job_text, str):
            expected_parts.append(job_text)
        response_file = response_path_for(source_id, job_file, job_data)
        prompt_version = request_prompt_version(source_id, job_data)
        job_result, job_records, global_index, section_state = process_job(
            source_id, job_file, job_data,
            response_file, log_file, source_stats,
            global_index, section_state, model, prompt_version,
        )
        if job_result["processed"]:
            records.extend(job_records)

    # ---- Source-level integrity gate ----
    # Sentence text was canonicalized per job by the Parser Output
    # Canonicalizer. This final gate verifies the accumulated canonical
    # sentence texts reconstruct the full cleaned source.
    verification = None
    if records:
        expected_text = "".join(expected_parts)
        verification = verify_source_reconstruction(records, expected_text)

    # ---- Canonical JSONL output (atomic) ----
    output_file = None
    if records and verification and verification.get("verified"):
        output_file = canonical_output_path(source_id)
        text = "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            for record in records
        )
        write_atomic_text(output_file, text)

    source_stats["records_written"] = (
        len(records) if (verification and verification.get("verified")) else 0
    )
    source_stats["output_file"] = (
        str(output_file) if output_file is not None else None
    )
    source_stats["verified"] = bool(
        verification and verification.get("verified")
    )

    return source_stats, records


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


def write_result(result):
    """
    Validate and atomically write a Corpus Builder Result artifact.
    """
    path = CORPUS_RESULTS / f"{result['source_id']}.corpus_builder_result.json"
    corpus_builder_result.write_result(path, result)
    return path


def write_log(source_id, status, details):
    """
    Write the Corpus Builder log for a source.

    Deterministic content; only the timestamp varies.
    """
    LOG_CORPUS_BUILDER.mkdir(parents=True, exist_ok=True)
    log_file = LOG_CORPUS_BUILDER / f"{source_id}.corpus_builder.log"
    lines = [
        f"Program: {PROGRAM_NAME}",
        f"Version: {PROGRAM_VERSION}",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Source: {source_id}",
        f"Status: {status}",
    ]
    lines.extend(details)
    write_atomic_text(log_file, "\n".join(lines) + "\n")
    return log_file


# ============================================================
# Source execution
# ============================================================

def run(source_id):
    """
    Execute the Corpus Builder for one source_id.

    Input: source_id (str).
    Output: exit code (0 success, non-zero failure).
    """
    source_id = str(source_id).strip()
    if not source_id:
        write_log("unknown", "FAILED", ["missing source_id"])
        return 1

    job_files = job_files_for(source_id)
    if not job_files:
        return fail(source_id, [f"no jobs found for {source_id}"])

    log_file = start_log()
    append_log(log_file, f"Run started: {timestamp()}")
    append_log(log_file, f"Source: {source_id}")

    source_stats = {
        "processed": 0,
        "failed": 0,
        "sentences": 0,
        "records_written": 0,
        "output_file": None,
        "verified": False,
    }
    try:
        source_stats, records = process_source(
            source_id, log_file, source_stats,
        )
    except CorpusBuilderError as exc:
        append_log(log_file, f"{timestamp()} CORPUS-FAILED: {exc}")
        return fail(source_id, [str(exc)])
    source_stats["sentences"] = len(records)

    success = (source_stats["failed"] == 0
               and source_stats["records_written"] > 0
               and source_stats["verified"])
    errors = []
    if source_stats["failed"]:
        errors.append(f"{source_stats['failed']} job(s) failed")

    result = corpus_builder_result.build_result(
        source_id=source_id,
        success=success,
        jobs_processed=source_stats["processed"],
        jobs_failed=source_stats["failed"],
        records_written=source_stats["records_written"],
        verified=source_stats["verified"],
        output_file=source_stats["output_file"],
        errors=errors,
        completion_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    try:
        write_result(result)
    except corpus_builder_result.CorpusBuilderResultError as exc:
        return fail(source_id, [f"cannot write corpus builder result: {exc}"])

    write_log(source_id, "SUCCESS" if success else "PARTIAL", [
        f"Jobs Processed: {source_stats['processed']}",
        f"Jobs Failed: {source_stats['failed']}",
        f"Records Written: {source_stats['records_written']}",
        f"Verified: {source_stats['verified']}",
    ])

    return 0 if success else 2


def fail(source_id, errors):
    """
    Write a failure Corpus Builder Result and log.

    A failure never writes a success result.
    """
    result = corpus_builder_result.build_result(
        source_id=source_id,
        success=False,
        jobs_processed=0,
        jobs_failed=0,
        records_written=0,
        verified=False,
        output_file=None,
        errors=list(errors),
    )
    try:
        write_result(result)
    except corpus_builder_result.CorpusBuilderResultError:
        pass
    write_log(source_id, "FAILED", list(errors))
    return 1


# ============================================================
# Entry point
# ============================================================

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="corpus_builder.py",
        description=PROGRAM_NAME,
    )
    parser.add_argument(
        "--source",
        required=True,
        help="source_id of the jobs to build a corpus for.",
    )
    args = parser.parse_args(argv)
    return run(args.source)


if __name__ == "__main__":
    sys.exit(main())
