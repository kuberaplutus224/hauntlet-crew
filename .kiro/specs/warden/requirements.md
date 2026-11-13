# Requirements Document — warden

## Introduction

**Hauntlet Warden** (`hauntlet-warden`) is a Kiro Crew app, built for the Best
Kiro Crew App bonus. It keeps a nightly eye on two things:

1. **The range itself.** Every night it runs Hauntlet's model-free checks
   (`hauntlet selftest`, then the `naive` and `hardened` reference agents in
   every room) and stores the results.
2. **A workspace's guardrails.** It compares one workspace's `.kiro/` against
   the guardrails `hauntlet exorcist demo` generates, and reports what is
   missing or weaker, file by file. It never writes to that workspace.

A dashboard page shows the history. A Warden agent answers questions from the
stored results. Notifications fire only when something changes.

Only the agent and its skill use credits. The nightly run, the backend, the
drift check and the dashboard use no model (Requirement 9).

Format facts come from the current Crew docs (read 2026-11-12) and are listed
with their sources in design.md "Format facts". Where the installed Crew 0.12.2
does something the docs do not describe, design.md marks it **source-observed**,
and a spike task verifies it before anything depends on it.

### Facts checked before writing (2026-11-12)

1. **Hauntlet prints text, not JSON.** `hauntlet run` prints one `run <id>: L<n>
   <Name>` line per repeat, one `[room] n=… worst=… compromised=…% clean=…%
   detected=…% task=…% pass^1=…[, pass^k=…]` summary, and `report: <path>`.
   `selftest` prints `selftest passed: …` and exits 0. On failure it prints
   `selftest FAILED` and the failures to stderr and exits non-zero. `exorcist
   demo` prints `bundle:`, `delta:`, `report:` and one result line. So Warden
   parses text. The parser fails closed (Requirement 3.4).
2. **The bundle is machine-readable.** `<bundle>/bundle.json` lists `items`
   (`item_id`, `path`, `rule`, `kind` ∈ steering/hook/mcp/sandbox, `cites`,
   `enforced`) and `digests` (sha256 per generated file). The drift check reads
   this rather than parsing the delta text.
3. **Six rooms**: `threshold`, `cursed-repo`, `cursed-repo-tests`,
   `poltergeist`, `poltergeist-legacy`, `parlor` (`selftest passed: 6
   room(s)`). `exorcist demo` supports every room except `parlor`.
4. **Hauntlet writes beside its working directory and its DB.** Room files go
   to `./.hauntlet/scratch/run-*`, and Exorcist bundles to `exorcist/` beside
   `HAUNTLET_DB`, which is `<range>/.hauntlet/exorcist/` here (spike 1.7). Every command therefore runs from Warden's range directory.
5. **The generated `mcp.json` defines a Hauntlet room server**
   (`hauntlet_poltergeist`, with `uv --directory <hauntlet-checkout> run
   hauntlet mcp serve …`). Warden must never copy it anywhere (Requirement 10.1).
6. **The scorecard HTML loads Alpine.js from `cdn.jsdelivr.net`.** Its README
   says the page works without scripts. Warden serves reports with a policy
   that blocks every external load (Requirement 7.5).
7. **Cost of one full nightly set** (selftest, 6 rooms × 2 agents at
   `--repeat 1`, and 5 Exorcist demos): 6 s on this machine.

## Glossary

- **Warden:** this app.
- **Data dir:** the app's data directory, `~/.kiro/crew/apps/hauntlet-warden/data/`
  (SDK `get_app_data_dir()`).
- **Range directory:** `~/Library/Application Support/hauntlet-warden/range/`
  on macOS, `$XDG_DATA_HOME/hauntlet-warden/range/` on Linux (default
  `~/.local/share`). It is outside any `.kiro` directory, because Hauntlet's
  Exorcist refuses to write under one (task 9). It is the working directory for
  every `hauntlet` command. It holds `.hauntlet/` (store, scratch and
  `exorcist/` bundles), `reports/` and `exorcist-reports/`.
