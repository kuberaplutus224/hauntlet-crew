"""Repository content checks for the safety rules (Requirement 12.5)."""

import re
from pathlib import Path

import pytest

from conftest import FIXTURES, ROOT
from warden import CLIENT_NOTE
from warden.commands import GIT_SOURCE_URL

SCANNED = ["warden", "backend", "agents", "skills", "ui/src", "ui/dist"]
TEXT_EXT = {".py", ".json", ".md", ".ts", ".tsx", ".js", ".mjs", ".css", ".html"}
URL = re.compile(r"[a-z+]*https?://([^/\s\"'`<>)\]]+)", re.I)
LOOPBACK = {"127.0.0.1", "localhost", "[::1]"}
UNMASKED = re.compile(r"HAUNTLET-DUMMY-[A-Za-z0-9]")
#: Statements about client behaviour other than the approved sentence (safety rule 4).
CLIENT_CLAIMS = re.compile(r"\b(Kiro (will|blocks|prevents|stops|guarantees)|client will|guarantee[sd]?)\b", re.I)
#: Modules that may name mcp.json: the readers of the watched workspace and the reference.
MCP_READERS = {"warden/readonly.py", "warden/drift.py", "warden/reference.py"}
WRITE_CALLS = re.compile(
    r"open\([^)]*['\"][wax+]|\.write_text\(|\.write_bytes\(|os\.replace|os\.rename|\.rename\(|unlink|rmtree|"
    r"mkdir|chmod|utime|O_WRONLY|O_RDWR|O_CREAT|O_TRUNC|O_APPEND|shutil\.|tempfile|atomic_write"
)


def files():
    for d in SCANNED:
        base = ROOT / d
        if base.is_dir():
            for p in sorted(base.rglob("*")):
                if p.is_file() and p.suffix in TEXT_EXT and "__pycache__" not in p.parts:
                    yield p


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def test_no_external_hosts_except_the_one_git_constant():
    bad = []
    for p in files():
        for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            for m in URL.finditer(line):
                host = m.group(1).split(":")[0] if not m.group(1).startswith("[") else m.group(1)
                if host in LOOPBACK:
                    continue
                if rel(p) == "warden/commands.py" and line.startswith("GIT_SOURCE_URL = ") and host == "github.com":
                    continue
                bad.append(f"{rel(p)}:{n}: {host}")
    assert bad == []
    assert GIT_SOURCE_URL == "git+https://github.com/kuberaplutus224/hauntlet"


def test_no_unmasked_dummy_secrets_in_code_or_fixtures():
    scanned = list(files()) + [p for p in FIXTURES.rglob("*") if p.is_file()]
    bad = [rel(p) for p in scanned if UNMASKED.search(p.read_text(errors="replace"))]
    assert bad == []


@pytest.mark.parametrize("module", ["warden/readonly.py", "warden/drift.py"])
def test_readonly_modules_have_no_write_calls(module):
    code = "\n".join(
        line for line in (ROOT / module).read_text().splitlines() if not line.lstrip().startswith("#")
    )
    code = re.sub(r'"""[\s\S]*?"""', "", code)
    assert WRITE_CALLS.findall(code) == []


def test_no_mcp_configuration_writes():
    for p in files():
        text = p.read_text(errors="replace")
        r = rel(p)
        if "mcp.json" in text:
            assert r in MCP_READERS, f"{r} names mcp.json"
        for needle in ("register_app_mcp", "registerAppMcp", "register_mcp_server", "/api/mcp", "mcpServers\":"):
            assert needle not in text, f"{r} contains {needle}"
        if r.endswith(".json") and r.startswith("agents/"):
            assert "mcpServers" not in text


def test_client_behaviour_statements():
    for p in files():
        text = p.read_text(errors="replace")
        assert CLIENT_CLAIMS.search(text.replace(CLIENT_NOTE, "")) is None, rel(p)
    assert CLIENT_NOTE == "Some client behaviours are out of reach of config."
    assert CLIENT_NOTE in (ROOT / "warden/__init__.py").read_text()


@pytest.mark.parametrize("where, task", [("ui/src", "task 7.1"), ("skills/warden/SKILL.md", "task 8.2")])
def test_approved_sentence_appears_in_ui_and_skill(where, task):
    p = ROOT / where
    if not p.exists():
        pytest.skip(f"{where} is created in {task}")
    texts = [f.read_text() for f in (p.rglob("*") if p.is_dir() else [p]) if f.is_file()]
    assert any(CLIENT_NOTE in t for t in texts)


def test_commands_never_use_a_shell_or_directory_flag():
    for p in files():
        if p.suffix == ".py":
            text = p.read_text()
            assert "shell=True" not in text and "os.system(" not in text, rel(p)
            assert '"--directory"' not in text, rel(p)
