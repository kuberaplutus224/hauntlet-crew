"""The nightly-range-check script cron (app.json ``script: backend/nightly.py:run``).

Crew runs ``run(ctx)`` with no model, so a scheduled run costs no credits. The cron
child starts with ``sys.path[0]`` set to this ``backend/`` directory and with the
gateway's working directory and environment (spike 1.1, 1.2). So this file adds the
app root to the import path, and every command sets its own cwd and env.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from warden import changes, runner, settings, store  # noqa: E402
from warden.mask import mask  # noqa: E402
from warden.paths import Paths  # noqa: E402


def run(ctx, *, paths: Paths | None = None, **runner_kwargs) -> str:
    os.umask(0o077)
    paths = paths or Paths.for_app_root(APP_ROOT)
    paths.ensure()
    trigger = store.consume_run_request(paths)
    try:
        with store.run_lock(paths):
            try:
                s = settings.load(paths)
            except settings.SettingsInvalid as exc:
                s, reason = None, str(exc)
            else:
                reason = "" if s else "open the Warden page and save the settings first"
            if s is None:
                rec = runner.not_configured(reason, trigger=trigger)
            else:
                rec = runner.run_all(s, paths, trigger=trigger, **runner_kwargs)
            prev = store.previous_comparable(paths)
            found = changes.detect(prev, rec)
            rec["changes"] = [c.to_dict() for c in found]
            line = mask(changes.render(found)) if found else None
            rec["notified"] = line
            if line:
                try:
                    ctx.notify(line)
                except Exception as exc:  # the record is saved either way
                    rec["notify_error"] = type(exc).__name__
            store.save_run(paths, rec)
            if rec.get("drift"):
                store.save_drift(paths, rec["drift"])
            store.write_summary(paths, rec, rec.get("drift"))
            store.prune(paths)
    except store.Locked:
        rec = runner.skipped(trigger=trigger)
        store.save_run(paths, rec)
    return f"hauntlet-warden: {rec['status']}"
