"""Hermetic Conveyor State tripwires.  No Marker, GPU, widget, or live pipeline is touched."""

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

QUARANTINE = Path(tempfile.mkdtemp(prefix="fp-intake-selftest-"))
os.environ["FP_PIPELINE"] = str(QUARANTINE)
sys.path.insert(0, str(Path(__file__).parent))

import watch_and_convert as w  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, label: str) -> None:
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


drop = QUARANTINE / "drop"
drop.mkdir(parents=True)
pdf = drop / "book.pdf"
pdf.write_bytes(b"one")

print("T1 non-blocking quiet tracker")
writer_open = True
tracker = w.IntakeTracker(quiet_s=1.0, readiness_probe=lambda _: not writer_open)
check(tracker.reconcile([pdf], now=10.0)[0]["phase"] == "receiving",
      "first observation is receiving")
check(tracker.reconcile([pdf], now=10.5)[0]["phase"] == "settling",
      "unchanged below one second is settling")
check(tracker.reconcile([pdf], now=11.1)[0]["phase"] == "receiving",
      "quiet longer than one second does not pass while writer owns file")
writer_open = False
check(tracker.reconcile([pdf], now=11.2)[0]["phase"] == "ready",
      "closed writer plus quiet signature becomes ready")
pdf.write_bytes(b"two-two")
check(tracker.reconcile([pdf], now=11.3)[0]["phase"] == "receiving",
      "size or mtime change revokes readiness")

print("T2 watcher receipt is atomic and excludes active")
rows = tracker.reconcile([pdf], now=12.5)
w._atomic_write_state(rows, "book.pdf", "selftest")
receipt = json.loads(w.INTAKE_STATE_FILE.read_text(encoding="utf-8"))
check(receipt["v"] == 1 and receipt["writer_pid"] == os.getpid(),
      "receipt carries schema and real writer pid")
check(receipt["active"] == "book.pdf" and receipt["waiting"] == 0,
      "one active PDF renders active=1 waiting=0")
check(receipt["items"][0]["phase"] == "running", "active row phase is running")
check(not list(QUARANTINE.glob(".intake-state.json.tmp.*")),
      "dot-temporary file has no post-publish residue")

print("T2b restart preserves detected age but re-proves readiness")
old = drop / "old.pdf"
old.write_bytes(b"old")
old_stat = old.stat()
first_seen = (datetime.now(timezone.utc) - timedelta(seconds=125)).isoformat().replace("+00:00", "Z")
prior = QUARANTINE / "prior-intake.json"
prior.write_text(json.dumps({
    "v": 1,
    "items": [{"name": "old.pdf", "bytes": old_stat.st_size,
               "mtime_ns": old_stat.st_mtime_ns, "first_seen_at": first_seen}],
}), encoding="utf-8")
restarted = w.IntakeTracker(quiet_s=1.0, readiness_probe=lambda _: False)
check(restarted.restore(prior) == 1, "matching prior bytes+mtime restore one detected clock")
restored_row = restarted.reconcile([old])[0]
check(restored_row["wait_s"] >= 120, "restart does not reset operator wait age to zero")
check(restored_row["phase"] != "ready", "restart never inherits readiness without a new proof")

print("T3 Windows open-writer negative control")
if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    held = drop / "held.pdf"
    k32 = ctypes.windll.kernel32
    k32.CreateFileW.restype = wintypes.HANDLE
    handle = k32.CreateFileW(str(held), 0x40000000, 0x1 | 0x2 | 0x4, None, 2, 0x80, None)
    invalid = wintypes.HANDLE(-1).value
    check(handle != invalid, "negative-control writer handle opened")
    if handle != invalid:
        check(not w._open_without_write_sharing(held),
              "open writer is rejected even after a hypothetical quiet pause")
        held_tracker = w.IntakeTracker(quiet_s=1.0)
        held_tracker.reconcile([held], now=20.0)
        time.sleep(1.05)
        check(held_tracker.reconcile([held], now=21.1)[0]["phase"] == "receiving",
              "grow-pause>1s-resume boundary cannot dispatch during pause")
        k32.CloseHandle(handle)
        check(w._open_without_write_sharing(held), "same file becomes readable after writer closes")
else:
    print("  UNREAD  Windows share-mode probe (non-Windows host)")

print("T4 notification remains a hint")
src = Path(w.__file__).read_text(encoding="utf-8")
check("ReadDirectoryChangesW" in src and "wake.wait(delay)" in src,
      "notification wake and timed reconciliation are both wired")
check(tracker.next_quiet_delay(now=30.0) == w.POLL_S,
      "settled tracker returns to periodic reconciliation cadence")
vocab = (Path(__file__).parent.parent / "windows-widget" / "src" / "event-vocab.js").read_text(encoding="utf-8")
check('"intake/stale-lock-reaped"' in vocab and '"intake/stale-hold-reaped"' in vocab,
      "shared operator vocabulary speaks both stale-residue recovery events")

print("T5 durable ordering")
for name in ("z.pdf", "a.pdf"):
    (drop / name).write_bytes(name.encode())
order_tracker = w.IntakeTracker(quiet_s=0.0, readiness_probe=lambda _: True)
names = [row["name"] for row in order_tracker.reconcile([drop / "z.pdf", drop / "a.pdf"], now=40.0)]
check(names == ["a.pdf", "z.pdf"], "dispatch candidates stay filename sorted")
check(w._next_dispatch([
    {"name": "a.pdf", "phase": "receiving"},
    {"name": "z.pdf", "phase": "ready"},
]) is None, "later ready file cannot bypass an earlier receiving file")
check(w._next_dispatch([
    {"name": "a.pdf", "phase": "ready"},
    {"name": "z.pdf", "phase": "ready"},
]) == "a.pdf", "ready filename head dispatches first")

print("SELFTEST " + ("PASS" if not FAILURES else f"FAIL ({len(FAILURES)})"))
raise SystemExit(0 if not FAILURES else 1)
