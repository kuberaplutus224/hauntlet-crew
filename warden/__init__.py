"""Hauntlet Warden: nightly, model-free Hauntlet range checks and read-only guardrail drift.

All logic lives here and uses only the Python standard library. ``backend/nightly.py``
(the script cron) and ``backend/server.py`` (the loopback backend) are thin shells.
"""

APP_NAME = "hauntlet-warden"
CRON_NAME = "nightly-range-check"

#: The only statement Warden makes about how any client behaves (safety rule 4).
CLIENT_NOTE = "Some client behaviours are out of reach of config."
