# Parser Output Field Specification

**Status:** APPROVED CONTRACT (frozen field definitions for the DeepSeek parser output).
**Version:** 1.0
**Documented basis:** README.md ("Corpus Parser Data-Preservation Architecture") and PROJECT_STATUS.md §§29–31.
**Contract boundary:** DeepSeek Parser → Response Validator → Corpus Builder → Analyzer.

This specification freezes the exact JSON object the DeepSeek parser returns for each job. It is the single contract consumed by the Response Validator and the Corpus Builder, and it is the source of truth for writing `parser_prompt.md`.

---

## 1. Scope and Principles

- The parser preserves linguistic evidence only. It never computes statistics.
- Positions reported by the parser are **job-local** only. Global source ordering and IDs are assigned later by the Corpus Builder.
- The parser returns **exactly one valid JSON object** per job.
- The parser must NOT produce: translations, readings, furigana, POS labels, grammar explanations, learner micro-chunks, frequencies, distances, averages, I+1 measurements, reports, or any other derived analysis.

## 2. Conventions (used consistently everywhere)

- **Indexing:** all indices are 0-based integers (`sentence_index`, word `index`, `start_word`, `end_word`, `char_start`, `char_end`).
- **Spans are half-open:** `char_start` is inclusive, `char_end` is exclusive; `start_word` is inclusive, `end_word` is exclusive. This matches Python slicing (`text[start:end]`).
- **Character positions** are 0-based Unicode code-point positions in the sentence `text`, counting every character including spaces and punctuation.
- **Field names** use snake_case, matching project conventions (`source_name`, `job_number`, `prompt_version`). The value of `source_name` is the exact pipeline `source_id`.

## 3. Word Rule (segmentation policy)

- If the source text is already whitespace-delimited, preserve the source's whitespace-delimited word units. Do **not** merge or re-segment them.
- For non-whitespace-delimited Japanese, use pragmatic meaningful word units as a reader perceives them.
- Keep inflected forms intact: `食べました`, `行って`, `思います`. Never decompose into morphological pieces such as `食べ / まし / た`.
- Functional elements may be separate units where appropriate.
- Do **not** add POS labels.
- Word units never include the spaces or punctuation that separate them.

## 4. Lexical Rule

Every word occurrence preserves both:

- `surface` — the exact Japanese form encountered in the source.
- `lexical` — the dictionary/base form corresponding to that occurrence.

Examples:

```
食べました → 食べる
食べない → 食べる
食べて → 食べる
行きました → 行く
行って → 行く
思います → 思う
```

- If the parser cannot confidently determine the dictionary/base form, `lexical` is `null`. Never invent a lexical form.

## 5. Sentence Rule

- Each sentence preserves the complete original Japanese sentence exactly. Do **not** normalize Japanese.
- The sentence `text` field is EVIDENCE: it must be copied byte-for-byte from the source, including every space exactly as it appears. The parser may analyze words/chunks/expressions, but must never insert or remove spaces, normalize particles, correct Japanese, or rewrite segmentation of the `text` field.
  - INVALID: `ことが` → `こと が`; `食べている` → `食べ ている`.
- A sentence is a complete Japanese sentence as encountered. Where the source text uses sentence-final punctuation (。, ！, ？), those mark sentence boundaries. Where the source text is a podcast-style transcript with no sentence-final punctuation, each line/utterance is one sentence.
- A sentence never spans a section/header marker line (see Section 9).
- `sentence_index` is job-local, 0-based, in order of appearance in the job text.

## 6. Top-Level Object

```
{
  "source_name": string,      // required, echoes the exact source_id; verified against the request file
  "job_number": integer,      // required, echoes the request; verified against the request file
  "sentences": [ ... ]        // required, non-empty array of sentence objects
}
```

`source_name` and `job_number` are echoed for self-identification. The parser must copy the exact `source_id` string (from the job identification) into the `source_name` field; it must not infer or generate a human-readable title. The Response Validator verifies they exactly match the request file.

## 7. Sentence Object

```
{
  "sentence_index": integer,     // required, 0-based, job-local
  "text": string,                // required, exact original Japanese sentence
  "words": [ ... ],              // required, array of 5-column positional arrays
  "chunks": [ ... ],             // required, array of 4-column positional arrays (may be empty)
  "expressions": [ ... ]         // required, array of 5-column positional arrays (may be empty)
}
```

Word, chunk, and expression records are POSITIONAL ARRAYS, never JSON objects.

## 8. Word Record

5-column positional array:

```
[index, surface, lexical, char_start, char_end]
```

| column | field | meaning |
|---|---|---|
| 0 | `index` | 0-based within the sentence, strictly ascending |
| 1 | `surface` | exact substring, no spaces |
| 2 | `lexical` | dictionary/base form; `null` only when no confident form |
| 3 | `char_start` | sentence-relative, inclusive |
| 4 | `char_end` | sentence-relative, exclusive |

Example:

```json
"words": [
  [0, "食べました", "食べる", 0, 5],
  [1, "を", "を", 6, 7]
]
```

### Character Spans

- `char_start` / `char_end` are **sentence-relative**.
- **Consistency invariant:** `text[char_start:char_end]` MUST equal `surface`.
- The Response Validator is responsible for checking this invariant.
- The parser is NOT required to emit sentence-level or source-global character offsets. Global positioning is derived deterministically by the Corpus Builder.

## 9. Grammar Chunk Rule

- Chunks are meaningful grammatical phrase-level units (e.g., `行くことにしました`), NOT learner/LingQ micro-chunks.
- Chunks are **flat and non-overlapping**. Every word belongs to at most one chunk.
- Chunks are ordered in the sentence (ascending `start_word`), and each chunk's `start_word` must be greater than or equal to the previous chunk's `end_word`.
- Chunk `text` corresponds to its word span: it MUST equal the verbatim substring of the sentence from the first word's `char_start` to the last word's `char_end` (including any spaces/punctuation inside that range).

