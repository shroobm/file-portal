# docs/16 — The Control Room becomes the widget's face (S34)

**Session:** Desktop S34 (2026-07-22), autonomous.
**Goal:** graduate the merged Claude-Design *Control Room* artifact into the live Tauri
widget's face — running with Claude off, on real pipeline data, no regressions.
**Method:** the vanilla *lift* (Claude Design's own recommendation, verified against the
bytes): lift the DC's **logic + tokens + markup**, drop its React runtime, and swap its
simulation for the widget's existing `invoke()` projections. No transpiler, no framework,
no build step added to the frontend.

This doc is both the **design record** and the **build audit**. Phases are measured — each
has an exit criterion recorded in §8.

---

## 1. Design principles (the laws the face must honor)

Carried from docs/13 (control-room design) + docs/15 (the Assay), made enforceable here:

1. **Projection principle.** All state lives on disk / in git. Python owns the schemas; the
   face *renders and requests*, never owns. → **Enforcement:** every panel reads from an
   `invoke()` command; the face writes nothing except through the existing intent-writing
   commands (`analyst_mode_set`, `audit_mode_set`, `rules_set`, `assay_reconvert`,
   `send_to_portal`, `watcher_*`, `vault_pull`). The pipeline (converter/formatter) is
   **never touched** — this is what makes an autonomous build safe.
2. **Terracotta `#D97757` means exactly one thing: your hand is required.** Nothing else
   pulses. → **Enforcement:** `--clay` is spent only on a pending gate decision and an audit
   `fail`; `pass`=`--ok` green, `flag`=`--warn` amber, running=neutral.
