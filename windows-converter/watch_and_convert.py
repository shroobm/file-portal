"""WHAT THIS FILE DOES: the long-running intake watcher. main() polls the drop folder for PDFs, decides when each
is fully copied (IntakeTracker), and hands the first ready one to a single worker thread, which runs
convert_and_ship.py as a child process (convert_one). It reads analyst-mode.txt, the chat-hold file and the card
mutex; it writes .gpu-lock, .intake-state.json, the watcher log, and moves finished PDFs to drop/done or
drop/failed. Started by the widget or by hand; one instance only (a named mutex).

Desktop conveyor front door (S17): watch a local drop folder, convert arrivals.

Drop a PDF into DROP_DIR and it goes through the full slice-1 pipeline (policy-routed
Marker -> bundle -> anchor -> ship to ThinkPad staging -> existing exporter). Analyst
routing: the file `analyst-mode.txt` next to the drop folder holds `off`, `local`,
`gemini`, or `ask` (parks the conversion in pending/ for the widget's pre-flight card),
re-read before every conversion — the per-segment-switch principle from the docs/11
design note.

Design mirrors the allocator's watcher discipline without making notifications truth:
dotfiles are ignored; ReadDirectoryChangesW is a wake hint; a periodic reconciliation
of drop/ is authoritative; a file must hold the same size+mtime for one second AND be
openable without write sharing before it is ready.  Intake keeps scanning while one
worker performs the single permitted conversion.  The watcher atomically publishes an
operator-facing receipt, .intake-state.json; it never moves the durable queue elsewhere.

Run with the marker-env interpreter:
  C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe watch_and_convert.py
"""

import json
import logging
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import fp_paths
from events import emit

# -- configuration: folders, state files, child command and timing constants --
# FP_PIPELINE / FP_CONVERT exist for the deferral-gate tripwire, which runs THIS file for real
# against an isolated root and a stub converter (SYM-010: never the live dirs, never Marker).
# Unset - the production case - nothing changes. Roots resolve through fp_paths (S108).
BASE = fp_paths.pipeline_root()
DROP_DIR = fp_paths.root("drop")
DONE_DIR = fp_paths.root("drop_done")
FAILED_DIR = fp_paths.root("drop_failed")
# S218 E6 (F5, SYM-174): the child's exit code for "converted and on the shelf, but the tar to staging failed" — the same
# number as convert_and_ship.SHIP_FAILED_EXIT (the watcher spawns the child, it does not import it; the selftest pins the two equal)
SHIP_FAILED_EXIT = 98
MODE_FILE = fp_paths.root("analyst_mode")  # off | local | gemini | ask
LOCK_FILE = fp_paths.root("gpu_lock")  # busy signal for the future control-room card
HOLD_FILE = fp_paths.root("chat_hold")  # the assistant's claim on the card - written by room_chat.py ONLY
LOG_FILE = fp_paths.root("watcher_log")
INTAKE_STATE_FILE = fp_paths.root("intake_state")
CONVERT = Path(os.environ.get("FP_CONVERT", str(Path(__file__).parent / "convert_and_ship.py")))
PYTHON = sys.executable
PATTERNS = {".pdf"}
POLL_S = 5
QUIET_S = 1.0
# The outer backstop. Review 2026-08-30: the stall-recovery ladder folded retry time into ONE
# child, so the inner bound can now exceed a flat 6 h (worst case ~9 Marker invocations per
# slice) — the Damodaran run came within ~20 min of this cap before a controlled restart.
# Env-overridable so an operator can raise it for a monster book without editing source.
# lever-waiver: Rab signed OK-17 2026-08-30; 8 h default = old 6 h + the measured worst
# ladder spend observed on the 1377-pp Damodaran (3 stalls x ~1600 s).
TIMEOUT_S = int(os.environ.get("FP_CONVERT_TIMEOUT_S", "28800"))

logger = logging.getLogger("fp-desktop-watcher")


# -- small helpers: analyst mode, timestamps, file readiness probe --
def analyst_mode() -> str:
    """Read analyst-mode.txt; returns one of off/local/gemini/ask, or "off" if unreadable or unknown."""
    # "ask" parks conversions in pending/ for the widget's pre-flight card (S18).
    try:
        mode = MODE_FILE.read_text(encoding="utf-8").strip().lower()
        return mode if mode in ("off", "local", "gemini", "ask") else "off"
    except OSError:
        return "off"


