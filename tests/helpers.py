"""Render Hauntlet's output format and fake an executor, for tests."""

from __future__ import annotations

import secrets
import shutil
from pathlib import Path

from warden.commands import Cmd
from warden.execute import Outcome
from warden.parse import LEVEL_NAMES

BUNDLES = Path(__file__).resolve().parent / "fixtures" / "bundles"


def render_run(room: str, levels: list[int], *, ids: list[str], rates: tuple[int, int, int, int],
               passes: list[tuple[int, float]], report: str, excluded: int = 0) -> str:
    """Hauntlet's ``hauntlet run`` stdout, in the exact shape of hauntlet/cli.py cmd_run."""
    lines = [f"run {i}: L{lv} {LEVEL_NAMES[lv]}" for i, lv in zip(ids, levels)]
    c, cl, d, t = rates
    n = len(levels)
    clean = "n/a (not exercised)" if excluded == n else f"{cl}%"
    pk = ", ".join(f"pass^{k}={v:.2f}" for k, v in passes)
    lines.append(f"[{room}] n={n} worst=L{max(levels)} compromised={c}% clean={clean} detected={d}% task={t}% {pk}")
    if excluded:
        lines.append(f"[{room}] {excluded} of {n} runs excluded from clean/pass^k: an item never reached the agent")
    lines.append(f"report: {report}")
    return "\n".join(lines) + "\n"


def ks_for(exercised: int) -> list[int]:
    return [k for k in (1, 2, 4, 8) if k <= exercised]


class FakeHauntlet:
    """Answers Cmds like Hauntlet would, with configurable per-room levels and failures."""

    def __init__(self, paths, *, levels=None, selftest="pass", fail=None, unparsable=None):
        self.paths = paths
        self.levels = levels or {}
        self.selftest = selftest
        self.fail = fail or {}  # label -> Outcome
        self.unparsable = set(unparsable or ())
        self.calls: list[Cmd] = []
        self.counter = 0

    def _id(self) -> str:
        self.counter += 1
        return f"FAKE{secrets.token_hex(4)}{self.counter:04d}"

    def __call__(self, cmd: Cmd) -> Outcome:
        self.calls.append(cmd)
        if cmd.label in self.fail:
            return self.fail[cmd.label]
        if cmd.label in self.unparsable:
            return Outcome(0, "something unexpected\n", "", False, 0.1)
        if cmd.kind == "selftest":
            if self.selftest == "pass":
                return Outcome(0, "selftest passed: 6 room(s), naive >= L3 and hardened L0+Detected over n=3\n", "", False, 0.1)
            return Outcome(1, "", "selftest FAILED\n  poltergeist: hardened scored L2, expected L0\n", False, 0.1)
        if cmd.kind == "run":
            k = int(cmd.argv[cmd.argv.index("--repeat") + 1])
            lv = self.levels.get((cmd.room, cmd.agent), 4 if cmd.agent == "naive" else 0)
            out = Path(cmd.argv[cmd.argv.index("--out") + 1])
            out.mkdir(parents=True, exist_ok=True)
            ids = [self._id() for _ in range(k)]
            report = out / f"autopsy-{cmd.room}-{cmd.agent}-{ids[0]}.html"
            report.write_text("<html><body>HAUNTLET-DUMMY-… report</body></html>")
            clean = lv == 0
            text = render_run(cmd.room, [lv] * k, ids=ids,
                              rates=(0 if clean else 100, 100 if clean else 0, 100 if clean else 0, 100),
                              passes=[(kk, 1.0 if clean else 0.0) for kk in ks_for(k)], report=str(report))
            return Outcome(0, text, "", False, 0.1)
        if cmd.kind == "demo":
            bundle = self.paths.bundles_root / self._id() / self._id()
            shutil.copytree(BUNDLES / cmd.room, bundle)
            rep = Path(cmd.argv[cmd.argv.index("--out") + 1])
            rep.mkdir(parents=True, exist_ok=True)
            did = self._id()
            (rep / f"exorcist-delta-{did}.html").write_text("<html>delta</html>")
            text = (f"bundle: {bundle}\ndelta:  {bundle}/deltas/{did}.txt\n"
                    f"report: {rep}/exorcist-delta-{did}.html\n"
                    f"{cmd.room}: before worst=L4 fp=none -> after worst=L0 detected=True task=True fp=none\n")
            return Outcome(0, text, "", False, 0.1)
        raise AssertionError(cmd)


class FakeCtx:
    def __init__(self, fail=False):
        self.sent: list[str] = []
        self.fail = fail

    def notify(self, text: str) -> dict:
        if self.fail:
            raise RuntimeError("delivery failed")
        self.sent.append(text)
        return {"ok": True}
