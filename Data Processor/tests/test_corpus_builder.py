#!/usr/bin/env python3
"""
test_corpus_builder.py

Deterministic tests for the single-source artifact-driven Corpus Builder.

Run:
    python "Data Processor/tests/test_corpus_builder.py"
"""

import importlib.util
import json
import pathlib
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_PROCESSOR = PROJECT_ROOT / "Data Processor"
sys.path.insert(0, str(DATA_PROCESSOR))

_spec = importlib.util.spec_from_file_location(
    "corpus_builder", str(DATA_PROCESSOR / "corpus_builder.py")
)
corpus_builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(corpus_builder)
cb = corpus_builder

import corpus_builder_result as cbr


SOURCE_ID = "pod_conteppei_ep051"
PROMPT_VERSION = "1.0"
MODEL = "deepseek-v4-flash"


def valid_request(source_id=SOURCE_ID, job_number=1, text="こんにちは。\n"):
    return {
        "source_id": source_id,
        "cleaned_artifact": f"Cleaned Archive/{source_id}.clean.txt",
        "job_number": job_number,
        "prompt_version": PROMPT_VERSION,
        "source_file": f"Cleaned Archive/{source_id}.clean.txt",
        "source_name": source_id,
        "messages": [
            {"role": "system", "content": "parser prompt"},
            {"role": "user", "content": text},
        ],
    }


def valid_parser(source_id=SOURCE_ID, job_number=1):
    return {
        "source_name": source_id,
        "job_number": job_number,
        "sentences": [
            {
                "sentence_index": 0,
                "text": "こんにちは。",
                "words": [[0, "こんにちは", "こんにちは", 0, 5],
                          [1, "。", "。", 5, 6]],
                "chunks": [[0, "こんにちは。", 0, 2]],
                "expressions": [],
            },
        ],
    }


