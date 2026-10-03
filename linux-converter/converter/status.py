"""WHAT THIS FILE DOES: appends per-file outcome records to the shared logs/status.json that the
widget polls. StatusWriter(path).record(action, filename, category, dest, reason) adds one event
(newest last, capped at MAX_EVENTS) and rewrites the file atomically. Called by the converter
service after each file; the allocator writes the same file from its own copy of this logic.

Status feed writer -- ported from linux-receiver/allocator/status.py.

The converter appends to the SAME logs/status.json the allocator writes, because the widget
polls only that one file. Writes are atomic (temp + os.replace) so a reader never sees partial
JSON, but the read-append-replace cycle is not locked across the two services: if the allocator
and converter record in the same instant, one event can be lost. Events are advisory UI feedback
(the log files are the record), so that narrow race is accepted rather than adding a lock file.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

# -- constants --
logger = logging.getLogger("file-portal-converter")

MAX_EVENTS = 200

# S108 writer identity: two services append to the SAME status.json (this converter and the
# allocator), so every record names its writer. The widget renders records without the field
# (pre-S108 history) as "unknown" -- old files are never rewritten to claim an identity.
SOURCE_COMPONENT = "converter"


# -- the writer --
class StatusWriter:
    """Maintains a bounded, newest-last list of per-file outcome records.

    Records use ``action`` values ``"allocated"``, ``"skipped"``, or ``"rejected"``, and each
    carries ``source_component`` naming its writer (here always ``"converter"``). A status
    write must never break conversion itself, so failures are logged and swallowed.
    """

    def __init__(self, path: Path, max_events: int = MAX_EVENTS):
        """Remember the status file path and the event cap. Touches no files."""
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
        """Append one outcome event (time, writer, action, file, category, optional dest/reason).

        Rewrites the status file via temp file + os.replace. A write failure is logged, not raised.
        """
        # build the event record; optional fields only when given
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

        # read old events, append, keep the newest max_events, replace the file atomically
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
        """Return the events list stored in the status file, or [] if missing/corrupt. Read-only."""
        try:
            events = json.loads(self.path.read_text(encoding="utf-8"))["events"]
            return events if isinstance(events, list) else []
        except (OSError, ValueError, KeyError):
            # Missing or corrupt status file: start a fresh event list rather than fail.
            return []
