"""Machine-readable status feed for the v2 feedback loop.

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

logger = logging.getLogger("file-portal-allocator")

MAX_EVENTS = 200


class StatusWriter:
    """Maintains a bounded, newest-last list of per-file outcome records.

    Records use ``action`` values ``"allocated"``, ``"skipped"``, or ``"rejected"``. A status
    write must never break allocation itself, so failures are logged and swallowed.
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