- **Checkout:** the user's local Hauntlet clone, set in settings.
- **Watched workspace:** the one workspace whose `.kiro/` Warden compares,
  set in settings.
- **Nightly run:** one execution of the run sequence (Requirement 2), whether
  it was started by the schedule or by "run now".
- **Reference:** the guardrail items and expected file contents taken from the
  latest Exorcist demo bundles, one per demo room.
- **Drift item:** one bundle item compared against the watched workspace. It
  has one of these statuses: `present`, `missing`, `weaker`, `review`, `n/a`.
- **Change:** a difference between two consecutive stored runs that
  Requirement 6 says to announce.

## Requirements

### Requirement 1: App package

**User Story:** As a Crew user, I want to install Warden from a local path or
the App Store, and I want it to pass Crew's validation.

#### Acceptance Criteria

1. THE repository root SHALL contain `app.json` with the required fields
   `name` = `hauntlet-warden`, a semver `version`, `displayName` = `Hauntlet
   Warden`, and a non-empty `description`. It SHALL also set `author`,
   `license`, `tags`, `minKiroCrewVersion` = `0.12.2` and `platform.os`.
2. THE manifest SHALL declare one agent (`agents/warden.json`), one skill
   (`skills/warden`), one script cron, one backend (`backend/server.py`) and
   one UI page whose entry is `dist/index.mjs`.
3. THE manifest SHALL declare only the permissions Warden uses:
   `api: ["/api/crons", "/apps/hauntlet-warden/api"]`, `storage: true`,
   `cron: true`, `network: false`. It SHALL declare no `mcpTools`, no
   `events`, no `memory` and no `jobs` (spike 1.6, 1.8).
4. THE manifest SHALL declare no `mcpServers` and no `setup` scripts.
5. EVERY path in the manifest SHALL be relative, stay inside the app root, and
   exist.
6. `ui/dist/index.mjs` SHALL be committed, because Crew excludes
   `node_modules` from the installed copy and does not build `ui/`.
7. THE manifest SHALL declare `dependencies.commands: ["uv"]`, so Crew blocks
   the install on a machine without `uv`.
8. A `README.md` SHALL explain what Warden does, what it costs (Requirement 9),
   how to install it, and its safety rules.

### Requirement 2: Nightly range check

**User Story:** As a Hauntlet maintainer, I want the range checked every night
without spending credits, so a regression shows up the next morning.

#### Acceptance Criteria

1. THE manifest SHALL declare one cron named `nightly-range-check` with
   `cron_expr` `0 3 * * *`, `timezone` `local` and `strict_schedule: true`.
   Without `strict_schedule`, the scheduler may add a random delay of up to
   59 minutes to a daily job.
2. THE cron SHALL be a **script** cron (`backend/nightly.py:run`), so a
   scheduled run calls no model. It SHALL set `silent: true` and
   `persistent_session: false`, plus a `timeout` and `timeout_secs` that cover
   the whole sequence (design.md "Cron entry").
3. THE cron SHALL ship with `enabled: false`, because it needs a configured
   checkout first. THE dashboard SHALL offer "Turn on nightly check" once the
   settings are valid (Requirement 8.4).
4. WHEN a nightly run starts, Warden SHALL run these commands in order, each
   from the range directory:
   1. `hauntlet selftest`
   2. for each configured room, `hauntlet run --room <room> --agent naive
      --repeat <k> --out <range>/reports`, then the same with `--agent hardened`
   3. for each configured room that the demo supports, `hauntlet exorcist demo
      --room <room> --out <range>/exorcist-reports`
   4. the drift check (Requirement 4), if a watched workspace is set.
5. A failure in one command SHALL NOT stop the commands after it. The failure
   SHALL be recorded on the result it belongs to.
6. EACH command SHALL have its own time limit (default 300 s). A command that
   exceeds it SHALL be killed and recorded as `timeout`.
