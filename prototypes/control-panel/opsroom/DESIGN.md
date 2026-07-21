# The Opsroom — design record

A professional control-panel / dashboard representation of the File Portal document
factory: pipeline segmentation, a live transit viewer, the Survival Audit, and live
golden-signal numbers. Built 2026-07-21 as a **quarantined** prototype (see
`../../README.md`) — it renders a self-contained simulation, never the live pipeline.

- **File:** `opsroom.html` — one self-contained page, zero dependencies, opens by
  double-click. No server, no network, no build step.
- **Live view:** published as a private Artifact — https://claude.ai/code/artifact/58b778cf-3c5d-464d-aef7-cc6bb4d0cadc
- **Status:** prototype awaiting Rab's verdict. Disposable by design.

---

## 1. The brief

Rab (2026-07-21, heading to bed) asked for a "professional dashboard control panel app
representation… very light on resources, but still extensive enough to be visually a full
fledged developed app interface, with live time numbers, loading bars, a live transit
viewer with a visualization to pair of what's going on… the pipeline segmentation, and the
audit," designed "akin to that of what's marketed by Claude Design," using "high order
references for research," with the design style focused toward those references. Elite code
organization, fully documented, quarantined from the pipeline.

## 2. The thesis

**A control room for a viable system — in the lineage of the one the author of these books
built.** The factory ingests Stafford Beer's cybernetics library; Beer also designed the
most famous control room in history. So the Opsroom is not a generic SaaS dashboard — it is
*that* control room, rebuilt in the Claude Design System, with modern observability
discipline. The concept is the design: observation and control of a production pipeline,
descended directly from the intellectual tradition the pipeline is preserving.

This also honours the widget's own laws (`docs/13`): **projection** (the panel renders
state, never owns it), **one reserved accent** (clay/terracotta = "your attention / live
action," nothing else), and **glanceable segmentation** (the line: intake → convert → gate
→ assay → ship → vault).

## 3. Research — the high-order references

Five references were consulted and each contributes a specific, traceable design decision.

### 3.1 Project Cybersyn — the Operations Room (Beer + Bonsiepe, Chile, 1972) — *primary*
The anchor. Stafford Beer's cybernetic management system; the Opsroom was a **hexagonal**
fibreglass room with seven swivel chairs (white, **orange cushions**), the walls lined with
data screens, "tables and paper banned — it had to look like the future." Interface and
information design by **Gui Bonsiepe** of **HfG Ulm** — the systematic, functional design
school whose lineage runs through Braun/Dieter Rams to Apple/Jony Ive.
- → the **hexagon** logo mark; the **orange → clay** accent (Cybersyn's chairs are the
  reason terracotta feels *native* here, not imported); the utilitarian, screens-only,
  "looks like the future" restraint.