### Chunk Record

4-column positional array:

```
[index, text, start_word, end_word]
```

| column | field | meaning |
|---|---|---|
| 0 | `index` | 0-based within the sentence |
| 1 | `text` | verbatim substring of the sentence (see rule above) |
| 2 | `start_word` | inclusive |
| 3 | `end_word` | exclusive |

Example:

```json
"chunks": [
  [0, "行くことにしました", 0, 4]
]
```

## 10. Expression Rule

- Expressions are a separate evidence layer from grammar chunks.
- **MOST IMPORTANT RULE:** preserve the LONGEST COMPLETE MEANINGFUL EXPRESSION. When a shorter expression is nested inside a longer expression, record only the longer one.
  - Example: `なぜかというと` is preserved as one expression; `という` is NOT additionally recorded when merely nested inside it.
- Independent, non-nested expressions elsewhere in the sentence may both be recorded.
- The parser identifies the expression as encountered. It does not provide a grammar lesson and never calculates expression statistics.

### Expression Record

5-column positional array:

```
[index, surface, start_word, end_word, pattern]
```

| column | field | meaning |
|---|---|---|
| 0 | `index` | 0-based within the sentence |
| 1 | `surface` | exact encountered surface (verbatim substring spanning its words, including any spaces as encountered) |
| 2 | `start_word` | inclusive |
| 3 | `end_word` | exclusive |
| 4 | `pattern` | OPTIONAL / ADVISORY, may be `null` |

Example:

```json
"expressions": [
  [0, "なぜか という と", 0, 3, "なぜかというと"]
]
```

### Pattern Field

- `pattern` is explicitly **OPTIONAL / ADVISORY**. It is a grouping aid, not authoritative truth.
- The actual occurrence evidence is `surface` + word span.
- `pattern` is a light normalization for grouping variants (e.g., `なぜかというと` as the normalized form of the encountered `なぜか という と`).
- The analyzer MUST remain capable of grouping and re-normalizing expressions later without relying on `pattern`.

## 11. Section Markers

- The parser must NOT output standalone source section/header marker lines (e.g., `===== Episode 51 =====`) as sentences, and must not include them inside any sentence `text`.
- Section/episode assignment is deterministic Corpus Builder work and is **not** trusted from the LLM as a global source position. No global section metadata is required from the parser.

## 12. Output Contract

The response content must be **exactly one valid JSON object**. It must contain:
- No Markdown fences (no ```).
- No explanatory prose.
- No comments.
- No multiple JSON objects.
- No text before or after the JSON.

## 13. Complete Example

```json
{
  "source_name": "podcast_transcript_con-teppei_ep051",
  "job_number": 1,
  "sentences": [
    {
      "sentence_index": 0,
      "text": "コーヒー を 飲んでます",
      "words": [
        [0, "コーヒー", "コーヒー", 0, 4],
        [1, "を", "を", 5, 6],
        [2, "飲んでます", "飲む", 7, 12]
      ],
      "chunks": [
        [0, "コーヒー を 飲んでます", 0, 3]
      ],
      "expressions": []
    },
    {
      "sentence_index": 1,
      "text": "なぜか という と",
      "words": [
        [0, "なぜか", "なぜか", 0, 3],
        [1, "という", "という", 4, 7],
        [2, "と", "と", 8, 9]
      ],
      "chunks": [
        [0, "なぜか という と", 0, 3]
      ],
      "expressions": [
        [0, "なぜか という と", 0, 3, "なぜかというと"]
      ]
    }
  ]
}
```

Notes on the example: the first sentence is whitespace-delimited (word units preserved from the source). In the second sentence, `なぜか という と` is the longest complete expression and is preserved as one expression; `という` is NOT recorded separately. `pattern` normalizes the spaced surface for grouping; it is advisory.

## 14. Validation Contract

### Response Validator (per response)

- Content parses as valid JSON.
- Required structure and field types per Sections 6–10.
- `source_name` (value = exact source_id) and `job_number` match the request file.
- `sentence_index` values are monotonic (strictly ascending, 0-based, no gaps).
- Word `index` values are strictly ascending within each sentence.
- Character spans are valid ranges within `text`; `text[char_start:char_end] == surface`.
- Chunk span consistency: chunk `text` equals the verbatim substring across its word span; `start_word`/`end_word` are valid word indices.
- Chunk non-overlap: chunks are ordered and do not overlap.
- Expression span validity: `start_word`/`end_word` are valid word indices.
- Basic longest-expression structural sanity where deterministically possible (no expression strictly contained within another expression with identical span).
- Rejects malformed responses; they must not reach corpus building.

### Corpus Builder (per source)

- Job ordering (process jobs in `job_number` order).
- Source-level reconstruction / integrity check (reconstructed sentence text reproduces the clean source text, with section/header marker lines removed).
- Section assignment (deterministic from source markers).
- Global sentence ordering and IDs.
- Global occurrence ordering and derived IDs.
- Provenance (source, source file, job number, model, prompt version, clean artifact).
- Source metadata.
- Final JSONL construction (one sentence = one JSONL record).

## 15. Analyzer Responsibilities

The analyzer derives from the saved corpus evidence (and never asks the parser to compute):

- word frequency
- lexical-form frequency
- expression frequency
- grammar-chunk frequency
- recurrence
- distance between occurrences
- clumping vs. dispersion
- source comparisons
- lesson/episode comparisons
- I+1 / comprehensibility measurements
- any other statistics or reports

The parser preserves enough positional evidence for all of these but never calculates them.
