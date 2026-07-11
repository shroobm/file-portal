# Changelog

All notable changes to File Portal are recorded here.
The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **Vault exporter (library pipeline, Part 4 — L11/L12).** `linux-converter/converter/exporter.py`,
  a second watch inside the existing converter service (no new unit): `library/staging/` bundle
  arrivals — plus a startup sweep for bundles that landed while the service was down — are
  committed into the working clone `~/file-portal/vault-work` at
  `Library/Inbox/<slug>--<sha256[:8]>/` and pushed to the local bare repo `~/file-portal/vault.git`
  (the transport resolved + wired in Open Decision #4). Per Decisions #5/#6: no tag/folder
  placement, no minted `[[links]]`, assets stay inside the bundle folder. Invariants enforced in
  code: creates new notes only (pathspec-scoped commits, committed paths never overwritten);
  re-ingest of an identical `source_sha256` is a no-op log line, deduped by `git grep` over
  committed `manifest.json` files in the **bare** repo so notes the Desktop has filed out of
  `Inbox/` still count; the staging copy is deleted only after the push succeeded AND
  `git cat-file -e` confirms the commit and every bundle file's blob in the bare repo — never on
  write-success alone (L12). Any git failure logs `EXPORT-FAIL` and keeps staging for the next
  sweep; a commit that pushed but crashed pre-verify resumes at push, not re-commit. Ingest
  commits are self-identifying (`user.name=file-portal-converter`). 8 unit tests against real
  temp git repos. Live-verified 2026-07-11 including the dedup no-op and blob-verified deletion.

### Fixed

- **Exporter event stall (found live 2026-07-11, fixed same session).** The converter assembles
  two dot-prefixed temp dirs inside `library/staging/` per bundle; their `created` events each
  held the watchdog dispatch thread for the full 60s stability timeout (the dir is renamed away,
  so its `manifest.json` never appears and `rglob` on the missing dir spins yielding `[]`),
  delaying every export by 2×60s. Dot-dirs are now skipped before the stability wait, and the
  wait bails when the directory vanishes. Export latency measured after the fix: ~25ms.

- **Conversion engine (library pipeline, Part 3 — L7-L10).** `linux-converter` now converts
  instead of logging "would convert". Dispatch is first-match by extension, mirroring the
  allocator's rules idiom: `.pdf`/`.epub` → PyMuPDF4LLM (layout mode; `import pymupdf.layout`
  is ordered before `import pymupdf4llm` in `converter/engines.py` because pymupdf4llm decides
  OCR availability at import time), `.docx` → Pandoc (`-t gfm`, media extracted and flattened
  into the bundle's assets). Clean-lane `.pdf`/`.epub` files are pre-probed for a real text
  layer (`chars_per_page`, logged on every conversion); sub-threshold files reroute to
  `pipeline/convert-scan-inbox/` as a normal `allocated` status event. The Scan lane
  (`use_ocr=OCRMode.FORCE_DROP_OLD` at `ocr_dpi` — NOT the plan doc's `force_ocr=True`, which
  in pymupdf4llm 1.28 maps to `FORCE_KEEP_OLD` and would *keep* a bad prior OCR layer; in 1.28
  layout mode OCR is need-based and automatic in every lane, and the modes only control prior
  OCR spans) is terminal: sub-threshold OCR yield quarantines the source
  with a `rejected` event — no retry cycle is possible by construction (Open Decision #3,
  resolved 2026-07-09). Event model, verified empirically: the allocator hop is a rename whose
  source is outside the converter's watch, which inotify reports as an unpaired `IN_MOVED_TO`
  = a plain `created` event (never `moved`, never `close_write`) — so the handler reacts to
  `created` with a size-stability wait, plus `moved` (the reroute) and `closed` (in-place
  writes), deduped by consuming the source on success.
  Output is a bundle folder (`<name>.md` + `assets/` + `manifest.json`
  with source SHA-256), assembled in a dot-prefixed temp dir and published by atomic rename to
  both `library/anchor/` (immutable snapshot) and `library/staging/` (transient export queue);
  image links are rewritten to Obsidian embeds (`![[assets/…]]`) and every markdown output is
  frontmatter-stamped with engine/lane/`lane_reason`/OCR provenance. Tuning lives in
  `linux-converter/config/converter.toml` (`min_chars_per_page` seed 100 — provisional),
  re-read per event like `rules.toml`. 26 unit tests added.
- **`convert-scan` category routing.** `rules.toml` routes `convert-scan` drops (`*.pdf`,
  `*.epub` — no `.docx`, Pandoc has no OCR) to `pipeline/convert-scan-inbox/`. This is the
  destination for the Desktop's W7 tile, whose meaning is now *force-OCR override* rather than
  "the lane for scans" (the probe detects scans itself) — see
  `coordination/messages/2026-07-09T23-05--linux-to-desktop--w7-semantics-force-scan.md`.
- **"Force OCR → Vault" widget tile (W7).** Sixth portal (`category = "convert-scan"`, 🔍)
  added to `config.rs` `AppConfig::default()` and the `portals.json` reference copy (and the
  live `%APPDATA%\file-portal\config.toml`). Per the 2026-07-09T23-05 coordination message the
  label is deliberately NOT "Scan → Vault": the Clean lane detects scans itself, so the tile is
  the user override that discards a garbled embedded OCR layer and re-OCRs at 300 dpi. No
  `main.js` change — the reroute/reject paths reuse the existing `allocated`/`rejected` events.

### Fixed

- **Hardcoded service paths (Defect A, flagged 2026-06-25, since duplicated).** Both
  `file-portal-allocator.service` and `file-portal-converter.service` hardcoded
  `%h/file-portal-src/...` while their `install.sh` copied the unit verbatim, breaking any
  other clone path. Both installers now `sed`-substitute `__WORKDIR__`/`__EXEC_PATH__`
  placeholders, matching `linux-dashboard/scripts/install.sh`.

- **Status feed regression on `feat/library-pipeline` (widget ✓/✗ feedback dead).** The
  `logs/status.json` writer was implemented on `master` (`0c3a074`) but never merged into the
  branch, so the widget's v2 feedback loop stalled at "allocator pending" the moment the ThinkPad
  service restarted onto branch code (found by W5 E2E, 2026-07-08). Ported `allocator/status.py`,
  the CLOSE_WRITE/`on_closed` completion handling with the non-inotify size-stability fallback,
  the per-file exception guard, quarantine collision-renames, and the 24-test suite
  (`tests/`, `requirements-dev.txt`) into the branch, reconciled with the L1 quarantine location
  (`root/quarantine` kept; master's `inbox/quarantine` discarded). Rejection semantics decided
  per the W5 coordination message: `rejected` = quarantine only; unmatched extensions are
  `allocated` to `sorted/misc` (the widget shows `dest`).

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
