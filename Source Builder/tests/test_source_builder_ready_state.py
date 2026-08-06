#!/usr/bin/env python3
"""
test_source_builder_ready_state.py

Deterministic tests for the Source Builder Ready State Engine and
Open Folder path resolution.

Ready State is owned by the controller; the GUI only applies it. Tests run
against a sandboxed Sources/ directory.

Run:
    python "Source Builder/tests/test_source_builder_ready_state.py"
"""

import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))

import controller


def setup():
    """Patch controller.SOURCES_ROOT to a temp dir."""
    root = pathlib.Path(tempfile.mkdtemp())
    sources = root / "Sources"
    saved = controller.SOURCES_ROOT
    controller.SOURCES_ROOT = sources
    return root, sources, saved


def restore(saved):
    controller.SOURCES_ROOT = saved


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


def ev(engine, **overrides):
    """Evaluate the engine with collection-mode defaults."""
    base = {
        "identity_type": "collection",
        "collection_id": "teppei_beginner",
        "source_name": "",
        "episode": "1",
        "source_type": "clean_text",
        "origin": "con_teppei_podcast",
        "source_text": "これはテストです。\n",
    }
    base.update(overrides)
    return engine.evaluate(**base)


# ============================================================
# State determination
# ============================================================

@test("empty form is INCOMPLETE")
def _():
    result = ev(controller.ReadyStateEngine(), collection_id="", episode="",
                source_type="", origin="", source_text="")
    check("state", result["state"] == "INCOMPLETE")
    check("save disabled", result["save_enabled"] is False)
    check("next disabled", result["next_enabled"] is False)


@test("complete collection form is READY")
def _():
    root, sources, saved = setup()
    try:
        result = ev(controller.ReadyStateEngine())
        check("state", result["state"] == "READY")
        check("message", result["message"] == "Ready to Save.")
        check("save enabled", result["save_enabled"] is True)
        check("next disabled", result["next_enabled"] is False)
        check("no saved filename", result["saved_filename"] is None)
    finally:
        restore(saved)


@test("complete standalone form is READY")
def _():
    root, sources, saved = setup()
    try:
        result = ev(controller.ReadyStateEngine(), identity_type="standalone",
                    source_name="nhk_weather", collection_id="", episode="")
        check("state", result["state"] == "READY")
        check("save enabled", result["save_enabled"] is True)
    finally:
        restore(saved)


# ============================================================
# Blocking reasons (first blocking reason wins)
# ============================================================

@test("blocking: missing collection")
def _():
    result = ev(controller.ReadyStateEngine(), collection_id="")
    check("state", result["state"] == "INCOMPLETE")
    check("message", result["message"] == "Waiting for collection.")


@test("blocking: missing episode")
def _():
    result = ev(controller.ReadyStateEngine(), episode="")
    check("state", result["state"] == "INCOMPLETE")
    check("message", result["message"] == "Waiting for episode number.")


@test("blocking: invalid episode")
def _():
    result = ev(controller.ReadyStateEngine(), episode="abc")
    check("state", result["state"] == "INCOMPLETE")
    check("message", result["message"] == "Episode number must be an integer.")


@test("blocking: negative episode")
def _():
    result = ev(controller.ReadyStateEngine(), episode="-3")
    check("state", result["state"] == "INCOMPLETE")
    check("message", result["message"] == "Episode number must be non-negative.")


@test("blocking: missing source name (standalone)")
def _():
    result = ev(controller.ReadyStateEngine(), identity_type="standalone",
                source_name="", collection_id="", episode="")
    check("state", result["state"] == "INCOMPLETE")
    check("message", result["message"] == "Waiting for source name.")


@test("blocking: missing source type")
def _():
    result = ev(controller.ReadyStateEngine(), source_type="")
    check("message", result["message"] == "Waiting for source type.")


@test("blocking: missing origin")
def _():
    result = ev(controller.ReadyStateEngine(), origin="")
    check("message", result["message"] == "Waiting for origin.")


@test("empty source text")
def _():
    result = ev(controller.ReadyStateEngine(), source_text="   \n")
    check("message", result["message"] == "Waiting for source text.")


