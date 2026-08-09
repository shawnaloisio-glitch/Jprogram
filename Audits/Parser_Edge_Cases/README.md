# Parser Edge Cases — tracking log for a later batch fix

Accumulates real, reproducible cases where the deterministic parser
(`Data Processor/deterministic_parser.py`) or the reconstruction gate
(`Data Processor/parser_normalizer.py`) rejects real content — both
Frozen Components, so fixes here need a real Coder task plus the
automatic audit trigger, not an ad-hoc patch. Per Owner's explicit call
(2026-08-09): don't fix these one at a time as they turn up; let them
accumulate here and batch them into one real fix/audit cycle later,
since the failure mode is "file doesn't make it into the corpus yet,"
not "wrong data gets in" — low urgency, safe to defer.

`bad_sentences.clean.txt` in this folder is a standalone, directly
runnable fixture containing just the real problem sentences (see below
for which cases it covers and which it can't) — the point is that
testing a future fix means running one small file, not reprocessing
full episodes.

---

## Batch 1 — 2026-08-09, from the first real production-scale run

Source: 326-file batch import of `D:\Nihongo Jikan media\Transcripts\Beginner`
(real content, `NHGJM id00000`–`id00325`, creator `nihongo_jikan`) — see
`Audits/Trigger_Log/` for the run itself. 321/326 imported cleanly;
these 5 failed. This batch is disposable test data and will be purged
before real use — this log is what survives that reset.

### Pattern A — word span absorbs the start of the next word (4 cases)

Every one of these 4 cases has the exact same shape: the parser's word
span for one token extends one extra syllable into the *next* word,
specifically swallowing a leading `だ` from what should be a separate
following word (`だって`/`だから`/`だけど`/`です`-adjacent). Strong
candidate for one shared root cause, not four separate bugs — worth
investigating together.

| # | source_id | original episode | sentence # | bad word (surface / lemma / span) | what got merged in |
|---|---|---|---|---|---|
| 1 | `clean_text_nhgjm-id00056` | `264 - Chatting with My Daughter 娘とおしゃべり.html` | 24 | `繋ぎましょうだ` / `繋ぐ` / [17,25) | `だ` from the following `だって` |
| 2 | `clean_text_nhgjm-id00235` | `711 - No Katakana Game Beginner #1 カタカナ禁止ゲーム 初級#1.html` | 313 | `せです` / `する` / [1,5) | `です` misparsed as part of a `する` conjugation of `せ` (which is a quoted kana character being discussed, not a verb form here) |
| 3 | `clean_text_nhgjm-id00262` | `757 - Two Truths and a Lie 二つの真実と一つの嘘.html` | 88 | `できてだ` / `できる` / [7,12) | `だ` from the following `だから` |
| 4 | `clean_text_nhgjm-id00306` | `862 - Let's Play Neko Odyssey EP04 日本語でゲーム ミキとネコの島 EP04.html` | 250 | `なさいだ` / `なさる` / [5,10) | `だ` from the following `だけど` |

Full sentence text for each (verbatim, real content):

1. `はい「見本と同じ傘はどれですか線で繋ぎましょう」だって。`
2. `「せ」です。`
3. `赤いブツブツができて、だからそれからエビをそのままでは食べてないんですよ。`
4. `」「ごめんなさい」だけど、猫なので、「びっくりしたかニャ？`

These 4 sentences are in `bad_sentences.clean.txt`, ready to run through
the parser directly. **Verified reproduced (2026-08-09)**, not assumed:
ran each sentence individually through the real
`deterministic_parser.parse_job` + `parser_normalizer.canonicalize`
directly — all 4 raise the exact same error as the original real
episode, byte-for-byte, in isolation, confirming these single-sentence
extracts are faithful, minimal repro cases (not dependent on
surrounding context that got lost in extraction).

### Pattern B — response truncated partway through a long file (1 case)

| # | source_id | original episode | response sentences | expected (cleaned-source blocks) |
|---|---|---|---|---|
| 5 | `clean_text_nhgjm-id00297` | `844 - Let's Play Neko Odyssey EP01 日本語でゲーム ミキとネコの島 EP01.html` | 774 | 831 (57 missing) |

The response stops at `...写真を撮ります。` instead of the real ending
`...またね！` (the standard sign-off every other episode in this batch
ends with). Content genuinely got dropped somewhere upstream of the
reconstruction check, not a word-boundary issue — different root cause
from Pattern A, needs its own investigation. **Cannot be reproduced from
an extracted sentence** the way Pattern A can — needs the full original
episode content (`844 - Let's Play Neko Odyssey EP01 日本語でゲーム
ミキとネコの島 EP01.html`, currently renamed to `NHGJM id00297.html` in
`D:\Nihongo Jikan media\Transcripts\Beginner\`) to reproduce, since the
bug is specifically about *where* in a long file things get lost, not
the content of any single sentence.
