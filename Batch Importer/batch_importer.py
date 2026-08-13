#!/usr/bin/env python3
"""
batch_importer.py

Japanese Corpus Pipeline - Batch Importer.

Bulk-imports a folder of already-normalized source files through the real
pipeline (Handoff -> Cleaner -> Job Builder -> Parser -> Validator -> Corpus
Builder) as standalone sources.

A separate personal tool (outside this repo) already normalizes messy
real-world filenames into "<Label> id<NNNNN>.<ext>" before this importer
ever sees them. This importer does NOT parse or interpret filenames in any
way beyond using the file's own stem as the source name.

Supported formats (routed to the existing importers, unchanged):
    .html       Nihongo Jikan transcripts  (Nihongo Jikan Importer)
    .vtt / .srt subtitles                  (Subtitle Importer)

The importer is non-recursive (only files directly inside --folder),
idempotent (a source whose canonical file already exists is skipped entirely,
so re-running on a partly-imported folder is safe), and failure-isolated (one
file's failure never aborts the batch).

Per supported file, in filename order:
    convert -> create_standalone_source -> handoff ->
    production_manager.py --source <id> --pipeline --auto (subprocess)

Exit codes:
    0  every supported file was imported or skipped; no failures
    1  usage error (bad folder / unknown creator) OR one or more files failed
       (the batch still completed, see the summary)
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Allow imports from the project root and Source Builder (project convention).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Source Builder"))
sys.path.insert(0, str(PROJECT_ROOT / "Production Manager"))

import config_loader
import controller
import handoff
import import_material
import paths
import source_package

PRODUCTION_MANAGER_SCRIPT = PROJECT_ROOT / "Production Manager" / "production_manager.py"

SOURCE_TYPE = "clean_text"

# Classification kinds.
KIND_IMPORT = "import"
KIND_SKIP_ALREADY = "skip_already"
KIND_SKIP_UNSUPPORTED = "skip_unsupported"


def resolve_venv_python():
    """
    Return the project venv Python executable.

    Same resolution convention as the QC Test Harness stage_parse() and the
    Production Manager api stage: PROJECT_ROOT/.venv/Scripts/python.exe.
    Never a hardcoded absolute path assumption.
    """
    return PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"


def format_for_path(path):
    """
    Return the import_material format constant for a file, or None.

    .html -> nihongo_jikan; .vtt/.srt -> subtitle; anything else -> None.
    The check is extension-only (case-insensitive), exactly the scope this
    importer is allowed: filenames are never interpreted beyond the stem.
    """
    suffix = Path(path).suffix.lower()
    if suffix == ".html":
        return import_material.FORMAT_NIHONGO_JIKAN
    if suffix in (".vtt", ".srt"):
        return import_material.FORMAT_SUBTITLE
    return None


def validate_creator(creator):
    """
    Return an error message when the creator is not configured, else None.

    Creators are workspace customer data (Config/creators.json). The importer
    must not create a source with an invalid creator, so validation happens up
    front and fails clearly.
    """
    creators = config_loader.load_creators()
    if creator in creators:
        return None
    available = ", ".join(creators) if creators else "(none configured)"
    return (
        f"unknown creator_id {creator!r}: not found in the workspace creators "
        f"config ({paths.CREATORS_CONFIG}). Available creators: {available}"
    )


def validate_style(style):
    """
    Return an error message when the style_id is not configured, else None.

    Input: style (int).
    """
    styles = config_loader.load_styles()
    if style in styles:
        return None
    available = ", ".join(str(s) for s in styles) if styles else "(none configured)"
    return (
        f"unknown style_id {style!r}: not found in the workspace styles "
        f"config ({paths.STYLES_CONFIG}). Available styles: {available}"
    )


def validate_topic(topic):
    """
    Return an error message when the topic_id is not configured, else None.

    Input: topic (int).
    """
    topics = config_loader.load_topics()
    if topic in topics:
        return None
    available = ", ".join(str(t) for t in topics) if topics else "(none configured)"
    return (
        f"unknown topic_id {topic!r}: not found in the workspace topics "
        f"config ({paths.TOPICS_CONFIG}). Available topics: {available}"
    )


def classify(path):
    """
    Classify one file for the batch (shared by real and dry-run modes).

    Input: path (Path).
    Output: (kind, source_format) where kind is one of KIND_* and
        source_format is the import_material format constant (None for the
        skip kinds).
    """
    source_format = format_for_path(path)
    if source_format is None:
        return KIND_SKIP_UNSUPPORTED, None
    source_name = Path(path).stem
    if controller.standalone_source_path(source_name).is_file():
        return KIND_SKIP_ALREADY, None
    return KIND_IMPORT, source_format


def build_pipeline_command(source_id, stage_timeout=None):
    """
    Build the argv for the production_manager pipeline subprocess.

    Input: source_id (str), stage_timeout (int|None).
    Output: list of strings. stage_timeout is passed through as
        production_manager.py's own --timeout.
    """
    argv = [
        str(resolve_venv_python()),
        str(PRODUCTION_MANAGER_SCRIPT),
        "--source", str(source_id),
        "--pipeline",
        "--auto",
    ]
    if stage_timeout is not None:
        argv += ["--timeout", str(stage_timeout)]
    return argv


def import_one(path, creator, stage_timeout=None, style_id=None, topic_id=None,
               episode_number=None, season_number=None):
    """
    Import one file through the full pipeline.

    Assumes the file was already classified for import (supported format and
    no existing canonical source).

    Input: path (Path), creator (str), stage_timeout (int|None),
        style_id (int|None), topic_id (int|None), episode_number (int|None),
        season_number (int|None) -- applied uniformly to every file in the
        batch (this importer processes one folder as one batch of the same
        content, no per-file overrides).
    Output: None on success, or (stage, message) on failure.
    """
    source_format = format_for_path(path)
    if source_format is None:
        return "format", "unsupported format"
    source_name = Path(path).stem

    try:
        source_text = import_material.convert_file(path, source_format)
    except import_material.ImportError as exc:
        return "convert", str(exc)

    # suggested_material_level may be None for an unmatched folder; that is a
    # valid "no suggestion" outcome and is passed through unchanged (matching
    # the GUI import flow for an unmatched folder). A None level makes
    # create_standalone_source report a package_error, which is caught below.
    material_level = import_material.suggested_material_level(path)
    created = controller.create_standalone_source(
        source_name, SOURCE_TYPE, creator, source_text,
        material_level=material_level,
        style_id=style_id, topic_id=topic_id,
        episode_number=episode_number, season_number=season_number)
    if not created["success"]:
        return "create", "; ".join(created["errors"])
    if created.get("package_error"):
        # The canonical file was written but the Source Package was not, so
        # the source cannot be handed off. Treat this as a create failure.
        return "create", f"source package was not written: {created['package_error']}"

    package_path = source_package.package_path_for(created["path"])
    try:
        package = handoff.load_source_package(package_path)
    except handoff.HandoffError as exc:
        return "create", f"cannot read source package: {exc}"

    try:
        handoff_result = handoff.handoff(package)
    except handoff.HandoffError as exc:
        return "handoff", str(exc)
    if handoff_result.get("errors"):
        return "handoff", "; ".join(handoff_result["errors"])

    source_id = package["source_id"]
    argv = build_pipeline_command(source_id, stage_timeout)
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(PROJECT_ROOT),
        )
    except OSError as exc:
        return "pipeline", f"failed to launch production_manager.py: {exc}"

    if completed.returncode != 0:
        detail = (completed.stderr or "").strip() or (completed.stdout or "").strip()
        if detail:
            # Keep the failure readable; the full output is in the pipeline's
            # own log.
            detail = detail[-500:]
        message = f"exit code {completed.returncode}"
        if detail:
            message += f": {detail}"
        return "pipeline", message

    return None


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="batch_importer.py",
        description="Bulk-import a folder of already-normalized source files "
                    "through the real Jprogram pipeline as standalone sources.",
    )
    parser.add_argument(
        "--folder",
        required=True,
        help="folder containing the normalized source files (non-recursive).",
    )
    parser.add_argument(
        "--creator",
        required=True,
        help="creator_id; must exist in the workspace Config/creators.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would happen for each file; create nothing, write "
             "nothing, run nothing.",
    )
    parser.add_argument(
        "--stage-timeout",
        type=int,
        default=None,
        help="optional timeout in seconds, passed through to "
             "production_manager.py --timeout.",
    )
    parser.add_argument(
        "--style",
        default=None,
        help="optional style_id; must exist in the workspace "
             "Config/styles.json. Applies to every file in the batch.",
    )
    parser.add_argument(
        "--topic",
        default=None,
        help="optional topic_id; must exist in the workspace "
             "Config/topics.json. Applies to every file in the batch.",
    )
    parser.add_argument(
        "--episode",
        type=int,
        default=None,
        help="optional episode_number. Applies to every file in the batch.",
    )
    parser.add_argument(
        "--season",
        type=int,
        default=None,
        help="optional season_number. Applies to every file in the batch.",
    )
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Error: folder not found: {folder}", file=sys.stderr)
        return 1

    creator_error = validate_creator(args.creator)
    if creator_error:
        print(f"Error: {creator_error}", file=sys.stderr)
        return 1

    style_id = None
    if args.style is not None:
        try:
            style_id = int(args.style)
        except ValueError:
            print(f"Error: --style must be an integer, got {args.style!r}",
                  file=sys.stderr)
            return 1
        style_error = validate_style(style_id)
        if style_error:
            print(f"Error: {style_error}", file=sys.stderr)
            return 1

    topic_id = None
    if args.topic is not None:
        try:
            topic_id = int(args.topic)
        except ValueError:
            print(f"Error: --topic must be an integer, got {args.topic!r}",
                  file=sys.stderr)
            return 1
        topic_error = validate_topic(topic_id)
        if topic_error:
            print(f"Error: {topic_error}", file=sys.stderr)
            return 1

    files = sorted(p for p in folder.iterdir() if p.is_file())

    imported = 0
    skipped_already = 0
    skipped_unsupported = 0
    failures = []

    for path in files:
        kind, source_format = classify(path)

        if kind == KIND_SKIP_UNSUPPORTED:
            skipped_unsupported += 1
            print(f"[SKIP unsupported-format] {path.name}"
                  if not args.dry_run
                  else f"[WOULD-SKIP unsupported-format] {path.name}")
            continue

        if kind == KIND_SKIP_ALREADY:
            skipped_already += 1
            print(f"[SKIP already-imported] {path.name}"
                  if not args.dry_run
                  else f"[WOULD-SKIP already-imported] {path.name}")
            continue

        if args.dry_run:
            print(f"[WOULD-IMPORT {source_format}] {path.name}")
            continue

        try:
            failure = import_one(
                path, args.creator, args.stage_timeout,
                style_id=style_id, topic_id=topic_id,
                episode_number=args.episode, season_number=args.season)
        except Exception as exc:
            # Defensive catch-all: never let one file abort the batch.
            failure = ("unexpected", str(exc))

        if failure is None:
            imported += 1
            print(f"[IMPORTED] {path.name}")
        else:
            stage, message = failure
            failures.append((path.name, stage, message))
            print(f"[FAIL {stage}] {path.name}: {message}")

    print()
    print("Summary:")
    print(f"  imported: {imported}")
    print(f"  skipped (already imported): {skipped_already}")
    print(f"  skipped (unsupported format): {skipped_unsupported}")
    print(f"  failed: {len(failures)}")
    if failures:
        print("Failures:")
        for file_name, stage, message in failures:
            print(f"  - {file_name} ({stage}): {message}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
