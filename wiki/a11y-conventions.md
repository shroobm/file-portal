---
title: A11y Conventions
section: Product
last-verified: 2026-08-23
verified-against: 57abcd9
sources:
  - prototypes/repair-bench/bench.html
  - windows-widget/src/styles.css
  - windows-widget/src/index.html
  - windows-widget/src/room.js
  - wiki/roadmap.md
  - OPEN-TASKS.md
---

**File Portal's two human surfaces — the widget (Dock ⇄ Room) and the Repair Bench — are
framework-free vanilla HTML/JS, so accessibility here is a sheet of small, ownable
conventions, not a library choice. Today the surfaces have almost none of them: across both
UIs there is exactly one `aria-*` attribute (the Minimize button,
windows-widget/src/index.html:23) and zero `role=`, `<dialog>`, or managed `tabindex`
(probe, 2026-08-23: `grep -c 'aria-'` / `'role='` / `'<dialog'` / `'tabindex'` on
windows-widget/src/index.html → 1/0/0/0 and prototypes/repair-bench/bench.html → 0/0/0/0).
This page is the convention sheet future surface work builds against; the retrofit order is
Rab's call (below).** Every sketch is written fresh for this page. Ratios measured
2026-08-23 with the WCAG 2.x relative-luminance formula, (L1+.05)/(L2+.05), alpha
composited over the named background — the probe is §1's sketch.

## 1 · Contrast floors — AA 4.5:1 body text; 3:1 large text and UI parts

Floors: **4.5:1** for body text, **3:1** for large text (≥24px, or ≥18.66px bold) and for
meaningful UI graphics, borders, and focus indicators. **The first two work items, measured:**

1. **Bench:** `--text-3: rgba(60,60,67,.32)` on `--bg:#f5f5f7` = **1.78:1**
   (tokens prototypes/repair-bench/bench.html:20,14) — live text at :103 (`.zchip .zs`
   zone stats), :120 (`#diag .dev` diagnosis text), :135 (`#zonefacts`).
2. **Widget, light theme:** `--text-3: #968b80` on `--bg:#eceae6` = **2.77:1**
   (tokens windows-widget/src/styles.css:20,18) — live text at :101 (`.rh-sub`),
   :104 (`.rh-stat.mono`), :144 (`.rl-name`).

Those are the floor-setting worst two, not the whole set: the same sweep measured bench
`--text-2` at 3.50:1 and `--accent` at 3.69:1 (bench.html:20-21), and the widget's
light-mode `--clay`/`--warn`/`--ok` at 3.85/3.43/3.66:1 on `--surface-1`
(styles.css:21-23). The full audit is roadmap C4 (wiki/roadmap.md:67), not this page.
Keep the probe beside the tokens — measure, never eyeball:

```js
const L = ([r, g, b]) => [r, g, b].map(v => { v /= 255;
    return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; })
  .reduce((s, v, i) => s + v * [.2126, .7152, .0722][i], 0);
const ratio = (fg, bg) => { const [hi, lo] = [L(fg), L(bg)].sort((a, b) => b - a);
  return (hi + .05) / (lo + .05); };            // floor: >= 4.5 body, >= 3 large/UI
```

## 2 · Skip link — first focusable element, jumps past the chrome

The Bench's tab order starts at the toolbar; a keyboard user crosses every chip to reach
the markdown pane. One link, visually hidden until focused:

```html
<a class="skip" href="#main">Skip to content</a>
<main id="main" tabindex="-1">…</main>
<style> .skip { position: absolute; left: -999px; }
        .skip:focus { left: 8px; top: 8px; } </style>
```

## 3 · `:focus-visible` — a visible ring, only for keyboard focus

The Bench already has the selector (bench.html:60) but paints the outline with
`var(--accent-bg)` — a 10 %-alpha fill (bench.html:21), invisible as a focus indicator.
The convention: full-opacity ring, `:focus-visible` so mouse clicks stay quiet:

```css
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
/* never `:focus { outline: none }` without a replacement ring */
```

## 4 · Roving tabindex — one tab stop per composite widget

Dock ⇄ Room, the Bench's zone-chip strip: a group is ONE Tab stop; arrows move inside it.
Exactly one member has `tabindex="0"`, the rest `-1`:

```html
<div role="tablist"><button role="tab" aria-selected="true">Dock</button>
  <button role="tab" tabindex="-1" aria-selected="false">Room</button></div>
<script> list.onkeydown = e => { const next = pick(e.key); if (!next) return;
  cur.tabIndex = -1; cur.ariaSelected = "false";
  next.tabIndex = 0; next.ariaSelected = "true"; next.focus(); }; </script>
```

## 5 · Focus-to-main on view switch

`setActiveSurface` (windows-widget/src/room.js, imported at main.js:14) swaps Dock and
Room but leaves focus wherever it was. Convention — when a surface swap replaces the view,
move focus to the new view's container so keyboard and reader users land in it:

```js
function showView(el) {
  el.hidden = false;
  el.setAttribute("tabindex", "-1");   // focusable target, not in tab order
  el.focus();
}
```

## 6 · Dialog focus return

Neither surface has a modal yet (`<dialog>` count 0/0 — probe above); the first one
follows this shape. `<dialog>.showModal()` traps focus natively — the RETURN trip is ours:

```js
let invoker;
function openDialog(d) { invoker = document.activeElement; d.showModal(); }
function closeDialog(d) { d.close(); invoker && invoker.focus(); }
// Esc fires the dialog's own "close" event — hook the same return there.
```

## 7 · `aria-live` for changing counts

The Dock's card counts and the Bench's zone tallies change without a page change; a reader
only announces them if the mutated element is a live region. Mutate the SAME element —
swapping nodes resets the announcement:

```html
<span id="count" aria-live="polite" aria-atomic="true">0 zones</span>
<script> function setCount(n) {
  document.getElementById("count").textContent = n + " zones";
} </script>
```

## 8 · `prefers-reduced-motion`

The widget's key-press springs and 340 ms release curves (styles.css:41-42) are decorative;
vestibular-safe means they collapse to ~zero when the OS says reduce:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important; transition-duration: .01ms !important;
    scroll-behavior: auto !important; } }
```

## Retrofit order — Rab's call

The ORDER is deliberately not decided here; it goes on the S108 sign sheet.
Recommendation only, cheapest-per-measured-harm first: (1) the two §1 contrast tokens —
one-line diffs, worst measured harm; (2) §3's real focus ring; (3) §8 reduced-motion;
(4) §2 + §5 skip link and focus-to-main; (5) §7 live counts; (6) §4 roving tablist;
(7) §6 at the first modal. Rab may reorder or strike any of it.

## Open items

- Roadmap C4 — "Accessibility: never audited; known input defects on the bench"
  (wiki/roadmap.md:67). This page is the convention sheet; C4 is the audit.
- OPEN-TASKS.md A30 (Ctrl+Z dead in the Bench after Enter) — the standing keyboard defect.
- OPEN-TASKS.md B5 (nothing tests bench.html) — until that lands, §2–§7 conventions on the
  Bench are unverifiable by CI.
- The two §1 contrast failures are measured but NOT yet rows in OPEN-TASKS.md as of this
  stamp — register entry is outside this page's lane.
