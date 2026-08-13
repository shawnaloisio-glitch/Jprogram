#!/usr/bin/env python3
"""
import_con_teppei.py

Japanese Corpus Pipeline - Con-Teppei podcast one-off importer.

Imports the 337 real "Beginners con Teppei" podcast transcript files from
    D:\\Sourced Content\\Japanese Import\\ready for parser\\9647179
as standalone sources through the real pipeline
(create_standalone_source -> handoff ->
 production_manager.py --source <id> --pipeline --auto).

This is a one-off importer for a format that will never recur: files are
named ep001.txt..ep337.txt by folder/download order, but that order does NOT
match the real underlying episode numbers -- e.g. ep001.txt is really episode
1055, ep002.txt is really episode 1054, ep200.txt is really episode 142. The
real episode number instead lives in manifest.csv's "title" column (e.g.
"Beginners-con-Teppei1055", with inconsistent spacing/casing across rows:
"Beginners -con - teppei 1", "Beginners - con - Teppei 235") and is repeated
verbatim as each file's own first line. Confirmed by direct inspection
(2026-08-13): all 337 manifest titles yield a unique trailing episode number,
so it is a reliable, collision-free identity -- the arbitrary "epNNN"
filename is deliberately NOT used for source naming or the episode_number
metadata. It deliberately does NOT live in the shared Batch Importer /
import_material infrastructure, for the same reason as the LingQ Mini
Stories importer: a one-off format, not a general rule.

Format-specific cleaning (the only difference from batch_importer.import_one):
    - The file's first line is the header (matches the manifest title's real
      episode number once parsed) and is dropped entirely -- it is not real
      sentence content.
    - Every remaining non-blank line is one real sentence, preserved
      verbatim, one per line.
    - Defensive check: the header's own parsed episode number must match the
      manifest row's parsed episode number for that file, or the file is
      failed rather than silently imported under a possibly-wrong number.

The importer is idempotent (a source whose canonical file already exists is
skipped entirely) and failure-isolated (one file's failure never aborts the
batch), exactly like batch_importer.py and import_lingq_mini_stories.py.

Exit codes:
    0  every episode file was imported or skipped; no failures
    1  usage error (missing folder / manifest / unknown creator) OR one or
       more files failed (the batch still completed, see the summary)
"""

import argparse
import csv
import re
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

# Allow imports from the project root, Source Builder, and Production Manager
# (project convention, mirroring batch_importer.py / the LingQ importer).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Source Builder"))
sys.path.insert(0, str(PROJECT_ROOT / "Production Manager"))

import config_loader
import controller
import handoff
import paths
import source_package

# ---------------------------------------------------------------------------
# Fixed import parameters (Owner-confirmed 2026-08-13; this is a one-off
# import).
# ---------------------------------------------------------------------------

SOURCE_FOLDER = Path(
    r"D:\Sourced Content\Japanese Import\ready for parser\9647179")

MANIFEST_NAME = "manifest.csv"

# source_type = "clean_text" is the only value in the current Config
# vocabulary (confirmed by reading Config/source_types.json).
SOURCE_TYPE = "clean_text"

# creator = "conteppei" (Owner-added to the workspace creators config
# 2026-08-13); the script validates it at startup and fails clearly rather
# than silently creating it.
CREATOR = "conteppei"

# material_level = 2 is "Beginner" in project_config.MATERIAL_LEVELS
# (Owner-confirmed: con-teppei is his beginner content).
MATERIAL_LEVEL = 2

# style_id = 3 "Pod Cast", topic_id = 1 "Various" (Owner-confirmed
# 2026-08-13, both already present in Workspace/Config).
STYLE_ID = 3
TOPIC_ID = 1

# Collision-safe source-name prefix: keeps every source traceable to its
# Con-Teppei folder. Per-file source_name = f"{PREFIX}-{real_episode_number}"
# (the real, manifest-derived episode number -- never the arbitrary "epNNN"
# file-order name).
SOURCE_NAME_PREFIX = "conteppei"

PRODUCTION_MANAGER_SCRIPT = (
    PROJECT_ROOT / "Production Manager" / "production_manager.py"
)

# Trailing-digits extractor for a manifest/header title like
# "Beginners-con-Teppei1055" or "Beginners -con - teppei 1" -> "1055" / "1".
_EPISODE_NUMBER_RE = re.compile(r"(\d+)\s*$")

# Classification kinds.
KIND_IMPORT = "import"
KIND_SKIP_ALREADY = "skip_already"
KIND_SKIP_NO_MANIFEST = "skip_no_manifest"


class ConTeppeiImportError(Exception):
    """Raised when a Con-Teppei source file cannot be read or cleaned."""


# Result of cleaning one file: the cleaned source text plus the real episode
# number parsed from the file's own header line.
CleanResult = namedtuple("CleanResult", ["source_text", "header_episode_number"])

# One manifest row's relevant fields.
ManifestRow = namedtuple("ManifestRow", ["lesson_id", "episode_number", "sentence_count"])


