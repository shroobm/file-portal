"""Browsable list for non-photo categories (documents/code/archive/misc).

A flat sortable list rather than a literal Gtk.TreeView tree: per docs/05-allocation-rules.md,
only "photos" gets date-bucketed subfolders, so a flat list with a "relative path" column already
shows any incidental subfolders (e.g. sorted/code/archives/ vs sorted/code/inbox/) without needing
real tree-expansion UI.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GObject, Gtk

from dashboard.scanner import Entry


class FileItem(GObject.Object):
    def __init__(self, entry: Entry, category_root: Path) -> None:
        super().__init__()
        self.entry = entry
        self.category_root = category_root

    @property
    def name(self) -> str:
        return self.entry.path.name

    @property
    def relative_dir(self) -> str:
        return str(self.entry.path.relative_to(self.category_root).parent)

    @property
    def modified(self) -> str:
        return datetime.datetime.fromtimestamp(self.entry.mtime).strftime("%Y-%m-%d %H:%M")


class FileTree(Gtk.ScrolledWindow):
    def __init__(self) -> None:
        super().__init__()
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self._store = Gio.ListStore(item_type=FileItem)
        self._selection = Gtk.SingleSelection(model=self._store)

        self._column_view = Gtk.ColumnView(model=self._selection)
        self._column_view.append_column(
            self._make_column("Name", lambda item: item.name, expand=True)
        )
        self._column_view.append_column(self._make_column("Folder", lambda item: item.relative_dir))
        self._column_view.append_column(self._make_column("Modified", lambda item: item.modified))
        self._column_view.connect("activate", self._on_activate)

        self.set_child(self._column_view)

    def set_entries(self, entries: list[Entry], category_root: Path) -> None:
        self._store.remove_all()
        for entry in entries:
            self._store.append(FileItem(entry, category_root))

    def _make_column(self, title: str, getter, expand: bool = False) -> Gtk.ColumnViewColumn:
        factory = Gtk.SignalListItemFactory()

        def on_setup(_factory, list_item: Gtk.ListItem) -> None:
            list_item.set_child(Gtk.Label(xalign=0))

        def on_bind(_factory, list_item: Gtk.ListItem) -> None:
            label: Gtk.Label = list_item.get_child()
            label.set_label(getter(list_item.get_item()))

        factory.connect("setup", on_setup)
        factory.connect("bind", on_bind)
        column = Gtk.ColumnViewColumn(title=title, factory=factory)
        column.set_expand(expand)
        return column

    def _on_activate(self, _column_view: Gtk.ColumnView, position: int) -> None:
        item: FileItem = self._store.get_item(position)
        uri = item.entry.path.resolve().as_uri()
        Gio.AppInfo.launch_default_for_uri(uri, None)
