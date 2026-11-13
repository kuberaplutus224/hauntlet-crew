import json
import random
import shutil

import pytest
from hypothesis import given, strategies as st

from conftest import BUNDLES, WORKSPACES
from warden import CLIENT_NOTE, drift, readonly, reference as R
from warden.readonly import WorkspaceSnapshot

ROOMS = ["cursed-repo", "cursed-repo-tests", "poltergeist", "poltergeist-legacy", "threshold"]


@pytest.fixture(scope="module")
def ref(tmp_path_factory):
    root = tmp_path_factory.mktemp("bundles")
    staged = []
    for room in ROOMS:
        dst = root / room / "b"
        shutil.copytree(BUNDLES / room, dst)
        staged.append((room, dst))
    return R.update(None, R.all_fragments(staged, root, "RUN1"))


def check(ref, ws_path):
    return drift.compare(R.merged_items(ref), readonly.snapshot(ws_path), checked_at="T",
                         reference_from=R.reference_rooms(ref))


def statuses(report):
    return {row["item"]: row["status"] for f in report["files"].values() for row in f["items"]}


def test_complete_workspace_is_all_present(ref):
    rep = check(ref, WORKSPACES / "complete")
    assert set(statuses(rep).values()) == {"present"}, rep
    assert rep["status"] == "present"
    assert rep["note"] == CLIENT_NOTE
    assert rep["warnings"] == []


def test_weaker_workspace_item_by_item(ref):
    st_ = statuses(check(ref, WORKSPACES / "weaker"))
    assert st_[".kiro/steering/untrusted-content.md#DATA"] == "missing"
    assert st_[".kiro/steering/untrusted-content.md#REPORT"] == "missing"
    assert st_[".kiro/steering/credentials.md#SECRETS"] == "weaker"  # inclusion: manual
    assert st_[".kiro/steering/unrequested-actions.md#LINKS"] == "present"
    assert st_[".kiro/hooks/credential-egress.json#credential-egress-web"] == "weaker"  # narrower matcher
    assert st_[".kiro/hooks/credential-egress.json#credential-egress-mcp"] == "weaker"  # agent action
    assert st_[".kiro/hooks/credential-egress.json#credential-egress-write"] == "missing"
    assert st_[".kiro/hooks/credential-egress.json#credential-egress-shell"] == "present"
    assert st_[".kiro/hooks/guards/credential_egress.py"] == "review"  # edited guard
    assert st_[".kiro/settings/sandbox.json#networkAccess"] == "weaker"
    assert st_[".kiro/settings/sandbox.json#mcpSandboxing"] == "weaker"
    assert st_[".kiro/settings/sandbox.json#enabled"] == "present"
    assert st_["mcp.json#autoApprove"] == "weaker"
    assert st_["mcp.json#disabledTools"] == "review"


def test_weaker_details_name_the_problem(ref):
    rep = check(ref, WORKSPACES / "weaker")
    rows = {r["item"]: r for f in rep["files"].values() for r in f["items"]}
    assert "github" in rows["mcp.json#autoApprove"]["detail"]
    assert "ALLOW_ALL" in rows[".kiro/settings/sandbox.json#networkAccess"]["detail"]
    assert "manual" in rows[".kiro/steering/credentials.md#SECRETS"]["detail"]
    assert rep["files"][".kiro/steering/untrusted-content.md"]["status"] == "missing"
    assert rep["status"] == "missing"


def test_empty_workspace(ref):
    st_ = statuses(check(ref, WORKSPACES / "empty"))
    assert st_["mcp.json#autoApprove"] == "n/a"
    assert st_[".kiro/settings/sandbox.json#networkAccess"] == "missing"
    assert all(v in ("missing", "n/a") for v in st_.values())


def test_hostile_workspace_warns_about_a_room_server(ref, hostile_workspace):
    rep = check(ref, hostile_workspace)
    assert "A Hauntlet room server is configured in this workspace: room" in rep["warnings"]
    assert any("symlink" in w for w in rep["warnings"])


def test_steering_moved_to_another_always_file_is_present(ref, workspace_copy):
    ws = workspace_copy("complete")
    text = (ws / ".kiro/steering/credentials.md").read_text()
    (ws / ".kiro/steering/credentials.md").unlink()
    (ws / ".kiro/steering/team.md").write_text(text)
    rows = {r["item"]: r for f in check(ref, ws)["files"].values() for r in f["items"]}
    assert rows[".kiro/steering/credentials.md#SECRETS"]["status"] == "present"
    assert "team.md" in rows[".kiro/steering/credentials.md#SECRETS"]["detail"]


