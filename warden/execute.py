"""Run one command: no shell, own process group, hard timeout, masked output."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass

from warden.commands import Cmd
from warden.mask import mask

TAIL = 4000


@dataclass(frozen=True)
class Outcome:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    duration: float
    error: str | None = None  # set when the process could not start


def tail(text: str, n: int = TAIL) -> str:
    return text if len(text) <= n else "…" + text[-n:]


def run_cmd(cmd: Cmd) -> Outcome:
    start = time.monotonic()
    cmd.cwd.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        proc = subprocess.Popen(
            list(cmd.argv),
            cwd=cmd.cwd,
            env=cmd.env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,  # so a timeout can kill uv and its children
        )
    except OSError as exc:
        return Outcome(None, "", "", False, time.monotonic() - start, f"could not start: {type(exc).__name__}")
    try:
        out, err = proc.communicate(timeout=cmd.timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, err = proc.communicate()
        timed_out = True
    return Outcome(proc.returncode, mask(out or ""), mask(err or ""), timed_out, time.monotonic() - start)
