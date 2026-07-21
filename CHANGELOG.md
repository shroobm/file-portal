# Changelog

All notable changes to File Portal are recorded here.
The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- **S30 — the Survival Audit's enforcement policy is SIGNED; `compute_verdict` gates on the two unambiguous signals (2026-07-20).**
  Closes the S28 "awaiting threshold sign-off" gate (docs/15 §12). `windows-converter/fidelity_audit.py`
  `compute_verdict` rewritten: **degeneration** (OCR/LLM repetition loops — witness-free, so it
  gates on either lane) and **analyst near-exact loss** (`doc < 0.995 OR run ≥ 25`) are now the
  only signals that reach `fail`; survival/agreement score, page flags, omission runs, and
  garbage rate are report-only **localizers** (`flag` at most) — acceptable books measure
  0.76–0.96 survival (legitimate reflow), so gating on them would false-fail good work and erode
  the terracotta signal. A clean-lane survival gate was explicitly considered and rejected.
  **Verified** over all four vaulted books: Brain of the Firm → `fail` (degeneration; worst block
  zlib 0.003, trigram ×2,267), the other three → `pass` — zero false positives; the prototype's
  loose-threshold Textor false alarm is cleared at the production thresholds. The verdict is
  always computed and recorded honestly; **enforcement is a separate, default-off lever**
  (`audit-mode.txt` `report`|`enforce`; a `fail` under `enforce` parks the bundle in `held/`
  rather than shipping — contract in docs/15 §12, wired in the dedicated widget-build session).
  Widget projection designed and specced as **§13 (The Assay)**: a `◎ assay` line station + an
  evidence card (damage map + verbatim runs) + the `report ⇄ enforce` control, terracotta
  reserved for `fail` only. No pipeline behavior changes yet (verdict-only; enforce defaults off).

### Added

- **S31 — the Assay: the Survival Audit's widget projection (docs/15 §13, 2026-07-20).**
  The audit becomes a see-and-steer channel in the widget. A new `◎ assay` line station
  (between gate and ship) carries the last conversion's verdict as a dot — green pass, amber
  flag, **terracotta fail, the only pulse** — with the survival number beside it. On flag/fail
  it opens an evidence card: a book-length **damage map** (OCR-loop zones as terracotta bands
  from the manifest's `degeneration_detail.worst` line positions ÷ a new `md_lines` field;
  omission runs as amber bands by page), the worst runs **verbatim** (chars/trigram/excerpt),
  a `report ⇄ enforce` control, and a `⟳ re-convert` remedy. Pure projection: new Rust
  `assay.rs` (`status` reads the newest anchor/pending/held `manifest.json` fidelity block +
  the held queue; `get_mode`/`set_mode` on `audit-mode.txt`; `reconvert` re-queues
  `drop/done/<src>` → `drop/`), four commands in `main.rs`, and the station + card + poll in
  `index.html`/`main.js`/`styles.css`. **Enforcement wired, default off:**
  `convert_and_ship.audit_mode()` + `_enforce_hold()` park a `fail` verdict in `held/<sha16>/`
  (with its manifest) instead of shipping, at all three ship sites (direct / defer-auto-local
  / resume); `report` mode is a verified no-op. The remedy's vault swap is still a manual
  content-replace (THE SUPERSEDE GAP). Verified: `cargo clippy -D warnings` clean, Python
  `py_compile` + `audit_mode()` → `report`, `main.js` parses. Live Beer flag→re-convert→
  re-audit test + `npm run tauri build` / relaunch pending (the rebuild ritual, Rab-driven).

