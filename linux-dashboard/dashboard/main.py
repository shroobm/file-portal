"""Entry point. Single-instance GtkApplication: a second launch toggles the existing window
(hide if visible, present+focus if hidden) instead of opening a duplicate."""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio

from dashboard.config import CONFIG_PATH, DEFAULT_ROOT, Paths, Settings
from dashboard.window import DashboardWindow

APPLICATION_ID = "com.shroobm.fileportal.Dashboard"


class DashboardApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APPLICATION_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self._window: DashboardWindow | None = None

    def do_activate(self) -> None:
        if self._window is None:
            paths = Paths.from_root(DEFAULT_ROOT)
            settings = Settings.load(CONFIG_PATH)
            self._window = DashboardWindow(self, paths, settings)
            self._window.present()
            return

        if self._window.is_visible():
            self._window.set_visible(False)
        else:
            self._window.present()


def main() -> int:
    app = DashboardApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