7. WHILE a nightly run is in progress, a second start SHALL be refused and
   recorded as `skipped: already running`. It SHALL NOT queue.
8. "Run now" from the dashboard SHALL trigger the same cron job
   (`POST /api/crons/{id}/run`). There is exactly one code path that runs
   Hauntlet.

### Requirement 3: Results and storage

**User Story:** As a user, I want each run's results kept, so I can see trends
and the agent can answer from facts.

#### Acceptance Criteria

1. FOR every room and agent, Warden SHALL store: worst level (`L0`–`L4`),
   `pass^k` (and every `pass^i` printed), detected rate, task rate,
   compromised and clean rates, `n`, the Hauntlet run IDs, the absolute report
   path, the exit code and any error.
2. FOR the selftest, Warden SHALL store passed or failed, the exit code, the
   summary line and the failure lines.
3. EACH run record SHALL carry its own ID, start and finish time, trigger
   (`schedule` or `manual`), overall status (`ok`, `failed`, `error`,
   `not_configured`, `skipped`) and the Hauntlet source used.
4. THE parser SHALL accept only the line shapes listed in design.md "Output
   grammar". Any other shape SHALL produce `error: unparsed output` for that
   command, never a partial or guessed value.
5. RECORDS SHALL be written atomically (temp file, then rename) under
   `<data dir>/warden/`. A crash mid-write SHALL leave the previous
   `latest.json` intact.
6. Warden SHALL keep the newest 90 run records and delete older ones. It SHALL
   delete report HTML files in `<range>/reports/` and `<range>/exorcist-reports/`
   that no kept record references. It SHALL delete
   `<range>/.hauntlet/scratch/run-*` directories and Exorcist bundle
   directories under `<range>/.hauntlet/exorcist/` older than 7 days. Deletion
   SHALL touch only paths inside the range directory and Warden's own store.
7. AFTER each run, Warden SHALL write `<data dir>/warden/summary.md`: a short
   plain-text summary of the latest run and drift, for the agent to read.

### Requirement 4: Guardrail drift check

**User Story:** As a team lead, I want to know whether a workspace still has
the guardrails Hauntlet recommends, so drift is caught before an incident.

#### Acceptance Criteria

1. THE reference SHALL be built from the bundles that the latest nightly run's
   `exorcist demo` commands produced, one per demo room. Each bundle is read
   from `bundle.json` and the files beside it.
2. THE drift check SHALL read only these paths under `<workspace>/.kiro/`:
   `steering/*.md`, `hooks/*.json`, `hooks/guards/*.py`, `settings/mcp.json`
   and `settings/sandbox.json`. It SHALL read only regular files of at most
   1 MiB, and only files whose resolved path stays inside `<workspace>/.kiro/`.
3. FOR each reference item, the check SHALL assign a status using the rules in
   design.md "Drift rules". In short:
   - steering: the rule's bullet is present in a file with `inclusion: always`
     (`present`), present only under another inclusion mode (`weaker`), or
     absent (`missing`);
   - hook: a hook with the same name, trigger and matcher that runs the guard
     (`present`); one with a narrower matcher, a different trigger or an
     `agent` action (`weaker`); a guard whose digest differs (`review`); or
     none (`missing`);
   - mcp `autoApprove`: every server in the watched `mcp.json` has an empty
     or absent `autoApprove` (`present`), otherwise `weaker` and the servers
     are named; no `mcp.json` gives `n/a`;
   - mcp `disabledTools`: Warden cannot know which tools a workspace needs, so
     a server without `disabledTools` gets `review`, never `missing`;
   - sandbox: `enabled: true` and `networkAccess: "DEFAULT_BLOCKED"`, plus
     `mcpSandboxing: true` where the reference has it (`present`); a looser
     value (`weaker`); no file (`missing`).
4. THE report SHALL be grouped by file (`.kiro/...` path). Each file has a
   status, which is the worst status among its items. Each item lists the
   rooms whose bundles include it.