def test_renamed_hook_is_present(ref, workspace_copy):
    ws = workspace_copy("complete")
    f = ws / ".kiro/hooks/credential-egress.json"
    data = json.loads(f.read_text())
    data["hooks"][0]["name"] = "our-own-name"
    f.write_text(json.dumps(data))
    assert set(statuses(check(ref, ws)).values()) == {"present"}


def test_invalid_json_hook_file_is_weaker_not_fixed(ref, workspace_copy):
    ws = workspace_copy("complete")
    f = ws / ".kiro/hooks/credential-egress.json"
    f.write_text("{broken")
    rows = {r["item"]: r for fl in check(ref, ws)["files"].values() for r in fl["items"]}
    assert rows[".kiro/hooks/credential-egress.json#credential-egress-web"]["status"] == "weaker"
    assert rows[".kiro/hooks/credential-egress.json#credential-egress-web"]["detail"] == drift.INVALID_JSON
    assert f.read_text() == "{broken"


def test_no_reference_gives_no_items():
    snap = readonly.snapshot(WORKSPACES / "complete")
    rep = drift.compare([], snap, checked_at="T", reference_from={})
    assert rep["files"] == {} and rep["status"] == "n/a"


# -- properties ----------------------------------------------------------------


def _shuffled_snapshot(snap: WorkspaceSnapshot, rnd: random.Random) -> WorkspaceSnapshot:
    files = {}
    for rel in rnd.sample(sorted(snap.files), len(snap.files)):
        data = snap.files[rel]
        if rel.endswith(".md"):
            text = data.decode()
            head, _, body = text.partition("\n---\n")
            lines = body.splitlines()
            rnd.shuffle(lines)
            data = (head + "\n---\n" + "\n".join(lines) + "\n").encode()
        elif rel.endswith(".json"):
            obj = json.loads(data)
            if isinstance(obj.get("hooks"), list):
                rnd.shuffle(obj["hooks"])
            if isinstance(obj.get("mcpServers"), dict):
                items = list(obj["mcpServers"].items())
                rnd.shuffle(items)
                obj["mcpServers"] = dict(items)
            data = json.dumps(obj).encode()
        files[rel] = data
    return WorkspaceSnapshot(snap.root, files, snap.warnings)


@given(seed=st.integers(0, 10_000), which=st.sampled_from(["complete", "weaker", "empty"]))
def test_p3_drift_is_order_independent(ref, seed, which):
    """Property P3: permuting items, bundles, files, bullets, hooks and servers changes nothing."""
    rnd = random.Random(seed)
    snap = readonly.snapshot(WORKSPACES / which)
    base = drift.compare(R.merged_items(ref), snap, checked_at="T", reference_from=R.reference_rooms(ref))
    rooms = list(ref["rooms"].items())
    rnd.shuffle(rooms)
    ref2 = {"rooms": dict(rooms)}
    items = R.merged_items(ref2)
    rnd.shuffle(items)
    other = drift.compare(items, _shuffled_snapshot(snap, rnd), checked_at="T",
                          reference_from=R.reference_rooms(ref2))
    assert other == base


FIXES = ["steering", "hook", "sandbox", "guard"]


@given(st.lists(st.sampled_from(FIXES), min_size=1, max_size=4, unique=True))
def test_p4_adding_a_reference_guardrail_never_worsens(ref, tmp_path_factory, fixes):
    """Property P4: adding a reference bullet, hook, guard or sandbox key never makes a status worse."""
    ws = tmp_path_factory.mktemp("p4") / "ws"
    shutil.copytree(WORKSPACES / "weaker", ws)
    before = statuses(check(ref, ws))
    src = BUNDLES / "poltergeist" / ".kiro"
    if "steering" in fixes:
        (ws / ".kiro/steering/added.md").write_text((src / "steering/untrusted-content.md").read_text())
    if "hook" in fixes:
        (ws / ".kiro/hooks/added.json").write_text((src / "hooks/credential-egress.json").read_text())
    if "guard" in fixes:
        shutil.copy(src / "hooks/guards/credential_egress.py", ws / ".kiro/hooks/guards/credential_egress.py")
    if "sandbox" in fixes:
        sb = json.loads((ws / ".kiro/settings/sandbox.json").read_text())
        sb.update({"networkAccess": "DEFAULT_BLOCKED", "mcpSandboxing": True})
        (ws / ".kiro/settings/sandbox.json").write_text(json.dumps(sb))
    after = statuses(check(ref, ws))
    for item, st_ in before.items():
        assert drift.RANK[after[item]] <= drift.RANK[st_], (item, st_, after[item])
