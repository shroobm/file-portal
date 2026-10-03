"""WHAT THIS FILE DOES: selftest script for watch_and_convert.py (the drop-folder watcher: IntakeTracker readiness
phases, the atomic intake-state receipt, dispatch order, the UTF-8 log setting, and convert_one's handling of the
child's exit code). It runs its checks at import time (no main function), prints one ok/FAIL line each and a final
SELFTEST PASS/FAIL line, and exits 1 on any failure. It sets FP_PIPELINE to a temp quarantine dir, writes only there,
temporarily replaces functions on the watch_and_convert module, runs one small python subprocess, and on Windows
opens a file handle on purpose. Nobody imports it; it is run directly.

Hermetic Conveyor State tripwires.  No Marker, GPU, widget, or live pipeline is touched."""

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

# -- failure list and the check() reporter --
FAILURES: list[str] = []


def check(cond: bool, label: str) -> None:
    """Print an ok/FAIL line for one check and add the label to FAILURES when cond is false."""
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


# -- shared fixture: a drop folder with one PDF inside the quarantine dir --
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


# ---------- SYM-125: the watcher's log is UTF-8 (S141 E7 fixed it; S163 E3 the tripwire) ----------
# The defect: `logging.basicConfig(filename=…)` without `encoding` wrote the locale's cp1252 with
# backslashreplace — U+2026 landed as the raw byte 0x85, everything else as an escape, a file no
# single decoder reads. (1) the source proxy: the watcher's call carries encoding="utf-8" (the
# planted removal reds it); (2) the class itself, behaviourally, in a subprocess with the console
# code page forced to cp1252: the same call WITH encoding round-trips U+2026; WITHOUT it a UTF-8
# reader raises on 0x85 — the row's exact symptom, watched.
import re as _s125_re  # noqa: E402 — the case's own imports beside the case (the file's `import watch_and_convert` is E402 too)
import subprocess as _s125_sp  # noqa: E402

_s125_src = Path(w.__file__).read_text(encoding="utf-8")
_s125_call = _s125_re.search(r"logging\.basicConfig\((.*?)\)", _s125_src, _s125_re.S)
check(_s125_call is not None and 'encoding="utf-8"' in _s125_call.group(1),
      "SYM-125 (a) the watcher's logging.basicConfig call carries encoding=\"utf-8\" (source proxy)")
_s125_planted = _s125_call.group(1).replace('encoding="utf-8",', "") if _s125_call else ""
check('encoding="utf-8"' not in _s125_planted and _s125_call is not None,
      "SYM-125 (b) NEGATIVE CONTROL: the encoding planted out of a copy of the call reds the proxy")

# the probe script run in a child process: logs one line with or without encoding="utf-8" and reports how the file decodes
_S125_PROBE = (
    "import logging, sys, tempfile, pathlib\n"
    "p = pathlib.Path(tempfile.mkdtemp()) / 'w.log'\n"
    "kw = {'encoding': 'utf-8'} if sys.argv[1] == 'fixed' else {}\n"
    "logging.basicConfig(filename=str(p), level=logging.INFO, format='%(message)s', **kw)\n"
    "logging.getLogger().info('Best Practices \u2026 Analysts')\n"
    "logging.shutdown()\n"
    "raw = p.read_bytes()\n"
    "try:\n"
    "    raw.decode('utf-8'); print('UTF8-OK', raw.hex())\n"
    "except UnicodeDecodeError as e:\n"
    "    print('UTF8-RAISES', raw.hex(), str(e)[:40])\n"
)


