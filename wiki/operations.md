---
title: Operations Runbook
section: Operations
last-verified: 2026-08-23
verified-against: 1790554
sources: [docs/11-gpu-pipeline-revamp.md, docs/17-remote-access-runbook.md, docs/20-file-portal-manual.md, docs/38-file-portal-full-system-scope.md, windows-converter/convert_and_ship.py, windows-converter/watch_and_convert.py, windows-converter/events.py, windows-converter/analyst.py, windows-widget/src-tauri/src/watcher.rs, windows-widget/src-tauri/src/preflight.rs, windows-widget/src-tauri/src/assay.rs, windows-widget/src-tauri/src/bench.rs, windows-widget/src-tauri/src/chat.rs, windows-widget/src-tauri/src/main.rs, windows-widget/src-tauri/src/events.rs, windows-widget/src/main.js, windows-widget/package.json, linux-converter/systemd/, linux-receiver/systemd/, linux-converter/converter/main.py, .claude/launch.json, .github/workflows/ci.yml, CLAUDE_README.md, SYMPTOM-INDEX.md, OPEN-TASKS.md, sessions/S106-desktop-2026-08-20.md]
---

> **Summary.** File Portal runs on two machines joined by Tailscale: the Desktop (Win10,
> RTX 3080 10 GB — the GPU convert lane and the widget) and the ThinkPad (`rab@archlinux` —
> systemd services and the vault). The widget is the operator surface; it spawns and owns the
> watcher, the Bench server, and the chat server via a kill-on-close Job Object — but two
> click-launched GPU conversions (`--resume`, `--reanalyze`) are NOT adopted, so a force-kill
> leaves them on the card. There is exactly one OS-enforced lock (the card mutex); everything
> else is a file-signal convention. The event stream's writer swallows all exceptions, so
> silence proves nothing. pytest and ruff are not installed on the Desktop — the Linux lanes
> are only verifiable in CI or on the ThinkPad.

## 1. The two machines, and how they meet

- **Desktop** — `bndit@DESKTOP-BNDIT`, Win10, RTX 3080 10 GB, 16 GB RAM (docs/20:342).
  Runs the widget, the drop-folder watcher, and every GPU convert. The card fits Marker
  (~5 GB peak) OR an 8B q4 model — never both at once (docs/11:12). A long clean book can
  reach 9.8/10.2 GB VRAM at recognition batch 16; use 8 for headroom (docs/20:346-347).
- **ThinkPad** — `rab@archlinux`, Arch, tailnet 100.107.238.61 (docs/20:354). Runs the
  allocator and converter systemd services and holds the bare vault `~/file-portal/vault.git`.
- **Between them**: everything rides Tailscale — `tailscale ssh` is the known_hosts-proof
  transport (docs/20:364; the ship hop uses it at convert_and_ship.py:1050). "Using my
  desktop from the ThinkPad" means a Sunshine→Moonlight stream of the real Desktop session
  (docs/17:32, docs/17:156). Gate 5 (pairing + in-home stream) is done 2026-07-31;
  out-of-home is PENDING in the runbook (docs/17:355).

## 2. Starting things

**Widget.** Production: the installed exe `%LOCALAPPDATA%\File Portal\file-portal-widget.exe`
(present, 10,205,696 bytes, mtime 2026-08-20 — `ls -la` 2026-08-23), adopted only by Rab's
hands per the MSIX ghost laws (docs/20:351-352). Development: `npm run dev` in
`windows-widget/` (`"dev": "tauri dev"`, windows-widget/package.json:8). At boot the widget
fires `init()` without awaiting it and launches its polling loops in one burst —
`watcherAutostart()` (main.js:1070) spawns the watcher before the UI is populated
(main.js:1064-1077).

**windows-converter CLIs.** `grep -l __main__ *.py` in `windows-converter/` returns exactly
8 files (run 2026-08-23): six operator entry points and two selftests.

| Entry point | One line |
|---|---|
| `watch_and_convert.py` | The conveyor: polls `drop/` every 5 s (`POLL_S = 5`, :44), waits for file-size stability (up to 120 s, :58), runs one conversion at a time (6 h backstop, :166), failures land in `drop/failed/` (:36, :177-179) |
| `convert_and_ship.py` | The spine: probe → route → Marker → bundle → anchor → ship; also `--resume` and `--reanalyze` |
| `fidelity_audit.py` | Survival-audit scorer for a converted bundle |
| `backend_parity.py` | Local-vs-Gemini analyst parity measurement |
| `figure_coverage.py` | P-1 figure-coverage report (report-only, unwired) |
| `room_chat.py` | The Room assistant server (spawned by the widget, chat.rs:69) |
| selftests | `figure_coverage_selftest.py`, `deferral_gate_selftest.py` — do NOT run the latter casually; it exercises the live gate machinery |

