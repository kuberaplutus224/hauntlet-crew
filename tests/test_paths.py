"""The range directory lives outside any .kiro directory (task 9 finding).

Hauntlet's Exorcist refuses to write under a path with a ``.kiro`` component, and
Crew installs the app's data dir under ``~/.kiro/crew/apps/``.
"""

from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from warden.paths import Paths, RangeDirInvalid, check_range_root, default_range_root

APP_ROOT = "/Users/me/.kiro/crew/apps/hauntlet-warden"


def test_macos_default():
    p = Paths.for_app_root(APP_ROOT, env={"HOME": "/Users/me"}, platform="darwin")
    assert p.data == Path(APP_ROOT) / "data"
    assert p.range == Path("/Users/me/Library/Application Support/hauntlet-warden/range")
    assert p.store == Path(APP_ROOT) / "data" / "warden"  # Warden's records stay in the app data dir


def test_linux_xdg_and_default():
    assert default_range_root({"HOME": "/home/me", "XDG_DATA_HOME": "/srv/data"}, "linux") == \
        Path("/srv/data/hauntlet-warden/range")
    assert default_range_root({"HOME": "/home/me"}, "linux") == Path("/home/me/.local/share/hauntlet-warden/range")
    assert default_range_root({"HOME": "/home/me", "XDG_DATA_HOME": "relative"}, "linux") == \
        Path("/home/me/.local/share/hauntlet-warden/range")


def test_xdg_under_kiro_is_ignored():
    r = default_range_root({"HOME": "/home/me", "XDG_DATA_HOME": "/home/me/.kiro/share"}, "linux")
    assert ".kiro" not in r.parts


def test_everything_hauntlet_writes_is_outside_kiro():
    p = Paths.for_app_root(APP_ROOT, env={"HOME": "/Users/me"}, platform="darwin")
    for d in (p.range, p.hauntlet_db, p.scratch, p.bundles_root, p.reports, p.exorcist_reports):
        assert ".kiro" not in d.parts, d


def test_a_range_under_kiro_is_refused(tmp_path):
    with pytest.raises(RangeDirInvalid):
        check_range_root(Path("/Users/me/.kiro/crew/apps/x/data/range"))
    with pytest.raises(RangeDirInvalid):
        Paths(tmp_path / "data", tmp_path / ".kiro" / "range").ensure()


def test_build_plan_refuses_a_kiro_range(tmp_path, checkout):
    from warden.commands import build_plan
    from warden.settings import Settings, SettingsInvalid

    with pytest.raises(SettingsInvalid, match=r"\.kiro"):
        build_plan(Settings(hauntlet_checkout=str(checkout)), Paths(tmp_path / "d", tmp_path / ".kiro" / "r"),
                   Path("/x/uv"), {})


segment = st.text(alphabet="abcdefgh._-", min_size=1, max_size=8).filter(lambda s: s not in (".", ".."))


@given(home=st.lists(segment, min_size=1, max_size=4), kiro_depth=st.integers(0, 3),
       platform=st.sampled_from(["darwin", "linux"]), xdg=st.one_of(st.none(), st.lists(segment, min_size=1, max_size=3)))
def test_range_never_contains_kiro_even_when_data_is_under_kiro(home, kiro_depth, platform, xdg):
    """A data dir under ~/.kiro (where Crew installs apps) still yields a range dir outside it."""
    home_path = Path("/", *home)
    app_root = home_path.joinpath(*(["x"] * kiro_depth), ".kiro", "crew", "apps", "hauntlet-warden")
    env = {"HOME": str(home_path)}
    if xdg is not None:
        env["XDG_DATA_HOME"] = str(Path("/", *xdg))
    try:
        p = Paths.for_app_root(app_root, env=env, platform=platform)
    except RangeDirInvalid:
        # only when HOME itself is under a .kiro directory: refusing is the safe outcome
        assert ".kiro" in home_path.parts or (xdg is not None and ".kiro" in xdg and ".kiro" in home_path.parts)
        return
    assert ".kiro" in p.data.parts
    assert ".kiro" not in p.range.parts
    assert not p.range.is_relative_to(p.data)
