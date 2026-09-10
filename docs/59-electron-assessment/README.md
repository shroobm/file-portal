# docs/59 — Electron for the widget? An assessment with a measured inventory (S126, 2026-09-10)

**Rab's words (S126 §1):** *"think if we should soon migrate onto making an electron based application to renovate
file portal tauri and widget? See how you could mirror all of file-portal in electron if its possible."*

This is an assessment, not a migration. Nothing in the widget was touched to write it. Every number below was
measured on this machine this session, with the command that produced it; a figure that was NOT measured here
says so. The recommendation is at §7; the mirror map — *how* it could be done — is §4 and §8.

## §0 The one-paragraph answer

Everything the widget does can be mirrored in Electron; nothing is impossible. But the migration would be a
**rewrite of 5,292 lines of Rust into ~4–5 k lines of TypeScript** and a re-proving of every guarantee those lines
paid for — while the part of the widget that Rab actually sees and I actually iterate on (the 3,186-line JS/CSS
front end) runs on **Chromium either way** and ports nearly verbatim. Of the widget's ten symptom rows that mention
the Rust side, seven are behaviours (two instances, a window close killing the watcher, pause-vs-stop) that would
recur identically in Electron; three are toolchain friction (`cargo fmt`, `LNK1104`, the adoption ritual). One
hard guarantee — **no orphaned watcher, ever** (S37: a Windows Job Object with kill-on-close) — has no Node API
and would need a native addon or a helper executable, i.e. a compiled toolchain again. And the runtime footprint
argument cuts the other way from intuition: the Tauri exe is 10 MB on disk, but its WebView2 tree is **379 MB
resident right now** — Electron's Chromium would be of the same order. **Not soon.** The conditions under which it
becomes right, and the cheaper renovations that address the real friction, are §7.

## §1 What the widget IS today (measured 2026-09-10, S126)

| Surface | Measured | Command |
|---|---|---|
| Rust (Tauri backend) | **5,292 lines / 15 modules** | `wc -l windows-widget/src-tauri/src/*.rs` |
| Front end (JS/CSS/HTML) | **3,186 lines**: `main.js` 1,161 · `room.js` 1,045 · `styles.css` 842 · `event-vocab.js` 84 · `index.html` 54 | `wc -l windows-widget/src/*` |
| IPC surface | **42 `#[tauri::command]`** handlers, all in `main.rs` | `grep -c '#\[tauri::command\]'` |
| Tests | **36 `#[test]`** (Rust); no JS test files in the tree | `grep -c '#\[test\]'`; `ls windows-widget/tests` |
| Crates | tauri 2, `tauri-plugin-single-instance` 2, serde/serde_json, toml, `windows-sys` 0.61 (Foundation, Security, **JobObjects**, Threading) — **481 crates** in `Cargo.lock` | `Cargo.toml`; `grep -c '^name = ' Cargo.lock` |
| Win32 calls | `Win32::System::JobObjects` (the S37 job), `Win32::System::Threading` ×2, `Win32::Foundation` ×2 | `grep -o 'Win32::[A-Za-z:]+'` |
| Window | one, **480×224, undecorated, transparent, always-on-top**; no tray | `tauri.conf.json` |
| CSP | `default-src 'none'; script-src 'self'; style-src 'self'; style-src-attr 'unsafe-inline'; connect-src ipc: …` (S94) | `tauri.conf.json` |
| Bundle | `msi` + `nsis`; identifier `dev.fileportal.widget` | `tauri.conf.json` |
| Installed exe | **10,335,232 bytes** (9.9 MiB), `C4559805`, at `AppData\Local\File Portal\file-portal-widget.exe` | `ls -l` |
| Runtime memory, right now | widget exe **26 MB** working set (10 MB private) · its WebView2 tree **6 processes, 379 MB** · **total 405 MB** · the Python watcher 3 MB | `Get-Process` + `Win32_Process` parent filter (PowerShell) |
| WebView2 runtime | **152.0.4191.66**, the shared Edge runtime under `Program Files (x86)\Microsoft\EdgeWebView` — updated by Windows, not by us | `ls` |
| Outward reach | spawns `gpu_python` (5 sites), `tailscale` (3), `taskkill` (2), `scp`, `git`, `reg`, `nvidia-smi`, `explorer.exe`, `cmd`; **4 `TcpStream` + 4 `http://`** sites (the loopback TOKEN routes, S108; Ollama) | `grep -o 'Command::new(…)'` |
| Node on this machine | **v24.18.0**, npm 11.16.0 (present, unused by the widget) | `node --version` |

