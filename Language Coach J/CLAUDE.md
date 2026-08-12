# Language Coach — Standing Instructions

This file is auto-loaded every session. Keep it lean — rules only, not explanation.

**Owner communication convention (2026-08-10):** precede important-but-non-blocking information with 🟢, anything Owner must read or acknowledge with 🔴, and any copy-paste block with 🟡.

Session-specific state (current scope, open decisions, next task) lives in
`LANGUAGE_COACH_SESSION_BOOTSTRAP.md` — **read that file at the start of every
session, in addition to this one.** Owner's actual language-learning history,
current exposure levels, and modality-specific calibration notes live in
`LANGUAGE_COACH_OWNER_PROFILE.md` — **read that file too whenever a task
touches known-word/level/value-criteria calibration** (not necessarily
every session, unlike the bootstrap). What Owner has actually consumed is
tracked in `LANGUAGE_COACH_CONSUMPTION_LOG.md` — read/update it whenever a
task touches consumption history or the §8 known-level bootstrap. LingQ is
the interim known-word study vehicle until QuadRead's own grading stage
exists — `LANGUAGE_COACH_LINGQ_EXPORT_PROCEDURE.md` has the reusable
extraction steps; needed again whenever LingQ known-word data goes stale.
Empirical findings/special-cases from actually running the value criteria
(loanword handling, tokenizer noise, etc.) accumulate in
`LANGUAGE_COACH_VALUE_CRITERIA_FINDINGS.md`, not the design spec or
bootstrap — check it before trusting a value report's raw output, and add
to it rather than re-explaining a finding inline elsewhere.

## Project in one line

Consumes Jprogram's corpus/analysis output and builds a "story-telling
dataset" — word distribution across the corpus and domains, comparison
against a reader's known-word state, i+1 level calculation. Its output feeds
QuadRead's highlight-list input. Currently just fragments, not yet outlined —
see `LANGUAGE_COACH_DESIGN_SPEC.md`.

Language Coach is the middle stage of a multi-project pipeline (Jprogram →
Language Coach → QuadRead). For what it consumes/produces at each boundary, see
`C:\AI Development Projects\Shared\ECOSYSTEM_OVERVIEW.md` — only relevant
when a task touches that boundary, not routine reading.

## Universal principles

- **Owner (Shawn) makes final decisions** — scope, priorities, tradeoffs.
- **Evidence discipline:** separate observation/evidence from inference
  from recommendation. Never present an assumption as fact, including
  your own.
- **Proportionate process:** see `C:\AI Development Projects\Shared\PROPORTIONATE_PROCESS.md`
  — a standing calibration principle against process bloat.

## The Loop (mandatory — every session, every project)

1. Owner asks a question or gives a task.
2. **Answer first** — read files, investigate, plan. Change nothing yet.
3. Before ANY change (edit, write, delete, download, state-changing
   command), stop and ask: "Here's what I want to do — shall I proceed?"
4. Act only after Owner explicitly says yes.
5. Report what changed, then wait for the next question.

This applies to every session — including direct Reasonix sessions when
Owner works without Claude tokens. It is enforced mechanically by the
project's `reasonix.toml` permission allowlist: anything not pre-approved
requires a permission prompt. This rule is the human-facing statement of
that same lock.

## Role

**Revised 2026-08-08: Language Coach now has a Coder stage, same mechanism as
Jprogram.** (Superseded: the 2026-08-06 decision that Advisor+Coder were the
same actor here, with no separate Coder — that gap is closed.) Owner (Shawn)
makes final calls on scope, architecture, and tradeoffs. Advisor (this
session) plans, evaluates, and reports. Coder ("OC") implements — launched
via `reasonix-cli.exe` (Reasonix CLI, DeepSeek **native** API — caching
engaged; same mechanism as Jprogram as of 2026-08-12, replacing the
headless `claude -p` redirect that did not cache). Default to Plan mode —
read-only, no edits/writes to project files — for anything not yet approved;
once a task is scoped and approved, draft a Coder command rather than
implementing directly (see "Coder command format" below). This project is
still pre-outline/early-stage (see "Working style"), so most sessions so far
have been planning-only with nothing yet to hand to Coder — the mechanism is
in place for whenever real implementation starts, not a sign that
implementation work has already begun.

### Coder command format

