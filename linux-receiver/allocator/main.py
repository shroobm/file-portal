"""WHAT THIS FILE DOES: the allocator service. It watches inbox/<category>/ for finished files,
moves each into the folder rules.toml picks (or quarantine if too big), and records the outcome
in logs/status.json. Entry points: main() (command line), run() (the service loop), InboxHandler
(the file-event handler) and sweep_inbox() (startup backlog). It reads the rules file, moves
files under the root, writes logs/allocator.log and tells systemd READY/WATCHDOG.

Entry point: watches inbox/<category>/ directories and allocates completed files according
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
from allocator.sdnotify import sd_notify, watchdog_armed
from allocator.status import StatusWriter

# -- shared logger --
logger = logging.getLogger("file-portal-allocator")


# -- the file-event handler: decides when a file is complete and moves it --
class InboxHandler(FileSystemEventHandler):
    """Watchdog handler for the inbox tree: turns file-complete events into allocations."""

    def __init__(
        self,
        paths: Paths,
        rules_path: Path,
        status: StatusWriter,
        react_to_created: bool = False,
    ):
        """Store the directories, rules.toml path, status writer and the on_created fallback flag."""
        self.paths = paths
        self.rules_path = rules_path
        self.status = status
        # Only observers without close-event support (i.e. anything that isn't inotify) need
        # the on_created + stability-wait fallback -- see run().
        self.react_to_created = react_to_created

    # -- watchdog event callbacks --
    def on_moved(self, event):
        """A file was renamed into place (the transport's finishing step): allocate the new path."""
        # The transport's finishing rename (transfer.rs streams to `.part-<name>` then `mv`s it
        # into place; rsync did the same in its era) -- this is the event that actually means
        # "a full file has arrived." See docs/04-linux-receiver.md.
        if not event.is_directory:
            self._handle(Path(event.dest_path))

    def on_closed(self, event):
        """A writer closed a file (inotify close-write): allocate it; directories are ignored."""
        # inotify IN_CLOSE_WRITE: the writer closed the file. This is the completion signal for
        # transports that write in place (the widget's `tailscale ssh ... cat > file` stream,
        # plain scp, a local `cp`). Reacting to on_created instead would race the transfer and
        # move half-written files.
        if not event.is_directory:
            self._handle(Path(event.src_path))

    def on_created(self, event):
        """Fallback for observers without close events: wait for the size to settle, then allocate."""
        # Fallback for platforms whose observer never emits close events: wait until the file
        # size stops changing before treating it as complete. Not used on Linux/inotify, where
        # this event would double up with on_closed.
        if event.is_directory or not self.react_to_created:
            return
        file_path = Path(event.src_path)
        self._wait_until_stable(file_path)
        self._handle(file_path)

    # -- allocation: guarded entry, the move itself, quarantine, collision naming --
    def _handle(self, file_path: Path):
        """Run _allocate on one file; on any error log it and write a 'rejected' status record."""
        # A single bad file (unreadable, template error, permission problem) must not kill the
        # observer thread and stop the service.
        try:
            self._allocate(file_path)
        except Exception as exc:
            logger.exception("failed to allocate %s", file_path)
            # S157 E54 (B32 U05, Codex's 2026-08-27 audit): the exception used to be logged and NOTHING written to
            # status.json, so the widget waited forever on a job that had already died. A failed allocation is a
            # terminal outcome and is recorded as one — `rejected` is the action the installed glass renders as ✗
            # with the reason; the reason says the file was NOT moved (unlike a quarantine). A file that vanished
            # between the check and the move was handled by the other path (the sweep vs the observer) and is not
            # a failure — exactly-once, said in the log, no record.
            if not file_path.exists():
                logger.info("%s is gone — allocated by another path, no record", file_path)
                return
            category = file_path.parent.name
            self.status.record(
                "rejected",
                file_path.name,
                category,
                reason=f"allocation failed: {type(exc).__name__}: {str(exc)[:160]} (file left in inbox/{category})",
            )

    def _allocate(self, file_path: Path):
        """Move one inbox file to its rule-chosen folder, or quarantine/skip it; record the outcome.

        Reads rules.toml fresh each call, creates the destination folder, moves the file and
        appends to status.json. Returns nothing; may raise (caught by _handle).
        """
        if not file_path.exists():
            return
        # Quarantine lives outside the watched inbox tree (root/quarantine), so the observer
        # never fires for quarantined files -- but keep the guard for direct calls and as
        # defense-in-depth against the old re-processing loop.
        if self.paths.quarantine in file_path.parents:
            return
        # Dot-prefixed files are in-progress temp files (the transport streams to
        # `.part-<name>` then renames; rsync's `.name.XXXXXX` in its era); the rename into
        # place arrives separately as on_moved.
        if file_path.name.startswith("."):
            return

        # The category is the name of the inbox subfolder the file landed in.
        rules = RuleSet.load(self.rules_path)
        category = file_path.parent.name
        size_mb = file_path.stat().st_size / (1024 * 1024)

        # Over the size limit: quarantine instead of allocating.
        if size_mb > rules.defaults.max_file_size_mb:
            self._quarantine(file_path, category, f"exceeds max_file_size_mb ({size_mb:.1f}MB)")
            return

        # Pick the destination folder from the rules, apply the collision policy, then move.
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
        """Move file_path into the quarantine folder (renaming on clash) and record a 'rejected' status."""
        # Never overwrite an earlier quarantined file of the same name -- rename like the
        # default collision policy does.
        dest = self._resolve_collision(self.paths.quarantine / file_path.name, "rename")
        shutil.move(str(file_path), str(dest))
        logger.warning("REJECTED %s (%s) -> %s", file_path, reason, dest)
        self.status.record("rejected", file_path.name, category, reason=reason)

    @staticmethod
    def _resolve_collision(dest_path: Path, policy: str) -> Path | None:
        """Return the path to write to given policy 'overwrite', 'skip' or (default) rename.

        Returns dest_path if free or overwriting, None for skip, else 'name (n).ext' for the first free n.
        """
        if not dest_path.exists():
            return dest_path
        if policy == "overwrite":
            return dest_path
        if policy == "skip":
            return None

        # Rename policy: try "name (1).ext", "name (2).ext", ... until one is free.
        stem, suffix = dest_path.stem, dest_path.suffix
        n = 1
        while True:
            candidate = dest_path.with_name(f"{stem} ({n}){suffix}")
            if not candidate.exists():
                return candidate
            n += 1

    # -- helper for the on_created fallback --
    @staticmethod
    def _wait_until_stable(file_path: Path, interval: float = 0.5, timeout: float = 60.0):
        """Block until file_path's size is unchanged across one polling interval.

        Only used on non-inotify platforms (react_to_created). Returns early if the file
        disappears; gives up after `timeout` seconds and lets _allocate see whatever is there.
        """
        # Poll the size; stop when two reads in a row agree, the file is gone, or time runs out.
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


# -- startup helpers --
def sweep_inbox(handler: InboxHandler, paths: Paths) -> int:
    """S157 E54 (B32 U01, Codex's 2026-08-27 audit): files that arrived while the service was down sat in
    inbox/<category>/ until something touched them — run() armed the watch and never looked. Called once at
    startup AFTER the observer is armed, so nothing arriving during the sweep is missed; a file the observer
    allocates first vanishes under the sweep and is not recorded twice (see _handle). Dot-prefixed files are
    in-progress transfers (their rename arrives as on_moved); quarantine/ is outside the inbox by design.
    Returns the number of files handed to the handler."""
    # Walk every category folder, then every plain file in it (skipping dot-files), in name order.
    n = 0
    for category_dir in sorted(p for p in paths.inbox.iterdir() if p.is_dir()):
        for file_path in sorted(p for p in category_dir.iterdir() if p.is_file()):
            if file_path.name.startswith("."):
                continue
            handler._handle(file_path)
            n += 1
    return n


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


# -- the service loop and command-line entry --
def run(root: Path, rules_path: Path):
    """Run the allocator service until Ctrl-C: set up folders and logging, watch the inbox, sweep, heartbeat.

    Creates directories under root, writes logs/allocator.log, starts a watchdog observer thread
    and talks to systemd (READY=1, then WATCHDOG=1 each second while the observer lives).
    """
    paths = Paths.from_root(root)
    paths.ensure_exist()

    # Pre-create inbox/<category>/ for every category in rules.toml. The widget's transport
    # now runs `mkdir -p` itself (transfer.rs), so for IT this is redundant -- it stays as
    # defense for any sender that does not (hand-run scp, the rsync era's tooling), where the
    # first transfer to a fresh category would otherwise fail.
    rules = RuleSet.load(rules_path)
    categories = {rule.category for rule in rules.rules}
    for category in categories:
        (paths.inbox / category).mkdir(parents=True, exist_ok=True)

    # Log to logs/allocator.log and also to the console.
    logging.basicConfig(
        filename=paths.logs / "allocator.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger().addHandler(logging.StreamHandler())

    # Build the handler and arm the recursive watch on the inbox.
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
    # S157 E54 (U01): the backlog that arrived while the service was down, allocated exactly once.
    swept = sweep_inbox(handler, paths)
    logger.info("startup sweep: %d pre-existing file(s) handed to the allocator", swept)

    # READY after the watch is armed -- under Type=notify this line IS the startup contract.
    sd_notify("READY=1")
    # Main loop: sleep one second at a time; Ctrl-C stops the observer and exits cleanly.
    heartbeat = watchdog_armed()
    try:
        while True:
            time.sleep(1)
            # Heartbeat only while the observer thread is alive: a dead watcher inside a
            # living process (SYM-023's failure shape) becomes a watchdog restart instead of
            # a silent wedge. See linux-converter/converter/main.py for the full rationale.
            if heartbeat and observer.is_alive():
                sd_notify("WATCHDOG=1")
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main():
    """Command-line entry: parse --root and --config, then call run()."""
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