**The Rust modules and what each one paid for** (lines): `assay.rs` 799 (the fidelity assay + the **bless** over
ssh, docs/18 §5.4) · `main.rs` 747 (the 42 commands, config, the single-instance plugin, OK-14 forward-instead-of-die)
· `line.rs` 724 (the algedonic line: events → chips, docs/30) · `algedonic.rs` 606 · `room.rs` 458 (the Room's
projection, docs/13/16) · `watcher.rs` 405 (**S37: the Job Object; supervised spawn, SYM-047 class; stop vs pause**)
· `bench.rs` 394 (the Repair Bench window) · `chat.rs` 229 · `transfer.rs` 168 (scp/ship) · `config.rs` 164 (toml,
levers) · `receipts.rs` 163 (tailing the ThinkPad's receipts) · `vault.rs` 151 (git; `CREATE_NO_WINDOW`) ·
`preflight.rs` 106 · `status.rs` 96 · `events.rs` 82 (the `events.jsonl` tail).

## §2 The guarantees any mirror must keep (each paid for in blood; the register rows)

1. **No orphans, ever (S37, `watcher.rs`).** The watcher — and by inheritance every Marker convert it spawns — is
   assigned to a Windows Job Object with `KILL_ON_JOB_CLOSE`; the widget holds the only handle, so a clean close, a
   force-kill or a crash all tear the whole tree down. Before it, orphan watchers thrashed the GPU (S36).
2. **One widget (SYM-033, `tauri-plugin-single-instance`).** A second launch fronts the running instance and
   forwards its open request (OK-14, Rab-signed 2026-08-31) instead of becoming a second factory.
3. **The projection law (docs/19 §0.2).** The widget READS; Python owns pipeline truth in single-writer files.
4. **⏻ pauses intake, only EXIT tears down** (`watcher.rs`; SYM-068/069 are the rows where that line was learned).
5. **Supervised spawns** (SYM-047 class): every child of the widget is adopted into the job.
6. **BatchMode ssh/scp** (docs/19 §0.6): windowless processes hang forever at an invisible host-key prompt.
7. **Kill process trees** (docs/19 §0.7): a single-pid kill leaves the launcher's real python holding the GPU.
8. **The CSP** (S94) and the loopback TOKEN routes (S108: signing-executes on 14 routes).
9. **Boot resilience** (S87): the config is verified from the widget's BOOT LOG, never the writing surface.
10. **Adoption is Rab's hand** (the MSIX ghost laws, docs/19 §0.3): build → SHA-8 → he copies and launches.
11. **The card mutex** `Local\file-portal-card` (S94) and the card's process probe by image name.

**What the registers say the Rust side has cost** (`grep -ci` over the registers, S126): rows mentioning `tauri`
6 SYM / 2 ERR, `cargo` 5 / 3, `clippy` 1 / 1, `MSIX` 2 / 0, `LNK1104` 1 / 0; closeouts mentioning `cargo` 40 and
`clippy` 38 times. Read by id, the ten SYM rows are **SYM-007** (a virtualized write — the MSIX ghost), **-018** (CI
missing), **-020** (`cargo fmt` red across 8 files), **-023** (the Bench window's close killed the watcher),
**-024**, **-033** (two widgets), **-051** (the session closes itself), **-068** (pause vs stop), **-069** (main
window close vs Bench/Chat), **-109** (`LNK1104` under a long path). **Seven of the ten are behaviours that any
framework would have had to learn; three are the toolchain.** The friction Rab feels is real but mostly not Tauri's.

## §3 What the two runtimes actually are on this machine

| | Tauri 2 (today) | Electron |
|---|---|---|
| Renderer | **WebView2 = Chromium** (Edge's runtime, 152.0.x, updated by Windows) | **Chromium, bundled** with the app (pinned per Electron version) |
| Backend language | Rust (5,292 lines here) | Node.js (TypeScript/JavaScript) in the main process |
| IPC | `invoke("cmd")` → `#[tauri::command]`; capability-scoped | `ipcRenderer.invoke` → `ipcMain.handle`, through a **preload** with `contextIsolation` |
| Disk | **10 MB** exe + the shared runtime | **~150–250 MB** unpacked (Chromium + Node ship inside) — *typical figure, NOT measured here* |
| Memory | widget 26 MB + WebView2 tree **379 MB = 405 MB measured** | a Chromium tree of the same order + Node main (~30–80 MB) — *typical, NOT measured here*; **not a discriminator** |
| Native APIs | `windows-sys` in-process (the Job Object is 30 lines) | none for Job Objects: a **native addon** (N-API, node-gyp → MSVC) or a **helper exe** |
| Single instance | plugin | `app.requestSingleInstanceLock()` + `second-instance` event (argv forwarded) — first-class |
| Undecorated / transparent / always-on-top | yes | `BrowserWindow({frame:false, transparent:true, alwaysOnTop:true})` — first-class |
| Spawning python/ssh/scp/tailscale | `std::process::Command` + `CREATE_NO_WINDOW` | `child_process.spawn` + `windowsHide: true` — first-class |
| Loopback HTTP / TCP | `TcpStream` by hand | `http`/`net` modules — easier |
| Tests | `cargo test` (36) | vitest/jest — the Rust tests would be rewritten |
| Build ritual | `cargo fmt --check` → `clippy -D warnings` → `cargo test` → `tauri build` (minutes; `LNK1104` under long paths) | `tsc` → `eslint`/`prettier` → `electron-builder` (seconds to a minute; **node-gyp brings MSVC back if an addon is needed**) |
| Packaging | msi + nsis, one exe to copy by hand | nsis/msi/**portable** (a self-extracting exe — hashable, slower first start); the app is a *directory* (`electron.exe` + `resources/app.asar` + dlls) |
| Security posture | the Rust boundary + capabilities + CSP | `nodeIntegration:false`, `contextIsolation:true`, a preload allowlist, CSP — equivalent **when done right**; a larger surface if not |
| Ecosystem / tooling familiarity | smaller; Rust | npm; more AI-tool and hiring familiarity; DevTools identical (both Chromium) |

## §4 The mirror map — every concern in the widget, and its Electron equivalent

| Concern (where it lives today) | Electron mirror | Cleanly? |
|---|---|---|
| The 42 commands (`main.rs`) | 42 `ipcMain.handle` entries grouped by module; the preload exposes `window.fp.invoke(name, args)` | yes — mechanical |
| `main.js` / `room.js` / `styles.css` / `index.html` (3,186 lines) | the same files; a ~30-line shim replaces `@tauri-apps/api`'s `invoke`/`listen` with the preload bridge | **yes — near-verbatim** (same Chromium) |
| Window: 480×224, no frame, transparent, always-on-top; minimize/restore (S94) | `BrowserWindow` options; `win.minimize()/restore()` | yes |
| Single instance + argv forwarding (SYM-033, OK-14) | `requestSingleInstanceLock` + `second-instance` | yes |
| **Job Object kill-on-close (S37)** | none in Node. (a) a native addon (~80 lines C++ over `CreateJobObject`/`AssignProcessToJobObject`, built with node-gyp = MSVC, prebuilt binaries possible); (b) a **tiny helper exe** (Rust or C, ~60 lines) that creates the job, spawns the watcher into it, and holds the handle — the widget spawns the helper; helper death = job death; (c) a soft design: the watcher polls the widget's pid and exits when it is gone (SYM-023's shape — a dead parent noticed late; converts in flight survive the gap) | **no — the hard one.** (a)/(b) keep a compiled toolchain; (c) weakens a guarantee paid for by S36's GPU thrash |
| Supervised spawn / adoption into the job (SYM-047 class) | the same helper, or `spawn` + tracking pids and `taskkill /T /F` on exit (a crash of the widget still leaks) | partial without (a)/(b) |
| ⏻ pause vs exit (`watcher.rs`) | the same state machine in TS | yes |
| `events.jsonl` tail (`events.rs`) | `fs.watch` + a readline tail | yes |
| Config in toml (`config.rs`) | `@iarna/toml` or `smol-toml` | yes |
| Spawning python / ssh / scp / tailscale / taskkill / nvidia-smi / reg (`assay`, `transfer`, `vault`, `preflight`) | `child_process.spawn` with `windowsHide` and BatchMode flags carried verbatim | yes |
| Loopback TOKEN routes (S108) + Ollama calls (`chat.rs`) | `http.createServer` / `fetch` | yes — simpler |
| Receipts tail over ssh (`receipts.rs`) | spawn ssh, stream stdout | yes |
| The Repair Bench and Chat windows (`bench.rs`, `chat.rs`) | additional `BrowserWindow`s; SYM-023/069's close semantics re-implemented and re-tested | yes, with the same lessons to relearn |
| CSP (S94) | `session.defaultSession.webRequest.onHeadersReceived` or a `<meta>` CSP; plus `contextIsolation` | yes |
| The card's probe (`open.sh`: image name `file-portal-widget.exe`) and the J57 task (the exe path) | set `executableName`; the task's action path changes; the card's probe changes | yes — small, but every session tool that names the exe moves |
| Adoption ritual (docs/19 §0.3: one exe, SHA-8, copied by hand) | a portable single-exe target keeps the ritual; an installer changes it (hash the asar + launcher) | yes, with a choice |
| 36 Rust tests | rewritten as vitest suites over the TS modules | a rewrite |
| Levers and lever-waivers (`close.sh` LEVERS gate reads Python/Rust/JS `NAME = <number>`) | the gate already reads JS | yes |

## §5 What Electron would buy, honestly

- **One language for main + renderer** (the pipeline stays Python either way; the Rust would be gone).
- **No `cargo` ritual**: `cargo fmt --check` (SYM-020), `clippy -D warnings`, the minutes-long builds, and `LNK1104`
  under a long worktree path (SYM-109) disappear — replaced by `tsc`/`eslint` in seconds (the number of gates stays
  the same; the wait does not).
- **Main-process changes need no compile step** — the Rust side is where iteration is slow today; the UI side is
  already JS.
- **npm** for the odd need (toml, a tray later, auto-update) and more familiarity for whoever comes next.
- A **chat/bench UI that grows** (docs/14, the remote-dispatch vision) is more at home in a full app than in a
  480×224 always-on-top pane.

## §6 What it would cost, honestly

- **A rewrite, not a port:** 5,292 lines of Rust → ~4–5 k lines of TypeScript, and the 36 tests again; every
  guarantee in §2 re-proved on the live machine (the register rows are the acceptance list).
- **The Job Object.** The one guarantee with no Node equivalent. A native addon or a helper exe means the compiled
  toolchain does not leave the project; a soft design means accepting orphan windows S36 already paid for.
- **Disk and the adoption ritual:** a 10 MB single exe becomes a ~200 MB directory (typical, not measured); the
  "one file, one hash, one copy" ritual needs a portable target or a new form.
- **A second runtime to keep current:** WebView2 is updated by Windows; a bundled Chromium is updated by us
  (Electron's cadence is a release every ~8 weeks with security backports), and the CSP/contextIsolation discipline
  is ours to keep.
- **Every session tool that names the exe** (the card, the J57 task, `installed-exe-state`, close.sh's RUST gate)
  moves with it.
- **The behaviours in the ten rows** would be relearned — SYM-023/033/068/069 are about windows, children and
  lifetimes, not about Rust.

## §7 Recommendation — not soon; and what to do instead

**Not soon.** The measured friction is mostly the build ritual and the adoption ritual, and the runtime footprint is
not the win it looks like (405 MB resident today, Chromium either way). A migration would spend weeks re-proving
guarantees the registers already hold, to arrive at the same front end on the same renderer.

**It becomes the right move if any of these come true — Rab's call, each:**
1. The widget's scope grows into the remote-dispatch client (docs/14) with multi-window UI, chat, and a bench that
   people other than Rab use — a full app, where Electron's shape fits and its size is irrelevant.
2. A Job Object addon can be adopted as a **prebuilt** binary (no per-machine MSVC), or Rab accepts the helper-exe
   design as the last compiled piece.
3. Rab wants a single-language codebase more than the 10 MB single-exe adoption ritual.

**Cheaper renovations that address the actual friction, in Tauri 2, now:**
- **A CI build of the widget** that publishes the artifact + its SHA-8 on every push (adoption stays Rab's hand;
  the *build* stops being the session's; `LNK1104` and the minutes go to the runner).
- **A `just`/script for the rebuild ritual** (`fmt --check → clippy → test → build → print SHA-8`) so the ritual
  is one command and its order cannot be skipped (SYM-020's shape).
- **Keep moving projection logic to the JS side** where the projection law already puts it (`line.rs`/`room.rs`
  render shapes that could live in `room.js`); the Rust shrinks toward its irreducible core: the job, the spawns,
  the loopback, the config.
- **Write the JS tests** the tree does not have (the 3,186 lines have no test file in this repo).

## §8 If it is ever done — the mirror sketch (so the question "how" has an answer on file)

```
electron/
  main.ts          app lifecycle; requestSingleInstanceLock + second-instance (OK-14 forwarding);
                   BrowserWindow(480×224, frame:false, transparent, alwaysOnTop); CSP; the 42 ipcMain.handle
  preload.ts       contextBridge.exposeInMainWorld("fp", { invoke, on })   ← the only bridge
  modules/
    watcher.ts     the state machine of watcher.rs (pause vs exit); spawns jobhelper
    jobhelper/     the ONE compiled piece: a ~60-line Rust or C exe that creates the Job Object with
                   KILL_ON_JOB_CLOSE, spawns the watcher into it, holds the handle (S37 kept, not softened)
    events.ts      events.jsonl tail            config.ts   toml + levers      vault.ts   git (spawn)
    assay.ts       fidelity + bless over ssh    transfer.ts scp                receipts.ts ssh tail
    line.ts/room.ts the projections that are not already in room.js            loopback.ts the TOKEN routes
  renderer/        = windows-widget/src/ unchanged, with tauri-shim.js replacing @tauri-apps/api
  tests/           vitest over modules/; the 36 Rust cases as the acceptance list
  build            electron-builder: nsis + portable (single exe for the SHA-8 ritual); executableName file-portal-widget
```

Order, if ever: (1) `jobhelper` first, live-proved by the S36 probe (force-kill the widget; every python must die);
(2) the preload + shim, so the existing renderer runs unchanged against a stub main; (3) modules in the order of
their tests; (4) the card, the J57 task and `installed-exe-state` renamed in the same commit as the first adoption.

## §9 Provenance and residue

Measured by hand this session (S126, 2026-09-10) on the Desktop: the commands are in §1. Single-lane (the Codex lane
is away by Rab's word). Electron's disk and memory figures are **typical, not measured here** — an Electron build of
this widget was not made; the claim that its footprint is "of the same order" rests on both runtimes being Chromium
and on the measured 379 MB WebView2 tree, not on a side-by-side. The Rust-line-to-TypeScript-line ratio (~1:0.8–1.0)
is an estimate. The S36 GPU-thrash incident and the S37 fix are `Historical` (their rows and closeouts). Whether Rab
wants a single language is his to say; this document names the conditions and does not decide them.
