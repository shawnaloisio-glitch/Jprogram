#!/usr/bin/env python3
"""
test_source_builder_processing_tab.py

Deterministic tests for the Processing tab support layer:

- source package enumeration (collections + standalone),
- human labels (no source_id shown),
- status mapping (Pending/Ready/Complete/Failed),
- friendly failure messages (no technical stage names),
- sequential processing result shape,
- failed-source detection,
- troubleshooting dump bundle contents (identity, report, artifacts, logs,
  environment).

Run:
    python "Source Builder/tests/test_source_builder_processing_tab.py"
"""

import json
import pathlib
import sys
import tempfile
import threading
from unittest import mock

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Production Manager"))

import controller
import config_loader
import diagnostics
import processing_tab
import source_package
import paths

COLLECTION_NAME = "Con Teppei for Beginner"


def write_collection_source(sources_root, collection_id, episode,
                            text="こんにちは。\n", material_level=1):
    """Write a canonical source + package at an explicit episode.

    The controller ignores a caller-supplied episode (it is a hidden
    auto-incrementing system identifier), so the canonical file + package
    are written directly here to pin the episode for the test.
    """
    canonical = sources_root / controller.generate_filename(collection_id,
                                                            episode)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text(text, encoding="utf-8")
    profile = source_package.cleaning_profile_for("clean_text")
    package = source_package.build_package(
        source_type="clean_text",
        creator="con_teppei_podcast",
        language=controller.PROJECT_LANGUAGE,
        canonical_path=canonical,
        cleaning_profile=profile,
        cleaner_version=source_package.cleaner_version_for(profile),
        material_level=material_level,
        collection_id=collection_id,
        episode=episode,
    )
    source_package.write_package(package)
    return {"success": True, "filename": canonical.name,
            "path": str(canonical), "errors": []}


def make_sources(sources_root):
    """Create sandbox sources: one collection package + one standalone."""
    sources_root.mkdir(parents=True, exist_ok=True)
    result = write_collection_source(sources_root, "teppei_beginner", 58)
    standalone = controller.create_standalone_source(
        "nhk_weather", "clean_text", "nhk_news", "天気です。\n",
        material_level=1)
    return result, standalone


def patch_root(sources_root, config_dir):
    """Redirect Sources, Config, and collections config; save the prior globals."""
    saved = (controller.SOURCES_ROOT, config_loader.CONFIG_DIR,
             paths.COLLECTIONS_CONFIG)
    controller.SOURCES_ROOT = sources_root
    config_loader.CONFIG_DIR = config_dir
    paths.COLLECTIONS_CONFIG = config_dir / "collections.json"
    return saved


def restore(saved):
    controller.SOURCES_ROOT, config_loader.CONFIG_DIR, paths.COLLECTIONS_CONFIG = saved


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("discover_packages finds collection and standalone packages")
def _():
    root = pathlib.Path(tempfile.mkdtemp())
    sources_root = root / "Sources"
    config_dir = root / "Config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "collections.json").write_text(json.dumps({
        "collections": [
            {"collection_id": "teppei_beginner", "name": COLLECTION_NAME,
             "source_type": "clean_text"},
        ]
    }), encoding="utf-8")
    (config_dir / "source_types.json").write_text(json.dumps(
        {"source_types": ["clean_text"]}), encoding="utf-8")
    (config_dir / "creators.json").write_text(json.dumps(
        {"creators": ["con_teppei_podcast", "nhk_news"]}), encoding="utf-8")

    saved = patch_root(sources_root, config_dir)
    try:
        make_sources(sources_root)
        packages = processing_tab.discover_packages(sources_root)
        check("two packages", len(packages) == 2)
        labels = sorted(processing_tab.human_label(p) for p in packages)
        check("collection label",
              f"{COLLECTION_NAME} — ID#58" in labels)
        check("standalone label", "nhk_weather" in labels)
    finally:
        restore(saved)


