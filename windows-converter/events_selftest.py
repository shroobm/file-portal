#!/usr/bin/env python3
"""WHAT THIS FILE DOES: tripwire for events.emit(), which appends one JSON line to the pipeline's events file and heals
a torn last line (one missing its newline). It points FP_PIPELINE at a temp folder, imports events, then writes the
events file in five states (healthy, torn record, torn garbage, missing, empty), calls emit(), and checks the lines
that result. Prints ok/FAIL lines; exit 0 when all fired, else 1. It writes only inside the temp folder, which it does
not delete.

Tripwire for emit()'s torn-line healing (SYM-037, ported from exporter.append_receipt).

A guard born today gets its tripwire today (docs/32 §6): each case VIOLATES the property the
guard stands for and requires the guard to answer. Case 1 is the positive control — a healthy
file must NOT grow a blank line, or the healer itself becomes the defect. No GPU, no network:

    python events_selftest.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Point the module at scratch BEFORE importing it — EVENTS_FILE is a module-level path, and a
# test event in the live stream would render on the widget as a phantom arrival (SYM-010).
SCRATCH = Path(tempfile.mkdtemp(prefix="fp-events-test-"))
os.environ["FP_PIPELINE"] = str(SCRATCH)
sys.path.insert(0, str(Path(__file__).parent))
import events  # noqa: E402

# -- test harness: counters, the check() recorder and two reading helpers --
passed = failed = 0


def check(name: str, ok: bool) -> None:
    """Print an ok/FAIL line for case name and update the passed / failed counters."""
    global passed, failed
    print(("  ok  " if ok else "  FAIL"), name)
    passed, failed = passed + (1 if ok else 0), failed + (0 if ok else 1)


def lines() -> list[str]:
    """Return the scratch events file's lines (read as UTF-8)."""
    return events.EVENTS_FILE.read_text(encoding="utf-8").splitlines()


def parseable(raw: list[str]) -> list[dict]:
    """Return the JSON objects for those lines in raw that parse as JSON, skipping the ones that do not."""
    out = []
    for line in raw:
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


# -- the five cases, run at import time in order; each rewrites the events file, calls emit(), checks the lines --
# 1 — positive control: append to a well-terminated file adds ONE line and no blank.
events.EVENTS_FILE.write_text('{"seed": 1}\n', encoding="utf-8")
events.emit("test", "control")
raw = lines()
check("healthy file: 2 lines, both parse, no blank",
      len(raw) == 2 and len(parseable(raw)) == 2 and all(raw))

# 2 — the torn line: a record whose newline a crash ate. Unhealed, the next append glues
# both into one garbage line; healed, both survive as parseable lines.
events.EVENTS_FILE.write_text('{"torn": true}', encoding="utf-8")
events.emit("test", "after_torn")
raw = lines()
check("torn file: both lines parse", len(raw) == 2 and len(parseable(raw)) == 2)
check("torn record survived", any(r.get("torn") for r in parseable(raw)))
check("new record survived", any(r.get("event") == "after_torn" for r in parseable(raw)))

# 3 — torn GARBAGE (half a record): the garbage stays torn, the new record still lands clean.
events.EVENTS_FILE.write_text('{"half": ', encoding="utf-8")
events.emit("test", "after_garbage")
raw = lines()
check("garbage stays torn, new record parses",
      len(raw) == 2 and [r.get("event") for r in parseable(raw)] == ["after_garbage"])

# 4 — missing file: first emit creates it, one clean line.
events.EVENTS_FILE.unlink()
events.emit("test", "first")
raw = lines()
check("missing file: 1 line, parses", len(raw) == 1 and len(parseable(raw)) == 1)

# 5 — empty file: no lead newline (a blank first line is the healer over-firing).
events.EVENTS_FILE.write_text("", encoding="utf-8")
events.emit("test", "onto_empty")
raw = lines()
check("empty file: 1 line, no blank", len(raw) == 1 and raw[0])

print("-" * 46)
print(f"{'ALL TRIPWIRES FIRED' if not failed else 'RED'} — {passed}/{passed + failed}")
sys.exit(1 if failed else 0)
