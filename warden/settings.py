"""Warden settings: one JSON file the backend writes and the cron reads (Requirement 8.4)."""

from __future__ import annotations

import datetime as _dt
import json
import os
import tomllib
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from warden.paths import Paths, overlaps

KNOWN_ROOMS: tuple[str, ...] = (
    "threshold",
    "cursed-repo",
    "cursed-repo-tests",
    "poltergeist",
    "poltergeist-legacy",
    "parlor",
)
#: ``hauntlet exorcist demo`` supports every room except parlor (decision Q6).
DEMO_ROOMS: tuple[str, ...] = tuple(r for r in KNOWN_ROOMS if r != "parlor")
#: The Hauntlet repository becomes public on this date (decision Q1).
GIT_PUBLIC_DATE = _dt.date(2026, 12, 4)

SOURCES = ("checkout", "git")
REPEAT_RANGE = (1, 10)
TIMEOUT_RANGE = (10, 600)


class SettingsInvalid(ValueError):
    """Settings that cannot be loaded or used. ``errors`` lists every problem."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class GitInstall:
    approved: bool = False
    installed_at: str | None = None
    tool_path: str | None = None


@dataclass(frozen=True)
class Settings:
    schema: int = 1
    hauntlet_source: str = "checkout"
    hauntlet_checkout: str = ""
    git_install: GitInstall = field(default_factory=GitInstall)
    uv_path: str = ""
    watched_workspace: str = ""
    rooms: tuple[str, ...] = KNOWN_ROOMS
    repeat: int = 3
    command_timeout_secs: int = 150

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["rooms"] = list(self.rooms)
        return d


_FIELDS = {
    "schema": int,
    "hauntlet_source": str,
    "hauntlet_checkout": str,
    "git_install": dict,
    "uv_path": str,
    "watched_workspace": str,
    "rooms": list,
    "repeat": int,
    "command_timeout_secs": int,
}


def from_dict(d: Any) -> Settings:
    """Parse with strict JSON types. Unknown keys and wrong types are refused."""
    if not isinstance(d, dict):
        raise SettingsInvalid(["settings must be a JSON object"])
    errors: list[str] = []
    unknown = sorted(set(d) - set(_FIELDS))
    if unknown:
        errors.append(f"unknown settings: {', '.join(unknown)}")
    for key, typ in _FIELDS.items():
        if key in d:
            v = d[key]
            # bool is an int subclass; refuse it for int fields
            if typ is int and (isinstance(v, bool) or not isinstance(v, int)):
                errors.append(f"{key} must be a whole number")
            elif typ is not int and not isinstance(v, typ):
                errors.append(f"{key} must be a JSON {typ.__name__}")
    if errors:
        raise SettingsInvalid(errors)
    gi = d.get("git_install", {})
    gi_errors = []
    if not isinstance(gi.get("approved", False), bool):
        gi_errors.append("git_install.approved must be true or false")
    for k in ("installed_at", "tool_path"):
        if gi.get(k) is not None and not isinstance(gi.get(k), str):
            gi_errors.append(f"git_install.{k} must be a string or null")
    if set(gi) - {"approved", "installed_at", "tool_path"}:
        gi_errors.append("git_install has unknown keys")
    rooms = d.get("rooms", list(KNOWN_ROOMS))
    if not all(isinstance(r, str) for r in rooms):
        gi_errors.append("rooms must be a list of room names")
    if gi_errors:
        raise SettingsInvalid(gi_errors)
    return Settings(
        schema=d.get("schema", 1),
        hauntlet_source=d.get("hauntlet_source", "checkout"),
        hauntlet_checkout=d.get("hauntlet_checkout", ""),
        git_install=GitInstall(
            approved=gi.get("approved", False),
            installed_at=gi.get("installed_at"),
            tool_path=gi.get("tool_path"),
        ),
        uv_path=d.get("uv_path", ""),
        watched_workspace=d.get("watched_workspace", ""),
        rooms=tuple(rooms),
        repeat=d.get("repeat", 3),
        command_timeout_secs=d.get("command_timeout_secs", 150),
    )


def _is_hauntlet_checkout(path: Path) -> bool:
    try:
        with open(path / "pyproject.toml", "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return False
    return data.get("project", {}).get("name") == "hauntlet"


def validate(s: Settings, paths: Paths, *, today: _dt.date | None = None) -> list[str]:
    """Return every reason these settings cannot run a nightly check (empty = runnable)."""
    today = today or _dt.date.today()
    errors: list[str] = []
    if s.schema != 1:
        errors.append("unsupported settings schema")
    if s.hauntlet_source not in SOURCES:
        errors.append("hauntlet_source must be 'checkout' or 'git'")
    elif s.hauntlet_source == "checkout":
        c = s.hauntlet_checkout
        if not c:
            errors.append("set the Hauntlet checkout path")
        elif not os.path.isabs(c):
            errors.append("the Hauntlet checkout must be an absolute path")
        elif not Path(c).is_dir():
            errors.append("the Hauntlet checkout does not exist")
        elif not _is_hauntlet_checkout(Path(c)):
            errors.append("the checkout's pyproject.toml does not declare the project 'hauntlet'")
        elif overlaps(c, paths.data) or overlaps(c, paths.range):
            errors.append("the Hauntlet checkout must not overlap Warden's data or range directory")
    else:  # git
        if today < GIT_PUBLIC_DATE:
            errors.append(f"the git source is available from {GIT_PUBLIC_DATE.isoformat()}")
        elif not s.git_install.approved or not s.git_install.tool_path:
            errors.append("Install Hauntlet from GitHub on the Warden page first")
        elif not Path(s.git_install.tool_path).is_file():
            errors.append("the installed Hauntlet tool is missing; install it again")
    w = s.watched_workspace
    if w:
        if not os.path.isabs(w):
            errors.append("the watched workspace must be an absolute path")
        elif not Path(w).is_dir():
            errors.append("the watched workspace does not exist")
        elif overlaps(w, paths.data) or overlaps(w, paths.range):
            errors.append("the watched workspace must not overlap Warden's data or range directory")
    if not s.rooms:
        errors.append("choose at least one room")
    elif len(set(s.rooms)) != len(s.rooms):
        errors.append("rooms must not repeat")
    elif any(r not in KNOWN_ROOMS for r in s.rooms):
        errors.append(f"rooms must be among: {', '.join(KNOWN_ROOMS)}")
    if not REPEAT_RANGE[0] <= s.repeat <= REPEAT_RANGE[1]:
        errors.append(f"repeat must be {REPEAT_RANGE[0]} to {REPEAT_RANGE[1]}")
    if not TIMEOUT_RANGE[0] <= s.command_timeout_secs <= TIMEOUT_RANGE[1]:
        errors.append(f"command_timeout_secs must be {TIMEOUT_RANGE[0]} to {TIMEOUT_RANGE[1]}")
    if s.uv_path and (not os.path.isabs(s.uv_path) or not Path(s.uv_path).is_file()):
        errors.append("uv_path must be an absolute path to the uv program")
    return errors


def load(paths: Paths) -> Settings | None:
    """The saved settings, or None if none were saved. Malformed JSON raises SettingsInvalid."""
    try:
        raw = paths.settings_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        return from_dict(json.loads(raw))
    except json.JSONDecodeError as exc:
        raise SettingsInvalid([f"settings.json is not valid JSON: {exc.msg}"]) from exc


def save(paths: Paths, s: Settings) -> None:
    from warden.store import atomic_write_json

    paths.ensure()
    atomic_write_json(paths.settings_file, s.to_dict())


def with_client_update(current: Settings | None, incoming: dict[str, Any]) -> Settings:
    """Apply a settings update from the page. ``git_install`` is backend-owned and kept."""
    if not isinstance(incoming, dict):
        raise SettingsInvalid(["settings must be a JSON object"])
    body = {k: v for k, v in incoming.items() if k != "git_install"}
    new = from_dict(body)
    return replace(new, git_install=(current.git_install if current else GitInstall()))