@test("discover_packages orders collection episodes numerically")
def _():
    root = pathlib.Path(tempfile.mkdtemp())
    sources_root = root / "Sources"
    config_dir = root / "Config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "collections.json").write_text(json.dumps({
        "collections": [
            {"collection_id": "teppei_beginner", "name": COLLECTION_NAME,
             "source_type": "clean_text"},
        ]
    }), encoding="utf-8")
    (config_dir / "source_types.json").write_text(json.dumps(
        {"source_types": ["clean_text"]}), encoding="utf-8")
    (config_dir / "creators.json").write_text(json.dumps(
        {"creators": ["con_teppei_podcast", "nhk_news"]}), encoding="utf-8")

    saved = patch_root(sources_root, config_dir)
    try:
        # Mixed multi-digit episodes: a lexicographic ("ID#N" string)
        # sort would put 10 before 2 and 1000 before 999.
        for ep in (2, 10, 999, 1000):
            write_collection_source(sources_root, "teppei_beginner", ep,
                                    f"episode {ep}\n")
        packages = processing_tab.discover_packages(sources_root)
        episodes = [p.get("episode") for p in packages]
        check("numeric episode order", episodes == [2, 10, 999, 1000])
    finally:
        restore(saved)


@test("discover_packages tolerates missing and non-numeric episodes")
def _():
    root = pathlib.Path(tempfile.mkdtemp())
    sources_root = root / "Sources"
    config_dir = root / "Config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "collections.json").write_text(json.dumps({
        "collections": [
            {"collection_id": "teppei_beginner", "name": COLLECTION_NAME,
             "source_type": "clean_text"},
        ]
    }), encoding="utf-8")
    (config_dir / "source_types.json").write_text(json.dumps(
        {"source_types": ["clean_text"]}), encoding="utf-8")
    (config_dir / "creators.json").write_text(json.dumps(
        {"creators": ["con_teppei_podcast", "nhk_news"]}), encoding="utf-8")

    saved = patch_root(sources_root, config_dir)
    try:
        write_collection_source(sources_root, "teppei_beginner", 3, "ok\n")
        # A hand-written sidecar with a non-numeric episode must not crash
        # the sort.
        (sources_root / "teppei_beginner_bad.source.json").write_text(json.dumps({
            "source_id": "clean_text_teppei-beginner_bad",
            "collection_id": "teppei_beginner",
            "episode": "abc",
        }), encoding="utf-8")
        packages = processing_tab.discover_packages(sources_root)
        check("no crash, both discovered", len(packages) == 2)
        episodes = sorted(p.get("episode") for p in packages
                          if isinstance(p.get("episode"), int))
        check("valid episode present", episodes == [3])
    finally:
        restore(saved)


@test("human_label never exposes source_id")
def _():
    package = {
        "source_id": "clean_text_teppei-beginner_ep058",
        "collection_id": "teppei_beginner",
        "episode": 58,
    }
    label = processing_tab.human_label(package)
    check("label has display text", "ID#58" in label)
    check("no source_id", "clean_text_teppei-beginner" not in label)


@test("simple_status maps corpus_available to Complete")
def _():
    status, message = processing_tab.simple_status(
        {}, {"state": "corpus_available"})
    check("complete", status == processing_tab.STATUS_COMPLETE)
    check("no message", message == "")


@test("simple_status maps failed with friendly message")
def _():
    status, message = processing_tab.simple_status(
        {}, {"state": "failed", "failed_stage": "api"})
    check("failed", status == processing_tab.STATUS_FAILED)
    check("friendly api message", message == "Failed during parsing")


@test("simple_status maps unregistered to Pending")
def _():
    status, _ = processing_tab.simple_status({}, {"state": "unregistered"})
    check("pending", status == processing_tab.STATUS_PENDING)


@test("simple_status maps mid-pipeline states to Ready")
def _():
    for state in ("registered", "cleaned", "jobs_created", "api_complete"):
        status, _ = processing_tab.simple_status({}, {"state": state})
        check(f"{state} -> ready", status == processing_tab.STATUS_READY)


@test("friendly_failure_message hides technical stage names")
def _():
    check("api", processing_tab.friendly_failure_message(
        {"failed_stage": "api"}) == "Failed during parsing")
    check("corpus", processing_tab.friendly_failure_message(
        {"failed_stage": "corpus"})
        == "Failed while producing the final output")
    check("clean", processing_tab.friendly_failure_message(
        {"failed_stage": "clean"}) == "Failed while preparing the source")
    for msg in (processing_tab.friendly_failure_message(
            {"failed_stage": "api"}),
            processing_tab.friendly_failure_message(
                {"failed_stage": "corpus"})):
        check("no raw stage name",
              not any(s in msg.lower()
                      for s in ("clean", "jobs", "requests", "api",
                                "corpus", "artifact")))


