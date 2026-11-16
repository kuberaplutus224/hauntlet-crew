"""The nightly sequence (Requirement 2.4–2.7): selftest, runs, demos, drift.

``run_all`` takes its executor, clock and environment as arguments, so tests drive it
with a fake executor. One failing command never stops the ones after it.
"""

from __future__ import annotations

import datetime as _dt
import os
import shutil
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from warden import commands, drift as drift_mod, parse, readonly, reference
from warden.commands import Cmd
from warden.execute import Outcome, run_cmd, tail
from warden.parse import LEVEL_NAMES, ParseError
from warden.paths import Paths
from warden.settings import Settings, SettingsInvalid, validate
from warden.store import iso, load_reference, new_run_id, save_reference, utc_now

#: Overall budget: the cron's ``timeout`` (1800 s) minus 100 s for storing results.
RUN_BUDGET_SECS = 1700.0
UNSYNCED_DETAIL = "Hauntlet checkout is not synced: run `uv sync` in {checkout}"


def _level(n: int) -> str:
    return f"L{n}"


def _skeleton(run_id: str, trigger: str, started: _dt.datetime, s: Settings | None) -> dict[str, Any]:
    return {
        "schema": 1,
        "run_id": run_id,
        "trigger": trigger,
        "started_at": iso(started),
        "finished_at": None,
        "status": "ok",
        "source": (
            {"kind": s.hauntlet_source, "project": s.hauntlet_checkout if s.hauntlet_source == "checkout" else s.git_install.tool_path}
            if s else None
        ),
        "selftest": {},
        "rooms": {},
        "demos": {},
        "errors": [],
        "drift": None,
        "changes": [],
        "notified": None,
    }


def not_configured(reason: str, *, trigger: str, now: _dt.datetime | None = None, s: Settings | None = None) -> dict[str, Any]:
    now = now or utc_now()
    rec = _skeleton(new_run_id(now), trigger, now, s)
    rec.update(status="not_configured", reason=reason, finished_at=iso(now))
    return rec


def skipped(*, trigger: str, now: _dt.datetime | None = None) -> dict[str, Any]:
    now = now or utc_now()
    rec = _skeleton(new_run_id(now), trigger, now, None)
    rec.update(status="skipped", reason="already running", finished_at=iso(now))
    return rec


def _classify(cmd: Cmd, out: Outcome, s: Settings) -> tuple[str, str] | None:
    """(kind, detail) when the command did not complete, else None."""
    if out.error:
        return "start", out.error
    if out.timed_out:
        return "timeout", f"killed after {int(cmd.timeout)} s"
    if parse.is_unsynced(out.stderr, out.exit_code):
        return "unsynced", UNSYNCED_DETAIL.format(checkout=s.hauntlet_checkout or "the checkout")
    return None


def run_drift(s: Settings, paths: Paths, ref: Mapping[str, Any] | None, now: _dt.datetime) -> dict[str, Any]:
    """The read-only drift check. Shared by the nightly run and "Check drift now"."""
    at = iso(now)
    if not s.watched_workspace:
        return drift_mod.special("not configured", checked_at=at)
    items = reference.merged_items(ref)
    if not items:
        return drift_mod.special("no reference yet", checked_at=at, workspace=s.watched_workspace)
    try:
        snap = readonly.snapshot(s.watched_workspace)
    except readonly.WorkspaceMissing:
        return drift_mod.special("error", checked_at=at, workspace=s.watched_workspace, error="workspace not found")
    return drift_mod.compare(items, snap, checked_at=at, reference_from=reference.reference_rooms(ref))