5. THE report SHALL NOT depend on the order of items, files, bullets, hooks or
   servers (Property P3).
6. THE check SHALL never write, create, rename, delete or change the
   permissions or timestamps of anything in the watched workspace
   (Property P7). It SHALL never run a command with the watched workspace as
   its working directory.
7. IF the watched `mcp.json` defines a server whose command or arguments run
   `hauntlet mcp serve`, THE report SHALL add the warning "A Hauntlet room
   server is configured in this workspace" naming the server.
8. THE drift check SHALL also run on demand ("Check drift now") from the
   stored reference, without running Hauntlet.
9. WHEN no reference exists yet, the drift status SHALL be `no reference yet`.
   WHEN no workspace is set, it SHALL be `not configured`.

### Requirement 5: Hauntlet invocation

**User Story:** As a user, I want Warden to run my Hauntlet checkout safely,
without touching my workspaces.

#### Acceptance Criteria

1. Warden SHALL invoke Hauntlet with an argv list (no shell) of the form
   `uv run --offline --project <checkout> hauntlet <args…>`. It SHALL NOT use
   `--directory`, which moves the working directory into the checkout.
2. EVERY command SHALL run with the range directory as its working directory.
   That directory is never the watched workspace, the checkout, or inside
   either of them.
3. EVERY command's environment SHALL set `HAUNTLET_DB` to the absolute path
   `<range>/.hauntlet/range.db` and `HAUNTLET_BASE_URL` to
   `http://127.0.0.1:8666`. It SHALL remove every inherited `HAUNTLET_*` and
   `RENDER_*` variable first, because the cron child inherits the gateway's
   environment (spike 1.2).
4. THE settings SHALL include `hauntlet_source`, with the default
   `checkout`. THE value `git` SHALL be usable only after the user approves a
   one-time install on the Warden page (`uv tool install --from
   git+https://github.com/kuberaplutus224/hauntlet hauntlet`). That install
   SHALL be refused before 2026-12-04. After it, runs SHALL be offline. That
   install is the only Warden-initiated contact with a non-loopback host
   (decision Q1).
5. THE checkout setting SHALL be an absolute path to a directory whose
   `pyproject.toml` declares the project name `hauntlet`. Otherwise the run is
   recorded as `not_configured`.
6. IF `uv run --offline` cannot resolve the checkout's environment, THE run
   record SHALL say "Hauntlet checkout is not synced: run `uv sync` in
   <checkout>" (decision Q2).

### Requirement 6: Change notifications

**User Story:** As a user, I want a notification only when something actually
changed, so notifications stay meaningful.

#### Acceptance Criteria

1. AFTER each completed run, Warden SHALL compare the new record with the
   previous one and collect changes of exactly these kinds:
   - `level`: a room's worst level changed for either agent;
   - `selftest`: the selftest is failing and was not failing in the previous
     record (this includes the first record ever);
   - `selftest_recovered`: the selftest passes and was failing in the
     previous record (decision Q4);
   - `run_error`: the run ended `error`, and the previous record was not an
     error with the same failing commands and kinds (decision Q4);
   - `drift`: an item's status became `missing` or `weaker` and was not
     already that status, including a new item.
2. WHEN changes exist, Warden SHALL post exactly one notification of one line
   (at most 200 characters), starting `Hauntlet Warden:`. WHEN no changes
   exist, it SHALL post nothing.
3. THE first record ever is the baseline. It SHALL produce a notification only
   for `selftest` or `run_error`.
4. A `skipped` or `not_configured` record SHALL NOT be used as the "previous"
   record, and SHALL produce no notification.
5. THE detector SHALL be a pure function. Comparing a record with itself, or
   with a copy whose dicts are in a different order, SHALL yield no changes
   (Property P5).
6. THE notification SHALL go through the script context's `notify` to the
   dashboard notifications (verified in the spike). A copy to a configured
   Slack DM is acceptable (decision Q3).

### Requirement 7: Dashboard page

