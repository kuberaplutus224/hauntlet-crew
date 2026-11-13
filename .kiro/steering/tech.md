---
inclusion: always
---

# Tech

- **Target:** Kiro Crew 0.12.2 (`minKiroCrewVersion`), macOS and Linux. Where
  the installed Crew differs from its docs (proxy header names, `PORT`, MCP
  cron tool scope), follow the verified behaviour in
  `.kiro/specs/warden/design.md` "Spike findings", and record both.
- **Python 3.12, standard library only at runtime.** The `warden/` package
  holds all logic and is pure where possible. `backend/nightly.py` (the script
  cron) and `backend/server.py` (a loopback `ThreadingHTTPServer`) are thin
  shells over it.
- **Dev tooling:** `uv`, pytest and Hypothesis. Run `uv run pytest`. Tests
  need neither Crew nor a Hauntlet checkout.
- **UI:** React ESM built with Vite into `ui/dist/index.mjs`, which is
  committed. Externals are `react`, `react-dom`, `react/jsx-runtime`,
  `lucide-react` and `@kirocrew/app-sdk`. Charts are hand-written SVG.
- **Hauntlet invocation:** an argv list, never a shell. The form is
  `uv run --offline --project <checkout> hauntlet …`, run from
  `<data dir>/range/`, with an absolute `HAUNTLET_DB` and
  `HAUNTLET_BASE_URL=http://127.0.0.1:8666`. Every inherited `HAUNTLET_*` and
  `RENDER_*` variable is removed first. Never use `--directory`.
- **Storage:** JSON files under `<data dir>/warden/`, written atomically
  (temp file, fsync, `os.replace`).
- **Backend auth:** verify `X-KiroCrew-Proxy-V2` with its nonce (replay
  cache, ±60 s). `/health` is the only unauthenticated route.
- **Commands:** `uv run pytest` · `kirocrew app install .` ·
  `kirocrew app info hauntlet-warden`.
- **License:** MIT.
