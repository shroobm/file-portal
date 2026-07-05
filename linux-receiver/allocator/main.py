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

from allocator.config import DEFAULT_ROOT, Paths
from allocator.rules import RuleSet
from allocator.status import StatusWriter

logger = logging.getLogger("file-portal-allocator")


class InboxHandler(FileSystemEventHandler):
    def __init__(
        self,
        paths: Paths,
        rules_path: Path,
        status: StatusWriter,
        react_to_created: bool = False,
    ):
        self.paths = paths
        self.rules_path = rules_path
        self.status = status
        # Only observers without close-event support (i.e. anything that isn't inotify) need
        # the on_created + stability-wait fallback -- see run().
        self.react_to_created = react_to_created

    def on_moved(self, event):
        # rsync renames its temp file into place on completion -- this is the event that
        # actually means "a full file has arrived." See docs/04-linux-receiver.md.
        if not event.is_directory:
            self._handle(Path(event.dest_path))

    def on_closed(self, event):
        # inotify IN_CLOSE_WRITE: the writer closed the file. This is the completion signal for
        # transports that write in place (the widget's `tailscale ssh ... cat > file` stream,
        # plain scp, a local `cp`). Reacting to on_created instead would race the transfer and
        # move half-written files.
        if not event.is_directory:
            self._handle(Path(event.src_path))

    def on_created(self, event):
        # Fallback for platforms whose observer never emits close events: wait until the file
        # size stops changing before treating it as complete. Not used on Linux/inotify, where
        # this event would double up with on_closed.
        if event.is_directory or not self.react_to_created:
            return
        file_path = Path(event.src_path)
        self._wait_until_stable(file_path)
        self._handle(file_path)

    def _handle(self, file_path: Path):
        # A single bad file (unreadable, template error, permission problem) must not kill the
        # observer thread and stop the service.
        try:
            self._allocate(file_path)
        except Exception:
            logger.exception("failed to allocate %s", file_path)

    def _allocate(self, file_path: Path):
        if not file_path.exists():
            return
        # The quarantine directory lives inside the watched inbox tree; without this guard the
        # allocator would re-process (and endlessly re-log) files it just quarantined.
        if self.paths.quarantine in file_path.parents:
            return
        # Dot-prefixed files are in-progress temp files (rsync writes `.name.XXXXXX` then
        # renames); the rename into place arrives separately as on_moved.
        if file_path.name.startswith("."):
            return

        rules = RuleSet.load(self.rules_path)
        category = file_path.parent.name
        size_mb = file_path.stat().st_size / (1024 * 1024)

        if size_mb > rules.defaults.max_file_size_mb:
            self._quarantine(file_path, category, f"exceeds max_file_size_mb ({size_mb:.1f}MB)")
            return

        dest_dir_rel = rules.resolve(category, file_path.name)
        dest_dir = self.paths.root / dest_dir_rel
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = self._resolve_collision(dest_dir / file_path.name, rules.defaults.on_collision)

        if dest_path is None:
            logger.info("SKIPPED %s (collision policy=skip)", file_path)
            self.status.record("skipped", file_path.name, category, reason="collision policy=skip")
            return

        shutil.move(str(file_path), str(dest_path))
        logger.info("ALLOCATED %s -> %s", file_path, dest_path)
        self.status.record(
            "allocated",
            file_path.name,
            category,
            dest=str(dest_path.relative_to(self.paths.root)),
        )

    def _quarantine(self, file_path: Path, category: str, reason: str):
        # Never overwrite an earlier quarantined file of the same name -- rename like the
        # default collision policy does.
        dest = self._resolve_collision(self.paths.quarantine / file_path.name, "rename")
        shutil.move(str(file_path), str(dest))
        logger.warning("REJECTED %s (%s) -> %s", file_path, reason, dest)
        self.status.record("rejected", file_path.name, category, reason=reason)

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

    @staticmethod
    def _wait_until_stable(file_path: Path, interval: float = 0.5, timeout: float = 60.0):
        """Block until file_path's size is unchanged across one polling interval.

        Only used on non-inotify platforms (react_to_created). Returns early if the file
        disappears; gives up after `timeout` seconds and lets _allocate see whatever is there.
        """
        deadline = time.monotonic() + timeout
        last_size = -1
        while time.monotonic() < deadline:
            try:
                size = file_path.stat().st_size
            except OSError:
                return
            if size == last_size:
                return
            last_size = size
            time.sleep(interval)


def _observer_emits_close_events(observer) -> bool:
    """True when the platform observer delivers on_closed (inotify's IN_CLOSE_WRITE).

    Only Linux/inotify does; every other backend (macOS FSEvents, Windows, polling) must fall
    back to on_created plus a size-stability wait.
    """
    try:
        from watchdog.observers.inotify import InotifyObserver
    except ImportError:
        return False
    return isinstance(observer, InotifyObserver)


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

    status = StatusWriter(paths.logs / "status.json")
    observer = Observer()
    handler = InboxHandler(
        paths,
        rules_path,
        status,
        react_to_created=not _observer_emits_close_events(observer),
    )
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
    parser.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT, help="file-portal root directory"
    )
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).parent.parent / "config" / "rules.toml"
    )
    args = parser.parse_args()
    run(args.root, args.config)


if __name__ == "__main__":
    main()
