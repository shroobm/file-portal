"""WHAT THIS FILE DOES: keeps logs/status.json, the list of what the allocator did with each file.
Entry point: StatusWriter.record() adds one event (allocated, skipped or rejected) and rewrites
the file. It reads and writes that one JSON file; main.py calls it and the Windows widget reads it.

Machine-readable status feed for the v2 feedback loop.

The allocator appends one record per handled file to ``logs/status.json``. The Windows widget
polls this file over the already-authenticated ``tailscale ssh ... cat`` channel, so the
feedback loop needs no new listening port -- see docs/01-architecture.md. The file is rewritten
atomically (temp file + ``os.replace``) so a concurrent reader never sees partial JSON.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

# -- shared logger and constants --
logger = logging.getLogger("file-portal-allocator")

MAX_EVENTS = 200

# S108 writer identity: two services append to the SAME status.json (this allocator and the
# converter), so every record names its writer. The widget renders records without the field
# (pre-S108 history) as "unknown" -- old files are never rewritten to claim an identity.
SOURCE_COMPONENT = "allocator"


# -- the status file writer --
class StatusWriter:
    """Maintains a bounded, newest-last list of per-file outcome records.

    Records use ``action`` values ``"allocated"``, ``"skipped"``, or ``"rejected"``, and each
    carries ``source_component`` naming its writer (here always ``"allocator"``). A status
    write must never break allocation itself, so failures are logged and swallowed.
    """

    def __init__(self, path: Path, max_events: int = MAX_EVENTS):
        """Remember the status.json path and how many newest events to keep."""
        self.path = path
        self.max_events = max_events

    def record(
        self,
        action: str,
        filename: str,
        category: str,
        dest: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Append one event (action, file, category, optional dest/reason) to status.json.

        Side effect: rewrites the file via a temp file and os.replace; OS errors are logged, not raised.
        """
        # Build the event record, adding dest and reason only when given.
        event: dict[str, str] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_component": SOURCE_COMPONENT,
            "action": action,
            "file": filename,
            "category": category,
        }
        if dest is not None:
            event["dest"] = dest
        if reason is not None:
            event["reason"] = reason

        # Load old events, append, trim to the newest max_events, then swap the file in atomically.
        try:
            events = self._load_events()
            events.append(event)
            doc = {"updated": event["ts"], "events": events[-self.max_events :]}
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(json.dumps(doc, indent=1), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:
            logger.warning("could not update status file %s", self.path, exc_info=True)

    def _load_events(self) -> list[dict[str, str]]:
        """Return the events list stored in status.json, or [] if the file is missing or malformed."""
        try:
            events = json.loads(self.path.read_text(encoding="utf-8"))["events"]
            return events if isinstance(events, list) else []
        except (OSError, ValueError, KeyError):
            # Missing or corrupt status file: start a fresh event list rather than fail.
            return []
