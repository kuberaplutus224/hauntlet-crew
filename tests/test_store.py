import json
import os
import time

import pytest
from hypothesis import given, strategies as st

from warden import store
from warden.mask import has_unmasked
from warden.paths import Paths


def mkrec(i: int, **extra) -> dict:
    return {"run_id": f"20261113T{i:06d}Z-ab{i % 100:02d}", "status": "ok", "started_at": "s", "finished_at": "f",
            "trigger": "schedule", "selftest": {"passed": True}, "rooms": {}, "demos": {}, **extra}


json_values = st.recursive(
    st.none() | st.booleans() | st.integers(-10**6, 10**6) | st.text(max_size=20),
    lambda kids: st.lists(kids, max_size=4) | st.dictionaries(st.text(max_size=8), kids, max_size=4),
    max_leaves=20,
)


@given(json_values)
def test_p6_save_then_load_is_identity(tmp_path_factory, value):
    """Property P6 (round trip)."""
    b = tmp_path_factory.mktemp("p6")
    p = Paths(b / "data", b / "range")
    rec = mkrec(1, payload=value)
    store.save_run(p, rec)
    assert store.latest(p) == rec
    assert store.load_runs(p) == [rec]


def test_save_run_masks(paths):
    store.save_run(paths, mkrec(1, note="HAUNTLET-DUMMY-run-trap-n0nce"))
    assert not has_unmasked(paths.latest.read_text())


def test_interrupted_write_keeps_previous_file(paths, monkeypatch):
    store.atomic_write_json(paths.latest, {"v": 1})

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        store.atomic_write_json(paths.latest, {"v": 2})
    assert json.loads(paths.latest.read_text()) == {"v": 1}
    assert [f for f in paths.store.iterdir() if f.name.endswith(".tmp")] == []


@given(st.integers(0, 12), st.integers(1, 6))
def test_p6_prune_keeps_exactly_the_newest(tmp_path_factory, n, keep):
    """Property P6 (prune keeps the newest ``keep``)."""
    b = tmp_path_factory.mktemp("prune")
    p = Paths(b / "data", b / "range")
    for i in range(n):
        store.save_run(p, mkrec(i))
    store.prune(p, keep=keep)
    names = [f.name for f in store.run_files(p)]
    assert names == [f"{mkrec(i)['run_id']}.json" for i in range(max(0, n - keep), n)]


def test_prune_scope(paths, tmp_path):
    paths.reports.mkdir(parents=True)
    kept_report = paths.reports / "autopsy-threshold-naive-AAAAAAAA.html"
    old_report = paths.reports / "autopsy-threshold-naive-BBBBBBBB.html"
    kept_report.write_text("k")
    old_report.write_text("o")
    store.save_run(paths, mkrec(1, rooms={"threshold": {"naive": {"report": str(kept_report)}}}))
    outside = tmp_path / "outside.html"
    outside.write_text("must survive")
    os.symlink(outside, paths.reports / "autopsy-threshold-naive-CCCCCCCC.html")
    old_scratch = paths.scratch / "run-old"
    new_scratch = paths.scratch / "run-new"
    for d in (old_scratch, new_scratch):
        d.mkdir(parents=True)
    old = time.time() - 8 * 24 * 3600
    os.utime(old_scratch, (old, old))
    linked = paths.scratch / "run-link"
    os.symlink(tmp_path, linked)
    os.utime(linked, (old, old), follow_symlinks=False)
    bundle = paths.bundles_root / "oldrun"
    bundle.mkdir(parents=True)
    os.utime(bundle, (old, old))
    deleted = store.prune(paths)
    assert kept_report.exists() and not old_report.exists()
    assert outside.exists()
    assert not old_scratch.exists() and new_scratch.exists()
    assert tmp_path.exists() and linked.is_symlink()
    assert not bundle.exists()
    assert deleted and all(str(d).startswith((str(paths.data), str(paths.range))) for d in deleted)


def test_run_lock_is_exclusive(paths):
    with store.run_lock(paths):
        with pytest.raises(store.Locked):
            with store.run_lock(paths):
                pass
    with store.run_lock(paths):
        pass


def test_run_request(paths):
    assert store.consume_run_request(paths) == "schedule"
    store.write_run_request(paths, now=1000.0)
    assert store.consume_run_request(paths, now=1060.0) == "manual"
    assert store.consume_run_request(paths, now=1061.0) == "schedule"  # consumed
    store.write_run_request(paths, now=1000.0)
    assert store.consume_run_request(paths, now=1200.0) == "schedule"  # too old


def test_previous_comparable_and_history(paths):
    store.save_run(paths, mkrec(1))
    store.save_run(paths, mkrec(2, status="skipped"))
    assert store.previous_comparable(paths)["run_id"] == mkrec(1)["run_id"]
    h = store.history(paths)
    assert [r["run_id"] for r in h] == [mkrec(1)["run_id"]]


def test_summary_is_plain_short_and_masked(paths):
    rec = mkrec(1, rooms={"threshold": {"naive": {"worst": "L4", "pass_k": 0.0},
                                         "hardened": {"worst": "L0", "pass_k": 1.0}}},
                errors=[{"command": "demo x", "detail": "HAUNTLET-DUMMY-abc <b>bold</b>"}])
    d = {"workspace": "/ws", "status": "missing", "warnings": ["w"] * 100,
         "files": {".kiro/steering/a.md": {"items": [{"item": ".kiro/steering/a.md#DATA", "status": "missing"}]}}}
    store.write_summary(paths, rec, d)
    text = paths.summary.read_text()
    assert len(text.splitlines()) <= store.SUMMARY_MAX_LINES
    assert "<" not in text and ">" not in text and not has_unmasked(text)
    assert "threshold: naive L4" in text and "DATA missing" in text
    assert "No run yet" in store.render_summary(None, None)
