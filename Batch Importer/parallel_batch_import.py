#!/usr/bin/env python3
"""
parallel_batch_import.py

Japanese Corpus Pipeline - Parallel Batch Importer (orchestration only).

Splits a folder's files across N worker processes, each running the real
batch_importer.py --batch-mode against its own disjoint slice, running
concurrently. Contains no import/pipeline logic of its own -- every file
still goes through the same, already-tested batch_importer.py; this script
only decides which files go to which worker and launches them.

Safe to parallelize: every source_id's artifacts are independent files,
written atomically (temp + rename) throughout the pipeline -- disjoint
file slices across workers never write to the same path, so there is
nothing for concurrent workers to race on.

Each worker still pays its own one-time ja_ginza model load (N workers =
N model loads, not one per file within that worker's slice), trading a
few extra model loads for real parallelism across CPU cores.

Run:
    python "Batch Importer/parallel_batch_import.py" --folder <dir> \
        --creator <id> [--workers 6] [--style S] [--topic T] \
        [--episode E] [--season S] [--stage-timeout T] [--dry-run]
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BATCH_IMPORTER_SCRIPT = Path(__file__).resolve().parent / "batch_importer.py"
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(PROJECT_ROOT))

import batch_importer


def resolve_venv_python():
    """Same resolution convention as batch_importer.resolve_venv_python()."""
    return PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"


def list_importable_files(folder):
    """
    Files in folder that batch_importer.classify() would actually import
    (not already-imported, not an unsupported format).

    Pre-filtering here (rather than staging every file and letting each
    worker skip the rest) means chunk sizes reflect real work, not just
    file count -- a folder that's mostly already-imported still splits the
    remaining real work evenly across workers.

    Input: folder (Path).
    Output: sorted list of Path.
    """
    files = sorted(p for p in Path(folder).iterdir() if p.is_file())
    todo = []
    for path in files:
        kind, _source_format = batch_importer.classify(path)
        if kind == batch_importer.KIND_IMPORT:
            todo.append(path)
    return todo


def chunk(items, n):
    """
    Split items into at most n roughly-equal, order-preserving chunks.

    Input: items (list), n (int).
    Output: list of non-empty lists (fewer than n if items has fewer than
        n elements).
    """
    chunks = [[] for _ in range(n)]
    for i, item in enumerate(items):
        chunks[i % n].append(item)
    return [c for c in chunks if c]


def stage_chunk(files, level_folder_name, staging_root, worker_index):
    """
    Copy one worker's file slice into its own staging subfolder, named
    after the source folder's own name so material-level detection (which
    reads the parent folder name) still resolves correctly.

    Input: files (list of Path), level_folder_name (str), staging_root
        (Path), worker_index (int).
    Output: the worker's staging directory (Path).
    """
    dest_dir = staging_root / f"worker_{worker_index}" / level_folder_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    for path in files:
        shutil.copy2(path, dest_dir / path.name)
    return dest_dir


def build_worker_command(folder, creator, style, topic, episode, season,
                         stage_timeout, dry_run):
    """Build the argv for one batch_importer.py --batch-mode worker."""
    argv = [
        str(resolve_venv_python()), str(BATCH_IMPORTER_SCRIPT),
        "--folder", str(folder), "--creator", creator, "--batch-mode",
    ]
    if style is not None:
        argv += ["--style", str(style)]
    if topic is not None:
        argv += ["--topic", str(topic)]
    if episode is not None:
        argv += ["--episode", str(episode)]
    if season is not None:
        argv += ["--season", str(season)]
    if stage_timeout is not None:
        argv += ["--stage-timeout", str(stage_timeout)]
    if dry_run:
        argv += ["--dry-run"]
    return argv


def parse_summary_counts(output):
    """
    Parse one worker's four Summary counters out of its stdout.

    Input: output (str) -- one worker's captured stdout+stderr.
    Output: dict with keys imported/skipped_already/skipped_unsupported/
        failed (int, 0 if a line was not found).
    """
    counts = {
        "imported": 0, "skipped_already": 0,
        "skipped_unsupported": 0, "failed": 0,
    }
    prefixes = {
        "  imported:": "imported",
        "  skipped (already imported):": "skipped_already",
        "  skipped (unsupported format):": "skipped_unsupported",
        "  failed:": "failed",
    }
    for line in output.splitlines():
        for prefix, key in prefixes.items():
            if line.startswith(prefix):
                try:
                    counts[key] = int(line[len(prefix):].strip())
                except ValueError:
                    pass
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="parallel_batch_import.py",
        description="Split a folder of already-normalized source files "
                    "across N parallel batch_importer.py --batch-mode "
                    "workers.",
    )
    parser.add_argument(
        "--folder", required=True,
        help="folder containing the normalized source files "
             "(non-recursive; same contract as batch_importer.py).",
    )
    parser.add_argument(
        "--creator", required=True,
        help="creator_id; must exist in the workspace Config/creators.json.",
    )
    parser.add_argument(
        "--workers", type=int, default=6,
        help="number of parallel worker processes (default 6).",
    )
    parser.add_argument("--style", default=None)
    parser.add_argument("--topic", default=None)
    parser.add_argument("--episode", type=int, default=None)
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--stage-timeout", type=int, default=None)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="print what would happen; create nothing, write nothing, "
             "run nothing.",
    )
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Error: folder not found: {folder}", file=sys.stderr)
        return 1

    if args.workers < 1:
        print("Error: --workers must be at least 1", file=sys.stderr)
        return 1

    creator_error = batch_importer.validate_creator(args.creator)
    if creator_error:
        print(f"Error: {creator_error}", file=sys.stderr)
        return 1

    level_folder_name = folder.name

    todo = list_importable_files(folder)
    print(f"Files to import: {len(todo)}")
    if not todo:
        print("Nothing to do.")
        return 0

    n_workers = max(1, min(args.workers, len(todo)))
    chunks = chunk(todo, n_workers)
    print(f"Splitting across {len(chunks)} worker(s) "
          f"(~{len(todo) // len(chunks)} files each)\n")

    staging_root = Path(tempfile.mkdtemp(prefix="parallel_batch_import_"))
    results = {}
    try:
        procs = []
        for i, file_chunk in enumerate(chunks):
            worker_dir = stage_chunk(
                file_chunk, level_folder_name, staging_root, i)
            cmd = build_worker_command(
                worker_dir, args.creator, args.style, args.topic,
                args.episode, args.season, args.stage_timeout,
                args.dry_run)
            print(f"[worker {i}] {len(file_chunk)} files -> launching")
            proc = subprocess.Popen(
                cmd, cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
            )
            procs.append((i, proc))

        # All n_workers processes are now running concurrently; waiting on
        # proc 0 here does not block the others, which continue running in
        # the background while we wait.
        for i, proc in procs:
            out, _ = proc.communicate()
            results[i] = (proc.returncode, out)
            print(f"[worker {i}] finished, exit code {proc.returncode}")
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)

    totals = {
        "imported": 0, "skipped_already": 0,
        "skipped_unsupported": 0, "failed": 0,
    }
    for i, (_code, out) in sorted(results.items()):
        print(f"\n=== worker {i} output ===")
        print(out)
        counts = parse_summary_counts(out)
        for key in totals:
            totals[key] += counts[key]

    print("\nCombined Summary:")
    print(f"  imported: {totals['imported']}")
    print(f"  skipped (already imported): {totals['skipped_already']}")
    print(f"  skipped (unsupported format): {totals['skipped_unsupported']}")
    print(f"  failed: {totals['failed']}")

    return 1 if totals["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