def resolve_venv_python():
    """
    Return the project venv Python executable.

    Same resolution convention as batch_importer.py and the LingQ importer.
    """
    return PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"


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


def validate_creator(creator):
    """
    Return an error message when the creator is not configured, else None.

    Creators are workspace customer data (paths.CREATORS_CONFIG). The
    importer must not create a source with an invalid creator, so validation
    happens up front and fails clearly.
    """
    creators = config_loader.load_creators()
    if creator in creators:
        return None
    available = ", ".join(creators) if creators else "(none configured)"
    return (
        f"unknown creator_id {creator!r}: not found in the workspace creators "
        f"config ({paths.CREATORS_CONFIG}). Available creators: {available}"
    )


def parse_episode_number(title):
    """
    Extract the real trailing episode number from a title/header string.

    Input: title (str), e.g. "Beginners-con-Teppei1055" or
        "Beginners -con - teppei 1".
    Output: int, or None if no trailing digits are found.
    """
    match = _EPISODE_NUMBER_RE.search(title.strip())
    return int(match.group(1)) if match else None


def load_manifest(folder):
    """
    Map each episode file stem to its manifest row.

    Input: folder (Path).
    Output: dict {file_stem: ManifestRow}, e.g. {"ep001": ManifestRow(...)}.
        Rows whose title yields no parseable episode number are skipped (not
        included in the returned dict).
    Raises: FileNotFoundError when manifest.csv is absent; OSError /
        UnicodeError / csv.Error when it cannot be read.
    """
    manifest_path = folder / MANIFEST_NAME
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    rows = {}
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            episode = (row.get("episode") or "").strip()
            title = (row.get("title") or "").strip()
            if not episode:
                continue
            episode_number = parse_episode_number(title)
            if episode_number is None:
                continue
            lesson_id = (row.get("lesson_id") or "").strip() or None
            sentence_count_raw = (row.get("sentence_count") or "").strip()
            sentence_count = int(sentence_count_raw) if sentence_count_raw.isdigit() else None
            rows[episode] = ManifestRow(lesson_id, episode_number, sentence_count)
    return rows


def clean_source_text(raw_text):
    """
    Clean raw Con-Teppei text into sentence-per-line source text.

    Input: raw_text (str), as read from an episode file.
    Output: CleanResult(source_text, header_episode_number):
        source_text - cleaned text, one real sentence per line, no blank
            lines, ending with a single newline. The first line (header) is
            dropped entirely.
        header_episode_number - int parsed from the dropped header line, or
            None if the header itself had no parseable trailing number.

    Cleaning rule (confirmed by direct inspection of multiple files across
    the full episode range, including the 4 lowercase-"teppei" variants):
    the first line is always the structural header (repeats the manifest
    title, e.g. "Beginners-con-Teppei1055"), never real sentence content, and
    is dropped unconditionally. Every remaining non-blank line is one real
    sentence, preserved verbatim.
    """
    lines = raw_text.splitlines()
    header_episode_number = parse_episode_number(lines[0]) if lines else None
    body_lines = [line for line in lines[1:] if line.strip()]
    return CleanResult("\n".join(body_lines) + "\n", header_episode_number)


def clean_file(path):
    """
    Read and clean one Con-Teppei episode file.

    Input: path (Path).
    Output: CleanResult.
    Raises: ConTeppeiImportError on read failure or empty cleaned text.
    """
    try:
        raw_text = path.read_text(encoding="utf-8-sig")
    except (UnicodeDecodeError, OSError) as exc:
        raise ConTeppeiImportError(f"cannot read {path.name}: {exc}") from exc
    result = clean_source_text(raw_text)
    if not result.source_text.strip():
        raise ConTeppeiImportError(f"cleaned text is empty: {path.name}")
    return result


def classify(episode_number):
    """
    Classify one episode file for the batch (shared by real and dry-run modes).

    Input: episode_number (int, the real manifest-derived episode number).
    Output: (kind, source_name) where kind is one of KIND_*.
    """
    source_name = f"{SOURCE_NAME_PREFIX}-{episode_number}"
    if controller.standalone_source_path(source_name).is_file():
        return KIND_SKIP_ALREADY, source_name
    return KIND_IMPORT, source_name


