# SOURCE_METADATA_SPEC

**Japanese Corpus Pipeline — Source Builder V1 Metadata Specification**

Date: 2026-08-02
Status: DESIGN SPECIFICATION (V1, pre-implementation)

This document specifies the configuration files and controlled vocabulary
used by the Source Builder.

---

## Config File Structure

The Source Builder reads controlled vocabulary from configuration files
under `C:\Jprogram\Config\`.

```
C:\Jprogram\Config\
    collections.json
    source_types.json
    origins.json
```

Config controls metadata selection. Each file defines a stable,
machine-friendly controlled vocabulary. The GUI presents these as
dropdowns; values are never free-typed by the user.

Machine-friendly names remain the canonical values.

Language is a project-level property, not source metadata. Each project
installation represents one language (this project: `ja`). Language is not a
source-level field, is not in `Config\`, and has no config file.

---

## collections.json

Controlled collection identifiers used in collection mode.

Structure: a list of collection objects.

```json
{
  "collections": []
}
```

Current state (2026-08-04): the collections table is empty for a fresh
real-data start. Collections are added via the app's metadata editor or by
editing this file. The example structure below (pre-cleanup) shows the object
shape:

```json
{
  "collections": [
    {
      "collection_id": "teppei_beginner",
      "name": "Con Teppei for Beginner",
      "source_type": "podcast_transcript"
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `collection_id` | Machine identifier used in filenames and identity (lowercase, underscores). |
| `name` | Human-readable name shown in the GUI. |
| `source_type` | The source type this collection is expected to produce. |

Rules:

- `collection_id` is unique.
- `collection_id` is machine-friendly: lowercase letters, digits, underscores.
- A collection is bound to a `source_type` to pre-select it in the GUI.

---

## source_types.json

Controlled source content formats.

```json
{
  "source_types": [
    {
      "source_type_id": "podcast_transcript",
      "display_name": "podcast_transcript"
    }
  ]
}
```

Current state (2026-08-04): `podcast_transcript` is the only configured source
type (the only type with a pipeline processing profile). Pre-cleanup the table
also listed `subtitle`, `article`, `manga_text`, and `book_text`; those were
removed as development values without processing profiles.

Rules:

- `source_type` describes the content format, not the medium.
- `subtitle` does not imply "anime only"; collections determine context.
- Values are lowercase, machine-friendly identifiers.

---

## origins.json

Controlled origin values (where material came from).

```json
{
  "origins": [
    {
      "origin_id": "user_transcription",
      "display_name": "user_transcription"
    }
  ]
}
```

Current state (2026-08-04): `user_transcription` is the only configured origin
(a generic default). Pre-cleanup the table also listed `con_teppei_podcast`,
`nhk_news`, and `ci_japanese`; those were removed as development values.

Rules:

- `origin` is a machine-friendly identifier.
- Each origin may optionally carry extra metadata (for example a display
  name) via an object form if needed in the future.

---

## Controlled Vocabulary Rules

- Every controlled field is drawn from exactly one config file.
- Values are stable, machine-friendly identifiers (lowercase, underscores,
  no spaces).
- The GUI presents controlled fields as dropdowns; the user never types a
  controlled value.
- Unknown or out-of-vocabulary values are rejected.
- Config files are plain JSON, human-editable, and managed outside the GUI.
- Adding a value to a config file makes it available in the GUI without code
  changes.

---

## Identity Examples

### Collection mode

```json
{
  "identity_type": "collection",
  "collection_id": "teppei_beginner",
  "episode": 51,
  "source_type": "podcast_transcript",
  "origin": "con_teppei_podcast"
}
```

Generated filename:

```
teppei_beginner_ep0051.txt
```

Canonical save path:

```
Sources\collections\teppei_beginner\teppei_beginner_ep0051.txt
```

### Standalone mode

```json
{
  "identity_type": "standalone",
  "source_name": "nhk_weather_article_august",
  "source_type": "article",
  "origin": "nhk_news"
}
```

Generated filename:

```
nhk_weather_article_august.txt
```

Canonical save path:

```
Sources\standalone\nhk_weather_article_august.txt
```

---

## Canonical Source Storage

The finalized production storage model:

```
C:\Jprogram\Sources\
    collections\
        <collection_id>\
            <collection_id>_epNNNN.txt

    standalone\
        <source_name>.txt
```

- Collection identity creates `Sources\collections\<collection_id>\<collection_id>_epNNNN.txt`.
- Standalone identity creates `Sources\standalone\<source_name>.txt`.
- The two identity paths remain mutually exclusive.
- The Source Builder owns creation of canonical source files; the save path
  is automatic and never user-selected.

---

## Production Install Assumption and Migration Note

Development and testing will eventually be completed. The production
workflow begins from a clean empty project structure.

Existing development datasets will be converted into canonical Source
Builder files before production use. Migration should:

- assign correct metadata,
- create canonical filenames,
- place files into `Sources\`,
- validate through Source Intake.

Existing datasets are not modified during this documentation task.

---

## Boundaries

- These config files define input vocabulary only.
- They do not define pipeline behavior, cleaning profiles, or artifact
  schemas (those remain in the pipeline configuration).
- No production code is modified by this specification.
