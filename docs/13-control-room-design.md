# Control Room Design — the Widget as a Projection

**Origin:** live co-design with the user, 2026-07-19 (post-S18, after the pre-flight card's
first real click). Successor to the docs/11 design note; this is the blueprint the build
sessions (S20+) implement, each piece landing separately and switchable.

---

## First law: the projection principle (user's doctrine, near-verbatim)

> The widget's functionality and representation are a **second source of truth — a
> projection of the GitHub/pipeline as a utility: conventional and pragmatic, but with taste.**

Mechanically: **all state lives on disk and in git** — pending card JSONs, the events
stream, drop/done/failed trays, the vault repo, manifests, frontmatter. Python (the
pipeline) owns every schema; the widget **renders and requests, never owns**. Any surface
of the widget must be reconstructible by reading the filesystem. (S18 already obeys this:
`preflight.rs` passes card JSON through untouched.) Corollary: if the widget dies, the
factory keeps working; if the factory dies, the widget honestly shows a stopped line.

## The line grammar (the one unifying representation)

Every document is a **chip on a horizontal line of stations**:

```
Drop ▸ Convert ▸ Analyst ▸ Ship ▸ Library
```

- A chip is always *somewhere*; "where is my file?" is answered by looking.
- The S18 pre-flight card is re-understood as **a chip paused at a decision gate**.
- The W8 vault bar is the **delivery dock** at the end of the line.
- Idle widget = compact (tiles + dock + shift line). The line breathes open only when
  pieces are on it — the existing grow/shrink behavior, promoted to principle.

**The terracotta rule:** `#D97757` means exactly one thing — *your hand is required*
(a gate decision, a failure to retry, a delivery to pull). Nothing else pulses, ever.
Green = delivered; amber = caution; grey = machinery humming. A control room, not a
notification farm.

## Stations and levers (control & variety)

- **Per-station switches, on the stations** (the docs/11 "each segment can be turned off"):
  Intake pause (drops queue, nothing converts), Plant pause (the gaming switch), Analyst
  gate as a 4-position selector — `ask / auto-local / auto-cloud / off` (today:
  `analyst-mode.txt`, which remains the on-disk truth the selector projects).
- **Per-chip overrides** (right-click): force scan lane, force backend, hold indefinitely.
- **Rules — "remember this choice":** a small check on the card's route buttons ("always
  route >18-chunk docs local") persists as a rules file; the card thereafter only appears
  for genuinely novel cases. Variety on first encounter, automation after the decision.

## Two engines, two natures (design rationale)

- **Marker is a stamping press:** specialized vision models (layout/OCR/order/tables),
  steered only by switches, not promptable. Its station shows mechanical telemetry
  (s/page) — there is nothing to "ask" it.
- **The analyst is a program slot:** the LLM is frozen; its behavior IS the prompt text.
  "Tuning" = editing/adding prompt files — no training, versioned in git:
  `windows-converter/prompts/<program>.txt` (`readability` is program #1; summarize,
  glossary, simplify are files away). The card later gains a program selector.
  **Local (qwen3) vs cloud (Flash) stays orthogonal to program choice.** Every program
  runs inside the same `⟦IMG-n⟧` link-fence — the fence is station infrastructure, not
  per-program code.

## Marker's visibility (answering a real confusion)

Today conversion is invisible — the widget learns only when the card appears afterward.
The line view fixes it: a chip visibly sits **in the Convert station** with live s/page.
Station display density is itself a toggle: full line / minimal dots / hidden-when-idle
(taste = the user chooses how much machinery they see).

## Metrics doctrine (evaluation, without a dashboard wall)

**Numbers live where decisions happen:**
- The free-tier budget renders **on the ☁ button itself** (depletion bar, e.g. `13/20`).
- Each station shows one rolling *measured* rate (s/page, chars/s) — self-calibrating,
  which turns ETAs into honest **ranges** (p50–p90), not points.
- Bottom line = **shift report** (replaces the status line when idle): "today: 3
  converted · 2 analyzed (3 chunks fence-protected) · 2 shipped · 1 duplicate skipped".
- **Fence rejections are displayed as protections** ("3 chunks protected"), never as
  errors — the security system reporting success.

## Receipts and lineage (examination)

- A delivered chip's click opens its **receipt**: probe → lane → engine → analyst
  (program/backend, passed/protected counts) → actual duration *vs the ETA promised*
  (trust calibration) → vault commit sha; buttons: *open note* / *open as-converted twin*.
  All of it is already in frontmatter + manifests — the receipt is a projection, law #1.
- **Failed tray**: `drop\failed\` surfaced with plain-language reasons and one-click retry.

## The dock has doors: reader launchers

Two titlebar icons — **Obsidian** and **ZenNotes** — launch the reading surfaces on the
vault. Config-driven (`reader_apps = [{label, icon, target}]`): Obsidian via its exe or
`obsidian://` URI; ZenNotes via its exe. The factory ends where reading begins; the
control room should open that door in one click.

## The keystone: one event stream

Replace the three separate polls (status.json, pending dir, vault check) with a single
local **`events.jsonl`** every pipeline stage appends to; the widget tails it. Instant
updates, one code path, and the shift report / receipts / rolling rates all *derive* from
the same stream. The watcher's lifecycle moves into the widget (spawn, supervise,
restart — `CREATE_NO_WINDOW`), killing the manual console ritual.

## Build order

- **S20 — foundation (mostly invisible):** events.jsonl emitters + widget tail; widget-managed
  watcher lifecycle; shift-report line. Prompt-file refactor of the analyst (programs).
- **S21 — the visible transformation:** line view with chips + station toggles + Convert
  station visibility; reader launcher icons.
- **S22 — judgment layer:** receipts, remember-my-choice rules, ETA ranges, failed tray.

Each lands separately, each switchable, bundle format and ThinkPad untouched throughout.
