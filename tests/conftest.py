"""Shared test setup. Tests need neither Crew nor a Hauntlet checkout (Requirement 12.1)."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, settings

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "tests" / "fixtures"
OUTPUTS = FIXTURES / "outputs"
BUNDLES = FIXTURES / "bundles"
WORKSPACES = FIXTURES / "workspaces"

settings.register_profile(
    "warden",
    max_examples=60,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
settings.load_profile("warden")


def output(name: str) -> dict:
    return json.loads((OUTPUTS / f"{name}.json").read_text())


@pytest.fixture
def paths(tmp_path):
    from warden.paths import Paths

    p = Paths(tmp_path / "app" / "data", tmp_path / "userdata" / "hauntlet-warden" / "range")
    p.ensure()
    return p


@pytest.fixture
def checkout(tmp_path):
    """A directory that looks like a Hauntlet checkout (no code; never run)."""
    c = tmp_path / "hauntlet"
    c.mkdir()
    (c / "pyproject.toml").write_text('[project]\nname = "hauntlet"\nversion = "0.1.0"\n')
    return c


@pytest.fixture
def workspace_copy(tmp_path):
    """Copy a fixture workspace into tmp so tests never touch the committed tree."""

    def make(name: str) -> Path:
        dst = tmp_path / f"ws-{name}"
        shutil.copytree(WORKSPACES / name, dst, symlinks=True)
        return dst

    return make


@pytest.fixture
def hostile_workspace(tmp_path):
    """Built at test time: a symlink out of .kiro, a 2 MiB file, invalid JSON, a room server."""
    ws = tmp_path / "ws-hostile"
    shutil.copytree(WORKSPACES / "complete", ws)
    outside = tmp_path / "outside-secret.md"
    outside.write_text("---\ninclusion: always\n---\n- outside content\n")
    os.symlink(outside, ws / ".kiro/steering/linked.md")
    (ws / ".kiro/steering/huge.md").write_bytes(b"- x\n" * (600 * 1024))
    (ws / ".kiro/hooks/broken.json").write_text("{not json")
    mcp = json.loads((ws / ".kiro/settings/mcp.json").read_text())
    mcp["mcpServers"]["room"] = {
        "command": "uv",
        "args": ["run", "hauntlet", "mcp", "serve", "--room", "poltergeist"],
        "autoApprove": [],
        "disabledTools": ["x"],
    }
    (ws / ".kiro/settings/mcp.json").write_text(json.dumps(mcp))
    return ws


def snapshot_tree(root: Path) -> dict[str, tuple]:
    """Bytes, mode and mtime of every entry under root (symlinks not followed)."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames + filenames:
            p = os.path.join(dirpath, name)
            st = os.lstat(p)
            data = None
            if os.path.isfile(p) and not os.path.islink(p):
                with open(p, "rb") as fh:
                    data = fh.read()
            out[os.path.relpath(p, root)] = (st.st_mode, st.st_mtime_ns, data)
    return out
