"""Hauntlet Warden backend: a loopback, stdlib-only HTTP server (Requirement 8).

The gateway proxies ``/apps/hauntlet-warden/api/<x>`` to ``/api/<x>`` here and signs
each request (spike 1.4). ``/health`` is the gateway's unsigned probe and returns no
data. Every other route requires a valid ``X-KiroCrew-Proxy-V2`` signature. The
backend never runs Hauntlet's nightly sequence; that is the cron's job.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import stat
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from warden import commands, proxyauth, reference, runner, settings, store  # noqa: E402
from warden.execute import run_cmd  # noqa: E402
from warden.mask import has_unmasked, mask_obj  # noqa: E402
from warden.paths import Paths  # noqa: E402

MAX_BODY = 16 * 1024
REPORT_NAME = re.compile(
    r"(?:autopsy-[a-z0-9]+(?:-[a-z0-9]+)*-(?:naive|hardened)-[A-Za-z0-9_-]{8,64}"
    r"|exorcist-delta-[A-Za-z0-9_-]{8,64})\.html"
)
REPORT_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data:"
COMMON_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


class App:
    """State shared by request handlers. Tests build one with temporary paths."""

    def __init__(self, paths: Paths, secret: str | None, *, today=None, execute=run_cmd, base_env=None):
        self.paths = paths
        self.secret = secret
        self.cache = proxyauth.ReplayCache()
        self.drift_lock = threading.Lock()
        self.install_lock = threading.Lock()
        self.today = today
        self.execute = execute
        self.base_env = os.environ if base_env is None else base_env

    def settings_view(self) -> tuple[settings.Settings | None, list[str]]:
        try:
            s = settings.load(self.paths)
        except settings.SettingsInvalid as exc:
            return None, exc.errors
        if s is None:
            return None, ["not configured"]
        return s, settings.validate(s, self.paths, today=self.today)


class Handler(BaseHTTPRequestHandler):
    server_version = "hauntlet-warden"
    sys_version = ""
    app: App  # set by make_server

    # -- plumbing ------------------------------------------------------------
    def log_message(self, fmt, *args):  # no request logging (paths may name local files)
        pass

    def _send(self, code: int, body: bytes, ctype: str, extra: dict[str, str] | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in {**COMMON_HEADERS, **(extra or {})}.items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code: int, obj: Any) -> None:
        self._send(code, json.dumps(mask_obj(obj), sort_keys=True).encode(), "application/json")

    def _body(self) -> bytes | None:
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return None
        if n < 0 or n > MAX_BODY:
            return None
        return self.rfile.read(n) if n else b""

    def _dispatch(self, method: str) -> None:
        target = self.path
        path = urlsplit(target).path
        if method == "GET" and path == "/health":
            return self._json(200, {"ok": True})
        body = self._body()
        if body is None:
            return self._json(413, {"error": "body too large"})
        if not proxyauth.verify(self.headers, method, target, body, self.app.secret, self.app.cache):
            return self._json(401, {"error": "unauthorized"})
        route = ROUTES.get((method, path))
        if route is None and method == "GET" and path.startswith("/api/reports/"):
            route = Handler.get_report
        if route is None:
            return self._json(404, {"error": "not found"})
        try:
            route(self, body)
        except Exception as exc:  # never leak a traceback
            self._json(500, {"error": type(exc).__name__})

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def _query(self) -> dict[str, list[str]]:
        return parse_qs(urlsplit(self.path).query)

    def _parse_json(self, body: bytes) -> Any:
        try:
            return json.loads(body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    # -- routes ----------------------------------------------------------------
    def get_state(self, body: bytes) -> None:
        p = self.app.paths
        s, errors = self.app.settings_view()
        drift = store.load_drift(p)
        ref = store.load_reference(p)
        self._json(200, {
            "latest": store.latest(p),
            "settings": s.to_dict() if s else None,
            "settings_errors": errors,
            "drift": {k: (drift or {}).get(k) for k in ("status", "checked_at", "workspace")},
            "reference": {"rooms": reference.reference_rooms(ref)},
            "known_rooms": list(settings.KNOWN_ROOMS),
            "demo_rooms": list(settings.DEMO_ROOMS),
            "git_available_from": settings.GIT_PUBLIC_DATE.isoformat(),
        })

    def get_history(self, body: bytes) -> None:
        q = self._query()
        try:
            limit = int(q.get("limit", ["30"])[0])
        except ValueError:
            return self._json(400, {"error": "limit must be a number"})
        room = q.get("room", [None])[0]
        if room is not None and room not in settings.KNOWN_ROOMS:
            return self._json(400, {"error": "unknown room"})
        self._json(200, {"runs": store.history(self.app.paths, limit=limit, room=room)})

    def get_drift(self, body: bytes) -> None:
        self._json(200, store.load_drift(self.app.paths) or {"status": "none"})

    def post_drift_check(self, body: bytes) -> None:
        if not self.app.drift_lock.acquire(blocking=False):
            return self._json(409, {"error": "a drift check is already running"})
        try:
            try:
                s = settings.load(self.app.paths)
            except settings.SettingsInvalid as exc:
                return self._json(400, {"error": "settings invalid", "errors": exc.errors})
            if s is None:
                s = settings.Settings()
            d = runner.run_drift(s, self.app.paths, store.load_reference(self.app.paths), store.utc_now())
            store.save_drift(self.app.paths, d)
            self._json(200, d)
        finally:
            self.app.drift_lock.release()

    def get_summary(self, body: bytes) -> None:
        try:
            text = self.app.paths.summary.read_text(encoding="utf-8")
        except FileNotFoundError:
            text = ""
        self._json(200, {"text": text})

    def post_run_request(self, body: bytes) -> None:
        store.write_run_request(self.app.paths)
        self._json(200, {"ok": True})

    def get_settings(self, body: bytes) -> None:
        s, errors = self.app.settings_view()
        self._json(200, {"settings": s.to_dict() if s else None, "errors": errors})

    def put_settings(self, body: bytes) -> None:
        data = self._parse_json(body)
        try:
            current = settings.load(self.app.paths)
        except settings.SettingsInvalid:
            current = None
        try:
            new = settings.with_client_update(current, data)
        except settings.SettingsInvalid as exc:
            return self._json(400, {"error": "settings invalid", "errors": exc.errors})
        errors = settings.validate(new, self.app.paths, today=self.app.today)
        if errors:
            return self._json(400, {"error": "settings invalid", "errors": errors})
        settings.save(self.app.paths, new)
        self._json(200, {"settings": new.to_dict(), "errors": []})

    def post_git_install(self, body: bytes) -> None:
        data = self._parse_json(body)
        today = self.app.today or _dt.date.today()
        if today < settings.GIT_PUBLIC_DATE:
            return self._json(403, {"error": f"available from {settings.GIT_PUBLIC_DATE.isoformat()}"})
        if not (isinstance(data, dict) and data.get("approve") is True):
            return self._json(400, {"error": 'confirm with {"approve": true}'})
        if not self.app.install_lock.acquire(blocking=False):
            return self._json(409, {"error": "an install is already running"})
        try:
            try:
                current = settings.load(self.app.paths) or settings.Settings()
            except settings.SettingsInvalid as exc:
                return self._json(400, {"error": "settings invalid", "errors": exc.errors})
            uv = commands.resolve_uv(current)
            if uv is None:
                return self._json(400, {"error": "uv not found; set uv_path"})
            self.app.paths.ensure()
            out = self.app.execute(commands.git_install_cmd(uv, self.app.paths, self.app.base_env))
            tool = self.app.paths.tools_bin / "hauntlet"
            if out.exit_code != 0 or not tool.is_file():
                return self._json(502, {"error": "install failed", "stderr_tail": out.stderr[-1500:]})
            gi = settings.GitInstall(approved=True, installed_at=store.iso(store.utc_now()), tool_path=str(tool))
            from dataclasses import replace

            settings.save(self.app.paths, replace(current, git_install=gi))
            self._json(200, {"ok": True, "tool_path": str(tool)})
        finally:
            self.app.install_lock.release()

    def get_report(self, body: bytes) -> None:
        name = urlsplit(self.path).path[len("/api/reports/"):]
        if not REPORT_NAME.fullmatch(name):
            return self._json(404, {"error": "not found"})
        p = self.app.paths
        for d in (p.reports, p.exorcist_reports):
            f = d / name
            try:
                st = os.lstat(f)
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(st.st_mode):
                return self._json(404, {"error": "not found"})
            data = f.read_bytes()
            if has_unmasked(data.decode("utf-8", errors="replace")):
                return self._json(500, {"error": "report holds an unmasked dummy secret; not served"})
            return self._send(200, data, "text/html; charset=utf-8", {"Content-Security-Policy": REPORT_CSP})
        self._json(404, {"error": "not found"})


ROUTES = {
    ("GET", "/api/state"): Handler.get_state,
    ("GET", "/api/history"): Handler.get_history,
    ("GET", "/api/drift"): Handler.get_drift,
    ("POST", "/api/drift/check"): Handler.post_drift_check,
    ("GET", "/api/summary"): Handler.get_summary,
    ("POST", "/api/run-request"): Handler.post_run_request,
    ("GET", "/api/settings"): Handler.get_settings,
    ("PUT", "/api/settings"): Handler.put_settings,
    ("POST", "/api/git-install"): Handler.post_git_install,
}


def make_server(app: App, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("the backend binds loopback only")
    handler = type("BoundHandler", (Handler,), {"app": app})
    srv = ThreadingHTTPServer((host, port), handler)
    srv.daemon_threads = True
    return srv


def main() -> int:
    os.umask(0o077)
    port = os.environ.get("PORT", "")
    if not port.isdigit():
        print("hauntlet-warden backend: PORT is not set", file=sys.stderr)
        return 2
    paths = Paths.for_app_root(APP_ROOT)
    app = App(paths, proxyauth.load_secret(os.environ, APP_ROOT))
    make_server(app, "127.0.0.1", int(port)).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
