"""Warden's JSON store: atomic writes, history, pruning, summary (Requirement 3, P6)."""

from __future__ import annotations

import datetime as _dt
import fcntl
import json
import os
import secrets
import shutil
import stat
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from warden import CLIENT_NOTE
from warden.mask import mask, mask_obj
from warden.paths import Paths, is_within

KEEP_RUNS = 90
SCRATCH_MAX_AGE_SECS = 7 * 24 * 3600
RUN_REQUEST_MAX_AGE_SECS = 120
SUMMARY_MAX_LINES = 60


class Locked(RuntimeError):
    pass


def atomic_write_json(path: Path, obj: Any) -> None:
    """Write JSON to a temp file in the same directory, fsync, then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data = json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    _atomic_write_text(path, data)


def _atomic_write_text(path: Path, data: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.UTC)


def iso(t: _dt.datetime) -> str:
    return t.astimezone(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_id(now: _dt.datetime) -> str:
    return f"{now.astimezone(_dt.UTC):%Y%m%dT%H%M%SZ}-{secrets.token_hex(2)}"


# ---- runs -------------------------------------------------------------------


def save_run(paths: Paths, rec: dict[str, Any]) -> None:
    rec = mask_obj(rec)
    paths.ensure()
    atomic_write_json(paths.runs / f"{rec['run_id']}.json", rec)
    atomic_write_json(paths.latest, rec)


def run_files(paths: Paths) -> list[Path]:
    """Oldest first. Run ids start with a UTC timestamp, so names sort by time."""
    if not paths.runs.is_dir():
        return []
    return sorted(p for p in paths.runs.glob("*.json") if not p.name.startswith("."))


def load_runs(paths: Paths) -> list[dict[str, Any]]:
    return [r for r in (read_json(p) for p in run_files(paths)) if isinstance(r, dict)]


def latest(paths: Paths) -> dict[str, Any] | None:
    rec = read_json(paths.latest)
    return rec if isinstance(rec, dict) else None


def previous_comparable(paths: Paths) -> dict[str, Any] | None:
    from warden.changes import comparable

    for rec in reversed(load_runs(paths)):
        if comparable(rec):
            return rec
    return None


def trim(rec: dict[str, Any]) -> dict[str, Any]:
    rooms = {
        room: {
            agent: {k: e.get(k) for k in ("worst", "pass_k", "detected", "task", "error")}
            for agent, e in (agents or {}).items()
        }
        for room, agents in (rec.get("rooms") or {}).items()
    }
    drift = rec.get("drift") or {}
    return {
        "run_id": rec.get("run_id"),
        "started_at": rec.get("started_at"),
        "finished_at": rec.get("finished_at"),
        "trigger": rec.get("trigger"),
        "status": rec.get("status"),
        "selftest": {"passed": (rec.get("selftest") or {}).get("passed")},
        "rooms": rooms,
        "drift_status": drift.get("status"),
    }


def history(paths: Paths, limit: int = 30, room: str | None = None) -> list[dict[str, Any]]:
    from warden.changes import comparable

    out = [trim(r) for r in load_runs(paths) if comparable(r)]
    if room:
        for r in out:
            r["rooms"] = {k: v for k, v in r["rooms"].items() if k == room}
    return out[-max(1, min(limit, KEEP_RUNS)) :]


# ---- drift, reference --------------------------------------------------------


def save_drift(paths: Paths, drift: dict[str, Any]) -> None:
    atomic_write_json(paths.drift_file, mask_obj(drift))


def load_drift(paths: Paths) -> dict[str, Any] | None:
    d = read_json(paths.drift_file)
    return d if isinstance(d, dict) else None


def save_reference(paths: Paths, ref: dict[str, Any]) -> None:
    atomic_write_json(paths.reference_file, ref)


def load_reference(paths: Paths) -> dict[str, Any] | None:
    d = read_json(paths.reference_file)
    return d if isinstance(d, dict) else None


# ---- run lock and run request ------------------------------------------------


@contextmanager
def run_lock(paths: Paths) -> Iterator[None]:
    paths.ensure()
    fd = os.open(paths.lock, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Locked("a nightly run is already in progress") from exc
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def write_run_request(paths: Paths, now: float | None = None) -> None:
    atomic_write_json(paths.run_request, {"requested_at": time.time() if now is None else now})


def consume_run_request(paths: Paths, now: float | None = None) -> str:
    """'manual' if the page asked to run in the last 120 s, else 'schedule'."""
    now = time.time() if now is None else now
    data = read_json(paths.run_request)
    try:
        paths.run_request.unlink()
    except FileNotFoundError:
        pass
    if isinstance(data, dict) and isinstance(data.get("requested_at"), (int, float)):
        if 0 <= now - data["requested_at"] <= RUN_REQUEST_MAX_AGE_SECS:
            return "manual"
    return "schedule"


# ---- pruning -----------------------------------------------------------------


def _referenced_reports(recs: list[dict[str, Any]]) -> set[str]:
    out = set()
    for r in recs:
        for agents in (r.get("rooms") or {}).values():
            for e in (agents or {}).values():
                if isinstance(e, dict) and e.get("report"):
                    out.add(os.path.realpath(e["report"]))
        for d in (r.get("demos") or {}).values():
            if isinstance(d, dict) and d.get("report"):
                out.add(os.path.realpath(d["report"]))
    return out


def _safe_remove_file(p: Path, root: Path) -> bool:
    st = os.lstat(p)
    if not stat.S_ISREG(st.st_mode) or not is_within(p, root):
        return False
    os.unlink(p)
    return True


def _safe_rmtree(p: Path, root: Path) -> bool:
    st = os.lstat(p)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode) or not is_within(p, root):
        return False
    shutil.rmtree(p)
    return True


def prune(paths: Paths, keep: int = KEEP_RUNS, now: float | None = None) -> list[str]:
    """Delete old records, unreferenced reports, and old scratch and bundle dirs.

    Every deletion is checked to be inside the range directory or Warden's store.
    Returns the deleted paths.
    """
    now = time.time() if now is None else now
    deleted: list[str] = []
    files = run_files(paths)
    for p in files[: max(0, len(files) - keep)]:
        if _safe_remove_file(p, paths.runs):
            deleted.append(str(p))
    kept = load_runs(paths)
    refs = _referenced_reports(kept)
    for d in (paths.reports, paths.exorcist_reports):
        if d.is_dir() and not d.is_symlink():
            for p in sorted(d.glob("*.html")):
                if os.path.realpath(p) not in refs and _safe_remove_file(p, paths.range):
                    deleted.append(str(p))
    for parent, pattern in ((paths.scratch, "run-*"), (paths.bundles_root, "*")):
        if not parent.is_dir() or parent.is_symlink():
            continue
        for p in sorted(parent.glob(pattern)):
            try:
                age = now - os.lstat(p).st_mtime
            except FileNotFoundError:
                continue
            if age > SCRATCH_MAX_AGE_SECS and _safe_rmtree(p, paths.range):
                deleted.append(str(p))
    return deleted


# ---- summary -----------------------------------------------------------------


def render_summary(rec: dict[str, Any] | None, drift: dict[str, Any] | None) -> str:
    """Plain markdown for the "Ask Warden" chat. No HTML, at most 60 lines, masked."""
    if not rec:
        return "# Hauntlet Warden summary\n\nNo run yet.\n"
    lines = [
        "# Hauntlet Warden summary",
        "",
        f"Last run: {rec.get('finished_at') or rec.get('started_at')} ({rec.get('trigger')}), status: {rec.get('status')}.",
    ]
    if rec.get("reason"):
        lines.append(f"Reason: {rec['reason']}")
    st = rec.get("selftest") or {}
    if "passed" in st:
        lines.append(
            "Selftest: " + ("passed" if st.get("passed") else "failed" if st.get("passed") is False else "did not complete")
            + (f" ({'; '.join(st.get('failures', []))})" if st.get("failures") else "")
        )
    rooms = rec.get("rooms") or {}
    if rooms:
        lines += ["", "Rooms (worst level, pass^k):"]
        for room in sorted(rooms):
            cells = []
            for agent in ("naive", "hardened"):
                e = rooms[room].get(agent) or {}
                cells.append(f"{agent} {e['worst']} pass^k={e.get('pass_k')}" if e.get("worst") else f"{agent} error")
            lines.append(f"- {room}: " + ", ".join(cells))
    for e in rec.get("errors") or []:
        lines.append(f"- error: {e.get('command')}: {e.get('detail')}")
    d = drift or rec.get("drift") or {}
    if d:
        lines += ["", f"Guardrail drift ({d.get('workspace') or 'no workspace'}): {d.get('status')}."]
        for f, info in (d.get("files") or {}).items():
            bad = [r for r in info.get("items", []) if r.get("status") not in ("present", "n/a")]
            if bad:
                lines.append(f"- {f}: " + "; ".join(f"{r['item'].rsplit('#', 1)[-1]} {r['status']}" for r in bad))
        for w in d.get("warnings") or []:
            lines.append(f"- warning: {w}")
        lines.append(CLIENT_NOTE)
    text = "\n".join(lines[:SUMMARY_MAX_LINES]) + "\n"
    return mask(text.replace("<", "‹").replace(">", "›"))


def write_summary(paths: Paths, rec: dict[str, Any] | None, drift: dict[str, Any] | None) -> None:
    paths.ensure()
    _atomic_write_text(paths.summary, render_summary(rec, drift))
