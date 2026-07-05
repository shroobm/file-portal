# Changelog

All notable changes to File Portal are recorded here.
The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- **Allocator could move files while they were still being written.** The watcher reacted to
  `on_created`, but the streaming transport (`tailscale ssh … "cat > file"`) creates the file
  before the bytes arrive, so a transfer could be sorted (and size-checked) half-written. The
  allocator now treats inotify `CLOSE_WRITE` (`on_closed`) as the completion signal for in-place
  writers and keeps `on_moved` for atomic-rename tools like rsync; on non-inotify platforms it
  falls back to `on_created` plus a wait-until-size-stable check.
- **In-flight rsync temp files could be sorted mid-transfer.** Dot-prefixed files (rsync's
  `.name.XXXXXX` pattern) are now ignored; the completing rename is handled instead.
- **Quarantined files could be re-processed.** `inbox/quarantine/` lives inside the watched inbox
  tree; events under it are now explicitly ignored, preventing re-handling/log loops for rejected
  files.
- **Quarantine overwrote earlier rejects of the same name.** Quarantine now applies the `rename`
  collision policy (`big.txt`, `big (1).txt`, …).
- **One bad file could kill the watcher.** Any exception while allocating a single file (invalid
  rules.toml, bad destination template, permissions) is now logged instead of propagating into —
  and stopping — the observer thread.

### Added (allocator / repo)

- **v2 feedback loop, Linux half:** every outcome (`allocated`/`skipped`/`rejected`) is appended
  to `~/file-portal/logs/status.json` (`allocator/status.py`) — bounded to the newest 200 events
  and rewritten atomically so the widget can poll it over the existing
  `tailscale ssh … "cat …"` channel without ever reading partial JSON.
- **Test suite:** `linux-receiver/tests/` covering rules resolution (globs, date tokens,
  defaults), collision policies, quarantine behavior, the new event guards, and the status feed;
  dev deps in `linux-receiver/requirements-dev.txt`.
- **CI:** `.github/workflows/ci.yml` — ruff lint + format check for both Python subprojects,
  pytest for the allocator, and `cargo fmt --check` + `cargo clippy -D warnings` for the Tauri
  widget on a Windows runner.

### Docs

- Corrected every remaining description of the retired rsync/scp transport (README diagram,
  00-overview, 01-architecture diagram + data flow + tradeoffs, 02-tailscale-setup step 6,
  03-windows-widget) to describe the `tailscale ssh … cat` streaming transport — the follow-up
  flagged in the documentation audit.
- 04-linux-receiver: documented the new completion-signal model (CLOSE_WRITE / MOVED_TO /
  stability-wait fallback), quarantine guard, `status.py`, and the test suite.

---

Earlier unreleased work (widget render + transport fixes):

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
  stream each file's bytes through `tailscale ssh <user>@<host> "mkdir -p … && cat > …"`, removing
  the rsync/scp dependency. Remote paths are shell-quoted (with `~/` preserved for expansion) to
  handle filenames containing spaces or quotes.

### Added

- Surfaced transfer errors to the UI and the console (`send_to_portal failed`, per-file failure
  details) and a clearer "dropped outside any portal" status message.
- Enabled the Tauri `devtools` feature in `src-tauri/Cargo.toml` for in-app debugging of the
  WebView during development.

> Note: the widget binary must be rebuilt for these changes to take effect
> (`cd windows-widget && npm install && npm run tauri build`, or `npm run tauri dev` for a
> hot-reloading dev run). The previously running `target/debug` binary predates this fix.
