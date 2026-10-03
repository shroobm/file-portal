"""WHAT THIS FILE DOES: defines FileTree, a scrollable three-column list (Name, Folder, Modified)
of scanner Entry records, and FileItem, the row object that wraps one Entry. set_entries() fills
the list; double-clicking or activating a row opens the file with the desktop's default app.
Reads file paths from scanner.Entry; writes nothing to disk. Callers are the dashboard window code.

Browsable list for non-photo categories (documents/code/archive/misc).

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


# -- row model: one list row wrapping a scanner Entry --
class FileItem(GObject.Object):
    """GObject wrapper for one Entry plus its category root, exposing the three column values."""

    def __init__(self, entry: Entry, category_root: Path) -> None:
        """Keep the Entry and the category folder (used to compute the relative folder)."""
        super().__init__()
        self.entry = entry
        self.category_root = category_root

    @property
    def name(self) -> str:
        """The file's name without its folder."""
        return self.entry.path.name

    @property
    def relative_dir(self) -> str:
        """The file's folder relative to the category root ("." when directly inside it)."""
        return str(self.entry.path.relative_to(self.category_root).parent)

    @property
    def modified(self) -> str:
        """The file's modified time formatted as local "YYYY-MM-DD HH:MM"."""
        return datetime.datetime.fromtimestamp(self.entry.mtime).strftime("%Y-%m-%d %H:%M")


# -- the list widget --
class FileTree(Gtk.ScrolledWindow):
    """Scrollable column view of FileItem rows; activating a row opens that file."""

    def __init__(self) -> None:
        """Create the empty list store, selection model and the Name/Folder/Modified columns."""
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

    # -- public API --
    def set_entries(self, entries: list[Entry], category_root: Path) -> None:
        """Replace all rows with one FileItem per Entry. Clears the list store first."""
        self._store.remove_all()
        for entry in entries:
            self._store.append(FileItem(entry, category_root))

    # -- internals: column construction and row activation --
    def _make_column(self, title: str, getter, expand: bool = False) -> Gtk.ColumnViewColumn:
        """Build a text column. getter maps a FileItem to the string shown; expand stretches it."""
        factory = Gtk.SignalListItemFactory()

        def on_setup(_factory, list_item: Gtk.ListItem) -> None:
            """Create the empty label for a new cell."""
            list_item.set_child(Gtk.Label(xalign=0))

        def on_bind(_factory, list_item: Gtk.ListItem) -> None:
            """Fill the cell's label with getter(item) when a row is bound to it."""
            label: Gtk.Label = list_item.get_child()
            label.set_label(getter(list_item.get_item()))

        factory.connect("setup", on_setup)
        factory.connect("bind", on_bind)
        column = Gtk.ColumnViewColumn(title=title, factory=factory)
        column.set_expand(expand)
        return column

    def _on_activate(self, _column_view: Gtk.ColumnView, position: int) -> None:
        """Open the activated row's file in the default application (launches an external process)."""
        item: FileItem = self._store.get_item(position)
        uri = item.entry.path.resolve().as_uri()
        Gio.AppInfo.launch_default_for_uri(uri, None)
