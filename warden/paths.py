"""Where Warden keeps things: its records in the app data dir, Hauntlet's files in the range dir."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

APP_DIR_NAME = "hauntlet-warden"


class RangeDirInvalid(ValueError):
    pass


def default_range_root(env: Mapping[str, str] | None = None, platform: str | None = None) -> Path:
    """Where Hauntlet runs: outside any ``.kiro`` directory (task 9 finding).

    Hauntlet's Exorcist refuses to write under a path with a ``.kiro`` component, and
    Crew's app data dir is ``~/.kiro/crew/apps/<name>/data``. So the range directory
    lives in the platform's user data location instead:

    - macOS: ``~/Library/Application Support/hauntlet-warden/range``
    - Linux: ``$XDG_DATA_HOME/hauntlet-warden/range`` (default ``~/.local/share``)
    """
    env = os.environ if env is None else env
    platform = sys.platform if platform is None else platform
    home = Path(env.get("HOME") or os.path.expanduser("~"))
    if platform == "darwin":
        base = home / "Library" / "Application Support"
    else:
        xdg = env.get("XDG_DATA_HOME", "")
        # XDG says a relative value is invalid and must be ignored; a value under .kiro
        # would bring back the refusal, so it is ignored too.
        base = Path(xdg) if xdg and os.path.isabs(xdg) and ".kiro" not in Path(xdg).parts else home / ".local" / "share"
    root = base / APP_DIR_NAME / "range"
    check_range_root(root)
    return root


def check_range_root(root: Path) -> None:
    if not root.is_absolute():
        raise RangeDirInvalid("the range directory must be absolute")
    if ".kiro" in root.parts or ".kiro" in Path(os.path.realpath(root)).parts:
        raise RangeDirInvalid("the range directory must not be inside a .kiro directory")


def _real(p: Path | str) -> Path:
    return Path(os.path.realpath(os.path.expanduser(str(p))))


def is_within(child: Path | str, parent: Path | str) -> bool:
    """True if ``child`` is ``parent`` or inside it, after resolving symlinks."""
    c, p = _real(child), _real(parent)
    return c == p or p in c.parents


def overlaps(a: Path | str, b: Path | str) -> bool:
    """True if either path is the other or inside it."""
    return is_within(a, b) or is_within(b, a)


@dataclass(frozen=True)
class Paths:
    """Warden's own records live in the app data dir; Hauntlet runs in ``range_root``."""

    data: Path
    range_root: Path

    @classmethod
    def for_app_root(cls, app_root: Path | str, env: Mapping[str, str] | None = None,
                     platform: str | None = None) -> "Paths":
        return cls(Path(app_root) / "data", default_range_root(env, platform))

    # Warden's own store
    @property
    def store(self) -> Path:
        return self.data / "warden"

    @property
    def runs(self) -> Path:
        return self.store / "runs"

    @property
    def settings_file(self) -> Path:
        return self.store / "settings.json"

    @property
    def latest(self) -> Path:
        return self.store / "latest.json"

    @property
    def drift_file(self) -> Path:
        return self.store / "drift.json"

    @property
    def reference_file(self) -> Path:
        return self.store / "reference.json"

    @property
    def summary(self) -> Path:
        return self.store / "summary.md"

    @property
    def lock(self) -> Path:
        return self.store / "run.lock"

    @property
    def run_request(self) -> Path:
        return self.store / "run-request.json"

    # The range directory: the working directory of every hauntlet command
    @property
    def range(self) -> Path:
        return self.range_root

    @property
    def hauntlet_db(self) -> Path:
        return self.range / ".hauntlet" / "range.db"

    @property
    def scratch(self) -> Path:
        return self.range / ".hauntlet" / "scratch"

    @property
    def bundles_root(self) -> Path:
        """Exorcist bundles land beside HAUNTLET_DB (spike H9)."""
        return self.range / ".hauntlet" / "exorcist"

    @property
    def reports(self) -> Path:
        return self.range / "reports"

    @property
    def exorcist_reports(self) -> Path:
        return self.range / "exorcist-reports"

    # The one-time git install (decision Q1) stays in Warden's own data dir
    @property
    def tools(self) -> Path:
        return self.data / "tools"

    @property
    def tools_bin(self) -> Path:
        return self.tools / "bin"

    def ensure(self) -> None:
        check_range_root(self.range)
        for d in (self.store, self.runs, self.range):
            d.mkdir(parents=True, exist_ok=True, mode=0o700)
