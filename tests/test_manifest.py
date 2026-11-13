"""app.json against the documented fields (D5–D13) and the verified 0.12.2 rules (S1–S4)."""

import ast
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from conftest import ROOT

MANIFEST = json.loads((ROOT / "app.json").read_text())
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")  # D5
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")  # D5
CREW_PY = Path("/Applications/KiroCrew.app/Contents/Resources/backend-dist/kirocrew-backend/bin/python3.12")
#: Created by later tasks (7: UI build, 8: agent and skill). Until then their checks skip.
LATER = {"agents/warden.json": "task 8.1", "skills/warden": "task 8.2", "ui/dist/index.mjs": "task 7.2"}


def need(rel: str) -> Path:
    p = ROOT / rel
    if not p.exists() and rel in LATER:
        pytest.skip(f"{rel} is created in {LATER[rel]}")
    return p


def test_required_fields_d5():
    for k in ("name", "version", "displayName", "description"):
        assert isinstance(MANIFEST.get(k), str) and MANIFEST[k].strip(), k
    assert NAME_RE.match(MANIFEST["name"]) and MANIFEST["name"] == "hauntlet-warden"
    assert SEMVER_RE.match(MANIFEST["version"])
    assert MANIFEST["displayName"] == "Hauntlet Warden"


def test_identity_fields_d6_d21():
    assert MANIFEST["author"] == "kuberaplutus224"
    assert MANIFEST["license"] == "MIT" and (ROOT / "LICENSE").read_text().startswith("MIT License")
    assert MANIFEST["minKiroCrewVersion"] == "0.12.2"
    assert MANIFEST["tags"] and all(isinstance(t, str) for t in MANIFEST["tags"])


def test_cron_entry_d7_s1_s3_s4():
    (cron,) = MANIFEST["crons"]
    assert cron["name"] == "nightly-range-check"
    assert ("every" in cron) != ("cron_expr" in cron)  # D7: exactly one schedule
    assert cron["cron_expr"] == "0 3 * * *" and cron["timezone"] == "local"
    assert cron["strict_schedule"] is True
    assert cron["enabled"] is False and isinstance(cron["enabled"], bool)  # D7: a JSON boolean
    assert ("script" in cron) and ("command" not in cron)  # S1: mutually exclusive
    assert "message" not in cron and "agent" not in cron  # no model on a scheduled run
    assert cron["silent"] is True and cron["persistent_session"] is False
    assert 0 < cron["timeout"] <= 3600 and cron["timeout_secs"] >= cron["timeout"] + 5  # S4
    file, _, func = cron["script"].partition(":")
    tree = ast.parse((ROOT / file).read_text())
    assert func in {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}


def test_permissions_are_exactly_what_warden_uses():
    assert MANIFEST["permissions"] == {
        "api": ["/api/crons", "/apps/hauntlet-warden/api"],
        "storage": True,
        "cron": True,  # S2: required when crons are declared
        "network": False,
    }


def test_nothing_forbidden_is_declared():
    assert "mcpServers" not in MANIFEST  # safety rule 1
    assert "setup" not in MANIFEST
    assert "routes" not in MANIFEST["backend"]  # spike 1.4: the proxy does not use it
    assert "mcpTools" not in MANIFEST["permissions"]


def test_backend_ui_dependencies_platform_d8_d9_d12_d13():
    b = MANIFEST["backend"]
    assert b == {"entryPoint": "backend/server.py", "type": "python", "port": "auto", "healthCheck": "/health"}
    (page,) = MANIFEST["ui"]["pages"]
    assert page["route"] and page["label"]  # D8
    assert page["route"] == "/apps/hauntlet-warden"
    assert MANIFEST["ui"]["entry"] == "dist/index.mjs"
    assert MANIFEST["dependencies"] == {"commands": ["uv"]}
    assert MANIFEST["platform"]["os"] == ["macos", "linux"]


def _paths():
    out = [(p, p) for p in MANIFEST["agents"] + MANIFEST["skills"]]
    out.append(("backend/server.py", "backend/server.py"))
    out.append(("ui/" + MANIFEST["ui"]["entry"], MANIFEST["ui"]["entry"]))
    out.append((MANIFEST["crons"][0]["script"].split(":")[0], MANIFEST["crons"][0]["script"]))
    return out


@pytest.mark.parametrize("rel, declared", _paths())
def test_paths_are_relative_contained_and_exist_d11(rel, declared):
    assert not os.path.isabs(declared) and ".." not in Path(declared).parts
    p = need(rel)
    assert p.resolve().is_relative_to(ROOT.resolve())
    assert p.exists()


@pytest.mark.skipif(not CREW_PY.exists(), reason="Crew is not installed here (optional check)")
def test_installed_crew_validates_the_manifest():
    code = (
        "import json,sys;from pathlib import Path;from kiro_crew.apps.manifest import AppManifest;"
        "m=AppManifest.from_dict(json.load(open(sys.argv[1])));print(json.dumps(m.validate()))"
    )
    out = subprocess.run([str(CREW_PY), "-s", "-c", code, str(ROOT / "app.json")],
                         capture_output=True, text=True, timeout=60, cwd="/")
    assert out.returncode == 0, out.stderr[-500:]
    assert json.loads(out.stdout.strip().splitlines()[-1]) == []