def _s125_run(mode: str) -> str:
    """Run the probe in a child python with the legacy locale forced; mode is "fixed" or "bare". Returns the
    child's combined stdout and stderr, stripped. Side effect: the child writes a log in its own temp dir."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="0", PYTHONLEGACYWINDOWSFSENCODING="0")
    r = _s125_sp.run([sys.executable, "-X", "utf8=0", "-c", _S125_PROBE, mode], capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    return (r.stdout + r.stderr).strip()


_s125_fixed = _s125_run("fixed")
_s125_bare = _s125_run("bare")
check(_s125_fixed.startswith("UTF8-OK") and "e280a6" in _s125_fixed,
      "SYM-125 (c) WITH encoding=utf-8 the ellipsis lands as e2 80 a6 and a UTF-8 reader decodes the log")
if _s125_bare.startswith("UTF8-RAISES"):
    check("85" in _s125_bare.split()[1],
          "SYM-125 (d) NEGATIVE CONTROL: WITHOUT it the locale writes the raw 0x85 and a UTF-8 reader raises — the row's symptom, watched")
else:
    # a failed probe never renders as a negative observation (the muster's rule 4): the control could not fire here, said
    check(True, "SYM-125 (d) NEGATIVE CONTROL UNREAD on this interpreter — the bare call wrote %s (the locale is not cp1252 here); not a statement that the class is gone" % _s125_bare[:24])

# ---------- S218 E6 (F5, SYM-174): convert_one reads the child's exit 98 as DONE-but-not-shipped ----------
# The first convert_one cases this suite has: subprocess.Popen stubbed (no child runs), chat_hold off, the lock under the
# quarantine. Exit 98 → the source under DONE_DIR, no intake/failed, no stderr file; exit 1 (the control) → FAILED_DIR,
# intake/failed, the stderr file kept; exit 0 → DONE_DIR. And the two constants (the watcher's and the child's) pinned equal.
import watch_and_convert as _wac  # noqa: E402
import convert_and_ship as _cas  # noqa: E402
check(_wac.SHIP_FAILED_EXIT == _cas.SHIP_FAILED_EXIT == 98, "E6 (0) the watcher's SHIP_FAILED_EXIT equals convert_and_ship's (98) — one number, two files")


# -- E6: a stub child process and a runner that drives convert_one with it --
class _E6Child:
    """Stand-in for subprocess.Popen's child: exits with a chosen code and prints canned output."""

    def __init__(self, code):
        """Store the exit code as returncode and a fake pid."""
        self.returncode, self.pid = code, 4242

    def communicate(self, timeout=None):
        """Return (stdout, stderr) text matching the stored exit code; the timeout is ignored."""
        return ("ANCHORED x\nSHIP-FAILED B: ship failed: tar=1 ssh=255" if self.returncode == 98 else "DONE", "Traceback: Marker died" if self.returncode == 1 else "")


def _e6_run(code):
    """Run watch_and_convert.convert_one on a fixture PDF with the child stubbed to exit with `code`. Creates the
    fixture PDF and the done/failed dirs in the quarantine, swaps five module attributes for the call and restores
    them. Returns (result, pdf file name, list of emitted events)."""
    drop = QUARANTINE / "e6drop"
    drop.mkdir(exist_ok=True)
    pdf = drop / ("book-%s.pdf" % code)
    pdf.write_bytes(b"%PDF-1.4 fixture")
    for d in (_wac.DONE_DIR, _wac.FAILED_DIR):
        d.mkdir(parents=True, exist_ok=True)
    emits = []
    # stub out the child process, chat hold, analyst mode, event emitter and lock file for the duration of the call
    saved = (_wac.subprocess.Popen, _wac.chat_hold, _wac.analyst_mode, _wac.emit, _wac.LOCK_FILE)
    _wac.subprocess.Popen = lambda *a, **k: _E6Child(code)
    _wac.chat_hold = lambda: None
    _wac.analyst_mode = lambda: "off"
    _wac.emit = lambda kind, status, **kw: emits.append((kind, status, kw))
    _wac.LOCK_FILE = QUARANTINE / "e6.lock"
    try:
        result = _wac.convert_one(pdf)
    finally:
        _wac.subprocess.Popen, _wac.chat_hold, _wac.analyst_mode, _wac.emit, _wac.LOCK_FILE = saved
    return result, pdf.name, emits


_r98, _n98, _e98 = _e6_run(98)
check(_r98 == "done" and (_wac.DONE_DIR / _n98).exists() and not (_wac.FAILED_DIR / _n98).exists()
      and not any(k == "intake" and s == "failed" for k, s, _ in _e98) and not (_wac.FAILED_DIR / (Path(_n98).stem + ".stderr.txt")).exists(),
      f"E6 (1) exit 98 (SHIP-FAILED): the source lands under drop/done, no intake/failed, no stderr file — result={_r98!r} emits={_e98!r}")
_r1, _n1, _e1 = _e6_run(1)
check(_r1 == "failed" and (_wac.FAILED_DIR / _n1).exists() and any(k == "intake" and s == "failed" and kw.get("exit_code") == 1 for k, s, kw in _e1)
      and (_wac.FAILED_DIR / (Path(_n1).stem + ".stderr.txt")).exists(),
      f"E6 (2) CONTROL: exit 1 still lands under drop/failed with intake/failed exit_code 1 and the stderr file — result={_r1!r} emits={_e1!r}")
