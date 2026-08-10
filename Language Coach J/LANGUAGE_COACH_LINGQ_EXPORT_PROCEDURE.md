# LingQ Known-Word Export Procedure

Why this exists: QuadRead's own known-word grading system (Stage 2/3 — see
`LANGUAGE_COACH_OWNER_PROFILE.md`) is a ways off. Until it's built, **LingQ
is the study vehicle** and its own per-word status tracking is the best
available known-word signal — confirmed 2026-08-07. This procedure will
need repeating periodically (Owner keeps studying, status data keeps
changing) until QuadRead's grading stage replaces it. Also stops mattering
once the LingQ subscription expires.

## Why not simpler options (tried and ruled out, 2026-08-07)

- **LingQ's native "Export Selected" CSV** — real, works, but only
  contains `term`/`phrase`/`meaning1-3`. No status field at all. Fine for
  vocabulary/context, useless for known/unknown.
- **The `cards` API pulled via browser navigation + `get_page_text`** —
  works in principle, but that tool truncates at 50,000 characters per
  call regardless of a larger requested limit, and a full record (with
  LingQ's bundled hints/transliteration/readings/etc., which the API's
  `fields=` param does *not* let you strip) runs ~750 bytes each. Pulling
  all ~6,600 records this way would take 100+ round trips. Not worth it.
- **A scripted `fetch()` from Advisor's own browser tool** — blocked
  outright ("Cookie/query string data") as a deliberate safety guard
  against scripts exfiltrating session-authenticated data. Don't try to
  route around this.

**What actually works:** Owner runs the fetch loop themselves, in their
own browser console, on their own logged-in session. Same-origin, real
user action, no restrictions — and it downloads a clean file Advisor can
just read.

## The procedure

1. Owner navigates to the LingQ Vocabulary page (logged in):
   `https://www.lingq.com/en/learn/ja/web/library/vocabulary/all`
2. Open DevTools (F12) → **Console** tab (not Elements — easy to land on
   the wrong tab).
3. Paste this script, press Enter:

```js
(async () => {
  let url = 'https://www.lingq.com/api/v3/ja/cards/?page=1&page_size=500&sort=alpha&status=0&status=1&status=2&status=3&status=4&status=5';
  let all = [];
  while (url) {
    const res = await fetch(url, {credentials: 'include'});
    const data = await res.json();
    for (const r of data.results) {
      all.push({
        term: r.term,
        status: r.status,
        extended_status: r.extended_status,
        importance: r.importance,
        status_changed_date: r.status_changed_date,
        srs_due_date: r.srs_due_date
      });
    }
    url = data.next;
    console.log('fetched', all.length, 'so far...');
  }
  const blob = new Blob([JSON.stringify(all, null, 2)], {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'lingq_cards_full.json';
  a.click();
  console.log('done, total:', all.length);
})();
```

4. It downloads `lingq_cards_full.json` to `C:\Users\Shawn\Downloads\`.
   Tell Advisor it's done; Advisor reads it directly from there.

## Decoding status → known-level (confirmed 2026-08-07, evidence below)

LingQ's UI shows a 1–5 scale (1=just defined ... 4=Known, 5=Mastered/
checkmark), but the raw API fields don't match that directly — this took
real cross-checking to resolve, don't re-guess it:

| Raw `status` | Raw `extended_status` | UI level | Meaning |
|---|---|---|---|
| 0 | any | 1 | Just defined |
| 1 | any | 2 | Toggled once |
| 2 | any | 3 | Toggled again |
| 3 | ≠ 3 | 4 | **Known** |
| 3 | = 3 | 5 | **Mastered** (checkmark; `srs_due_date` pushed out to ~2040) |

**Evidence this is right, not guessed:** filtering the API on
`status=4&status=5` returned exactly 49 records, and every one had
`extended_status: 3` — that count (49) exactly matches
`extended_status==3` in the full pull. Separately, `status==3 &
extended_status!=3` came to exactly 773, which is the same number LingQ's
own UI showed as "Select all 773" when a status-4 filter was active.
Two independent confirmations, not a coincidence.

**Not resolved, don't over-interpret:** `extended_status` also shows up
as `0` (vs. `None`) across status levels 0-2 with no clear pattern found
yet. Doesn't affect the level mapping above, just flagged as an open loose
end.

**Actual distribution from the 2026-08-07 pull (6,633 total):**
level 1: 5,365 · level 2: 304 · level 3: 142 · level 4 (Known): 773 ·
level 5 (Mastered): 49.

## Output

Advisor processes the raw download into
`bootstrap/lingq_known_words.jsonl` — one record per term, with the
decoded `lingq_level` (1-5) instead of the raw status pair, plus
`importance`, `status_changed_date`, `srs_due_date`. The raw download in
`Downloads/` is not kept — only the processed version lives in this
workspace.

**Caveat carried forward:** LingQ's status reflects Owner's own casual
in-app clicking while reading, not the stricter "confident recall out of
context" standard used in the manual `Shawn/teppei_1-50_self_assessment.tsv`
approach. The two aren't measuring the same thing — worth keeping distinct
rather than merging them naively into one "known" number.
