import datetime as dt
import itertools

from conftest import output
from helpers import FakeHauntlet
from warden import runner, store
from warden.execute import Outcome
from warden.settings import DEMO_ROOMS, KNOWN_ROOMS, Settings

TODAY = dt.date(2026, 11, 13)


def settings_for(checkout, ws="", **kw):
    return Settings(hauntlet_checkout=str(checkout), watched_workspace=str(ws), **kw)


def go(paths, s, fake, **kw):
    return runner.run_all(s, paths, trigger="schedule", execute=fake, base_env={}, which=lambda _: "/x/uv",
                          today=TODAY, **kw)


def test_full_run_records_everything(paths, checkout, workspace_copy):
    ws = workspace_copy("complete")
    fake = FakeHauntlet(paths)
    rec = go(paths, settings_for(checkout, ws), fake)
    assert rec["status"] == "ok" and rec["errors"] == []
    assert rec["selftest"]["passed"] is True
    assert set(rec["rooms"]) == set(KNOWN_ROOMS)
    n = rec["rooms"]["poltergeist"]["naive"]
    h = rec["rooms"]["poltergeist"]["hardened"]
    assert (n["worst"], n["pass_k"], n["k"]) == ("L4", 0.0, 2)
    assert (h["worst"], h["pass_k"], h["detected"]) == ("L0", 1.0, 1.0)
    assert n["report"].endswith(".html") and len(n["run_ids"]) == 3
    assert set(rec["demos"]) == set(DEMO_ROOMS)
    assert rec["drift"]["status"] == "present"
    assert set(store.load_reference(paths)["rooms"]) == set(DEMO_ROOMS)
    assert [c.label for c in fake.calls][0] == "selftest"
    assert all(c.cwd == paths.range for c in fake.calls)


def test_one_failure_does_not_stop_the_rest(paths, checkout):
    fake = FakeHauntlet(paths, fail={"run threshold naive": Outcome(None, "", "", True, 150.0)},
                        unparsable={"run parlor hardened"})
    rec = go(paths, settings_for(checkout), fake)
    assert rec["status"] == "error"
    kinds = {(e["command"], e["kind"]) for e in rec["errors"]}
    assert kinds == {("run threshold naive", "timeout"), ("run parlor hardened", "unparsed")}
    assert rec["rooms"]["threshold"]["hardened"]["worst"] == "L0"
    assert rec["rooms"]["threshold"]["naive"]["error"].startswith("timeout")
    assert len(fake.calls) == 1 + 2 * 6 + 5


def test_unsynced_checkout_gives_the_uv_sync_message(paths, checkout):
    o = output("selftest_unsynced")
    fake = FakeHauntlet(paths, fail={"selftest": Outcome(1, o["stdout"], o["stderr"], False, 1.0)})
    rec = go(paths, settings_for(checkout), fake)
    err = rec["errors"][0]
    assert err["kind"] == "unsynced"
    assert err["detail"] == f"Hauntlet checkout is not synced: run `uv sync` in {checkout}"
    assert rec["selftest"]["passed"] is None


def test_selftest_failure_is_failed_not_error(paths, checkout):
    rec = go(paths, settings_for(checkout), FakeHauntlet(paths, selftest="fail"))
    assert rec["status"] == "failed"
    assert rec["selftest"]["failures"] == ["poltergeist: hardened scored L2, expected L0"]


def test_time_budget(paths, checkout):
    clock = itertools.count(0, 100)
    rec = go(paths, settings_for(checkout), FakeHauntlet(paths), monotonic=lambda: next(clock), budget=350)
    budget = [e for e in rec["errors"] if e["kind"] == "budget"]
    assert budget and all(e["detail"] == "not run (time budget)" for e in budget)


def test_failed_demo_keeps_previous_fragment(paths, checkout):
    go(paths, settings_for(checkout), FakeHauntlet(paths))
    first = store.load_reference(paths)["rooms"]["threshold"]["from_run"]
    rec = go(paths, settings_for(checkout), FakeHauntlet(paths, fail={"demo threshold": Outcome(1, "", "boom", False, 1)}))
    ref = store.load_reference(paths)["rooms"]
    assert ref["threshold"]["from_run"] == first
    assert ref["poltergeist"]["from_run"] == rec["run_id"]


def test_not_configured(paths, checkout, monkeypatch):
    rec = go(paths, Settings(), FakeHauntlet(paths))
    assert rec["status"] == "not_configured" and "checkout" in rec["reason"]
    from warden import commands

    monkeypatch.setattr(commands, "resolve_uv", lambda s, which=None: None)
    fake = FakeHauntlet(paths)
    rec2 = go(paths, settings_for(checkout), fake)
    assert rec2["status"] == "not_configured" and rec2["reason"] == "uv not found; set uv_path"
    assert fake.calls == []


def test_drift_without_workspace_or_reference(paths, checkout, workspace_copy):
    s = settings_for(checkout)
    assert runner.run_drift(s, paths, None, store.utc_now())["status"] == "not configured"
    s2 = settings_for(checkout, workspace_copy("complete"))
    assert runner.run_drift(s2, paths, None, store.utc_now())["status"] == "no reference yet"
    s3 = settings_for(checkout, "/does/not/exist")
    d = runner.run_drift(s3, paths, {"rooms": {"r": {"mcp": ["autoApprove"]}}}, store.utc_now())
    assert d["status"] == "error" and d["error"] == "workspace not found"
