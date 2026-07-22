# The Control Room — design record

The **Opsroom** and the **Tauri widget** merged into one adaptable surface, plus a
station drill-down file explorer. Built as a **quarantined** prototype (see
`../../README.md`) — it renders a self-contained simulation, never the live pipeline.

- **File:** `control-room.html` — one self-contained page, zero dependencies, opens by
  double-click. No server, no network, no build step. (Compiled from a Design Component
  source; this HTML is the shippable, inspectable artifact.)
- **Status:** prototype awaiting Rab's verdict. Disposable by design.
- **Lineage:** successor to `../opsroom/` — same tokens (a superset of
  `windows-widget/src/styles.css`), same laws (docs/13).

---

## 1. The thesis

The opsroom dashboard and the widget are **the same pipeline at two densities**. The
projection principle (docs/13, law #1 — "all state lives on disk and in git; the face
renders, never owns") means one shared state can render at *any* density. So this is one
control room with three switchable surfaces, which is also the answer to the open question
in the opsroom's DESIGN.md §7 ("a larger window, a separate ops window, or a tray panel"):
**all of them, from one projection.**

## 2. The three surfaces (top-right switch)

- **Room** — the operations dashboard: the line + canvas transit belt, golden-signal KPIs,
  Convert station, Survival Audit, event stream. The opsroom, improved.
- **Dock** — the widget rebuilt: 7 drop portals, the compact line strip, the degeneration
  assay card (survival, loop-zone map, verbatim `tri×` runs, re-convert, held tray),
  Library bar, shift line. Matches the shipped widget's face.
- **Wall** — a glanceable projection for a screen across the room (docs/14): giant system
  verdict, the line as big station dots, three hero numbers.

## 3. What the merge added (over the read-only opsroom)

The opsroom only *observed*. The Control Room makes the same panels *operable*, lifting
the widget's real controls into the dashboard:

- **Gate routing cards** — a doc awaiting your decision: `🔒 Local` / `☁ Flash` / ship
  as-is, with ETA ranges and the "always route big docs local" rule (`analyst-mode.txt`).
- **Report ⇄ enforce lever** on the Survival Audit, plus **re-convert** remedy and the
  **held/** tray (docs/15).
- **Drop portals**, **reader launchers** (Obsidian / ZenNotes), **watcher** toggle,
  **Library** pull bar.

## 4. The drill-down (the S-addition)

Clicking a **Wall** station icon FLIP-expands it (transform-origin at the click point,
~260 ms, no library) into a full-pane **live file explorer** — a collapsible recursive
tree, color-coded by survival, self-updating from the same state. Each station opens its
real on-disk shape:

| Station | Opens |
|---|---|
| Vault | `vault.git` (bare) → `Library/Inbox/<slug>--<sha8>/` — `index.md` (frontmatter `lane`/`ocr`/`src_sha256`), `assets/` embeds, `manifest.json` |
| Assay | `library/staging` audit block — `held/` fail bundles with real degeneration zones (Brain of the Firm line 1600, `zlib 0.003`, `tri×2152`, 32,294 ch), recent verdicts, the docs/15 §9.1 flag threshold |
| Convert | `pipeline/convert-inbox`, `converting/` (live page · s/page · VRAM), `convert-scan-inbox`, `library/anchor` |
| Gate | `pending/` card JSONs · `analyst-mode.txt` |
| Ship | `vault-work → vault.git` over Tailscale SSH, cat-file verified (L12) |
| Intake | allocator `sorted/` (rules.toml) + `quarantine/` |

Feasibility (per Gemini's handoff): FLIP via CSS transform-origin (no JS animation lib);
recursive tree flattened to indented rows for a frameworkless render; "live" is the
projection reading `events.jsonl`. In the real widget the tree binds to Tauri events and
updates the specific node — the graduation step, not prototype work.

## 5. Malleability (tweaks)

`mode` (dock/room/wall), `theme` (dark/light), `accent` (clay / indigo / teal —
brand-adaptable while keeping the terracotta = "your hand required" rule), `density`
(full/dots/min), `showBelt`, `showPortals`, `simSpeed`, `paused`. In-UI switches for
mode / theme / accent / density mirror the props so the morph is felt live.

## 6. Honest boundaries

- **Quarantined.** Nothing here reads, writes, or triggers the pipeline. Self-contained
  simulation; every figure drawn from real data (the vaulted books, measured s/page,
  ~8 GB VRAM, the recalibrated survival scores, the Brain-of-the-Firm degeneration
  finding) so it reads true.
- **Graduation** = replace the simulation with the widget's existing `invoke()`
  projections (`line_state`, `assay_status`, `shift_summary`, `last_receipt`) and bind the
  drill-down tree to `events.jsonl`. The tokens are a superset of the widget's palette.
