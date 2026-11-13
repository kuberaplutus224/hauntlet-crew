# Hauntlet Warden

A [Kiro Crew](https://kiro.dev/docs/crew/apps/) app that keeps watch over
[Hauntlet](https://github.com/kuberaplutus224/hauntlet), the haunted house
for AI agents. It watches two things:

1. **The range itself.** Every night at 03:00 local time, Warden runs
   Hauntlet's model-free checks: `hauntlet selftest`, then the `naive` and
   `hardened` reference agents in every room, then the Exorcist demo for
   every room that has one. It stores each room's worst level, pass^k,
   detected and task rates, and the path of the local scorecard.
2. **One workspace's guardrails.** Warden compares the workspace's `.kiro/`
   (steering, hooks, `settings/mcp.json`, `settings/sandbox.json`) with the
   guardrails the Exorcist demo generates. It reports what is missing or
   weaker, file by file. It is read-only: it never writes to that workspace.

The **Warden** page in the dashboard shows the history, the drift and links
to the scorecards. A notification appears only when something changes.

Built for Kiroween 2026 (Best Kiro Crew App). The spec is in
`.kiro/specs/warden/`.

## What it costs

| Part | Calls a model? |
|---|---|
| Nightly run (a script cron) | No |
| Run now, drift check, the page, the backend | No |
| **Ask Warden** (the Warden agent) | **Yes, one agent turn per question** |

The agent is the only part that uses credits. A scheduled run's row on the
Schedule page shows elapsed time and no credits.

## Install

Requirements: Kiro Crew 0.12.2 or newer, `uv`, and a local Hauntlet
checkout. Run `uv sync` in the checkout once.

```bash
kirocrew app install /path/to/hauntlet-crew
```

Then open **Apps → Library**, find **Hauntlet Warden** and choose **Enable**.
Crew asks you to trust this app, because it runs a Python backend and a script
cron. Third-party apps cannot be enabled from the CLI while
`agent.apps_allow_third_party` is off, so use the dashboard.

`ui/dist/index.mjs` is committed. Crew does not build `ui/` on install. After
changing `ui/src/`, run `cd ui && npm install && npm run build` and commit
the result.

## Settings

Open **Warden** in the sidebar. The settings panel opens until Warden is
configured.

| Setting | Meaning |
|---|---|
| Hauntlet checkout | Absolute path to your local Hauntlet clone. Its `pyproject.toml` must declare the project `hauntlet` |
| Watched workspace | Optional. The workspace whose `.kiro/` Warden compares, read-only |
| Rooms | Which of the six rooms to run. All six by default. Drift uses the five that have an Exorcist demo (not `parlor`) |
| Repeats per agent (k) | 1–10, default 3. Hauntlet prints pass^k for k = 1, 2, 4, 8 up to this number, so at 3 the headline is **pass^2**. The page labels the k |
| Hauntlet source | `local checkout` now. `installed from GitHub` becomes available from 2026-12-04 (see below) |

The nightly job ships **paused**. Once the settings are valid, press **Turn on
nightly check**, or press **Run now** to run once immediately.

### The schedule and the 03:00 reset

The job is `nightly-range-check`, at `0 3 * * *` in local time with no random
start delay. You can change the time on Crew's **Schedule** page. Disabling
and re-enabling the app re-creates its jobs from `app.json`, which **resets
the time to 03:00** and pauses the job again. Re-apply your change
afterwards.

### How Hauntlet is run

Each command is an argument list (no shell) of the form:

```
uv run --offline --project <checkout> hauntlet …
```

Every command runs from Warden's own range directory. It never runs from
the watched workspace or the checkout, because Hauntlet writes room files to
`./.hauntlet/scratch/`. It uses an absolute `HAUNTLET_DB` and
`HAUNTLET_BASE_URL=http://127.0.0.1:8666`, and it first removes any inherited
`HAUNTLET_*` and `RENDER_*` variables.

`--offline` means a run never reaches PyPI. If the checkout is not synced,
the run reports "Hauntlet checkout is not synced: run `uv sync` in
<checkout>" and sends one notification.

**Why `--offline --project` and not `--no-sync`:** `uv run` keeps the
checkout's own `.venv` in step with its lock file, and may update that
`.venv` (which the checkout's `.gitignore` excludes). `--no-sync` would leave
it untouched, but it could silently run a stale environment and report wrong
results. That is worse. Warden writes nothing else in the checkout.

### Where things are kept

| What | Where |
|---|---|
| Warden's records: settings, run history, drift, reference, summary | `~/.kiro/crew/apps/hauntlet-warden/data/warden/` (the app's data dir) |
| The range directory: Hauntlet's store, room scratch files, scorecards, Exorcist bundles | macOS: `~/Library/Application Support/hauntlet-warden/range/`. Linux: `$XDG_DATA_HOME/hauntlet-warden/range/` (default `~/.local/share/hauntlet-warden/range/`) |

The range directory is outside `~/.kiro` on purpose. Hauntlet's Exorcist
refuses to write anywhere under a `.kiro` directory, and Crew installs apps
under `~/.kiro/crew/apps/`.

**Uninstalling the app leaves the range directory in place**, because it is
not inside the app's data dir. Delete it yourself afterwards:

```bash
rm -rf ~/Library/Application\ Support/hauntlet-warden          # macOS
rm -rf "${XDG_DATA_HOME:-$HOME/.local/share}/hauntlet-warden"  # Linux
```

### Installing from GitHub (from 2026-12-04)

Once the Hauntlet repository is public, the settings panel offers **Install
Hauntlet from GitHub**. Tick **I approve this one-time download** and press
**Install**. Warden runs `uv tool install` from
`git+https://github.com/kuberaplutus224/hauntlet` once, into its own data
directory. After that, runs use the installed tool offline. This click is the
only time Warden contacts a host other than localhost.

## Notifications

One line on the dashboard's notifications panel, only when something changed
since the previous run:

- a room's worst level changed, for either agent;
- the selftest started failing, or recovered;
- a run had an error that differs from the previous run's (for example an
  unsynced checkout or a timeout);
- a guardrail became missing or weaker in the watched workspace.

The first run is a silent baseline, except for a failing selftest or a run
error. If Slack is configured in Crew, a copy may also go to your Slack DM.

## Ask Warden

**Ask Warden** opens a chat with the Warden agent. The latest summary is
already in the message, and you type your question after it. The agent has
**no tools**. It answers from that summary only, cannot open files or start
runs, and points you to **Run now** for a new run. Crew's cron tools cannot
see app-owned jobs, and file reads would need an approval in every session.
Seeding the chat avoids both.

## Safety rules

These are in `.kiro/steering/safety-rules.md` and enforced by tests:

1. **No Hauntlet room MCP server in Crew.** Crew is an agent, and a hostile
   server in its configuration would plant a trap in it. Warden declares no
   MCP servers, writes no MCP configuration, and never stores a room server's
   command.
2. **Dummy secrets show only as `HAUNTLET-DUMMY-…`**, in records, on the
   page, in notifications and in the summary.
3. **Localhost only.** Runs are offline, and the backend listens on loopback.
   Scorecards are served with a security header that blocks every external
   load. The scorecard's Alpine.js request is blocked on purpose: the
   scorecard is built to work without scripts.
   The one exception is the approved GitHub install above.
4. **One statement about client behaviour:** "Some client behaviours are out
   of reach of config."
5. **Read-only on the watched workspace.** Warden reads only the listed
   `.kiro/` files and does not follow symlinks out of `.kiro/`.

## Decisions

| | Decision |
|---|---|
| Q1 | The GitHub source is an opt-in: installed once after your approval, then offline. The localhost rule covers Warden's runtime traffic. The checkout is the default until 2026-12-04 |
| Q2 | `--offline`, with a clear "run `uv sync`" message when the checkout is not synced. Keep `--offline --project`, not `--no-sync` (see above) |
| Q3 | A Slack copy of a notification is acceptable when Slack is configured |
| Q4 | A run error and a selftest recovery both count as changes and notify |
| Q5 | The schedule resets to 03:00 on disable/enable. No undocumented API is used to avoid that |
| Q6 | Drift covers the five rooms that have an Exorcist demo |
| Q7 | `repeat` defaults to 3, so the headline is pass^2 |
| Agent | The page seeds the chat with the summary. The agent has no tools |

## Development

```bash
uv sync && uv run pytest          # backend, drift, parser and property tests; no Crew or Hauntlet needed
cd ui && npm install && npm run build
npm run preview:build             # a local preview with mock data (git-ignored output)
```

The layout:
- `warden/` holds all the logic, using the standard library only.
- `backend/nightly.py` is the script cron.
- `backend/server.py` is the loopback backend.
- `ui/` is the page.
- `agents/` and `skills/` hold the agent and its skill.

## License

MIT