- **S28 — the Survival Audit: a conversion-fidelity gate (`windows-converter/fidelity_audit.py`, 2026-07-20).**
  Implements docs/15. Measures how much of a source PDF survives into the Marker markdown
  (convert stage) and how much of the Marker markdown survives the qwen pass (analyst stage),
  by window-survival containment against an **ephemeral pymupdf witness** (extracted, scored,
  discarded — nothing doubled or vaulted). Deterministic, CPU-only, long-path-safe (`\\?\`),
  CJK-aware (space-free char-window matching). Recall-first: it asks "is every window of the
  source findable in the output?", localizes misses into per-page **runs** with excerpts, and
  runs §5 tripwires (degeneration via per-paragraph zlib + repeated-trigram; page-coverage;
  informational asset-delta; reverse-containment anti-hallucination sample; scan-lane
  garbage-token rate). Per-stage asymmetry per docs/15 §6: clean lane = `fidelity`, scan lane
  = `agreement` (imperfect witness, never hard-fails), analyst stage = near-exact (the Marker
  doc is the reference). Writes a `fidelity` block into `manifest.json` (schema §7) that rides
  the unchanged exporter, and emits `stage:"audit"` events. **Wired report-only into
  `convert_and_ship.py`** (convert stage after Marker; analyst stage inline + in `apply_analyst`)
  — every hook is crash-wrapped so an audit failure can never fail a conversion; the verdict is
  recorded but **gates nothing** until thresholds are signed off (docs/15 §9). Activates on the
  next watcher restart. Widget projection (terracotta-on-fail) deferred to a post-sign-off slice.
  Calibrated over the vaulted books: the degeneration tripwire cleanly flags Brain of the Firm's
  two loop zones and none of the other three at the §9.1 priors (zlib<0.20 OR trigram≥40);
  survival/runs validated as a localizer (findings in the S28 Session Log).

- **S18 — pre-flight analyst card in the widget + `windows-converter/` GPU lane (2026-07-19).**
  The Phase 4 intake inversion's Desktop half (docs/11+12): a new top-level
  `windows-converter/` (Python, runs in the `marker-env` outside the repo) converts
  documents on the Desktop GPU with Marker — policy-routed via a text-render-mode-3 OCR-layer
  probe (default vs `--strip_existing_ocr` + capped batches) — assembles bundles
  format-identical to `linux-converter`'s, and ships them to ThinkPad staging over
  tar-through-`tailscale ssh` (dot-dir + atomic `mv`); the unchanged exporter commits them
  (cross-machine dedup live-proven: EXPORTED `6008eb66`, re-ship + Beer both EXPORT-SKIP).
  Optional link-fenced analyst pass (`analyst.py`): every embed becomes an opaque
  `⟦IMG-n⟧` token before the LLM sees text and must survive verbatim, or that chunk ships
  un-analyzed — two backends behind one flag, local `qwen3:8b` (air-gapped, 138 chars/s
  measured) and `gemini-flash-latest` (cloud, 186.7 chars/s, 13 s pacing + backoff under
  the measured free-tier 20-request window), both book-proven (44/47 with 3 fence-saves;
  7/7). `watch_and_convert.py` watches `drop/` (dotfile skip, stability wait, sequential
  single-flight, done/failed archiving; live E2E drop→convert→ship→EXPORT-SKIP in 52 s).
  **Widget:** new `#preflight-cards` panel (vault-bar's Claude Code styling) rendering
  `analyst.preflight()` JSON per parked bundle — measured ETAs, chunk/token counts,
  GPU-busy flag, free-tier warning, privacy labels, terracotta-highlighted recommendation —
  with three routes (🔒 Local / ☁ Flash / Ship as-is); a click spawns the converter's
  `--resume` detached (`preflight.rs`, `CREATE_NO_WINDOW`) and the card tracks
  running/failed states until the queue clears and the vault bar takes over. New config
  keys (all `serde(default)`, feature hidden when unset): `gpu_pipeline_dir`,
  `gpu_python_exe`, `gpu_converter_dir`. Window grows per visible card
  (`core:window:allow-set-size`). Watcher analyst-mode gains `ask` = park for the card.
- **W8 — "Add to Library" button in the widget (2026-07-12).** New `#vault-bar` under the
  tiles (Claude Code-styled: near-black panel, terracotta `#D97757` accent, monospace, ✳
  glyph) backed by a new `src-tauri/src/vault.rs`: `vault_check` (git fetch + behind-count +
  new `Inbox/<slug>/manifest.json` slugs vs `origin/main`) and `vault_pull` (fetch +
  `merge --ff-only`, then reports exactly which bundles arrived). The clone's persisted
  `core.sshCommand="tailscale ssh"` carries all transport; the widget never talks to the
  host itself and never initializes a repo (Decision #4). Button states: hidden when
  `vault_library_dir` (new config key, `serde(default)` so old configs parse) is unset; dim
  "Library · up to date"; glow-pulse "Add N new note(s) to Library" when the ThinkPad has
  pushed bundles this machine hasn't pulled; spinner while pulling; green "✓ Added: <slugs>".
  Polls every 45s, tightens to 10s for 3 minutes after any drop allocated to
  `pipeline/convert*` (a conversion is ~1–2 min away from landing). Window height 186 → 224.
  All git calls pass `-c core.longpaths=true` — the first live pull failed checkout on
  bundle-interior filenames longer than Windows' 260-char MAX_PATH (see L15 coordination
  message; that message also asks the converter to shorten interior names at the source).
  Also fixed while in there: pull errors are now classified fetch-vs-merge so a local
  checkout failure no longer reads as "vault host unreachable", and the exe is built
  `windows_subsystem = "windows"` so no console window spawns behind the widget.
  Live-verified end to end: the Textor ingest (`fd0e50a`) lit the button with its slug
  within one poll, one click pulled + checked out the bundle (note + 4 assets + manifest),
  and the bar settled back to "up to date".

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

- **Ship stage: an offline ThinkPad was masked as a tar timeout (2026-07-19, `e7ea85a`).**
  During the first ⚡ production run (Brain of the Firm), the ThinkPad going dark mid-ship
  surfaced as `tar … timed out after 60 seconds` (the 17:57 UTC `gate/failed` event): ssh
  died on the dead tailnet dial, leaving the local tar wedged writing into a dead pipe, and
  tar's own 60 s timeout fired first — burying the real network error. `ship()` now wraps
  the ssh run in try/finally, kills the wedged tar whenever ssh fails or times out so the
  actual error propagates, and the tar wait is 60 → 600 s for large bundles. The book
  recovered and vaulted the same night (20:49 UTC, `f310f759`). *Entry written
  retroactively in S27 — the fix was committed after S26's close and §4 accounting caught
  it with no CHANGELOG entry.*

- **CI first-contact failures on PR #1 (2026-07-13).** The workflow (written 2026-07-05 on
  master) had never run against the branch's code. Two independent breaks: (1) `CI / python` —
  pytest collection died with `No module named 'allocator'` because the runner pip-installs
  only requirements and bare `pytest` doesn't put the package root on `sys.path` (local venvs
  never hit this). Fixed with `[tool.pytest.ini_options] pythonpath = ["."]` in
  `linux-receiver/pyproject.toml` and `linux-converter/pyproject.toml` (converter tests aren't
  in CI yet — same latent bug fixed while there); reproduced and verified in a fresh
  requirements-only venv (collection error → 24 tests collected). (2) `CI / rust` —
  `cargo fmt --check` diffs in `config.rs`/`main.rs`/`status.rs`/`vault.rs`, all code written
  after the July 5 formatting pass. Fixed with `cargo fmt` (style-only, zero behavior change);
  `cargo clippy --all-targets -- -D warnings` verified clean locally so the never-reached
  clippy step doesn't become the next surprise. Known-red follow-ups, not fixed tonight:
  CI doesn't run `linux-converter`/`linux-dashboard` tests, and `actions/checkout@v4` +
  `setup-python@v5` emit Node 20 deprecation warnings (bump to current majors later).

