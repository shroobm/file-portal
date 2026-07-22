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

## 6. — reserved: build log (see §8) —
## 7. — reserved —

## 8. Phase log (measured)

*(appended as the session runs)*

## 9. Higher-order goals — next major installments

*(written at close)*
