#!/usr/bin/env python3
"""
test_source_builder_gui_visuals.py

Deterministic tests for the Source Builder GUI's pure visual mapping:

- Ready State -> button visuals (style + enabled flags),
- Ready State -> button state transitions,
- Workflow Panel block layout (message primary, filename/save location
  secondary, in display order).

These tests exercise the pure helpers in gui.py and the ReadyStateEngine
(controller). They do not open a window.

Run:
    python "Source Builder/tests/test_source_builder_gui_visuals.py"
"""

import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE_BUILDER = PROJECT_ROOT / "Source Builder"
sys.path.insert(0, str(SOURCE_BUILDER))

import controller
import gui


def sandbox():
    """Patch controller.SOURCES_ROOT to a temp dir; return restore fn."""
    saved = controller.SOURCES_ROOT
    controller.SOURCES_ROOT = pathlib.Path(tempfile.mkdtemp()) / "Sources"
    return lambda: setattr(controller, "SOURCES_ROOT", saved)


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
        "creator": "con_teppei_podcast",
        "source_text": "これはテストです。\n",
        "material_level": 2,
    }
    base.update(overrides)
    return engine.evaluate(**base)


def ev_incomplete(engine):
    """Evaluate with an empty (INCOMPLETE) collection form."""
    return ev(engine, collection_id="", episode="", source_type="", creator="",
              source_text="")


# ============================================================
# Ready State -> button visuals mapping
# ============================================================

@test("visuals: INCOMPLETE disables both buttons (grey)")
def _():
    v = gui.ready_state_visuals("INCOMPLETE")
    check("save bg grey", v["save_bg"] == gui.COLOR_GREY)
    check("next bg grey", v["next_bg"] == gui.COLOR_GREY)
    check("save disabled", v["save_enabled"] is False)
    check("next disabled", v["next_enabled"] is False)


@test("visuals: ERROR disables both buttons (grey)")
def _():
    v = gui.ready_state_visuals("ERROR")
    check("save bg grey", v["save_bg"] == gui.COLOR_GREY)
    check("next bg grey", v["next_bg"] == gui.COLOR_GREY)
    check("save disabled", v["save_enabled"] is False)
    check("next disabled", v["next_enabled"] is False)


@test("visuals: READY enables Save green, Next grey")
def _():
    v = gui.ready_state_visuals("READY")
    check("save bg green", v["save_bg"] == gui.COLOR_GREEN)
    check("next bg grey", v["next_bg"] == gui.COLOR_GREY)
    check("save enabled", v["save_enabled"] is True)
    check("next disabled", v["next_enabled"] is False)


@test("visuals: SAVED enables Next green, Save blue")
def _():
    v = gui.ready_state_visuals("SAVED")
    check("save bg blue", v["save_bg"] == gui.COLOR_BLUE)
    check("next bg green", v["next_bg"] == gui.COLOR_GREEN)
    check("save disabled", v["save_enabled"] is False)
    check("next enabled", v["next_enabled"] is True)


@test("visuals: Save enabled only in READY across full transition")
def _():
    restore = sandbox()
    try:
        engine = controller.ReadyStateEngine()
        save_enabled_by_state = {}

        def snapshot(result):
            save_enabled_by_state[result["state"]] = result["save_enabled"]

        snapshot(ev_incomplete(engine))  # INCOMPLETE (empty)
        snapshot(ev(engine))  # READY

        engine.mark_saved({
            "identity_type": "collection",
            "collection_id": "teppei_beginner",
            "source_name": "",
            "episode": "1",
            "source_type": "clean_text",
            "creator": "con_teppei_podcast",
            "source_text": "これはテストです。\n",
            "material_level": 2,
            "filename": "teppei_beginner_ep0001.txt",
        })
        snapshot(ev(engine))  # SAVED

        check("save off in INCOMPLETE",
              save_enabled_by_state["INCOMPLETE"] is False)
        check("save on in READY", save_enabled_by_state["READY"] is True)
        check("save off in SAVED", save_enabled_by_state["SAVED"] is False)
    finally:
        restore()


@test("visuals: Next enabled only in SAVED across full transition")
def _():
    restore = sandbox()
    try:
        engine = controller.ReadyStateEngine()
        next_enabled_by_state = {}

        def snapshot(result):
            next_enabled_by_state[result["state"]] = result["next_enabled"]

        snapshot(ev_incomplete(engine))  # INCOMPLETE
        snapshot(ev(engine))  # READY

        engine.mark_saved({
            "identity_type": "collection",
            "collection_id": "teppei_beginner",
            "source_name": "",
            "episode": "1",
            "source_type": "clean_text",
            "creator": "con_teppei_podcast",
            "source_text": "これはテストです。\n",
            "material_level": 2,
            "filename": "teppei_beginner_ep0001.txt",
        })
        snapshot(ev(engine))  # SAVED

        check("next off in INCOMPLETE",
              next_enabled_by_state["INCOMPLETE"] is False)
        check("next off in READY", next_enabled_by_state["READY"] is False)
        check("next on in SAVED", next_enabled_by_state["SAVED"] is True)
    finally:
        restore()