def run_all(
    s: Settings,
    paths: Paths,
    *,
    trigger: str,
    execute: Callable[[Cmd], Outcome] = run_cmd,
    base_env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    now: Callable[[], _dt.datetime] = utc_now,
    monotonic: Callable[[], float] = time.monotonic,
    budget: float = RUN_BUDGET_SECS,
) -> dict[str, Any]:
    """Run the whole sequence and return the run record (with its drift report)."""
    started = now()
    errors = validate(s, paths)
    if errors:
        return not_configured("; ".join(errors), trigger=trigger, now=started, s=s)
    uv = commands.resolve_uv(s, which=which)
    try:
        plan = commands.build_plan(s, paths, uv, os.environ if base_env is None else base_env)
    except SettingsInvalid as exc:
        return not_configured(str(exc), trigger=trigger, now=started, s=s)
    paths.ensure()
    rec = _skeleton(new_run_id(started), trigger, started, s)
    deadline = monotonic() + budget
    fragments: dict[str, dict] = {}

    def fail(cmd: Cmd, kind: str, detail: str, out: Outcome | None) -> str:
        entry = {"command": cmd.label, "kind": kind, "detail": detail}
        if out is not None:
            entry["stderr_tail"] = tail(out.stderr, 1500)
            entry["exit_code"] = out.exit_code
        rec["errors"].append(entry)
        return f"{kind}: {detail}"

    for cmd in plan:
        if monotonic() > deadline:
            err = fail(cmd, "budget", "not run (time budget)", None)
            out = None
        else:
            out = execute(cmd)
            bad = _classify(cmd, out, s)
            err = fail(cmd, bad[0], bad[1], out) if bad else None
        if cmd.kind == "selftest":
            entry: dict[str, Any] = {"passed": None, "exit_code": out.exit_code if out else None,
                                     "summary": "", "failures": [], "error": err}
            if err is None:
                try:
                    st = parse.parse_selftest(out.stdout, out.stderr, out.exit_code)
                    entry.update(passed=st.passed, summary=st.summary, failures=list(st.failures))
                except ParseError as exc:
                    entry["error"] = fail(cmd, "unparsed", str(exc), out)
            rec["selftest"] = entry
        elif cmd.kind == "run":
            entry = {"error": err, "exit_code": out.exit_code if out else None}
            if err is None:
                try:
                    r = parse.parse_run(out.stdout, out.stderr, out.exit_code, room=cmd.room, repeat=s.repeat)
                    entry.update(
                        n=r.n, worst=_level(r.worst), worst_name=LEVEL_NAMES[r.worst],
                        compromised=r.compromised, clean=r.clean, detected=r.detected, task=r.task,
                        passes={str(k): v for k, v in r.passes}, pass_k=r.pass_k, k=r.k,
                        excluded=r.excluded, run_ids=list(r.run_ids), report=r.report,
                    )
                except ParseError as exc:
                    entry["error"] = fail(cmd, "unparsed" if out.exit_code == 0 else "exit", str(exc), out)
            rec["rooms"].setdefault(cmd.room, {})[cmd.agent] = entry
        elif cmd.kind == "demo":
            entry = {"error": err, "exit_code": out.exit_code if out else None}
            if err is None:
                try:
                    d = parse.parse_demo(out.stdout, out.stderr, out.exit_code, room=cmd.room)
                    entry.update(bundle=d.bundle, report=d.report, before_worst=_level(d.before_worst),
                                 after_worst=_level(d.after_worst), detected=d.detected, task=d.task)
                    try:
                        fragments[cmd.room] = reference.fragment_from_bundle(
                            Path(d.bundle), paths.bundles_root, from_run=rec["run_id"])
                    except (OSError, ValueError) as exc:
                        entry["error"] = fail(cmd, "unparsed", f"bundle not readable: {type(exc).__name__}", out)
                except ParseError as exc:
                    entry["error"] = fail(cmd, "unparsed" if out.exit_code == 0 else "exit", str(exc), out)
            rec["demos"][cmd.room] = entry

    ref = load_reference(paths)
    if fragments:
        ref = reference.update(ref, fragments)
        save_reference(paths, ref)
    rec["drift"] = run_drift(s, paths, ref, now())
    if rec["errors"]:
        rec["status"] = "error"
    elif rec["selftest"].get("passed") is False:
        rec["status"] = "failed"
    rec["finished_at"] = iso(now())
    return rec
