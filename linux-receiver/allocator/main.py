"""Entry point: watches inbox/<category>/ directories and allocates completed files according
to rules.toml. Runs as a systemd --user service -- see systemd/file-portal-allocator.service.
"""

import argparse
import logging
import shutil
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from allocator.config import Paths, DEFAULT_ROOT
from allocator.rules import RuleSet

logger = logging.getLogger("file-portal-allocator")


class InboxHandler(FileSystemEventHandler):
    def __init__(self, paths: Paths, rules_path: Path):
        self.paths = paths
        self.rules_path = rules_path

    def on_moved(self, event):
        # rsync renames its temp file into place on completion -- this is the event that
        # actually means "a full file has arrived." See docs/04-linux-receiver.md.
        if not event.is_directory:
            self._handle(Path(event.dest_path))

    def on_created(self, event):
        # Covers plain `scp` (and any tool that doesn't do an atomic rename).
        if not event.is_directory:
            self._handle(Path(event.src_path))

    def _handle(self, file_path: Path):
        if not file_path.exists():
            return

        rules = RuleSet.load(self.rules_path)
        category = file_path.parent.name
        size_mb = file_path.stat().st_size / (1024 * 1024)

        if size_mb > rules.defaults.max_file_size_mb:
            self._quarantine(file_path, f"exceeds max_file_size_mb ({size_mb:.1f}MB)")
            return

        dest_dir_rel = rules.resolve(category, file_path.name)
        dest_dir = self.paths.root / dest_dir_rel
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = self._resolve_collision(dest_dir / file_path.name, rules.defaults.on_collision)

        if dest_path is None:
            logger.info("SKIPPED %s (collision policy=skip)", file_path)
            return

        shutil.move(str(file_path), str(dest_path))
        logger.info("ALLOCATED %s -> %s", file_path, dest_path)

    def _quarantine(self, file_path: Path, reason: str):
        dest = self.paths.quarantine / file_path.name
        shutil.move(str(file_path), str(dest))
        logger.warning("REJECTED %s (%s) -> %s", file_path, reason, dest)

    @staticmethod
    def _resolve_collision(dest_path: Path, policy: str) -> Path | None:
        if not dest_path.exists():
            return dest_path
        if policy == "overwrite":
            return dest_path
        if policy == "skip":
            return None

        stem, suffix = dest_path.stem, dest_path.suffix
        n = 1
        while True:
            candidate = dest_path.with_name(f"{stem} ({n}){suffix}")
            if not candidate.exists():
                return candidate
            n += 1


def run(root: Path, rules_path: Path):
    paths = Paths.from_root(root)
    paths.ensure_exist()

    # Pre-create inbox/<category>/ for every category in rules.toml. rsync/scp can't create a
    # missing remote directory themselves, so without this the first transfer to a fresh
    # category would fail.
    rules = RuleSet.load(rules_path)
    categories = {rule.category for rule in rules.rules}
    for category in categories:
        (paths.inbox / category).mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        filename=paths.logs / "allocator.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger().addHandler(logging.StreamHandler())

    handler = InboxHandler(paths, rules_path)
    observer = Observer()
    observer.schedule(handler, str(paths.inbox), recursive=True)
    observer.start()
    logger.info("watching %s", paths.inbox)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main():
    parser = argparse.ArgumentParser(description="File Portal allocator service")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="file-portal root directory")
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).parent.parent / "config" / "rules.toml"
    )
    args = parser.parse_args()
    run(args.root, args.config)


if __name__ == "__main__":
    main()
