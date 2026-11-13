import os
import string

import pytest
from hypothesis import given, strategies as st

from conftest import WORKSPACES, snapshot_tree
from warden import readonly


def test_complete_workspace_reads_only_allowed_files():
    snap = readonly.snapshot(WORKSPACES / "complete")
    assert set(snap.files) == {
        ".kiro/steering/credentials.md",
        ".kiro/steering/unrequested-actions.md",
        ".kiro/steering/untrusted-content.md",
        ".kiro/hooks/credential-egress.json",
        ".kiro/hooks/guards/credential_egress.py",
        ".kiro/settings/mcp.json",
        ".kiro/settings/sandbox.json",
    }
    assert snap.warnings == ()


def test_workspace_without_kiro_is_empty():
    snap = readonly.snapshot(WORKSPACES / "empty")
    assert snap.files == {} and snap.warnings == ()


def test_missing_workspace_raises(tmp_path):
    with pytest.raises(readonly.WorkspaceMissing):
        readonly.snapshot(tmp_path / "nope")


def test_hostile_workspace(hostile_workspace):
    before = snapshot_tree(hostile_workspace)
    snap = readonly.snapshot(hostile_workspace)
    assert ".kiro/steering/linked.md" not in snap.files
    assert ".kiro/steering/huge.md" not in snap.files
    assert any("linked.md is a symlink" in w for w in snap.warnings)
    assert any("huge.md is larger than 1 MiB" in w for w in snap.warnings)
    assert ".kiro/hooks/broken.json" in snap.files  # read, then judged by drift
    assert snapshot_tree(hostile_workspace) == before


def test_kiro_symlink_is_not_followed(tmp_path):
    real = tmp_path / "real-kiro"
    (real / "steering").mkdir(parents=True)
    (real / "steering" / "a.md").write_text("- a\n")
    ws = tmp_path / "ws"
    ws.mkdir()
    os.symlink(real, ws / ".kiro")
    snap = readonly.snapshot(ws)
    assert snap.files == {} and snap.warnings == (".kiro is a symlink; not read",)


def test_symlinked_subdirectory_is_not_followed(tmp_path):
    ws = tmp_path / "ws"
    (ws / ".kiro").mkdir(parents=True)
    other = tmp_path / "other"
    other.mkdir()
    (other / "x.md").write_text("- x\n")
    os.symlink(other, ws / ".kiro" / "steering")
    snap = readonly.snapshot(ws)
    assert snap.files == {} and ".kiro/steering is a symlink; not read" in snap.warnings


def test_fifo_is_skipped(tmp_path):
    ws = tmp_path / "ws"
    (ws / ".kiro" / "steering").mkdir(parents=True)
    os.mkfifo(ws / ".kiro" / "steering" / "pipe.md")
    assert readonly.snapshot(ws).files == {}


names = st.text(alphabet=string.ascii_lowercase + "-_", min_size=1, max_size=8)
entry = st.tuples(
    st.sampled_from(["steering", "hooks", "hooks/guards", "settings", "other"]),
    names,
    st.sampled_from([".md", ".json", ".py", ".txt"]),
    st.sampled_from(["text", "bigger", "badjson", "symlink-out", "symlink-in"]),
)


@given(st.lists(entry, max_size=10))
def test_p7_snapshot_and_compare_change_nothing(tmp_path_factory, entries):
    """Property P7: snapshot + compare leave bytes, mode and mtime unchanged and create nothing."""
    from warden import drift, reference

    base = tmp_path_factory.mktemp("p7")
    ws = base / "ws"
    (ws / ".kiro").mkdir(parents=True)
    outside = base / "outside.md"
    outside.write_text("- outside\n")
    for sub, name, ext, kind in entries:
        d = ws / ".kiro" / sub
        d.mkdir(parents=True, exist_ok=True)
        p = d / (name + ext)
        if p.exists() or p.is_symlink():
            continue
        if kind == "text":
            p.write_text("---\ninclusion: always\n---\n- a rule\n")
        elif kind == "bigger":
            p.write_bytes(b"- y\n" * 2000)
        elif kind == "badjson":
            p.write_text("{nope")
        elif kind == "symlink-out":
            os.symlink(outside, p)
        else:
            target = ws / ".kiro" / "target.txt"
            target.write_text("t")
            os.symlink(target, p)
    before = snapshot_tree(base)
    snap = readonly.snapshot(ws)
    ref = {"rooms": {"r": {"steering": {".kiro/steering/a.md": {"X": ["a rule"]}}, "inclusion": {},
                           "hooks": {}, "guards": {}, "mcp": ["autoApprove"], "sandbox": {"enabled": True}}}}
    drift.compare(reference.merged_items(ref), snap, checked_at="t", reference_from={})
    assert snapshot_tree(base) == before
    assert "outside" not in " ".join(v.decode(errors="replace") for v in snap.files.values())