**ThinkPad systemd units** (`systemctl --user`; deploy = `cd ~/file-portal-src && git pull
&& systemctl --user restart file-portal-converter`, docs/20:361-362):

- `file-portal-allocator.service` (linux-receiver/systemd/) — sorts widget arrivals;
  Type=notify, WatchdogSec=90.
- `file-portal-converter.service` (linux-converter/systemd/) — CPU converts AND the vault
  exporter: `ExportHandler` watches `staging/` from inside this service
  (linux-converter/converter/main.py:305). `READY=1` fires only after the startup sweep
  (:315); `WATCHDOG=1` heartbeats only while the observer thread is alive (:328) — a hung
  conversion subprocess is explicitly NOT covered.
- `file-portal-vault-fixity.service` + `.timer` — weekly `git fsck` over the bare vault;
  `Persistent=true` so a slept-through week fires on next boot (the .timer file).

**Servers and ports.** Bench: one `bench.py` per held bundle on 7077–7096, first free port
proven by binding (bench.rs:82). Chat UI: 7100–7109 (chat.rs:47-49); room_chat's llama child
uses 7110–7119 (chat.rs:43-44). `.claude/launch.json` adds repair-bench @7077,
room-harness @7080, docs @8321 — but its `room-chat` config still points at
`prototypes/room-chat/chat.py`, which no longer exists (`ls prototypes/room-chat/` =
README.md + `__pycache__` only; the live server is `windows-converter/room_chat.py`).

## 3. The background inventory — what runs, who owns its death

