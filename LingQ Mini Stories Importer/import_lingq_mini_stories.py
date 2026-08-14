#!/usr/bin/env python3
"""
import_lingq_mini_stories.py

Japanese Corpus Pipeline - LingQ Mini Stories one-off importer.

Imports the 62 real LingQ "Mini Stories" episode files from
    D:\\Sourced Content\\import\\ready for parser\\9795706
as standalone sources through the real pipeline
(create_standalone_source -> handoff ->
 production_manager.py --source <id> --pipeline --auto).

This is a one-off importer for a format that will never recur: each file is a
short story told twice (3rd person, then 1st person) plus a comprehension
quiz. It deliberately does NOT live in the shared Batch Importer /
import_material infrastructure.

Format-specific cleaning (the only difference from batch_importer.import_one):
    - A line-start "A)" or "B)" structural prefix is stripped.
    - A line that, after stripping A)/B)/whitespace, is exactly the section
      label "質問:" or "質問：" is dropped entirely (no blank line left in its
      place -- blank lines are the sentence separator for the parser to come).
    - Every remaining line is one real sentence, preserved verbatim, one per
      line. Numbered question-index prefixes (一:, 二:, ...) stay embedded.

The importer is idempotent (a source whose canonical file already exists is
skipped entirely, so re-running on a partly-imported folder is safe) and
failure-isolated (one file's failure never aborts the batch), exactly like
batch_importer.py.

Exit codes:
    0  every episode file was imported or skipped; no failures
    1  usage error (missing folder / manifest / unknown creator) OR one or
       more files failed (the batch still completed, see the summary)
"""

import argparse
import csv
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

# Allow imports from the project root, Source Builder, and Production Manager
# (project convention, mirroring batch_importer.py).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Source Builder"))
sys.path.insert(0, str(PROJECT_ROOT / "Production Manager"))

import config_loader
import controller
import handoff
import paths

# ---------------------------------------------------------------------------
# Fixed import parameters (Owner-confirmed; this is a one-off import).
# ---------------------------------------------------------------------------

# The real LingQ Mini Stories folder being imported.
SOURCE_FOLDER = Path(r"D:\Sourced Content\Japanese Import\ready for parser\9795706")

MANIFEST_NAME = "manifest.csv"

# source_type = "clean_text" is the only value in the current Config
# vocabulary (confirmed by reading Config/source_types.json).
SOURCE_TYPE = "clean_text"

# creator = "lingq" exists in the real workspace creators config
# (paths.CREATORS_CONFIG); the script validates it at startup and fails
# clearly rather than silently creating it.
CREATOR = "lingq"

# material_level = 1 is "Absolute Beginner" in project_config.MATERIAL_LEVELS
# (confirmed by reading that constant; 1 is still correct).
MATERIAL_LEVEL = 1

# Collision-safe source-name prefix: keeps every source traceable to its
# LingQ folder and safe against any future LingQ folder that also happens to
# have its own ep001.txt. Per-file source_name = f"{PREFIX}-{episode}".
SOURCE_NAME_PREFIX = "lingq-9795706"

PRODUCTION_MANAGER_SCRIPT = (
    PROJECT_ROOT / "Production Manager" / "production_manager.py"
)

# Pure section-label lines to drop. Nothing else is stripped: the numbered
# question-index prefixes (一:, 二:, ...) are intentionally left embedded.
_SECTION_LABELS = ("質問:", "質問：")

# Classification kinds.
KIND_IMPORT = "import"
KIND_SKIP_ALREADY = "skip_already"
KIND_SKIP_NO_MANIFEST = "skip_no_manifest"


class LingQImportError(Exception):
    """Raised when a LingQ source file cannot be read or cleaned."""


# Result of cleaning one file: the cleaned source text plus the number of
# lines that had an "A)"/"B)" structural prefix removed.
CleanResult = namedtuple("CleanResult", ["source_text", "n_stripped"])


