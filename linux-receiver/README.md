# linux-receiver

The user-level allocator service that sorts files dropped into `inbox/`. See
[`../docs/04-linux-receiver.md`](../docs/04-linux-receiver.md) for the design rationale and
[`../docs/05-allocation-rules.md`](../docs/05-allocation-rules.md) for the `rules.toml` format.

## Quick install on Arch Linux (clone + install in one step)

```bash
curl -fsSL https://raw.githubusercontent.com/shroobm/file-portal/master/scripts/linux/bootstrap-arch.sh | bash
```

This installs `git`/`python`/`rsync` via `pacman` (one-time `sudo`, same category as `tailscale up`
itself), clones the repo to `~/file-portal-src`, and runs `install.sh` as your normal user — no
further `sudo` anywhere in the process. See [`../scripts/linux/bootstrap-arch.sh`](../scripts/linux/bootstrap-arch.sh).

**This repo is currently private.** `git clone`/`curl` against a private GitHub repo needs
authentication — either run `gh auth login` first (so `git` picks up GitHub CLI's credential
helper) or use an SSH remote with a deploy key. Easiest path for a fresh Arch box: install `github-cli`
(`sudo pacman -S github-cli`), run `gh auth login`, then `gh repo clone shroobm/file-portal ~/file-portal-src`
instead of the raw `curl` one-liner above.

## Run in the foreground (for development/debugging)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m allocator.main
```

Default root is `~/file-portal` (override with `--root`). This creates `inbox/`, `sorted/`,
`logs/`, and `inbox/quarantine/` on first run.

## Install as a systemd --user service

```bash
./scripts/install.sh
systemctl --user status file-portal-allocator
journalctl --user -u file-portal-allocator -f
```

Never run `install.sh` with `sudo` — the script refuses to run as root on purpose. See
[`../docs/06-security-model.md`](../docs/06-security-model.md) for why.

## Editing rules

Edit `config/rules.toml` and save — no restart needed, it's re-read on every incoming file.

## Uninstalling

```bash
systemctl --user disable --now file-portal-allocator
rm ~/.config/systemd/user/file-portal-allocator.service
systemctl --user daemon-reload
```
