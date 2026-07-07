# Changelog

All notable changes to File Portal are recorded here.
The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- **Widget showed nothing on launch (blank/invisible window).** `windows-widget/src/main.js`
  imported the Tauri JS API with bare ES-module specifiers
  (`import { invoke } from "@tauri-apps/api/core"`). The project intentionally ships no
  frontend bundler (see `docs/07-development-guide.md`), so the WebView cannot resolve those
  specifiers; the module failed to load, `init()` never ran, and no portal tiles were rendered.
  Because the window is transparent and undecorated, this looked like the app failing to open at
  all. Fixed by enabling `app.withGlobalTauri` in `src-tauri/tauri.conf.json` and reading the API
  off the injected `window.__TAURI__` global (`core`, `webview`) instead of importing it.
- **Invalid dev configuration.** Removed `build.devUrl: "../src"` from
  `src-tauri/tauri.conf.json`; `devUrl` expects a dev-server URL, not a static directory, and the
  widget is run from the built `frontendDist` assets.
- **Drag-and-drop hit-testing was wrong under display scaling.** `tileForPosition()` compared the
  drag event's physical-pixel coordinates against `getBoundingClientRect()` CSS/logical pixels, so
  tiles were mis-targeted on any DPI scale other than 100%. Coordinates are now divided by
  `window.devicePixelRatio` before the hit-test.
- **First drag frame was ignored.** The drag handler only reacted to `over`; it now also handles
  the initial `enter` event so highlighting starts immediately.
- **File transfer transport could not work as written.** `src-tauri/src/transfer.rs` shelled out to
  `rsync`/`scp` over `tailscale ssh`. `rsync` is not present on stock Windows, and `scp`/plain `ssh`
  fail host-key verification against Tailscale SSH's managed keys. Rewrote `send_one_file()` to
  stream each file's bytes through `tailscale ssh <user>@<host> "mkdir -p … && cat > .part-<name> &&
  mv -f .part-<name> <name>"`, removing the rsync/scp dependency. Writing to a `.part-` temp and
  renaming into place makes arrival a single atomic `on_moved` event (the allocator never picks up a
  half-written file), and the bytes are streamed with `std::io::copy` instead of being buffered in
  RAM. Remote paths are shell-quoted (with `~/` preserved for expansion) to handle filenames
  containing spaces or quotes.
- **A malformed `config.toml` silently reverted to `CHANGE_ME` defaults.** `src-tauri/src/config.rs`
  now surfaces the TOML parse error (naming the file) and exits, and only seeds defaults when the
  config is genuinely absent — a present-but-unparseable config no longer masquerades as a working
  install pointed at the placeholder host/user.

### Added

- **`convert` category routing (library pipeline, Part 2).** `linux-receiver/config/rules.toml`
  routes `convert` drops (`*.pdf`, `*.epub`, `*.docx`) to `pipeline/convert-inbox/` — a process
  mouth for the converter, deliberately outside `sorted/`. Unmatched extensions still fall through
  to `sorted/misc`. Verified live on the ThinkPad allocator.
- **`linux-converter/` service skeleton (library pipeline, Part 2).** A second `systemd --user`
  watcher (`file-portal-converter`) mirroring the allocator's structure and event model (prefer
  `on_moved`, fall back to `on_created`, skip `.part-*` dotfiles). Watches
  `~/file-portal/pipeline/convert-inbox` and, for now, only logs `would convert <path>` to
  `logs/converter.log` — the conversion engine (PyMuPDF4LLM/Pandoc, Clean/Scan lanes) is Part 3.
  Installed, enabled, and verified end-to-end (allocator hop → converter log) on the ThinkPad.

### Fixed (linux)

- **Quarantine loop.** `allocator/config.py` moved quarantine from `inbox/quarantine/` (inside the
  watched tree — quarantining fired another event and re-processed the file forever) to
  `~/file-portal/quarantine/` at the root. Verified live: an oversized file is rejected once and
  stays quarantined. Docs (`docs/05`, `linux-receiver/README.md`) updated to match.
- **`linux-converter/scripts/install.sh` was not executable** (mode 100644 vs the receiver's
  100755), so the documented `./scripts/install.sh` invocation failed.

- **Widget titlebar with drag and minimize.** The frameless window gains a `data-tauri-drag-region`
  titlebar (grab cursor) with a minimize button wired to `getCurrentWindow().minimize()`;
  `src-tauri/capabilities/default.json` grants `core:window:allow-start-dragging` and
  `core:window:allow-minimize`, and the window height goes 160→186 so the bar doesn't crowd the
  tiles.
- Surfaced transfer errors to the UI and the console (`send_to_portal failed`, per-file failure
  details) and a clearer "dropped outside any portal" status message.
- Enabled the Tauri `devtools` feature in `src-tauri/Cargo.toml` for in-app debugging of the
  WebView during development.

> Note: the widget binary must be rebuilt for these changes to take effect
> (`cd windows-widget && npm install && npm run tauri build`, or `npm run tauri dev` for a
> hot-reloading dev run). The previously running `target/debug` binary predates this fix.