- **Bundle-interior filenames blew past Windows' 260-char MAX_PATH on the consuming end
  (L15, found by W8's first live click, 2026-07-12).** The bundle directory was already
  slug-clamped in the vault, but the names *inside* it re-derived from the raw source stem:
  a 200-byte-clamped `.md` plus engine-named asset PNGs (`<full-source-name>-<page>-<idx>.png`,
  ~230 bytes for real Anna's Archive names) pushed full vault paths past 330 chars — the
  Desktop needed `core.longpaths=true` to check the Textor bundle out at all. Fixed at the
  source, both halves: (1) the converter now hands the engine a short, sanitizer-proof
  hardlink (`<slugify(stem)[:40]><ext>`, hardlink with copy fallback) inside the sha-keyed
  assembly dir — pymupdf4llm derives image names from the document path it opens (its
  `filename=` kwarg is ignored for path-opened docs), so asset basenames drop to ≤ ~61 bytes;
  the link is removed before publish and is never part of the bundle. This also closes a
  latent Linux-side overflow: a >243-byte source name + `-0001-00.png` would have exceeded
  ext4's 255-byte component limit and quarantined, L13-style. (2) `bundle.clamp_name`'s
  budget drops 200 → 80 bytes, so the worst-case vault-relative note path
  `Inbox/<slug60>--<sha8>/<stem80>.md` is exactly 160 bytes — inside MAX_PATH with margin
  for real vault prefixes. Regression test (red-first on both halves): a 230-byte spaced
  stem with an embedded image converts, every emitted vault-relative path ≤ 160 bytes, the
  bundle root holds exactly note + manifest + assets/, and every embed resolves on disk.

- **Black console window flashing every 45 seconds (W8 follow-up, 2026-07-12, user-reported).**
  W8's `windows_subsystem = "windows"` removed the widget's own console — which the child
  processes (`git` vault polls, `tailscale ssh` status/transfer calls) had been silently
  attaching to. Orphaned, each spawn opened its own console window for the duration of the
  command, most visibly the 45s vault poll. All three spawn sites (`vault.rs`, `status.rs`,
  `transfer.rs`) now pass `CREATE_NO_WINDOW` (0x08000000). Verified across a live poll
  cycle: no window, bar still reports fresh state.

- **Spaced filenames with images quarantined every time (L13, found by the first real
  document 2026-07-12).** pymupdf4llm sanitizes the entire image output path it is given —
  spaces become underscores in *directory components* too — while the converter built its
  assembly temp dir from the source stem verbatim, so the engine wrote images into a
  sibling directory that never existed and the first image write failed the whole
  conversion. The assembly dir is now keyed on the source SHA-256
  (`.part-<sha256[:16]>`), which is sanitizer-proof by construction and immune to
  filename-length pressure; the published bundle keeps the original stem, spaces and all.
  While in there, bundle names are clamped to a 200-byte budget (`bundle.clamp_name`) —
  ~225-byte Anna's Archive stems plus the derived `.part-<name>.staging-copy` suffix
  brushed ext4's 255-byte component limit. Regression-tested with a spaced-name+image
  fixture that reproduces the exact field failure, and live-verified end to end.
- **Exporter placed bundles at `Library/Library/Inbox/` in the vault (L14, cosmetic).**
  Decision #6's `Library/Inbox/<slug>--<sha8>` is a *vault-relative* path, but the repo
  root already IS the vault's Library folder (Decision #4), so `exporter.py`'s
  `INBOX_REL` doubled the level; the L11 tests asserted the same misreading and stayed
  green. Now `Inbox/<slug>--<sha8>` repo-relative. No migration: the Desktop had already
  filed the one affected bundle to repo-root `Inbox/` as a normal Decision #6 filing move.
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
