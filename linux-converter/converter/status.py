"""Status feed writer -- ported from linux-receiver/allocator/status.py.

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

logger = logging.getLogger("file-portal-converter")

MAX_EVENTS = 200


class StatusWriter:
    """Maintains a bounded, newest-last list of per-file outcome records.

    Records use ``action`` values ``"allocated"``, ``"skipped"``, or ``"rejected"``. A status
    write must never break conversion itself, so failures are logged and swallowed.
    """

    def __init__(self, path: Path, max_events: int = MAX_EVENTS):
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
        event: dict[str, str] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "action": action,
            "file": filename,
            "category": category,
        }
        if dest is not None:
            event["dest"] = dest
        if reason is not None:
            event["reason"] = reason

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
        try:
            events = json.loads(self.path.read_text(encoding="utf-8"))["events"]
            return events if isinstance(events, list) else []
        except (OSError, ValueError, KeyError):
            # Missing or corrupt status file: start a fresh event list rather than fail.
            return []
