"""Reference × watched .kiro/ → drift report (Requirement 4.3–4.5, design.md "Drift rules").

``compare`` is pure. It reads only the snapshot it is given, and its output is sorted,
which makes it order-independent (Property P3).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from warden import CLIENT_NOTE
from warden.readonly import WorkspaceSnapshot
from warden.reference import Item, bullets, frontmatter_inclusion, guard_in, normalise

SCHEMA = 1
RANK = {"n/a": 0, "present": 1, "review": 2, "weaker": 3, "missing": 4}
MCP_FILE = ".kiro/settings/mcp.json"
SANDBOX_FILE = ".kiro/settings/sandbox.json"
INVALID_JSON = "file is not valid JSON"


def worst(statuses: Sequence[str]) -> str:
    return max(statuses, key=RANK.__getitem__) if statuses else "n/a"


def _json(snap: WorkspaceSnapshot, rel: str) -> tuple[bool, Any]:
    """(present, parsed). parsed is INVALID_JSON when the file is not valid JSON."""
    text = snap.text(rel)
    if text is None:
        return False, None
    try:
        return True, json.loads(text)
    except json.JSONDecodeError:
        return True, INVALID_JSON


def _steering_index(snap: WorkspaceSnapshot) -> list[tuple[str, str, set[str]]]:
    out = []
    for rel in sorted(snap.files):
        if rel.startswith(".kiro/steering/") and rel.endswith(".md"):
            text = snap.text(rel) or ""
            out.append((rel, frontmatter_inclusion(text), {normalise(b) for b in bullets(text)}))
    return out


def _hooks_index(snap: WorkspaceSnapshot) -> tuple[list[dict], set[str]]:
    hooks, invalid = [], set()
    for rel in sorted(snap.files):
        if not (rel.startswith(".kiro/hooks/") and rel.endswith(".json") and rel.count("/") == 2):
            continue
        _, data = _json(snap, rel)
        if data == INVALID_JSON or not isinstance(data, dict) or not isinstance(data.get("hooks"), list):
            invalid.add(rel)
            continue
        for h in data["hooks"]:
            if isinstance(h, dict):
                action = h.get("action") if isinstance(h.get("action"), dict) else {}
                hooks.append({
                    "file": rel,
                    "name": str(h.get("name", "")),
                    "trigger": str(h.get("trigger", "")),
                    "matcher": str(h.get("matcher", "")),
                    "type": str(action.get("type", "")),
                    "command": str(action.get("command", "")),
                })
    return hooks, invalid


def _steering(item: Item, parts: list[dict], index) -> tuple[str, str]:
    wanted = {normalise(p["text"]) for p in parts}
    hits = [(rel, inc) for rel, inc, bl in index if wanted & bl]
    always = [rel for rel, inc in hits if inc == "always"]
    if always:
        where = sorted(always)[0]
        return "present", "" if where == item.file else f"found in {where}"
    if hits:
        rel, inc = sorted(hits)[0]
        return "weaker", f"only in {rel} (inclusion: {inc}); loaded only when that mode applies"
    return "missing", "rule text not found in any steering file"


def _hook(item: Item, variants: list[dict], hooks: list[dict], invalid: set[str]) -> tuple[str, str]:
    name = item.key.rsplit("#", 1)[1]

    def runs_guard(h: dict, v: dict) -> bool:
        return h["type"] == "command" and v.get("guard") and guard_in(h["command"]) == v["guard"]

    same = [h for h in hooks if h["name"] == name]
    for h in same:
        for v in variants:
            if h["trigger"] == v["trigger"] and h["matcher"] == v["matcher"] and runs_guard(h, v):
                return "present", "" if h["file"] == item.file else f"found in {h['file']}"
    for h in hooks:  # renamed
        for v in variants:
            if h["trigger"] == v["trigger"] and h["matcher"] == v["matcher"] and runs_guard(h, v):
                return "present", f"found as {h['name']} in {h['file']}"
    if same:
        h, v = sorted(same, key=lambda x: x["file"])[0], variants[0]
        if h["trigger"] != v["trigger"]:
            return "weaker", f"trigger is {h['trigger'] or 'unset'}, generated is {v['trigger']}"
        if h["type"] != "command":
            return "weaker", f"action is {h['type'] or 'unset'}, so it is advisory, not enforced"
        if not runs_guard(h, v):
            return "weaker", "does not run the generated guard"
        if h["matcher"] != v["matcher"] and h["matcher"] in v["matcher"]:
            return "weaker", f"matcher {h['matcher']!r} is narrower than {v['matcher']!r}"
        return "review", f"matcher {h['matcher']!r} differs from {v['matcher']!r}"
    if item.file in invalid:
        return "weaker", INVALID_JSON
    return "missing", "no hook with this name or this trigger and matcher"


def _guard(item: Item, digests: list[str], snap: WorkspaceSnapshot) -> tuple[str, str]:
    data = snap.files.get(item.file)
    if data is None:
        return "missing", "guard script not found"
    if hashlib.sha256(data).hexdigest() in digests:
        return "present", ""
    return "review", "differs from the generated guard"


def _mcp(item: Item, prop: str, snap: WorkspaceSnapshot) -> tuple[str, str]:
    present, data = _json(snap, MCP_FILE)
    if not present:
        return "n/a", "no mcp.json"
    if data == INVALID_JSON:
        return "weaker", INVALID_JSON
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(servers, dict) or not servers:
        return "n/a", "no MCP servers"
    if prop == "autoApprove":
        bad = sorted(n for n, s in servers.items() if isinstance(s, dict) and s.get("autoApprove"))
        return ("weaker", f"autoApprove is not empty for: {', '.join(bad)}") if bad else ("present", "")
    bad = sorted(
        n for n, s in servers.items()
        if not (isinstance(s, dict) and isinstance(s.get("disabledTools"), list) and s["disabledTools"])
    )
    if bad:
        return "review", f"no disabledTools for: {', '.join(bad)} (only you know which tools the task needs)"
    return "present", ""


def _sandbox(item: Item, key: str, expected: Any, snap: WorkspaceSnapshot) -> tuple[str, str]:
    present, data = _json(snap, SANDBOX_FILE)
    if not present:
        return "missing", "no sandbox.json"
    if data == INVALID_JSON or not isinstance(data, dict):
        return "weaker", INVALID_JSON
    actual = data.get(key)
    if actual == expected:
        return "present", ""
    return "weaker", f"{key} is {json.dumps(actual)}, generated is {json.dumps(expected)}"


def _warnings(snap: WorkspaceSnapshot) -> list[str]:
    out = list(snap.warnings)
    present, data = _json(snap, MCP_FILE)
    if present and isinstance(data, dict) and isinstance(data.get("mcpServers"), dict):
        for name, s in sorted(data["mcpServers"].items()):
            if not isinstance(s, dict):
                continue
            args = s.get("args") if isinstance(s.get("args"), list) else []
            joined = " ".join([str(s.get("command", ""))] + [str(a) for a in args])
            if "hauntlet" in joined and "mcp serve" in joined:
                out.append(f"A Hauntlet room server is configured in this workspace: {name}")
    return sorted(set(out))


def compare(
    items: Sequence[Item],
    snap: WorkspaceSnapshot,
    *,
    checked_at: str,
    reference_from: Mapping[str, str],
) -> dict[str, Any]:
    index = _steering_index(snap)
    hooks, invalid = _hooks_index(snap)
    files: dict[str, list[dict]] = {}
    for it in items:
        parts = [json.loads(p) for p in it.expect]
        if it.kind == "steering":
            st, detail = _steering(it, parts, index)
        elif it.kind == "hook":
            st, detail = _hook(it, parts, hooks, invalid)
        elif it.kind == "guard":
            st, detail = _guard(it, parts, snap)
        elif it.kind == "mcp":
            st, detail = _mcp(it, parts[0], snap)
        elif it.kind == "sandbox":
            # parts are [key, value] pairs; any generated value counts
            key = parts[0][0]
            results = [_sandbox(it, key, v, snap) for _, v in parts]
            st, detail = min(results, key=lambda r: RANK[r[0]])
        else:
            continue
        files.setdefault(it.file, []).append(
            {"item": it.key, "kind": it.kind, "status": st, "rooms": list(it.rooms), "detail": detail}
        )
    out_files = {}
    for f in sorted(files):
        rows = sorted(files[f], key=lambda r: r["item"])
        out_files[f] = {"status": worst([r["status"] for r in rows]), "items": rows}
    return {
        "schema": SCHEMA,
        "checked_at": checked_at,
        "workspace": snap.root,
        "reference_from": dict(sorted(reference_from.items())),
        "status": worst([f["status"] for f in out_files.values()]),
        "files": out_files,
        "warnings": _warnings(snap),
        "note": CLIENT_NOTE,
    }


def special(status: str, *, checked_at: str, workspace: str = "", error: str = "") -> dict[str, Any]:
    """A drift report that could not compare: no reference, not configured, or an error."""
    return {
        "schema": SCHEMA,
        "checked_at": checked_at,
        "workspace": workspace,
        "reference_from": {},
        "status": status,
        "files": {},
        "warnings": [],
        "error": error,
        "note": CLIENT_NOTE,
    }
