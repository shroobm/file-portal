# File Portal

Drag-and-drop "portal" widgets for the Windows 10 desktop that securely push files to a Linux
machine over a [Tailscale](https://tailscale.com) tailnet, where a small user-level service sorts
("allocates") them into the right destination folder — **no sudo required on either end.**

```
┌─────────────────────────┐        Tailscale SSH         ┌──────────────────────────┐
│   Windows 10 Desktop     │  (encrypted, no open ports)  │   Linux Box (any distro)  │
│                          │ ───────────────────────────► │                          │
│  [Docs] [Photos] [Code]  │ streamed over `tailscale ssh`│  ~/file-portal/inbox/     │
│   portal widgets         │                               │  → allocator sorts into  │
│   (Tauri app)            │                               │    ~/file-portal/sorted/ │
└─────────────────────────┘                               └──────────────────────────┘
```

## Why this exists

Most "send file to my server" tools either require opening a port, running a privileged daemon,
or trusting a third-party cloud relay. This project avoids all three:

- **Tailscale** gives us a private, encrypted, NAT-traversing network between exactly the devices
  you own — no port forwarding, no public exposure.
- **Tailscale SSH** authenticates using your tailnet identity, so the Windows side never needs to
  manage SSH keys, and the Linux side never needs a password prompt or `sudo` — it's just your
  normal user account receiving files it already has permission to write.
- The Linux-side **allocator** is a plain user-level (`systemd --user`) Python service. It only
  ever touches paths under the receiving user's home directory.

## Repository layout

| Path                | What it is                                                              |
|---------------------|--------------------------------------------------------------------------|
| `docs/`             | The knowledge base — read `docs/00-overview.md` first.                  |
| `windows-widget/`   | The Tauri desktop app that renders the portal widgets.                  |
| `linux-receiver/`   | The user-level allocator service that sorts incoming files.             |
| `linux-dashboard/`  | Optional GTK4 desktop app that visualizes `sorted/` (gallery + lists).  |
| `scripts/`          | One-off setup helpers (Tailscale SSH config, dev environment bootstrap).|

## Quickstart

1. Read [`docs/00-overview.md`](docs/00-overview.md) for the full mental model.
2. Set up Tailscale SSH between the two machines: [`docs/02-tailscale-setup.md`](docs/02-tailscale-setup.md).
3. Install the Linux allocator service: [`linux-receiver/README.md`](linux-receiver/README.md).
4. Run the Windows widget in dev mode: [`windows-widget/README.md`](windows-widget/README.md).
5. (Optional) Install the Linux dashboard to browse `sorted/`: [`linux-dashboard/README.md`](linux-dashboard/README.md).

## Status

Early scaffold — architecture and interfaces are defined, implementation is in progress. See
[`docs/08-roadmap.md`](docs/08-roadmap.md) for what's done vs. planned.

## License

MIT — see [`LICENSE`](LICENSE).
