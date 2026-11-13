"""The committed UI bundle (Requirement 7). Checked statically; building needs Node."""

import re

from conftest import ROOT
from warden import CLIENT_NOTE

DIST = (ROOT / "ui/dist/index.mjs").read_text()
SRC = "\n".join(p.read_text() for p in sorted((ROOT / "ui/src").rglob("*")) if p.is_file())
EXTERNALS = {"react", "react-dom", "react/jsx-runtime", "lucide-react", "@kirocrew/app-sdk"}


def test_bundle_imports_only_host_externals():
    specs = set(re.findall(r'(?:from\s*|import\s*\(?\s*)"([^"]+)"', DIST))
    assert specs and specs <= EXTERNALS, specs
    assert "@kirocrew/app-sdk" in specs


def test_bundle_has_a_default_export():
    assert re.search(r"export\s*\{[^}]*\bas default\b", DIST)


def test_bundle_is_built_from_the_current_source():
    # strings the source defines must be in the bundle; catches a stale dist/
    for s in ("nightly-range-check", "hauntlet-warden", "/apps/", "Ask Warden", "Turn on nightly check",
              "Check drift now", "No range results yet", "No reference yet", "No workspace watched",
              "Point Warden at your Hauntlet checkout", "--- Warden summary ---", "#33D480", "#FF7A88"):
        assert s in SRC, s
        assert s in DIST, s


def test_level_colours_match_the_scorecard():
    for c in ("#33D480", "#EFE08A", "#FFC857", "#FF9F5A", "#FF7A88", "#000000", "#19161D", "#9046FF"):
        assert c in DIST


def test_ask_warden_is_not_auto_sent_and_targets_the_agent():
    assert re.search(r"autoSend\s*:\s*(!1|false)", DIST)
    assert "hauntlet-warden" in DIST


def test_approved_sentence_and_no_absolute_urls():
    assert CLIENT_NOTE in DIST
    assert not re.search(r"https?://", DIST)
