---
title: Control Room (Widget)
section: Product
last-verified: 2026-08-23
verified-against: 1790554
sources: [windows-widget/src-tauri/src/main.rs, windows-widget/src-tauri/src/bench.rs, windows-widget/src-tauri/src/chat.rs, windows-widget/src-tauri/src/watcher.rs, windows-widget/src-tauri/src/preflight.rs, windows-widget/src-tauri/src/assay.rs, windows-widget/src-tauri/src/line.rs, windows-widget/src-tauri/src/config.rs, windows-widget/src/main.js, windows-widget/src/room.js, windows-widget/src/index.html, windows-widget/src/styles.css, windows-widget/src-tauri/tauri.conf.json, windows-widget/src-tauri/capabilities/default.json, .claude/skills/muster/open.sh, SYMPTOM-INDEX.md, OPEN-TASKS.md]
---

**The Control Room is the operator's Tauri v2 desktop app (`windows-widget/`): one frameless,
always-on-top webview hosting the portal tiles and three switchable surfaces (Dock / Room /
Wall), plus two surfaces that are deliberately NOT in that webview — the Repair Bench and the
Assistant each open as a separate window pointed at a local Python HTTP server the widget
spawns and supervises. The entire IPC surface is 42 commands in one 696-line `main.rs` with
zero tests; boot fires nine loop/init calls in one synchronous burst beside an un-awaited
`init()`, spawning the watcher process before the first render; process death is governed by a single kill-on-close Job
Object that only 3 of the 10 spawn sites adopt into — the two click-launched GPU conversions
do not. The frontend is four framework-free files, effectively untested. Design briefs:
docs/13 (control-room design), docs/16 (the Room face).**

## Surfaces: one webview, plus two external windows

The main window (480×224, `decorations:false`, `alwaysOnTop:true`, `transparent:true` —
windows-widget/src-tauri/tauri.conf.json) loads `src/index.html`. Portal tiles render from
`invoke("list_portals")` inside `init()` (windows-widget/src/main.js:78-80, renderer at :56).
Three in-webview surfaces switch via the `data-surface` buttons Dock / Room / Wall
(windows-widget/src/index.html:13-15); `room.js` renders both Room and Wall densities
(surface flag at windows-widget/src/room.js:36, `renderWall` at :918).

Two more buttons open **separate windows**, not surfaces:

- **Bench** (index.html:16 → main.js:1061): `bench.rs` spawns the quarantined prototype
  server `prototypes/repair-bench/bench.py` (path built at
  windows-widget/src-tauri/src/bench.rs:93-95, spawn :149, Job-Object adoption :151), waits
  for readiness, then builds a window labeled `repair-bench` with
  `tauri::WebviewUrl::External` (bench.rs:199-202). The main.js status line names the
  transport: "Repair Bench up on 127.0.0.1:${port}" (main.js:1056).
- **Assistant** (index.html:18, `hidden` until configured → main.js:1062): `chat.rs` spawns
  `windows-converter/room_chat.py` (windows-widget/src-tauri/src/chat.rs:69, spawn :113,
  adoption :115) and opens window `room-chat` via `WebviewUrl::External` (chat.rs:196-199).

Consequence: the app's only capability grant names `"windows": ["main"]`
(windows-widget/src-tauri/capabilities/default.json — the sole file in `capabilities/`), so
the Tauri IPC permission set never reaches the Bench or Assistant windows; and the CSP in
tauri.conf.json (`default-src 'none'; script-src 'self'; …`) governs the bundled `../src`
assets, while the two external windows render whatever the local Python servers serve.

## Boot order

Rust side, in source order (windows-widget/src-tauri/src/main.rs):

1. `:610` `hydrate_env_from_registry()` — PATH + `GEMINI_API_KEY` from `HKCU\Environment`
   before anything else (key read at :602-605).
2. `:611` `config::load_or_init().expect("failed to load config")` — a malformed config
   kills the process before any window exists.
3. `:617` `tauri_plugin_single_instance` registered as the FIRST plugin (comment cites
   SYM-033); a second launch unminimizes + fronts the one instance (:623-626).
4. `:628-633` four managed state cells (AppState, WatcherState, BenchState, ChatState);
   `:634` the invoke_handler with all 42 commands.

JS side (windows-widget/src/main.js): `init()` is fired with only a `.catch` — **not
awaited** (:1064) — then nine loop/init calls run synchronously in one burst (:1068-1076):
`vaultLoop, pfLoop, watcherAutostart, watcherLoop, shiftLoop, assayLoop, algedonicLoop,
lineInit, initSizing`, closing with `dbg("boot: all loops launched")` (:1077).
`watcherAutostart()` (:1070) reaches `Command::new(gpu_python_exe)…spawn()` at
windows-widget/src-tauri/src/watcher.rs:157 — so an OS process can be converting before the
un-awaited `init()` has rendered a single portal tile.

## The IPC surface

- **42 of 42** `#[tauri::command]` fns live in main.rs; the other 14 `.rs` modules have 0
  (`grep -c '#\[tauri::command\]' windows-widget/src-tauri/src/*.rs`). main.rs is 696 lines
  (`wc -l`) with 0 `#[test]` (`grep -c '#\[test\]' …/main.rs`).
- **35 distinct** literal command names match `invoke("` across the 2 frontend JS files
  (`grep -ohE "invoke\(\s*[\"'][a-z_]+" windows-widget/src/*.js | sort -u | wc -l`). That is
  a lower bound on live commands: `room.js` defines `call(name, args)` forwarding to
  `invoke` and nulling errors (windows-widget/src/room.js:95-98), and gatherVM routes nine
  commands through it as `call("line_state")` etc. (room.js:110-114) — a naive
  `invoke("x")` grep misses every one of them. Dead-command hunts must chase both spellings.
