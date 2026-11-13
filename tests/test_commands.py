import os
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from warden import commands as C
from warden.paths import Paths, overlaps
from warden.settings import DEMO_ROOMS, KNOWN_ROOMS, GitInstall, Settings, SettingsInvalid

UV = Path("/opt/homebrew/bin/uv")


def plan(paths, checkout, **kw):
    s = Settings(hauntlet_checkout=str(checkout), **kw)
    return C.build_plan(s, paths, UV, {"PATH": "/usr/bin", "HAUNTLET_DB": "/stray.db", "RENDER_EXTERNAL_URL": "https://x"})


def test_plan_order_and_shape(paths, checkout):
    p = plan(paths, checkout)
    labels = [c.label for c in p]
    assert labels[0] == "selftest"
    assert labels[1:3] == ["run threshold naive", "run threshold hardened"]
    assert [c.label for c in p if c.kind == "demo"] == [f"demo {r}" for r in DEMO_ROOMS]
    assert len(p) == 1 + 2 * len(KNOWN_ROOMS) + len(DEMO_ROOMS)
    sel = p[0]
    assert sel.argv == (str(UV), "run", "--offline", "--project", str(checkout), "hauntlet", "selftest")
    run = p[1]
    assert run.argv[-8:] == ("--room", "threshold", "--agent", "naive", "--repeat", "3", "--out", str(paths.reports))


def test_env_drops_inherited_hauntlet_and_render_vars(paths, checkout):
    env = plan(paths, checkout)[0].env
    assert env["HAUNTLET_DB"] == str(paths.hauntlet_db)
    assert env["HAUNTLET_BASE_URL"] == "http://127.0.0.1:8666"
    assert "RENDER_EXTERNAL_URL" not in env
    assert env["PATH"] == "/usr/bin"


def test_never_uses_directory_flag(paths, checkout):
    assert all("--directory" not in c.argv for c in plan(paths, checkout))


def test_no_uv_is_refused(paths, checkout):
    with pytest.raises(SettingsInvalid, match="uv not found"):
        C.build_plan(Settings(hauntlet_checkout=str(checkout)), paths, None, {})


def test_git_source_needs_the_install(paths):
    with pytest.raises(SettingsInvalid):
        C.build_plan(Settings(hauntlet_source="git"), paths, UV, {})
    s = Settings(hauntlet_source="git", git_install=GitInstall(True, "t", "/data/tools/bin/hauntlet"))
    p = C.build_plan(s, paths, UV, {})
    assert p[0].argv == ("/data/tools/bin/hauntlet", "selftest")
    assert p[0].env["UV_OFFLINE"] == "1"


def test_git_install_cmd_stays_inside_data_dir(paths):
    c = C.git_install_cmd(UV, paths, {})
    assert C.GIT_SOURCE_URL in c.argv
    assert c.env["UV_TOOL_DIR"] == str(paths.tools)
    assert c.env["UV_TOOL_BIN_DIR"] == str(paths.tools_bin)
    assert c.cwd == paths.range


def test_resolve_uv():
    s = Settings()
    assert C.resolve_uv(s, which=lambda _: "/x/uv") == Path("/x/uv")
    assert C.resolve_uv(s, which=lambda _: None, is_file=lambda p: p == "/opt/homebrew/bin/uv") == Path("/opt/homebrew/bin/uv")
    assert C.resolve_uv(s, which=lambda _: None, is_file=lambda p: False) is None
    assert C.resolve_uv(Settings(uv_path="/u/uv"), is_file=lambda p: True) == Path("/u/uv")


def test_range_overlapping_watched_workspace_is_refused(tmp_path, checkout):
    ws = tmp_path / "ws"
    paths = Paths(ws / "inner" / "data", ws / "inner" / "range")
    with pytest.raises(SettingsInvalid, match="watched workspace"):
        C.build_plan(Settings(hauntlet_checkout=str(checkout), watched_workspace=str(ws)), paths, UV, {})


segment = st.text(alphabet="abcdefghij", min_size=1, max_size=6)


@given(
    rooms=st.lists(st.sampled_from(KNOWN_ROOMS), min_size=1, max_size=6, unique=True),
    repeat=st.integers(1, 10),
    layout=st.sampled_from(["separate", "data-in-ws", "data-in-checkout", "ws-in-data"]),
    names=st.tuples(segment, segment, segment),
)
def test_p9_every_cmd_meets_the_invariants(tmp_path_factory, rooms, repeat, layout, names):
    """Property P9: every Cmd meets the commands invariants, or build_plan refuses."""
    base = tmp_path_factory.mktemp("p9")
    a, b, c = names
    checkout = base / f"co-{a}"
    ws = base / f"ws-{b}"
    data = base / f"data-{c}"
    if layout == "data-in-ws":
        data = ws / "data"
    elif layout == "data-in-checkout":
        data = checkout / "data"
    elif layout == "ws-in-data":
        ws = data / "ws"
    for d in (checkout, ws, data):
        d.mkdir(parents=True, exist_ok=True)
    paths = Paths(data, data.with_name(data.name + "-range"))
    s = Settings(hauntlet_checkout=str(checkout), watched_workspace=str(ws), rooms=tuple(rooms), repeat=repeat)
    try:
        p = C.build_plan(s, paths, UV, {"HAUNTLET_DB": "x"})
    except SettingsInvalid:
        assert layout != "separate"
        return
    assert layout == "separate"
    for cmd in p:
        assert cmd.cwd == paths.range
        assert not overlaps(cmd.cwd, ws) and not overlaps(cmd.cwd, checkout)
        assert os.path.isabs(cmd.env["HAUNTLET_DB"]) and Path(cmd.env["HAUNTLET_DB"]).is_relative_to(paths.range)
        assert cmd.env["HAUNTLET_BASE_URL"] == "http://127.0.0.1:8666"
        assert "--directory" not in cmd.argv
        assert cmd.argv[:6] == (str(UV), "run", "--offline", "--project", str(checkout), "hauntlet")
        if "--room" in cmd.argv:
            assert cmd.argv[cmd.argv.index("--room") + 1] in KNOWN_ROOMS
        if "--out" in cmd.argv:
            out = Path(cmd.argv[cmd.argv.index("--out") + 1])
            assert out.is_absolute() and out.is_relative_to(paths.range)
        assert all(isinstance(a, str) for a in cmd.argv)
