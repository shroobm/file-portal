"""WHAT THIS FILE DOES: defines SettingsPopover, a GTK4 popover holding the dashboard's controls.
Each control writes straight into the shared Settings object and then calls the on_change callback
the caller supplied. It reads Settings and ALL_CATEGORIES from dashboard.config; it writes no file
itself (saving is the caller's job). Presumably created by the dashboard window (not shown here).

Popover for the adjustable bits the user asked for: window size, refresh interval,
category filter, photo date range, and "stay on top"."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from dashboard.config import ALL_CATEGORIES, Settings

# -- display names for the category keys (key = folder name under sorted/) --
CATEGORY_LABELS = {
    "photos": "Photos",
    "documents": "Documents",
    "code": "Code",
    "archive": "Archive",
    "misc": "Misc",
}


# -- the popover widget --
class SettingsPopover(Gtk.Popover):
    """Popover with window size, refresh interval, category checkboxes and photo date range."""

    def __init__(self, settings: Settings, on_change: Callable[[], None]) -> None:
        """Build the control grid. Inputs: the shared Settings object (mutated by the handlers) and
        an on_change callback fired after every edit. Returns nothing; sets the popover's child."""
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

        # Row: window width x height spin buttons
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

        # Row: refresh interval in seconds
        grid.attach(Gtk.Label(label="Refresh interval (s)", xalign=0), 0, row, 1, 1)
        self._interval_spin = Gtk.SpinButton.new_with_range(5, 3600, 5)
        self._interval_spin.set_value(settings.refresh_interval_seconds)
        self._interval_spin.connect("value-changed", self._on_interval_changed)
        grid.attach(self._interval_spin, 1, row, 1, 1)
        row += 1

        # Row: one checkbox per category, ticked when the category is in enabled_categories
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

        # Row: photo date range lower bound (text entry, yyyy-mm; empty = any)
        grid.attach(Gtk.Label(label="Photos from (yyyy-mm)", xalign=0), 0, row, 1, 1)
        self._date_from_entry = Gtk.Entry(text=settings.photo_date_from, placeholder_text="any")
        self._date_from_entry.connect("changed", self._on_date_from_changed)
        grid.attach(self._date_from_entry, 1, row, 1, 1)
        row += 1

        # Row: photo date range upper bound (text entry, yyyy-mm; empty = any)
        grid.attach(Gtk.Label(label="Photos to (yyyy-mm)", xalign=0), 0, row, 1, 1)
        self._date_to_entry = Gtk.Entry(text=settings.photo_date_to, placeholder_text="any")
        self._date_to_entry.connect("changed", self._on_date_to_changed)
        grid.attach(self._date_to_entry, 1, row, 1, 1)

        self.set_child(grid)

    # -- change handlers: copy the control's value into Settings, then notify the caller --
    def _on_size_changed(self, _widget) -> None:
        """Store both spin-button values as window_width/window_height, then call on_change."""
        self._settings.window_width = int(self._width_spin.get_value())
        self._settings.window_height = int(self._height_spin.get_value())
        self._on_change()

    def _on_interval_changed(self, _widget) -> None:
        """Store the spin-button value as refresh_interval_seconds, then call on_change."""
        self._settings.refresh_interval_seconds = int(self._interval_spin.get_value())
        self._on_change()

    def _on_category_toggled(self, _widget, category: str) -> None:
        """Rebuild enabled_categories from all checkboxes (in ALL_CATEGORIES order), call on_change."""
        enabled = {c for c, check in self._category_checks.items() if check.get_active()}
        self._settings.enabled_categories = [c for c in ALL_CATEGORIES if c in enabled]
        self._on_change()

    def _on_date_from_changed(self, entry: Gtk.Entry) -> None:
        """Store the stripped entry text as photo_date_from, then call on_change."""
        self._settings.photo_date_from = entry.get_text().strip()
        self._on_change()

    def _on_date_to_changed(self, entry: Gtk.Entry) -> None:
        """Store the stripped entry text as photo_date_to, then call on_change."""
        self._settings.photo_date_to = entry.get_text().strip()
        self._on_change()
