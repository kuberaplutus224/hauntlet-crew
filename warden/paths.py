"""Where Warden keeps things. Everything lives under the app's data dir."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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
    """The data dir layout (design.md "Glossary", spike S6 and H9)."""

    data: Path

    @classmethod
    def for_app_root(cls, app_root: Path | str) -> "Paths":
        return cls(Path(app_root) / "data")

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
        return self.data / "range"

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

    # The one-time git install (decision Q1) stays inside the data dir too
    @property
    def tools(self) -> Path:
        return self.data / "tools"

    @property
    def tools_bin(self) -> Path:
        return self.tools / "bin"

    def ensure(self) -> None:
        for d in (self.store, self.runs, self.range):
            d.mkdir(parents=True, exist_ok=True, mode=0o700)
