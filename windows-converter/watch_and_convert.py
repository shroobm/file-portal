"""Desktop conveyor front door (S17): watch a local drop folder, convert arrivals.

Drop a PDF into DROP_DIR and it goes through the full slice-1 pipeline (policy-routed
Marker -> bundle -> anchor -> ship to ThinkPad staging -> existing exporter). Analyst
routing: the file `analyst-mode.txt` next to the drop folder holds `off`, `local`,
`gemini`, or `ask` (parks the conversion in pending/ for the widget's pre-flight card),
re-read before every conversion — the per-segment-switch principle from the docs/11
design note.

Design mirrors the allocator's watcher discipline, poll-based (no extra deps):
dotfiles ignored, size-stability wait before touching a file, one conversion at a
time (sequential loop = the Marker/Ollama single-flight guarantee on this GPU),
successes archived to done/, failures to failed/ with the error logged.

Run with the marker-env interpreter:
  C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe watch_and_convert.py
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from events import emit

# FP_PIPELINE / FP_CONVERT exist for the deferral-gate tripwire, which runs THIS file for real
# against an isolated root and a stub converter (SYM-010: never the live dirs, never Marker).
# Unset - the production case - nothing changes.
BASE = Path(os.environ.get("FP_PIPELINE", r"C:\Users\Bndit\ml\library"))
DROP_DIR = BASE / "drop"
DONE_DIR = DROP_DIR / "done"
FAILED_DIR = DROP_DIR / "failed"
MODE_FILE = BASE / "analyst-mode.txt"  # off | local | gemini | ask
LOCK_FILE = BASE / ".gpu-lock"  # busy signal for the future control-room card
HOLD_FILE = BASE / "chat-hold.json"  # the assistant's claim on the card - written by room_chat.py ONLY
LOG_FILE = BASE / "watcher.log"
CONVERT = Path(os.environ.get("FP_CONVERT", str(Path(__file__).parent / "convert_and_ship.py")))
PYTHON = sys.executable
PATTERNS = {".pdf"}
POLL_S = 5

logger = logging.getLogger("fp-desktop-watcher")


def analyst_mode() -> str:
    # "ask" parks conversions in pending/ for the widget's pre-flight card (S18).
    try:
        mode = MODE_FILE.read_text(encoding="utf-8").strip().lower()
        return mode if mode in ("off", "local", "gemini", "ask") else "off"
    except OSError:
        return "off"


def stable_size(path: Path, interval: float = 1.0, timeout: float = 120.0) -> bool:
    """True once the file size holds still across one interval (transfer finished)."""
    deadline = time.monotonic() + timeout
    last = -1
    while time.monotonic() < deadline:
        try:
            size = path.stat().st_size
        except OSError:
            return False
        if size == last:
            return True
        last = size
        time.sleep(interval)
    return False


# One deferral log/event per PDF per hold episode - the loop retries every POLL_S seconds and a
# held card can stay held for a long chat; a log line every 5 s would bury the signal.
_deferred: set[str] = set()


def pid_alive(pid: int) -> bool:
    """Windows process liveness, WITHOUT os.kill.

    On Windows, CPython's os.kill(pid, sig) is TerminateProcess(handle, sig) for ordinary sigs -
    the "harmless" POSIX liveness idiom os.kill(pid, 0) is a MURDER WEAPON here (or, depending
    on access rights, an OSError that reads as "dead"). The deferral tripwire caught this on its
    first run against the reaper: a live holder was declared dead and its hold reaped. The
    honest probe is OpenProcess + GetExitCodeProcess == STILL_ACTIVE.
    """
    import ctypes
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return False
    try:
        code = ctypes.c_ulong()
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


def convert_one(pdf: Path) -> None:
    hold = chat_hold()
    if hold:
        if pdf.name not in _deferred:
            _deferred.add(pdf.name)
            logger.info("DEFERRED %s - the assistant holds the card (chat-hold.json); "
                        "retrying every %ss until it clears", pdf.name, POLL_S)
            emit("intake", "deferred", source=pdf.name, reason="chat-hold")
        return
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
    try:
        # Backstop only — convert_and_ship caps Marker itself, scaled to the page count. This
        # outer cap exists so a wedged child can't block the queue forever, so it must sit ABOVE
        # the inner one or it silently becomes the real limit (a flat 7200 s made long books
        # unconvertible through the drop folder; found S45 on a 1,356-page book).
        proc = subprocess.run(args, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=21600)
    finally:
        LOCK_FILE.unlink(missing_ok=True)
    if proc.returncode == 0:
        dest = DONE_DIR / pdf.name
        shutil.move(str(pdf), str(dest))
        logger.info("DONE %s -> drop/done/ | %s", pdf.name,
                    (proc.stdout or "").strip().splitlines()[-1] if proc.stdout else "")
    else:
        dest = FAILED_DIR / pdf.name
        shutil.move(str(pdf), str(dest))
        logger.error("FAILED %s -> drop/failed/ (exit %s): %s", pdf.name,
                     proc.returncode, (proc.stderr or "").strip()[-400:])
        emit("intake", "failed", source=pdf.name, exit_code=proc.returncode)


def main() -> None:
    for d in (DROP_DIR, DONE_DIR, FAILED_DIR):
        d.mkdir(parents=True, exist_ok=True)
    if not MODE_FILE.exists():
        MODE_FILE.write_text("off\n", encoding="utf-8")
    logging.basicConfig(
        filename=LOG_FILE, level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger().addHandler(logging.StreamHandler())
    logger.info("watching %s (poll %ss, analyst-mode file: %s)", DROP_DIR, POLL_S, MODE_FILE)
    while True:
        try:
            for entry in sorted(DROP_DIR.iterdir()):
                if not entry.is_file() or entry.name.startswith("."):
                    continue
                if entry.suffix.lower() not in PATTERNS:
                    continue
                if not stable_size(entry):
                    continue
                convert_one(entry)
        except Exception:
            logger.exception("watcher loop error (continuing)")
        time.sleep(POLL_S)


if __name__ == "__main__":
    main()
