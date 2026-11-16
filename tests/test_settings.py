
import pytest

from warden import settings as S
from warden.settings import GitInstall, Settings, SettingsInvalid



def ok(checkout, ws="") -> Settings:
    return Settings(hauntlet_checkout=str(checkout), watched_workspace=str(ws))


def test_defaults_are_the_decided_ones():
    s = Settings()
    assert s.repeat == 3  # decision Q7
    assert s.rooms == S.KNOWN_ROOMS
    assert s.hauntlet_source == "checkout"
    assert "parlor" not in S.DEMO_ROOMS and len(S.DEMO_ROOMS) == 5


def test_valid_settings_have_no_errors(paths, checkout, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    assert S.validate(ok(checkout, ws), paths) == []


@pytest.mark.parametrize(
    "change, needle",
    [
        ({"hauntlet_checkout": ""}, "checkout path"),
        ({"hauntlet_checkout": "relative/path"}, "absolute"),
        ({"hauntlet_checkout": "/nonexistent/hauntlet"}, "does not exist"),
        ({"rooms": ()}, "at least one room"),
        ({"rooms": ("threshold", "threshold")}, "must not repeat"),
        ({"rooms": ("nosuch",)}, "rooms must be among"),
        ({"repeat": 0}, "repeat"),
        ({"repeat": 11}, "repeat"),
        ({"command_timeout_secs": 5}, "command_timeout_secs"),
        ({"watched_workspace": "/nonexistent/ws"}, "does not exist"),
        ({"uv_path": "uv"}, "uv_path"),
        ({"hauntlet_source": "pypi"}, "hauntlet_source"),
    ],
)
def test_invalid_settings_are_reported(paths, checkout, change, needle):
    from dataclasses import replace

    errors = S.validate(replace(ok(checkout), **change), paths)
    assert any(needle in e for e in errors), errors


def test_checkout_must_declare_hauntlet(paths, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (other / "pyproject.toml").write_text('[project]\nname = "not-hauntlet"\n')
    assert any("does not declare" in e for e in S.validate(ok(other), paths))


def test_workspace_or_checkout_may_not_overlap_data_dir(paths, checkout):
    assert any("overlap" in e for e in S.validate(ok(checkout, paths.data), paths))
    assert any("overlap" in e for e in S.validate(ok(checkout, paths.data.parent), paths))


def test_git_source_needs_the_approved_install_and_no_date(paths, tmp_path):
    s = Settings(hauntlet_source="git")
    errors = S.validate(s, paths)
    assert any("Install Hauntlet from GitHub" in e for e in errors)
    assert not any("2026" in e for e in errors)  # no date gate
    unapproved = Settings(hauntlet_source="git", git_install=GitInstall(False, None, str(tmp_path / "x")))
    assert any("Install Hauntlet from GitHub" in e for e in S.validate(unapproved, paths))
    tool = tmp_path / "hauntlet-tool"
    tool.write_text("#!/bin/sh\n")
    s2 = Settings(hauntlet_source="git", git_install=GitInstall(True, "2026-12-05T00:00:00Z", str(tool)))
    assert S.validate(s2, paths) == []


def test_from_dict_is_strict():
    with pytest.raises(SettingsInvalid):
        S.from_dict({"repeat": "3"})
    with pytest.raises(SettingsInvalid):
        S.from_dict({"repeat": True})
    with pytest.raises(SettingsInvalid):
        S.from_dict({"surprise": 1})
    with pytest.raises(SettingsInvalid):
        S.from_dict([])
    with pytest.raises(SettingsInvalid):
        S.from_dict({"git_install": {"approved": "yes"}})


def test_round_trip_and_load(paths, checkout):
    s = ok(checkout)
    S.save(paths, s)
    assert S.load(paths) == s
    assert S.from_dict(s.to_dict()) == s


def test_load_missing_and_malformed(paths):
    assert S.load(paths) is None
    paths.settings_file.write_text("{oops")
    with pytest.raises(SettingsInvalid):
        S.load(paths)


def test_client_update_cannot_set_git_install(checkout):
    current = Settings(git_install=GitInstall(True, "t", "/x/hauntlet"))
    new = S.with_client_update(current, {"hauntlet_checkout": str(checkout),
                                         "git_install": {"approved": True, "tool_path": "/evil"}})
    assert new.git_install == current.git_install
    assert S.with_client_update(None, {"git_install": {"approved": True}}).git_install == GitInstall()
