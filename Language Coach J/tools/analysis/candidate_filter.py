"""
candidate_filter.py — deterministic candidate filter for value-criteria reports.

Removes shape-noise (never-words) from candidate lists before value scoring.

Design decisions (Owner, 2026-08-09):
- Katakana / loanwords are NOT filtered. They are legitimately "unknown"
  until encountered; Owner grades or ignores them in the Reasonix reader.
  False-friend vs. simple-transfer distinction is a reader-grading concern,
  not a report-filter concern.
- The known-gate (LingQ level >=4, later Reasonix status=='known') is the
  CALLER's responsibility, applied before this filter or after — this module
  only removes surfaces that are never words regardless of known-state.
- Rule-based, deterministic, no external references (dictionary-gating was
  investigated and rejected: JMdict contains the fragments — うーん/お/でし
  are all real dictionary entries — and omits conjugations — あります/持って —
  so dictionary lookup cannot separate noise from vocabulary).

Classes removed:
  1. Digits            — fullwidth or ASCII digit runs (１/２/3)
  2. Single kana       — one-character hiragana/katakana (お/あ/た/つ)
  3. Filler shape      — hiragana ending in ー (うーん/えー/あー/んー)
  4. Punctuation marks — ヽ/ヾ/々/〆 etc.
  5. Explicit tokenizer-split fragments — verified non-word splits like でし
     (tail of です/でした) that pass shape rules but are not vocabulary.

Boundary cases deliberately KEPT (documented):
- 2-char hiragana like こと/もの/どう/もう/こっち — real vocabulary (even if
  low LingQ level); the known-gate handles them, not this filter.
- Conjugated forms (あります/持って/やって) — real vocabulary; not
  dictionary-lookable, but shape rules don't touch them. Correct.
- Single kanji (時/目/回) — real words; only *kana* single chars are noise.
"""

import re

# --- Class 1: shape noise -------------------------------------------------

DIGIT_RE = re.compile(r'^[\uFF10-\uFF19\u0030-\u0039]+$')
SINGLE_KANA_RE = re.compile(r'^[\u3040-\u30FF]$')          # one kana char
# hiragana-only filler with ー anywhere inside/end (うーん/えー/あー/んー).
# Katakana (30A0-30FF) deliberately excluded — アクセサリー/コーヒー must survive.
HIRAGANA = r'\u3040-\u309F'
# hiragana string of length <=3 that CONTAINS ー (うーん/えー/あー/んー).
# Katakana (30A0-30FF) deliberately excluded — アクセサリー/コーヒー must survive.
# Plain short hiragana without ー (こと/もの/どう/もう/こっち/やって) is real vocab.
FILLER_RE = re.compile(rf'^[{HIRAGANA}ー]+$')
FILLER_MAX_LEN = 3
PUNCT_MARKS = set('ヽヾ々〆ー、。・「」『』（）〜')

# --- Class 5: explicit tokenizer-split fragments --------------------------
# Verified from real corpus data as non-word splits (tails of auxiliaries /
# particles that pass shape rules). Keep this list tiny; prefer adding shape
# rules over list entries. でし: split tail of です/でした (GiNZA).
EXPLICIT_FRAGMENTS = {
    'でし',   # です/でした tail
}

_kana_only = re.compile(r'^[\u3040-\u30FF]+$')


def is_shape_noise(surface: str) -> bool:
    """True if the surface is never a word (regardless of known-state)."""
    if not surface:
        return True
    if DIGIT_RE.match(surface):
        return True
    if SINGLE_KANA_RE.match(surface):
        return True
    if FILLER_RE.match(surface) and len(surface) <= FILLER_MAX_LEN and 'ー' in surface:
        return True
    if all(c in PUNCT_MARKS for c in surface):
        return True
    if surface in EXPLICIT_FRAGMENTS:
        return True
    return False


def filter_candidates(candidates, known: set = None, include_katakana: bool = True):
    """
    Drop shape-noise from a candidate iterable.

    candidates: iterable of surface strings (or dicts with 'surface' key).
    known: optional set of known surfaces — surfaces in it are dropped
           (caller's known-gate; None disables).
    include_katakana: if False, also drop pure-katakana surfaces (currently
           unused — Owner decision keeps katakana as unknowns; kept as a
           parameter so the loanword-filter work can reuse this module later).

    Returns list of surfaces that survive.
    """
    out = []
    for c in candidates:
        surface = c if isinstance(c, str) else c.get('surface', '')
        if is_shape_noise(surface):
            continue
        if known and surface in known:
            continue
        if not include_katakana and re.fullmatch(r'[\u30A0-\u30FFー]+', surface):
            continue
        out.append(surface)
    return out
