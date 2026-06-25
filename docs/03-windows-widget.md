# 03 — Windows Widget

Lives in [`windows-widget/`](../windows-widget). Built with [Tauri](https://tauri.app) (Rust
backend, HTML/CSS/JS frontend) — chosen over WPF/Electron because the resulting binary is small,
the app can sit on the desktop as a borderless always-on-top window, and the UI layer is trivial to
restyle without touching the transfer logic.

## What it looks like

A small panel of "portal" tiles, each one a labeled drop zone:

```
┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
│ 📄 Docs    │ │ 🖼 Photos  │ │ 💻 Code   │ │ 📦 Archive │
└───────────┘ └───────────┘ └───────────┘ └───────────┘
```

Dragging a file from Explorer onto a tile sends it through that portal's category. Tiles and their
categories are defined in [`windows-widget/src-tauri/tauri.conf.json`](../windows-widget/src-tauri/tauri.conf.json)
adjacent config (see `portals.json` once added) — adding a new portal is a config change, not a
code change.

## Responsibilities (and non-responsibilities)

The widget **does**:
- present drop targets and basic transfer feedback (queued / sending / done / failed),
- resolve native file paths from the OS drag-and-drop event,
- invoke the Rust `send_to_portal(category, paths)` command,
- shell out to `tailscale ssh <host> -- rsync ...` (falling back to `scp`) to move bytes.

The widget explicitly **does not**:
- decide the final destination folder on Linux — that's the allocator's job (see
  [`04-linux-receiver.md`](04-linux-receiver.md)),
- manage SSH keys or credentials — Tailscale SSH handles auth,
- run anything elevated — it only ever calls the `tailscale` CLI and `rsync`/`scp`, both as the
  logged-in Windows user.

## Key files

| File | Purpose |
|------|---------|
| `src/index.html` / `main.js` / `styles.css` | Portal UI, drag-and-drop handling, transfer status. |
| `src-tauri/src/main.rs` | Tauri commands, including `send_to_portal`, which builds and runs the `tailscale ssh` + `rsync` child process. |
| `src-tauri/tauri.conf.json` | Window config (borderless, always-on-top, size) and app metadata. |

## Configuration

The Linux host alias and per-category inbox subpaths are read from
`%APPDATA%\file-portal\config.toml` at runtime (created with sane defaults on first launch — see
the `config::load_or_init` function in `main.rs`). This keeps host-specific details out of the
repo/binary.

## Next

[`04-linux-receiver.md`](04-linux-receiver.md) — what happens to a file after it lands in `inbox/`.
