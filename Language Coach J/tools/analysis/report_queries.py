"""
report_queries.py — standard report queries for Language Coach.

The default path for "show me the value candidates" questions. Combines
the SQLite library (fast cross-cutting queries) with the deterministic
candidate filter, so every report is clean by default.

Usage (chat-driven):
    from report_queries import top_unknown

    top_unknown(tier='Beginner', limit=20)                 # all Beginner pieces
    top_unknown(source='clean_text_nhgjm-id00123')         # one piece
    top_unknown(session=['id00123', 'id00456'])            # a bounded session set

Ownership (Owner 2026-08-09): reports are saved queries delivered in
chat; the one file artifact is the per-episode reader package (built
elsewhere, see the LC->Reasonix handoff item).
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import candidate_filter as cf

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library.db")


def _connect():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"{DB_PATH} missing — run build_library_db.py first")
    return sqlite3.connect(DB_PATH)


def _source_filter(tier=None, source=None, session=None):
    """Build WHERE clause + params for sources selection."""
    where, params = [], []
    if tier:
        where.append("s.tier = ?")
        params.append(tier)
    if source:
        where.append("s.source_id = ?")
        params.append(source)
    if session:
        where.append("s.source_id IN (%s)" % ",".join("?" * len(session)))
        params.extend(session)
    return (" AND " + " AND ".join(where)) if where else "", params


def top_unknown(tier=None, source=None, session=None, limit=20, include_katakana=True, known_sql=None):
    """
    Top unknown surfaces (filtered) ranked by occurrences.

    Returns list of (surface, occurrences, source_count).
    """
    sf, params = _source_filter(tier, source, session)
    con = _connect()
    cur = con.cursor()
    rows = cur.execute(f"""
        SELECT f.surface, SUM(f.occurrences) AS occ, COUNT(DISTINCT f.source_id) AS nsrc
        FROM frequency f JOIN sources s ON f.source_id = s.source_id
        WHERE f.surface NOT IN (SELECT surface FROM known_words){sf}
        GROUP BY f.surface ORDER BY occ DESC, nsrc DESC LIMIT 1000
    """, params).fetchall()
    con.close()
    clean = [(w, o, n) for w, o, n in rows
             if not cf.is_shape_noise(w)
             and (include_katakana or not __import__('re').fullmatch(r'[\u30A0-\u30FFー]+', w))]
    return clean[:limit]


def known_coverage(tier=None, source=None, session=None, limit=20):
    """Per-source known-coverage ranking (easiest first)."""
    sf, params = _source_filter(tier, source, session)
    con = _connect()
    cur = con.cursor()
    rows = cur.execute(f"""
        SELECT s.source_id, s.title, s.tier,
               100.0 * (SELECT COUNT(DISTINCT f.surface) FROM frequency f
                        WHERE f.source_id = s.source_id
                          AND f.surface IN (SELECT surface FROM known_words))
                      / (SELECT COUNT(DISTINCT f.surface) FROM frequency f
                         WHERE f.source_id = s.source_id) AS pct
        FROM sources s
        WHERE 1=1{sf}
        ORDER BY pct DESC LIMIT {int(limit)}
    """, params).fetchall()
    con.close()
    return rows


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Value-candidate report queries")
    ap.add_argument("--tier", help="filter by tier (Beginner/Intermediate/...)")
    ap.add_argument("--source", help="single source_id")
    ap.add_argument("--session", nargs="*", help="bounded session: list of source_ids")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--coverage", action="store_true", help="known-coverage ranking instead")
    a = ap.parse_args()
    if a.coverage:
        for sid, title, tier, pct in known_coverage(a.tier, a.source, a.session, a.limit):
            print(f"{pct:5.1f}%  [{tier}] {title}")
    else:
        for i, (w, o, n) in enumerate(top_unknown(a.tier, a.source, a.session, a.limit), 1):
            print(f"{i:>3}. {w} ({o} occ, {n} sources)")