The widget creates one process-wide Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`
(watcher.rs:35-41); `adopt_into_job` is best-effort (watcher.rs:57). Census, run 2026-08-23:
3 of the 10 `.spawn()` sites in `windows-widget/src-tauri/src/*.rs` adopt their child.

| Process | Spawned by | Job-adopted? | On widget force-kill |
|---|---|---|---|
| `watch_and_convert.py` | watcher.rs:157 | yes (:160) | dies with the widget |
| `bench.py` server | bench.rs:149 | yes (:151) | dies |
| `room_chat.py` server | chat.rs:113 | yes (:115) | dies (its stale `chat-hold.json` is reaped by pid-liveness, chat.rs:18-20) |
| `convert_and_ship.py --resume` | preflight.rs:97 | **NO** | **keeps converting on the GPU** |
| `convert_and_ship.py --reanalyze` | assay.rs:318 | **NO** | **keeps running** |
| llama-server (grandchild of room_chat) | room_chat.py | see OPEN-TASKS B25 | contested — B25 says a hard kill orphans it |

The remaining spawn sites (line.rs:255/260/380/390 — reader/notepad/explorer opens;
transfer.rs:147 — a per-transfer `tailscale ssh`) are short-lived, not background. A watcher
started by any OTHER runtime is outside the Job Object entirely — SYM-047.

## 4. The locks

| Lock | Kind | Reality |
|---|---|---|
| `Local\file-portal-card` | OS-enforced named mutex | The ONLY real mutual exclusion. Every converter entry acquires it (convert_and_ship.py:203, :214); waits loudly at 30 s polls (:221-224). Fails OPEN: if `CreateMutexW` itself fails it prints "proceeding UNGUARDED" and continues (:214-219) |
| `.gpu-lock` | write-only busy signal | Not a lock — nothing gates on it (SYM-032). Written watch_and_convert.py:159, deleted :168; voluntary readers refuse or display (assay.rs:303, line.rs:33, room.rs:397, backend_parity.py:265) |
| `chat-hold.json` | real gate, file-based | The signed watcher deferral gate: the conveyor refuses to START a convert while the assistant holds the card (watch_and_convert.py:105-118, docs/33 §2.3). Stale holds from dead pids are reaped mechanically |
| single-instance | Tauri plugin | A relaunch restores and fronts the existing window — unminimize, show, focus (main.rs:617-627) — never a twin |
| `.done` slice gates | identity-gated resume | A finished slice is re-admitted only if `source_sha256`, engine args and Marker version all match; recognition **batch is deliberately NOT identity** — it is a performance knob (convert_and_ship.py:752-758, :803-812) |

## 5. The product clock — events.jsonl

`C:\Users\Bndit\ml\library\events.jsonl` (path: events.py:14, `FP_PIPELINE` overridable).
Measured 2026-08-23: **137 lines; newest `ts` 2026-08-14T03:32:13+00:00** (`wc -l` +
`tail -1`) — nine days of silence at measurement time. Read that silence correctly: the
writer is best-effort by design, `except Exception: pass` (events.py:18, :43), and the
widget's reader skips unparseable lines (events.rs:23-25). **Absence of events proves
nothing about absence of work** — a stage that stopped emitting is indistinguishable from a
stage that stopped running. The file has no rotation; the reader re-reads it whole per poll.

## 6. Resume after a crash — what survives, what is lost

- **Survives:** finished slices of a CHUNKED convert — slice work lives outside the run's
  temp dir, `.done` is written by atomic staging-rename, and resume re-admits only on the
  three-field identity match (convert_and_ship.py:752-758, :803-812). Finished analyst
  chunks — journalled to `chunks.jsonl` with fsync per chunk (analyst.py:267-274, :297-298).
  Any conversion that reached the anchor: the bundle is copied to `anchor/` unconditionally
  BEFORE defer/hold/ship (convert_and_ship.py:1330-1333), so a dead ThinkPad costs a
  re-ship, not GPU hours.
- **Lost:** everything of a book UNDER the chunk threshold (600 clean / 400 scan pages,
  convert_and_ship.py:170) — the whole run lives inside `tempfile.TemporaryDirectory`
  (:1326). A failed ship moves the PDF to `drop/failed/` and nothing automatically re-ships
  the already-anchored bundle (watch_and_convert.py:177-179) — recovery is manual.

## 7. Operator hazard digest

1. A bare `glass_detector.py` run exits 0 while listing glitches — the only honest form is
   `--since <pin> --enforce` (SYM-046).
2. `.gpu-lock` is not a lock; converter-vs-converter exclusion is the card mutex alone (SYM-032).
3. Force-killing the widget orphans `--resume`/`--reanalyze` GPU runs (§3; nearest register
   rows: OPEN-TASKS B9, B25).
4. Never convert while the little brother games — the seat is his (docs/20:346-347).
5. `--force_ocr` at defaults thrashes the 10 GB card (27+ min, no output) — ruled out (docs/11:86).
6. Preview-pane mirage: the Claude app auto-opens `index.html` as a static snapshot — a
   "broken widget" screenshot may be the mirage (CLAUDE_README.md:1877).
7. Stale-env: Explorer shortcut launches inherit the LOGIN-time PATH; the widget hydrates
   from the registry at boot — verify config from the boot log, not the writing surface
   (CLAUDE_README.md:1877, ledger row :1157).
8. Non-UTF-8 lever-file saves (ANSI/UTF-16) once made `levers()` raise; decode is BOM-first
   now, but name every non-UTF-8 read (sessions/S106-desktop-2026-08-20.md:260).
9. The two clocks (ledger row + tally) must agree at session open — disagreement means a
   rewind, fork, or blind session (docs/38:839, :1235).
10. events.jsonl silence is not idleness — the writer swallows exceptions (events.py:43, §5).

## 8. Local toolchain reality — what you can verify on the Desktop

Measured 2026-08-23: `which pytest` and `which ruff` both return nothing on the Desktop
(positive control: the same probe finds `cargo`, `node`, `npm`), and
`C:\Users\Bndit\ml\marker-env\Scripts\` (54 entries: python.exe/pythonw.exe, the marker
tooling, misc console scripts) carries no pytest and no ruff. Consequences:

- **CAN verify locally:** `cargo fmt --check` / `clippy` / `cargo test` (widget);
  `node windows-widget/p0-asset-ledger.test.mjs`; the windows-converter selftests under the
  marker-env python; the glass detector.
- **CANNOT verify locally:** ruff + pytest for the three Linux lanes — those run only in CI
  (.github/workflows/ci.yml: working-directories are linux-receiver, linux-dashboard,
  linux-converter, windows-widget/src-tauri; nothing else) or on the ThinkPad itself.
- `gh` is unauthenticated here — never claim CI's current colour; observe it in the browser
  after a push. Note the inversion: CI covers zero of windows-converter, the live GPU lane.

## Open items

- OPEN-TASKS §B: B9 (watcher pid/parent file for the SYM-047 class, OPEN-TASKS.md:152),
  B25 (llama-server Job-Object adoption, OPEN-TASKS.md:186).
- SYMPTOM-INDEX: SYM-032 (.gpu-lock), SYM-046 (bare glass run), SYM-047 (orphan watcher).
- Unregistered as of 2026-08-23: the un-adopted `--resume`/`--reanalyze` spawns (§3) and the
  stale `room-chat` entry in `.claude/launch.json` (§2) appear in no OPEN-TASKS row.
- docs/17:355 — Gate 5 out-of-home formal done-when still pending in the runbook.
