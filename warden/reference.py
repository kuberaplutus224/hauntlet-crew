"""Exorcist demo bundles → the guardrail reference the drift check compares against.

The reference is one fragment per demo room (design.md "Reference"). It keeps only
what the comparison needs. It never keeps an MCP server's name, command, arguments
or environment (Requirement 10.1).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from warden.paths import is_within

SCHEMA = 1
_GUARD = re.compile(r"(\.kiro/hooks/guards/[A-Za-z0-9_.-]+\.py)")
_FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)


class BundleRefused(ValueError):
    pass


def frontmatter_inclusion(text: str) -> str:
    """The steering ``inclusion`` mode. Kiro's default is ``always``."""
    m = _FRONT.match(text.replace("\r\n", "\n"))
    if not m:
        return "always"
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        if k.strip() == "inclusion":
            return v.strip().strip("'\"") or "always"
    return "always"


def bullets(text: str) -> list[str]:
    return [line.strip()[2:].strip() for line in text.splitlines() if line.strip().startswith("- ")]


def normalise(text: str) -> str:
    return " ".join(text.split()).rstrip(".;:!").casefold()


def guard_in(command: str) -> str | None:
    m = _GUARD.search(command or "")
    return m.group(1) if m else None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fragment_from_bundle(bundle: Path, bundles_root: Path, *, from_run: str) -> dict[str, Any]:
    """One room's reference fragment, read from one demo bundle."""
    if not is_within(bundle, bundles_root):
        raise BundleRefused("bundle is outside the range's exorcist directory")
    meta = json.loads((bundle / "bundle.json").read_text(encoding="utf-8"))
    items = meta.get("items", [])
    frag: dict[str, Any] = {
        "from_run": from_run,
        "steering": {},
        "inclusion": {},
        "hooks": {},
        "guards": {},
        "mcp": [],
        "sandbox": {},
        "cannot_fix_titles": sorted({c.get("title", "") for c in meta.get("cannot_fix", []) if c.get("title")}),
    }
    by_path: dict[str, list[str]] = {}
    for it in items:
        if it.get("kind") == "steering":
            by_path.setdefault(it["path"], []).append(it["rule"])
    for path, rules in by_path.items():
        text = (bundle / path).read_text(encoding="utf-8")
        bl = bullets(text)
        frag["inclusion"][path] = frontmatter_inclusion(text)
        if len(bl) == len(rules):  # verified order mapping (spike H10)
            frag["steering"][path] = {rule: [b] for rule, b in zip(rules, bl)}
        else:  # fallback: by bullet text, without rule IDs
            frag["steering"][path] = {f"bullet-{hashlib.sha1(normalise(b).encode()).hexdigest()[:8]}": [b] for b in bl}
    hook_files: dict[str, dict] = {}
    for it in items:
        kind, path, rule = it.get("kind"), it.get("path", ""), it.get("rule", "")
        if kind == "hook":
            if path not in hook_files:
                hook_files[path] = json.loads((bundle / path).read_text(encoding="utf-8"))
            for h in hook_files[path].get("hooks", []):
                if h.get("name") == rule:
                    action = h.get("action", {})
                    guard = guard_in(action.get("command", ""))
                    frag["hooks"].setdefault(path, {})[rule] = {
                        "trigger": h.get("trigger", ""),
                        "matcher": h.get("matcher", ""),
                        "guard": guard,
                    }
                    if guard and (bundle / guard).is_file():
                        frag["guards"][guard] = _sha256(bundle / guard)
        elif kind == "mcp":
            # rule looks like "<server>.autoApprove": keep the property, drop the server
            prop = rule.rsplit(".", 1)[-1]
            if prop in ("autoApprove", "disabledTools") and prop not in frag["mcp"]:
                frag["mcp"].append(prop)
        elif kind == "sandbox":
            sb = json.loads((bundle / path).read_text(encoding="utf-8"))
            frag["sandbox"]["enabled"] = sb.get("enabled", False) is True
            if rule in ("networkAccess", "mcpSandboxing"):
                frag["sandbox"][rule] = sb.get(rule)
    frag["mcp"].sort()
    return frag


def update(reference: Mapping[str, Any] | None, fragments: Mapping[str, dict]) -> dict[str, Any]:
    """Replace the fragments of rooms whose demo succeeded; keep the others."""
    rooms = dict((reference or {}).get("rooms", {}))
    rooms.update(fragments)
    return {"schema": SCHEMA, "rooms": {k: rooms[k] for k in sorted(rooms)}}


@dataclass(frozen=True)
class Item:
    """One comparable expectation, merged across rooms."""

    file: str
    key: str
    kind: str  # steering | hook | guard | mcp | sandbox
    expect: Any
    rooms: tuple[str, ...]


def merged_items(reference: Mapping[str, Any] | None) -> list[Item]:
    """The sorted union of every fragment's expectations (keeps P3)."""
    acc: dict[tuple[str, str], dict] = {}

    def add(file: str, key: str, kind: str, room: str, expect_part: Any) -> None:
        slot = acc.setdefault((file, key), {"kind": kind, "rooms": set(), "parts": []})
        slot["rooms"].add(room)
        if expect_part not in slot["parts"]:
            slot["parts"].append(expect_part)

    for room, frag in (reference or {}).get("rooms", {}).items():
        for path, rules in frag.get("steering", {}).items():
            inc = frag.get("inclusion", {}).get(path, "always")
            for rule, texts in rules.items():
                for t in texts:
                    add(path, f"{path}#{rule}", "steering", room, {"text": t, "inclusion": inc})
        for path, hooks in frag.get("hooks", {}).items():
            for name, spec in hooks.items():
                add(path, f"{path}#{name}", "hook", room, spec)
        for gpath, digest in frag.get("guards", {}).items():
            add(gpath, gpath, "guard", room, digest)
        for prop in frag.get("mcp", []):
            add(".kiro/settings/mcp.json", f"mcp.json#{prop}", "mcp", room, prop)
        sb = frag.get("sandbox", {})
        if sb:
            add(".kiro/settings/sandbox.json", ".kiro/settings/sandbox.json#enabled", "sandbox", room, ["enabled", True])
            for k in ("networkAccess", "mcpSandboxing"):
                if k in sb:
                    add(".kiro/settings/sandbox.json", f".kiro/settings/sandbox.json#{k}", "sandbox", room, [k, sb[k]])
    out = []
    for (file, key), slot in acc.items():
        parts = sorted(slot["parts"], key=lambda p: json.dumps(p, sort_keys=True))
        out.append(Item(file, key, slot["kind"], tuple(json.dumps(p, sort_keys=True) for p in parts), tuple(sorted(slot["rooms"]))))
    return sorted(out, key=lambda i: (i.file, i.key))


def reference_rooms(reference: Mapping[str, Any] | None) -> dict[str, str]:
    return {room: frag.get("from_run", "") for room, frag in (reference or {}).get("rooms", {}).items()}


def all_fragments(bundles: Iterable[tuple[str, Path]], bundles_root: Path, from_run: str) -> dict[str, dict]:
    return {room: fragment_from_bundle(b, bundles_root, from_run=from_run) for room, b in bundles}