_r0, _n0, _e0 = _e6_run(0)
check(_r0 == "done" and (_wac.DONE_DIR / _n0).exists(), f"E6 (3) exit 0 lands under drop/done as before — result={_r0!r}")

# -- E9 (S218, SYM-190's line side): a source the watcher could not move is PARKED, never converted twice --
# The fixture is the field's shape: the test itself keeps the PDF open (Python's open() shares read/write, never
# delete, so Windows refuses the rename with WinError 32 - what the Scanner's cached pymupdf.open() did on 2026-09-27).
def _e9_run(name, hold):
    """convert_one on a fixture IN DROP_DIR with the child stubbed to exit 0; hold=True keeps the PDF open across the
    call. Returns (result, pdf path, emitted events, the handle or None)."""
    _wac.DROP_DIR.mkdir(parents=True, exist_ok=True)
    pdf = _wac.DROP_DIR / name
    pdf.write_bytes(b"%PDF-1.4 fixture e9")
    for d in (_wac.DONE_DIR, _wac.FAILED_DIR):
        d.mkdir(parents=True, exist_ok=True)
    emits = []
    saved = (_wac.subprocess.Popen, _wac.chat_hold, _wac.analyst_mode, _wac.emit, _wac.LOCK_FILE)
    _wac.subprocess.Popen = lambda *a, **k: _E6Child(0)
    _wac.chat_hold = lambda: None
    _wac.analyst_mode = lambda: "off"
    _wac.emit = lambda kind, status, **kw: emits.append((kind, status, kw))
    _wac.LOCK_FILE = QUARANTINE / "e9.lock"
    handle = open(pdf, "rb") if hold else None
    try:
        result = _wac.convert_one(pdf)
    finally:
        _wac.subprocess.Popen, _wac.chat_hold, _wac.analyst_mode, _wac.emit, _wac.LOCK_FILE = saved
    return result, pdf, emits, handle


def _e9_rows(*names):
    """Tracker-shaped rows for the given names as they sit in DROP_DIR now, all `ready`, in filename order."""
    rows = []
    for n in sorted(names):
        st = (_wac.DROP_DIR / n).stat()
        rows.append({"name": n, "bytes": st.st_size, "mtime_ns": st.st_mtime_ns, "phase": "ready"})
    return rows


_wac._parked.clear()
_r9, _p9, _e9, _h9 = _e9_run("book-e9.pdf", hold=True)
_mf9 = [kw for k, s, kw in _e9 if (k, s) == ("intake", "move_failed")]
_pk9 = _wac._parked.get("book-e9.pdf")
# (measured here: shutil.move's rename fails on the held file, then its copy-then-delete fallback COPIES the PDF under
# drop/done and fails the delete - so a copy may sit under done/ while the held source stays in drop/; the late move
# overwrites that copy. The park is keyed on the SOURCE in drop/, which is what the loop re-dispatched before E9.)
check(_r9 == "done" and _p9.exists() and len(_mf9) == 1 and _pk9 is not None
      and _pk9["size"] == _p9.stat().st_size and _pk9["mtime_ns"] == _p9.stat().st_mtime_ns and _pk9["reason"],
      f"E9 (1) a held handle: the move fails once (intake/move_failed), the source stays in drop/ and is PARKED with its identity and reason — result={_r9!r} parked={_pk9!r} emits={_e9!r}")
(_wac.DROP_DIR / "book-z.pdf").write_bytes(b"%PDF-1.4 fixture z")
_rows9 = _wac._apply_park(_e9_rows("book-e9.pdf", "book-z.pdf"))
check(_rows9[0]["name"] == "book-e9.pdf" and _rows9[0]["phase"] == "deferred" and _rows9[0].get("parked") is True
      and _rows9[0]["reason"].startswith("parked: ") and _wac._next_dispatch(_rows9) == "book-z.pdf",
      f"E9 (2) the parked row reads deferred+parked with its reason and dispatch skips it: the row behind it is the head — rows={_rows9!r} next={_wac._next_dispatch(_rows9)!r}")
_e9b = []
_saved_emit = _wac.emit
_wac.emit = lambda kind, status, **kw: _e9b.append((kind, status, kw))
try:
    _wac._retry_parked()
    _still = _p9.exists() and "book-e9.pdf" in _wac._parked and not _e9b
    _h9.close()
    _wac._retry_parked()
finally:
    _wac.emit = _saved_emit
