"""
build_library_db.py — build the SQLite query library from analyzer outputs.

Source of truth stays the JSON analyzer outputs (tools/analysis/outputs/).
This script imports them (plus catalog metadata + known words) into a
SQLite database for fast cross-cutting queries ("top unknown in Beginner",
"pieces sharing vocab with X", "pieces closest to my level").

Ownership (Owner structural change 2026-08-09): Language Coach owns
everything downstream of the corpus — analyzers, filter, reports, and this
library. Jprogram stops at the parser output.

Usage:
    python build_library_db.py [--rebuild]

Metadata join at import (revised 2026-08-09 — match Jprogram, not content format):
    - analyzer outputs      -> counts (frequency/exposure/chunks)
    - source_metadata.csv   -> Jprogram's authoritative metadata backbone
                              (source_name/creator/material_level/style_id/
                              topic_id/duration_seconds/episode_number/season_number)
    - material_level code   -> tier name (Jprogram mapping: 1=Complete Beginner,
                              2=Beginner, 3=Intermediate, 4=Advanced)
    - rename_log.csv        -> human title
    - NJ catalog            -> enrichment only (difficulty/teacher), may be NULL
    - lingq_known_words     -> known-word gate (LingQ now; Reasonix later)

Schema:
    sources(source_id PK, title, tier, difficulty, teacher, series,
            sentences, words, chunks, expressions)
    frequency(source_id, surface, occurrences)          -- idx (surface), (source_id)
    exposure(source_id, surface, first_seen, gap_mean)  -- idx (surface)
    chunks(source_id, chunk_text, occurrences)
    known_words(surface PK, source)   -- 'lingq' now; 'reasonix' later
"""

import csv
import json
import os
import re
import sqlite3
import sys

ANALYSIS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library.db")
# Japanese: canonical corpus is JapaneseCorpus's output (JAPANESECORPUS_WORKSPACE env or default).
CORPUS_DIR = os.path.join(
    os.environ.get("JAPANESECORPUS_WORKSPACE", r"C:\AI Development Projects\JapaneseCorpus\Workspace"),
    "jsonl",
)
RENAME_LOG = os.path.join(CORPUS_DIR, "rename_log.csv")
SOURCE_METADATA = os.path.join(CORPUS_DIR, "source_metadata.csv")
NJ_CATALOG = r"C:\AI Development Projects\Content Collection\nihongo-jikan\catalog\nj_catalog.tsv"
# Known-word gate file lives at the project root's bootstrap/ — this script
# sits at tools/analysis/, so walk up three dirnames (LCT's copy only walks
# two and resolves to a non-existent tools/bootstrap/ — not mirrored).
LINGQ = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     "bootstrap", "lingq_known_words.jsonl")
KNOWN_LEVEL = 4

# Jprogram's material_level code -> tier name (verified from Jprogram's own
# tests: 1=Complete Beginner, 2=Beginner; 3/4=Intermediate/Advanced per the
# same ladder; 0 = unset/unknown).
MATERIAL_LEVEL_NAMES = {
    "": None, "0": None, "1": "Complete Beginner", "2": "Beginner",
    "3": "Intermediate", "4": "Advanced",
}


