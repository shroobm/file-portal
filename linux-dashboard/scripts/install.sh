#!/usr/bin/env bash
# Installs the dashboard's system packages, a venv for its Python deps, and an app-menu launcher.
# Never run with sudo as a whole -- only the pacman step needs it, same category as `tailscale up`.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ "$(id -u)" -eq 0 ]; then
  echo "Do not run this script as root/with sudo -- it will ask for sudo itself when needed." >&2
  exit 1
fi

sudo pacman -S --needed gtk4 libadwaita python-gobject gobject-introspection

# --system-site-packages so `import gi` resolves to the pacman-installed PyGObject bindings;
# pip cannot install GTK bindings reliably on its own.
python3 -m venv --system-site-packages .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

mkdir -p "$HOME/.local/share/applications"
DESKTOP_SRC="scripts/file-portal-dashboard.desktop"
DESKTOP_DST="$HOME/.local/share/applications/file-portal-dashboard.desktop"
sed "s|__EXEC_PATH__|$(pwd)/.venv/bin/python -m dashboard.main|; s|__WORKDIR__|$(pwd)|" \
  "$DESKTOP_SRC" > "$DESKTOP_DST"
chmod +x "$DESKTOP_DST"

echo "Installed. Launch from your app menu as 'File Portal Dashboard', or run directly:"
echo "  cd $(pwd) && .venv/bin/python -m dashboard.main"
echo ""
echo "To toggle show/hide from a keyboard shortcut, bind a key in XFCE's Keyboard settings to:"
echo "  $(pwd)/.venv/bin/python -m dashboard.main"
