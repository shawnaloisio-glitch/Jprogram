# OC (OpenCode) Session Access Procedure

Referenced from `CLAUDE.md`'s evidence-hierarchy rule: Advisor reads OC's raw
output directly, never OC's own narrative summary or a terminal-display
paste. This file is the durable, standalone record of how to actually do
that, so it doesn't have to be rediscovered each session.

**Owner runs the OpenCode desktop app, not the bare CLI.** This matters —
generic OpenCode documentation describes a flat-file storage layout
(`~/.local/share/opencode/storage/message/{sessionID}/msg_{id}.json`) that
does **not** match what the desktop app actually uses. That layout may be
accurate for CLI-only installs; it was not found on this machine. What was
found and verified instead:

## Storage location

```
C:\Users\Shawn\.local\share\opencode\opencode.db
```

A SQLite database, running in WAL mode (`opencode.db-wal`, `opencode.db-shm`
alongside it). WAL mode means it is safe to open and read while the desktop
app is open and actively writing — readers don't block writers. **Always
connect read-only in spirit: only ever run `SELECT` queries against this
file. Never write to it.**

Discovery path, if this ever needs to be re-derived (e.g. after an OpenCode
update moves things): checked `%APPDATA%\ai.opencode.desktop\` first (found
app-level Electron state, not session content, but confirmed the desktop
app's data root), then checked the OpenCode docs' documented Windows path
(`%USERPROFILE%\.local\share\opencode`) directly — found the real data
there, including this SQLite file, even though the docs describe an older
flat-file layout under that same directory.

## Schema (as verified 2026-08-05)

Relevant tables:

- **`project`** — one row per project OpenCode has opened. Columns include
  `id`, `worktree` (e.g. `C:/AI Development Projects/JapaneseCorpus/JapaneseCorpus`), `name`.
  Find Jprogram's project row by filtering
  `worktree = 'C:/AI Development Projects/JapaneseCorpus/JapaneseCorpus'`. Sessions from before
  the 2026-08-06 relocation have a separate project row with the old
  `worktree = 'C:/Jprogram'` — check both if searching across that date.
- **`session`** — one row per OC session/conversation. Columns include `id`
  (e.g. `ses_02f603404ffeCLdqAMx1LfzJR3`), `project_id` (FK to `project.id`),
  `title` (often auto-generated from the task, e.g. "Fix test isolation in
  preset tests"), `time_created`, `time_updated` (epoch milliseconds — the
  most recently active session for a task is usually the one with the
  highest `time_updated`).
- **`message`** — one row per conversational turn. Columns: `id`,
  `session_id` (FK), `time_created`, `data` (JSON text; parse it — has a
  `role` field, `"user"` or `"assistant"`).
- **`part`** — one row per content block *within* a message. A single
  assistant message can have many parts (reasoning, tool calls, text, step
  markers). Columns: `id`, `message_id` (FK), `session_id` (FK),
  `time_created`, `data` (JSON text). `data.type` is one of:
  - `"text"` — plain assistant/user text; content in `data.text`.
  - `"tool"` — a tool call; `data.tool` is the tool name (`read`, `edit`,
    `bash`, `grep`, `glob`, `question`, etc.), `data.state.status` is
    `"completed"`/`"error"`, `data.state.input` / `data.state.output` hold
    the call's arguments and result.
  - `"reasoning"` — model's internal reasoning text (`data.text`).
  - `"step-start"` / `"step-finish"` — turn boundary markers; `step-finish`
    carries `tokens`/`cost`.
  - `"patch"` — a file-change record; `data.files` lists what changed
    (useful as a second, independent cross-check against `git status`, but
    `git status`/`git diff` remain the primary evidence per the evidence
    hierarchy).

## Use `oc_session_dump.py`, not a hand-rolled script

A real, reusable, tested script lives at `oc_session_dump.py` (repo root).
Built 2026-08-05 after hand-writing this same query inline for TASKs 1-3 —
don't do that again; use the script.

```bash
python oc_session_dump.py                                    # list recent sessions
python oc_session_dump.py <session_id>                       # full transcript
python oc_session_dump.py <session_id> --since <epoch_ms>    # just one task within a reused session
python oc_session_dump.py <session_id> --full <message_id>   # complete text of one part (e.g. a final report)
```

Get a `--since` timestamp by first dumping without it and reading the
`time_created` of the message where the task you care about begins (each
line is printed as `[TYPE message_id @timestamp] ...`).

## Caveats

- **Re-verify this whole procedure if OC's output ever looks empty or
  stale.** The DB path and schema are tied to the specific installed
  OpenCode desktop version; an update could change either. If a query
  that used to work returns nothing, don't assume the session doesn't
  exist — check whether the schema changed first (`PRAGMA table_info(<table>)`
  against each of the tables above).
- The `Local State` / `Local Storage` / `Session Storage` folders alongside
  `opencode.db` in `%APPDATA%\ai.opencode.desktop\` are standard Electron/
  Chromium browser-state files, not session content — ignore them for this
  purpose.
- Per `CLAUDE.md`'s standing sandbox warning: if a fresh session's shell
  reports this path doesn't exist, don't conclude OpenCode was
  reinstalled/reconfigured — first rule out this tool's shell being
  sandboxed from the real filesystem, the same failure mode documented for
  the Qwen Code install check.
