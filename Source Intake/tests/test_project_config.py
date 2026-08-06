#!/usr/bin/env python3
"""
test_project_config.py

Deterministic tests for the Source Intake configuration additions in
project_config.py.

Run:
    python "Source Intake/tests/test_project_config.py"
"""

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import project_config as pc


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


def raises_value_error(fn):
    try:
        fn()
        return False
    except ValueError:
        return True


@test("source types constant")
def _():
    check("is a frozenset", isinstance(pc.SOURCE_TYPES, frozenset))
    check("contains clean_text", "clean_text" in pc.SOURCE_TYPES)


@test("cleaning profiles constant")
def _():
    check("is a frozenset", isinstance(pc.CLEANING_PROFILES, frozenset))
    check("contains transcript_standard_v1", "transcript_standard_v1" in pc.CLEANING_PROFILES)


@test("processing profiles mapping")
def _():
    check("clean_text maps", pc.PROCESSING_PROFILES["clean_text"] == {
        "cleaning_profile": "transcript_standard_v1",
        "cleaner": "clean_transcript",
    })
    check("every profile in PROCESSING_PROFILES is a known profile",
          all(p["cleaning_profile"] in pc.CLEANING_PROFILES
              for p in pc.PROCESSING_PROFILES.values()))


@test("cleaner versions")
def _():
    check("transcript version", pc.CLEANER_VERSIONS["transcript_standard_v1"] == "1.0")


@test("raw directory mapping")
def _():
    check("clean_text raw dir", pc.SOURCE_TYPE_RAW_DIR["clean_text"] == "Raw Transcripts")


@test("cleaned artifact extension and default language")
def _():
    check("extension", pc.CLEANED_ARTIFACT_EXTENSION == ".clean.txt")
    check("default language", pc.DEFAULT_LANGUAGE == "ja")


@test("real configuration validates")
def _():
    check("validates True", pc.validate_source_intake_config() is True)


@test("deterministic validation")
def _():
    check("validates repeatedly",
          pc.validate_source_intake_config() is True
          and pc.validate_source_intake_config() is True)


@test("unknown source type rejected")
def _():
    raised = raises_value_error(lambda: pc.validate_source_intake_config(
        source_types=frozenset({"clean_text"}),
        cleaning_profiles=frozenset({"transcript_standard_v1"}),
        processing_profiles={
            "mystery": {"cleaning_profile": "transcript_standard_v1", "cleaner": "c"},
        },
        cleaner_versions={"transcript_standard_v1": "1.0"},
        source_type_raw_dir={"clean_text": "Raw Transcripts"},
    ))
    check("raises ValueError", raised)


@test("unknown cleaning profile rejected")
def _():
    raised = raises_value_error(lambda: pc.validate_source_intake_config(
        source_types=frozenset({"clean_text"}),
        cleaning_profiles=frozenset({"transcript_standard_v1"}),
        processing_profiles={
            "clean_text": {"cleaning_profile": "bogus_profile", "cleaner": "c"},
        },
        cleaner_versions={"transcript_standard_v1": "1.0"},
        source_type_raw_dir={"clean_text": "Raw Transcripts"},
    ))
    check("raises ValueError", raised)


@test("profile without a version rejected")
def _():
    raised = raises_value_error(lambda: pc.validate_source_intake_config(
        source_types=frozenset({"clean_text"}),
        cleaning_profiles=frozenset({"transcript_standard_v1"}),
        processing_profiles={
            "clean_text": {"cleaning_profile": "transcript_standard_v1", "cleaner": "c"},
        },
        cleaner_versions={},
        source_type_raw_dir={"clean_text": "Raw Transcripts"},
    ))
    check("raises ValueError", raised)


@test("source type without a raw directory rejected")
def _():
    raised = raises_value_error(lambda: pc.validate_source_intake_config(
        source_types=frozenset({"clean_text"}),
        cleaning_profiles=frozenset({"transcript_standard_v1"}),
        processing_profiles={
            "clean_text": {"cleaning_profile": "transcript_standard_v1", "cleaner": "c"},
        },
        cleaner_versions={"transcript_standard_v1": "1.0"},
        source_type_raw_dir={},
    ))
    check("raises ValueError", raised)


