# 00 — Overview

## The problem

You want to drag a file on your Windows desktop and have it land in the right folder on a Linux
box (a home server, a NAS, a dev box) — without:

- opening a port on your router,
- running anything as `root`/`sudo` on the Linux side,
- managing SSH keys by hand,
- or trusting a third-party file-relay service with your data.

## The shape of the solution

Three pieces, each with one job:

1. **Tailscale** — a private mesh network (WireGuard under the hood). Both machines join the same
   tailnet and get stable private IPs / MagicDNS names. No public exposure, no port forwarding.
2. **Tailscale SSH** — Tailscale's own SSH implementation, gated by your tailnet's ACLs instead of
   SSH keys or passwords. Whoever is allowed into the tailnet (and matches the ACL rule) can SSH in
   as a normal, unprivileged user. This is what gives us "no sudo" — we never need root because we
   only ever write to paths the receiving user already owns.
3. **The Windows widget + Linux allocator** — the part this repo actually builds:
   - **`windows-widget/`**: a small always-on-top Tauri app. Each "portal" on screen represents one
     destination category (e.g. *Documents*, *Photos*, *Code*). Drop a file on a portal and the app
     streams it over `tailscale ssh` into a per-category inbox folder on the Linux box — a remote
     `cat >` into a `.part-` temp file, then an atomic rename (no `rsync`/`scp`).
   - **`linux-receiver/`**: a `systemd --user` Python service that watches the inbox folder(s) and
     moves files into their final destination according to rules in
     [`linux-receiver/config/rules.toml`](../linux-receiver/config/rules.toml) — e.g. by file
     extension, by which portal/category it arrived through, or by simple glob patterns.
   - **`linux-dashboard/`** (optional, read-only): a standalone GTK4 desktop app that visualizes
     what's actually in `sorted/` — a thumbnail gallery for photos, a browsable list for
     everything else — and updates live as the allocator sorts new files in. Not part of the
     transfer path; see [`09-linux-dashboard.md`](09-linux-dashboard.md).

## Why "allocate" instead of just "send"

A plain file copy answers "did the bytes arrive." Allocation answers "did the bytes end up in the
right place, and did anything need follow-up?" The allocator owns:

- routing rules (category → destination directory),
- collision handling (what happens if a file with the same name already exists),
- basic validation (reject oversized files beyond `max_file_size_mb`),
- and an event log so you can see what moved where and when.

## Read next

- [`01-architecture.md`](01-architecture.md) — component diagram and data flow.
- [`02-tailscale-setup.md`](02-tailscale-setup.md) — get Tailscale SSH working first; everything
  else depends on it.
- [`06-security-model.md`](06-security-model.md) — what this design protects against, and what it
  explicitly does not.
