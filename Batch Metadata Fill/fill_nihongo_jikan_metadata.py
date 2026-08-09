#!/usr/bin/env python3
"""
fill_nihongo_jikan_metadata.py

Japanese Corpus Pipeline - Batch Metadata Fill.

One-off script that fills Style / Topic / Duration / Episode# metadata on the
nihongo_jikan source packages created by the Batch Importer
(Batch Importer/batch_importer.py) from D:\\Nihongo Jikan media\\Transcripts\\Beginner.

The rename log (Workspace/jsonl/rename_log.csv) records how each normalized
"NHGJM id<NNNNN>" source name maps back to its original title (real_name);
that original title is the only source of topic / episode information. Audio
duration is read from the matching .mp3 in D:\\Nihongo Jikan media\\Audio
\\Beginner via ONE PowerShell Shell.Application COM call (the "Length" column
is looked up by name, never a hardcoded index) and returned as JSON.

Default mode is dry-run: it prints exactly what would change and writes
nothing. Pass --apply to actually write the updated packages through Source
Builder's source_package.write_package() so validation and atomic-write
behavior are preserved exactly as the rest of the product already guarantees.

This script is NEW code (a new file in a new folder). It does not modify any
existing pipeline stage. It touches only four fields on each package --
style_id, topic_id, duration_seconds, episode_number -- and leaves every other
field, including material_level and season_number, completely untouched.
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

# Allow imports from the project root and Source Builder (project convention;
# this is the same pattern Batch Importer/batch_importer.py uses to resolve
# paths.SOURCES and import Source Builder modules).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Source Builder"))

import paths
import source_package
from config_loader import load_styles_full, load_topics_full

# The audio folder whose matching .mp3 files provide duration (Windows
# Explorer "Length" shell property, HH:MM:SS, read via Shell.Application).
AUDIO_DIR = Path(r"D:\Nihongo Jikan media\Audio\Beginner")

# The rename log written by the batch importer: new_name,real_name,size,date.
RENAME_LOG = paths.JSONL / "rename_log.csv"

# Every one of these sources gets the "Comprehensible Input" style.
STYLE_DISPLAY_NAME = "Comprehensible Input"

# Topic rules, checked in this order; the first match wins. The "Let.?s Play"
# regex is case-sensitive and matches any single-char apostrophe variant
# ("Let's Play" / "Lets Play" / ...). The other two are literal substrings.
TOPIC_RULES = (
    (re.compile(r"Let.?s Play"), "Let's Play"),
    (re.compile(r"Father and Son"), "Father and Son"),
    (re.compile(r"Mini-Fantasy Theater"), "Mini-Fantasy Theater"),
)
FALLBACK_TOPIC = "Various"

EPISODE_RE = re.compile(r"EP(\d+)")

# PowerShell script that emits {"<basename-without-extension>": <seconds>} for
# every .mp3 in the folder, as a single JSON object on stdout. The "Length"
# column index is found by property NAME (GetDetailsOf($null, $i)) rather than
# hardcoded. __AUDIO_DIR__ is replaced with the real folder before invoking.
POWERSHELL_DURATION_SCRIPT = """\
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$folder = '__AUDIO_DIR__'
$shell = New-Object -ComObject Shell.Application
$dir = $shell.NameSpace($folder)
if ($null -eq $dir) { throw "cannot open folder: $folder" }
$lengthIndex = $null
for ($i = 0; $i -lt 400; $i++) {
    $column = $dir.GetDetailsOf($null, $i)
    if ($column -eq 'Length') { $lengthIndex = $i; break }
}
if ($null -eq $lengthIndex) { throw "Length column not found in Shell.Application folder details" }
$result = @{}
foreach ($item in $dir.Items()) {
    if (-not $item.IsFolder -and $item.Name -like '*.mp3') {
        $base = [System.IO.Path]::GetFileNameWithoutExtension($item.Name)
        $value = $dir.GetDetailsOf($item, $lengthIndex)
        $parts = $value -split ':'
        if ($parts.Count -eq 3) {
            $result[$base] = [int]$parts[0] * 3600 + [int]$parts[1] * 60 + [int]$parts[2]
        }
        elseif ($parts.Count -eq 2) {
            $result[$base] = [int]$parts[0] * 60 + [int]$parts[1]
        }
    }
}
$result | ConvertTo-Json -Compress
"""


def _without_html(name):
    """Strip a trailing '.html' / '.HTML' extension from a filename."""
    if name is None:
        return None
    if name.lower().endswith(".html"):
        return name[: -len(".html")]
    return name


def load_style_id(display_name):
    """
    Return the real style_id for a display_name from the workspace styles
    config (never a hardcoded id). Fails loudly when the entry is missing.
    """
    for entry in load_styles_full():
        if entry["display_name"] == display_name:
            return entry["style_id"]
    raise SystemExit(
        f"ERROR: style {display_name!r} not found in {paths.STYLES_CONFIG}")


def load_topic_ids_by_name():
    """
    Return {display_name: topic_id} from the workspace topics config (never
    hardcoded ids). Fails loudly when any topic the rules need is missing.
    """
    topics = load_topics_full()
    result = {entry["display_name"]: entry["topic_id"] for entry in topics}
    required = {name for _, name in TOPIC_RULES} | {FALLBACK_TOPIC}
    missing = sorted(required - set(result))
    if missing:
        raise SystemExit(
            f"ERROR: topics {missing} not found in {paths.TOPICS_CONFIG}")
    return result


def load_rename_log(path):
    """
    Build {new_name_without_extension: real_name_without_extension} from the
    rename log CSV. Both the normalized name and the original title have their
    ".html" extension stripped (the audio basename is the title without the
    extension).
    """
    rename_log = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            new_name = _without_html(row.get("new_name"))
            real_name = _without_html(row.get("real_name"))
            if new_name and real_name:
                rename_log[new_name] = real_name
    return rename_log


def build_audio_duration_lookup(audio_dir):
    """
    Build {mp3_basename_without_extension: total_duration_seconds} for every
    .mp3 in audio_dir.

    One PowerShell Shell.Application COM invocation for the whole folder
    (never one per file); its stdout is parsed as JSON into an in-memory dict.
    """
    audio_dir = Path(audio_dir)
    if not audio_dir.is_dir():
        raise FileNotFoundError(f"audio directory not found: {audio_dir}")

    ps_script = POWERSHELL_DURATION_SCRIPT.replace(
        "__AUDIO_DIR__", str(audio_dir))
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        detail = (completed.stderr or "").strip() or (completed.stdout or "").strip()
        raise RuntimeError(
            f"PowerShell duration scan failed (exit {completed.returncode}): {detail}")

    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"cannot parse PowerShell duration output as JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise RuntimeError(
            "unexpected PowerShell duration output (expected a JSON object): "
            f"{type(data).__name__}")
    return data


def enumerate_nihongo_jikan_sources():
    """
    Return the sorted list of every *.source.json under paths.SOURCES whose
    creator is "nihongo_jikan", read as JSON.

    Unreadable packages are reported as skip reasons (identifier, reason) so
    the run never crashes on one bad file, but the dry-run summary still shows
    exactly what was skipped and why.
    """
    packages = []
    unreadable = []
    for package_path in sorted(paths.SOURCES.glob("*.source.json")):
        try:
            with package_path.open("r", encoding="utf-8-sig") as file:
                package = json.load(file)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
            unreadable.append((package_path.name, f"unreadable package JSON: {exc}"))
            continue
        if package.get("creator") == "nihongo_jikan":
            packages.append(package)
    return packages, unreadable


def topic_for(real_name):
    """Return the topic display_name for a real_name per the ordered rules."""
    for regex, display_name in TOPIC_RULES:
        if regex.search(real_name):
            return display_name
    return FALLBACK_TOPIC


def episode_for(real_name):
    """Return int(EP<digits>) from the first match, or None when no match."""
    match = EPISODE_RE.search(real_name)
    if match:
        return int(match.group(1))
    return None


def compute_metadata(real_name, style_id, topic_id_by_name):
    """Compute the 4 metadata values for one matched real_name."""
    topic_id = topic_id_by_name[topic_for(real_name)]
    return {
        "style_id": style_id,
        "topic_id": topic_id,
        "duration_seconds": None,  # filled by the caller from the audio lookup
        "episode_number": episode_for(real_name),
    }


def format_transition(old, new):
    """Render one field's old->new transition for the dry-run line."""
    return f"{old}->{new}"


