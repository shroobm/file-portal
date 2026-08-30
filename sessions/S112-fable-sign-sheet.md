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

- OK-0: _____ · OK-1: _____ · OK-2: _____ · OK-3: _____ · OK-4: _____ · OK-5: _____
- OK-6: _____ · OK-7: _____ · OK-8: _____ · OK-9: _____ · OK-10: _____ · OK-11: _____
- OK-12: _____ · OK-13: _____ · OK-14: _____ · OK-15: _____

*Standing older signature items from earlier sessions (S110 sheet C+D, D1 —
`ship-with-losses-named` vs `audit-must-be-green`, still the only item that moves the north
star — S108 sheet, E3 compaction) remain open and are NOT restated here; this sheet is only
the Okular commission's surface.*