@test("visual mapping agrees with engine for all four states")
def _():
    restore = sandbox()
    try:
        engine = controller.ReadyStateEngine()
        states_seen = set()

        states_seen.add(ev_incomplete(engine)["state"])  # INCOMPLETE
        states_seen.add(ev(engine)["state"])  # READY
        engine.mark_saved({
            "identity_type": "collection",
            "collection_id": "teppei_beginner",
            "source_name": "",
            "episode": "1",
            "source_type": "clean_text",
            "creator": "con_teppei_podcast",
            "source_text": "これはテストです。\n",
            "material_level": 2,
            "filename": "teppei_beginner_ep0001.txt",
        })
        states_seen.add(ev(engine)["state"])  # SAVED
        engine.set_error("boom")
        states_seen.add(ev(engine)["state"])  # ERROR

        check("all four states reached",
              states_seen == {"INCOMPLETE", "READY", "SAVED", "ERROR"})
        for state in states_seen:
            v = gui.ready_state_visuals(state)
            # Every state must map to a defined style for both buttons.
            check(f"{state} save bg defined", bool(v["save_bg"]))
            check(f"{state} next bg defined", bool(v["next_bg"]))
    finally:
        restore()


# ============================================================
# Workflow Panel layout expectations
# ============================================================

@test("workflow panel: message is the primary block")
def _():
    blocks = gui.workflow_panel_blocks("Waiting for source text.",
                                       "teppei_beginner_ep0001.txt",
                                       r"C:\j\teppei_beginner_ep0001.txt")
    check("first block is message", blocks[0]["kind"] == "message")
    check("message text", blocks[0]["text"] == "Waiting for source text.")


@test("workflow panel: order is message, Filename, Save Location")
def _():
    blocks = gui.workflow_panel_blocks("Ready to Save.",
                                       "teppei_beginner_ep0051.txt",
                                       r"C:\j\Sources\collections\teppei_beginner")
    check("block count", len(blocks) == 5)
    check("block kinds",
          [b["kind"] for b in blocks]
          == ["message", "caption", "value", "caption", "value"])
    check("caption 1", blocks[1]["text"] == "Filename")
    check("value 1", blocks[2]["text"] == "teppei_beginner_ep0051.txt")
    check("caption 2", blocks[3]["text"] == "Save Location")
    check("value 2",
          blocks[4]["text"] == r"C:\j\Sources\collections\teppei_beginner")


@test("workflow panel: missing filename/save location shown as placeholder")
def _():
    blocks = gui.workflow_panel_blocks("Waiting for collection.", None, None)
    check("filename placeholder", blocks[2]["text"] == "—")
    check("save location placeholder", blocks[4]["text"] == "—")


@test("workflow panel: empty-string values also fall back to placeholder")
def _():
    blocks = gui.workflow_panel_blocks("Waiting for source name.", "", "")
    check("filename placeholder", blocks[2]["text"] == "—")
    check("save location placeholder", blocks[4]["text"] == "—")


# ============================================================
# Child window positioning (centered over parent)
# ============================================================

@test("centered_position: centres child over parent")
def _():
    # Parent at 100,100, size 800x600; child 400x300.
    x, y = gui.centered_position(100, 100, 800, 600, 400, 300)
    check("x centred", x == 100 + (800 - 400) // 2)
    check("y centred", y == 100 + (600 - 300) // 2)


@test("centered_position: larger child stays aligned at parent centre")
def _():
    # Child larger than parent still aligns centres (offset may be negative).
    x, y = gui.centered_position(0, 0, 200, 200, 300, 100)
    check("x negative ok", x == (200 - 300) // 2)
    check("y negative ok", y == (200 - 100) // 2)


@test("centered_position: follows parent position on the virtual desktop")
def _():
    # A parent on a secondary monitor has a non-zero (possibly negative) x.
    x, y = gui.centered_position(-960, 0, 800, 600, 400, 300)
    check("x keeps monitor offset", x == -960 + (800 - 400) // 2)
    check("y centred", y == 0 + (600 - 300) // 2)


# ============================================================
# Button state transitions (engine-level enable logic)
# ============================================================

@test("transition: INCOMPLETE -> READY -> SAVED -> INCOMPLETE")
def _():
    restore = sandbox()
    try:
        engine = controller.ReadyStateEngine()
        check("1 incomplete", ev_incomplete(engine)["state"] == "INCOMPLETE")

        ready = ev(engine)
        check("2 ready", ready["state"] == "READY")
        check("save enabled", ready["save_enabled"] is True)
        check("next disabled", ready["next_enabled"] is False)

        engine.mark_saved({
            "identity_type": "collection",
            "collection_id": "teppei_beginner",
            "source_name": "",
            "episode": "1",
            "source_type": "clean_text",
            "creator": "con_teppei_podcast",
            "source_text": "これはテストです。\n",
            "material_level": 2,
            "filename": "teppei_beginner_ep0001.txt",
        })
        saved = ev(engine)
        check("3 saved", saved["state"] == "SAVED")
        check("save disabled", saved["save_enabled"] is False)
        check("next enabled", saved["next_enabled"] is True)

        engine.reset()
        after = ev(engine, source_text="")
        check("4 incomplete", after["state"] == "INCOMPLETE")
        check("save disabled", after["save_enabled"] is False)
        check("next disabled", after["next_enabled"] is False)
    finally:
        restore()


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
