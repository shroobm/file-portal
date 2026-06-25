# windows-widget

The Tauri desktop app that renders the portal tiles. See
[`../docs/03-windows-widget.md`](../docs/03-windows-widget.md) for the design rationale — this
file is just "how do I run it."

## Prerequisites

See [`../docs/07-development-guide.md`](../docs/07-development-guide.md) for the full toolchain
list (Node.js, Rust, Tauri CLI).

## Run in dev mode

```powershell
npm install
npm run tauri dev
```

## Build a release binary

```powershell
npm run tauri build
```

Output lands under `src-tauri/target/release/bundle/`.

## Desktop & taskbar shortcut

To launch the widget without a terminal, double-click
[`../scripts/windows/install-shortcuts.cmd`](../scripts/windows/install-shortcuts.cmd). It creates a
**File Portal** icon on your Desktop and in the Start Menu, pointing at whatever you've built
(release if present, otherwise the debug binary) and using `src-tauri/icons/icon.ico`.

Windows blocks scripts from pinning to the taskbar, so do that last step by hand: right-click the
new Desktop icon → **Pin to taskbar** (on Windows 11, → *Show more options* → *Pin to taskbar*).

Re-run the script after a fresh `npm run tauri build` to repoint the shortcuts at the new binary.

## First-run configuration

On first launch the app writes `%APPDATA%\file-portal\config.toml` with placeholder values.
Edit it (or delete it and relaunch to regenerate defaults) to point at your own Linux box:

```toml
linux_host = "mybox.your-tailnet.ts.net"
remote_user = "you"
remote_inbox_root = "~/file-portal/inbox"
```

`remote_user` must be a non-root account — see
[`../docs/06-security-model.md`](../docs/06-security-model.md).

## Note on icons

`src-tauri/tauri.conf.json` references `icons/icon.ico`, which is not included in this scaffold.
Drop a 256x256 `.ico` into `src-tauri/icons/` before running `tauri build` (dev mode works without
it).
