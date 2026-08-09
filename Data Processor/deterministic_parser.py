#!/usr/bin/env python3
"""
deterministic_parser.py

Japanese Corpus Pipeline - Deterministic Parser (GiNZA / spaCy).

A self-contained, rule-based parser that satisfies the same
PARSER_OUTPUT_SPEC.md contract as the DeepSeek parser. It uses GiNZA
and spaCy's ja_ginza model (split_mode "A") and is fully
deterministic: no LLM calls, no statistical sentence segmentation.

Layers:

1. Sentence splitting (split_sentences) is a pure function over the
   job's clean source text. Sentence-final punctuation (。！？) marks a
   boundary and stays attached to the preceding sentence; a line with
   no such punctuation is one whole sentence.

2. Word segmentation (segment_sentence) preserves an already
   whitespace-delimited source's units exactly. Otherwise it runs the
   pipeline on the sentence and fuses tokenizer-level morphemes into
   Word-Rule-compliant words with a fixed merge rule keyed on the
   fine-grained UniDic tag (token.tag_), never the coarse spaCy POS
   field (which is unreliable on Japanese, confirmed in this study).

   Merge rule:
   - A conjugatable head (動詞-一般, 形容詞-一般, or a サ変可能 noun
     immediately followed by a conjugated する/auxiliary chain)
     absorbs every immediately-following bound continuation
     (助動詞, 助詞-接続助詞) of its conjugation.
   - A 動詞-非自立可能 token NEVER merges backward into a preceding
     word: it always starts a fresh word boundary. It is still a valid
     head in its own right and forward-merges its own following
     助動詞/接続助詞 chain (so きた = one word, lexical くる).
   - A merge stops before absorbing a bound continuation whose
     would-be tail is already grammatically complete: if the current
     group tail's morph Inflection is in terminal form (終止形, the
     conjugation-form component after the semicolon), the next
     助動詞/助詞-接続助詞 token starts a fresh word instead (so 決まるです
     = two words 決まる + です, while 食べました stays one word).
   - Merging never crosses a bunsetu boundary, which guarantees the
     chunk layer stays flat and non-overlapping.

3. Chunk mapping uses GiNZA's bunsetu_spans() and re-expresses each
   bunsetu span over the MERGED word indices produced by layer 2.

4. parse_job assembles layers 1-3 into the full contract-shaped dict,
   including deterministic expression detection (detect_expressions)
   against a small pre-vetted Phase 1 dictionary of known Japanese
   expressions.

This module is built and tested in isolation. It is not yet wired
into the pipeline (Job Builder, Request Builder, Production Manager,
or app.py) and is not part of the frozen component set yet.
"""

import json
import re
import sys
from pathlib import Path

import ginza
import spacy

# Project import convention: expose the project root and the shared
# Common utility layer (same sys.path/import pattern Transcript
# Cleaner/clean_transcript.py uses to import from Common/cleaning_utils.py).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "Common"))

from sentence_split import split_line, SENTENCE_FINAL_PUNCT

CANONICAL_LINE_SEPARATOR = "\n\n"

# Word separator characters, mirroring the Response Validator's evidence
# separators: word units never include the spaces or punctuation that
# separate them (PARSER_OUTPUT_SPEC section 3).
PUNCTUATION = frozenset(
    "。、，．！？!?…；：,.;:()（）「」『』\u301C\uFF5E\u30FB\u2015\u2014")

# Conjugatable-head fine-grained UniDic tags.
HEAD_TAGS = frozenset({"動詞-一般", "形容詞-一般"})

SURU_NOUN_TAG = "名詞-普通名詞-サ変可能"
SURU_LEMMA = "する"

# Forward-only head: never merges backward into a preceding word; always
# starts a fresh word and forward-merges its own continuation chain.
FORWARD_ONLY_HEAD_TAGS = frozenset({"動詞-非自立可能"})

# Bound-continuation fine-grained UniDic tags.
CONTINUATION_TAGS = frozenset({"助動詞", "助詞-接続助詞"})

_WHITESPACE_RUN = re.compile(r"\S+")

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load(
            "ja_ginza",
            config={"components": {"compound_splitter": {"split_mode": "A"}}},
        )
    return _nlp