@test("blocking: filename already exists (collection)")
def _():
    root, sources, saved = setup()
    try:
        controller.create_collection_source(
            "teppei_beginner", 1, "clean_text",
            "con_teppei_podcast", "ja", "existing\n")
        result = ev(controller.ReadyStateEngine(), episode="1")
        check("state", result["state"] == "INCOMPLETE")
        check("message", result["message"] == "Filename already exists.")
        check("save disabled", result["save_enabled"] is False)
    finally:
        restore(saved)


@test("blocking: filename already exists (standalone)")
def _():
    root, sources, saved = setup()
    try:
        controller.create_standalone_source(
            "nhk_weather", "article", "nhk_news", "ja", "existing\n")
        result = ev(controller.ReadyStateEngine(), identity_type="standalone",
                    source_name="nhk_weather", collection_id="", episode="")
        check("state", result["state"] == "INCOMPLETE")
        check("message", result["message"] == "Filename already exists.")
    finally:
        restore(saved)


@test("blocking order: empty text reported after metadata present")
def _():
    result = ev(controller.ReadyStateEngine(), source_text="")
    check("message", result["message"] == "Waiting for source text.")


# ============================================================
# Transitions: INCOMPLETE -> READY -> SAVED -> INCOMPLETE
# ============================================================

@test("transition: INCOMPLETE to READY")
def _():
    root, sources, saved = setup()
    try:
        engine = controller.ReadyStateEngine()
        incomplete = ev(engine, episode="", source_text="")
        check("initial incomplete", incomplete["state"] == "INCOMPLETE")
        ready = ev(engine, episode="2", source_text="text\n")
        check("now ready", ready["state"] == "READY")
        check("save enabled", ready["save_enabled"] is True)
    finally:
        restore(saved)


@test("transition: READY to SAVED after mark_saved")
def _():
    root, sources, saved = setup()
    try:
        engine = controller.ReadyStateEngine()
        check("ready first", ev(engine)["state"] == "READY")
        engine.mark_saved({
            "identity_type": "collection",
            "collection_id": "teppei_beginner",
            "source_name": "",
            "episode": "1",
            "source_type": "clean_text",
            "origin": "con_teppei_podcast",
            "source_text": "これはテストです。\n",
            "filename": "teppei_beginner_ep0001.txt",
        })
        saved_state = ev(engine)
        check("state saved", saved_state["state"] == "SAVED")
        check("save disabled", saved_state["save_enabled"] is False)
        check("next enabled", saved_state["next_enabled"] is True)
        check("filename present",
              saved_state["saved_filename"] == "teppei_beginner_ep0001.txt")
        check("message clean", saved_state["message"] == "Saved successfully.")
    finally:
        restore(saved)


@test("transition: SAVED back to READY on valid field edit")
def _():
    root, sources, saved = setup()
    try:
        engine = controller.ReadyStateEngine()
        engine.mark_saved({
            "identity_type": "collection",
            "collection_id": "teppei_beginner",
            "source_name": "",
            "episode": "1",
            "source_type": "clean_text",
            "origin": "con_teppei_podcast",
            "source_text": "これはテストです。\n",
            "filename": "teppei_beginner_ep0001.txt",
        })
        # Changing the episode breaks the saved snapshot.
        edited = ev(engine, episode="2")
        check("edited leaves SAVED", edited["state"] != "SAVED")
        check("edited is READY", edited["state"] == "READY")
        check("next disabled", edited["next_enabled"] is False)
    finally:
        restore(saved)


@test("transition: SAVED back to INCOMPLETE on invalid edit")
def _():
    root, sources, saved = setup()
    try:
        engine = controller.ReadyStateEngine()
        engine.mark_saved({
            "identity_type": "collection",
            "collection_id": "teppei_beginner",
            "source_name": "",
            "episode": "1",
            "source_type": "clean_text",
            "origin": "con_teppei_podcast",
            "source_text": "これはテストです。\n",
            "filename": "teppei_beginner_ep0001.txt",
        })
        edited = ev(engine, source_text="")
        check("edited is INCOMPLETE", edited["state"] == "INCOMPLETE")
        check("message", edited["message"] == "Waiting for source text.")
    finally:
        restore(saved)


