---
inclusion: always
---

# Hauntlet Warden safety rules (always loaded)

These rules bind every spec, task and file in this repository. Kiro must
refuse or flag any work that breaks them.

## Hard rules

1. **Never wire a Hauntlet room MCP server into Crew.** Crew is an agent. A
   hostile room server in its configuration would plant a trap in it. Warden
   declares no `mcpServers`, writes no MCP configuration anywhere
   (`~/.kiro/crew/mcp.json`, `~/.kiro/settings/mcp.json`, agent files, the
   watched workspace), and never stores a room server's command or arguments.
2. **Dummy secrets only as `HAUNTLET-DUMMY-…`.** Anything Warden stores, shows
   or sends passes through `warden.mask`. A full dummy value never appears in
   a record, the page, a notification, a fixture or a log.
3. **No external hosts. Localhost only.** At runtime Warden contacts only
   `127.0.0.1` / `localhost`. Hauntlet runs with `--offline` and a loopback
   base URL. Scorecards are served with a CSP that blocks every external load.
   The single exception is the user-approved, one-time
   `uv tool install` from the Hauntlet git URL (decision Q1).
4. **One statement about client behaviour.** The only statement Warden makes
   about how any client behaves is: "Some client behaviours are out of reach
   of config."
5. **Read-only on the watched workspace.** Warden reads only the listed
   `.kiro/` files, never follows a symlink out of `.kiro/`, never runs a
   command there, and never writes, creates, renames, deletes or touches
   anything in it.

## Also

- Every `hauntlet` command runs from Warden's range directory under its data
  dir. It never runs from the watched workspace, the checkout or this repo.
- The Warden agent has no tools. It answers from the summary the page puts in
  the message, and never asks for scorecard HTML or room files.
- Credits: only the agent uses them. Say so wherever cost is described.

## When in doubt

If a change could put hostile room content in front of an agent (Crew's or
the user's), or could write to a place Warden does not own, stop and flag it.