@test("process_sources returns structured results sequentially")
def _():
    captured = []
    packages = [{"source_id": "a"}, {"source_id": "b"}, {"source_id": "c"}]

    def fake_pipeline(source_id, **kwargs):
        captured.append(source_id)
        return {"success": True, "state": "corpus_available",
                "failed_stage": None, "exit_code": 0}

    def fake_state_for(source_id):
        return {"state": "corpus_available"}

    with mock.patch.object(processing_tab.pm, "pipeline",
                           side_effect=fake_pipeline), \
         mock.patch.object(processing_tab.pm, "state_for",
                           side_effect=fake_state_for), \
         mock.patch.object(processing_tab, "_ensure_registered",
                           return_value=None):
        results = processing_tab.process_sources(packages)
    check("sequential order", captured == ["a", "b", "c"])
    check("three results", len(results) == 3)
    check("all success", all(r["success"] for r in results))
    check("state", results[0]["state"] == "corpus_available")


@test("process_sources stops at the next package once cancel is set")
def _():
    captured = []
    packages = [{"source_id": "a"}, {"source_id": "b"}, {"source_id": "c"}]
    cancel = threading.Event()

    def fake_pipeline(source_id, **kwargs):
        captured.append(source_id)
        if source_id == "a":
            cancel.set()
        return {"success": True, "state": "corpus_available",
                "failed_stage": None, "exit_code": 0}

    def fake_state_for(source_id):
        return {"state": "corpus_available"}

    with mock.patch.object(processing_tab.pm, "pipeline",
                           side_effect=fake_pipeline), \
         mock.patch.object(processing_tab.pm, "state_for",
                           side_effect=fake_state_for), \
         mock.patch.object(processing_tab, "_ensure_registered",
                           return_value=None):
        results = processing_tab.process_sources(
            packages, cancel_event=cancel)
    check("only the in-flight package ran", captured == ["a"])
    check("partial results only", len(results) == 1)
    check("result is a", results[0]["source_id"] == "a")
    check("full run not reported", results[0]["success"])


@test("process_sources runs nothing when cancel is already set")
def _():
    captured = []
    packages = [{"source_id": "a"}, {"source_id": "b"}]
    cancel = threading.Event()
    cancel.set()

    def fake_pipeline(source_id, **kwargs):
        captured.append(source_id)
        return {"success": True, "state": "corpus_available",
                "failed_stage": None, "exit_code": 0}

    def fake_state_for(source_id):
        return {"state": "corpus_available"}

    with mock.patch.object(processing_tab.pm, "pipeline",
                           side_effect=fake_pipeline), \
         mock.patch.object(processing_tab.pm, "state_for",
                           side_effect=fake_state_for), \
         mock.patch.object(processing_tab, "_ensure_registered",
                           return_value=None):
        results = processing_tab.process_sources(
            packages, cancel_event=cancel)
    check("no package started", captured == [])
    check("no results", len(results) == 0)


@test("process_sources reports progress per package in order")
def _():
    progress = []
    packages = [
        {"source_id": "a", "collection_id": "teppei_beginner", "episode": 1},
        {"source_id": "b", "source_name": "nhk_weather"},
    ]

    def fake_pipeline(source_id, **kwargs):
        return {"success": True, "state": "corpus_available",
                "failed_stage": None, "exit_code": 0}

    def fake_state_for(source_id):
        return {"state": "corpus_available"}

    def record(index, total, label):
        progress.append((index, total, label))

    with mock.patch.object(processing_tab.pm, "pipeline",
                           side_effect=fake_pipeline), \
         mock.patch.object(processing_tab.pm, "state_for",
                           side_effect=fake_state_for), \
         mock.patch.object(processing_tab, "_ensure_registered",
                           return_value=None):
        processing_tab.process_sources(
            packages, on_progress=record)
    check("two progress calls", len(progress) == 2)
    check("first index", progress[0][0] == 1)
    check("second index", progress[1][0] == 2)
    check("total constant", progress[0][1] == 2 and progress[1][1] == 2)
    check("first label",
          progress[0][2] == processing_tab.human_label(packages[0]))
    check("second label",
          progress[1][2] == processing_tab.human_label(packages[1]))


