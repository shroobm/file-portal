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

import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path

from events import emit

BASE = Path(r"C:\Users\Bndit\ml\library")
DROP_DIR = BASE / "drop"
DONE_DIR = DROP_DIR / "done"
FAILED_DIR = DROP_DIR / "failed"
MODE_FILE = BASE / "analyst-mode.txt"  # off | local | gemini | ask
LOCK_FILE = BASE / ".gpu-lock"  # busy signal for the future control-room card
LOG_FILE = BASE / "watcher.log"
CONVERT = Path(__file__).parent / "convert_and_ship.py"
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


def convert_one(pdf: Path) -> None:
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
