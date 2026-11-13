---
inclusion: always
---

# Product

**Hauntlet Warden** (`hauntlet-warden`) is a Kiro Crew app built for the Best
Kiro Crew App bonus. It watches two things:

- **The Hauntlet range itself.** Every night it runs Hauntlet's model-free
  checks: `hauntlet selftest`, then the `naive` and `hardened` reference agents
  in every room, then `hauntlet exorcist demo` for every room the demo
  supports. It stores worst level, pass^k, detected, task and the report path.
- **One workspace's guardrails.** It compares that workspace's `.kiro/` with
  the guardrails the Exorcist demo generates, and reports what is missing or
  weaker, file by file. It never writes to that workspace.

A dashboard page shows the history, the drift and links to the local
scorecards. An "Ask Warden" button opens a chat with the Warden agent, seeded
with the latest summary. Notifications fire only when something changes.

- **Users:** Hauntlet maintainers and teams who applied Exorcist guardrails
  and want to know when a range result or a guardrail drifts.
- **Not:** an attack tool, a way to run Hauntlet rooms against Crew itself, or
  a writer of anyone's `.kiro/`.
- **Credits:** only the Warden agent uses credits (one turn per question).
  The nightly run, drift check, backend and page call no model.
- **Spec:** `.kiro/specs/warden/` (requirements, design, tasks).
