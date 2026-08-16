"""The control room's event stream (docs/13 keystone): every pipeline stage appends one
JSON line to <gpu_pipeline_dir>\\events.jsonl; the widget tails it. Append-only, one
writer at a time per process, newline-delimited — reconstructible truth on disk.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

# FP_PIPELINE override matches watch_and_convert.py's: the deferral-gate tripwire runs the real
# watcher against an isolated root, and its telemetry must land THERE - a test event in the live
# stream would render on the widget as a phantom arrival (SYM-010's class).
EVENTS_FILE = Path(os.environ.get("FP_PIPELINE", r"C:\Users\Bndit\ml\library")) / "events.jsonl"


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
        with open(EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass
