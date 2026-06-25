"""Watches sorted/ for changes and notifies the GTK main loop.

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

DEBOUNCE_MS = 300


class SortedTreeWatcher:
    def __init__(self, sorted_root: Path, on_change: Callable[[], None]) -> None:
        self._on_change = on_change
        self._debounce_source_id: int | None = None
        self._observer = Observer()
        handler = _DebouncedHandler(self._schedule_refresh)
        self._observer.schedule(handler, str(sorted_root), recursive=True)

    def start(self) -> None:
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join(timeout=2)

    def _schedule_refresh(self) -> None:
        if self._debounce_source_id is not None:
            GLib.source_remove(self._debounce_source_id)
        self._debounce_source_id = GLib.timeout_add(DEBOUNCE_MS, self._fire_refresh)

    def _fire_refresh(self) -> bool:
        self._debounce_source_id = None
        self._on_change()
        return False  # one-shot


class _DebouncedHandler(FileSystemEventHandler):
    def __init__(self, schedule_refresh: Callable[[], None]) -> None:
        self._schedule_refresh = schedule_refresh

    def on_any_event(self, event) -> None:
        self._schedule_refresh()
