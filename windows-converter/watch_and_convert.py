"""Desktop conveyor front door (S17): watch a local drop folder, convert arrivals.

Drop a PDF into DROP_DIR and it goes through the full slice-1 pipeline (policy-routed
Marker -> bundle -> anchor -> ship to ThinkPad staging -> existing exporter). Analyst
routing is a manual toggle until the widget pre-flight card exists (S18): the file
`analyst-mode.txt` next to the drop folder holds `off`, `local`, or `gemini`, re-read
before every conversion — the per-segment-switch principle from the docs/11 design note.

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

BASE = Path(r"C:\Users\Bndit\ml\library")
DROP_DIR = BASE / "drop"
DONE_DIR = DROP_DIR / "done"
FAILED_DIR = DROP_DIR / "failed"
MODE_FILE = BASE / "analyst-mode.txt"  # off | local | gemini
LOCK_FILE = BASE / ".gpu-lock"  # busy signal for the future control-room card
LOG_FILE = BASE / "watcher.log"
CONVERT = Path(__file__).parent / "convert_and_ship.py"
PYTHON = sys.executable
PATTERNS = {".pdf"}
POLL_S = 5

logger = logging.getLogger("fp-desktop-watcher")


def analyst_mode() -> str:
    try:
        mode = MODE_FILE.read_text(encoding="utf-8").strip().lower()
        return mode if mode in ("off", "local", "gemini") else "off"
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
    if mode != "off":
        args += ["--analyst", "--backend", mode]
    logger.info("CONVERTING %s (analyst=%s)", pdf.name, mode)
    LOCK_FILE.write_text(pdf.name, encoding="utf-8")
    try:
        proc = subprocess.run(args, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=7200)
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