def valid_response(source_id=SOURCE_ID, job_number=1):
    parser = valid_parser(source_id, job_number)
    return {
        "model": MODEL,
        "choices": [{"finish_reason": "stop",
                     "message": {"content": json.dumps(parser, ensure_ascii=False)}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        "job_number": job_number,
    }


def write_requests(requests_dir, source_id, requests):
    request_dir = requests_dir / source_id
    request_dir.mkdir(parents=True, exist_ok=True)
    for request in requests:
        path = request_dir / f"request_{request['job_number']:06d}.json"
        path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
    return request_dir


def write_responses(responses_dir, source_id, responses):
    response_dir = responses_dir / source_id
    response_dir.mkdir(parents=True, exist_ok=True)
    for response in responses:
        job_number = response["job_number"]
        path = response_dir / f"response_{job_number:06d}.json"
        path.write_text(json.dumps(response, ensure_ascii=False), encoding="utf-8")
    return response_dir


def setup():
    """Create isolated temp dirs and patch Corpus Builder globals."""
    root = pathlib.Path(tempfile.mkdtemp())
    requests_dir = root / "requests"
    responses_dir = root / "responses"
    jsonl_dir = root / "jsonl"
    corpus_dir = root / "Corpus Results"
    logs_dir = root / "logs"
    for folder in (requests_dir, responses_dir, jsonl_dir, corpus_dir, logs_dir):
        folder.mkdir(parents=True)

    saved = (
        cb.REQUESTS,
        cb.RESPONSES,
        cb.JSONL,
        cb.CORPUS_RESULTS,
        cb.LOG_CORPUS_BUILDER,
    )
    cb.REQUESTS = requests_dir
    cb.RESPONSES = responses_dir
    cb.JSONL = jsonl_dir
    cb.CORPUS_RESULTS = corpus_dir
    cb.LOG_CORPUS_BUILDER = logs_dir
    return root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved


def restore(saved):
    (cb.REQUESTS, cb.RESPONSES, cb.JSONL, cb.CORPUS_RESULTS,
     cb.LOG_CORPUS_BUILDER) = saved


def result_path(corpus_dir, source_id):
    return corpus_dir / f"{source_id}.corpus_builder_result.json"


def load_result(corpus_dir, source_id):
    return json.loads(
        result_path(corpus_dir, source_id).read_text(encoding="utf-8")
    )


TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed. {detail}")


@test("1. --source CLI invocation")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        write_requests(requests_dir, SOURCE_ID, [valid_request()])
        write_responses(responses_dir, SOURCE_ID, [valid_response()])
        code = cb.main(["--source", SOURCE_ID])
        check("exit 0", code == 0)
        check("jsonl created",
              (jsonl_dir / f"{SOURCE_ID}.jsonl").is_file())
        check("result created",
              result_path(corpus_dir, SOURCE_ID).is_file())
    finally:
        restore(saved)


@test("2. missing argument rejected")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        raised = False
        try:
            cb.main([])
        except SystemExit:
            raised = True
        check("argparse rejects missing --source", raised)
    finally:
        restore(saved)


@test("3. source_id lineage")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        write_requests(requests_dir, SOURCE_ID, [valid_request()])
        write_responses(responses_dir, SOURCE_ID, [valid_response()])
        code = cb.run(SOURCE_ID)
        check("exit 0", code == 0)
        check("jsonl named by source_id",
              (jsonl_dir / f"{SOURCE_ID}.jsonl").is_file())
    finally:
        restore(saved)


@test("3b. source_id mismatch rejected")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        bad = valid_request(source_id="pod_wrong_ep999")
        write_requests(requests_dir, SOURCE_ID, [bad])
        write_responses(responses_dir, SOURCE_ID,
                        [valid_response(source_id="pod_wrong_ep999")])
        code = cb.run(SOURCE_ID)
        check("exit non-zero", code != 0)
        check("no jsonl", not (jsonl_dir / f"{SOURCE_ID}.jsonl").exists())
        result = load_result(corpus_dir, SOURCE_ID)
        check("success false", result["success"] is False)
        check("failed jobs recorded", result["jobs_failed"] == 1)
    finally:
        restore(saved)


@test("4. request/response pairing")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        write_requests(requests_dir, SOURCE_ID, [valid_request()])
        write_responses(responses_dir, SOURCE_ID, [valid_response()])
        code = cb.run(SOURCE_ID)
        check("exit 0", code == 0)
        result = load_result(corpus_dir, SOURCE_ID)
        check("jobs_processed", result["jobs_processed"] == 1)
        check("jobs_failed", result["jobs_failed"] == 0)
        check("verified", result["verified"] is True)
    finally:
        restore(saved)


@test("5. valid corpus generation")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        write_requests(requests_dir, SOURCE_ID, [valid_request()])
        write_responses(responses_dir, SOURCE_ID, [valid_response()])
        code = cb.run(SOURCE_ID)
        check("exit 0", code == 0)

        jsonl_file = jsonl_dir / f"{SOURCE_ID}.jsonl"
        lines = jsonl_file.read_text(encoding="utf-8").splitlines()
        check("one record", len(lines) == 1)
        record = json.loads(lines[0])
        check("text preserved", record["text"] == "こんにちは。")
        check("sentence_id", record["ids"]["sentence_id"] == 0)
        check("section present", record["section"] == "default")
    finally:
        restore(saved)


@test("5b. E2E: canonicalizer -> validator -> corpus JSONL with punctuation-omitting surfaces")
def _():
    # Clean source sentence contains punctuation; parser word surfaces omit
    # it. The new flow canonicalize() -> validate_parser_output() -> build
    # must complete and write canonical JSONL.

    source_id = SOURCE_ID
    clean_text = "こんにちは。\n\nさようなら。\n"
    parser = {
        "source_name": source_id,
        "job_number": 1,
        "sentences": [
            {"sentence_index": 0, "text": "こんにちは。",
             "words": [[0, "こんにちは", "こんにちは", 0, 5]],
             "chunks": [[0, "こんにちは", 0, 1]], "expressions": []},
            {"sentence_index": 1, "text": "さようなら。",
             "words": [[0, "さようなら", "さようなら", 0, 5]],
             "chunks": [[0, "さようなら", 0, 1]], "expressions": []},
        ],
    }
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        # Request whose user message carries the job text (canonicalizer
        # derives sentence text from it).
        request = valid_request(source_id=source_id, job_number=1, text=clean_text)
        request["messages"][1]["content"] = (
            f"SOURCE METADATA:\nsource_id: {source_id}\n"
            f"job_number: 1\n\nTEXT:\n{clean_text}"
        )
        write_requests(requests_dir, source_id, [request])
        write_responses(responses_dir, source_id, [
            {"model": MODEL, "job_number": 1,
             "choices": [{"finish_reason": "stop",
                          "message": {"content": json.dumps(parser, ensure_ascii=False)}}],
             "usage": {"prompt_tokens": 10, "completion_tokens": 5,
                       "total_tokens": 15}},
        ])

        code = cb.run(source_id)
        check("exit 0", code == 0)

        jsonl_file = jsonl_dir / f"{source_id}.jsonl"
        lines = jsonl_file.read_text(encoding="utf-8").splitlines()
        check("two records", len(lines) == 2)
        record = json.loads(lines[0])
        check("text preserved", record["text"] == "こんにちは。")
        check("sentence_id", record["ids"]["sentence_id"] == 0)
        check("word span matches surface",
              record["text"][record["words"][0][3]:record["words"][0][4]]
              == record["words"][0][1])
    finally:
        restore(saved)


@test("6. provenance source_id")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        write_requests(requests_dir, SOURCE_ID, [valid_request()])
        write_responses(responses_dir, SOURCE_ID, [valid_response()])
        code = cb.run(SOURCE_ID)
        check("exit 0", code == 0)

        record = json.loads(
            (jsonl_dir / f"{SOURCE_ID}.jsonl")
            .read_text(encoding="utf-8").splitlines()[0]
        )
        p = record["provenance"]
        check("source_id", p["source_id"] == SOURCE_ID)
        check("source == source_id", p["source"] == SOURCE_ID)
        check("source_file", p["source_file"]
              == f"Cleaned Archive/{SOURCE_ID}.clean.txt")
        check("job_number", p["job_number"] == 1)
        check("model", p["model"] == MODEL)
        check("prompt_version", p["prompt_version"] == PROMPT_VERSION)
        check("sentence_id", p["sentence_id"] == 0)
        check("sentence_position", p["sentence_position"] == 0)
    finally:
        restore(saved)


@test("7. frozen record structure unchanged")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        write_requests(requests_dir, SOURCE_ID, [valid_request()])
        write_responses(responses_dir, SOURCE_ID, [valid_response()])
        code = cb.run(SOURCE_ID)
        check("exit 0", code == 0)

        record = json.loads(
            (jsonl_dir / f"{SOURCE_ID}.jsonl")
            .read_text(encoding="utf-8").splitlines()[0]
        )
        check("top-level keys",
              set(record) == {"text", "words", "chunks", "expressions",
                              "sentence_index", "ids", "section",
                              "provenance"})
        check("word 5-col",
              record["words"] == [[0, "こんにちは", "こんにちは", 0, 5],
                                  [1, "。", "。", 5, 6]])
        check("chunk 4-col", record["chunks"] == [[0, "こんにちは。", 0, 2]])
        check("expressions empty", record["expressions"] == [])
    finally:
        restore(saved)


@test("8. missing response handling")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        write_requests(requests_dir, SOURCE_ID, [valid_request()])
        # No response written.
        code = cb.run(SOURCE_ID)
        check("exit non-zero", code != 0)
        check("no jsonl", not (jsonl_dir / f"{SOURCE_ID}.jsonl").exists())
        result = load_result(corpus_dir, SOURCE_ID)
        check("success false", result["success"] is False)
        check("failed jobs", result["jobs_failed"] == 1)
    finally:
        restore(saved)


@test("9. invalid response handling")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        write_requests(requests_dir, SOURCE_ID, [valid_request()])
        bad = {"choices": [{"message": {"content": "not valid json"}}],
               "usage": {},
               "job_number": 1}
        write_responses(responses_dir, SOURCE_ID, [bad])
        code = cb.run(SOURCE_ID)
        check("exit non-zero", code != 0)
        check("no jsonl", not (jsonl_dir / f"{SOURCE_ID}.jsonl").exists())
        result = load_result(corpus_dir, SOURCE_ID)
        check("success false", result["success"] is False)
    finally:
        restore(saved)


@test("10. deterministic repeat")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        write_requests(requests_dir, SOURCE_ID, [valid_request()])
        write_responses(responses_dir, SOURCE_ID, [valid_response()])

        code_a = cb.run(SOURCE_ID)
        jsonl_a = (jsonl_dir / f"{SOURCE_ID}.jsonl").read_bytes()
        code_b = cb.run(SOURCE_ID)
        jsonl_b = (jsonl_dir / f"{SOURCE_ID}.jsonl").read_bytes()
        check("both exit 0", code_a == 0 and code_b == 0)
        check("byte-identical jsonl", jsonl_a == jsonl_b)
    finally:
        restore(saved)


@test("11. atomic write (no temp leftover)")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        write_requests(requests_dir, SOURCE_ID, [valid_request()])
        write_responses(responses_dir, SOURCE_ID, [valid_response()])
        code = cb.run(SOURCE_ID)
        check("exit 0", code == 0)
        check("no jsonl .tmp",
              not (jsonl_dir / f"{SOURCE_ID}.jsonl.tmp").exists())
        check("no result .tmp",
              not result_path(corpus_dir, SOURCE_ID).with_name(
                  result_path(corpus_dir, SOURCE_ID).name + ".tmp").exists())
    finally:
        restore(saved)


@test("12. forbidden writes")
def _():
    import paths as project_paths

    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        write_requests(requests_dir, SOURCE_ID, [valid_request()])
        write_responses(responses_dir, SOURCE_ID, [valid_response()])

        before = {
            p: sorted(x.name for x in p.iterdir())
            for p in (project_paths.SOURCE_REGISTRY,
                      project_paths.CLEANING_JOBS,
                      project_paths.CLEANING_RESULTS,
                      project_paths.CLEANED_ARCHIVE,
                      project_paths.REQUESTS,
                      project_paths.RESPONSES,
                      project_paths.PROCESSING_RESULTS)
        }
        code = cb.run(SOURCE_ID)
        check("exit 0", code == 0)
        after = {
            p: sorted(x.name for x in p.iterdir())
            for p in before
        }
        for folder in before:
            check(f"no write to {folder.name}", after[folder] == before[folder])
    finally:
        restore(saved)


@test("13. forbidden imports")
def _():
    source = pathlib.Path(DATA_PROCESSOR / "corpus_builder.py").read_text(
        encoding="utf-8")
    import_lines = "\n".join(
        ln for ln in source.splitlines()
        if ln.lstrip().startswith("import ") or ln.lstrip().startswith("from ")
    )
    for forbidden in ("deepseek_client", "request builder", "job builder",
                      "Analysis", "process_file", "clean_subtitles",
                      "clean_transcript", "urllib", "http", "openai"):
        check(f"no {forbidden!r}", forbidden not in import_lines)


@test("13b. corpus_builder_result writer boundary")
def _():
    source = pathlib.Path(DATA_PROCESSOR / "corpus_builder_result.py").read_text(
        encoding="utf-8")
    import_lines = "\n".join(
        ln for ln in source.splitlines()
        if ln.lstrip().startswith("import ") or ln.lstrip().startswith("from ")
    )
    for forbidden in ("corpus_builder", "deepseek_client",
                      "response_validator", "request builder", "Analysis",
                      "schemas", "paths", "project_config", "urllib"):
        check(f"no {forbidden!r}", forbidden not in import_lines)


@test("14. Corpus Result creation")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        write_requests(requests_dir, SOURCE_ID, [valid_request()])
        write_responses(responses_dir, SOURCE_ID, [valid_response()])
        code = cb.run(SOURCE_ID)
        check("exit 0", code == 0)
        result = load_result(corpus_dir, SOURCE_ID)
        check("schema valid", cbr.validate_result(result) == [])
        check("source_id", result["source_id"] == SOURCE_ID)
        check("success", result["success"] is True)
        check("records_written", result["records_written"] == 1)
        check("output_file",
              result["output_file"] == str(jsonl_dir / f"{SOURCE_ID}.jsonl"))
    finally:
        restore(saved)


@test("15. resume behavior")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        write_requests(requests_dir, SOURCE_ID, [valid_request()])
        write_responses(responses_dir, SOURCE_ID, [valid_response()])

        code_a = cb.run(SOURCE_ID)
        jsonl_a = (jsonl_dir / f"{SOURCE_ID}.jsonl").read_bytes()
        code_b = cb.run(SOURCE_ID)
        jsonl_b = (jsonl_dir / f"{SOURCE_ID}.jsonl").read_bytes()
        check("both exit 0", code_a == 0 and code_b == 0)
        check("idempotent output", jsonl_a == jsonl_b)
        result = load_result(corpus_dir, SOURCE_ID)
        check("success true on resume", result["success"] is True)
    finally:
        restore(saved)


@test("16. schema validation round-trip")
def _():
    result = cbr.build_result(
        source_id=SOURCE_ID,
        success=True,
        jobs_processed=1,
        jobs_failed=0,
        records_written=1,
        verified=True,
        output_file="jsonl/pod_conteppei_ep051.jsonl",
        errors=[],
        completion_time="2026-08-01 12:00:00",
    )
    check("valid", cbr.validate_result(result) == [])
    path = pathlib.Path(tempfile.mkdtemp()) / "x.json"
    cbr.write_result(path, result)
    check("round-trips",
          json.loads(path.read_text(encoding="utf-8")) == result)

    bad = cbr.build_result(
        source_id=SOURCE_ID,
        success=True,
        jobs_processed=1,
        jobs_failed=0,
        records_written="one",
        verified=True,
        output_file="x",
        errors=[],
    )
    check("invalid rejected", cbr.validate_result(bad) != [])


@test("17. corpus builder owns sentence text (parser text ignored)")
def _():
    # The parser altered ことが -> こと が. The corpus builder must produce
    # JSONL using the cleaned source text verbatim.
    canonical = "大きく 変わる ことが できます"
    parser_text = "大きく 変わる こと が できます"
    sentence = {
        "sentence_index": 0,
        "text": parser_text,
        "words": [[0, "大きく", "大きい", 0, 3],
                  [1, "変わる", "変わる", 4, 7],
                  [2, "こと", "こと", 8, 10],
                  [3, "が", "が", 11, 12],
                  [4, "できます", "できる", 13, 17]],
        "chunks": [[0, parser_text, 0, 5]],
        "expressions": [],
    }
    records = cb.restore_sentence_text([sentence], [canonical])
    check("text from cleaned source",
          records[0]["text"] == "大きく 変わる ことが できます")
    check("parser text ignored", records[0]["text"] != parser_text)

    # End-to-end: build a JSONL record with the restored text.
    record = dict(records[0])
    _, record = cb.assign_global_ids(record, 0)
    record = cb.stamp_provenance(record, {
        "source_id": SOURCE_ID, "source": SOURCE_ID,
        "source_file": "x.txt", "job_number": 1,
        "model": MODEL, "prompt_version": PROMPT_VERSION,
    })
    out = pathlib.Path(tempfile.mkdtemp()) / "out.jsonl"
    state = cb.jsonl_writer_state()
    state = cb.write_jsonl_record(record, out, state)
    line = out.read_text(encoding="utf-8").splitlines()[0]
    obj = json.loads(line)
    check("jsonl text is canonical",
          obj["text"] == "大きく 変わる ことが できます")
    check("jsonl word span matches canonical",
          obj["words"][2][3:5] == [8, 10])
    check("jsonl chunk text canonical",
          obj["chunks"][0][1] == "大きく 変わる ことが できます")


@test("18. offset verification still succeeds after restore")
def _():
    canonical = "大きく 変わる ことが できます"
    sentence = {
        "sentence_index": 0,
        "text": "大きく 変わる こと が できます",
        "words": [[0, "大きく", "大きい", 0, 3],
                  [1, "変わる", "変わる", 4, 7],
                  [2, "こと", "こと", 8, 10],
                  [3, "が", "が", 11, 12],
                  [4, "できます", "できる", 13, 17]],
        "chunks": [[0, "大きく 変わる こと が できます", 0, 5]],
        "expressions": [],
    }
    records = cb.restore_sentence_text([sentence], [canonical])
    r = records[0]
    check("word span exact",
          canonical[r["words"][2][3]:r["words"][2][4]] == r["words"][2][1])
    check("chunk span exact",
          canonical[r["words"][0][3]:r["words"][4][4]] == r["chunks"][0][1])
    check("all spans within text",
          all(0 <= w[3] <= w[4] <= len(canonical) for w in r["words"]))


@test("19. deliberately incorrect offset still fails")
def _():
    canonical = "大きく 変わる ことが できます"
    # Surface that cannot be matched in the canonical sentence.
    sentence = {
        "sentence_index": 0,
        "text": "x",
        "words": [[0, "存在しない", "存在しない", 0, 5]],
        "chunks": [],
        "expressions": [],
    }
    raised = False
    try:
        cb.restore_sentence_text([sentence], [canonical])
    except cb.CorpusBuilderError:
        raised = True
    check("impossible surface raises", raised)

    # Count mismatch also fails.
    s = {"sentence_index": 0, "text": "a",
         "words": [[0, "a", "a", 0, 1]], "chunks": [], "expressions": []}
    raised = False
    try:
        cb.restore_sentence_text([s, s], ["a"])
    except cb.CorpusBuilderError:
        raised = True
    check("count mismatch raises", raised)


@test("20. canonical sentence splitting matches expected content")
def _():
    source = "これは テスト です\n\nあいうえお\n\nさようなら！\n"
    texts = cb.canonical_sentence_texts(source)
    check("three canonical sentences", texts ==
          ["これは テスト です", "あいうえお", "さようなら！"])
    check("reconstructs", cb._expected_content(source) ==
          "\n\n".join(texts))
    check("empty source", cb.canonical_sentence_texts("") == [])


@test("21. empty expressions produce a valid corpus")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        # A response with all-empty expressions (Flash policy output).
        parser = {
            "source_name": SOURCE_ID,
            "job_number": 1,
            "sentences": [{
                "sentence_index": 0,
                "text": "こんにちは。",
                "words": [[0, "こんにちは", "こんにちは", 0, 5],
                          [1, "。", "。", 5, 6]],
                "chunks": [[0, "こんにちは。", 0, 2]],
                "expressions": [],
            }],
        }
        write_requests(requests_dir, SOURCE_ID, [valid_request()])
        resp = {
            "model": MODEL,
            "choices": [{"finish_reason": "stop",
                         "message": {"content":
                                     json.dumps(parser, ensure_ascii=False)}}],
            "usage": {},
            "job_number": 1,
        }
        write_responses(responses_dir, SOURCE_ID, [resp])
        code = cb.run(SOURCE_ID)
        check("exit 0", code == 0)
        result = json.loads(
            result_path(corpus_dir, SOURCE_ID).read_text(encoding="utf-8"))
        check("corpus success", result["success"] is True)
        check("records written", result["records_written"] == 1)
        check("jsonl exists", (jsonl_dir / f"{SOURCE_ID}.jsonl").is_file())
    finally:
        restore(saved)


@test("22. JSONL schema unchanged with empty expressions")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        parser = {
            "source_name": SOURCE_ID,
            "job_number": 1,
            "sentences": [{
                "sentence_index": 0,
                "text": "こんにちは。",
                "words": [[0, "こんにちは", "こんにちは", 0, 5],
                          [1, "。", "。", 5, 6]],
                "chunks": [[0, "こんにちは。", 0, 2]],
                "expressions": [],
            }],
        }
        write_requests(requests_dir, SOURCE_ID, [valid_request()])
        resp = {
            "model": MODEL,
            "choices": [{"finish_reason": "stop",
                         "message": {"content":
                                     json.dumps(parser, ensure_ascii=False)}}],
            "usage": {},
            "job_number": 1,
        }
        write_responses(responses_dir, SOURCE_ID, [resp])
        code = cb.run(SOURCE_ID)
        check("exit 0", code == 0)
        record = json.loads(
            (jsonl_dir / f"{SOURCE_ID}.jsonl")
            .read_text(encoding="utf-8").splitlines()[0]
        )
        check("schema keys unchanged",
              set(record) == {"text", "words", "chunks", "expressions",
                              "sentence_index", "ids", "section",
                              "provenance"})
        check("expressions present as empty list",
              record["expressions"] == [])
        check("expression_ids present as empty list",
              record["ids"]["expression_ids"] == [])
    finally:
        restore(saved)


@test("23. validator accepts empty expressions")
def _():
    import response_validator as rv
    response = {
        "source_name": SOURCE_ID,
        "job_number": 1,
        "sentences": [{
            "sentence_index": 0,
            "text": "こんにちは。",
            "words": [[0, "こんにちは", "こんにちは", 0, 5],
                      [1, "。", "。", 5, 6]],
            "chunks": [[0, "こんにちは。", 0, 2]],
            "expressions": [],
        }],
    }
    result = rv.validate_response(response, expected_source_name=SOURCE_ID,
                                  expected_job_number=1)
    check("valid with empty expressions", result["valid"] is True)


@test("24. corpus validation passes with metadata-supplied request")
def _():
    root, requests_dir, responses_dir, jsonl_dir, corpus_dir, saved = setup()
    try:
        text = "こんにちは。\n"
        # Request whose user message carries the SOURCE METADATA section
        # (the metadata payload contract fix).
        request = valid_request(source_id=SOURCE_ID, job_number=1, text=text)
        request["messages"][1]["content"] = (
            "SOURCE METADATA:\n"
            f"source_id: {SOURCE_ID}\n"
            "job_number: 1\n"
            "\n"
            "TEXT:\n"
            f"{text}"
        )
        write_requests(requests_dir, SOURCE_ID, [request])

        # Response echoes the supplied metadata -> validator passes.
        parser = {
            "source_name": SOURCE_ID,
            "job_number": 1,
            "sentences": [{
                "sentence_index": 0,
                "text": "こんにちは。",
                "words": [[0, "こんにちは", "こんにちは", 0, 5],
                          [1, "。", "。", 5, 6]],
                "chunks": [[0, "こんにちは。", 0, 2]],
                "expressions": [],
            }],
        }
        resp = {
            "model": MODEL,
            "choices": [{"finish_reason": "stop",
                         "message": {"content":
                                     json.dumps(parser, ensure_ascii=False)}}],
            "usage": {},
            "job_number": 1,
        }
        write_responses(responses_dir, SOURCE_ID, [resp])
        code = cb.run(SOURCE_ID)
        check("exit 0", code == 0)
        result = json.loads(
            result_path(corpus_dir, SOURCE_ID).read_text(encoding="utf-8"))
        check("corpus success", result["success"] is True)
        check("verified", result["verified"] is True)
        check("records written", result["records_written"] == 1)
        check("jsonl exists", (jsonl_dir / f"{SOURCE_ID}.jsonl").is_file())
    finally:
        restore(saved)


@test("25. job_text_from_user_content strips the metadata header")
def _():
    content = ("SOURCE METADATA:\n"
               "source_id: pod_x_ep001\n"
               "job_number: 1\n"
               "\n"
               "TEXT:\n"
               "これは　本文です。\n")
    text = cb.job_text_from_user_content(content)
    check("text extracted", text == "これは　本文です。\n")
    check("no metadata in text", "SOURCE METADATA" not in text)
    check("legacy content unchanged",
          cb.job_text_from_user_content("ただのテキスト。\n")
          == "ただのテキスト。\n")


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
