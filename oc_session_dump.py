#!/usr/bin/env python3
"""
oc_session_dump.py

Japanese Corpus Pipeline - Advisor tooling.

Reads OC (OpenCode desktop) session data directly from its SQLite store,
per the procedure documented in OC_Session_Access_Procedure.md. Exists so
this doesn't get hand-rolled as an inline one-off script every time a
Coder task needs evaluating.

This is read-only against the OpenCode database (SELECT only) and makes
no changes to Jprogram itself.

Usage:
    python oc_session_dump.py
        List recent Jprogram sessions (id, title, last-updated), newest
        first. Use this to find the session id you want.

    python oc_session_dump.py <session_id>
        Dump the full text/tool-call transcript for that session.

    python oc_session_dump.py <session_id> --since <epoch_ms>
        Dump only the parts created at or after the given timestamp
        (milliseconds since epoch, matching the session/message/part
        tables' own time_created values) -- useful for pulling just one
        TASK out of a session OC continued reusing across multiple tasks.
        Get a starting timestamp by first dumping without --since and
        reading the time_created of the message where your task begins.

    python oc_session_dump.py <session_id> --full <message_id>
        Print the complete, untruncated text of one specific part (e.g.
        a final report) rather than the abbreviated per-line view.

Requires no third-party packages (sqlite3, json, argparse are stdlib).
"""

import argparse
import io
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
JPROGRAM_WORKTREE = "C:/Jprogram"


def _utf8_stdout():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    elif hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def _connect():
    if not DB_PATH.is_file():
        raise SystemExit(
            f"OpenCode database not found at {DB_PATH}. If this path has "
            f"changed (e.g. after an OpenCode update), re-verify per "
            f"OC_Session_Access_Procedure.md before assuming OC isn't "
            f"installed -- this tool's own shell/environment can be stale "
            f"or sandboxed (see CLAUDE.md)."
        )
    return sqlite3.connect(str(DB_PATH))


def list_sessions(limit=15):
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT id FROM project WHERE worktree = ?", (JPROGRAM_WORKTREE,))
    row = cur.fetchone()
    if row is None:
        print(f"No OpenCode project found for worktree {JPROGRAM_WORKTREE!r}.")
        con.close()
        return
    project_id = row[0]
    cur.execute(
        "SELECT id, title, time_created, time_updated FROM session "
        "WHERE project_id = ? ORDER BY time_updated DESC LIMIT ?",
        (project_id, limit),
    )
    for sid, title, created, updated in cur.fetchall():
        print(f"{sid}  updated={updated}  {title!r}")
    con.close()


def dump_session(session_id, since=None):
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "SELECT id, message_id, time_created, data FROM part "
        "WHERE session_id = ? ORDER BY time_created",
        (session_id,),
    )
    rows = cur.fetchall()
    con.close()

    if not rows:
        print(f"No parts found for session {session_id!r}. Check the id is "
              f"correct (run with no arguments to list sessions).")
        return

    for _pid, mid, tc, data in rows:
        if since is not None and tc < since:
            continue
        d = json.loads(data)
        t = d.get("type")
        if t == "text":
            text = d.get("text", "")
            print(f"[TEXT {mid} @{tc}] {text[:300]!r}")
        elif t == "tool":
            state = d.get("state", {})
            print(f"[TOOL {mid} @{tc}] tool={d.get('tool')} "
                  f"status={state.get('status')} "
                  f"input={json.dumps(state.get('input', {}))[:250]}")
        elif t in ("step-start", "step-finish", "patch", "reasoning"):
            continue  # noise for evaluation purposes; use --full for a specific part if needed
        else:
            print(f"[{t} {mid} @{tc}] keys={list(d.keys())}")


def dump_full_part(session_id, message_id):
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "SELECT data FROM part WHERE session_id = ? AND message_id = ? "
        "ORDER BY time_created",
        (session_id, message_id),
    )
    rows = cur.fetchall()
    con.close()
    if not rows:
        print(f"No parts found for message {message_id!r} in session "
              f"{session_id!r}.")
        return
    for (data,) in rows:
        d = json.loads(data)
        if d.get("type") == "text":
            print(d.get("text", ""))


def main():
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__.split("Usage:")[0])
    parser.add_argument("session_id", nargs="?", default=None)
    parser.add_argument("--since", type=int, default=None,
                        help="epoch-ms timestamp; only show parts at/after this time")
    parser.add_argument("--full", metavar="MESSAGE_ID", default=None,
                        help="print the complete untruncated text of one message's part(s)")
    args = parser.parse_args()

    if args.session_id is None:
        list_sessions()
        return

    if args.full:
        dump_full_part(args.session_id, args.full)
        return

    dump_session(args.session_id, since=args.since)


if __name__ == "__main__":
    main()