@test("transition: SAVED to INCOMPLETE via reset (Create Next)")
def _():
    root, sources, saved = setup()
    try:
        engine = controller.ReadyStateEngine()
        engine.mark_saved({
            "identity_type": "collection",
            "collection_id": "teppei_beginner",
            "source_name": "",
            "episode": "5",
            "source_type": "clean_text",
            "origin": "con_teppei_podcast",
            "source_text": "これはテストです。\n",
            "filename": "teppei_beginner_ep0005.txt",
        })
        check("saved first", ev(engine, episode="5")["state"] == "SAVED")
        engine.reset()
        # In the real workflow Create Next also clears the source text, so the
        # form returns to INCOMPLETE.
        after = ev(engine, episode="5", source_text="")
        check("reset -> INCOMPLETE", after["state"] == "INCOMPLETE")
        check("save disabled", after["save_enabled"] is False)
        check("next disabled", after["next_enabled"] is False)
    finally:
        restore(saved)


# ============================================================
# ERROR state
# ============================================================

@test("ERROR disables both buttons and shows message")
def _():
    root, sources, saved = setup()
    try:
        engine = controller.ReadyStateEngine()
        engine.set_error("boom")
        result = ev(engine)
        check("state error", result["state"] == "ERROR")
        check("save disabled", result["save_enabled"] is False)
        check("next disabled", result["next_enabled"] is False)
        check("message", result["message"] == "boom")
    finally:
        restore(saved)


@test("ERROR cleared by reset")
def _():
    root, sources, saved = setup()
    try:
        engine = controller.ReadyStateEngine()
        engine.set_error("boom")
        engine.reset()
        check("recovered", ev(engine)["state"] == "READY")
    finally:
        restore(saved)


@test("ERROR cleared by mark_saved")
def _():
    root, sources, saved = setup()
    try:
        engine = controller.ReadyStateEngine()
        engine.set_error("boom")
        engine.mark_saved({
            "identity_type": "collection",
            "collection_id": "teppei_beginner",
            "source_name": "",
            "episode": "1",
            "source_type": "clean_text",
            "origin": "con_teppei_podcast",
            "source_text": "これはテストです。\n",
            "filename": "teppei_beginner_ep0001.txt",
        })
        check("saved after error", ev(engine)["state"] == "SAVED")
    finally:
        restore(saved)


# ============================================================
# Save / Create Next enable logic
# ============================================================

@test("Save enabled only in READY")
def _():
    root, sources, saved = setup()
    try:
        engine = controller.ReadyStateEngine()
        check("incomplete: save off", ev(engine, episode="")["save_enabled"] is False)
        check("ready: save on", ev(engine)["save_enabled"] is True)
        engine.mark_saved({
            "identity_type": "collection",
            "collection_id": "teppei_beginner",
            "source_name": "",
            "episode": "1",
            "source_type": "clean_text",
            "origin": "con_teppei_podcast",
            "source_text": "これはテストです。\n",
            "filename": "teppei_beginner_ep0001.txt",
        })
        check("saved: save off", ev(engine)["save_enabled"] is False)
        engine.set_error("x")
        check("error: save off", ev(engine)["save_enabled"] is False)
    finally:
        restore(saved)


@test("Create Next enabled only in SAVED")
def _():
    root, sources, saved = setup()
    try:
        engine = controller.ReadyStateEngine()
        check("incomplete: next off", ev(engine, episode="")["next_enabled"] is False)
        check("ready: next off", ev(engine)["next_enabled"] is False)
        engine.mark_saved({
            "identity_type": "collection",
            "collection_id": "teppei_beginner",
            "source_name": "",
            "episode": "1",
            "source_type": "clean_text",
            "origin": "con_teppei_podcast",
            "source_text": "これはテストです。\n",
            "filename": "teppei_beginner_ep0001.txt",
        })
        check("saved: next on", ev(engine)["next_enabled"] is True)
        engine.set_error("x")
        check("error: next off", ev(engine)["next_enabled"] is False)
    finally:
        restore(saved)


# ============================================================
# Open Folder path resolution
# ============================================================

@test("open folder path: collection")
def _():
    root, sources, saved = setup()
    try:
        folder = controller.collection_dir("teppei_beginner")
        check("path", folder == sources / "collections" / "teppei_beginner")
    finally:
        restore(saved)


@test("open folder path: standalone")
def _():
    root, sources, saved = setup()
    try:
        folder = controller.standalone_dir()
        check("path", folder == sources / "standalone")
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
