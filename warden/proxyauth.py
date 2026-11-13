"""Verify that a backend request came through the Crew gateway's reverse proxy.

Crew 0.12.2 signs every proxied request with ``X-KiroCrew-Proxy`` (v1) and the
replay-proof pair ``X-KiroCrew-Proxy-Nonce`` / ``X-KiroCrew-Proxy-V2`` (spike 1.4).
The docs name the header ``X-Crew-Proxy``. Warden accepts **only** a valid v2
signature with a fresh, unseen nonce.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

V2_HEADER = "X-KiroCrew-Proxy-V2"
NONCE_HEADER = "X-KiroCrew-Proxy-Nonce"
MAX_SKEW_SECS = 60
_NONCE = re.compile(r"[0-9a-f]{32}")
_V2 = re.compile(r"(?P<ts>\d{1,12}(?:\.\d{1,9})?):(?P<mac>[0-9a-f]{64})")


def load_secret(env: Mapping[str, str], app_root: Path) -> str | None:
    secret = env.get("KIROCREW_PROXY_SECRET", "").strip()
    if secret:
        return secret
    try:
        secret = (app_root / ".app_secret").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return secret or None


def _header(headers: Any, name: str) -> str:
    v = headers.get(name)
    if v is None and isinstance(headers, Mapping):
        low = name.lower()
        for k, val in headers.items():
            if k.lower() == low:
                return str(val)
    return "" if v is None else str(v)


def v2_signature(secret: str, ts: str, nonce: str, method: str, target: str, body: bytes) -> str:
    msg = f"v2:{ts}:{nonce}:{method}:{target}:{hashlib.sha256(body).hexdigest()}"
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()


class ReplayCache:
    """Remembers nonces for twice the allowed skew. Bounded in size."""

    def __init__(self, ttl: float = 2 * MAX_SKEW_SECS, max_entries: int = 10_000):
        self.ttl, self.max_entries = ttl, max_entries
        self._seen: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()

    def check_and_add(self, nonce: str, now: float) -> bool:
        """True if the nonce is new (and is now remembered); False on a replay."""
        with self._lock:
            while self._seen and next(iter(self._seen.values())) < now - self.ttl:
                self._seen.popitem(last=False)
            if nonce in self._seen:
                return False
            self._seen[nonce] = now
            while len(self._seen) > self.max_entries:
                self._seen.popitem(last=False)
            return True


def verify(
    headers: Any,
    method: str,
    target: str,
    body: bytes,
    secret: str | None,
    cache: ReplayCache,
    now: float | None = None,
) -> bool:
    if not secret:
        return False
    now = time.time() if now is None else now
    m = _V2.fullmatch(_header(headers, V2_HEADER))
    nonce = _header(headers, NONCE_HEADER)
    if not m or not _NONCE.fullmatch(nonce):
        return False
    try:
        ts = float(m["ts"])
    except ValueError:
        return False
    if abs(now - ts) > MAX_SKEW_SECS:
        return False
    want = v2_signature(secret, m["ts"], nonce, method, target, body)
    if not hmac.compare_digest(want, m["mac"]):
        return False
    return cache.check_and_add(nonce, now)


def sign_headers(secret: str, method: str, target: str, body: bytes = b"", *, now: float | None = None,
                 nonce: str | None = None) -> dict[str, str]:
    """Headers the gateway would send. Used by tests."""
    ts = str(int(time.time() if now is None else now))
    nonce = nonce or os.urandom(16).hex()
    return {NONCE_HEADER: nonce, V2_HEADER: f"{ts}:{v2_signature(secret, ts, nonce, method, target, body)}"}
