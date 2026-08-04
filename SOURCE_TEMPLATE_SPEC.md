# SOURCE TEMPLATE SPECIFICATION

**Japanese Corpus Pipeline — Frozen V1.0 Source Template**

Date: 2026-08-02
Status: FROZEN (V1.0)
Applies to: `Templates/transcript_template.txt`, `Templates/subtitle_template.txt`

This specification defines the canonical source template used for manually
assembling raw collections before they enter the pipeline. It is a
human-authoring format; the pipeline consumes the cleaned per-source output.

---

## 1. Purpose

A source template is a single file that groups one collection's episodes so
raw text can be pasted in a consistent, machine-readable structure. One
template file = one collection.

---

## 2. SOURCE Header Fields

Every template begins with a `SOURCE` header. The header contains exactly
these eight fields, in this order:

```
template_version:
source_type:
collection:
season:
language:
origin:
episodes:
notes:
```

| Field | Meaning |
|---|---|
| `template_version` | Template format version. **Mandatory.** Defaults to `1.0`. |
| `source_type` | The type of source: `podcast_transcript` or `anime_subtitle`. |
| `collection` | Human-readable collection/series name. |
| `season` | Season number or label (blank if not applicable). |
| `language` | Language of the content (default `ja`). |
| `origin` | Where the material came from (e.g., show/podcast name, platform). |
| `episodes` | Count or summary of episodes in this file. |
| `notes` | Free-form notes for the human author. |

`template_version` is mandatory and defaults to `1.0`.

---

## 3. Episode Marker (Frozen)

The episode marker is frozen and MUST appear exactly as:

```
==================================================
EPISODE

episode: 0001

==================================================
```

- The separator line is exactly 50 `=` characters.
- The word `EPISODE` appears on its own line.
- The `episode:` field follows on its own line after a blank line.
- The closing separator line follows after a blank line.
- After each marker there is blank space for pasting the raw episode text.

---

## 4. Four-Digit Episode Numbering

Episode numbers use **four digits**:

- `0001`, `0002`, `0003`, ... `0015`

Numbers are zero-padded to four characters. The frozen templates provide
exactly **15 episode blocks** numbered `0001` through `0015`.

---

## 5. One Collection Per File

Each template file represents exactly one collection. The `collection` header
field identifies it. A new collection requires a new template file (a copy of
the frozen template with the header filled in). Multiple collections must
never be combined in one file.

---

## 6. Blank Episode Blocks Allowed

Unused episode blocks are permitted. A block may be left blank (no pasted
text) and does not need to be removed. The pipeline/process decides which
episodes are populated; the template does not enforce that every block is
used.

---

## 7. Human-Editable Boundary

The header (fields `collection`, `season`, `language`, `origin`, `episodes`,
`notes`) and the episode text content are **human-editable**. The human author
fills in the collection metadata and pastes raw transcript/subtitle text into
the episode blocks.

---

## 8. Machine-Generated Boundary

The structural elements are **machine-generated** and must not be hand-edited
in ways that break parsing:

- the `SOURCE` header block and its field names,
- the `template_version` value,
- the episode marker structure (separator lines, `EPISODE`, `episode: NNNN`),
- the four-digit episode numbering,
- the presence of exactly 15 episode blocks.

These are produced from the frozen template and are stable across files.

---

## 9. Canonical Source Text Ownership

The text pasted into the episode blocks is the canonical source evidence.
Once a raw episode is processed through cleaning, the cleaned transcript is
the canonical authority for sentence text (the Corpus Builder owns sentence
text). The template is only the authoring container; it does not redefine
source ownership.

---

## 10. No Internal IDs in Templates

Templates contain **no internal IDs**. There are no source_id values,
database keys, hashes, or pipeline identifiers in the template. Identity is
assigned later by the pipeline (Source Intake). The only identifiers present
are the human-facing `episode: NNNN` labels.

---

## 11. Origin Field Purpose

The `origin` field records where the material came from (e.g., a specific
show, podcast, platform, or episode source). It is metadata for human
understanding and future provenance; it is not used as pipeline identity.
For transcripts a sensible default origin may be filled in; subtitles may
leave it blank for the author to complete.

---

## 12. Backward Compatibility Policy

- The template format is frozen at `template_version: 1.0`.
- Existing template files remain valid as long as they keep the `SOURCE`
  header fields, the frozen episode marker, and four-digit episode numbers.
- Adding optional header fields or additional episode blocks is a format
  change and requires a new `template_version`.
- `template_version` exists so future consumers can detect format changes and
  remain backward compatible.

---

## 13. Template Files

- `Templates/transcript_template.txt` — `source_type: podcast_transcript`,
  15 episode blocks.
- `Templates/subtitle_template.txt` — `source_type: anime_subtitle`,
  15 episode blocks.

The two templates differ only in `source_type` (and a sensible default
`origin` if appropriate). All structural rules above are identical.