def print_dry_run_line(result):
    """Print one per-source dry-run line: source_id + 4 field transitions."""
    old, new = result["old"], result["new"]
    print(
        f"[DRY-RUN] {result['source_id']}"
        f" | style_id: {format_transition(old['style_id'], new['style_id'])}"
        f" | topic_id: {format_transition(old['topic_id'], new['topic_id'])}"
        f" | duration_seconds: "
        f"{format_transition(old['duration_seconds'], new['duration_seconds'])}"
        f" | episode_number: "
        f"{format_transition(old['episode_number'], new['episode_number'])}"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="fill_nihongo_jikan_metadata.py",
        description="Fill Style/Topic/Duration/Episode# metadata on the "
                    "nihongo_jikan source packages created by the Batch "
                    "Importer. Default is dry-run (writes nothing); pass "
                    "--apply to write the updated packages.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually write the updated source packages via "
             "source_package.write_package() (default is dry-run only).",
    )
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Controlled vocabularies -- read the real ids, never hardcode them.
    style_id = load_style_id(STYLE_DISPLAY_NAME)
    topic_id_by_name = load_topic_ids_by_name()

    rename_log = load_rename_log(RENAME_LOG)
    audio_lookup = build_audio_duration_lookup(AUDIO_DIR)

    packages, unreadable = enumerate_nihongo_jikan_sources()

    results = []
    skips = []

    for package in packages:
        source_name = package.get("source_name")
        source_id = package.get("source_id", "?")
        if not source_name:
            skips.append((source_id, "package has no source_name"))
            continue

        real_name = rename_log.get(source_name)
        if real_name is None:
            skips.append((source_id, "not found in rename_log.csv"))
            continue

        new = compute_metadata(real_name, style_id, topic_id_by_name)
        new["duration_seconds"] = audio_lookup.get(real_name)

        old = {
            "style_id": package.get("style_id"),
            "topic_id": package.get("topic_id"),
            "duration_seconds": package.get("duration_seconds"),
            "episode_number": package.get("episode_number"),
        }

        results.append({
            "source_id": source_id,
            "source_name": source_name,
            "real_name": real_name,
            "package": package,
            "old": old,
            "new": new,
        })

    # Include unreadable packages in the skip list (they carry the file name
    # instead of a source_id, which is the only identity available).
    skips.extend(unreadable)

    # --- per-source output -------------------------------------------------
    if args.apply:
        write_failures = []
        for result in results:
            package = dict(result["package"])
            for field, value in result["new"].items():
                package[field] = value
            try:
                written = source_package.write_package(package)
            except Exception as exc:
                # Defensive catch-all, matching the Batch Importer's
                # failure-isolation: one bad write never aborts the batch.
                write_failures.append((result["source_id"], str(exc)))
                print(f"[FAIL] {result['source_id']}: {exc}")
                continue
            print(f"[APPLY] {result['source_id']} wrote {written}")
        for source_id, reason in skips:
            print(f"[SKIP] {source_id}: {reason}")
    else:
        for result in results:
            print_dry_run_line(result)
        for source_id, reason in skips:
            print(f"[SKIP] {source_id}: {reason}")

    # --- summary block -----------------------------------------------------
    topic_counter = Counter(result["new"]["topic_id"] for result in results)
    topic_by_id = {topic_id: display_name
                   for display_name, topic_id in topic_id_by_name.items()}
    topic_breakdown = {
        topic_by_id[topic_id]: count
        for topic_id, count in sorted(topic_counter.items(),
                                      key=lambda item: topic_by_id[item[0]])
    }
    duration_matched = sum(
        1 for result in results if result["new"]["duration_seconds"] is not None)
    episode_set = sum(
        1 for result in results if result["new"]["episode_number"] is not None)

    skip_reason_counter = Counter(reason for _, reason in skips)

    print()
    print("Summary:")
    print(f"  total sources found: {len(packages)}")
    print(f"  matched rename_log: {len(results)}")
    print(f"  matched audio duration: {duration_matched}")
    print(f"  topic breakdown: {topic_breakdown}")
    print(f"  sources with non-null episode_number: {episode_set}")
    print(f"  unmatched/skipped: {len(skips)}")
    for reason, count in skip_reason_counter.most_common():
        print(f"    - {reason}: {count}")
    if args.apply:
        print(f"  write failures: {len(write_failures)}")
        for source_id, message in write_failures:
            print(f"    - {source_id}: {message}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
