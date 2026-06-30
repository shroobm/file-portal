"""Entry point: watches pipeline/convert-inbox and (for now) only logs arrivals.

This is the Part 2 skeleton from docs/10-library-pipeline-plan.md -- the conversion engine
(PyMuPDF4LLM / Pandoc, Clean/Scan lanes, bundle output) lands in Part 3. It reuses the allocator's
event model: prefer the atomic-rename (on_moved) signal, fall back to on_created, and skip the
".part-*" temp files the transfer writes. Runs as a systemd --user service -- see
systemd/file-portal-converter.service.
"""

import argparse
import logging
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from converter.config import Paths, DEFAULT_ROOT

logger = logging.getLogger("file-portal-converter")


class ConvertHandler(FileSystemEventHandler):
    def on_moved(self, event):
        # The allocator moves a completed file into convert-inbox via an atomic rename, so this is
        # the event that actually means "a full file has arrived." Same pattern as the allocator.
        if not event.is_directory:
            self._handle(Path(event.dest_path))

    def on_created(self, event):
        # Fallback for tools/moves that surface as a create rather than a rename.
        if not event.is_directory:
            self._handle(Path(event.src_path))

    def _handle(self, file_path: Path):
        # Skip dotfiles: the transfer streams into a ".part-<name>" file before renaming it into
        # place, so only the final, complete file should be converted.
        if file_path.name.startswith("."):
            return
        if not file_path.exists():
            return
        # Part 3 replaces this with real dispatch (.pdf/.epub -> PyMuPDF4LLM, .docx -> Pandoc).
        logger.info("would convert %s", file_path)


def run(root: Path):
    paths = Paths.from_root(root)
    paths.ensure_exist()

    logging.basicConfig(
        filename=paths.logs / "converter.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger().addHandler(logging.StreamHandler())

    handler = ConvertHandler()
    observer = Observer()
    observer.schedule(handler, str(paths.convert_inbox), recursive=True)
    observer.start()
    logger.info("watching %s", paths.convert_inbox)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main():
    parser = argparse.ArgumentParser(description="File Portal converter service")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="file-portal root directory")
    args = parser.parse_args()
    run(args.root)


if __name__ == "__main__":
    main()
