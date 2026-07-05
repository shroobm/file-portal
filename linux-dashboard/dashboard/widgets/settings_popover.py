"""Popover for the adjustable bits the user asked for: window size, refresh interval,
category filter, photo date range, and "stay on top"."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from dashboard.config import ALL_CATEGORIES, Settings

CATEGORY_LABELS = {
    "photos": "Photos",
    "documents": "Documents",
    "code": "Code",
    "archive": "Archive",
    "misc": "Misc",
}


class SettingsPopover(Gtk.Popover):
    def __init__(self, settings: Settings, on_change: Callable[[], None]) -> None:
        super().__init__()
        self._settings = settings
        self._on_change = on_change

        grid = Gtk.Grid(
            row_spacing=8,
            column_spacing=12,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        row = 0

        grid.attach(Gtk.Label(label="Window size", xalign=0), 0, row, 1, 1)
        size_box = Gtk.Box(spacing=4)
        self._width_spin = Gtk.SpinButton.new_with_range(400, 4000, 50)
        self._width_spin.set_value(settings.window_width)
        self._height_spin = Gtk.SpinButton.new_with_range(300, 4000, 50)
        self._height_spin.set_value(settings.window_height)
        self._width_spin.connect("value-changed", self._on_size_changed)
        self._height_spin.connect("value-changed", self._on_size_changed)
        size_box.append(self._width_spin)
        size_box.append(Gtk.Label(label="x"))
        size_box.append(self._height_spin)
        grid.attach(size_box, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label="Refresh interval (s)", xalign=0), 0, row, 1, 1)
        self._interval_spin = Gtk.SpinButton.new_with_range(5, 3600, 5)
        self._interval_spin.set_value(settings.refresh_interval_seconds)
        self._interval_spin.connect("value-changed", self._on_interval_changed)
        grid.attach(self._interval_spin, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label="Categories", xalign=0, valign=Gtk.Align.START), 0, row, 1, 1)
        category_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._category_checks: dict[str, Gtk.CheckButton] = {}
        for category in ALL_CATEGORIES:
            check = Gtk.CheckButton(label=CATEGORY_LABELS[category])
            check.set_active(category in settings.enabled_categories)
            check.connect("toggled", self._on_category_toggled, category)
            category_box.append(check)
            self._category_checks[category] = check
        grid.attach(category_box, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label="Photos from (yyyy-mm)", xalign=0), 0, row, 1, 1)
        self._date_from_entry = Gtk.Entry(text=settings.photo_date_from, placeholder_text="any")
        self._date_from_entry.connect("changed", self._on_date_from_changed)
        grid.attach(self._date_from_entry, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label="Photos to (yyyy-mm)", xalign=0), 0, row, 1, 1)
        self._date_to_entry = Gtk.Entry(text=settings.photo_date_to, placeholder_text="any")
        self._date_to_entry.connect("changed", self._on_date_to_changed)
        grid.attach(self._date_to_entry, 1, row, 1, 1)

        self.set_child(grid)

    def _on_size_changed(self, _widget) -> None:
        self._settings.window_width = int(self._width_spin.get_value())
        self._settings.window_height = int(self._height_spin.get_value())
        self._on_change()

    def _on_interval_changed(self, _widget) -> None:
        self._settings.refresh_interval_seconds = int(self._interval_spin.get_value())
        self._on_change()

    def _on_category_toggled(self, _widget, category: str) -> None:
        enabled = {c for c, check in self._category_checks.items() if check.get_active()}
        self._settings.enabled_categories = [c for c in ALL_CATEGORIES if c in enabled]
        self._on_change()

    def _on_date_from_changed(self, entry: Gtk.Entry) -> None:
        self._settings.photo_date_from = entry.get_text().strip()
        self._on_change()

    def _on_date_to_changed(self, entry: Gtk.Entry) -> None:
        self._settings.photo_date_to = entry.get_text().strip()
        self._on_change()