_ml9 = [kw for k, s, kw in _e9b if (k, s) == ("intake", "moved_late")]
check(_still and not _p9.exists() and (_wac.DONE_DIR / "book-e9.pdf").exists() and len(_ml9) == 1
      and _ml9[0]["source"] == "book-e9.pdf" and _ml9[0]["dest"] == "drop/done/" and _ml9[0]["outcome"] == "done"
      and isinstance(_ml9[0]["waited_s"], int) and _ml9[0]["waited_s"] >= 0 and "book-e9.pdf" not in _wac._parked,
      f"E9 (3) while held the retry leaves it parked (no event); once released the MOVE is retried, the source lands under drop/done, intake/moved_late once with waited_s, the park cleared — still={_still} emits={_e9b!r} parked={list(_wac._parked)!r}")
_wac._parked["book-z.pdf"] = {"reason": "stale identity", "outcome": "done", "dest": _wac.DONE_DIR, "size": 1, "mtime_ns": 1, "since": 0.0, "since_wall": "x"}
_rowsz = _wac._apply_park(_e9_rows("book-z.pdf"))
check(_rowsz[0]["phase"] == "ready" and not _rowsz[0].get("parked") and "book-z.pdf" not in _wac._parked and _wac._next_dispatch(_rowsz) == "book-z.pdf",
      f"E9 (4) CONTROL: a file under a parked name with a DIFFERENT identity (re-dropped) is cleared from the park and dispatchable — rows={_rowsz!r}")
_wac._parked["book-gone.pdf"] = {"reason": "left", "outcome": "done", "dest": _wac.DONE_DIR, "size": 1, "mtime_ns": 1, "since": 0.0, "since_wall": "x"}
_wac._apply_park(_e9_rows("book-z.pdf"))
check("book-gone.pdf" not in _wac._parked, "E9 (5) CONTROL: a parked name no longer in drop/ (moved by another hand) is cleared")
_r9c, _p9c, _e9c, _ = _e9_run("book-e9c.pdf", hold=False)
check(_r9c == "done" and (_wac.DONE_DIR / "book-e9c.pdf").exists() and "book-e9c.pdf" not in _wac._parked
      and not any((k, s) == ("intake", "move_failed") for k, s, _ in _e9c),
      f"E9 (6) CONTROL: a move that succeeds first time parks nothing and emits no move_failed — result={_r9c!r} parked={list(_wac._parked)!r}")
_wac._parked.clear()
# (7) the WIRING in main() - E9's blind verifier removed `_retry_parked()` and the `_apply_park(...)` wrap from the loop and
# the suite stayed green: the park's end-to-end behaviour rested on two untested lines. main() runs forever, so the
# tripwire reads its syntax tree: both calls must sit in main()'s loop, the retry BEFORE the folder is read and the
# wrap AROUND tracker.reconcile, both before worker.snapshot(). A mutant that drops either must fail here.
import ast as _e9_ast
_e9_tree = _e9_ast.parse(Path(_wac.__file__).read_text(encoding="utf-8"))
_e9_main = next(n for n in _e9_tree.body if isinstance(n, _e9_ast.FunctionDef) and n.name == "main")
_e9_calls = []
for _n in _e9_ast.walk(_e9_main):
    if isinstance(_n, _e9_ast.Call):
        _f = _n.func
        _name = _f.id if isinstance(_f, _e9_ast.Name) else (_f.attr if isinstance(_f, _e9_ast.Attribute) else "")
        if _name in ("_retry_parked", "_pdfs_in_drop", "_apply_park", "reconcile", "snapshot"):
            _e9_calls.append((_n.lineno, _name, [getattr(a.func, "attr", getattr(a.func, "id", "")) for a in _n.args if isinstance(a, _e9_ast.Call)]))
_e9_calls.sort()
_e9_names = [c[1] for c in _e9_calls]
_e9_wrap = any(c[1] == "_apply_park" and "reconcile" in c[2] for c in _e9_calls)
check("_retry_parked" in _e9_names and "_apply_park" in _e9_names and _e9_wrap
      and _e9_names.index("_retry_parked") < _e9_names.index("_pdfs_in_drop") < _e9_names.index("_apply_park") < _e9_names.index("snapshot"),
      f"E9 (7) main()'s loop wires the park: _retry_parked() before _pdfs_in_drop(), _apply_park(tracker.reconcile(...)) before worker.snapshot() — calls={_e9_calls!r}")

print("SELFTEST " + ("PASS" if not FAILURES else f"FAIL ({len(FAILURES)})"))
raise SystemExit(0 if not FAILURES else 1)
