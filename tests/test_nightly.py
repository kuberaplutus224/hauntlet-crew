import json
import shutil

from conftest import WORKSPACES
from helpers import FakeCtx, FakeHauntlet
from warden import settings as S, store
from warden.mask import has_unmasked

from backend import nightly



def configure(paths, checkout, ws=""):
    S.save(paths, S.Settings(hauntlet_checkout=str(checkout), watched_workspace=str(ws)))


def run(paths, ctx, fake):
    return nightly.run(ctx, paths=paths, execute=fake, base_env={}, which=lambda _: "/x/uv")


def test_not_configured_records_reason_and_does_not_notify(paths):
    ctx = FakeCtx()
    assert run(paths, ctx, FakeHauntlet(paths)) == "hauntlet-warden: not_configured"
    assert ctx.sent == []
    assert "save the settings" in store.latest(paths)["reason"]


def test_first_run_is_a_silent_baseline_then_only_changes_notify(paths, checkout, tmp_path):
    ws = tmp_path / "ws"
    shutil.copytree(WORKSPACES / "complete", ws)
    configure(paths, checkout, ws)
    ctx = FakeCtx()
    assert run(paths, ctx, FakeHauntlet(paths)) == "hauntlet-warden: ok"
    assert ctx.sent == []
    run(paths, ctx, FakeHauntlet(paths))
    assert ctx.sent == []  # unchanged rerun
    # a level change and new drift
    (ws / ".kiro/settings/sandbox.json").write_text(json.dumps({"enabled": True, "networkAccess": "ALLOW_ALL"}))
    run(paths, ctx, FakeHauntlet(paths, levels={("poltergeist", "hardened"): 2}))
    assert len(ctx.sent) == 1
    line = ctx.sent[0]
    assert line.startswith("Hauntlet Warden: ") and len(line) <= 200
    assert "poltergeist hardened L0→L2" in line and "networkAccess weaker" in line
    latest = store.latest(paths)
    assert latest["notified"] == line and latest["changes"]
    assert store.load_drift(paths)["status"] == "weaker"
    assert "poltergeist" in paths.summary.read_text()


def test_notify_failure_still_saves_the_record(paths, checkout):
    configure(paths, checkout)
    ctx = FakeCtx(fail=True)
    run(paths, ctx, FakeHauntlet(paths, selftest="fail"))
    rec = store.latest(paths)
    assert rec["status"] == "failed" and rec["notify_error"] == "RuntimeError"


def test_locked_run_is_skipped(paths, checkout):
    configure(paths, checkout)
    with store.run_lock(paths):
        assert run(paths, FakeCtx(), FakeHauntlet(paths)) == "hauntlet-warden: skipped"
    assert store.latest(paths)["status"] == "skipped"


def test_manual_trigger_from_run_request(paths, checkout):
    configure(paths, checkout)
    store.write_run_request(paths)
    run(paths, FakeCtx(), FakeHauntlet(paths))
    assert store.latest(paths)["trigger"] == "manual"


def test_stored_files_hold_no_unmasked_dummy(paths, checkout):
    configure(paths, checkout)
    run(paths, FakeCtx(), FakeHauntlet(paths))
    for f in paths.store.rglob("*"):
        if f.is_file() and f.suffix in (".json", ".md"):
            assert not has_unmasked(f.read_text()), f
