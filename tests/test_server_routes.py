import http.client
import json
import threading
from pathlib import Path

import pytest

from warden import proxyauth, settings as S, store

from backend import server

SECRET = "route-test-secret"


@pytest.fixture
def srv(paths):
    app = server.App(paths, SECRET)
    s = server.make_server(app, "127.0.0.1", 0)
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    yield s
    s.shutdown()
    s.server_close()


def call(srv, method, target, body=b"", sign=True, extra=None):
    conn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=10)
    hdrs = {"Content-Type": "application/json"}
    if sign:
        hdrs.update(proxyauth.sign_headers(SECRET, method, target, body))
    hdrs.update(extra or {})
    conn.request(method, target, body=body, headers=hdrs)
    r = conn.getresponse()
    data = r.read()
    conn.close()
    return r.status, dict(r.getheaders()), data


def jcall(srv, method, target, obj=None, **kw):
    body = b"" if obj is None else json.dumps(obj).encode()
    status, h, data = call(srv, method, target, body, **kw)
    return status, json.loads(data)


def test_health_is_unsigned_and_empty(srv):
    assert jcall(srv, "GET", "/health", sign=False) == (200, {"ok": True})


@pytest.mark.parametrize("method, target", [
    ("GET", "/api/state"), ("GET", "/api/history"), ("GET", "/api/drift"), ("POST", "/api/drift/check"),
    ("GET", "/api/summary"), ("POST", "/api/run-request"), ("GET", "/api/settings"), ("PUT", "/api/settings"),
    ("POST", "/api/git-install"), ("GET", "/api/reports/autopsy-threshold-naive-AAAAAAAA.html"),
])
def test_every_other_route_needs_a_signature(srv, method, target):
    status, body = jcall(srv, method, target, sign=False)
    assert status == 401 and body == {"error": "unauthorized"}


def test_unknown_route_is_404(srv):
    assert jcall(srv, "GET", "/api/nope")[0] == 404


def test_state_before_configuration(srv):
    status, body = jcall(srv, "GET", "/api/state")
    assert status == 200 and body["latest"] is None and body["settings"] is None
    assert body["known_rooms"] == list(S.KNOWN_ROOMS) and "git_available_from" not in body


def test_settings_put_valid_and_invalid(srv, checkout, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    good = {"hauntlet_checkout": str(checkout), "watched_workspace": str(ws), "repeat": 3}
    status, body = jcall(srv, "PUT", "/api/settings", good)
    assert status == 200 and body["settings"]["watched_workspace"] == str(ws)
    status, body = jcall(srv, "PUT", "/api/settings", {**good, "repeat": 99})
    assert status == 400 and any("repeat" in e for e in body["errors"])
    status, body = jcall(srv, "PUT", "/api/settings", {**good, "hauntlet_source": "git"})
    assert status == 400
    status, body = jcall(srv, "GET", "/api/settings")
    assert body["settings"]["repeat"] == 3 and body["errors"] == []


def test_body_size_cap(srv):
    status, _ = jcall(srv, "PUT", "/api/settings", {"x": "a" * (17 * 1024)})
    assert status == 413


def test_summary_and_run_request(srv, paths):
    assert jcall(srv, "GET", "/api/summary") == (200, {"text": ""})
    store.write_summary(paths, None, None)
    status, body = jcall(srv, "GET", "/api/summary")
    assert "No run yet" in body["text"]
    assert jcall(srv, "POST", "/api/run-request", {}) == (200, {"ok": True})
    assert store.consume_run_request(paths) == "manual"


def test_git_install_needs_explicit_approval_and_stays_in_data_dir(paths, monkeypatch):
    from warden.execute import Outcome

    seen = []

    def fake_exec(cmd):
        seen.append(cmd)
        paths.tools_bin.mkdir(parents=True, exist_ok=True)
        (paths.tools_bin / "hauntlet").write_text("#!/bin/sh\n")
        return Outcome(0, "", "", False, 1.0)

    monkeypatch.setattr("warden.commands.resolve_uv", lambda s, **k: Path("/x/uv"))
    app = server.App(paths, SECRET, execute=fake_exec, base_env={})
    s = server.make_server(app)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        for body in ({}, {"approve": "yes"}, {"approve": 1}, None):
            assert jcall(s, "POST", "/api/git-install", body)[0] == 400
        assert seen == []  # nothing ran without {"approve": true}
        status, body = jcall(s, "POST", "/api/git-install", {"approve": True})
        assert status == 200 and body["tool_path"] == str(paths.tools_bin / "hauntlet")
        assert seen[0].env["UV_TOOL_DIR"] == str(paths.tools)
        gi = S.load(paths).git_install
        assert gi.approved and gi.tool_path == str(paths.tools_bin / "hauntlet")
    finally:
        s.shutdown()
        s.server_close()


def test_report_guard_and_csp(srv, paths, tmp_path):
    paths.reports.mkdir(parents=True)
    good = paths.reports / "autopsy-poltergeist-naive-AbCdEfGh12.html"
    good.write_text("<html>HAUNTLET-DUMMY-… ok</html>")
    status, h, data = call(srv, "GET", f"/api/reports/{good.name}")
    assert status == 200 and data.startswith(b"<html>")
    assert h["Content-Security-Policy"] == "default-src 'none'; style-src 'unsafe-inline'; img-src data:"
    assert h["X-Content-Type-Options"] == "nosniff" and h["Referrer-Policy"] == "no-referrer"
    for bad in ["../warden/settings.json", "autopsy-x-naive-short.html", "evil.html", "%2e%2e%2fsettings.json"]:
        assert call(srv, "GET", f"/api/reports/{bad}")[0] == 404
    outside = tmp_path / "outside.html"
    outside.write_text("secret")
    import os

    os.symlink(outside, paths.reports / "autopsy-poltergeist-naive-LINKLINK.html")
    assert call(srv, "GET", "/api/reports/autopsy-poltergeist-naive-LINKLINK.html")[0] == 404


def test_report_with_unmasked_dummy_is_refused(srv, paths):
    paths.exorcist_reports.mkdir(parents=True)
    f = paths.exorcist_reports / "exorcist-delta-AAAABBBBCC.html"
    f.write_text("<html>HAUNTLET-DUMMY-run1-trap-zz</html>")
    status, _, data = call(srv, "GET", f"/api/reports/{f.name}")
    assert status == 500 and b"HAUNTLET-DUMMY-run1" not in data


def test_json_responses_are_masked(srv, paths):
    store.save_drift(paths, {"status": "x", "workspace": "/w", "detail": "HAUNTLET-DUMMY-abc"})
    status, h, data = call(srv, "GET", "/api/drift")
    assert b"HAUNTLET-DUMMY-abc" not in data and h["Cache-Control"] == "no-store"


def test_drift_check_without_settings(srv):
    status, body = jcall(srv, "POST", "/api/drift/check", {})
    assert status == 200 and body["status"] == "not configured"


def test_make_server_refuses_non_loopback(paths):
    with pytest.raises(ValueError):
        server.make_server(server.App(paths, SECRET), "0.0.0.0", 0)