def _utc_now() -> str:
    """Current UTC time as an ISO-8601 string with milliseconds and a trailing Z."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _open_without_write_sharing(path: Path) -> bool:
    """Prove no writer still owns *path*; a quiet size alone cannot prove copy completion.

    A producer can grow, pause longer than QUIET_S, then resume.  Opening with FILE_SHARE_READ
    and FILE_SHARE_DELETE but deliberately NOT FILE_SHARE_WRITE conflicts with an existing
    write handle, so that pause remains `receiving`.  This is a readiness probe, never a lock:
    it is closed immediately and the worker rechecks just before dispatch.
    """
    if os.name != "nt":
        try:
            with path.open("rb"):
                return True
        except OSError:
            return False
    import ctypes
    from ctypes import wintypes

    generic_read = 0x80000000
    share_read = 0x00000001
    share_delete = 0x00000004
    open_existing = 3
    normal = 0x00000080
    invalid = wintypes.HANDLE(-1).value
    k32 = ctypes.windll.kernel32
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                wintypes.HANDLE]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = k32.CreateFileW(str(path), generic_read, share_read | share_delete, None,
                             open_existing, normal, None)
    if handle == invalid:
        return False
    k32.CloseHandle(handle)
    return True


# -- intake tracking: what the watcher knows about each file in drop/ --
@dataclass
class _Tracked:
    """What is known about one dropped file: last size and mtime, when first seen (wall and monotonic
    clocks), and since when its size/mtime have been unchanged."""
    size: int
    mtime_ns: int
    first_seen_wall: str
    first_seen_mono: float
    unchanged_since: float


class IntakeTracker:
    """Non-blocking reconciliation state.  Filesystem observations remain the authority."""

    def __init__(self, quiet_s: float = QUIET_S, readiness_probe=_open_without_write_sharing):
        """Set the quiet period and the readiness probe (injectable); start with no tracked files."""
        self.quiet_s = quiet_s
        self.readiness_probe = readiness_probe
        self.files: dict[str, _Tracked] = {}

    def restore(self, receipt_path: Path) -> int:
        """Restore durable detected age only when the prior receipt matches current bytes+mtime.

        Liveness and readiness are never inherited: unchanged_since resets to now, requiring a
        new quiet/share-mode proof.  Only the first-seen clock survives a watcher restart.
        """
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            # S219 E3-fix: a receipt that is not an object (null, a list, a number) is no receipt - 0 rows, never a raise
            # (this ran before _restore_parked at boot and an AttributeError here killed the watcher)
            if not isinstance(receipt, dict) or receipt.get("v") != 1 or not isinstance(receipt.get("items"), list):
                return 0
        except (OSError, json.JSONDecodeError):
            return 0
        now_mono = time.monotonic()
        now_wall = datetime.now(timezone.utc)
        restored = 0
        # re-adopt each receipt row whose file still has the same size and mtime; skip malformed rows
        for row in receipt["items"]:
            try:
                name = str(row["name"])
                size = int(row["bytes"])
                mtime_ns = int(row["mtime_ns"])
                first_text = str(row["first_seen_at"])
                first = datetime.fromisoformat(first_text.replace("Z", "+00:00"))
                if first.tzinfo is None:
                    first = first.replace(tzinfo=timezone.utc)
                path = DROP_DIR / name
                stat = path.stat()
                if stat.st_size != size or stat.st_mtime_ns != mtime_ns:
                    continue
                age_s = max(0.0, (now_wall - first.astimezone(timezone.utc)).total_seconds())
                self.files[name] = _Tracked(size, mtime_ns, first_text,
                                            now_mono - age_s, now_mono)
                restored += 1
            except (KeyError, TypeError, ValueError, OSError, OverflowError):
                continue
        return restored

    def reconcile(self, paths: list[Path], now: float | None = None) -> list[dict]:
        """Compare the PDFs now in drop/ with what is tracked; returns one row per file (name, bytes, mtime_ns,
        phase receiving/settling/ready, first_seen_at, wait_s, quiet_s) in filename order. Forgets vanished files."""
        now = time.monotonic() if now is None else now
        present = {p.name for p in paths}
        # forget files that left the folder
        for stale in set(self.files) - present:
            del self.files[stale]
        rows: list[dict] = []
        # classify each file: new or changed = receiving; unchanged < quiet_s = settling; else probe for a writer
        for path in sorted(paths, key=lambda p: p.name):
            try:
                stat = path.stat()
            except OSError:
                continue
            old = self.files.get(path.name)
            signature = (stat.st_size, stat.st_mtime_ns)
            if old is None:
                old = _Tracked(*signature, _utc_now(), now, now)
                self.files[path.name] = old
                phase = "receiving"
            elif signature != (old.size, old.mtime_ns):
                old.size, old.mtime_ns, old.unchanged_since = *signature, now
                phase = "receiving"
            else:
                quiet = now - old.unchanged_since
                if quiet < self.quiet_s:
                    phase = "settling"
                elif self.readiness_probe(path):
                    phase = "ready"
                else:
                    phase = "receiving"
            rows.append({
                "name": path.name,
                "bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "phase": phase,
                "first_seen_at": old.first_seen_wall,
                "wait_s": max(0, int(now - old.first_seen_mono)),
                "quiet_s": round(max(0.0, now - old.unchanged_since), 3),
            })
        return rows

    def next_quiet_delay(self, now: float | None = None) -> float:
        """Seconds until the soonest tracked file finishes its quiet period (at least 0.05), else POLL_S."""
        now = time.monotonic() if now is None else now
        remaining = [self.quiet_s - (now - f.unchanged_since) for f in self.files.values()]
        positive = [n for n in remaining if n > 0]
        return max(0.05, min(positive)) if positive else POLL_S


# -- state receipt, directory-change wake hint, and single-instance / card-ownership checks (Windows API) --
def _atomic_write_state(rows: list[dict], active: str | None, wake_mode: str,
                        card_state: str = "UNREAD") -> None:
    """Watcher-only, dot-then-replace publication.  Failure is cosmetic and best-effort."""
    phases = {row["name"]: row for row in rows}
    if active and active in phases:
        phases[active]["phase"] = "running"
    ordered = [phases[name] for name in sorted(phases)]
    receipt = {
        "v": 1,
        "writer_pid": os.getpid(),
        "written_at": _utc_now(),
        "wake_mode": wake_mode,
        "card_state": card_state,
        "active": active,
        "waiting": sum(1 for row in ordered if row["name"] != active),
        "items": ordered,
    }
    tmp = INTAKE_STATE_FILE.with_name(f"{INTAKE_STATE_FILE.name}.tmp.{os.getpid()}")
    try:
        tmp.write_text(json.dumps(receipt, ensure_ascii=False, separators=(",", ":")) + "\n",
                       encoding="utf-8")
        os.replace(tmp, INTAKE_STATE_FILE)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _directory_change_listener(wake: threading.Event) -> None:
    """Best-effort Windows wake hint.  Any failure returns control to periodic reconciliation."""
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes

    file_list_directory = 0x0001
    share_all = 0x00000001 | 0x00000002 | 0x00000004
    open_existing = 3
    backup_semantics = 0x02000000
    notify_mask = 0x00000001 | 0x00000008 | 0x00000010
    invalid = wintypes.HANDLE(-1).value
    k32 = ctypes.windll.kernel32
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                wintypes.HANDLE]
    k32.ReadDirectoryChangesW.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, wintypes.BOOL,
        wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    # open the drop folder, block on change notifications and set `wake`; reopen after any failure
    while True:
        handle = k32.CreateFileW(str(DROP_DIR), file_list_directory, share_all, None,
                                 open_existing, backup_semantics, None)
        if handle == invalid:
            return
        try:
            buf = ctypes.create_string_buffer(8192)
            used = wintypes.DWORD()
            while k32.ReadDirectoryChangesW(handle, buf, len(buf), False, notify_mask,
                                             ctypes.byref(used), None, None):
                wake.set()
        finally:
            k32.CloseHandle(handle)
        time.sleep(1)


def _claim_single_watcher() -> bool:
    """One real interpreter owns intake, even when the configured exe is a launcher shim."""
    if os.name != "nt":
        return True
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.windll.kernel32
    k32.CreateMutexW.restype = wintypes.HANDLE
    k32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    # FP_WATCHER_MUTEX: a selftest's per-run name (S141) - the production case is the fixed name; the
    # fixed name alone made the deferral-gate tripwire exit 3 beside the live watcher since 2026-08-31.
    name = os.environ.get("FP_WATCHER_MUTEX", "Local\\FilePortalWatcher")
    handle = k32.CreateMutexW(None, False, name)
    if not handle:
        return False
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.kernel32.CloseHandle(handle)
        return False
    # Intentionally retain the handle for process lifetime.
    globals()["_WATCHER_MUTEX_HANDLE"] = handle
    return True


def _card_mutex_busy() -> bool | None:
    """Read card ownership without retaining it: True busy, False idle, None UNREAD."""
    if os.name != "nt":
        return False
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.windll.kernel32
    k32.CreateMutexW.restype = wintypes.HANDLE
    k32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k32.ReleaseMutex.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    name = os.environ.get("FP_CARD_MUTEX", "Local\\file-portal-card")
    handle = k32.CreateMutexW(None, False, name)
    if not handle:
        return None
    try:
        result = k32.WaitForSingleObject(handle, 0)
        if result == 0x102:  # WAIT_TIMEOUT: another process owns it
            return True
        if result in (0x00, 0x80):  # WAIT_OBJECT_0 / WAIT_ABANDONED: we briefly own it
            k32.ReleaseMutex(handle)
            return False
        return None
    finally:
        k32.CloseHandle(handle)


# -- deferral and the assistant's chat-hold on the card --
# One deferral log/event per PDF per hold episode - the loop retries every POLL_S seconds and a
# held card can stay held for a long chat; a log line every 5 s would bury the signal.
_deferred: set[str] = set()


def _note_deferred(name: str, reason: str) -> None:
    """One DEFERRED line + one `intake deferred` event per PDF per episode (S141: since f045a66 the loop
    pre-empts the dispatch under a hold, so convert_one's own branch was unreachable and the event stream
    lost every deferral - the state file alone knew)."""
    if name in _deferred:
        return
    _deferred.add(name)
    if reason == "chat-hold":
        logger.info("DEFERRED %s - the assistant holds the card (chat-hold.json); "
                    "retrying every %ss until it clears", name, POLL_S)
    else:
        logger.info("DEFERRED %s - the card mutex is %s; retrying every %ss until it clears",
                    name, reason, POLL_S)
    emit("intake", "deferred", source=name, reason=reason)


def pid_alive(pid: int) -> bool:
    """Windows process liveness, WITHOUT os.kill.

    On Windows, CPython's os.kill(pid, sig) is TerminateProcess(handle, sig) for ordinary sigs -
    the "harmless" POSIX liveness idiom os.kill(pid, 0) is a MURDER WEAPON here (or, depending
    on access rights, an OSError that reads as "dead"). The deferral tripwire caught this on its
    first run against the reaper: a live holder was declared dead and its hold reaped. The
    honest probe is OpenProcess + GetExitCodeProcess == STILL_ACTIVE.
    """
    import ctypes
    from ctypes import wintypes
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    k32 = ctypes.windll.kernel32
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return False
    try:
        code = wintypes.DWORD()
        if not k32.GetExitCodeProcess(h, ctypes.byref(code)):
            return False
        return code.value == STILL_ACTIVE
    finally:
        k32.CloseHandle(h)


def chat_hold() -> str | None:
    """The assistant's claim on the card - READ here, written only by room_chat.py.

    THE SIGNED WATCHER DEFERRAL GATE (docs/33 §2.3, signed by Rab 2026-08-15; built S85 on his
    graduation commission). The conveyor refuses to START a conversion while the assistant holds
    the card; the PDF stays in drop/ and the normal poll picks it up the moment the hold clears.
    A lost intent is the safe direction (docs/19) - and unlike `.gpu-lock` (SYM-032), this file
    is read by the thing that yields, which is what makes it a gate instead of a name.

    THE STALE-HOLD REAP, and why the reader may delete the writer's file here and nowhere else:
    the widget's Job Object kills the chat server with TerminateProcess - no cleanup runs - so a
    hold from a dead pid would defer the conveyor FOREVER. The single-writer law protects
    against conflicting INTENT; a dead process has none. The reap is keyed on pid liveness
    (mechanical, os.kill(pid, 0)), logged, and deletes only what can no longer be released by
    its owner. A malformed hold is stale by definition - unreadable JSON cannot hold a card.
    """
    try:
        raw = HOLD_FILE.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        rec = json.loads(raw)
        pid = int(rec.get("pid", -1))
        if pid > 0 and pid_alive(pid):
            return str(rec.get("model") or rec.get("held_by") or "the assistant")
        reason = f"pid {pid} is dead" if pid > 0 else "hold carries no pid"
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        reason = f"malformed ({e})"
    try:
        HOLD_FILE.unlink(missing_ok=True)
        logger.warning("REAPED a stale chat-hold (%s) - the card was never actually held", reason)
        emit("intake", "stale-hold-reaped", reason=reason)
    except OSError:
        pass
    return None


# -- converting one PDF: move the source, run the child converter, classify its exit --
def _move_source(pdf: Path, dest_dir: Path, outcome: str) -> str:
    """Move the converted source out of drop/; returns where it went, for the DONE/FAILED line.

    A failure is an EVENT and one log line, never a bare traceback (S141, unread-surfaces): on
    2026-08-31 the source left drop/ by another hand 20 s into its conversion (drop/failed/ was
    written at 07:37:14Z, between `estimate` and `converted`) and the only trace was a
    "watcher loop error (continuing)" traceback in watcher.log - events.jsonl never learned that
    the book's source had vanished. The full-width colon in that name was NOT the cause: the same
    name had moved on 07-19 and twice on 07-22.
    """
    dest = dest_dir / pdf.name
    try:
        shutil.move(str(pdf), str(dest))
        return "drop/%s/" % dest_dir.name
    except OSError as e:
        if not pdf.exists():
            reason = "source missing from drop/ (removed by another hand during the conversion)"
        else:
            reason = ("%s: %s" % (type(e).__name__, e))[:300]
        logger.error("MOVE FAILED %s -> drop/%s/ after %s: %s", pdf.name, dest_dir.name, outcome, reason)
        emit("intake", "move_failed", source=pdf.name, outcome=outcome, dest="drop/%s/" % dest_dir.name,
             reason=reason)
        if pdf.exists():
            _park(pdf, dest_dir, outcome, reason)
        return "NOT MOVED (%s)" % reason


# -- the park register (S218 E9, SYM-190's line side): a source the watcher could not move out of drop/ is remembered by
# name AND identity (size, mtime) and never dispatched again while that same file sits there; only its MOVE is retried,
# every poll, until it succeeds (MOVED LATE) or the file leaves drop/ by another hand or is re-dropped as a new file --
_parked: dict[str, dict] = {}


def _park(pdf: Path, dest_dir: Path, outcome: str, reason: str) -> None:
    """Remember a source whose move out of drop/ failed: its identity (size, mtime_ns), where it was going, why it
    failed, since when. Before this (2026-09-27, SYM-190) the loop saw the file still in drop/, read it ready and
    converted the same book a second time - a full pass of the card for a book already on the shelf."""
    try:
        st = pdf.stat()
    except OSError:
        return
    _parked[pdf.name] = {"reason": reason, "outcome": outcome, "dest": dest_dir, "size": st.st_size,
                         "mtime_ns": st.st_mtime_ns, "since": time.monotonic(), "since_wall": _utc_now()}
    logger.warning("PARKED %s (not moved after %s): never re-dispatched while this file sits in drop/; "
                   "the move is retried each poll - %s", pdf.name, outcome, reason)


def _apply_park(rows: list[dict]) -> list[dict]:
    """Mark the parked rows for the receipt and the card - phase `deferred` (a phase the widget already renders)
    plus `parked: true` and the reason - and clear entries whose file left drop/ by another hand or was re-dropped
    under the same name as a different file (a new size/mtime is a new book, dispatchable)."""
    present = {row["name"]: row for row in rows}
    for name in list(_parked):
        entry = _parked[name]
        row = present.get(name)
        if row is None:
            logger.info("PARK CLEARED %s: the source left drop/ by another hand", name)
            del _parked[name]
            continue
        if (row["bytes"], row["mtime_ns"]) != (entry["size"], entry["mtime_ns"]):
            logger.info("PARK CLEARED %s: a different file under the same name (re-dropped)", name)
            del _parked[name]
            continue
        row["phase"] = "deferred"
        row["parked"] = True
        row["reason"] = "parked: " + entry["reason"]
        # S218 E11: what a restart needs to rebuild the entry from the receipt (the watcher's own durable store);
        # S219 E3-fix: a park HELD without a destination writes park_dest null, so the next restart holds it again
        row["park_dest"] = entry["dest"].name if entry["dest"] is not None else None
        row["park_outcome"] = entry["outcome"]
        row["parked_since"] = entry["since_wall"]
    return rows


def _restore_parked(receipt_path: Path) -> int:
    """S218 E11: rebuild the park register from the last receipt at boot - every row marked `parked` whose file is still
    in drop/ with the same size and mtime_ns is parked again (reason, dest, outcome, since); a changed or absent file
    restores nothing. Before this a restart forgot the park and the next poll converted the parked book again.
    S219 E3 (E11's blind verifier): a row that is not a dict is skipped (it raised AttributeError and killed the boot).
    S219 E3-fix (E3's blind verifier): a parked row without BOTH park keys (an old-shape receipt), with a null or an odd
    `park_dest`, is restored as a park WITHOUT a destination - in the register (never dispatched), never moved by
    _retry_parked, logged PARK HELD once, for a hand to decide. E3 had SKIPPED such a row, which left its file `ready`
    in drop/ and the next poll would have converted a finished book again (SYM-190's own symptom); the code before E3
    guessed done/done (a misfile). A parked row without a name cannot be parked: skipped and counted. The file's
    presence and identity are checked before anything is logged, so an absent file is dropped silently as before."""
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        items = receipt.get("items") if receipt.get("v") == 1 else None
    except (OSError, json.JSONDecodeError, AttributeError):
        return 0
    if not isinstance(items, list):
        return 0
    restored = 0
    skipped = 0
    for row in items:
        if not isinstance(row, dict):
            skipped += 1
            continue
        try:
            if not row.get("parked"):
                continue
            if "name" not in row:
                skipped += 1
                continue
            name = str(row["name"])
            st = (DROP_DIR / name).stat()
            if st.st_size != int(row["bytes"]) or st.st_mtime_ns != int(row["mtime_ns"]):
                continue
            keyless = "park_dest" not in row or "park_outcome" not in row
            dest_name = None if keyless else str(row["park_dest"])
            if dest_name == FAILED_DIR.name:
                dest = FAILED_DIR
            elif dest_name == DONE_DIR.name:
                dest = DONE_DIR
            else:
                dest = None   # keyless, null, or a name that is neither done nor failed: held without a destination
            reason = str(row.get("reason") or "")
            reason = reason[len("parked: "):] if reason.startswith("parked: ") else reason
            outcome = str(row["park_outcome"]) if "park_outcome" in row and row["park_outcome"] is not None else "unknown"
            _parked[name] = {"reason": reason, "outcome": outcome, "dest": dest,
                             "size": st.st_size, "mtime_ns": st.st_mtime_ns, "since": time.monotonic(),
                             "since_wall": str(row.get("parked_since") or _utc_now())}
            if dest is None:
                logger.warning("PARK HELD %s: parked without a destination (an old-shape or odd receipt row, park_dest=%r) - "
                               "never dispatched, never moved; a hand decides", name, row.get("park_dest"))
            else:
                logger.warning("PARK RESTORED %s from the receipt (parked since %s): %s", name, _parked[name]["since_wall"], reason)
            restored += 1
        except (KeyError, TypeError, ValueError, OSError):
            continue
    if skipped:
        logger.warning("PARK RESTORE: %d receipt row(s) skipped (not a dict, or parked without a name)", skipped)
    return restored


def _retry_parked() -> None:
    """Retry the MOVE (never the conversion) of every parked source still in drop/ with its parked identity; on
    success log MOVED LATE, emit intake/moved_late with the seconds waited, and forget it."""
    for name in list(_parked):
        entry = _parked[name]
        if entry["dest"] is None:
            continue   # S219 E3-fix: held without a destination - never moved, never dispatched; a hand decides
        src = DROP_DIR / name
        try:
            st = src.stat()
        except OSError:
            continue   # gone - _apply_park clears the entry on the next reconcile
        if (st.st_size, st.st_mtime_ns) != (entry["size"], entry["mtime_ns"]):
            continue   # re-dropped as a new file - not ours to move
        dest = entry["dest"] / name
        try:
            shutil.move(str(src), str(dest))
        except OSError:
            continue   # still held; the next poll tries again
        waited = int(time.monotonic() - entry["since"])
        logger.info("MOVED LATE %s -> drop/%s/ after %d s (parked since %s)", name, entry["dest"].name, waited,
                    entry["since_wall"])
        emit("intake", "moved_late", source=name, dest="drop/%s/" % entry["dest"].name, outcome=entry["outcome"],
             waited_s=waited)
        del _parked[name]


def convert_one(pdf: Path) -> str:
    """Convert one PDF by running convert_and_ship.py as a child (analyst flags follow analyst-mode.txt).
    Returns "deferred" (chat-hold, PDF stays in drop/), "done" (exit 0, or the ship-failed exit; PDF moved to
    drop/done) or "failed" (other exit or timeout; PDF to drop/failed with its stderr). Writes/removes .gpu-lock."""
    hold = chat_hold()
    if hold:
        if pdf.name not in _deferred:
            _deferred.add(pdf.name)
            logger.info("DEFERRED %s - the assistant holds the card (chat-hold.json); "
                        "retrying every %ss until it clears", pdf.name, POLL_S)
            emit("intake", "deferred", source=pdf.name, reason="chat-hold")
        return "deferred"
    _deferred.discard(pdf.name)
    mode = analyst_mode()
    args = [PYTHON, str(CONVERT), str(pdf)]
    if mode == "ask":
        args += ["--defer-analyst"]
    elif mode != "off":
        args += ["--analyst", "--backend", mode]
    logger.info("CONVERTING %s (analyst=%s)", pdf.name, mode)
    emit("intake", "detected", source=pdf.name, analyst_mode=mode)
    LOCK_FILE.write_text(pdf.name, encoding="utf-8")
    timed_out = False
    try:
        # Backstop only — convert_and_ship caps Marker itself, scaled to the page count. This
        # outer cap exists so a wedged child can't block the queue forever, so it must sit ABOVE
        # the inner one or it silently becomes the real limit (a flat 7200 s made long books
        # unconvertible through the drop folder; found S45 on a 1,356-page book).
        # Popen + explicit tree-kill, NOT subprocess.run: run's internal timeout kill is
        # TerminateProcess on the DIRECT child only — the launcher-vs-real-python orphan class.
        # A timed-out convert used to leave marker's python holding ~9.7 GB of VRAM with no
        # `failed` event and the PDF still in drop/, so the next poll started a SECOND
        # converter beside the orphan (review 2026-08-30, the worst path in this file).
        # S187 E3 (SYM-135): the child's OWN stdout encoding is the child's env's business — the widget's spawn sets
        # PYTHONIOENCODING for this watcher (watcher.rs) but a watcher spawned another way (the lane's S175 WMI respawn)
        # did not, and the child died at a print on a non-cp1252 character. Pass it explicitly; convert_and_ship also
        # reconfigures its streams at import, so either half alone would do — both are kept.
        child = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, encoding="utf-8", errors="replace",
                                 env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        try:
            out, err = child.communicate(timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired:
            timed_out = True
            subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                           capture_output=True)
            out, err = child.communicate()
    finally:
        LOCK_FILE.unlink(missing_ok=True)
    # classify the child's outcome: clean exit, ship-failed exit (still done), or failure/timeout
    if child.returncode == 0 and not timed_out:
        went = _move_source(pdf, DONE_DIR, "done")
        logger.info("DONE %s -> %s | %s", pdf.name, went,
                    (out or "").strip().splitlines()[-1] if out else "")
        return "done"
    elif child.returncode == SHIP_FAILED_EXIT and not timed_out:
        # S218 E6 (F5, SYM-174): exit 98 is the child's SHIP-FAILED — the conversion is COMPLETE, audited, on the shelf and
        # registered; only the tar to the ThinkPad's staging failed (the child has emitted ship/failed with the error). The
        # SOURCE is done, never quarantined under failed (where it read as a Marker crash in the Room and in PORTAL, and where
        # the re-audit tools could not find it until S218 E5). No event is minted here: the intake vocabulary has no `done`
        # kind and T7 forbids one the Room cannot speak; the child's ship/failed carries the fact and the log says it.
        went = _move_source(pdf, DONE_DIR, "done")
        logger.warning("DONE %s -> %s (SHIP-FAILED: the bundle is on the shelf, not in staging — the ship leg failed: ssh, tar or the remote move-aside; the reason is in ship/failed) | %s",
                       pdf.name, went, (out or "").strip().splitlines()[-1] if out else "")
        return "done"
    else:
        went = _move_source(pdf, FAILED_DIR, "failed")
        exit_code = "timeout" if timed_out else child.returncode
        # S214 E18 (SYM-189's residue): the tail below cut the exception's TYPE off twice on one book (pdfium's
        # "Unsupported security scheme", found only by a probe). The whole stderr is kept beside the failed PDF.
        kept = ""
        try:
            stderr_path = FAILED_DIR / (pdf.stem + ".stderr.txt")
            stderr_path.write_text(err or "", encoding="utf-8", errors="replace")
            kept = " | whole stderr: %s" % stderr_path.name
        except OSError as e:
            kept = " | whole stderr NOT KEPT (%s)" % e.__class__.__name__
        logger.error("FAILED %s -> %s (exit %s): %s%s", pdf.name, went,
                     exit_code, (err or "").strip()[-400:], kept)
        emit("intake", "failed", source=pdf.name, exit_code=exit_code,
             **({"timeout_s": TIMEOUT_S} if timed_out else {}))
        return "failed"


# -- the single conversion worker thread --
class _Worker:
    """Exactly one conversion worker; intake reconciliation never blocks behind Marker."""

    def __init__(self, wake: threading.Event):
        """Create the one-slot job queue and start the daemon worker thread; `wake` is set after each job."""
        self.wake = wake
        self.jobs: queue.Queue[Path] = queue.Queue(maxsize=1)
        self._lock = threading.Lock()
        self._active: str | None = None
        self._reserved = False
        threading.Thread(target=self._run, name="file-portal-convert", daemon=True).start()

    def snapshot(self) -> tuple[bool, str | None]:
        """Return (a job is reserved, name of the active PDF or None), read under the lock."""
        with self._lock:
            return self._reserved, self._active

    def submit(self, pdf: Path) -> bool:
        """Queue `pdf` for conversion; returns False if a job is already reserved, True once queued."""
        with self._lock:
            if self._reserved:
                return False
            self._reserved = True
            self._active = pdf.name
        self.jobs.put_nowait(pdf)
        self.wake.set()
        return True

    def _run(self) -> None:
        """Worker thread body: take a job, recheck the file has no writer, convert it, then clear the active
        state and wake the main loop. Any exception is logged and emitted as a worker_error event."""
        while True:
            pdf = self.jobs.get()
            try:
                # Recheck the transfer boundary at the last responsible moment.  A producer
                # that reopened the file after reconciliation goes back to receiving.
                if not _open_without_write_sharing(pdf):
                    logger.info("READINESS REVOKED %s - writer handle is open", pdf.name)
                    continue
                convert_one(pdf)
            except Exception as e:
                logger.exception("conversion worker error for %s; PDF remains on durable belt",
                                 pdf.name)
                emit("intake", "worker_error", source=pdf.name,
                     error=("%s: %s" % (type(e).__name__, e))[:300])
            finally:
                with self._lock:
                    self._active = None
                    self._reserved = False
                self.jobs.task_done()
                self.wake.set()


# -- the main loop --
def _pdfs_in_drop() -> list[Path]:
    """List non-hidden .pdf files directly in the drop folder; [] if the folder cannot be read."""
    try:
        return [p for p in DROP_DIR.iterdir()
                if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in PATTERNS]
    except OSError:
        return []


def _next_dispatch(rows: list[dict]) -> str | None:
    """The first filename is the queue head; later ready rows may not bypass it. A PARKED row (S218 E9: a source
    the watcher could not move) is not in the queue - it is skipped and the row behind it is the head."""
    for row in rows:
        # S218 E11: the live register too - a park written by the worker AFTER this poll read its rows (the conversion
        # finished between reconcile and snapshot) must not let the same file dispatch once more
        if row.get("parked") or row["name"] in _parked:
            continue
        return row["name"] if row["phase"] == "ready" else None
    return None


def main() -> None:
    """Run the watcher forever: create folders, set up logging, claim the single-instance mutex (exit 3 if
    taken), start the worker and the change listener, then loop reconcile -> dispatch -> publish state."""
    for d in (DROP_DIR, DONE_DIR, FAILED_DIR):
        d.mkdir(parents=True, exist_ok=True)
    if not MODE_FILE.exists():
        MODE_FILE.write_text("off\n", encoding="utf-8")
    logging.basicConfig(
        filename=LOG_FILE, level=logging.INFO, encoding="utf-8",  # S141: was the locale's cp1252
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger().addHandler(logging.StreamHandler())
    if not _claim_single_watcher():
        logger.error("another real File Portal watcher already owns %s",
                     os.environ.get("FP_WATCHER_MUTEX", "Local\\FilePortalWatcher"))
        raise SystemExit(3)
    wake = threading.Event()
    worker = _Worker(wake)
    tracker = IntakeTracker()
    restored = tracker.restore(INTAKE_STATE_FILE)
    reparked = _restore_parked(INTAKE_STATE_FILE)   # S218 E11: the park survives a restart
    notify = threading.Thread(target=_directory_change_listener, args=(wake,),
                              name="file-portal-drop-notify", daemon=True)
    notify.start()
    wake_mode = "notify+reconcile" if os.name == "nt" else "reconcile"
    logger.info("watching %s (%s, fallback %ss, quiet %.1fs, analyst-mode file: %s)",
                DROP_DIR, wake_mode, POLL_S, QUIET_S, MODE_FILE)
    if restored:
        logger.info("restored first-seen age for %s waiting PDF(s)", restored)
    if reparked:
        logger.info("restored the park for %s source(s) from the receipt", reparked)
    # one pass per wake-up or poll interval; an error in a pass is logged and the loop continues
    while True:
        try:
            _retry_parked()   # S218 E9: a parked source's MOVE is retried before the folder is read
            paths = _pdfs_in_drop()
            rows = _apply_park(tracker.reconcile(paths))
            busy, active = worker.snapshot()
            card_busy = _card_mutex_busy()
            card_state = "busy" if card_busy is True else "idle" if card_busy is False else "UNREAD"
            external_block = card_busy is not False
            # A lock is only an active-file name when the kernel card mutex corroborates it.
            # If the card is idle, the lock is stale residue from a dead watcher and this
            # watcher (its sole writer) reaps it instead of republishing fiction as fresh state.
            if not busy:
                try:
                    lock_name = LOCK_FILE.read_text(encoding="utf-8").strip()
                except OSError:
                    lock_name = ""
                if lock_name and card_busy is True and any(row["name"] == lock_name for row in rows):
                    active = lock_name
                elif lock_name and card_busy is False:
                    LOCK_FILE.unlink(missing_ok=True)
                    logger.warning("REAPED stale .gpu-lock for %s; card mutex is idle", lock_name)
                    emit("intake", "stale-lock-reaped", source=lock_name)
            # while the assistant or another process holds the card, mark ready files as deferred
            hold = chat_hold()
            if hold or (not busy and external_block and not active):
                for row in rows:
                    if row["phase"] == "ready" and row["name"] != active:
                        row["phase"] = "deferred"
                        _note_deferred(row["name"], "chat-hold" if hold else card_state)
            if not busy and not active and not hold and not external_block:
                # Filename order is the queue law, not merely a sort over ready rows: a later
                # PDF must never bypass an earlier file that is still receiving or settling.
                ready_name = _next_dispatch(rows)
                if ready_name:
                    candidate = DROP_DIR / ready_name
                    if worker.submit(candidate):
                        active = candidate.name
                        busy = True
            _atomic_write_state(rows, active, wake_mode, card_state)
        except Exception:
            logger.exception("watcher loop error (continuing)")
        delay = min(POLL_S, tracker.next_quiet_delay())
        wake.wait(delay)
        wake.clear()


if __name__ == "__main__":
    main()
