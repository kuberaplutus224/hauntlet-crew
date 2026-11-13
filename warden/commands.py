"""The only place a Hauntlet command is shaped (Requirement 5, Property P9)."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from warden.paths import Paths, RangeDirInvalid, check_range_root, overlaps
from warden.settings import DEMO_ROOMS, KNOWN_ROOMS, Settings, SettingsInvalid

#: The one allow-listed non-loopback URL (decision Q1). Used only by the one-time,
#: user-approved install; nightly runs never contact it.
GIT_SOURCE_URL = "git+https://github.com/kuberaplutus224/hauntlet"
BASE_URL = "http://127.0.0.1:8666"
AGENTS = ("naive", "hardened")
#: Inherited variables that could redirect Hauntlet (spike 1.2: the cron child
#: inherits the gateway's environment).
_DROP_PREFIXES = ("HAUNTLET_", "RENDER_")
_UV_FALLBACKS = ("~/.local/bin/uv", "/opt/homebrew/bin/uv", "/usr/local/bin/uv")


@dataclass(frozen=True)
class Cmd:
    label: str
    kind: str  # "selftest" | "run" | "demo" | "git-install"
    argv: tuple[str, ...]
    cwd: Path
    env: dict[str, str] = field(compare=False, hash=False)
    timeout: float
    room: str | None = None
    agent: str | None = None


def resolve_uv(
    s: Settings,
    *,
    which: Callable[[str], str | None] = shutil.which,
    is_file: Callable[[str], bool] = os.path.isfile,
) -> Path | None:
    if s.uv_path:
        return Path(s.uv_path) if is_file(s.uv_path) else None
    found = which("uv")
    if found:
        return Path(found)
    for cand in _UV_FALLBACKS:
        p = os.path.expanduser(cand)
        if is_file(p):
            return Path(p)
    return None


def child_env(base: Mapping[str, str], paths: Paths) -> dict[str, str]:
    env = {k: v for k, v in base.items() if not k.startswith(_DROP_PREFIXES)}
    env["HAUNTLET_DB"] = str(paths.hauntlet_db)
    env["HAUNTLET_BASE_URL"] = BASE_URL
    return env


def hauntlet_prefix(s: Settings, uv: Path | None) -> tuple[str, ...]:
    if s.hauntlet_source == "checkout":
        if uv is None:
            raise SettingsInvalid(["uv not found; set uv_path"])
        return (str(uv), "run", "--offline", "--project", s.hauntlet_checkout, "hauntlet")
    if s.hauntlet_source == "git":
        if not (s.git_install.approved and s.git_install.tool_path):
            raise SettingsInvalid(["Install Hauntlet from GitHub on the Warden page first"])
        return (s.git_install.tool_path,)
    raise SettingsInvalid(["hauntlet_source must be 'checkout' or 'git'"])


def _check_range(s: Settings, paths: Paths) -> None:
    errs = []
    try:
        check_range_root(paths.range)
    except RangeDirInvalid as exc:
        errs.append(str(exc))
    # Checked against both the data dir and the range dir, so neither the checkout nor
    # the watched workspace can hold, or sit inside, anything Warden writes.
    for own in (paths.data, paths.range):
        if s.hauntlet_source == "checkout" and s.hauntlet_checkout and overlaps(own, s.hauntlet_checkout):
            errs.append("the Hauntlet checkout must not overlap Warden's data or range directory")
        if s.watched_workspace and overlaps(own, s.watched_workspace):
            errs.append("the watched workspace must not overlap Warden's data or range directory")
    errs = list(dict.fromkeys(errs))
    bad = [r for r in s.rooms if r not in KNOWN_ROOMS]
    if bad:
        errs.append(f"unknown rooms: {', '.join(bad)}")
    if errs:
        raise SettingsInvalid(errs)


def build_plan(s: Settings, paths: Paths, uv: Path | None, base_env: Mapping[str, str]) -> list[Cmd]:
    """The nightly sequence (Requirement 2.4): selftest, runs, demos."""
    _check_range(s, paths)
    pre = hauntlet_prefix(s, uv)
    env = child_env(base_env, paths)
    if s.hauntlet_source == "git":
        env["UV_OFFLINE"] = "1"
    t = float(s.command_timeout_secs)
    plan = [Cmd("selftest", "selftest", pre + ("selftest",), paths.range, env, t)]
    for room in s.rooms:
        for agent in AGENTS:
            argv = pre + ("run", "--room", room, "--agent", agent, "--repeat", str(s.repeat), "--out", str(paths.reports))
            plan.append(Cmd(f"run {room} {agent}", "run", argv, paths.range, env, t, room, agent))
    for room in s.rooms:
        if room in DEMO_ROOMS:
            argv = pre + ("exorcist", "demo", "--room", room, "--out", str(paths.exorcist_reports))
            plan.append(Cmd(f"demo {room}", "demo", argv, paths.range, env, t, room))
    return plan


def git_install_cmd(uv: Path, paths: Paths, base_env: Mapping[str, str]) -> Cmd:
    """The one-time install the user approves on the page (decision Q1).

    The tool is installed inside Warden's data dir, so nothing outside it changes.
    """
    env = child_env(base_env, paths)
    env["UV_TOOL_DIR"] = str(paths.tools)
    env["UV_TOOL_BIN_DIR"] = str(paths.tools_bin)
    argv = (str(uv), "tool", "install", "--force", "--from", GIT_SOURCE_URL, "hauntlet")
    return Cmd("git-install", "git-install", argv, paths.range, env, 300.0)
