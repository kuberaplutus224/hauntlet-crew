"""Read-only snapshot of the watched workspace's .kiro/ (Requirement 4.2, 4.6, P7).

This module opens files for reading only. It never writes, creates, renames,
deletes or changes anything, and the content test enforces that.
"""

from __future__ import annotations

import fnmatch
import os
import stat
from dataclasses import dataclass
from pathlib import Path

MAX_BYTES = 1 << 20  # 1 MiB
#: (subdirectory of .kiro, file-name pattern)
ALLOWED: tuple[tuple[str, str], ...] = (
    ("steering", "*.md"),
    ("hooks", "*.json"),
    ("hooks/guards", "*.py"),
    ("settings", "mcp.json"),
    ("settings", "sandbox.json"),
)


class WorkspaceMissing(FileNotFoundError):
    pass


@dataclass(frozen=True)
class WorkspaceSnapshot:
    root: str
    files: dict[str, bytes]  # ".kiro/steering/a.md" -> content
    warnings: tuple[str, ...]

    def text(self, rel: str) -> str | None:
        data = self.files.get(rel)
        return None if data is None else data.decode("utf-8", errors="replace")


def _read(path: str) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise OSError("not a regular file")
        chunks, size = [], 0
        while size <= MAX_BYTES:
            b = os.read(fd, 65536)
            if not b:
                break
            chunks.append(b)
            size += len(b)
        if size > MAX_BYTES:
            raise OSError("larger than 1 MiB")
        return b"".join(chunks)
    finally:
        os.close(fd)


def snapshot(workspace: Path | str) -> WorkspaceSnapshot:
    ws = os.path.abspath(str(workspace))
    if not os.path.isdir(ws):
        raise WorkspaceMissing(ws)
    kiro = os.path.join(ws, ".kiro")
    files: dict[str, bytes] = {}
    warnings: list[str] = []
    try:
        kst = os.lstat(kiro)
    except FileNotFoundError:
        return WorkspaceSnapshot(ws, files, ())
    if stat.S_ISLNK(kst.st_mode):
        return WorkspaceSnapshot(ws, files, (".kiro is a symlink; not read",))
    if not stat.S_ISDIR(kst.st_mode):
        return WorkspaceSnapshot(ws, files, (".kiro is not a directory; not read",))
    kiro_real = os.path.realpath(kiro)
    for sub, pattern in ALLOWED:
        d = os.path.join(kiro, sub)
        rel_d = f".kiro/{sub}"
        try:
            dst = os.lstat(d)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(dst.st_mode):
            warnings.append(f"{rel_d} is a symlink; not read")
            continue
        if not stat.S_ISDIR(dst.st_mode):
            continue
        with os.scandir(d) as it:
            names = sorted(e.name for e in it)
        for name in names:
            if not fnmatch.fnmatchcase(name, pattern):
                continue
            p = os.path.join(d, name)
            rel = f"{rel_d}/{name}"
            st = os.lstat(p)
            if stat.S_ISLNK(st.st_mode):
                warnings.append(f"{rel} is a symlink; not read")
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            if st.st_size > MAX_BYTES:
                warnings.append(f"{rel} is larger than 1 MiB; not read")
                continue
            real = os.path.realpath(p)
            if os.path.commonpath([real, kiro_real]) != kiro_real:
                warnings.append(f"{rel} resolves outside .kiro; not read")
                continue
            try:
                files[rel] = _read(p)
            except OSError as exc:
                warnings.append(f"{rel} could not be read ({exc.strerror or exc})")
    return WorkspaceSnapshot(ws, files, tuple(sorted(warnings)))