@test("cleaning profile without a version in the set rejected")
def _():
    raised = raises_value_error(lambda: pc.validate_source_intake_config(
        source_types=frozenset({"clean_text"}),
        cleaning_profiles=frozenset({"transcript_standard_v1", "new_profile"}),
        processing_profiles={
            "clean_text": {"cleaning_profile": "transcript_standard_v1", "cleaner": "c"},
        },
        cleaner_versions={"transcript_standard_v1": "1.0"},
        source_type_raw_dir={"clean_text": "Raw Transcripts"},
    ))
    check("raises ValueError", raised)


@test("valid alternate configuration passes")
def _():
    check("manga config validates", pc.validate_source_intake_config(
        source_types=frozenset({"manga"}),
        cleaning_profiles=frozenset({"manga_ocr_v1"}),
        processing_profiles={
            "manga": {"cleaning_profile": "manga_ocr_v1", "cleaner": "clean_manga"},
        },
        cleaner_versions={"manga_ocr_v1": "1.0"},
        source_type_raw_dir={"manga": "Raw Manga"},
    ) is True)


@test("cleaning transforms exist for every profile")
def _():
    for profile in pc.CLEANING_PROFILES:
        check(f"table for {profile}", profile in pc.CLEANING_TRANSFORMS)


@test("transcript_standard_v1 transformation flags")
def _():
    transforms = pc.CLEANING_TRANSFORMS["transcript_standard_v1"]
    check("strip_bom", transforms["strip_bom"] is True)
    check("trim_lines", transforms["trim_lines"] is True)
    check("remove_subtitle_numbers",
          transforms["remove_subtitle_numbers"] is False)
    check("remove_timecodes", transforms["remove_timecodes"] is False)
    check("collapse_blank_lines",
          transforms["collapse_blank_lines"] is True)
    check("collapse_repeated_spaces",
          transforms["collapse_repeated_spaces"] is True)


@test("real cleaning transform configuration validates")
def _():
    check("validates True", pc.validate_cleaning_transforms() is True)


@test("deterministic cleaning transform validation")
def _():
    check("validates repeatedly",
          pc.validate_cleaning_transforms() is True
          and pc.validate_cleaning_transforms() is True)


@test("cleaning transform table with non-bool value rejected")
def _():
    raised = raises_value_error(lambda: pc.validate_cleaning_transforms(
        cleaning_profiles=frozenset({"transcript_standard_v1"}),
        cleaning_transforms={
            "transcript_standard_v1": {"strip_bom": "yes"},
        },
    ))
    check("raises ValueError", raised)


@test("cleaning transform table for unknown profile rejected")
def _():
    raised = raises_value_error(lambda: pc.validate_cleaning_transforms(
        cleaning_profiles=frozenset({"transcript_standard_v1"}),
        cleaning_transforms={
            "transcript_standard_v1": {"strip_bom": True},
            "mystery_profile": {"strip_bom": True},
        },
    ))
    check("raises ValueError", raised)


@test("cleaning transform missing table for profile rejected")
def _():
    raised = raises_value_error(lambda: pc.validate_cleaning_transforms(
        cleaning_profiles=frozenset({"transcript_standard_v1"}),
        cleaning_transforms={},
    ))
    check("raises ValueError", raised)


@test("valid alternate cleaning transform configuration passes")
def _():
    check("alternate validates", pc.validate_cleaning_transforms(
        cleaning_profiles=frozenset({"manga_ocr_v1"}),
        cleaning_transforms={
            "manga_ocr_v1": {"strip_bom": True, "trim_lines": False},
        },
    ) is True)


@test("expression extraction capability per model")
def _():
    check("flash disabled",
          pc.expressions_enabled("deepseek-v4-flash") is False)
    check("unknown model enabled by default",
          pc.expressions_enabled("deepseek-reasoner") is True)
    check("no-arg uses MODEL_NAME",
          pc.expressions_enabled() ==
          pc.MODEL_EXPRESSIONS_ENABLED.get(pc.MODEL_NAME, True))
    check("mapping is a dict", isinstance(pc.MODEL_EXPRESSIONS_ENABLED, dict))


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
