# File Portal

Drag-and-drop "portal" widgets for the Windows 10 desktop that securely push files to a Linux
machine over a [Tailscale](https://tailscale.com) tailnet, where a small user-level service sorts
("allocates") them into the right destination folder — **no sudo required on either end.**

```
┌─────────────────────────┐        Tailscale SSH         ┌──────────────────────────┐
│   Windows 10 Desktop     │  (encrypted, no open ports)  │   Linux Box (any distro)  │
│                          │ ───────────────────────────► │                          │
│  [Docs] [Photos] [Code]  │  stream over `tailscale ssh` │  ~/file-portal/inbox/     │
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
| `docs/`             | The knowledge base. **Start with [`docs/20-file-portal-manual.md`](docs/20-file-portal-manual.md)** — the current system, end to end. `docs/00`–`docs/09` describe the original file-routing tool only (see Status). |
| `windows-widget/`   | The Tauri desktop app: portal tiles plus the Dock · Room · Wall · Bench surfaces. |
| `windows-converter/`| Desktop-side document conversion — Marker/GPU lanes, the analyst pass, the survival audit, shipping bundles to the Linux staging area. |
| `windows-remote/`   | Remote-access setup and lockdown scripts for the desktop (see [`docs/17-remote-access-runbook.md`](docs/17-remote-access-runbook.md)). |
| `linux-receiver/`   | The user-level allocator service that sorts incoming files.             |
| `linux-converter/`  | The user-level converter + **exporter** service: converts documents and writes vaulted notes into the bare git vault. |
| `linux-dashboard/`  | Optional GTK4 desktop app that visualizes `sorted/` (gallery + lists).  |
| `prototypes/`       | Working prototypes, notably `repair-bench/` — the human-in-the-loop repair tool for failed conversions. |
| `coordination/`     | Agent-to-agent message bus between the two machines — see its own README. |
| `sessions/`         | One structured closeout per development session ([`docs/21`](docs/21-session-closeout-contract.md)). |
| `SYMPTOM-INDEX.md`  | Known failures, keyed on what the system *does* when it's wrong. Read it before debugging anything. |
| `CLAUDE_README.md`  | The cross-machine mission brief, session protocol, and Change Ledger. |
| `scripts/`          | One-off setup helpers (Tailscale SSH config, dev environment bootstrap).|

## Quickstart

1. Read [`docs/20-file-portal-manual.md`](docs/20-file-portal-manual.md) — the user textbook and
   developer reference for the system as it actually stands. For the original file-routing design
   in isolation, [`docs/00-overview.md`](docs/00-overview.md) still holds.
2. Set up Tailscale SSH between the two machines: [`docs/02-tailscale-setup.md`](docs/02-tailscale-setup.md).
3. Install the Linux allocator service: [`linux-receiver/README.md`](linux-receiver/README.md).
4. Run the Windows widget in dev mode: [`windows-widget/README.md`](windows-widget/README.md).
5. (Optional) Install the Linux dashboard to browse `sorted/`: [`linux-dashboard/README.md`](linux-dashboard/README.md).

## Status

**Two eras, and it matters when reading the docs.** The original goal — drag a file onto a tile,
have it sorted on the Linux box — is **built and in daily use**: streamed transfer over Tailscale
SSH, the allocator, the status feed, the dashboard.

The project then grew a second half: a **document library pipeline** that converts dropped PDFs to
markdown (GPU Marker with clean/scan lanes), scores them for degeneration in a survival audit,
holds anything that fails, and exports blessed bundles into a git-backed Obsidian vault — plus a
control-room UI, remote access, and a repair bench for fixing failed conversions by hand.

`docs/00`–`docs/09` were written for the first era and **do not describe the pipeline at all**.
`docs/10` onward is the second era; [`docs/20`](docs/20-file-portal-manual.md) is the current
whole-system reference and [`CHANGELOG.md`](CHANGELOG.md) plus `CLAUDE_README.md`'s Change Ledger
are the authoritative record of what shipped when. [`docs/08-roadmap.md`](docs/08-roadmap.md)
tracks the first era only and its checkboxes lag reality.

## License

MIT — see [`LICENSE`](LICENSE).