def load_metadata():
    """source_metadata.csv (Jprogram's authoritative metadata) by source_id."""
    m = {}
    if not os.path.exists(SOURCE_METADATA):
        return m
    with open(SOURCE_METADATA, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            m[row["source_id"]] = row
    return m


def load_rename_map():
    """rename_log.csv: 'NHGJM idNNNNN.html' -> (nj_id, real_title)"""
    m = {}
    if not os.path.exists(RENAME_LOG):
        return m
    with open(RENAME_LOG, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            new = row["new_name"].replace(".html", "")
            real = row["real_name"].replace(".html", "")
            mid = re.match(r"^(\d+) - ", real)
            m["clean_text_" + new.lower().replace(" ", "-")] = (int(mid.group(1)) if mid else None, real)
    return m


def load_nj_catalog():
    """NJ catalog id -> {level, difficulty, teacherIds, series} — enrichment only."""
    cat = {}
    if not os.path.exists(NJ_CATALOG):
        return cat
    with open(NJ_CATALOG, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            cat[row["id"]] = row
    return cat


def load_known():
    known = set()
    if not os.path.exists(LINGQ):
        return known
    with open(LINGQ, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("lingq_level", 0) >= KNOWN_LEVEL:
                known.add(r["term"])
    return known


def build(rebuild=False):
    if os.path.exists(DB_PATH) and not rebuild:
        print(f"library.db already exists ({os.path.getsize(DB_PATH)/1e6:.0f} MB). Use --rebuild to rebuild.")
        return
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    metadata = load_metadata()
    rename = load_rename_map()
    catalog = load_nj_catalog()
    known = load_known()

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE sources(
            source_id TEXT PRIMARY KEY,
            source_name TEXT,          -- Jprogram metadata: NHGJM idNNNNN
            title TEXT,                -- human title (rename_log)
            creator TEXT,              -- Jprogram metadata: nihongo_jikan
            material_level INTEGER,    -- Jprogram metadata code (0-4)
            tier TEXT,                 -- derived from material_level
            style_id TEXT, topic_id TEXT,
            duration_seconds REAL, episode_number TEXT, season_number TEXT,
            difficulty REAL,           -- enrichment (NJ catalog), may be NULL
            teacher TEXT,              -- enrichment (NJ catalog), may be NULL
            sentences INTEGER, words INTEGER, chunks INTEGER, expressions INTEGER
        );
        CREATE TABLE frequency(source_id TEXT, surface TEXT, occurrences INTEGER);
        CREATE INDEX idx_freq_surface ON frequency(surface);
        CREATE INDEX idx_freq_source ON frequency(source_id);
        CREATE TABLE exposure(source_id TEXT, surface TEXT, first_seen TEXT, gap_mean REAL);
        CREATE INDEX idx_exposure_surface ON exposure(surface);
        CREATE TABLE chunks(source_id TEXT, chunk_text TEXT, occurrences INTEGER);
        CREATE INDEX idx_chunks_source ON chunks(source_id);
        CREATE TABLE known_words(surface TEXT PRIMARY KEY, source TEXT);
    """)

    files = sorted(f for f in os.listdir(ANALYSIS_DIR) if f.endswith(".analysis.json"))
    n = 0
    for f in files:
        source_id = f[: -len(".analysis.json")]
        with open(os.path.join(ANALYSIS_DIR, f), encoding="utf-8") as fh:
            d = json.load(fh)

        meta = metadata.get(source_id, {})
        nj_id, title = rename.get(source_id, (None, source_id))
        cat = catalog.get(str(nj_id), {}) if nj_id else {}
        ml = (meta.get("material_level") or "").strip()
        tier = MATERIAL_LEVEL_NAMES.get(ml)

        freq = d["frequency"]["frequency"]
        sm = d["sentence_metrics"].get("by_source", {}).get(source_id, {})
        cur.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (source_id, meta.get("source_name"), title, meta.get("creator"),
             int(ml) if ml.isdigit() else None, tier,
             meta.get("style_id"), meta.get("topic_id"),
             meta.get("duration_seconds"), meta.get("episode_number"), meta.get("season_number"),
             cat.get("difficulty"), cat.get("teacherIds"),
             sm.get("sentences", 0), sm.get("words", 0),
             sm.get("chunks", 0), sm.get("expressions", 0)))
        cur.executemany(
            "INSERT INTO frequency VALUES (?,?,?)",
            [(source_id, s, info["occurrences"]) for s, info in freq.items()])
        exp = d["exposure"]["exposure"]
        cur.executemany(
            "INSERT INTO exposure VALUES (?,?,?,?)",
            [(source_id, s, json.dumps(info.get("first_seen"), ensure_ascii=False),
              (info.get("distribution", {}).get("word_distance", {}) or {}).get("mean"))
             for s, info in exp.items()])
        ch = d["chunk"]["chunks"]
        cur.executemany(
            "INSERT INTO chunks VALUES (?,?,?)",
            [(source_id, c, info["occurrences"]) for c, info in ch.items()])
        n += 1

    cur.executemany("INSERT INTO known_words VALUES (?,?)", [(w, "lingq") for w in known])
    con.commit()
    con.close()
    print(f"imported {n} sources -> {DB_PATH} ({os.path.getsize(DB_PATH)/1e6:.0f} MB)")
    print(f"  known words: {len(known)} (lingq level>={KNOWN_LEVEL})")


if __name__ == "__main__":
    build(rebuild="--rebuild" in sys.argv)