3. **One projection, many densities** (the merge's thesis). Dock (narrow), Room (wide ops),
   Wall (glanceable) are the *same* state at three densities. → **Enforcement:** a single
   view-model (`renderVals()` shape) feeds every surface; the surface switch changes layout,
   not data.
4. **Numbers live on the levers they inform** (docs/13). → the gate count sits on the gate
   station; survival on the ◎ station; ETA on convert.
5. **Boot resilience is non-negotiable** (S22/S29/S32 lessons): windowless spawns get
   `Stdio::null()`; env hydrated from registry; window autosizes from DOM `scrollHeight`,
   never an arithmetic model; every uncaught error lands in the status line + `widget-boot.log`.
   → the new face keeps `dbg()`, the error sinks, and `reflow()`.
6. **No regressions.** The currently-installed widget keeps working until Rab opts into the
   new build by running the new installer. The Dock stays the guaranteed-good default.

---

## 2. The source object (indexed)

The artifact `Control Room_ Opsroom & Widget Merged.zip` is a **Claude Artifacts publish
bundle** — a runtime harness that gunzips assets and mounts them into sandboxed iframes.
It is *not* editable source. Decoded, it contains:

| Asset | Bytes | What it is | Use to us |
|---|---|---|---|
| `react-dom.production.min.js` | 131 KB | bundled React DOM | **discard** — runtime substrate only |
| `react.production.min.js` | 10 KB | bundled React | **discard** |
| `dc-runtime` (`32cb761c`) | 66 KB | the Design-Component compiler (`parse/expr/compile/component.ts`) | **discard** — infrastructure |
| **template `<x-dc>` body** | 44 KB | **the actual UI**: declarative markup + `{{ }}` bindings + one `<script>` `class Component` (38 KB) + inline CSS tokens | **THIS is the source object** |

**The source object = the `<x-dc>` template**, staged in-repo for the build:

- `prototypes/control-panel/control-room/control-room.html` — the published bundle (reference render).
- `prototypes/control-panel/control-room/_source-object.template.html` — the decoded template (the real source).
- `prototypes/control-panel/control-room/DESIGN.md` — the merge's design record (§6 names the graduation seam).

Inside the source object, the **graduation seam is `renderVals()`** (`class Component`,
line ~392): it computes a complete view-model from `this.sim` (the simulation). Everything
the markup shows binds to `renderVals()`'s return. **Port = reproduce `renderVals()`'s output
shape from real `invoke()` data instead of `this.sim`.** The markup and tokens lift verbatim.

Key structures lifted from the source object:
- `SEGMENTS = [intake, convert, gate, assay, ship, vault]` — the six stations (1:1 with the pipeline).
- `MODE_LABELS/MODE_ORDER` — the gate cycle (matches `line.rs` MODES: ask/local/gemini/off; the DC calls gemini "cloud").
- The KPI set, convert panel, assay evidence card, gate cards, event stream, vault bar, portals — each mapped in §3.
- The token block (`--bg --surface-1/2 --elev --border --text/2/3 --clay --ok --warn --flow`, dark/light + clay/indigo/teal accents, the animations) — a **superset** of `windows-widget/src/styles.css`.

---

## 3. Integration check — every panel → real command (measured)

Legend: **REAL** = an existing `invoke()` command returns it today · **DERIVE** = computable
in-frontend from existing command output · **BACKEND+** = needs a new read-only projection
command (added this session in `room.rs`) · **DEFER** = needs pipeline/converter change,
out of scope (→ §9 higher-order goals).

### Stations
| Element | Source | Status |
|---|---|---|
| intake count / sub | `line_state.drop_waiting` / `watcher_status` | REAL |
| convert count / eta | `line_state.converting` / `.converting_eta_s` | REAL |
| convert live page X/Y | per-page progress | **DEFER** (converter emits none; ETA countdown stands in) |
| gate count / mode | `preflight_list.length` / `analyst_mode_get` | REAL |
| assay verdict / survival | `assay_status.verdict` / `.doc_survival` | REAL |
| ship / last shipped | `line_state.last_shipped.bundle` | REAL |
| vault count | Library/Inbox entry count | **BACKEND+** (`room_metrics.vault_count`) |

### KPI tiles
| Tile | Source | Status |
|---|---|---|
| Throughput pp/s | events (pages ÷ wall_s) | **BACKEND+** (`room_metrics.throughput`) |
| Median s/page | events (median of s_per_page) — `line.rs` already computes this for ETA | **BACKEND+** (`room_metrics.median_spp`) |
| GPU VRAM | live `nvidia-smi` | **BACKEND+** (`gpu_vram` cmd; null → "—" if absent) |
| Queue depth | `line_state.drop_waiting` + gate count | DERIVE |
| Survival avg | mean of all manifest verdicts | **BACKEND+** (`room_metrics.survival_avg`) |
| Uptime | watcher start → now | **BACKEND+** (`room_metrics.uptime_s`; watcher pid start) |

### Panels
| Panel | Source | Status |
|---|---|---|
| Convert panel (name/lane/eta/engine/batch) | `line_state` + static engine label | REAL (page%/vram → DEFER/BACKEND+) |
| Survival Audit card (verdict/survival/degeneration/zones/runs/held/mode) | `assay_status` | REAL (reuse existing `assayRender` logic) |
| Recent audits list | all-manifest scan | **BACKEND+** (`room_metrics.recent_audits`) |
| Gate cards (chunks/tokens/rec/etas) | `preflight_list` | REAL |
| Event stream | `shift_summary.tail` (last 10) | REAL |
| Vault bar | `vault_check` → state/bundles/behind | REAL |
| Portals | `list_portals` | REAL |
| Shift line | `shift_summary.today` | REAL |
| System/watcher/clock | `watcher_status` + local clock | REAL |

**Tally:** REAL/DERIVE covers ~70% of the surface with zero backend change. One new
read-only command `room_metrics` + one `gpu_vram` fill the KPI band and vault count — both
**pure projections** (read disk, own nothing), safe to add autonomously. One item
(**live convert page %**) is deferred: it needs the converter to emit per-page events, which
would touch the pipeline Rab relies on — out of scope for a Claude-off safe build.

Result: **0 unmapped panels.** ✅ (integration-check exit criterion met.)

---

## 4. Build plan (surfaces & files)

- `windows-widget/src/styles.css` — introduce the token layer (the source object's `:root`
  vars, dark/light + accents), refactor the Dock's hardcoded hexes to tokens, add Room styles.
- `windows-widget/src/index.html` — add the surface switch + the Room container.
- `windows-widget/src/main.js` — add the surface controller + the Room render + the
  `room_metrics`/`gpu_vram` wiring; keep every existing Dock loop intact.
- `windows-widget/src-tauri/src/room.rs` — NEW read-only module: `room_metrics` + `gpu_vram`.
- `windows-widget/src-tauri/src/main.rs` — register the two commands.

Verification order: mock browser harness (real-data snapshot) → `cargo clippy -D warnings`
→ `npm run tauri build` → launch release exe → desktop screenshot → pipeline-segment tests.

---

## 5. Scope boundary (what this session does NOT ship)

Deferred to the next major installment (§9), because each needs net-new backend that can't be
delivered safely blind:
- **Wall** surface (glanceable across-room projection) — layout only, low risk, but unverified;
  staged behind the surface switch, not wired.
- **Canvas transit belt** — the moving-package animation. Cosmetic; deferred to keep the
  first graduated face lean and certain.
- **Drill-down file explorer** (station → live tree) — needs new tree-read commands + Tauri
  event binding; DESIGN.md itself flags it "the graduation step, not prototype work."
- **Live convert page %** — needs converter per-page emission.

---

## 6. Build log — what shipped

Frontend (the lift, vanilla, no build step / framework added):
- `windows-widget/src/styles.css` — token layer (`:root` + dark/light + clay/indigo/teal),
  the surface switch, the whole Room stylesheet; Dock hexes left pixel-stable.
- `windows-widget/src/index.html` — the `Dock | Room` switch + `#room` container.
- `windows-widget/src/main.js` — `import ./room.js`; the surface controller (window resize,
  body class, poll start/stop). Every existing Dock loop untouched.
- `windows-widget/src/room.js` — NEW: the Room render, `renderVals()`'s shape rebuilt from
  live `invoke()` (line_state / assay_status / shift_summary / preflight_list / watcher_status
  / vault_check / room_metrics / gpu_vram / analyst_mode_get). Reuses the Dock's `.ac-*` assay
  classes (with token-scoped overrides for light-mode contrast).

Backend (two read-only projections, pipeline never touched):
- `windows-widget/src-tauri/src/room.rs` — NEW: `room_metrics` (throughput, median s/page,
  survival average, recent audits, vault count — from events.jsonl + anchor/pending/held
  manifests + the vault Library clone) and `gpu_vram` (live nvidia-smi; null when no probe).
- `windows-widget/src-tauri/src/main.rs` — `mod room;` + the two registered commands.

## 7. Verification — measured results

| # | Phase | Exit criterion | Result |
|---|---|---|---|
| 1 | Design principles | 6 laws → enforcement | ✅ §1 |
| 2 | Integration check | 0 unmapped panels | ✅ §3 — ~70% REAL/DERIVE, 5 filled by `room_metrics`/`gpu_vram`, 1 (live page %) deferred |
| 3 | Integration / build | clippy `-D warnings` + `tauri build` 0 + harness 0 errors | ✅ clippy clean (fixed 1 lint) · build exit 0 (release exe + NSIS + MSI) · harness rendered the real snapshot, 0 console errors, dark+light; **fixed** a light-mode `.ac-*` contrast bug |
| 4 | Testing (boot) | frontend boots clean vs live pipeline | ✅ `widget-boot.log`: `module evaluating` → `all loops launched`, **0 error lines** — `room.js` import resolved in the real webview |
| 5 | Widget testing | launch, real state, controls | ✅ Room live in the real Tauri app: **VRAM 1.9/10** (nvidia-smi), **VAULT 4** (Library), **survival avg 0.69**, median 3.4, real event stream, **ASSAY fail** (Cybernetics) in terracotta; surface switch + resize work; Dock unchanged (7 portals + real assay card) |
| 6 | Converter | lane intact + reflected | ✅ `windows-converter/` **untouched** (git) · `convert_and_ship.py` + `fidelity_audit.py` compile · marker imports · the new widget's **watcher is watching** (poll 5s); prior Cybernetics convert completed. No fresh GPU convert triggered unattended (would occupy the GPU + write the real vault) |
| 7 | Formatter / analyst | mode wiring | ✅ analyst logic (in `convert_and_ship.py`) compiles · `analyst-mode.txt` readable (`off`) · gate cycle wired (harness-verified) · Ollama present (local) · Gemini key hydrated from registry |
| 8 | Vault path | `vault_check` valid | ✅ clone healthy (branch `main`, remote `rab@archlinux:…vault.git`) · Library/Inbox = **4** (matches the Room tile) · widget `vault_check` live **"up to date"** |
| 9 | Linux device sync | reachability | ✅ ThinkPad `archlinux` **ACTIVE** over Tailscale (direct 192.168.2.149, tx/rx flowing) · vault remote reachable · live fetch proven by the widget's "up to date" |
| 10 | Documenting / auditing | files updated, clocks aligned | ✅ this doc + CHANGELOG + ledger row + memory; two clocks advanced together |
| 11 | Higher-order goals | next MAJOR installments | ✅ §8 |

## 8. Higher-order goals — the next MAJOR installments

Not small fixes — the substantial builds this graduation sets up (each its own session):

1. ~~**The Wall surface + live canvas transit belt.**~~ **✅ SHIPPED S35 (2026-07-22).** The
   `Dock|Room|Wall` switch is complete: **Wall** = a glanceable across-room projection (giant
   system verdict — terracotta only on attention/fail — the six stations as big dots, three hero
   numbers: survival avg / throughput / vault) that the window resizes into (900×500); the
   **canvas transit belt** sits under the Room's station rail as an *ambient activity projection*
   — chip count/tint reflect real in-flight work (drop_waiting / converting / gate / held), empty
   when the watcher is down, reduced-motion-safe, palette-cached. Frontend-only, no pipeline
   touch. Verified in the harness (0 console errors) and **live in the real widget** (belt
   animating, Wall "ATTENTION" on the real Cybernetics hold, live VRAM/survival). Still pairs with
   the phone projection ([[remote-dispatch-vision]], docs/14 Phase A) as a future host target.
2. ~~**The drill-down file explorer** (station → live tree).~~ **✅ SHIPPED S36 (2026-07-22).**
   Clicking a Room station flip-expands (transform-origin at the click) into a **live, accurate
   file tree read straight from disk** — a real observation system for granularity, not a
   simulation. New read-only `room::station_tree(seg)` walks the real dirs per station: **vault**
   → `Library/Inbox/*` bundles; **assay** → `held/*` (with the manifest's real degeneration zones)
   + recent verdicts; **convert** → `drop/`, `.gpu-lock`, `drop/done/`, `anchor/`; **gate** →
   `pending/*` + analyst-mode; **ship** → last-shipped (events) + invariants; **intake** → `drop/`
   + `drop/failed/`. Each node carries true byte sizes, manifest fields (lane/pages/sha/engine),
   the analyst pass/reject/fail line, and — for audited bundles — the verbatim degeneration zones
   (zlib/tri×/chars/excerpt) and survival/verdict color-coding. The tree re-reads disk every 4 s
   while open (live), collapse-state persists (stable name-hash ids), Esc/backdrop/× close.
   Verified in the harness (0 console errors) and **live in the real widget**: the Assay drill
   showed the held Cybernetics bundle's real `.md` (155 KB), `assets/` (92 files), and zones at
   lines 1014/2400 exactly matching the on-disk manifest; the Convert drill showed the anchor
   bundles with the real analyst summary (270✓ 22🛡 10✗). Frontend-only render + one read-only
   Rust command; pipeline untouched.
3. **Live convert progress — PARTIAL S37.** The Convert station now shows a **live progress bar +
   %** from measured data (elapsed `.gpu-lock` age ÷ measured-median ETA; `convert_elapsed_s` added
   to `line_state`), capped at 95 % until `converted` fires. True **per-page %** is still deferred:
   Marker runs with `--disable_tqdm` + buffered `subprocess.run`, so page progress would need
   re-enabling tqdm, streaming `Popen`, and parsing surya's *multi-stage* (not per-page) bars —
   fragile, and it touches the core convert call. A careful dedicated converter session.

**Robustness fix (S37) — the orphan-watcher shutdown.** Not a docs/16 face feature, but found by
the §7 live PDF test and fixed the same effort: a force-killed/crashed widget used to orphan its
Python watcher (graceful `watcher::stop` skipped), and racing orphans thrashed the GPU. Fix: the
watcher (+ its Marker subprocesses) runs in a Windows Job Object with `KILL_ON_JOB_CLOSE`, so it
dies with the widget by any means. Proven live (force-kill, incl. mid-convert → whole tree to zero).
See CHANGELOG "Fixed / S37" + `watcher.rs`.
4. **GPU telemetry sparkline — SHIPPED S38 (2026-07-23).** The GPU VRAM KPI tile now draws a
   **rolling sparkline** instead of a bare instantaneous gauge: the poll loop *is* the sampler
   (one `nvidia-smi` read per `gatherVM`, accumulated into a bounded module-scoped ring — no
   always-on background thread, since the sparkline is unviewable with the Room closed anyway). It
   draws on a **fixed 0–100 % scale** so the height means true card-fullness (idle sits low, a
   convert spikes) — deliberately *not* autoscaled like the throughput/median tiles, which would
   exaggerate idle noise and flatten a real spike. `gpu_vram()` was extended to also report
   **utilization + temperature** (`{used,total,util,temp}`, still `Null` when there is no probe),
   surfaced on the header GPU stat (`4.2/10 GB · 41% · 62°`). Gauge remains the first-poll fallback
   (until ≥2 samples); clay stroke under pressure (>92 %), else flow. `sparkSvg` gained an optional
   fixed-domain param (existing tiles unchanged). Verified in the harness (0 console errors; exact
   fixed-scale Y-coords; gauge→sparkline transition; util/temp in dark+light; throughput/median
   sparklines unregressed), `clippy -D warnings` clean, `tauri build` green.
   **Completed S41 (2026-07-23):** the telemetry stream is now whole — **utilization + temperature
   got their own rolling sparklines** in a unified **GPU telemetry strip** (VRAM % / GPU util % /
   Temp °C, three fixed-scale sparklines: 0–100 / 0–100 / 30–95 °C, clay under pressure at
   >92 / >95 / >83). The VRAM sparkline graduated from the KPI tile into the strip (tile reverts to a
   gauge — no duplication). Same poll-is-the-sampler principle (`sampleGpu` feeds `vramHist` +
   `utilHist` + `tempHist`); frontend-only. Harness-verified (0 console errors; all three accumulate
   on their fixed scales — temp Y-coords confirm the 30–95 domain; util clay at 98 %; dark+light).
   **Still deferred by choice** (their own installments, and each argued against above): an always-on
   backend sampler (would probe the GPU with the Room closed — against the S37 idle-resource
   discipline); and re-backing the throughput/median sparklines with a rolling window (their
   events-tail series already IS the last-12-converts rolling window — reworking risks regressing a
   working thing for no gain).
5. **Close the Beer remedy loop.** Audit flags → re-convert → re-audit passes → **supersede
   auto-swap** in the vault (THE SUPERSEDE GAP, ThinkPad exporter). The Room's ⟳ re-convert
   already re-queues; closing the loop needs the exporter's auto-swap on the ThinkPad lane.
