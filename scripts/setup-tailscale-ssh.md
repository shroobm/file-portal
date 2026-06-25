# Tailscale SSH setup checklist

Quick checklist version of [`../docs/02-tailscale-setup.md`](../docs/02-tailscale-setup.md) —
use the doc for explanations, this for a fast re-run when setting up a new pair of machines.

- [ ] Install Tailscale on Windows machine, sign in.
- [ ] Install Tailscale on Linux machine: `curl -fsSL https://tailscale.com/install.sh | sh`
- [ ] `sudo tailscale up --ssh --advertise-tags=tag:home-server` on Linux.
- [ ] `tailscale status` on both machines — confirm both devices visible.
- [ ] Add an SSH ACL rule in the admin console restricting `users` to a non-root account.
- [ ] From Windows: `tailscale ssh you@<linux-magicdns-name>` — confirm no prompt, lands in shell.
- [ ] On Linux: `which rsync` — install via package manager if missing.
- [ ] Note the Linux MagicDNS name; put it in `%APPDATA%\file-portal\config.toml`
      (`linux_host`) after first launching the widget.
