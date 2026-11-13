"""Change detection between two consecutive comparable runs (Requirement 6, P5).

``detect`` is pure. Comparing a record with itself, or with a re-ordered copy, yields
no changes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from warden.mask import mask

PREFIX = "Hauntlet Warden: "
MAX_LEN = 200
KIND_ORDER = ("selftest", "selftest_recovered", "run_error", "level", "drift")
NOT_COMPARABLE = ("skipped", "not_configured")
DRIFT_BAD = ("missing", "weaker")
DRIFT_SPECIAL = ("no reference yet", "not configured", "error")


@dataclass(frozen=True)
class Change:
    kind: str
    key: str
    before: str | None
    after: str

    def sort_key(self) -> tuple:
        return (KIND_ORDER.index(self.kind), self.key, self.before or "", self.after)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "key": self.key, "before": self.before, "after": self.after}


def comparable(rec: Mapping[str, Any] | None) -> bool:
    return bool(rec) and rec.get("status") not in NOT_COMPARABLE


def _level(entry: Any) -> str | None:
    if isinstance(entry, Mapping) and not entry.get("error") and isinstance(entry.get("worst"), str):
        return entry["worst"]
    return None


def _passed(rec: Mapping[str, Any] | None) -> bool | None:
    st = (rec or {}).get("selftest") or {}
    return st.get("passed") if isinstance(st.get("passed"), bool) else None


def _errset(rec: Mapping[str, Any]) -> set[tuple[str, str]]:
    return {(str(e.get("command", "")), str(e.get("kind", ""))) for e in rec.get("errors", []) or []}


def _drift_items(drift: Mapping[str, Any] | None) -> dict[str, str]:
    out = {}
    for f in (drift or {}).get("files", {}).values():
        for row in f.get("items", []):
            out[row["item"]] = row["status"]
    return out


def detect(prev: Mapping[str, Any] | None, new: Mapping[str, Any]) -> list[Change]:
    """Changes between ``prev`` (newest comparable earlier run, or None) and ``new``."""
    if not comparable(new):
        return []
    if prev is not None and not comparable(prev):
        prev = None
    changes: list[Change] = []
    new_passed = _passed(new)
    if new_passed is False and (prev is None or _passed(prev) is not False):
        changes.append(Change("selftest", "selftest", None, "failing"))
    if prev is not None and new_passed is True and _passed(prev) is False:
        changes.append(Change("selftest_recovered", "selftest", "failing", "passing"))
    if new.get("status") == "error":
        es = _errset(new)
        if prev is None or prev.get("status") != "error" or _errset(prev) != es:
            first = sorted(es)[0] if es else ("run", "error")
            changes.append(Change("run_error", first[0], None, first[1]))
    if prev is not None:
        for room, agents in sorted((new.get("rooms") or {}).items()):
            for agent, entry in sorted((agents or {}).items()):
                after = _level(entry)
                before = _level(((prev.get("rooms") or {}).get(room) or {}).get(agent))
                if after is not None and before is not None and after != before:
                    changes.append(Change("level", f"{room}/{agent}", before, after))
        pd, nd = prev.get("drift"), new.get("drift")
        # A drift baseline needs a real comparison on both sides for the same workspace.
        if (
            pd and nd
            and pd.get("status") not in DRIFT_SPECIAL and nd.get("status") not in DRIFT_SPECIAL
            and pd.get("workspace") and pd.get("workspace") == nd.get("workspace")
        ):
            old = _drift_items(pd)
            for item, st in sorted(_drift_items(nd).items()):
                if st in DRIFT_BAD and old.get(item) != st:
                    changes.append(Change("drift", item, old.get(item), st))
    return sorted(set(changes), key=Change.sort_key)


_ERROR_WORDS = {
    "unsynced": "checkout not synced, run uv sync",
    "timeout": "timed out",
    "budget": "not run (time budget)",
    "unparsed": "unparsed output",
    "exit": "failed",
    "start": "could not start",
}


def _short_item(item: str) -> str:
    return item.rsplit("/", 1)[-1]


def _part(c: Change) -> str:
    if c.kind == "level":
        return f"{c.key.replace('/', ' ')} {c.before}→{c.after}"
    if c.kind == "selftest":
        return "selftest failing"
    if c.kind == "selftest_recovered":
        return "selftest passing again"
    if c.kind == "run_error":
        return f"run error: {c.key} {_ERROR_WORDS.get(c.after, c.after)}"
    return f"drift: {_short_item(c.key)} {c.after}"


def render(changes: list[Change]) -> str:
    """One line, at most 200 characters, starting ``Hauntlet Warden:``."""
    parts = [mask(_part(c)) for c in changes]
    line = PREFIX
    for i, p in enumerate(parts):
        rest = len(parts) - i - 1
        sep = "" if i == 0 else "; "
        suffix = f"; +{rest} more" if rest else ""
        if len(line) + len(sep) + len(p) + len(suffix) <= MAX_LEN:
            line += sep + p
            continue
        more = f"{'; ' if i else ''}+{len(parts) - i} more"
        if len(line) + len(more) > MAX_LEN:  # the first part alone is too long
            line = line[: MAX_LEN - len(more) - 1] + "…"
        return line + more
    return line
