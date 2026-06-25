"""Thumbnail grid for the photos category, backed by Gtk.GridView."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GObject, Gtk

from dashboard.scanner import Entry

THUMB_SIZE = 160
_CACHE_MAX = 256


class PhotoItem(GObject.Object):
    def __init__(self, entry: Entry) -> None:
        super().__init__()
        self.entry = entry


class ThumbnailCache:
    """Tiny in-memory LRU keyed by (path, mtime) so edits/replacements invalidate naturally."""

    def __init__(self, max_size: int = _CACHE_MAX) -> None:
        self._max_size = max_size
        self._store: OrderedDict[tuple[str, float], Gdk.Texture] = OrderedDict()

    def get(self, path: Path, mtime: float) -> Gdk.Texture | None:
        key = (str(path), mtime)
        texture = self._store.get(key)
        if texture is not None:
            self._store.move_to_end(key)
        return texture

    def put(self, path: Path, mtime: float, texture: Gdk.Texture) -> None:
        key = (str(path), mtime)
        self._store[key] = texture
        self._store.move_to_end(key)
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)


class PhotoGrid(Gtk.ScrolledWindow):
    def __init__(self) -> None:
        super().__init__()
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self._cache = ThumbnailCache()
        self._store = Gio.ListStore(item_type=PhotoItem)
        selection = Gtk.NoSelection(model=self._store)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_setup)
        factory.connect("bind", self._on_bind)

        self._grid_view = Gtk.GridView(model=selection, factory=factory)
        self._grid_view.set_min_columns(2)
        self._grid_view.set_max_columns(8)
        self.set_child(self._grid_view)

    def set_entries(self, entries: list[Entry]) -> None:
        self._store.remove_all()
        for entry in entries:
            self._store.append(PhotoItem(entry))

    def _on_setup(self, _factory, list_item: Gtk.ListItem) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)
        picture = Gtk.Picture()
        picture.set_size_request(THUMB_SIZE, THUMB_SIZE)
        picture.set_content_fit(Gtk.ContentFit.COVER)
        label = Gtk.Label(ellipsize=3, max_width_chars=18)  # 3 == Pango.EllipsizeMode.END
        box.append(picture)
        box.append(label)
        list_item.set_child(box)

    def _on_bind(self, _factory, list_item: Gtk.ListItem) -> None:
        item: PhotoItem = list_item.get_item()
        box = list_item.get_child()
        picture: Gtk.Picture = box.get_first_child()
        label: Gtk.Label = box.get_last_child()

        entry = item.entry
        label.set_label(entry.path.name)

        texture = self._cache.get(entry.path, entry.mtime)
        if texture is None:
            texture = self._load_thumbnail(entry.path)
            if texture is not None:
                self._cache.put(entry.path, entry.mtime, texture)
        if texture is not None:
            picture.set_paintable(texture)

    @staticmethod
    def _load_thumbnail(path: Path) -> Gdk.Texture | None:
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(path), THUMB_SIZE, THUMB_SIZE, preserve_aspect_ratio=True
            )
        except GObject.GError:
            return None
        return Gdk.Texture.new_for_pixbuf(pixbuf)
