"""The control room's event stream (docs/13 keystone): every pipeline stage appends one
JSON line to <gpu_pipeline_dir>\\events.jsonl; the widget tails it. Append-only, one
writer at a time per process, newline-delimited — reconstructible truth on disk.
"""

import json
import os
from datetime import datetime, timezone

import fp_paths

# FP_PIPELINE override (via the fp_paths resolver, S108): the deferral-gate tripwire runs the
# real watcher against an isolated root, and its telemetry must land THERE - a test event in the
# live stream would render on the widget as a phantom arrival (SYM-010's class).
EVENTS_FILE = fp_paths.root("events")


def emit(stage: str, event: str, **fields) -> None:
    """Best-effort append; the pipeline must never fail because telemetry did."""
    try:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "pid": os.getpid(),
            "stage": stage,
            "event": event,
            **fields,
        }
        EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        # A crash mid-append leaves a torn final line with no newline; appending straight onto
        # it would glue THIS record into the garbage and lose both (SYM-037 — healed first in
        # exporter.append_receipt, ported here S93). Heal the boundary: lead with a newline
        # when the file's last byte isn't one. The torn line stays torn — readers already skip
        # unparseable lines — but this record survives. One seek(-1) read; emit() stays hot.
        lead = ""
        try:
            with open(EVENTS_FILE, "rb") as check:
                check.seek(-1, 2)
                if check.read(1) != b"\n":
                    lead = "\n"
        except OSError:
            pass  # missing or empty file needs no lead
        with open(EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(lead + json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass
