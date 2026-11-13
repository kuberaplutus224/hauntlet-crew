# Implementation Plan — warden

## Overview

The order is: spike first (it can change the run path), then repo scaffolding
and steering, then the pure `warden` package with its tests, then the thin
cron/backend shells, the UI, the agent and skill, and a manual install check.
Nothing is committed. Every Hauntlet command in development runs from a
throwaway range directory, never from this repo, the checkout or a watched
workspace.

## Tasks

- [x] 1. Spike: verify the source-observed Crew behaviour (design.md "Spike findings")
  - [x] 1.1 Manifest script cron: registers paused, runs on trigger, passes the vet. `import warden` needs the app root on `sys.path`
  - [x] 1.2 Cron child: data-dir writes, `uv` on PATH and `--offline` selftest all work. The child inherits the gateway's env and cwd. The context does not expose the trigger
  - [x] 1.3 `ctx.notify` reaches the dashboard notifications
  - [x] 1.4 Backend: binds `PORT`. Proxy path is `/api/<x>`. Headers are `X-KiroCrew-Proxy` and `-V2` + `-Nonce` (not the docs' `X-Crew-Proxy`). Secret from `KIROCREW_PROXY_SECRET`
  - [x] 1.5 UI: list, run and enable/pause of the app's own job via `/api/crons` work
  - [x] 1.6 `useAppApi` needs `/apps/hauntlet-warden/api` in `permissions.api`
  - [x] 1.7 Bullet order equals item order. `DATA` has two texts. Bundles live in `<range>/.hauntlet/exorcist/`
  - [x] 1.8 Agent: `cron_*` MCP tools cannot see app jobs, and `fs_read` needs approval. Decided: option A (design.md "Agent: decision")
  - [x] 1.9 Findings written, throwaway app uninstalled, data removed, gateway stopped
  - _Requirements: 2.2, 2.8, 6.6, 7.3, 8.1, 8.2, 11.1_

- [x] 2. Repository scaffolding, steering and hook
  - [x] 2.1 `pyproject.toml` (package `warden`, Python ≥ 3.12, no runtime deps, dev: pytest, hypothesis), `LICENSE` (MIT), `.gitignore` (`.venv`, `__pycache__`, `.pytest_cache`, `.hypothesis`, `ui/node_modules`)
  - [x] 2.2 `.kiro/steering/product.md`, `tech.md`, `safety-rules.md` (`inclusion: always`). `safety-rules.md` holds the five rules from the request plus "Credits: only the agent and skill"
  - [x] 2.3 `.kiro/hooks/kiro-usage-log.json` created with the `createHook` tool, matching `../hauntlet/.kiro/hooks/kiro-usage-log.json`, and `docs/kiro-usage-log.md`
  - _Requirements: 13.1, 13.2, 10.6_

- [x] 3. Fixtures
  - [x] 3.1 Golden outputs in `tests/fixtures/outputs/`, captured from real runs in a throwaway range dir (run, run --repeat 3, selftest pass, a synthesised selftest FAILED stderr, demo for each demo room)
  - [x] 3.2 Trimmed bundles for all five demo rooms, with `mcp.json` server `command`/`args`/`env` replaced by `"<redacted>"`
  - [x] 3.3 Workspaces `complete/`, `empty/`, `weaker/`, `hostile/`. The symlink and the 2 MiB file in `hostile/` are created by a pytest fixture at test time, not committed
  - _Requirements: 12.2_

- [x] 4. `warden` core (pure), each with its unit and property tests
  - [x] 4.1 `mask.py` + `test_mask.py` (P8)
  - [x] 4.2 `paths.py`, `settings.py` + tests (validation, refusals of Requirement 8.3)
  - [x] 4.3 `commands.py` + `test_commands.py` (P9; no `--directory`; `git` refused)
  - [x] 4.4 `parse.py` + `test_parse.py` (golden, P1, P2)
  - [x] 4.5 `reference.py` + `test_reference.py` (no server command or args kept; bundle path containment)
  - [x] 4.6 `readonly.py` + `test_readonly.py` (P7, hostile fixture)
  - [x] 4.7 `drift.py` + `test_drift.py` (every rule in "Drift rules", P3, P4, Hauntlet-server warning)
  - [x] 4.8 `changes.py` + `test_changes.py` (P5, baseline rule, skipped/not_configured, workspace change, ≤ 200 chars)
  - [x] 4.9 `store.py` + `test_store.py` (P6, prune scope, lock → skipped, summary.md)
  - [x] 4.10 `execute.py`, `runner.py` + tests with a fake executor (order, continue-on-failure, per-command timeout, time budget)
  - _Requirements: 2.4–2.7, 3, 4, 5, 6.1–6.5, 10.2, 10.5_

- [x] 5. Cron entry and backend
  - [x] 5.1 `backend/nightly.py:run(ctx)`, using the trigger detection from spike 1.2
  - [x] 5.2 `warden/proxyauth.py` + `test_proxyauth.py` (valid, stale, tampered body, wrong path)
  - [x] 5.3 `backend/server.py` routes (including `GET /api/summary` for "Ask Warden") + `test_server_routes.py` (auth on every route except `/health`, report-name guard, CSP headers, unmasked-dummy refusal, settings validation, body size cap)
  - _Requirements: 2.2, 6.2, 6.6, 7.5, 8_

- [x] 6. Manifest and content tests
  - [x] 6.1 `app.json` as in design.md, adjusted by the spike findings
  - [x] 6.2 `test_manifest.py` (D5, D7, D8, D11, S1, S2, S4, the exact permissions, no `mcpServers`/`setup`/`mcpTools`/`backend.routes`, Crew 0.12.2's own `AppManifest.validate()` when Crew is installed). The existence checks for `agents/warden.json`, `skills/warden` and `ui/dist/index.mjs` skip until tasks 7–8 create them
  - [x] 6.3 `test_content.py` (Requirement 12.5)
  - _Requirements: 1, 10, 12.3, 12.5_

- [x] 7. Dashboard page
  - [x] 7.1 `ui/` Vite project with the externals of D16, `src/api.ts` (paths from the spike), `App.tsx`, the rooms, drift and settings panels, SVG charts, and the "Ask Warden" button (`useChatLauncher`; check its argument shape on the 0.12.2 host)
  - [x] 7.2 `npm install && npm run build` → `ui/dist/index.mjs` (to be committed by you; not committed here). `tests/test_ui.py` checks the bundle statically: only host externals, a default export, built from the current source, the scorecard colours, Ask Warden not auto-sent, no absolute URLs
  - _Requirements: 7, 1.6_

- [x] 8. Agent, skill and README (option A, design.md "Agent: decision")
  - [x] 8.1 `agents/warden.json` with `"tools": []` and the option-A prompt. Confirm the registered file in `~/.kiro/agents/` after `kirocrew app update`
  - [x] 8.2 `skills/warden/SKILL.md`: answer from the summary in the message, send the user to the page when there is none, "Run now" is the page button
  - [x] 8.3 `test_agent_skill.py` (JSON fields, empty `tools`, frontmatter, the approved sentence, the credit note, no instruction to open `range/` or HTML)
  - [x] 8.4 `README.md` (what it does, credits, install, settings, the 03:00 reset, why `--offline --project` and not `--no-sync`, safety rules, the Q decisions)
  - _Requirements: 9, 11, 1.8_

- [x] 9. Checkpoint: full suite and manual install
  - [x] 9.1 `uv run pytest` is green
  - [x] 9.2 `kirocrew app install .` → enable → page loads → settings saved → "Turn on nightly check" → `kirocrew cron trigger <id>` → the record and charts appear and no credits are shown on the run row
  - [x] 9.3 Force a change (point the watched workspace at the `weaker/` fixture copy). Expect exactly one notification. Rerun unchanged. Expect no notification
  - [x] 9.4 Confirm the watched workspace is unchanged (`find … -newer` marker file) and that no MCP server was added to Crew's config (`kirocrew` MCP list before and after)
  - [x] 9.5 Report results. Do not commit
  - _Requirements: all_

## Task Dependency Graph

Task 1 (spike) is done and is not listed. Tasks in one wave do not depend on
each other. Each wave depends only on earlier waves.

```json
{
  "waves": [
    { "id": 0, "tasks": ["2.1", "2.2", "2.3"] },
    { "id": 1, "tasks": ["3.1", "3.2", "3.3", "4.1", "4.2", "5.2", "6.1"] },
    { "id": 2, "tasks": ["4.3", "4.4", "4.5", "4.6", "4.9"] },
    { "id": 3, "tasks": ["4.7", "4.10"] },
    { "id": 4, "tasks": ["4.8"] },
    { "id": 5, "tasks": ["5.1", "5.3"] },
    { "id": 6, "tasks": ["6.3", "7.1"] },
    { "id": 7, "tasks": ["7.2", "8.1", "8.2"] },
    { "id": 8, "tasks": ["6.2", "8.3", "8.4"] },
    { "id": 9, "tasks": ["9.1"] },
    { "id": 10, "tasks": ["9.2"] },
    { "id": 11, "tasks": ["9.3", "9.4"] },
    { "id": 12, "tasks": ["9.5"] }
  ]
}
```

Why each task sits in its wave:
- 4.3 needs 4.2 (settings, paths). 4.4 needs 3.1 (golden outputs). 4.5 needs
  3.2 (bundles). 4.6 needs 3.3 (workspaces). 4.9 needs 4.1 and 4.2.
- 4.7 needs 4.5 and 4.6. 4.10 needs 4.3 and 4.4.
- 4.8 needs the record and drift models from 4.7 and 4.9.
- 5.1 needs 4.8, 4.9 and 4.10. 5.3 needs 4.7, 4.9 and 5.2.
- 7.1 needs the routes from 5.3. 6.3 scans the code from waves 2–5.
- 6.2 checks that `ui/dist/index.mjs` (7.2), the agent (8.1) and the skill
  (8.2) exist.

## Notes

- **Agent:** option A. The agent has no tools. The page seeds the chat with
  the summary, and "Run now" is a page button.
- **Not committed:** nothing in this spec's execution is committed.
  `ui/dist/index.mjs` (7.2) must be committed by you, because Crew does not
  build `ui/` on install.
- **Credits:** only an agent turn uses credits. No task in this plan runs the
  agent, so executing the plan spends none. Testing the agent by hand after
  task 8 costs one turn per question.
- **Range directories:** every Hauntlet command in development and tests runs
  from a throwaway directory under `/tmp`, never from this repo, the checkout
  or a watched workspace. The test suite needs neither Hauntlet nor Crew
  (Requirement 12.1).
- **Spike leftovers:** Crew keeps its own records of the spike: two cron
  history entries for job `03fce83c`, two dashboard notifications and one
  memory-history line. Warden does not touch them.
- **Docs vs 0.12.2:** where the installed Crew differs from the docs
  (proxy header names, `PORT`, MCP cron tool scope), the design follows the
  verified behaviour and records both. Re-check them on a Crew upgrade.
  - Task 9 found that Hauntlet's Exorcist refuses a range dir under `.kiro`; the range dir moved to the platform user-data location (design.md "Findings during task 9"), with `tests/test_paths.py`
