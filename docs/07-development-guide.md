# 07 — Development Guide

> **Scope: the first era — file routing.** This document describes the original system (drag a file
> onto a tile, the allocator sorts it on the Linux box), which is built and in daily use. It does
> **not** cover the document library pipeline the project grew later — conversion, the survival
> audit, the vault, the control room, the repair bench. For the system as a whole see
> [`20-file-portal-manual.md`](20-file-portal-manual.md); the pipeline's own design docs are `10`–`19`.
> Statements here are accurate within this scope unless noted inline.

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

## The other subprojects (second era)

This guide covers `linux-receiver/` and `windows-widget/`. The pipeline half of the project has four
more areas, each with its own README:

| Area | Notes |
|---|---|
| `linux-converter/` | Converter + exporter service. **Has its own 51-test suite** — `cd linux-converter && python -m pytest tests/ -v` (deps in `requirements-dev.txt`). Runs in CI. |
| `windows-converter/`| Desktop GPU conversion, analyst pass, survival audit. No test suite; verified by live acceptance runs. Not in CI. |
| `windows-remote/` | Remote-access/lockdown scripts — see [`17-remote-access-runbook.md`](17-remote-access-runbook.md). |
| `prototypes/repair-bench/` | Human-in-the-loop repair tool. Self-check: `python acceptance.py` (26 checks). Not in CI. |

Both Linux Python services are linted in CI; `windows-converter/` and the prototypes are not, so
run `ruff` there by hand before committing.

## Code style

- Rust: `cargo fmt` + `cargo clippy` before committing. The widget's full ritual is
  `cargo clippy --all-targets -- -D warnings` → `node --check` on touched JS → `cargo test` →
  `npm run build`. **Note:** `cargo test` is not yet in CI (see the workflow's trigger note).
- Python: `ruff` for linting/formatting — line-length 100, target py311, configured identically in
  each subproject's own `pyproject.toml`.
- Frontend JS: kept deliberately framework-free (no React/Vue) — it's a handful of drop zones, a
  build step would be more overhead than the UI warrants.

## Branching / commits

Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`) — see
[`08-roadmap.md`](08-roadmap.md) for the milestone each change should map to.