@test("failed_sources returns only failed packages")
def _():
    state_map = {
        "ok": {"state": "corpus_available"},
        "bad": {"state": "failed", "failed_stage": "api"},
    }
    packages = [
        {"source_id": "ok"},
        {"source_id": "bad"},
    ]
    with mock.patch.object(processing_tab.pm, "state_for",
                           side_effect=lambda sid: state_map[sid]):
        failed = processing_tab.failed_sources(packages)
    check("one failed", len(failed) == 1)
    check("correct source", failed[0]["source_id"] == "bad")


@test("build_dump includes identity, report, artifacts, environment")
def _():
    root = pathlib.Path(tempfile.mkdtemp())
    sources_root = root / "Sources"
    config_dir = root / "Config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "collections.json").write_text(json.dumps({
        "collections": [
            {"collection_id": "teppei_beginner", "name": COLLECTION_NAME,
             "source_type": "clean_text"},
        ]
    }), encoding="utf-8")
    (config_dir / "source_types.json").write_text(json.dumps(
        {"source_types": ["clean_text"]}), encoding="utf-8")
    (config_dir / "creators.json").write_text(json.dumps(
        {"creators": ["con_teppei_podcast", "nhk_news"]}), encoding="utf-8")

    saved = patch_root(sources_root, config_dir)
    try:
        result, _ = make_sources(sources_root)
        source_id = controller.source_id_for(
            "clean_text", collection_id="teppei_beginner", episode=58)
        package = json.loads(
            source_package.package_path_for(result["path"]).read_text(
                encoding="utf-8"))
        with mock.patch.object(diagnostics.pm, "report",
                               return_value={"state": "unregistered"}):
            dump = diagnostics.build_dump([source_id], [package])
        check("created_at present", "created_at" in dump)
        check("environment present", "environment" in dump)
        check("sources list", len(dump["sources"]) == 1)
        source_bundle = dump["sources"][0]
        check("source_id", source_bundle["source_id"] == source_id)
        check("report present", "report" in source_bundle)
        check("artifacts dict", isinstance(source_bundle.get("artifacts"), dict))
        check("logs dict", isinstance(source_bundle.get("logs"), dict))
        check("identity has collection_id",
              source_bundle["identity"].get("collection_id") == "teppei_beginner")
    finally:
        restore(saved)


@test("write_dump produces a gzipped bundle")
def _():
    import gzip
    dump = {"created_at": "now", "sources": [{"source_id": "x"}]}
    with mock.patch.object(diagnostics, "DIAGNOSTICS_DIR",
                           pathlib.Path(tempfile.mkdtemp())):
        target = diagnostics.write_dump(dump, label="test_sources")
        check("file exists", target.is_file())
        check("gzip suffix", target.suffixes == [".json", ".gz"])
        with gzip.open(target, "rt", encoding="utf-8") as file:
            data = json.loads(file.read())
        check("round trip", data["sources"][0]["source_id"] == "x")