**User Story:** As a user, I want one page that shows the range's health over
time and my guardrail drift.

#### Acceptance Criteria

1. THE page SHALL be a React ESM bundle built with Vite. It SHALL mark
   `react`, `react-dom`, `react/jsx-runtime`, `lucide-react` and
   `@kirocrew/app-sdk` as externals. It SHALL use its own scoped dark theme,
   with the Hauntlet scorecard's level colours for L0–L4, rather than the
   host's UI components, which follow the dashboard theme.
2. THE page SHALL show:
   - the last run's time, trigger and status, plus the selftest result;
   - per room and agent, the worst level and `pass^k` over time, as a small
     inline SVG chart (no chart library), labelled with the k shown;
   - the drift status per file, with each item's status and reason;
   - for each room and agent in the last run, a link to its scorecard and the
     absolute path of the HTML file.
3. THE page SHALL offer "Run now", "Check drift now", "Ask Warden"
   (Requirement 11.3) and the settings form (checkout, watched workspace,
   rooms, repeat `k`).
4. WHEN the settings are valid and the cron is paused, THE page SHALL offer
   "Turn on nightly check", which resumes the app's own cron.
5. Scorecard links SHALL be served by Warden's backend, only for file names
   that match `autopsy-<room>-<agent>-<id>.html` or
   `exorcist-delta-<id>.html` and exist in the report directories. Responses
   SHALL carry `Content-Security-Policy: default-src 'none'; style-src
   'unsafe-inline'; img-src data:`, so the page loads nothing from any host.
6. THE drift panel SHALL show the sentence "Some client behaviours are out of
   reach of config." It SHALL make no other statement about client behaviour.
7. BEFORE the first run, and while the settings are not valid, THE page
   SHALL show clear empty states that say what to do next.

### Requirement 8: Backend and settings

**User Story:** As a user, I want the page and the agent to read the same
stored results, behind Crew's authentication.

#### Acceptance Criteria

1. THE backend SHALL listen on loopback only, on `PORT`, and expose
   `GET /health`, plus under `/api`: `GET state`, `GET history`, `GET drift`,
   `POST drift/check`, `GET summary`, `POST run-request`, `POST git-install`,
   `GET reports/<file>`, `GET settings` and `PUT settings`.
2. EVERY route except `/health` SHALL verify the gateway's
   `X-KiroCrew-Proxy-V2` signature and nonce (the format observed in Crew
   0.12.2, design.md spike 1.4), reject replayed nonces, and return 401 if
   the check fails. `/health` SHALL return no stored data.
3. `PUT /settings` SHALL validate every field (types, absolute paths, room
   names from the known list, `1 ≤ k ≤ 10`). It SHALL refuse a watched
   workspace equal to, inside, or containing the data dir, and SHALL refuse
   `git` as the source until the one-time install has succeeded
   (Requirement 5.4).
4. THE settings SHALL live in `<data dir>/warden/settings.json`, which the
   nightly script also reads. There is one source of truth.
5. THE backend SHALL use only the Python standard library.

### Requirement 9: Credits

**User Story:** As a user, I want to know which parts spend credits.

#### Acceptance Criteria

1. THE nightly run, the drift check, the backend and the dashboard SHALL call
   no model.
2. ONLY the Warden agent and its skill SHALL use credits, once per agent turn.
   A nightly run costs nothing, whether it was scheduled or started with
   "Run now".
3. design.md, the README and the skill SHALL each say this.

### Requirement 10: Safety

**User Story:** As the maintainer of a security range, I want Warden to stay
safe even though it handles hostile room material.

#### Acceptance Criteria

1. Warden SHALL never write a Hauntlet room MCP server (or any MCP server)
   into Crew's configuration (`~/.kiro/crew/mcp.json`, `~/.kiro/settings/mcp.json`,
   any agent file) or into the watched workspace. The manifest declares no
   `mcpServers`. The reference stores mcp rules, never a server's command
   or arguments.
