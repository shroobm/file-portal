#!/usr/bin/env python3
"""Tripwire for the SIGNED watcher deferral gate (docs/33 §2.3; room-chat README §5).

The requirement, in the design's own words: "drop a PDF while the hold is set, prove it defers
AND prove it converts the moment the hold clears." This runs the REAL watch_and_convert.py -
not a reimplementation (SYM-001) - against an ISOLATED pipeline root (SYM-010) with a stub
converter (FP_CONVERT), so no Marker, no GPU, no live dirs, no live event stream.

    python deferral_gate_selftest.py        (any python; ~40 s)
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).parent
failed: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'BAD '} {name}" + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        failed.append(name)


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="fp-gate-"))
    drop = root / "drop"
    drop.mkdir(parents=True)
    (root / "analyst-mode.txt").write_text("off\n", encoding="utf-8")

    stub = root / "stub_convert.py"
    marker = root / "CONVERTED.txt"
    stub.write_text(
        "import sys, pathlib\n"
        f"pathlib.Path(r'{marker}').write_text(sys.argv[1], encoding='utf-8')\n",
        encoding="utf-8")

    hold = root / "chat-hold.json"
    # The hold carries OUR pid - a live process, so the reaper must respect it (a pid-less or
    # dead-pid hold is stale by the S85 reap law, and phase C proves that half).
    hold.write_text(json.dumps({"held_by": "tripwire", "pid": os.getpid(), "port": 0,
                                "model": "tripwire"}), encoding="utf-8")

    env = {**os.environ, "FP_PIPELINE": str(root), "FP_CONVERT": str(stub)}
    watcher = subprocess.Popen(
        [sys.executable, str(HERE / "watch_and_convert.py")],
        env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=open(root / "watcher-stderr.log", "wb"),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        pdf = drop / "tripwire.pdf"
        pdf.write_bytes(b"%PDF-1.4 tripwire, not a real book")

        # Phase A - HELD. Two poll cycles plus the stability wait.
        time.sleep(16)
        log = (root / "watcher.log").read_text(encoding="utf-8") if (root / "watcher.log").exists() else ""
        check("held: the stub converter was NOT invoked", not marker.exists())
        check("held: the PDF stays in drop/ (not consumed, not moved)", pdf.exists())
        check("held: DEFERRED logged, naming the hold", "DEFERRED" in log and "chat-hold" in log)
        ev = (root / "events.jsonl").read_text(encoding="utf-8") if (root / "events.jsonl").exists() else ""
        check("held: one 'deferred' event in the ISOLATED stream", ev.count('"deferred"') == 1,
              f"count={ev.count(chr(34) + 'deferred' + chr(34))}")
        check("held: the deferral did not spam (one log line across polls)",
              log.count("DEFERRED") == 1, f"count={log.count('DEFERRED')}")

        # Phase B - CLEARED. The same PDF must convert on the next poll.
        hold.unlink(missing_ok=True)   # missing_ok: a reaper bug must fail CHECKS, not crash the suite
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not marker.exists():
            time.sleep(1)
        check("cleared: the stub converter ran", marker.exists())
        if marker.exists():
            check("cleared: it ran on the deferred PDF",
                  "tripwire.pdf" in marker.read_text(encoding="utf-8"))
        time.sleep(3)
        check("cleared: the PDF was archived to done/", (drop / "done" / "tripwire.pdf").exists())
        log = (root / "watcher.log").read_text(encoding="utf-8")
        check("cleared: CONVERTING logged after the deferral", "CONVERTING tripwire.pdf" in log)

        # Phase C - STALE. A hold from a DEAD pid must be reaped, not obeyed: a Job-Object kill
        # runs no cleanup, and without the reap the conveyor would defer forever (recon hazard 3).
        marker.unlink(missing_ok=True)
        hold.write_text(json.dumps({"held_by": "ghost", "pid": 999_999_999, "port": 0,
                                    "model": "ghost"}), encoding="utf-8")
        (drop / "stale.pdf").write_bytes(b"%PDF-1.4 second tripwire")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not marker.exists():
            time.sleep(1)
        check("stale: a dead pid's hold did NOT stop the convert", marker.exists())
        log = (root / "watcher.log").read_text(encoding="utf-8")
        check("stale: the reap was logged, naming the dead pid",
              "REAPED" in log and "999999999" in log)
        check("stale: the hold file is gone", not hold.exists())
    finally:
        subprocess.run(["taskkill", "/pid", str(watcher.pid), "/t", "/f"],
                       capture_output=True)  # tree-kill, never a bare kill (SYM-006)

    print()
    if failed:
        print(f"TRIPWIRES DISARMED - {len(failed)} failed: {failed}")
        return 1
    print("ALL TRIPWIRES FIRED - the gate defers while held and converts the moment it clears")
    return 0


if __name__ == "__main__":
    sys.exit(main())
