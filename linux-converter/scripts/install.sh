#!/usr/bin/env bash
# Installs the converter as a systemd --user service. Never run with sudo: everything here
# operates on the current user's own home directory and user-level systemd instance.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ "$(id -u)" -eq 0 ]; then
  echo "Do not run this as root/with sudo -- see docs/06-security-model.md" >&2
  exit 1
fi

python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

mkdir -p "$HOME/.config/systemd/user"
# Substitute the real clone path into the unit (the unit ships with __WORKDIR__/__EXEC_PATH__
# placeholders) -- same approach as linux-dashboard/scripts/install.sh.
SERVICE_SRC="systemd/file-portal-converter.service"
SERVICE_DST="$HOME/.config/systemd/user/file-portal-converter.service"
sed "s|__WORKDIR__|$(pwd)|; s|__EXEC_PATH__|$(pwd)/.venv/bin/python|" \
  "$SERVICE_SRC" > "$SERVICE_DST"

# S157 E51 (B32 U03, Codex's 2026-08-27 completion audit, probed at HEAD): the vault-fixity service and timer
# shipped in systemd/ with the same __WORKDIR__/__EXEC_PATH__ placeholders — and their own comment said this
# script substituted them — while this script installed only the converter, so a fresh machine had no weekly
# fixity check unless someone hand-installed the units. The service is templated like the converter's; the
# timer carries no placeholder and is copied as is; the TIMER is what gets enabled (the service is its oneshot).
FIXITY_SRC="systemd/file-portal-vault-fixity.service"
FIXITY_DST="$HOME/.config/systemd/user/file-portal-vault-fixity.service"
sed "s|__WORKDIR__|$(pwd)|; s|__EXEC_PATH__|$(pwd)/.venv/bin/python|" \
  "$FIXITY_SRC" > "$FIXITY_DST"
cp "systemd/file-portal-vault-fixity.timer" "$HOME/.config/systemd/user/file-portal-vault-fixity.timer"

systemctl --user daemon-reload
systemctl --user enable --now file-portal-converter
systemctl --user enable --now file-portal-vault-fixity.timer

echo "Installed. Check status with: systemctl --user status file-portal-converter"
echo "Tail logs with: journalctl --user -u file-portal-converter -f"
echo "Weekly vault fixity: systemctl --user list-timers file-portal-vault-fixity.timer"
