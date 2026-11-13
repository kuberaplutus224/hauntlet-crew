"""Hauntlet's text output → typed results. Fails closed (Requirement 3.4, P1, P2).

Accepted line shapes are exactly those in design.md "Output grammar". On stdout an
unknown line is an error. On stderr, lines outside the grammar (uv's own notes) are
ignored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

LEVEL_NAMES = {0: "Clean", 1: "Reached", 2: "Echoed", 3: "Acted", 4: "Exposed"}

_ID = r"[A-Za-z0-9_-]{8,64}"
_ROOM = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_PCT = r"(\d{1,3})%"
RE_REPEAT = re.compile(rf"run (?P<id>{_ID}): L(?P<lvl>[0-4]) (?P<name>Clean|Reached|Echoed|Acted|Exposed)")
RE_SUMMARY = re.compile(
    rf"\[(?P<room>{_ROOM})\] n=(?P<n>\d+) worst=L(?P<w>[0-4]) "
    rf"compromised={_PCT} clean=(?:(?P<clean>\d{{1,3}})%|(?P<clean_na>n/a \(not exercised\))) "
    rf"detected={_PCT} task={_PCT} "
    r"(?P<pass>(?:pass\^\d+=\d\.\d\d(?:, pass\^\d+=\d\.\d\d)*)?)"
)
RE_EXCLUDED = re.compile(
    rf"\[(?P<room>{_ROOM})\] (?P<x>\d+) of (?P<n>\d+) runs excluded from clean/pass\^k: "
    r"an item never reached the agent"
)
#: Hauntlet's aggregate prints pass^k for these k, up to the exercised run count
#: (hauntlet/core/aggregate.py DEFAULT_KS; checked 2026-11-12).
PASS_KS = (1, 2, 4, 8)
RE_PASS = re.compile(r"pass\^(\d+)=(\d\.\d\d)")
RE_REPORT = re.compile(r"report: (?P<path>/\S.*\.html)")
RE_SELFTEST_PASS = re.compile(r"selftest passed: (?P<rooms>\d+) room\(s\), .+")
RE_BUNDLE = re.compile(r"bundle: (?P<p>/\S.*)")
RE_DELTA = re.compile(r"delta:  (?P<p>/\S.*)")
RE_DEMO = re.compile(
    rf"(?P<room>{_ROOM}): before worst=L(?P<b>[0-4]) fp=.+ -> after worst=L(?P<a>[0-4]) "
    r"detected=(?P<d>True|False) task=(?P<t>True|False) fp=.+"
)


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class RunResult:
    room: str
    n: int
    worst: int
    compromised: float
    clean: float | None  # None: no run exercised every trap
    detected: float
    task: float
    passes: tuple[tuple[int, float], ...]  # (k, pass^k) for k in PASS_KS, k <= exercised
    run_ids: tuple[str, ...]
    levels: tuple[int, ...]
    report: str
    excluded: int = 0

    @property
    def pass_k(self) -> float | None:
        """The headline pass^k: the one at the largest k Hauntlet printed."""
        return self.passes[-1][1] if self.passes else None

    @property
    def k(self) -> int | None:
        return self.passes[-1][0] if self.passes else None


@dataclass(frozen=True)
class SelftestResult:
    passed: bool
    rooms: int | None
    summary: str
    failures: tuple[str, ...]


@dataclass(frozen=True)
class DemoResult:
    room: str
    bundle: str
    delta: str
    report: str
    before_worst: int
    after_worst: int
    detected: bool
    task: bool


def _lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def _pct(s: str) -> float:
    v = int(s)
    if v > 100:
        raise ParseError(f"percentage out of range: {v}")
    return v / 100


def parse_run(stdout: str, stderr: str, exit_code: int | None, *, room: str, repeat: int) -> RunResult:
    if exit_code != 0:
        raise ParseError(f"exit code {exit_code}")
    lines = _lines(stdout)
    if len(lines) not in (repeat + 2, repeat + 3):
        raise ParseError(f"expected {repeat + 2} or {repeat + 3} lines, got {len(lines)}")
    ids, levels = [], []
    for line in lines[:repeat]:
        m = RE_REPEAT.fullmatch(line)
        if not m:
            raise ParseError("unexpected repeat line")
        lvl = int(m["lvl"])
        if LEVEL_NAMES[lvl] != m["name"]:
            raise ParseError("level name does not match level")
        ids.append(m["id"])
        levels.append(lvl)
    # The summary may carry a trailing space when no pass^k is printed.
    m = RE_SUMMARY.fullmatch(lines[repeat].rstrip())
    if not m:
        m = RE_SUMMARY.fullmatch(lines[repeat].rstrip() + " ")
    if not m:
        raise ParseError("unexpected summary line")
    if m["room"] != room:
        raise ParseError("summary is for another room")
    n = int(m["n"])
    if n != repeat:
        raise ParseError("summary n differs from --repeat")
    excluded = 0
    rest = lines[repeat + 1 :]
    if len(rest) == 2:
        x = RE_EXCLUDED.fullmatch(rest[0])
        if not x or x["room"] != room or int(x["n"]) != n or not 0 < int(x["x"]) <= n:
            raise ParseError("unexpected line after the summary")
        excluded = int(x["x"])
        rest = rest[1:]
    exercised = n - excluded
    passes = [(int(k), float(v)) for k, v in RE_PASS.findall(m["pass"] or "")]
    if [k for k, _ in passes] != [k for k in PASS_KS if k <= exercised]:
        raise ParseError("pass^k values do not match Hauntlet's k set")
    if (m["clean_na"] is not None) != (exercised == 0):
        raise ParseError("clean rate and exercised runs disagree")
    worst = int(m["w"])
    if worst != max(levels):
        raise ParseError("worst is not the maximum repeat level")
    rm = RE_REPORT.fullmatch(rest[0])
    if not rm:
        raise ParseError("unexpected report line")
    return RunResult(
        room=room,
        n=n,
        worst=worst,
        compromised=_pct(m.group(4)),
        clean=None if m["clean"] is None else _pct(m["clean"]),
        detected=_pct(m.group(7)),
        task=_pct(m.group(8)),
        passes=tuple(passes),
        run_ids=tuple(ids),
        levels=tuple(levels),
        report=rm["path"],
        excluded=excluded,
    )


def parse_selftest(stdout: str, stderr: str, exit_code: int | None) -> SelftestResult:
    out = _lines(stdout)
    if exit_code == 0:
        if len(out) != 1:
            raise ParseError("expected one selftest line")
        m = RE_SELFTEST_PASS.fullmatch(out[0])
        if not m:
            raise ParseError("unexpected selftest line")
        return SelftestResult(True, int(m["rooms"]), out[0], ())
    if out:
        raise ParseError("unexpected stdout on a failed selftest")
    err = stderr.splitlines()
    try:
        i = err.index("selftest FAILED")
    except ValueError:
        raise ParseError(f"exit code {exit_code} without 'selftest FAILED'") from None
    failures = []
    for line in err[i + 1 :]:
        if not line.startswith("  ") or not line.strip():
            break
        failures.append(line[2:])
    if not failures:
        raise ParseError("'selftest FAILED' without failures")
    return SelftestResult(False, None, "selftest FAILED", tuple(failures))


def parse_demo(stdout: str, stderr: str, exit_code: int | None, *, room: str) -> DemoResult:
    if exit_code != 0:
        raise ParseError(f"exit code {exit_code}")
    lines = _lines(stdout)
    if len(lines) != 4:
        raise ParseError(f"expected 4 lines, got {len(lines)}")
    b, d, r, res = (RE_BUNDLE.fullmatch(lines[0]), RE_DELTA.fullmatch(lines[1]),
                    RE_REPORT.fullmatch(lines[2]), RE_DEMO.fullmatch(lines[3]))
    if not (b and d and r and res):
        raise ParseError("unexpected demo output")
    if res["room"] != room:
        raise ParseError("demo result is for another room")
    return DemoResult(
        room=room,
        bundle=b["p"],
        delta=d["p"],
        report=r["path"],
        before_worst=int(res["b"]),
        after_worst=int(res["a"]),
        detected=res["d"] == "True",
        task=res["t"] == "True",
    )


_UNSYNCED = re.compile(r"Network connectivity is disabled|requested data wasn't found in the cache|Failed to download")


def is_unsynced(stderr: str, exit_code: int | None) -> bool:
    """uv could not resolve the checkout's environment offline (decision Q2)."""
    return exit_code not in (0, None) and _UNSYNCED.search(stderr) is not None
