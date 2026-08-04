# HANDOFF — M1-7.6 FLASH EXPRESSION POLICY

Date: 2026-08-02
Scope: Expression extraction policy for the DeepSeek Flash parser model.
Type: Architecture decision + milestone handoff.

---

## ARCHITECTURE DECISION — EXPRESSIONS ARE ENRICHMENT DATA

Expressions are enrichment data.

They are model-dependent and are not required for successful corpus
generation.

The canonical corpus consists of:

- sentence text
- words
- chunks
- provenance

Expression extraction may be enabled or disabled depending on model
capability without changing the JSONL schema.

---

## Rationale

Real production validation demonstrated that DeepSeek Flash reliably
produces sentence, word, and chunk data to the required standard, but
expression extraction remains stochastic and occasionally produces invalid
spans (e.g., an expression surface not matching its word span). This is a
MODEL CAPABILITY limitation, not an architecture limitation.

The response is a per-model capability policy rather than a schema change.

## Behavior

- Expressions remain part of the canonical JSONL schema.
- Every record always contains the `expressions` field.
- When expression extraction is disabled for the configured model, the
  parser is instructed to always emit `"expressions": []`.
- The validator accepts empty expression arrays.
- The corpus builder writes empty expression arrays.
- No failures occur because expressions are absent.

## Per-model capability table

Defined in `project_config.py`:

    MODEL_EXPRESSIONS_ENABLED = {
        "deepseek-v4-flash": False,
    }

`expressions_enabled(model_name)` returns the capability for a model.
Unknown models default to enabled, so a future capable model (DeepSeek
Think, GPT, Claude, ...) re-enables expressions without any pipeline or
schema change.

## Files changed (M1-7.6)

- `project_config.py` — `MODEL_EXPRESSIONS_ENABLED` + `expressions_enabled()`.
- `Data Processor/request builder.py` — `effective_prompt()` appends the
  `EXPRESSIONS_DISABLED_DIRECTIVE` when the configured model has expressions
  disabled; `run()` uses `effective_prompt()`.
- `Data Processor/tests/test_request_builder.py` — updated message-payload
  assertion to `effective_prompt()`; added tests 13/13b/13c.
- `Data Processor/tests/test_corpus_builder.py` — added tests 21/22/23
  (empty expressions produce a valid corpus; JSONL schema unchanged;
  validator accepts empty expressions).
- `Source Intake/tests/test_project_config.py` — added expression-capability
  test.

## Validation

Corpus generation succeeds with `"expressions": []`. JSONL schema unchanged.

## Status

Regression green. Expressions are now a per-model capability. DeepSeek Flash
ships with expressions disabled; future capable models enable them by simply
adding an entry to `MODEL_EXPRESSIONS_ENABLED` (or by omission, since unknown
models default to enabled).
