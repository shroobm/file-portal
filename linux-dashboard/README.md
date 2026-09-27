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

## Serving sorted/ to the tailnet (opt-in, loopback only) — S214 E16

`python -m dashboard.serve` is the sorted browse without the GTK window: it binds `127.0.0.1:<serve_port>`
(8766 by default, `serve_port` in dashboard.toml, `--port N` overrides) and nothing else, opens no other
port, and no unit ships for it. Reach it through `tailscale serve` — the pattern docs/06 names for a new
surface:

```bash
python -m dashboard.serve                                    # foreground
tailscale serve --bg --set-path /sorted http://127.0.0.1:8766   # tailnet-only, identity-bound
```

Routes (GET, read-only): `/health`; `/sorted?category=&from=&to=` — the same `scan()` model the window
renders, as JSON, paths relative to `sorted/`; `/thumb?path=&px=` — a small JPEG of one photo under
`sorted/photos` (GdkPixbuf, else Pillow, else an honest 501). Its own auth is `~/file-portal/serve.token`,
shared with the indexer's endpoint: when the file exists every route but `/health` wants `X-FP-Token`.
Nothing here opens, moves or writes a file. Tests: `pytest tests/` (hermetic; no GTK).

## Uninstalling

```bash
rm ~/.local/share/applications/file-portal-dashboard.desktop
rm -rf ~/file-portal-src/linux-dashboard/.venv
```