def resolve_venv_python():
    """
    Return the project venv Python executable.

    Same resolution convention as batch_importer.py and the Production
    Manager api stage: PROJECT_ROOT/.venv/Scripts/python.exe. Never a
    hardcoded absolute path assumption.
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


def load_manifest(folder):
    """
    Map each episode file stem to its manifest episode value.

    Input: folder (Path).
    Output: dict {file_stem: manifest "episode" column value}, e.g.
        {"ep001": "ep001", ...}.
    Raises: FileNotFoundError when manifest.csv is absent; OSError /
        UnicodeError / csv.Error when it cannot be read.
    """
    manifest_path = folder / MANIFEST_NAME
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    episodes = {}
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            episode = (row.get("episode") or "").strip()
            if episode:
                episodes[episode] = episode
    return episodes


def clean_source_text(raw_text):
    """
    Clean raw LingQ Mini Stories text into sentence-per-line source text.

    Input: raw_text (str), as read from an episode file.
    Output: CleanResult(source_text, n_stripped):
        source_text - cleaned text, one real sentence per line, no blank
            lines, ending with a single newline;
        n_stripped - count of lines that had an "A)"/"B)" prefix removed.

    Cleaning rules (confirmed by direct inspection of all 62 files):
      - A line-start "A)" or "B)" (exactly two characters: capital letter,
        ASCII close-paren) is a structural prefix and is removed.
      - A line that, after stripping A)/B)/whitespace, is exactly the section
        label "質問:" or "質問：" is dropped entirely (never blanked -- a
        dropped line leaves no empty line behind).
      - Every remaining line is one real sentence, preserved verbatim
        including its own internal punctuation. Numbered question-index
        prefixes (一:, 二:, ... and the observed non-kanji variant "ー:") are
        deliberately NOT detected or stripped.
    """
    lines = []
    n_stripped = 0
    for raw_line in raw_text.splitlines():
        line = raw_line
        if line.startswith("A)") or line.startswith("B)"):
            line = line[2:]
            n_stripped += 1
        if line.strip() in _SECTION_LABELS:
            # Pure section-label line: drop it entirely, not blanked.
            continue
        if not line.strip():
            # Defensive: no blank lines are sentence content.
            continue
        lines.append(line)
    return CleanResult("\n".join(lines) + "\n", n_stripped)


def clean_file(path):
    """
    Read and clean one LingQ episode file.

    Input: path (Path).
    Output: CleanResult.
    Raises: LingQImportError on read failure or empty cleaned text.
    """
    try:
        raw_text = path.read_text(encoding="utf-8-sig")
    except (UnicodeDecodeError, OSError) as exc:
        raise LingQImportError(f"cannot read {path.name}: {exc}") from exc
    result = clean_source_text(raw_text)
    if not result.source_text.strip():
        raise LingQImportError(f"cleaned text is empty: {path.name}")
    return result


def classify(path, episode):
    """
    Classify one episode file for the batch (shared by real and dry-run modes).

    Input: path (Path), episode (str, the manifest episode value).
    Output: (kind, source_name) where kind is one of KIND_*.
    """
    source_name = f"{SOURCE_NAME_PREFIX}-{episode}"
    if controller.standalone_source_path(source_name).is_file():
        return KIND_SKIP_ALREADY, source_name
    return KIND_IMPORT, source_name


def import_one(path, episode, stage_timeout=None):
    """
    Import one episode file through the full pipeline.

    Assumes the file was already classified for import (has a manifest row
    and no existing canonical source).

    Mirrors batch_importer.import_one() exactly (create_standalone_source ->
    load_source_package -> handoff -> production_manager subprocess), swapping
    only the format-specific conversion step for the LingQ cleaning above.

    Input: path (Path), episode (str), stage_timeout (int|None).
    Output: None on success, or (stage, message) on failure.
    """
    source_name = f"{SOURCE_NAME_PREFIX}-{episode}"

    try:
        source_text = clean_file(path).source_text
    except LingQImportError as exc:
        return "clean", str(exc)

    try:
        result = handoff.register_standalone_source(
            source_name, SOURCE_TYPE, CREATOR, source_text,
            material_level=MATERIAL_LEVEL)
    except handoff.HandoffError as exc:
        return "create", str(exc)

    # register_standalone_source returns two shapes: controller's own
    # create-result dict (no "registry" key) when it stopped before ever
    # reaching handoff, or handoff()'s result dict (has "registry") on
    # success/non-collision failure.
    if "registry" not in result:
        if result.get("package_error"):
            return "create", f"source package was not written: {result['package_error']}"
        return "create", "; ".join(result["errors"])
    if result.get("errors"):
        return "handoff", "; ".join(result["errors"])

    source_id = result["source_id"]
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
        prog="import_lingq_mini_stories.py",
        description="Import the 62 LingQ Mini Stories episode files through "
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
        episodes = load_manifest(folder)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError, csv.Error) as exc:
        print(f"Error: cannot read manifest {folder / MANIFEST_NAME}: {exc}",
              file=sys.stderr)
        return 1
    if not episodes:
        print(f"Error: manifest has no episode rows: {folder / MANIFEST_NAME}",
              file=sys.stderr)
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
        if path.stem not in episodes:
            skipped_no_manifest += 1
            print(f"[SKIP no-manifest-row] {path.name}"
                  if not args.dry_run
                  else f"[WOULD-SKIP no-manifest-row] {path.name}")
            continue

        episode = episodes[path.stem]
        kind, source_name = classify(path, episode)

        if args.dry_run:
            # Dry run: clean (read-only) to report what WOULD happen; create,
            # write, and run nothing.
            try:
                result = clean_file(path)
            except LingQImportError as exc:
                failures.append((path.name, "clean", str(exc)))
                print(f"[WOULD-FAIL clean] {path.name}: {exc}")
                continue
            detail = (
                f"({len(result.source_text.splitlines())} lines, "
                f"{result.n_stripped} A/B stripped)"
            )
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
            failure = import_one(path, episode, args.stage_timeout)
        except Exception as exc:
            # Defensive catch-all: never let one file abort the batch.
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