# Phase 1 expression dictionary (see detect_expressions in Part 4).
# Each line is one entry {"surface", "reading", "gloss", "score", "lemmas"},
# where "lemmas" was precomputed by running the entry's surface through this
# module's own segment_sentence(), so it is guaranteed consistent with how
# real sentence words are lemmatized.
EXPRESSIONS_DICTIONARY_PATH = (
    Path(__file__).resolve().parent
    / "Expression Dictionary"
    / "jmdict_expressions_phase1.jsonl"
)

_expression_index = None


def _get_expression_index():
    """Lazily load the Phase 1 expression dictionary, indexed by first lemma.

    Mirrors _get_nlp()'s lazy-singleton pattern: loaded once on first use,
    then cached. Entries with fewer than two lemmas are skipped -- a
    single-lemma "expression" would just duplicate the existing word layer.
    Returns a dict mapping each kept entry's first lemma to the list of
    entries starting with it, so detect_expressions() only inspects
    candidates whose first lemma matches a word, never a full linear scan.
    """
    global _expression_index
    if _expression_index is None:
        index = {}
        with open(EXPRESSIONS_DICTIONARY_PATH, encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                lemmas = entry["lemmas"]
                if len(lemmas) < 2:
                    continue
                index.setdefault(lemmas[0], []).append(entry)
        _expression_index = index
    return _expression_index


# ============================================================
# Part 1 - Sentence splitting (pure, deterministic)
# ============================================================

def _is_section_marker_line(line):
    """True if the line is a section/header marker such as ===== Episode 51 =====."""
    stripped = line.strip()
    return stripped.startswith("=====") and stripped.endswith("=====")


def split_sentences(clean_text):
    """Split the job's clean source text into sentences.

    Deterministic and rule-based (PARSER_OUTPUT_SPEC section 5). The
    sentence text is copied byte-for-byte from the source; nothing is
    normalized, and section/header marker lines are never sentences.
    """
    if not clean_text:
        return []
    lines = clean_text.split(CANONICAL_LINE_SEPARATOR)
    kept = [line for line in lines if not _is_section_marker_line(line)]
    if kept and kept[-1].endswith("\n"):
        kept[-1] = kept[-1][:-1]
    sentences = []
    for line in kept:
        sentences.extend(split_line(line))
    return sentences


# ============================================================
# Part 2 - Word segmentation + merge rule
# ============================================================

def _is_separator(text):
    """True if every character is a separator (space or punctuation)."""
    return all(ch in PUNCTUATION or ch.isspace() for ch in text)


def _is_suru(token):
    """True for a conjugated する token (the suru continuation)."""
    return token.tag_ == "動詞-非自立可能" and token.lemma_ == SURU_LEMMA


def _is_terminal_form(token):
    """True if the token's morph Inflection names a terminal (終止形) form.

    The conjugation-form component is the part of the Inflection value
    after the semicolon, e.g. "五段-ラ行;終止形-一般" -> "終止形-一般".
    A token already in terminal form is grammatically complete and must
    not absorb a following bound continuation (助動詞/助詞-接続助詞).
    """
    for inf in token.morph.get("Inflection"):
        form = inf.split(";")[-1].strip()
        if form.startswith("終止形"):
            return True
    return False


def _merge_groups(doc, token_bunsetu=None):
    """Apply the deterministic merge rule over a spaCy Doc's raw tokens.

    Returns a list of groups; each group is the list of raw tokens
    fused into one word. Separator tokens are never part of a word and
    are excluded. When token_bunsetu is given, a merge never crosses a
    bunsetu boundary.
    """
    tokens = [t for t in doc if not _is_separator(t.text)]
    groups = []
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        tag = tok.tag_
        group_boundary = token_bunsetu[tok.i] if token_bunsetu is not None else None
        is_suru_head = (
            tag == SURU_NOUN_TAG
            and i + 1 < n
            and _is_suru(tokens[i + 1])
        )
        if tag in HEAD_TAGS or is_suru_head:
            j = i + 1
            while j < n:
                nxt = tokens[j]
                if token_bunsetu is not None and token_bunsetu[nxt.i] != group_boundary:
                    break
                if _is_terminal_form(tokens[j - 1]):
                    break
                if nxt.tag_ in CONTINUATION_TAGS:
                    j += 1
                    continue
                if is_suru_head and _is_suru(nxt):
                    j += 1
                    continue
                break
            groups.append(tokens[i:j])
            i = j
        elif tag in FORWARD_ONLY_HEAD_TAGS:
            j = i + 1
            while j < n:
                nxt = tokens[j]
                if token_bunsetu is not None and token_bunsetu[nxt.i] != group_boundary:
                    break
                if _is_terminal_form(tokens[j - 1]):
                    break
                if nxt.tag_ in CONTINUATION_TAGS:
                    j += 1
                    continue
                break
            groups.append(tokens[i:j])
            i = j
        else:
            groups.append([tokens[i]])
            i += 1
    return groups


def _word_from_group(group):
    """Build a 4-column word record [surface, lexical, char_start, char_end]."""
    surface = "".join(t.text for t in group)
    lexical = group[0].lemma_
    char_start = group[0].idx
    char_end = group[-1].idx + len(group[-1].text)
    return [surface, lexical, char_start, char_end]


def _lexical_for_unit(surface):
    """Resolve one whitespace-delimited unit's lexical form.

    The unit's own boundary is authoritative and is never split further
    by the tokenizer's morpheme boundaries. The head-token/merge logic
    picks one lexical value for the whole unit: the head lemma of the
    merge group that contains the unit's first token.
    """
    doc = _get_nlp()(surface)
    groups = _merge_groups(doc)
    if not groups:
        return surface
    return groups[0][0].lemma_


def _build_chunks(text, words, token_to_word, bunsetu_spans):
    """Re-express bunsetu spans over merged word indices.

    words are 4-column records; token_to_word maps each raw token index
    to its word index (or None for separator tokens). If a bunsetu
    boundary falls inside a word, the chunk is coarsened into the
    previous chunk so chunks stay flat, non-overlapping, and ordered.
    Chunks reference only post-merge word indices.
    """
    chunks = []
    for b in bunsetu_spans:
        ws = None
        we = None
        for i in range(b.start, b.end):
            w = token_to_word[i]
            if w is None:
                continue
            if ws is None or w < ws:
                ws = w
            if we is None or w >= we:
                we = w + 1
        if ws is None:
            continue
        if chunks and chunks[-1][2] > ws:
            chunks[-1][1] = min(chunks[-1][1], ws)
            chunks[-1][2] = max(chunks[-1][2], we)
        else:
            chunks.append([None, ws, we])
    for c in chunks:
        sw, ew = c[1], c[2]
        c[0] = text[words[sw][2]:words[ew - 1][3]]
    return chunks


def _segment_continuous(text):
    """Word/chunk segmentation for standard continuous Japanese."""
    nlp = _get_nlp()
    doc = nlp(text)
    bunsetu_spans = list(ginza.bunsetu_spans(doc))
    token_bunsetu = [None] * len(doc)
    for bi, b in enumerate(bunsetu_spans):
        for i in range(b.start, b.end):
            token_bunsetu[i] = bi
    groups = _merge_groups(doc, token_bunsetu)
    words = []
    token_to_word = [None] * len(doc)
    for wi, group in enumerate(groups):
        words.append(_word_from_group(group))
        for t in group:
            token_to_word[t.i] = wi
    chunks = _build_chunks(text, words, token_to_word, bunsetu_spans)
    return words, chunks


def _segment_whitespace(text):
    """Word/chunk segmentation preserving the source's space-delimited units."""
    nlp = _get_nlp()
    doc = nlp(text)
    bunsetu_spans = list(ginza.bunsetu_spans(doc))
    words = []
    token_to_word = [None] * len(doc)
    for m in _WHITESPACE_RUN.finditer(text):
        start = m.start()
        end = m.end()
        k = start
        while k < end and text[k] in PUNCTUATION:
            k += 1
        l = end
        while l > k and text[l - 1] in PUNCTUATION:
            l -= 1
        if k >= l:
            continue
        surface = text[k:l]
        lexical = _lexical_for_unit(surface)
        wi = len(words)
        words.append([surface, lexical, k, l])
        for t in doc:
            if not _is_separator(t.text) and t.idx >= k and t.idx + len(t.text) <= l:
                token_to_word[t.i] = wi
    chunks = _build_chunks(text, words, token_to_word, bunsetu_spans)
    return words, chunks


def segment_sentence(text):
    """Segment one sentence into words and chunks.

    Returns (words, chunks) with final positional-array columns:
    words are 5-column [index, surface, lexical, char_start, char_end];
    chunks are 4-column [index, text, start_word, end_word].
    """
    if " " in text:
        words4, chunks3 = _segment_whitespace(text)
    else:
        words4, chunks3 = _segment_continuous(text)
    words = [[i] + w for i, w in enumerate(words4)]
    chunks = [[i] + c for i, c in enumerate(chunks3)]
    return words, chunks


# ============================================================
# Part 4 - Expression detection (Phase 1) + assembly
# ============================================================

def detect_expressions(text, words):
    """Detect known Japanese expressions in one sentence.

    Matches each word's already-computed lexical (lemma) value against the
    Phase 1 dictionary's precomputed lemma sequences. The
    longest-complete-expression rule (PARSER_OUTPUT_SPEC section 10) is
    enforced by explicit overlap resolution: candidates are considered
    longest-span first (ties broken by earlier start_word), and a candidate
    is accepted only if its word-index span shares no word index with an
    already-accepted span. This alone rejects every shorter/nested
    candidate that a longer accepted expression covers; independent,
    non-overlapping expressions are all kept.

    Args:
        text: the sentence text (verbatim, including spaces/punctuation).
        words: the sentence's 5-column word records
            [index, surface, lexical, char_start, char_end].

    Returns:
        A list of 5-column expression records
        [index, surface, start_word, end_word, pattern], ordered by
        ascending start_word with index 0-based in that order. surface is
        the verbatim substring spanning the words
        (text[words[start][3]:words[end - 1][4]]); pattern is the matched
        dictionary entry's own surface (advisory, per the spec).
    """
    word_lemmas = [w[2] for w in words]
    n = len(word_lemmas)
    index = _get_expression_index()

    candidates = []
    for start in range(n):
        for entry in index.get(word_lemmas[start], ()):
            lemmas = entry["lemmas"]
            end = start + len(lemmas)
            if end <= n and word_lemmas[start:end] == lemmas:
                candidates.append((start, end, entry))

    # Longest span first, then earlier start_word as a tiebreaker.
    candidates.sort(key=lambda c: (-(c[1] - c[0]), c[0]))

    accepted = []
    covered = set()
    for start, end, entry in candidates:
        span = range(start, end)
        if any(i in covered for i in span):
            continue
        covered.update(span)
        accepted.append((start, end, entry))

    accepted.sort(key=lambda c: c[0])
    return [
        [i, text[words[start][3]:words[end - 1][4]], start, end, entry["surface"]]
        for i, (start, end, entry) in enumerate(accepted)
    ]


# ============================================================
# Assembly
# ============================================================

def parse_job(source_name, job_number, clean_text):
    """Parse one job's clean source text into the contract-shaped dict.

    Returns {"source_name": str, "job_number": int, "sentences": [...]},
    with sentence_index assigned 0-based in order of appearance.
    Each sentence's expressions are detected deterministically by
    detect_expressions(): lemma-sequence matching against the Phase 1
    expression dictionary of 1,120 multi-lemma entries, with explicit
    longest-expression overlap resolution. Matching is deliberately
    limited to that small pre-vetted dictionary as a known, intentional
    Phase 1 scope boundary, not a bug; Phase 2 scales to the full
    35,633-entry dictionary.
    """
    sentences = split_sentences(clean_text)
    parsed = []
    for index, text in enumerate(sentences):
        words, chunks = segment_sentence(text)
        parsed.append({
            "sentence_index": index,
            "text": text,
            "words": words,
            "chunks": chunks,
            "expressions": detect_expressions(text, words),
        })
    return {
        "source_name": source_name,
        "job_number": job_number,
        "sentences": parsed,
    }


__all__ = [
    "CANONICAL_LINE_SEPARATOR",
    "SENTENCE_FINAL_PUNCT",
    "PUNCTUATION",
    "HEAD_TAGS",
    "FORWARD_ONLY_HEAD_TAGS",
    "CONTINUATION_TAGS",
    "split_sentences",
    "segment_sentence",
    "detect_expressions",
    "parse_job",
    "_is_section_marker_line",
    "_merge_groups",
    "_word_from_group",
    "_get_expression_index",
]