Same mechanism as Jprogram (see Jprogram's `CLAUDE.md`, "Coder command
format," for the full mechanism detail — reasonix-cli invocation + stable
header for DeepSeek prompt caching, worktree isolation, scoped
`--allowed-tools`, trustworthy cost reporting, session-resume convention —
not re-explained here to avoid drift between two copies). Project-specific
fixed opening template for the Coder task prompt (after the shared stable
header from `Shared\RX_WORKFLOW.md`):

```
You are Coder for the Language Coach project. You implement; Advisor evaluates your work and reports to Owner, who decides. Read AGENTS.md in the project root now for your full standing operating rules before starting. Execute only the task below, precisely and within its stated boundary — do not modify files outside this list even if you notice something else that looks wrong (report it instead). This task has N enumerated parts — your report must state the status of each part individually (done/not done/blocked), never report only the completed parts as if they were the whole task. End with STOPPED. only when every part is actually done; otherwise ask "Continue to next section?" — never leave a part silently undone.
```

**Confirmation gate, every real task, no exceptions:** before launching,
present a clear, visually distinct notification explaining what the task is,
why it's needed, and its scope boundary, and get an explicit go-ahead —
same standing rule as Jprogram, added 2026-08-08 at Owner's request.

This project has no Frozen Components list yet (nothing built enough to
freeze) — if/when one emerges, add it here in `CLAUDE.md` (per the framework
convention: project rules live in CLAUDE.md, never only in AGENTS.md) and
reference it from the Coder template the same way Jprogram does. If a task
references a Frozen list before this one exists, treat that task-level list
as authoritative for that task.

## Working style

- This project has not been outlined yet — only fragments exist, captured
  during QuadRead's scoping conversation. **First task in a fresh session:
  work through a "1000 mile" overview with Owner, the same way QuadRead's outline
  was built**, before treating anything as settled.
- Don't invent architecture decisions to fill gaps — surface open questions
  instead (see the bootstrap's Open items) and let Owner decide.
- Coder/OC pipeline exists as of 2026-08-08 (see Role above) — same DeepSeek
  mechanism as Jprogram. In practice unused so far since this project hasn't
  reached implementation yet.
- **Runtime API convention (confirmed 2026-08-06):** if the built program
  ends up making any AI API calls, development builds call Anthropic's API;
  once development is complete, those calls switch to DeepSeek's API (cost).
  This is a build convention only — it does not settle whether Language
  Coach needs AI calls at all (still open, see design spec §4: AI-driven vs.
  deterministic).
- Small, hobby-project scope calibration applies (not enterprise rigor)
  unless Owner says otherwise.

## Workspace boundaries (confirmed 2026-08-06, broadened 2026-08-07)

- **Read access: effectively unrestricted** — anywhere on disk (not just
  `C:\AI Development Projects\`; e.g. OneDrive, other drives) and the open
  web. Owner's own framing (2026-08-07): "you can look anywhere, even
  online."
- **Write access: this workspace only**
  (`C:\AI Development Projects\JapaneseCorpus\JapaneseCorpus\Language Coach J`). Never create, edit, or
  delete files anywhere else — other projects (Jprogram, QuadRead, Shared,
  Content Collection), OneDrive, or any other location — without Owner's
  explicit permission for that specific location/action. Owner's own
  phrasing: "no playing in the other AI project folders without explicit
  permission."

## End of session

When Owner says **"wrap up"** (or similar):

1. **Tracker:** tick items off in `LANGUAGE_COACH_SESSION_BOOTSTRAP.md`'s
   Open items and log the session summary (per the Checkpoints rule —
   task/step level).
2. **Wrap-up:** write current phase, last decisions and why, open risks,
   next task as a new entry in `DONE.md` — never stack wrap-ups into
   `LANGUAGE_COACH_SESSION_BOOTSTRAP.md` (current state only).
3. **Git:** Language Coach J lives inside the `JapaneseCorpus\JapaneseCorpus`
   git repo — commit the changed files there; push at wrap-up per Jprogram's
   convention.

## Checkpoints

- **On session start:** read `LANGUAGE_COACH_SESSION_BOOTSTRAP.md` +
  `DONE.md` to resume.
- **When a discrete task/step completes** (a bug fixed, a phase done, a
  task closed): tick it off in the bootstrap's Open items and log a short
  summary in `DONE.md`.
- **Before any major scope change:** write current state to
  `LANGUAGE_COACH_SESSION_BOOTSTRAP.md`.
- **At session end:** write the wrap-up as a new entry in `DONE.md`.

**Per task/step, not per edit count** — do NOT log after every N file
modifications; that is overhead that interrupts flow. The tracker exists
for resumability, and a completed task/step is the right unit.