@test("run_analysis writes a frequency report from the corpus")
def _():
    root = pathlib.Path(tempfile.mkdtemp())
    sources_root = root / "Sources"
    config_dir = root / "Config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "collections.json").write_text(json.dumps({
        "collections": [
            {"collection_id": "teppei_beginner", "name": COLLECTION_NAME,
             "source_type": "clean_text"},
        ]
    }), encoding="utf-8")
    (config_dir / "source_types.json").write_text(json.dumps(
        {"source_types": ["clean_text"]}), encoding="utf-8")
    (config_dir / "creators.json").write_text(json.dumps(
        {"creators": ["con_teppei_podcast", "nhk_news"]}), encoding="utf-8")

    saved = patch_root(sources_root, config_dir)
    try:
        result, _ = make_sources(sources_root)
        source_id = controller.source_id_for(
            "clean_text", collection_id="teppei_beginner", episode=58)
        package = json.loads(
            source_package.package_path_for(result["path"]).read_text(
                encoding="utf-8"))
        # Create a fake corpus JSONL and point jsonl_path at it.
        jsonl = pathlib.Path(tempfile.mkdtemp()) / f"{source_id}.jsonl"
        record = {"text": "こんにちは。", "words": [[0, "こんにちは", "こんにちは", 0, 5]],
                  "chunks": [], "expressions": [], "sentence_index": 0,
                  "ids": {}, "section": {}, "provenance": {}}
        jsonl.write_text(json.dumps(record, ensure_ascii=False) + "\n",
                         encoding="utf-8")
        out_dir = pathlib.Path(tempfile.mkdtemp())
        with mock.patch.object(processing_tab.pm, "jsonl_path",
                               return_value=jsonl):
            analysis = processing_tab.run_analysis(package, output_dir=out_dir)
        check("output path set", analysis["output_path"].endswith(
            f"{source_id}.frequency.json"))
        check("report file exists",
              pathlib.Path(analysis["output_path"]).is_file())
        report = json.loads(pathlib.Path(analysis["output_path"]).read_text(
            encoding="utf-8"))
        check("summary present", "summary" in report)
        check("records processed",
              report.get("summary", {}).get("records_processed") == 1)
    finally:
        restore(saved)


@test("run_analysis raises cleanly without a corpus")
def _():
    package = {"source_id": "no_corpus"}
    jsonl = pathlib.Path(tempfile.mkdtemp()) / "no_corpus.jsonl"
    with mock.patch.object(processing_tab.pm, "jsonl_path",
                           return_value=jsonl):
        try:
            processing_tab.run_analysis(package)
            check("missing corpus rejected", False)
        except processing_tab.ProcessingTabError as exc:
            check("friendly message", "No corpus available" in str(exc))


@test("completed_corpora lists only packages with a corpus JSONL")
def _():
    root = pathlib.Path(tempfile.mkdtemp())
    sources_root = root / "Sources"
    config_dir = root / "Config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "collections.json").write_text(json.dumps({
        "collections": [
            {"collection_id": "teppei_beginner", "name": COLLECTION_NAME,
             "source_type": "clean_text"},
        ]
    }), encoding="utf-8")
    (config_dir / "source_types.json").write_text(json.dumps(
        {"source_types": ["clean_text"]}), encoding="utf-8")
    (config_dir / "creators.json").write_text(json.dumps(
        {"creators": ["con_teppei_podcast", "nhk_news"]}), encoding="utf-8")

    saved = patch_root(sources_root, config_dir)
    try:
        make_sources(sources_root)
        # Simulate a corpus for the collection package only.
        ep58 = controller.source_id_for(
            "clean_text", collection_id="teppei_beginner", episode=58)
        jsonl = pathlib.Path(tempfile.mkdtemp()) / f"{ep58}.jsonl"
        jsonl.write_text("", encoding="utf-8")
        with mock.patch.object(processing_tab.pm, "jsonl_path",
                               side_effect=lambda sid: jsonl
                               if sid == ep58 else pathlib.Path(
                                   tempfile.mkdtemp()) / f"{sid}.jsonl"):
            completed = processing_tab.completed_corpora(sources_root)
        check("one completed", len(completed) == 1)
        check("correct source", completed[0]["source_id"] == ep58)
        check("human label",
              processing_tab.human_label(completed[0])
              == f"{COLLECTION_NAME} — ID#58")
    finally:
        restore(saved)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    passed = 0
    failed = 0
    failures = []
    for name, fn in TESTS:
        try:
            fn()
            passed += 1
            print(f"  PASS  {name}")
        except AssertionError as ex:
            failed += 1
            failures.append((name, str(ex)))
            print(f"  FAIL  {name}: {ex}")
        except Exception as ex:
            failed += 1
            failures.append((name, f"{type(ex).__name__}: {ex}"))
            print(f"  FAIL  {name}: {type(ex).__name__}: {ex}")

    print()
    print(f"Tests: {len(TESTS)}  Passed: {passed}  Failed: {failed}")
    if failures:
        print("Failures:")
        for name, detail in failures:
            print(f"  - {name}: {detail}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
