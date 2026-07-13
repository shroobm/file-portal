#!/usr/bin/env bash
# Bootstraps the linux-receiver allocator on Arch Linux straight from GitHub.
#
# The one `sudo pacman` call below installs system packages -- a one-time admin action, the same
# category as `tailscale up` itself (see docs/06-security-model.md). Everything after that,
# including the actual install.sh, runs as your normal user with no further sudo.
set -euo pipefail

REPO_URL="${FILE_PORTAL_REPO_URL:-https://github.com/shroobm/file-portal.git}"
CLONE_DIR="${FILE_PORTAL_CLONE_DIR:-$HOME/file-portal-src}"

if [ "$(id -u)" -eq 0 ]; then
  echo "Don't run this script itself as root -- it calls sudo only for the one pacman step." >&2
  exit 1
fi

echo "==> Installing system dependencies (git, python, rsync) via pacman..."
sudo pacman -S --needed --noconfirm git python rsync

echo "==> Enabling user lingering so the --user allocator runs without an active login..."
sudo loginctl enable-linger "$USER"

if [ -d "$CLONE_DIR/.git" ]; then
  echo "==> $CLONE_DIR already exists, pulling latest..."
  git -C "$CLONE_DIR" pull --ff-only
else
  echo "==> Cloning $REPO_URL into $CLONE_DIR..."
  git clone "$REPO_URL" "$CLONE_DIR"
fi

echo "==> Running linux-receiver install..."
cd "$CLONE_DIR/linux-receiver"
./scripts/install.sh

echo ""
echo "Done. Next: edit $CLONE_DIR/linux-receiver/config/rules.toml if you want non-default"
echo "routing, then point the Windows widget's config.toml at this machine's Tailscale name."
echo "See docs/02-tailscale-setup.md and docs/04-linux-receiver.md in the repo for details."
