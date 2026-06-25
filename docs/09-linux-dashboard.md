# 09 — Linux Dashboard

Lives in [`linux-dashboard/`](../linux-dashboard). A small standalone GTK4 + libadwaita app —
read-only, optional, and entirely separate from the transfer path (it never touches `inbox/` or
the allocator). It exists to answer "what actually landed in `sorted/`?" without opening a file
manager and knowing the date-bucketed photo path scheme by heart.

## What it looks like

```
┌──────────────────────────────────────────────────────┐
│ [⟳]                                          [⚙]      │  <- header bar: refresh, settings
├───────────┬────────────────────────────────────────────┤
│ Photos    │  ┌────┐ ┌────┐ ┌────┐ ┌────┐                │
│ Documents │  │ img│ │ img│ │ img│ │ img│   (thumbnail   │
│ Code      │  └────┘ └────┘ └────┘ └────┘    grid, for   │
│ Archive   │  ┌────┐ ┌────┐                  "Photos")   │
│ Misc      │  │ img│ │ img│                              │
└───────────┴────────────────────────────────────────────┘
```

Selecting a non-photo category swaps the content area for a sortable list (name / folder /
modified) instead of the thumbnail grid.

## What it does

1. Walks `~/file-portal/sorted/<category>/...` on startup and whenever asked to refresh —
   `dashboard/scanner.py` understands that only `photos` has `{yyyy}/{mm}` date-bucketed
   subfolders per [`05-allocation-rules.md`](05-allocation-rules.md); every other category is
   scanned flat.
2. Watches `sorted/` recursively with `watchdog` (the same library `linux-receiver` already uses)
   so new files the allocator drops in appear within ~300ms, debounced, with no restart needed.
   `dashboard/config.py`'s `refresh_interval_seconds` also drives a periodic full rescan as a
   fallback.
3. Renders photos as a thumbnail grid (`Gtk.GridView`, thumbnails via `GdkPixbuf` — no extra
   image-processing dependency) and everything else as a flat sortable list
   (`Gtk.ColumnView`), opened via `Gio.AppInfo.launch_default_for_uri` (whatever the user's
   default app for that file type is).
4. Persists window size, refresh interval, category filter, and the photo date range to
   `~/.config/file-portal/dashboard.toml`.

## Why GTK4 over GTK3, and why no Pillow

GTK3 + PyGObject were already installed on this machine; GTK4 + libadwaita were not. The user
chose GTK4 anyway for the modern widget set (`Gtk.GridView`) and accepted the one-time
`sudo pacman -S gtk4 libadwaita` cost — see [`scripts/install.sh`](../linux-dashboard/scripts/install.sh).
Thumbnailing uses `GdkPixbuf.Pixbuf.new_from_file_at_scale`, which ships with GTK itself, so Pillow
was never added as a dependency.

## "Toggle/dock" without eww/Waybar

This machine runs XFCE/xfwm4, not a tiling WM with eww/Waybar, so there's no panel to embed a
widget into. Instead the app is single-instance (`Adw.Application`'s default DBus activation):
launching it again while it's already open hides it if visible, or shows + focuses it if hidden.
Bind a keyboard shortcut to the launch command in XFCE's *Keyboard > Application Shortcuts* to get
a global show/hide hotkey. "Always on top" / "keep on all workspaces" are deliberately **not**
implemented in-app — GTK4 dropped the portable keep-above API, and xfwm4 already exposes both via
the titlebar's right-click window properties, so duplicating that would just fight the WM.

## Key files

| File | Purpose |
|------|---------|
| `dashboard/main.py` | Entry point — `Adw.Application` with single-instance toggle logic. |
| `dashboard/config.py` | `Paths` (the `sorted/` root) and `Settings` (load/save `dashboard.toml`). |
| `dashboard/scanner.py` | Walks `sorted/` into an in-memory model; date-aware for `photos`. |
| `dashboard/watcher.py` | `watchdog` Observer on `sorted/`, debounced, marshalled onto the GTK main loop via `GLib.idle_add`/`timeout_add`. |
| `dashboard/window.py` | The main window: sidebar, header bar, content area. |
| `dashboard/widgets/photo_grid.py` | Thumbnail grid + in-memory LRU thumbnail cache. |
| `dashboard/widgets/file_tree.py` | Sortable list for non-photo categories. |
| `dashboard/widgets/settings_popover.py` | Window size / refresh interval / category filter / date range controls. |
| `scripts/install.sh` | `pacman` deps, venv (`--system-site-packages`), app-menu launcher. |

## Configuration

`~/.config/file-portal/dashboard.toml`, written whenever a setting changes or the window is
resized/closed, read on next launch:

```toml
window_width = 1000
window_height = 700
refresh_interval_seconds = 30
enabled_categories = ["photos", "documents", "code", "archive", "misc"]
photo_date_from = ""   # "yyyy-mm", empty = no lower bound
photo_date_to = ""     # "yyyy-mm", empty = no upper bound
```

## Next

[`08-roadmap.md`](08-roadmap.md) — where this fits relative to the rest of the project.