- Sources: [99% Invisible — Project Cybersyn](https://99percentinvisible.org/episode/project-cybersyn/),
  [Wikipedia — Project Cybersyn](https://en.wikipedia.org/wiki/Project_Cybersyn),
  [Dubberly — Gui Bonsiepe: Framing Design as Interface](https://www.dubberly.com/articles/gui-bonsiepe-framing-design-as-interface.html).

### 3.2 ISOTYPE (Otto Neurath & Gerd Arntz, 1928) — via Ulm
The Opsroom's screens descended from ISOTYPE — an iconic visual grammar built so anyone
could read the state of the system "with a minimal amount of scientific training"; figures
were avoided in favour of graphic displays.
- → **iconic station glyphs** (▚ ⚙ ✳ ◎ ⇈ ▤) carrying meaning at a glance; graphics for
  *state/flow* (the transit viewer, meters, the damage map) and numbers reserved for the
  levers where a figure is the point.
- Source: [Operative communication: Project Cybersyn (AI & SOCIETY, 2022)](https://link.springer.com/article/10.1007/s00146-021-01346-2).

### 3.3 Modern observability practice (Grafana / SRE) — *discipline*
How real operators read a live system: focus on **golden signals** (throughput, latency,
saturation), answer "**is it healthy?**" in seconds, then drill down; keep it glanceable
(< ~12 panels), replace repetitive labels with **icons**, minimise latency.
- → the **KPI signal row** (throughput, s/page, VRAM saturation, queue, survival, uptime);
  the top-bar **"system viable"** health verdict; the panel count kept tight.
- Sources: [openobserve — Observability dashboards](https://openobserve.ai/blog/observability-dashboards/),
  [groundcover — Grafana dashboards best practices](https://www.groundcover.com/learn/observability/grafana-dashboards),
  [UXPin — Dashboard design principles](https://www.uxpin.com/studio/blog/dashboard-design-principles/).

### 3.4 Linear — the modern engineering aesthetic — *execution reference*
The bar for "comfortably professional." Linear's language: **restraint**, dark, monochrome
with a **minimal accent**, high contrast, a clean **sans for UI + a premium monospace for
data/code**, one type voice from display to body.
- → **system-ui sans** for chrome, **monospace** (Cascadia/Consolas — the widget's own) for
  every number, label, and log line; one accent; tabular numerals everywhere digits align.
- Sources: [LogRocket — Linear design](https://blog.logrocket.com/ux-design/linear-design/),
  [awesome-design-md — linear.app](https://github.com/voltagent/awesome-design-md/blob/main/design-md/linear.app/DESIGN.md).

### 3.5 The Claude Design System — the named target
Rab asked for "akin to what's marketed by Claude Design." CDS principles applied: flat
surfaces (no gradients/mesh/noise beyond one faint ambient wash), **one reserved accent**
(clay is Claude's color, for the system's own live actions), **semantic color separate from
the accent** (green = pass/healthy, amber = flag), restraint ("too cluttered" is the common
failure), sentence-case copy, elevation used sparingly. Structural mono micro-labels are the
one deliberate departure — a control-room convention shared by Linear and observability UIs.

## 4. The design system (as built)

**Color.** A warm-neutral dark ground (`#100e0c`, biased toward the accent so it reads as
*chosen*, not default black) with layered surfaces. One accent — **clay `#d97757`** (dark) /
`#c15f3c` (light) — reserved for attention/live action. Semantic, separate: **green** (pass /
healthy), **amber** (flag / warn). One cool counter-tone — **flow `#79a6bd`** — marks
motion/in-transit, the only cool note against the warm palette. Fully **theme-aware**: a
committed dark "opsroom at night" and a deliberate warm-grey light theme (a *cool*-leaning
paper, explicitly not the cliché cream), switchable and honouring `prefers-color-scheme`.

**Type.** `system-ui` for chrome (native, weightless, zero-load); `ui-monospace` /
Cascadia / Consolas for all data, labels, and logs — tying the panel to the widget and
carrying the engineering register. Two weights (400/500). `tabular-nums` on every figure.
Uppercase mono micro-labels with letter-spacing for eyebrows.

**Layout.** A 1240px app shell: top bar (identity + health cluster + clock + theme) → the
**line** (six stations + the transit canvas) as the hero → a six-tile **golden-signal row**
→ a three-panel grid (Convert station · Survival Audit · Event stream). Responsive to a
single column. Flat cards, hairline borders, one faint ambient clay wash top-right.

**Motion.** A client-side simulation gives it life: numbers tick, the convert bar fills with
a live ETA, sparklines advance, documents glide through the transit viewer, the event log
streams. All gated by `prefers-reduced-motion`. The canvas caches its palette once (and on
theme change) so the 60 fps loop never touches layout — it stays genuinely light.

## 5. Feature ↔ pipeline map

| Panel | Shows | Real pipeline source (when wired) |
|---|---|---|
| The line (6 stations) | per-segment counts + active/done state | filesystem projection + `events.jsonl` |
| Transit viewer (canvas) | documents in flight, tinted by state | in-flight bundles across segments |
| Golden-signal row | throughput, s/page, VRAM, queue, survival avg, uptime | measured rates, `.gpu-lock`, GPU, audit block |
| Convert station | current doc, page progress, ETA, VRAM, lane, batch | `line_state` / `.gpu-lock` / probe events |
| Survival Audit | recent verdicts, survival meters, a damage map | manifest `fidelity` block (docs/15) |
| Event stream | the live event tail | `events.jsonl` |

Every number in the prototype is drawn from **real** figures (the vaulted books, measured
8.1 / 3.0 s-per-page, ~8 GB VRAM, the recalibrated survival scores) so it reads true.

## 6. Honest boundaries

- **Quarantined.** Nothing here reads, writes, or triggers the pipeline. The data is a
  self-contained simulation. Graduating any of this into the real widget (whose frontend is
  the same frameworkless HTML/CSS/JS, so it is portable) is a separate, explicit decision.
- **A prototype, not a product.** It demonstrates the *design direction and execution bar*.
  Wiring it to live projection (the Rust commands already exist: `line_state`,
  `assay_status`, `shift_summary`, `last_receipt`) would be the real build.
- **Disposable.** If the direction is wrong, it stays here as a record or is deleted — it
  never leaks into production.

## 7. If it graduates — next steps

1. Replace the simulation with the widget's existing `invoke()` projections (the commands
   already return exactly this shape of state).
2. Decide the surface: a larger widget window, a separate "operations" window, or a tray-
   opened panel — the skeleton (Python owns truth, the face renders) supports any.
3. Carry the theme tokens into `windows-widget/src/styles.css` (they are a superset of the
   widget's current palette).