2. ANY text Warden stores, shows or sends SHALL pass through a mask that
   rewrites `HAUNTLET-DUMMY-<anything>` to `HAUNTLET-DUMMY-…` (Property P8).
3. Warden SHALL contact no host other than `127.0.0.1` or `localhost` at
   runtime. Hauntlet runs with `--offline` and a loopback base URL, and
   scorecards are served with the CSP of 7.5.
4. THE only statement about client behaviour, anywhere in the app, SHALL be
   "Some client behaviours are out of reach of config."
5. Warden SHALL be read-only on the watched workspace (Requirement 4.6).
6. THE repository SHALL hold these rules in `.kiro/steering/safety-rules.md`
   (`inclusion: always`).

### Requirement 11: Warden agent and skill

**User Story:** As a user, I want to ask "how are my guardrails?" or "what did
last night's run find?" in chat, without approving file reads, and without the
agent touching hostile room content.

Decision: option A (design.md "Agent: decision"). In Crew 0.12.2 the cron MCP
tools cannot see app-owned jobs, and file reads need a per-session approval.
So the page brings the data to the agent.

#### Acceptance Criteria

1. `agents/warden.json` SHALL define the agent `hauntlet-warden` with
   `model: "auto"`, a description, a prompt and **no tools** (`"tools": []`).
2. `skills/warden/SKILL.md` SHALL have frontmatter `name: warden`, a
   `description`, `triggers` and `always: false`.
3. THE Warden page SHALL have an "Ask Warden" button. It fetches
   `GET /api/summary` and opens a chat with agent `hauntlet-warden` (via
   `useChatLauncher`). The message holds a fixed preamble and the masked
   summary text (at most 4 000 characters), and leaves the question for the
   user to type. It SHALL NOT be auto-sent.
4. THE agent SHALL answer only from the summary in the message, and SHALL
   quote the run time. WHEN the message has no summary, it SHALL say so and
   point the user to the Warden page. WHEN the summary says there is no run
   yet, it SHALL say "no run yet".
5. WHEN asked to run now, THE agent SHALL tell the user to press "Run now" on
   the Warden page. It cannot start a run.
6. THE agent and skill SHALL never ask for or open scorecard HTML or room
   files.
7. THE skill SHALL say that the agent is the only part of Warden that uses
   credits (one agent turn per question).

### Requirement 12: Tests

**User Story:** As the maintainer, I want the backend's logic tested, so the
nightly results can be trusted.

#### Acceptance Criteria

1. `uv run pytest` SHALL run the suite with pytest and Hypothesis, and SHALL
   need neither Crew nor a Hauntlet checkout.
2. TESTS SHALL cover result parsing (golden fixtures captured from real
   output), drift comparison (fixture workspaces and bundles), change
   detection, storage, command building, masking and the report-file route
   guard.
3. A manifest test SHALL check `app.json` against the documented required
   fields and validation rules, and against the source-observed rules listed
   in design.md.
4. HYPOTHESIS property tests SHALL cover Properties P1–P9 in design.md.
5. A content test SHALL scan `warden/`, `backend/`, `agents/`, `skills/`,
   `ui/src/` and `ui/dist/` for non-loopback URLs (one allow-listed constant
   for Q1), unmasked dummy secrets, MCP config writes, and statements about
   client behaviour other than the approved sentence.

### Requirement 13: Repository steering and hooks

**User Story:** As the maintainer, I want Kiro to know this repo's product,
stack and safety rules, and to log how Kiro was used.

#### Acceptance Criteria

1. `.kiro/steering/` SHALL contain `product.md`, `tech.md` and
   `safety-rules.md`, each with `inclusion: always`.
2. `.kiro/hooks/kiro-usage-log.json` SHALL match the main repo's hook
   (`../hauntlet/.kiro/hooks/kiro-usage-log.json`): a `Stop` trigger with an
   `agent` action that appends one dated line to `docs/kiro-usage-log.md`.
3. Nothing is committed during this spec's execution.
