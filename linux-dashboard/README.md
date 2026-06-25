# linux-dashboard

A standalone GTK4 viewer for `~/file-portal/sorted/` — a thumbnail gallery for `photos`, a
browsable list for `documents`/`code`/`archive`/`misc`. Read-only: it never touches `inbox/` or
the allocator's sorting logic. See [`../docs/09-linux-dashboard.md`](../docs/09-linux-dashboard.md)
for the design rationale.

## Install on Arch Linux

```bash
cd linux-dashboard
./scripts/install.sh
```

This installs `gtk4`/`libadwaita`/`python-gobject` via `pacman` (one-time `sudo`, same category as
`tailscale up` itself), creates a venv for the rest of the Python deps, and registers an app-menu
launcher named "File Portal Dashboard".

## Run in the foreground (for development/debugging)

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m dashboard.main
```

`--system-site-packages` is required so `import gi` resolves to the pacman-installed GTK bindings
— pip can't install those reliably on its own.

## Toggling show/hide with a hotkey

The app is single-instance: running `python -m dashboard.main` again while it's already open hides
it if visible, or shows + focuses it if hidden. Bind a keyboard shortcut to that same command in
XFCE's *Settings > Keyboard > Application Shortcuts* to get a global toggle hotkey.

"Always on top" and "show on all workspaces" are left to xfwm4's own window properties (right-click
the titlebar) rather than duplicated in-app.

## Settings

Window size, refresh interval, category filters, and the photo date range live in
`~/.config/file-portal/dashboard.toml`, editable from the gear menu in the app's header bar or by
hand (re-read on next launch / next settings change, no restart required for in-app edits).

## Uninstalling

```bash
rm ~/.local/share/applications/file-portal-dashboard.desktop
rm -rf ~/file-portal-src/linux-dashboard/.venv
```
