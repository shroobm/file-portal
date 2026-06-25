"""Main window: sidebar of categories, a refresh/settings header bar, and a content area that
swaps between the photo grid and the file list depending on which category is selected."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from dashboard.config import ALL_CATEGORIES, Paths, Settings
from dashboard.scanner import scan
from dashboard.watcher import SortedTreeWatcher
from dashboard.widgets.file_tree import FileTree
from dashboard.widgets.photo_grid import PhotoGrid
from dashboard.widgets.settings_popover import CATEGORY_LABELS, SettingsPopover

REFRESH_TIMER_NAME = "refresh-timer"


class DashboardWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, paths: Paths, settings: Settings) -> None:
        super().__init__(application=app)
        self._paths = paths
        self._settings = settings
        self._refresh_timeout_id: int | None = None
        self._current_category = settings.enabled_categories[0] if settings.enabled_categories else "photos"

        self.set_title("File Portal Dashboard")
        self.set_default_size(settings.window_width, settings.window_height)
        self.connect("notify::default-width", self._on_window_resized)
        self.connect("notify::default-height", self._on_window_resized)
        self.connect("close-request", self._on_close_request)

        self._build_ui()
        self._refresh()
        self._start_refresh_timer()

        self._watcher = SortedTreeWatcher(paths.sorted, on_change=self._refresh)
        self._watcher.start()

    def _build_ui(self) -> None:
        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()

        refresh_button = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Refresh now")
        refresh_button.connect("clicked", lambda _b: self._refresh())
        header.pack_start(refresh_button)

        settings_button = Gtk.MenuButton(icon_name="emblem-system-symbolic", tooltip_text="Settings")
        self._settings_popover = SettingsPopover(self._settings, on_change=self._on_settings_changed)
        settings_button.set_popover(self._settings_popover)
        header.pack_end(settings_button)

        toolbar_view.add_top_bar(header)

        split_view = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self._sidebar = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self._sidebar.set_size_request(160, -1)
        self._sidebar.connect("row-selected", self._on_sidebar_row_selected)
        for category in ALL_CATEGORIES:
            row = Gtk.ListBoxRow()
            row.category = category
            row.set_child(Gtk.Label(label=CATEGORY_LABELS[category], xalign=0, margin_top=8,
                                     margin_bottom=8, margin_start=10, margin_end=10))
            self._sidebar.append(row)

        split_view.append(self._sidebar)
        split_view.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        self._photo_grid = PhotoGrid()
        self._file_tree = FileTree()
        self._content_stack = Gtk.Stack()
        self._content_stack.add_named(self._photo_grid, "photos")
        self._content_stack.add_named(self._file_tree, "files")
        self._content_stack.set_hexpand(True)
        self._content_stack.set_vexpand(True)
        split_view.append(self._content_stack)

        toolbar_view.set_content(split_view)
        self.set_content(toolbar_view)

        for row in self._sidebar:
            if row.category == self._current_category:
                self._sidebar.select_row(row)
                break

    def _on_sidebar_row_selected(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row is None:
            return
        self._current_category = row.category
        self._render_current_category()

    def _refresh(self) -> None:
        self._scanned = scan(self._paths, self._settings)
        self._render_current_category()

    def _render_current_category(self) -> None:
        if not hasattr(self, "_scanned"):
            return
        entries = self._scanned.get(self._current_category, [])
        if self._current_category == "photos":
            self._photo_grid.set_entries(entries)
            self._content_stack.set_visible_child_name("photos")
        else:
            self._file_tree.set_entries(entries, self._paths.sorted / self._current_category)
            self._content_stack.set_visible_child_name("files")

    def _on_settings_changed(self) -> None:
        self._settings.save()
        self._start_refresh_timer()
        self._refresh()

    def _start_refresh_timer(self) -> None:
        if self._refresh_timeout_id is not None:
            GLib.source_remove(self._refresh_timeout_id)
        self._refresh_timeout_id = GLib.timeout_add_seconds(
            self._settings.refresh_interval_seconds, self._on_refresh_timer
        )

    def _on_refresh_timer(self) -> bool:
        self._refresh()
        return True  # keep repeating

    def _on_window_resized(self, *_args) -> None:
        width = self.get_width()
        height = self.get_height()
        if width > 0 and height > 0:
            self._settings.window_width = width
            self._settings.window_height = height

    def _on_close_request(self, *_args) -> bool:
        self._settings.save()
        self._watcher.stop()
        return False  # allow close to proceed
