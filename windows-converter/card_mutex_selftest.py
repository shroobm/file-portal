#!/usr/bin/env python3
"""Tripwire for the card mutex (SYM-033/SYM-042; docs/37 §3.2, signed 2026-08-17).

A guard born today gets its tripwire today (docs/32 §6). The property under guard: at most
ONE converter process owns the card, for every entry path, enforced by the OS — and a dead
holder must never deadlock the next converter. Each case violates or stresses that property:

  0  positive control — a free mutex is acquired immediately (else every later "blocked"
     observation is meaningless)
  1  a second process REALLY blocks while the first holds, prints the loud CARD BUSY line,
     and proceeds the moment the holder releases
  2  a holder that DIES without releasing abandons the mutex; the next acquire inherits it
     fast instead of hanging forever
  3  after everything, a fresh acquire is immediate again (no leaked ownership)

Isolated: unique per-run mutex name via FP_CARD_MUTEX, scratch pipeline via FP_PIPELINE
(a test event in the live stream is SYM-010's class), 100 ms poll via FP_CARD_MUTEX_POLL_MS.

    python card_mutex_selftest.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

HERE = Path(__file__).parent
# INHERIT the name when a parent set one — a child re-running this module top must contend
# on the PARENT'S mutex, not mint its own (the first version did, and its "contention" case
# silently tested two different mutexes — SYM-001's shape, caught by this suite's own red).
MUTEX_NAME = os.environ.get("FP_CARD_MUTEX") or f"Local\\fp-card-selftest-{uuid.uuid4().hex[:12]}"
ENV = {**os.environ,
       "FP_CARD_MUTEX": MUTEX_NAME,
       "FP_CARD_MUTEX_POLL_MS": "100",
       "FP_PIPELINE": os.environ.get("FP_PIPELINE") or tempfile.mkdtemp(prefix="fp-mutex-test-")}

os.environ.update(ENV)
sys.path.insert(0, str(HERE))
import convert_and_ship as cs  # noqa: E402


def child(role: str, hold_s: float = 0.0) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--role", role, str(hold_s)],
        env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace")


if "--role" in sys.argv:
    role, hold_s = sys.argv[sys.argv.index("--role") + 1], float(sys.argv[-1])
    # TRYING lands BEFORE the acquire so the parent can hold until the contention is real —
    # the first version released on a timer, the child was still importing pymupdf, and the
    # "blocked" waiter never contended at all (a proxy measuring startup, not the guard).
    print("TRYING", flush=True)
    handle = cs.acquire_card_mutex()
    print("ACQUIRED", flush=True)
    if role == "holder-release":
        time.sleep(hold_s)
        cs.release_card_mutex(handle)
    elif role == "holder-abandon":
        os._exit(0)  # die owning it — the abandonment case
    sys.exit(0)

passed = failed = 0


def check(name: str, ok: bool) -> None:
    global passed, failed
    print(("  ok  " if ok else "  FAIL"), name)
    passed, failed = passed + (1 if ok else 0), failed + (0 if ok else 1)


# 0 — positive control: free mutex, immediate ownership.
t0 = time.perf_counter()
handle = cs.acquire_card_mutex()
check("free mutex acquired immediately", handle is not None
      and time.perf_counter() - t0 < 0.5)

# 1 — a waiter REALLY blocks while we hold, then proceeds on release. Synchronized on the
# child's TRYING line, so the mutex is provably held at the moment the child contends;
# the CARD BUSY print is then the guard's own evidence that WaitForSingleObject timed out
# against a live holder (not a startup artifact).
waiter = child("waiter")
assert waiter.stdout.readline().strip() == "TRYING"
time.sleep(0.5)                         # the child is now inside the blocked wait
cs.release_card_mutex(handle)
out, _ = waiter.communicate(timeout=30)
check("waiter completed after release", waiter.returncode == 0)
check("waiter printed the loud CARD BUSY line (real contention)", "CARD BUSY" in out)
check("waiter then acquired", "ACQUIRED" in out)

# 2 — a dead holder abandons; the next acquire inherits fast instead of hanging.
holder = child("holder-abandon", 0)
out, _ = holder.communicate(timeout=30)
check("abandoning holder did acquire first", "ACQUIRED" in out)
t0 = time.perf_counter()
handle = cs.acquire_card_mutex()
check("abandoned mutex inherited, no deadlock", handle is not None
      and time.perf_counter() - t0 < 2.0)
cs.release_card_mutex(handle)

# 3 — nothing leaked: a fresh acquire is immediate again.
t0 = time.perf_counter()
handle = cs.acquire_card_mutex()
check("fresh acquire immediate after all releases", handle is not None
      and time.perf_counter() - t0 < 0.5)
cs.release_card_mutex(handle)

print("-" * 46)
print(f"{'ALL TRIPWIRES FIRED' if not failed else 'RED'} — {passed}/{passed + failed}")
sys.exit(1 if failed else 0)