def import_one(path, manifest_row, stage_timeout=None):
    """
    Import one episode file through the full pipeline.

    Assumes the file was already classified for import (has a manifest row
    and no existing canonical source).

    Mirrors import_lingq_mini_stories.import_one() exactly (clean ->
    create_standalone_source -> load_source_package -> handoff ->
    production_manager subprocess), swapping only the format-specific
    cleaning/naming for Con-Teppei.

    Input: path (Path), manifest_row (ManifestRow), stage_timeout (int|None).
    Output: None on success, or (stage, message) on failure.
    """
    try:
        result = clean_file(path)
    except ConTeppeiImportError as exc:
        return "clean", str(exc)

    if result.header_episode_number != manifest_row.episode_number:
        return ("clean",
                f"header episode number {result.header_episode_number} does "
                f"not match manifest episode number "
                f"{manifest_row.episode_number}")

    source_name = f"{SOURCE_NAME_PREFIX}-{manifest_row.episode_number}"

    created = controller.create_standalone_source(
        source_name, SOURCE_TYPE, CREATOR, result.source_text,
        material_level=MATERIAL_LEVEL, style_id=STYLE_ID, topic_id=TOPIC_ID,
        episode_number=manifest_row.episode_number)
    if not created["success"]:
        return "create", "; ".join(created["errors"])
    if created.get("package_error"):
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
            detail = detail[-500:]
        message = f"exit code {completed.returncode}"
        if detail:
            message += f": {detail}"
        return "pipeline", message

    return None


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="import_con_teppei.py",
        description="Import the 337 Con-Teppei podcast episode files through "
                    "the real Jprogram pipeline as standalone sources.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would happen for each file (cleaned line count, "
             "computed source_name); create nothing, write nothing, run "
             "nothing.",
    )
    parser.add_argument(
        "--stage-timeout",
        type=int,
        default=None,
        help="optional timeout in seconds, passed through to "
             "production_manager.py --timeout.",
    )
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    folder = SOURCE_FOLDER
    if not folder.is_dir():
        print(f"Error: source folder not found: {folder}", file=sys.stderr)
        return 1

    creator_error = validate_creator(CREATOR)
    if creator_error:
        print(f"Error: {creator_error}", file=sys.stderr)
        return 1

    try:
        manifest_rows = load_manifest(folder)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError, csv.Error) as exc:
        print(f"Error: cannot read manifest {folder / MANIFEST_NAME}: {exc}",
              file=sys.stderr)
        return 1
    if not manifest_rows:
        print(f"Error: manifest has no usable episode rows: "
              f"{folder / MANIFEST_NAME}", file=sys.stderr)
        return 1

    files = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() == ".txt"
    )

    imported = 0
    skipped_already = 0
    skipped_no_manifest = 0
    failures = []

    for path in files:
        if path.stem not in manifest_rows:
            skipped_no_manifest += 1
            print(f"[SKIP no-manifest-row] {path.name}"
                  if not args.dry_run
                  else f"[WOULD-SKIP no-manifest-row] {path.name}")
            continue

        manifest_row = manifest_rows[path.stem]
        kind, source_name = classify(manifest_row.episode_number)

        if args.dry_run:
            try:
                result = clean_file(path)
            except ConTeppeiImportError as exc:
                failures.append((path.name, "clean", str(exc)))
                print(f"[WOULD-FAIL clean] {path.name}: {exc}")
                continue
            if result.header_episode_number != manifest_row.episode_number:
                failures.append((
                    path.name, "clean",
                    f"header episode number {result.header_episode_number} "
                    f"does not match manifest episode number "
                    f"{manifest_row.episode_number}"))
                print(f"[WOULD-FAIL clean] {path.name}: header/manifest "
                      f"episode number mismatch "
                      f"({result.header_episode_number} vs "
                      f"{manifest_row.episode_number})")
                continue
            n_lines = len(result.source_text.splitlines())
            detail = f"({n_lines} lines"
            if manifest_row.sentence_count is not None:
                detail += (f", manifest says {manifest_row.sentence_count}"
                            f"{' MISMATCH' if n_lines != manifest_row.sentence_count else ''}")
            detail += ")"
            if kind == KIND_SKIP_ALREADY:
                skipped_already += 1
                print(f"[WOULD-SKIP already-imported] {path.name} -> "
                      f"{source_name} {detail}")
            else:
                imported += 1
                print(f"[WOULD-IMPORT] {path.name} -> {source_name} {detail}")
            continue

        if kind == KIND_SKIP_ALREADY:
            skipped_already += 1
            print(f"[SKIP already-imported] {path.name} -> {source_name}")
            continue

        try:
            failure = import_one(path, manifest_row, args.stage_timeout)
        except Exception as exc:
            failure = ("unexpected", str(exc))

        if failure is None:
            imported += 1
            print(f"[IMPORTED] {path.name} -> {source_name}")
        else:
            stage, message = failure
            failures.append((path.name, stage, message))
            print(f"[FAIL {stage}] {path.name}: {message}")

    print()
    print("Summary:")
    print(f"  files: {len(files)}")
    print(f"  source_type: {SOURCE_TYPE}")
    print(f"  creator: {CREATOR}")
    print(f"  material_level: {MATERIAL_LEVEL}")
    print(f"  style_id: {STYLE_ID}")
    print(f"  topic_id: {TOPIC_ID}")
    print(f"  {'would-import' if args.dry_run else 'imported'}: {imported}")
    print(f"  skipped (already imported): {skipped_already}")
    print(f"  skipped (no manifest row): {skipped_no_manifest}")
    print(f"  failed: {len(failures)}")
    if failures:
        print("Failures:")
        for file_name, stage, message in failures:
            print(f"  - {file_name} ({stage}): {message}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
