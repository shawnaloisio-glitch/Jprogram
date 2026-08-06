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
    6. corpus   - Corpus Builder (no cost, no network)
    7. check    - Run frequency_analyzer / distribution_analyzer /
                  chunk_analyzer on the real output and compare against
                  qc_test_001_expected.json.

Usage:
    python "QC Test Harness/run_qc_pipeline.py" setup
    python "QC Test Harness/run_qc_pipeline.py" clean
    python "QC Test Harness/run_qc_pipeline.py" jobs
    python "QC Test Harness/run_qc_pipeline.py" requests
    python "QC Test Harness/run_qc_pipeline.py" send      # spends money
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
sys.path.insert(0, str(PROJECT_ROOT / "Analysis"))

SOURCE_NAME = "qc_test_001"
SOURCE_TYPE = "clean_text"
ORIGIN = "qc_test"
LANGUAGE = "ja"
SOURCE_ID = "clean_text_qc-test-001"


def stage_setup():
    import source_package
    import handoff
    import paths

    standalone_dir = paths.SOURCES / "standalone"
    standalone_dir.mkdir(parents=True, exist_ok=True)
    canonical_path = standalone_dir / f"{SOURCE_NAME}.txt"

    src_text = (HARNESS_DIR / "qc_test_001_source.txt").read_text(encoding="utf-8")
    canonical_path.write_text(src_text, encoding="utf-8", newline="\n")
    print("wrote canonical text:", canonical_path, "chars:", len(src_text))

    cleaning_profile = source_package.cleaning_profile_for(SOURCE_TYPE)
    cleaner_version = source_package.cleaner_version_for(cleaning_profile)

    package = source_package.build_package(
        source_type=SOURCE_TYPE,
        origin=ORIGIN,
        language=LANGUAGE,
        canonical_path=canonical_path,
        cleaning_profile=cleaning_profile,
        cleaner_version=cleaner_version,
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


def stage_corpus():
    return _run([sys.executable, str(PROJECT_ROOT / "Data Processor" / "corpus_builder.py"),
                 "--source", SOURCE_ID])


def stage_check():
    import corpus_loader
    import frequency_analyzer
    import distribution_analyzer
    import chunk_analyzer
    import paths

    expected = json.loads((HARNESS_DIR / "qc_test_001_expected.json").read_text(encoding="utf-8"))

    corpus_path = paths.JSONL / f"{SOURCE_ID}.jsonl"
    if not corpus_path.is_file():
        print(f"No canonical corpus found at {corpus_path} -- run the 'corpus' stage first.")
        return 1

    records = corpus_loader.load_all(corpus_path)
    freq = frequency_analyzer.analyze(records)
    dist = distribution_analyzer.analyze(records)
    chunks = chunk_analyzer.analyze(records)

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
