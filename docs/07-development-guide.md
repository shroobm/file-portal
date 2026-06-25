# 07 — Development Guide

## Prerequisites

| Tool | Used for | Install |
|------|----------|---------|
| Node.js (LTS) + npm | Tauri frontend tooling | https://nodejs.org |
| Rust toolchain (`rustup`) | Tauri backend | https://rustup.rs |
| Tauri CLI | `cargo tauri dev` / `build` | `cargo install tauri-cli --version "^2"` |
| Python 3.11+ | Linux allocator | distro package manager |
| Tailscale (both machines) | Transport | see [`02-tailscale-setup.md`](02-tailscale-setup.md) |

Windows also needs the [Microsoft C++ Build Tools / WebView2 runtime](https://tauri.app/start/prerequisites/)
that Tauri's own setup docs require — WebView2 ships with Windows 10/11 by default on most
up-to-date machines, but check `tauri info` if the dev build fails.

## Running the widget locally

```powershell
cd windows-widget
npm install
npm run tauri dev
```

This opens the portal panel in dev mode with hot-reload on the frontend files.

## Running the allocator locally

```bash
cd linux-receiver
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m allocator.main --config config/rules.toml
```

Run it in the foreground first to watch log output before installing it as a `systemd --user`
service via `scripts/install.sh`.

## Testing a full round trip

1. Start the allocator on the Linux box (foreground, for visible logs).
2. Run the widget in dev mode on Windows.
3. Drag a test file onto any portal tile.
4. Confirm: file appears briefly in `~/file-portal/inbox/<category>/`, then is moved into
   `~/file-portal/sorted/...`, and an entry appears in `~/file-portal/logs/allocator.log`.

## Code style

- Rust: `cargo fmt` + `cargo clippy` before committing.
- Python: `ruff` for linting/formatting (config in `linux-receiver/pyproject.toml` once added).
- Frontend JS: kept deliberately framework-free (no React/Vue) — it's a handful of drop zones, a
  build step would be more overhead than the UI warrants.

## Branching / commits

Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`) — see
[`08-roadmap.md`](08-roadmap.md) for the milestone each change should map to.
