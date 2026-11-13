"""The Warden agent and skill (Requirement 11, option A)."""

import json
import re

from conftest import ROOT
from warden import CLIENT_NOTE

AGENT = json.loads((ROOT / "agents/warden.json").read_text())
SKILL = (ROOT / "skills/warden/SKILL.md").read_text()


def frontmatter(text: str) -> dict:
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    assert m, "SKILL.md needs frontmatter"
    out = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip()
    return out


def test_agent_fields_d14():
    assert set(AGENT) == {"name", "model", "description", "prompt", "tools"}
    assert AGENT["name"] == "hauntlet-warden" and AGENT["model"] == "auto"
    assert AGENT["description"].strip() and AGENT["prompt"].strip()


def test_agent_has_no_tools():
    assert AGENT["tools"] == []
    assert "allowedTools" not in AGENT and "mcpServers" not in AGENT


def test_agent_prompt_follows_option_a():
    p = AGENT["prompt"]
    for needle in ("--- Warden summary ---", "Ask Warden", "Run now", "no run yet", "HAUNTLET-DUMMY-…",
                   "uses credits", "hostile", "cannot start a run"):
        assert needle.lower() in p.lower(), needle
    assert CLIENT_NOTE in p


def test_skill_frontmatter_d15():
    fm = frontmatter(SKILL)
    assert set(fm) == {"name", "description", "triggers", "always"}
    assert fm["name"] == "warden" and fm["always"] == "false" and fm["description"]
    triggers = [t.strip().strip('"') for t in fm["triggers"].strip("[]").split(",")]
    assert {"warden", "guardrails", "drift", "last night"} <= set(triggers)


def test_skill_content():
    assert CLIENT_NOTE in SKILL
    assert "only part of Warden that uses credits" in SKILL
    assert "Run now" in SKILL and "Ask Warden" in SKILL and "pass^2" in SKILL
    for lv in ("L0 | Clean", "L1 | Reached", "L2 | Echoed", "L3 | Acted", "L4 | Exposed"):
        assert lv in SKILL


def test_neither_tells_the_agent_to_open_room_content():
    for text in (SKILL, AGENT["prompt"]):
        for bad in (r"\bopen the (report|scorecard)", r"read .*range/", r"fs_read", r"cron_trigger", r"cat \S+\.html"):
            assert not re.search(bad, text, re.I), bad