- After chasing both spellings, two registered commands have **zero** frontend callers:
  `audit_mode_get` (main.rs:190, registered :650) and `chat_stop` (main.rs:390, registered
  :674) — `grep -rn 'audit_mode_get\|chat_stop' windows-widget/src/ windows-widget/*.mjs`
  returns nothing.
- Validation is per-command, in the topic modules: `reconvert` rejects any `source`
  containing `/`, `\`, or `:` because the manifest hands it a bare filename, never a path
  (windows-widget/src-tauri/src/assay.rs:220); `open_engineering`'s `match target` IS the
  allowlist — named engineering targets only, never an arbitrary path
  (windows-widget/src-tauri/src/line.rs:342, contract stated :332-334).

## Process supervision

One process-wide Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, created once and
never explicitly closed — it closes when the widget dies, killing the adopted tree
(windows-widget/src-tauri/src/watcher.rs:33-40; `adopt_into_job`, best-effort, at :57).

Census: **10** `.spawn()` sites in `src-tauri/src` (`grep -n '\.spawn()' *.rs`): assay.rs:318,
bench.rs:149, chat.rs:113, line.rs:255/:260/:380/:390, preflight.rs:97, transfer.rs:147,
watcher.rs:157. **3** adopt into the Job Object: the watcher (watcher.rs:160), the bench
server (bench.rs:151), the chat server (chat.rs:115). The line.rs and transfer.rs sites are
short-lived user actions. The two that matter and do NOT adopt are both full GPU conversions:

- `convert_and_ship.py --resume` (windows-widget/src-tauri/src/preflight.rs:88-97; stderr
  appends to `resume-stderr.log`, :80-85);
- `convert_and_ship.py --reanalyze` (windows-widget/src-tauri/src/assay.rs:310-318; stderr
  is `Stdio::null()` at :316; gated only on `.gpu-lock` absence at :303).

A force-killed widget leaves either one running on the card — the orphan class SYM-047
records for the watcher. The register covers the watcher (OPEN-TASKS.md §B B9, :152) and the
llama-server grandchild (§B B25, :186), but no item names these two spawns
(`grep -in 'adopt' OPEN-TASKS.md` hits only B25, D1, and prose).

## Config

Config lives at `dirs::config_dir()\file-portal\config.toml` — i.e.
`%APPDATA%\file-portal\config.toml` (windows-widget/src-tauri/src/config.rs:102-107).
`load_or_init` (:109) surfaces a parse error naming the file rather than silently writing
defaults over it; only a genuinely-absent file seeds first-run defaults (:122-125).

The standing rule (SYM-007, SYMPTOM-INDEX.md row at :25, 4 firings): an MSIX-packaged
session's writes to that path are silently virtualized — a mirage copy reads back as
success. **Verify config from the widget's boot log, never from the writing surface.** The
boot log is `widget-boot.log` in the GPU pipeline dir, written by the S22 debug channel
(windows-widget/src-tauri/src/main.rs:427) and by window-creation failures via `log_boot`
(bench.rs:216, file join at :241).

## Frontend reality

- Framework-free: `git ls-files windows-widget/src/` returns exactly **4** files —
  `index.html`, `main.js`, `room.js`, `styles.css`. No bundler:
  `build.frontendDist: "../src"` (tauri.conf.json); package.json scripts are only
  `tauri`/`dev`/`build`.
- `styles.css` carries **two token layers**: the S34 layer (`:root` at
  windows-widget/src/styles.css:4 — bg/surface/clay/ok/warn/flow tokens, with
  `[data-theme="light"]` at :16 and accent overrides :26-27) and the S73 "MASS layer"
  (`:root` at :33, docs/25 design tokens, motion via native `linear()` springs — comment
  :29-32).
- JS is untested: the lane's one test file, `windows-widget/p0-asset-ledger.test.mjs`, is
  wired to nothing — package.json has no test script, and
  `grep -in 'node\|mjs' .github/workflows/ci.yml` returns 0 hits.

## Installed exe adoption

The muster card measures the installed binary at every session open: open.sh names it
(`~/AppData/Local/File Portal/file-portal-widget.exe`, .claude/skills/muster/open.sh:25) and
prints the "installed exe" row as the first 8 hex chars of its sha256, annotated "adoption
is Rab's hand — docs/19 §0.3" (open.sh:238). Re-measured 2026-08-23:
`sha256sum "$HOME/AppData/Local/File Portal/file-portal-widget.exe" | cut -c1-8` →
**4DCB73E2**, matching the S102 adoption. Trust the card row at each open, not any prose
line — including this one.

## Open items

- OPEN-TASKS.md §B **B9** (:152) — watcher pid/parent file at boot; the SYM-047 guard.
- OPEN-TASKS.md §B **B25** (:186) — `llama_server_exe` config key + adopt the llama-server
  spawn into the Job Object.
- SYMPTOM-INDEX.md **SYM-047** — orphaned watcher outside any Job Object; the un-adopted
  `--resume`/`--reanalyze` spawns above are the same class and have no register row yet.
- SYMPTOM-INDEX.md **SYM-007** — config-write virtualization; the boot-log rule above.
- Dead IPC pair `audit_mode_get` / `chat_stop` — zero frontend callers; wire, delete, or
  disposition (no register row yet; measured on this page).
- Design briefs: docs/13, docs/16. Bench-window semantics (undo, render cost, zero tests on
  `bench.html`) belong to the Repair Bench's own page, not here.
