"""Dummy-secret masking (Requirement 10.2, Property P8).

Hauntlet plants non-functional dummy credentials of the form
``HAUNTLET-DUMMY-<run>-<trap>-<nonce>``. Warden never stores, shows or sends one in
full: every one becomes ``HAUNTLET-DUMMY-…``.
"""

from __future__ import annotations

import re
from typing import Any

PREFIX = "HAUNTLET-DUMMY-"
MASKED = PREFIX + "…"

# A dummy value runs until whitespace, a quote, an angle bracket or the ellipsis.
# The lookahead leaves an already-masked value alone, so mask() is idempotent.
_DUMMY = re.compile(re.escape(PREFIX) + r"(?!…)[^\s\"'<>…]+")
_UNMASKED = re.compile(re.escape(PREFIX) + r"[A-Za-z0-9]")


def mask(text: str) -> str:
    """Return ``text`` with every dummy value replaced by ``HAUNTLET-DUMMY-…``."""
    return _DUMMY.sub(MASKED, text)


def has_unmasked(text: str) -> bool:
    """True if ``text`` still holds a dummy value that is not masked."""
    return _UNMASKED.search(text) is not None


def mask_obj(obj: Any) -> Any:
    """Mask every string (keys included) inside a JSON-shaped value."""
    if isinstance(obj, str):
        return mask(obj)
    if isinstance(obj, dict):
        return {mask_obj(k): mask_obj(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [mask_obj(v) for v in obj]
    return obj
