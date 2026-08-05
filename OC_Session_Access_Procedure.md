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
  `id`, `worktree` (e.g. `C:/Jprogram`), `name`. Find Jprogram's project row
  by filtering `worktree = 'C:/Jprogram'`.
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

## Example: dump a full session transcript

```python
import sqlite3, json

DB = r"C:\Users\Shawn\.local\share\opencode\opencode.db"

con = sqlite3.connect(DB)  # read-only in practice: only SELECT below
cur = con.cursor()

# 1. Find the Jprogram project id
cur.execute("SELECT id FROM project WHERE worktree = 'C:/Jprogram'")
project_id = cur.fetchone()[0]

# 2. Find the session (adjust title match / ordering as needed)
cur.execute(
    "SELECT id, title FROM session WHERE project_id = ? "
    "ORDER BY time_updated DESC LIMIT 10",
    (project_id,),
)
for row in cur.fetchall():
    print(row)  # eyeball this to pick the right session id

session_id = "ses_..."  # paste the chosen id

# 3. Walk every part in time order — this is the full raw transcript
cur.execute(
    "SELECT message_id, data FROM part WHERE session_id = ? "
    "ORDER BY time_created",
    (session_id,),
)
for message_id, data in cur.fetchall():
    d = json.loads(data)
    t = d.get("type")
    if t == "text":
        print(f"[TEXT {message_id}] {d.get('text')}")
    elif t == "tool":
        st = d.get("state", {})
        print(f"[TOOL {message_id}] {d.get('tool')} "
              f"status={st.get('status')} input={st.get('input')}")
        # st.get('output') has the full result if you need it

con.close()
```

Run this with the project's own Python (no extra install — `sqlite3` and
`json` are both standard library).

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
