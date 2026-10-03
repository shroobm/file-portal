"""WHAT THIS FILE DOES: program entry point. main() creates the DashboardApplication and runs it;
on first activation it loads Settings from dashboard.toml (via config), builds Paths from the
default root and opens a DashboardWindow. Reads the config file; writes nothing itself.

Entry point. Single-instance GtkApplication: a second launch toggles the existing window
(hide if visible, present+focus if hidden) instead of opening a duplicate."""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio

from dashboard.config import CONFIG_PATH, DEFAULT_ROOT, Paths, Settings
from dashboard.window import DashboardWindow

# -- application identity (the single-instance key) --
APPLICATION_ID = "com.shroobm.fileportal.Dashboard"


# -- the GTK application --
class DashboardApplication(Adw.Application):
    """Single-instance Adwaita application that owns the one DashboardWindow."""

    def __init__(self) -> None:
        """Register with APPLICATION_ID and start with no window yet."""
        super().__init__(application_id=APPLICATION_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self._window: DashboardWindow | None = None

    def do_activate(self) -> None:
        """Run on every launch. First time: create and show the window. Later: toggle visibility."""
        # First launch: load settings from disk and open the window.
        if self._window is None:
            paths = Paths.from_root(DEFAULT_ROOT)
            settings = Settings.load(CONFIG_PATH)
            self._window = DashboardWindow(self, paths, settings)
            self._window.present()
            return

        # Later launches: hide the window if it is showing, otherwise bring it to the front.
        if self._window.is_visible():
            self._window.set_visible(False)
        else:
            self._window.present()


# -- program start --
def main() -> int:
    """Create the application, run it with the command-line arguments, return its exit status."""
    app = DashboardApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
