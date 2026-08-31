# S112 · Fable lane SIGN SHEET — the Okular adoptions

⟨claimed: Fable lane · occupant: Claude Fable 5 · S112 · 2026-08-30⟩

**This sheet is OPEN-TASKS A49 made signable.** Every ticket derives from
`docs/49-okular-digest.md` §1 (candidate numbers match), evidence dump D0005. Signing a ticket
authorizes BUILDING it in the bench/prototype quarantine layer (`prototypes/repair-bench/`,
zero pipeline coupling, docs/19 §7 rules) — graduation to a widget surface, audit credit, or
any pipeline/vault effect stays a separate signature, as always. Nothing starts unsigned.
Sign by prompt (your words, quoted verbatim into this sheet) or by editing a slot.

Every ticket: read-only against held bundles until its own record says otherwise; every new
guard ships its tripwire in the same commit (docs/32 §6); every build closes with its measured
numbers, docs/34 form.

## The tickets

| id | ticket | effort | what signing buys | depends on |
|---|---|---|---|---|
| **OK-0** | **UUID identity for repair-site records** — every `manifest["repairs"]` entry gets a UUID at creation; later features key on it, not line numbers (AU-09) | S | fixes the manifest's line-number fragility regardless of everything else | — |
| **OK-1** | **Viewport sidecar** — page + normalized (x,y) as the bench's one address type; position restore, back/forward history (append-on-page-change rule), per-viewport bookmarks. Keyed on a **stable bundle id**, NOT size+name (audit hazard) | S | position restore · history · bookmarks · search-hit addressing | — |
| **OK-2** | **Placeholder paint + progressive first render** — CSS-scale the dpi-30 thumb while the 140/220 PNG loads; low-dpi-first only for pages measured slow (the 500 ms rule) | S | perceived blank-page latency → ~0 | — |
| **OK-3** | **Prefetch + priorities + cancellation** — next/prev prefetch at low priority, suppressed during scroll gestures, stale results dropped by request-generation token before PNG encode | M | instant page turns without racing the rasterizer | — |
| **OK-4** | **The search suite** — 700 ms typeahead, red-field/spinner states, next/prev traversal with wrap toast, 5% no-jump rule, multiply-blend normalized-rect highlights by search ID, NFKC + hyphenation-aware matching, thumbnail-rail results filtering | M | every named bench search pain; hyphen matching ends a class of false "not found" | OK-5 for on-page rects on any page (degrades fine without) |
| **OK-5** | **Text layer for the raster pane** — per-page word/char rects, 0..1 normalized, lazy per page, evictable; PyMuPDF words/rawdict now, OCR boxes later (the DjVu sidecar pattern) | M–L | drag-to-select, precise on-page highlights, real zone anchors | — |
| **OK-6** | **Table divider tool** — drag region, tick-sweep divider guessing, click-to-correct (3 px snap), central-pixel cell extraction → markdown pipe-table. MUST consume char + synthetic-space rects (audit: words-only fails) | M | the humane SYM-003 table-wreck repair | **OK-5** |
| **OK-7** | **Trim margins** — auto paper-color edge scan on the dpi-30 thumbs (+4% pad, 50% cap), manual one-rect-for-all-pages override | S | reading width on scanned books, immediately | — |
| **OK-8** | **Zoom upgrades** — ladder with fit-width/fit-page spliced in, computed-dpi requests (target pixel width → server dpi, one line), loupe = high-dpi crop request, dark/recolor as CSS post-raster | S | fit modes reachable, smooth zoom, loupe, night reading | — |
| **OK-9** | **Unified undo command stack** — one stack, every mutation a command, timer-less keystroke coalescing, clean-marker dirty flag (unsaved-repairs badge + close warning), UUID re-binding across saves | M–L | replaces the bench's three uncoordinated undo systems | OK-0 |
| **OK-10** | **Reviews panel over repair sites** — flat model + stacked toggleable filters, jump-to centering both panes, incremental per-page refresh (never a full rebuild), provenance stamps, External flag for pipeline-authored entries, batch = one undoable macro | M | the missing review index over zones/repairs | OK-0 (OK-9 helps) |
| **OK-11** | **Watch / reload / swap** — 750 ms debounced file watch behind a setting, reload snapshot checklist, mtime-based conflict fork, swap-not-reload on save (with the audit's notify-on-abort fix) | M | edits, scroll, and undo survive the pipeline writing under you | — |
| **OK-12** | **Observability grammar** — typed change flags per surface, severity ladder (banner/toast/modal-fallback), length-proportional toast timeouts, pinned mode-instruction toasts | S–M | surfaces update only what changed; modes explain themselves | — |
| **OK-13** | **Paged markdown reading surface** — server-side pagination of the bundle (layout-once, render page = slice), TOC/anchors/search over it; the md pane stays the editor, this is the READER | L | kills the ~1 s DOM for reading; page coordinates match the raster pane | strategic; OK-5 synergy |
| **OK-14** | **Widget: forward-instead-of-die single instance** — losing launch forwards its open request to the mutex winner (OBS-10). Widget territory: build → SHA-8 → your hand launches, MSIX ghost laws | S | second launches open the book instead of dying | — |
| **OK-15** | **Pipeline evidence extras** (parcel; strike lines you don't want) — per-page `mupdf_warnings()` into bundle evidence · page-label map (i, ii, xiv) · OCG layers off before capture rasters · pdftotext reading-order diff-oracle · embedded /Thumb probe | S–M each | renderer complaints become damage signals; front-matter page confusion ends | — |

## Fable's recommendation (mine, not a signature)

**First batch — sign OK-0 + OK-1 + OK-2 + OK-7** (all S; independent; each closes a named
bench pain in an evening-class build). **Second — OK-4** (search is the largest daily-use
gain). **Then OK-5 → OK-6** (the text layer unlocks the table tool, the SYM-003 weapon).
OK-13 is the strategic one and deserves its own echo/commission when you're ready.

## Signature slots

- OK-0: **SIGNED (Rab, 2026-08-30) · BUILT same day** · OK-1: **SIGNED (Rab, 2026-08-30) ·
  BUILT same day** · OK-2: **SIGNED (Rab, 2026-08-30) · BUILT same day** · OK-3: **SIGNED (Rab, 2026-08-31 15:4xZ)** ·
  OK-4: **SIGNED · BUILT (0181636)** · OK-5: **SIGNED · BUILT (80df03b)**
- OK-6: **SIGNED · BUILT (cd5b10e)** · OK-7: **SIGNED (Rab, 2026-08-30) · BUILT same
  day** · OK-8: **SIGNED · BUILT (be191bf)** ·
  OK-9: **SIGNED (Rab, 2026-08-31 15:4xZ)** · OK-10: **SIGNED (Rab, 2026-08-31 15:4xZ)** · OK-11: **SIGNED (Rab, 2026-08-31 15:4xZ)**
- OK-12: **SIGNED · BUILT (be191bf; change-flag half OPEN)** · OK-13: **SIGNED (Rab, 2026-08-31 15:4xZ) — commission echo owed before build** · OK-14: **SIGNED · BUILT (091ffd7)** · OK-15: **SIGNED · QUARANTINE PROTOTYPE BUILT (77d0361) · REVIEW FINDINGS CLOSED (8da7005) · CROSS-VENDOR DELTA PASS (MSG-FAB-0059); bundle/pipeline graduation remains unsigned**

**Post-close additions (born of the 4e-Damodaran stall, 2026-08-30 evening):**

| id | ticket | effort | status |
|---|---|---|---|
| OK-16 | **Pre-convert ollama unload** — free the ~1.5–2.0 GB the idle analyst residents hold during the convert phase (both stall events read 9.8/10.2 GB; the analyst needs the models only AFTER convert) | S | **SIGNED (Rab, 2026-08-30: "Signed")** — execution deferred until the live convert releases the gpu-lock |
| OK-17 | **Review + commit the stall-recovery ladder** — the uncommitted +139-line retry/split ladder in `convert_and_ship.py` (live-proving itself on slice retries right now): adversarial review, tripwires in the same commit, attribution resolved on the bus | S–M | **SIGNED (Rab, 2026-08-30: "Signed")** — same deferral; the running process is not disturbed |

**Post-close additions round 2 (the batch sheet, 2026-08-31 morning):**

| id | ticket | effort | status |
|---|---|---|---|
| A1 | **Keep slices until the vault receipt** — stop consuming `.chunk-work/<sha16>` at merge; clean on receipt/ship, retention bounded to the latest book (the night paid the full convert twice for want of this) | S–M | **SIGNED (Rab, 2026-08-31) · BUILT same day (cd93987, T12, selftest 50/50)** |
| A2 | **WAT-2: watcher stop kills the TREE** — `watcher::stop` reaches only the venv launcher; the real interpreter survives in the job (measured live 32068/3532). Tree-kill + verify death + symptom row | S | **SIGNED (Rab, 2026-08-31) · BUILT same day (091ffd7, SYM-068 filed; staged exe 933AB9C7)** |
| A3 | **Multi-window deferred job-kill** — main-window close defers the job kill while Bench/Chat windows live; row + explicit exit handler | S | **SIGNED (Rab, 2026-08-31) · BUILT same day (091ffd7, SYM-069 filed; same staged exe)** |
| NUM-1 | **The Numeration Census** — every stepping quantity in the ecosystem registered: name, steps-when, numerator/denominator/conditions (docs/34), kind, defined-at, shown-where, HONEST? (SYM-066-class caps flagged) | M | **SIGNED (Rab, 2026-08-31 ~15:55Z: "Signed, Both", Reading C via /echo)** — Fable lane, building now |
| NUM-2 | **The Live Counter on the glass** — a Room panel deriving the census's live-readable numerations from feeds the Room already polls, event-streamer style; projection, never authority | M | **SIGNED (same word)** — staged AFTER NUM-1; rides the widget exe + adoption gate |
| A4 | **Schema registry + key tripwire** — `observability/schemas.json` generated from the writers; consumer/emitter parity guard (the guessed-key class ends mechanically) | M | **SIGNED (Rab, 2026-08-31) — BANKED FOR CODEX** (relay MSG-FAB-0055) |

**The batch signature, verbatim (Rab, 2026-08-31, ~14:2xZ):** *"Signed, except dont defer to
codex yet, just bank those tickets in relay so when Codex wakes up, it'll take those tickets
first."* — read with the batch presented in-session: Fable lane builds A1, A2, A3, OK-5, OK-4,
OK-6, OK-8, OK-12, OK-14 now; the Codex-shaped slate (conveyor-state build under C1–C8, A4,
OK-15, SYM-065, standing verify-half duties) is BANKED on the relay as a signed queue Codex
takes first at its next wake — no handover before then.

**Build record (2026-08-30):** the four signed tickets landed in the live bench
(`prototypes/repair-bench/bench.py`, `bench.html`, `test_bench_page.py`; docs/22 schema
updated). Harness **45/45** (19 pre-existing + 26 added, every family with positive AND
negative controls). A 3-lens Opus 5 adversarial review of the diff filed 32 findings — 2
CRITICAL (a CSS-cascade bug that would have permanently stuck the placeholder over the page;
a restored view leaving zone context unbound so crops would land at body line 40) — all
confirmed findings fixed and pinned by new tripwires before commit. **Not yet exercised in a
live browser session** (the JS layer is source-verified + reviewed, not runtime-observed —
starting the real bench on a held bundle is your hand): first live run is the honest
remaining gate, `Intended`, exercised the next time the bench opens.

**The signature, verbatim (Rab, 2026-08-30):** *"Do do quarantine only, just implement it.
Signing on OK-0, OK-1, OK-2, OK-7, use opus 5 models if you need / No just implmenet, no
quarantine"*. Reading taken: the four tickets are signed for implementation **directly in the
live bench** (`prototypes/repair-bench/bench.py` + `bench.html`), not behind a quarantine
copy — overriding this sheet's quarantine default for these four only. Pipeline, vault,
widget, and audit-credit boundaries unchanged; the bench's own safety net (`.md.bench-bak`,
append-only provenance, sandbox/reading modes) stays intact.

*Standing older signature items from earlier sessions (S110 sheet C+D, D1 —
`ship-with-losses-named` vs `audit-must-be-green`, still the only item that moves the north
star — S108 sheet, E3 compaction) remain open and are NOT restated here; this sheet is only
the Okular commission's surface.*

**NUM batch (2026-08-31 ~20:30Z, Rab: "Signed. Work, delibrately plan out."):** NUM-3
(true counts beside caps) · NUM-4 (promise repairs) · NUM-5 (decision evidence) · NUM-6
(analyst goodput) · NUM-7 (82-row dispositions) — ALL SIGNED, Fable lane, agent cap 2-3.
