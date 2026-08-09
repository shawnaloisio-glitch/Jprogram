#!/usr/bin/env python3
"""
run_qc_pipeline.py

Japanese Corpus Pipeline - QC Test Harness.

Drives a hand-authored, known-ground-truth Japanese source (see
qc_test_001_source.txt / qc_test_001_expected.json) through the REAL
production pipeline, using the same functions the GUI and Production
Manager call -- not a reimplementation. Because the intermediate result
is known in advance, this doubles as independent QC: the analyzer output
can be checked against the recorded expected values rather than just
trusted.

Stages, in order:
    1. setup    - birth certificate (Source Package) + Registry + Cleaning Job
                  (Source Intake functions, no cost, no network)
    2. clean    - Transcript Cleaner (no cost, no network)
    3. jobs     - Job Builder (no cost, no network)
    4. requests - Request Builder (no cost, no network)
     5. send     - DeepSeek Client -- REAL API CALL, spends real money.
                   Requires a valid DEEPSEEK_API_KEY environment variable.
     6. parse    - Deterministic Parser Client (GiNZA via the project's
                   .venv, no cost, no network). Free/local alternative to
                   "send" for testing the deterministic parser; same
                   job-in/response-out contract, but deterministic and
                   offline.
     7. corpus   - Corpus Builder (no cost, no network)
     8. check    - Scan the canonical JSONL records directly (no analyzer
                   modules) and compare against qc_test_001_expected.json.

Usage:
    python "QC Test Harness/run_qc_pipeline.py" setup
    python "QC Test Harness/run_qc_pipeline.py" clean
    python "QC Test Harness/run_qc_pipeline.py" jobs
    python "QC Test Harness/run_qc_pipeline.py" requests
    python "QC Test Harness/run_qc_pipeline.py" send      # spends money
    python "QC Test Harness/run_qc_pipeline.py" parse     # free, no network
    python "QC Test Harness/run_qc_pipeline.py" corpus
    python "QC Test Harness/run_qc_pipeline.py" check
    python "QC Test Harness/run_qc_pipeline.py" all       # runs everything, including send

Re-running "setup" is safe: Source Intake's handoff is idempotent (same
source_id + same sha256 -> reports "exists", creates nothing new).
Re-running "send" is also safe if a response already exists (DeepSeek
Client resumes rather than re-sending), but if you genuinely want a fresh
parse, delete the response file under
responses\\clean_text_qc-test-001\\ first.
"""

import json
import subprocess
import sys
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = HARNESS_DIR.parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Source Builder"))
sys.path.insert(0, str(PROJECT_ROOT / "Source Intake"))

SOURCE_NAME = "qc_test_001"
SOURCE_TYPE = "clean_text"
CREATOR = "qc_test"
LANGUAGE = "ja"
SOURCE_ID = "clean_text_qc-test-001"


def stage_setup():
    import source_package
    import handoff
    import paths

    paths.SOURCES.mkdir(parents=True, exist_ok=True)
    canonical_path = paths.SOURCES / f"{SOURCE_NAME}.txt"

    src_text = (HARNESS_DIR / "qc_test_001_source.txt").read_text(encoding="utf-8")
    canonical_path.write_text(src_text, encoding="utf-8", newline="\n")
    print("wrote canonical text:", canonical_path, "chars:", len(src_text))

    cleaning_profile = source_package.cleaning_profile_for(SOURCE_TYPE)
    cleaner_version = source_package.cleaner_version_for(cleaning_profile)

    package = source_package.build_package(
        source_type=SOURCE_TYPE,
        creator=CREATOR,
        language=LANGUAGE,
        canonical_path=canonical_path,
        cleaning_profile=cleaning_profile,
        cleaner_version=cleaner_version,
        material_level=0,
        source_name=SOURCE_NAME,
    )
    source_package.write_package(package)
    print("source_id:", package["source_id"])

    result = handoff.handoff(package)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def _run(args):
    print("+", " ".join(str(a) for a in args))
    result = subprocess.run(args, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"  -> exit code {result.returncode}")
    return result.returncode


def stage_clean():
    import paths
    job_path = paths.CLEANING_JOBS / f"{SOURCE_ID}.cleaning_job.json"
    return _run([sys.executable, str(PROJECT_ROOT / "Transcript Cleaner" / "clean_transcript.py"),
                 "--job", str(job_path)])


def stage_jobs():
    return _run([sys.executable, str(PROJECT_ROOT / "Data Processor" / "job builder.py"),
                 "--source", SOURCE_ID])


def stage_requests():
    return _run([sys.executable, str(PROJECT_ROOT / "Data Processor" / "request builder.py"),
                 "--source", SOURCE_ID])


def stage_send():
    print("*** This stage makes a real DeepSeek API call and spends real money. ***")
    return _run([sys.executable, str(PROJECT_ROOT / "Data Processor" / "deepseek_client.py"),
                 "--source", SOURCE_ID])


def stage_parse():
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    return _run([str(venv_python), str(PROJECT_ROOT / "Data Processor" / "deterministic_parser_client.py"),
                 "--source", SOURCE_ID])


def stage_corpus():
    return _run([sys.executable, str(PROJECT_ROOT / "Data Processor" / "corpus_builder.py"),
                 "--source", SOURCE_ID])


