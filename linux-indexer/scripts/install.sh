#!/usr/bin/env bash
# Installs the indexer as a systemd --user oneshot + timer, and the vault's post-update hook.
# Never run with sudo: everything here operates on the current user's own home directory and
# user-level systemd instance.
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
# Substitute the real clone path into the units (they ship with __WORKDIR__/__EXEC_PATH__
# placeholders) -- same approach as linux-converter/scripts/install.sh, for BOTH units so a
# fresh machine gets the timer too (the fixity pair was hand-installed: OPEN-TASKS U03).
for unit in file-portal-indexer.service file-portal-indexer.timer; do
  sed "s|__WORKDIR__|$(pwd)|; s|__EXEC_PATH__|$(pwd)/.venv/bin/python|" \
    "systemd/$unit" > "$HOME/.config/systemd/user/$unit"
done

systemctl --user daemon-reload
systemctl --user enable --now file-portal-indexer.timer

# The hook that makes every push reconcile promptly. Never overwrites an existing hook: the
# vault repo was initialised by hand (Decision #4) and a hook someone else wrote is theirs.
HOOK="$HOME/file-portal/vault.git/hooks/post-update"   # the unit indexes DEFAULT_ROOT; so does the hook
if [ -e "$HOOK" ]; then
  echo "Hook already present, left untouched: $HOOK"
else
  install -m 0755 scripts/post-update.hook "$HOOK"
  echo "Installed hook: $HOOK"
fi

echo "Installed. First reconcile: systemctl --user start file-portal-indexer.service"
echo "Check status with: .venv/bin/python -m indexer.status"
echo "Tail logs with: journalctl --user -u file-portal-indexer -f  (or logs/indexer.log)"
