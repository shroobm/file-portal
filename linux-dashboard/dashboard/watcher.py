"""WHAT THIS FILE DOES: SortedTreeWatcher watches a folder tree for any file event (using the
watchdog library) and calls a supplied on_change callback on the GTK main loop, at most once per
burst. It only reads filesystem events; it writes nothing. Callers are the dashboard window code.

Watches sorted/ for changes and notifies the GTK main loop.

watchdog fires callbacks on its own observer thread, so every callback here just schedules the
real refresh via GLib.idle_add instead of touching widgets directly. Bursts of events (e.g. a big
batch the allocator just sorted) are debounced into a single refresh.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from gi.repository import GLib
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# -- quiet period (milliseconds) that ends an event burst --
DEBOUNCE_MS = 300


# -- the watcher the window uses --
class SortedTreeWatcher:
    """Recursive watcher on a folder that fires on_change once after a burst of events settles."""

    def __init__(self, sorted_root: Path, on_change: Callable[[], None]) -> None:
        """Register a recursive watch on sorted_root; on_change is the callback to fire.

        The observer thread is created here but not started (see start()).
        """
        self._on_change = on_change
        self._debounce_source_id: int | None = None
        self._observer = Observer()
        handler = _DebouncedHandler(self._schedule_refresh)
        self._observer.schedule(handler, str(sorted_root), recursive=True)

    # -- lifecycle --
    def start(self) -> None:
        """Start the background watchdog observer thread."""
        self._observer.start()

    def stop(self) -> None:
        """Stop the observer thread and wait up to 2 seconds for it to finish."""
        self._observer.stop()
        self._observer.join(timeout=2)

    # -- debounce internals (run via the GLib main loop) --
    def _schedule_refresh(self) -> None:
        """(Re)start the debounce timer: cancel any pending one, then schedule _fire_refresh."""
        if self._debounce_source_id is not None:
            GLib.source_remove(self._debounce_source_id)
        self._debounce_source_id = GLib.timeout_add(DEBOUNCE_MS, self._fire_refresh)

    def _fire_refresh(self) -> bool:
        """Timer callback: clear the pending-timer id and call on_change. Returns False (run once)."""
        self._debounce_source_id = None
        self._on_change()
        return False  # one-shot


# -- watchdog event handler --
class _DebouncedHandler(FileSystemEventHandler):
    """Watchdog handler that reports every filesystem event by calling schedule_refresh."""

    def __init__(self, schedule_refresh: Callable[[], None]) -> None:
        """Keep the callback to invoke on each event."""
        self._schedule_refresh = schedule_refresh

    def on_any_event(self, event) -> None:
        """Called by watchdog on its own thread for any event; the event itself is ignored."""
        self._schedule_refresh()