def stage_check():
    import paths

    expected = json.loads((HARNESS_DIR / "qc_test_001_expected.json").read_text(encoding="utf-8"))

    corpus_path = paths.JSONL / f"{SOURCE_ID}.jsonl"
    if not corpus_path.is_file():
        print(f"No canonical corpus found at {corpus_path} -- run the 'corpus' stage first.")
        return 1

    # Inline canonical JSONL reader (replaces corpus_loader.load_all):
    # one record per non-blank line, in file order.
    records = []
    with corpus_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            records.append(json.loads(line))

    # Frequency (replaces frequency_analyzer.analyze): per lexical key,
    # total occurrences and per-surface counts. Grouping key matches
    # Analysis/frequency_analyzer.py: word[2] (lexical) when it is a
    # non-empty string, else word[1] (surface).
    freq_items = {}
    for record in records:
        for word in record.get("words") or []:
            surface = word[1]
            lexical = word[2]
            key = lexical if isinstance(lexical, str) and lexical else surface
            item = freq_items.setdefault(key, {"occurrences": 0, "surfaces": {}})
            item["occurrences"] += 1
            item["surfaces"][surface] = item["surfaces"].get(surface, 0) + 1

    freq = {
        "frequency": {
            key: {
                "occurrences": item["occurrences"],
                "surfaces": {
                    surface: item["surfaces"][surface]
                    for surface in sorted(item["surfaces"])
                },
            }
            for key, item in sorted(freq_items.items())
        }
    }

    # Distribution (replaces distribution_analyzer.analyze): only
    # sentence_distance min/max is read by the comparison below, so only
    # that is computed. The running global sentence index is 0-based and
    # incremented once per record, matching Analysis/distribution_analyzer.py.
    prev_sentence_by_key = {}
    sentence_gaps_by_key = {}
    global_sentence_index = 0
    for record in records:
        for word in record.get("words") or []:
            surface = word[1]
            lexical = word[2]
            key = lexical if isinstance(lexical, str) and lexical else surface
            gaps = sentence_gaps_by_key.setdefault(key, [])
            if key in prev_sentence_by_key:
                gaps.append(global_sentence_index - prev_sentence_by_key[key])
            prev_sentence_by_key[key] = global_sentence_index
        global_sentence_index += 1

    dist = {
        "distribution": {
            key: {
                "sentence_distance": {
                    "min": min(gaps) if gaps else None,
                    "max": max(gaps) if gaps else None,
                }
            }
            for key, gaps in sentence_gaps_by_key.items()
        }
    }

    # Chunks (replaces chunk_analyzer.analyze): per chunk-text occurrence
    # count, grouped by chunk[1] (text), matching Analysis/chunk_analyzer.py.
    chunk_counts = {}
    for record in records:
        for chunk in record.get("chunks") or []:
            key = chunk[1]
            chunk_counts[key] = chunk_counts.get(key, 0) + 1

    chunks = {
        "chunks": {
            key: {"occurrences": chunk_counts[key]}
            for key in sorted(chunk_counts)
        },
        "summary": {"distinct_chunks": len(chunk_counts)},
    }

    print(f"records loaded: {len(records)} (expected sentence_count: {expected['sentence_count']})")
    print()

    ok = True
    for lexical, exp in expected["lexical_items"].items():
        f = freq["frequency"].get(lexical)
        d = dist["distribution"].get(lexical)
        print(f"--- {lexical!r} ({exp.get('gloss', '')}) ---")
        if f is None:
            print(f"  MISSING from frequency output (expected occurrences={exp['occurrences']})")
            ok = False
            continue
        occ_ok = f["occurrences"] == exp["occurrences"]
        print(f"  occurrences: actual={f['occurrences']} expected={exp['occurrences']} "
              f"{'OK' if occ_ok else 'MISMATCH'}")
        if not occ_ok:
            ok = False
        print(f"  surfaces: {f['surfaces']}")
        if "expected_surfaces" in exp:
            surf_ok = f["surfaces"] == exp["expected_surfaces"]
            print(f"  surfaces match expected: {'OK' if surf_ok else 'MISMATCH'} "
                  f"(expected {exp['expected_surfaces']})")
            if not surf_ok:
                ok = False
        if d and "sentence_distance" in exp:
            sd = d["sentence_distance"]
            exp_sd = exp["sentence_distance"]
            sd_ok = (sd["min"] == exp_sd["min"] and sd["max"] == exp_sd["max"])
            print(f"  sentence_distance: actual={sd} expected={exp_sd} "
                  f"{'OK (min/max)' if sd_ok else 'MISMATCH'}")
            if not sd_ok:
                ok = False
        print()

    print("--- qualitative checks (not hard-asserted) ---")
    print("chunk count:", chunks["summary"]["distinct_chunks"])
    for key, c in chunks["chunks"].items():
        if "ことにし" in key or "こと" in key:
            print(f"  candidate chunk match: {key!r} occurrences={c['occurrences']}")

    print()
    print("OVERALL:", "PASS" if ok else "MISMATCHES FOUND -- see above")
    return 0 if ok else 1


STAGES = {
    "setup": stage_setup,
    "clean": stage_clean,
    "jobs": stage_jobs,
    "requests": stage_requests,
    "send": stage_send,
    "parse": stage_parse,
    "corpus": stage_corpus,
    "check": stage_check,
}

ORDER = ["setup", "clean", "jobs", "requests", "send", "corpus", "check"]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) != 2 or sys.argv[1] not in STAGES and sys.argv[1] != "all":
        print(__doc__)
        return 1

    which = sys.argv[1]
    stages = ORDER if which == "all" else [which]

    for name in stages:
        print(f"=== stage: {name} ===")
        code = STAGES[name]()
        if code:
            print(f"stage {name!r} failed (exit {code}); stopping.")
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
