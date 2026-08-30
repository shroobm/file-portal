# docs/49 — THE OKULAR DIGEST: what a 20-year-old reader knows that File Portal can use

⟨claimed: Fable lane · occupant: Claude Fable 5 · S112 · 2026-08-30⟩

**Status: RESEARCH. Nothing here is adopted. Adoption is Rab's hand (docs/19 §0.3).**
Commission: `sessions/S112-fable-lane-okular-2026-08-30.md` §1, verbatim. Relay claim:
`MSG-FAB-0044`.

## §0 How this was measured

- **Subject:** KDE Okular 20.08.0 source, `C:\Users\Bndit\Downloads\okular-v20.08.0` — 896
  files; sha256 anchors pinned in the evidence dump (core/document.cpp `60983f2a…`,
  ui/pageview.cpp `9a14e0ea…`). "Popper" read as **Poppler**, reached through Okular's bridge
  (`generators/poppler/`) plus bounded upstream-docs reading; no Poppler source tree exists on
  this machine (`ls Downloads | grep -ci poppler` → 0).
- **Instrument:** a 15-agent fleet under `docs/47` (run `wf_61b440a5-0c1`): 8 sweep lanes
  (model claude-fable-5), each with orchestrator-measured GROUND, a first-phase ground check,
  read-only blast radius, calibrated negative controls (known-present token + known-absent
  token), tagged claims, and declared residue — then **7 audit lanes (model claude-opus-5,
  distinct lens each) that re-measured every citation of the seven CODE lanes, not a sample.
  The popplerweb lane had NO audit lane: its 12 findings (36 citations) are unaudited and
  marked as such wherever they appear.**
- **Audit outcome: 404 of the 438 total citations re-measured — 404/404 MATCH** (0 drifted,
  0 not-found; 404 counts audit rows, which include a few references the auditors added beyond
  the reports' own), with **23 tag downgrades** (one, GEN-05, is a number correction whose tag
  was already Observed) **and 3 number corrections** applied throughout this digest (§2). The
  orchestrator hand-checked the two most consequential findings before writing this (GEN-01
  pagination at `textdocumentgenerator.cpp:319/407-421`; LAT-04 tile hysteresis at
  `document.cpp:1326/1373`) — a re-read with the SAME instrument, so a coverage check, not
  corroboration (the exact defect class the audits filed 23 times; named rather than dressed
  up). Both mechanisms hold, and the hand-read of line 1326 confirms the audits' fourth
  conjunct (§2 item 3).
- **Tags:** every finding carries Observed / Verified / Inferred per docs/21. `↓` in §4 = the
  audit downgraded the tag, with the reason inline. Citations are `file:line` into the 20.08.0
  tree; quotes were re-measured by the audit lanes on 2026-08-30.
- **Full evidence** (all 8 sweep reports + all 7 audit reports, verbatim JSON): dumped via
  `dumps/dump.sh` — pointer + digest in the ledger row this commit carries and in `MSG-FAB-0045`.

The bench pains this digest aims at, measured in `prototypes/repair-bench/bench.html` (read in
full this sitting) and the registers: the ~1 s whole-file DOM rebuild on text change (B22),
one full-page PNG per page with no prefetch/tiles/progressive render, no next/prev search
traversal, highlights only on the current page, no reading-position restore, no viewport
history, fixed zoom steps, no trim margins, no text selection on the raster, no review index
over repair sites, three uncoordinated undo systems, and SYM-003's table wrecks.

## §1 THE SHORTLIST — ranked adoption candidates

*Ranked by value-per-effort against the bench pains above. Effort: S = an evening, M = a
session, L = multi-session/strategic. Every mechanism from the seven code lanes survived the
citation audit; **PW-\* findings ride the unaudited popplerweb lane** and are flagged where
they appear. Where the audit corrected the sweep, the corrected form is what is stated here.*

### 1 · The viewport as the one address type — position restore, history, bookmarks [S]
Okular's whole navigation system keys off one struct: **page number + normalized (x,y)
re-position point**, serialized to a compact string (`N;C2:x:y:pos`) that TOC destinations,
bookmarks, history and cross-file links all carry (`core/document.h:1301`, scannav-01).
History appends **only when the page changes; same-page scrolls overwrite the top entry** —
that one rule stops scroll spam (100 in RAM, 10 persisted; `document.cpp:167`, scannav-02).
Per-document state (viewport history, zoom value+mode, continuous, trim) lands in a sidecar
XML **keyed by file size + name**, written on a 5-minute timer + close
(`document.cpp:2170/2436`, scannav-03, OBS-8). **⚠ Audit hazard, load-bearing for FP:**
size-in-key means every rewrite silently loses the reader's position — fine for Okular,
wrong for a bench whose pipeline re-emits bundles; key FP's sidecar on a stable bundle id
instead. Sync fan-out: one viewport object updated by a nearest-to-center rule and published
to TOC/thumbs/minibar (scannav-09 — audit: the notification actually includes the sender, so
exclude-self is the port's job, not the framework's). Bookmarks are **per-viewport, not
per-page** — fragment = the viewport string, fuzzy-matched at 1e-6, inline rename, default
titles `#p-n` (`bookmarkmanager.cpp:436`, scannav-13).
**Bench:** one JSON sidecar per bundle + `N;C2:x:y` in the URL hash gives restore, back/forward
(~30 lines), search-hit addressing, and "come back to this half-fixed table" bookmarks — four
gaps, one struct.

### 2 · Never show a blank page — placeholder rescale + progressive render [S]
While the right-size raster is absent, Okular paints **the nearest existing pixmap from ANY
observer** (even the thumbnail) scaled into place; blank+icon only beyond 20×/0.25× rescale
(`pagepainter.cpp:105/113-115`, LAT-09). For slow renders, poppler streams partial images via
callbacks the bridge arms **only for first paint, suppressed for the first 500 ms** — fast
pages never pay the overhead, slow pages appear progressively (`generator_pdf.cpp:1026`,
`document.cpp:1429`, LAT-08/PW-01/GEN-13).
**Bench:** on page turn or zoom, CSS-scale the dpi-30 thumbnail (already fetched) as the
placeholder and swap in the 140/220-dpi PNG when it lands; add a low-dpi-first route only for
pages measured slow. Perceived blank-page latency → ~0 at trivial cost.

### 3 · Prefetch with priorities, gated by scroll-settle, with cancellation [M]
One request queue, priorities 0–5: **visible page (1) always beats thumbnails (2) beats
preloads (3/4/5 — 4 is the page-view lane a bench would copy)** (`ui/priorities.h:14-19`,
`document.cpp:1287`, LAT-01). Requests are **suppressed during a kinetic flick** —
`QScroller::Scrolling` state only, zero timers; pages flown past are never rasterized (audit:
held drags report `Dragging` and DO still issue requests — the sweep's "any scroll gesture"
was broader than the gate; `pageview.cpp:4365`, LAT-02). Preload = viewColumns() neighbours
each side, **dropped if they would evict a cached page closer to the reading position**
(`pageview.cpp:4469`, `document.cpp:1315`, LAT-03 — audit: the 512 px expansion is
vertical-only, and the whole preload block is skipped under the Low memory profile). New batches purge the same observer's stale
queue; poppler polls an abort flag mid-render (LAT-10, PW-03 — PyMuPDF has no mid-render
abort, so the bench server needs request-generation tokens that drop stale results before PNG
encode).
**Bench:** prefetch next/prev page at low priority, never during a scroll, cancel-by-token on
page flips. Kills the page-turn wait without racing the rasterizer.

### 4 · The search suite — traversal, debounce, honest feedback [M]
The core of the contract the bench lacks, in field-proven constants:
- **Find-as-you-type at 700 ms debounce**, min length, **red input field** below minimum or on
  no-match, busy spinner only after 100 ms (`searchlineedit.cpp:143/254/305`, S-02, S-12).
- **Next/prev traversal**: per-page resume cursors (`textpage.cpp:702`, S-04), cross-page
  walk starting at the *current* page, **wrap-around with a 3-second toast** ("Continuing
  search from beginning"), not-found only after a full lap (`document.cpp:1606`, S-05).
- **Viewport jumps only if the match ± 5% margin is off-screen, then centers it** — repeated
  next-match inside the visible area never scrolls (`document.cpp:1664`, S-06; audit: this
  rule is additionally gated per-caller by a moveViewport flag — the sidebar list never steals
  the viewport, exactly the bench's own "place never stolen" law).
- **Highlights = paint-time multiply-blend overlays keyed by normalized rects + search ID** —
  never baked into the raster, cleared per-ID, legible text under yellow
  (`pagepainter.cpp:357`, S-07/TG-10; CSS `mix-blend-mode: multiply` is the direct equivalent).
- **Thumbnail rail doubles as the results list** — filter to matching pages, paint hit rects
  on the thumbs (S-09): for scanned-book repair this beats a text results list.
- **NFKC-normalized, hyphenation-aware matching** — `word-\n` matches `word`
  (`textpage.cpp:807/772`, S-13). FP's conversions inherit scanned-book hyphens; without this,
  repair searches silently miss — a class of false "not found" at the bench today.
- Search is **chunked one page per event-loop turn** and cancellable between pages (S-01 ↓ —
  audit: Okular renders results only at the end; *streaming* first hits is a bench upgrade on
  top of the chunking, not something Okular does).
- The rest of the lane, adjacent and cheap: **concurrent search IDs** so the results list and
  the traversal cursor coexist as independently-cleared overlay sets (S-03); **all-words /
  any-words modes with per-word hue-rotated colors** — far better for locating damage
  described by multiple terms (S-08); **per-ID cancellation with a deliver-the-found-match
  grace** (S-11, which also names Okular's global-flag wart to avoid); and the **minimal
  persisted option set + F3/Shift+F3/Escape bindings** (S-14). The server-side match design
  that returns `(page, rect-list, resume-token)` per hit is TG-14.

### 5 · A text layer for the raster pane [M–L]
The universal currency is **per-character rects in 0..1 page-normalized doubles** — one
geometry serves every dpi and zoom (`core/area.h:71`, TG-01); the minimum viable layer is
literally `[{string, x0,y0,x1,y1}]` per page (TG-02). The poppler bridge builds it **lazily on
first touch, per page, evictable under memory pressure** (TG-13 ↓ — newline per line-end), and
DjVu proves the OCR case: **a sidecar word-rect layer feeds the SAME search/selection machinery
as born-digital text — core cannot tell OCR text from real text**
(`generator_djvu.cpp:202`, GEN-09). Selection needs no range trees: with a reading-ordered
list, drag = nearest entity to start/end, take everything between
(`textpage.cpp:535`, TG-08).
**Bench:** a per-page word-rect sidecar (PyMuPDF words / rawdict, or the OCR lane's boxes)
unlocks on-page search hits on any page, drag-to-select, precise zone anchors — the
single biggest capability gap between the bench and a real reader.

### 6 · The table tool — machine guesses dividers, human corrects with clicks [M]
Drag a region; Okular **auto-guesses row/column dividers by an interval tick-sweep over
entity-box whitespace** (running tally returns to zero across a gap → divider at the gap
midpoint, drawn dashed); a click within 3 px deletes a divider, elsewhere inserts one
(`pageview.cpp:3020/2284`, TG-11 ↓). Cell text joins by **central-pixel inclusion** (a glyph
belongs to the cell holding its center — straddlers never duplicate), output as TSV + HTML
(`pageview.cpp:2822`, TG-12).
**⚠ Port-critical audit correction:** the sweep said "needs only the word layer." False — the
algorithm consumes **per-character entities PLUS synthetic space rects whose boxes span the
gaps**; a words-only port would emit a divider between every pair of words. Space-gap
geometry must be part of the layer (TG-07 shows how Okular synthesizes it).
**Bench:** this is the humane answer to SYM-003 table wrecks — divider guessing over the §1.5
text layer, one-click correction, central-pixel cells → markdown pipe-table.

### 7 · Trim margins — auto by raster scan, manual by one dragged rect [S]
Trim is measured **from the rendered image**, no PDF metadata: scan for the first
non-paper-color pixel from each edge, store a normalized box per page, **expand 4%, never crop
past 50%** (`core/utils.cpp:90`, `pageview.cpp:3385/3396`, scannav-06). Manual override:
drag ONE rect, applied to ALL pages (20% floor), mode auto-reverts (scannav-07 — scan books
have uniform geometry, one rect genuinely suffices).
**Bench:** run the same edge scan server-side on the dpi-30 thumbs it already makes; CSS-crop
the big PNG client-side. Reading width on scanned books improves immediately.

### 8 · Zoom that reaches the states readers want [S]
16-step ladder with **computed fit-width/fit-page factors SORTED INTO the ladder** — stepping
naturally lands on the fit modes (`pageview.cpp:105`, scannav-04). Auto-fit picks
height/width/page by one aspect-ratio comparison at 1.25 (scannav-05). The bridge renders at
**computed DPI from requested pixel width — zoom granularity is a UI decision, not a render
one** (`generator_pdf.cpp:1081`, PW-04): the bench server can accept a target pixel width and
derive dpi in one line, keeping 140/220 as cache-friendly defaults. Without tiles, clamp near
4× (scannav-04's own rule). A loupe is a **small high-dpi crop request (+50% margin), not a
10× whole-page raster** (`magnifierview.cpp:29`, scannav-14) — PyMuPDF `clip=` is the same
primitive. Dark/recolor reading modes are **post-raster pixel ops** — CSS filter on the PNG,
zero server change (scannav-14).

### 9 · One undo stack over everything, with identity [M–L]
The bench runs **three uncoordinated undo systems** (append-only manifest, 20-deep server
byte-undo, Blink-native). Okular runs ONE document-level QUndoStack; **every mutation is a
command whose redo() IS the mutation** (`document.cpp:2133`, AU-01 ↓ — audit: four form-edit
paths, not five, and one dialog does mutate live state). Keystrokes coalesce **with zero
timers** — merge iff new state == successor's previous state and same edit class, break on
newline (`documentcommands.cpp:337`, AU-02). Drags merge by command id until a gesture-end
terminator (AU-11). **The stack's clean marker IS the dirty flag** — save/close UX falls out
of one integer comparison (AU-03). Every undoable object gets a **UUID at attach**
(`page.cpp:653`, AU-09), and after a save the entire stack **re-binds pointers by UUID or the
swap aborts** — undo history survives saving (AU-10). Bench repair sites keyed by line
numbers break under edits; UUID identity is the fix the manifest needs regardless of any
other adoption.

### 10 · A Reviews panel over repair sites [M]
One flat model + **three individually-toggleable stacked filters** (current-page / group-by-page
/ group-by-author) + a text filter line; each toolbar toggle flips one proxy and persists
(`side_reviews.cpp:124`, AU-04 ↓). Jump-to maps a row to a viewport **centered on the item's
normalized rect** — page AND position (AU-05); for the bench: raster scroll + markdown line
anchor from one click. Refresh is an **incremental per-page diff, never a full rebuild**
(`annotationmodel.cpp:151-239`, AU-06 ↓) — the exact anti-pattern lesson for B22's whole-file
rebuild. Provenance is stamped at creation from configured identity and **runtime-only flags
are stripped before persisting** (AU-08) — the manifest's missing who/when layer, plus the
rule that transient UI state never serializes. Two boundary rules from the same lane:
pipeline-authored entries get the **External flag** — reviewable and jump-to-able, but
modify/delete only where the contract permits (AU-13); and batch repairs group as **one
undoable macro** (AU-14).

### 11 · Watch, reload, swap — surviving the pipeline writing under you [M]
- **KDirWatch + 750 ms quiet-window debounce**, deletion-aware (atomic save-via-rename safe),
  behind a user setting (`part.cpp:1874/578`, OBS-2).
- **Reload snapshots**: viewport (clamped to new page count), sidebar state, TOC expansion
  with rollback, rotation; retries while the writer is still writing (OBS-3).
- **mtime snapshot decides the conflict dialog**: unsaved edits + file changed on disk = the
  honest fork ("your edits can no longer be saved onto this file"), not a generic confirm
  (`part.cpp:1362`, OBS-4) — the upgrade to the bench's `confirm()`.
- **SwapBackingFile**: after save, swap the document identity under the view — undo stack
  re-bound, Page pointers transplanted, only UrlChanged notified; **rendered pixmaps and the
  user's place survive their own save** (`document.cpp:4437/4457`, OBS-5 ↓, PW-11). This is
  the architectural answer to "save then reload loses everything" — bench edition: patch
  changed line nodes, keep scroll/caret/undo. **⚠ Audit hazard:** the abort path returns
  false *after* the generator has already swapped its backing file, and emits **no observer
  notification** — a silent half-swapped state; a bench port must notify on the failure
  branch, or it inherits the bug.

### 12 · Observability grammar — typed changes, severity ladder, honest toasts [S–M]
- **DocumentObserver: 7 notify methods + one eviction veto, with typed change flags**
  (Pixmap=1, Highlights=4, Annotations=16…, `observer.h:48`, OBS-1): the bench's ~1 s rebuild
  exists because nothing tells surfaces *what kind* of change happened. Flags first; the
  rebuild fix follows.
- **Severity ladder**: generator error/warning → inline banner; notice → transient OSD toast;
  modal only as fallback; **open-failures are captured into the open result, never toasted
  mid-run** (`generator.h:475`, OBS-7 ↓) — maps directly onto converter-job errors vs the live
  widget surface.
- **OSD toasts with reading-length-proportional timeouts** (500 + 100·chars ms), click-dismiss,
  pinned mode instructions ("Draw a rectangle around the table… press Esc to clear") that
  never steal focus (`pageviewutils.cpp:220`, OBS-6, OBS-12) — the bench's implicit modes have
  zero in-surface guidance today.
- **The renderer's own complaints are damage evidence**: poppler's error stream is captured
  per-document into logs (`generator_pdf.cpp:580`, PW-12). PyMuPDF's `Tools.mupdf_warnings()`
  per page into the bundle's evidence layer would flag suspect pages before a human reaches
  the bench.
- **Memory as budgets, not vibes**: profiles as fractions of measured free RAM, farthest-page
  eviction with a visible-page veto, free-RAM probe cached ~1.9 s, single-request oversize
  refusal at 100× screen (OBS-9, LAT-05/06/07/14 — with the audit's 1900 ms correction).

### 13 · Strategic: the paged markdown reading surface [L]
`TextDocumentGenerator` turns any reflowable format into a paged, searchable, linked book:
**layout once at fixed page size; render page N = clip + translate at N·pageHeight**
(`textdocumentgenerator.cpp:319/407/421` — hand-checked). Headings/links map through cursor
positions to per-page viewports and ObjectRects: **TOC, internal anchors, search, selection,
and even PDF/HTML/ODF export fall out of the one model** (GEN-01/02/03, GEN-12). The markdown
backend is **277 lines across its two files**; txt is 72 (41 converter + 31 generator)
(GEN-04). Layout is whole-document at load — no incremental pagination exists (the §3 null
that makes server-side pagination the safe port). Two audit-sharpened caveats:
**(a)** TDG is NOT threaded — layout+render sit on the main thread (GEN-07); in a browser
bench that argues for server-side or worker-side pagination, never main-thread reflow of a
whole book. **(b)** the piggybacked text-extraction that makes search "free" fires only for
threaded generators — TDG family pays a synchronous text-page build on first search of each
page (GEN-06+07 joined by the audit).
**Why it matters:** the bench's markdown pane is an *editor* being used as a *reader*. A paged
read view over the bundle (server-paginated) makes the ~1 s whole-file DOM irrelevant for
reading, gives page-addressable coordinates that match the raster pane, and puts FP's own
output through the same reading machinery as the source PDF.

### Ranked out of the top list, still live

- **Tiles for deep zoom [M]** — poppler's `renderToImage` sub-rect is the native tile
  primitive (PW-02, *unaudited lane*); Okular's gate — on when requested pixels > 4× screen
  AND < 75% of the page visible AND a nonzero rect (the audits' fourth conjunct), off below
  3× — plus the 4×4-grid/2 MP quadtree store with distance eviction (LAT-04/05, GEN-11).
  PyMuPDF `get_pixmap(clip=…)` is the same primitive. Ranked out only because the bench's
  fixed zoom steps cap raster sizes today; this becomes candidate 8's other half the day free
  zoom ships.
- **Forward-instead-of-die single instance [S · widget]** — the widget already holds the
  `Local\file-portal-card` mutex; Okular adds the missing half: the losing launch **forwards
  its open request to the winner** (openDocument + tryRaise), with a capability probe deciding
  adopt-as-tab vs new window (OBS-10).
- **Cheap nav wins [S]** — non-continuous layout + wheel-at-edge page turn as the shippable
  intermediate before full continuous scroll (scannav-08); bold-current-branch TOC + filter
  box (scannav-11); quarter-viewport thumbnail follow (scannav-10 — its 200/2000 ms numbers
  were the audit's label-swap catch; thumbnail scroll itself is undebounced).
- **Parallel text-page pre-extraction** — while rasterizing a page, extract its text in a
  parallel worker so search/selection are warm before anyone asks (LAT-11).
- **Keep typography on PyMuPDF spans** — poppler-qt5's TextBox is geometry-only; span-level
  font name/size/flags (heading/emphasis detection, drop-cap repair) are strictly richer in
  PyMuPDF (PW-05, *unaudited lane*).

### Pipeline-lane extras (not bench UX, still money)
- **XY-cut reading-order reference**: ~714 lines, self-calibrating thresholds (word_spacing×2,
  line_spacing×2, 10% X-noise floor), column gaps detected as per-line max spaces promoted to
  their own histogram — portable to Python over PyMuPDF rawdict as an independent
  reading-order/column oracle (TG-03..07; audit: the cut rule has a third branch and the noise
  floor is X-only — read the audit notes before porting).
- **pdftotext's default reading-order mode as a free diff-oracle** against PyMuPDF block order
  for two-column books (PW-06, Inferred); poppler 26.01 added an explicit ReadingOrder API.
- **Tagged-PDF structure trees** (author-declared reading order) are reachable only via
  poppler's glib frontend — neither Okular-qt nor PyMuPDF sees them; a small sidecar dump tool
  could feed conversion-quality checks (PW-09, Inferred).
- **OCG layers**: render with watermark/stamp layers disabled before OCR/figure capture —
  PyMuPDF `get_ocgs`/`set_layer` (PW-10).
- **Page labels** (i, ii, xiv…): `label ≠ ordinal` test + label→index map fixes the
  front-matter page-number confusion at the bench (scannav-12; PyMuPDF exposes pageLabels).
- **Embedded /Thumb probe** before rasterizing sidebar thumbnails (PW-08 — Okular itself never
  uses it).
- **Central-pixel inclusion** as the universal "which cell/zone does this glyph belong to"
  rule (TG-12) — relevant to zone attribution in the audit pipeline, not just tables.

## §2 What the audit layer changed — corrections carried into this digest

The 7 Opus audit lanes checked **404 audit rows across the seven code lanes (404 MATCHES)**
and then attacked mechanisms and tags. The twelve most consequential corrections are carried
below and folded into §1; every filed correction, verbatim, is in the evidence dump.

1. **LAT-12 falsified in part**: the sweep's "thumbnails debounced 200 ms after scrolling" is
   wrong — the 200/2000 ms labels were swapped (200 ms = setup, 2000 ms = resize) and
   **thumbnail-list scrolling is wired straight to the request slot with no timer at all**.
   The fp advice "copy Okular's sidebar-scroll debounce" recommended something Okular does not
   have. (The queue/visible-only halves of the finding stand.)
2. **LAT-06 number**: free-RAM probe cache window is **1900 ms** (`document.cpp:462`,
   `kMemCheckTime - 100`), not 2 s.
3. **LAT-04/GEN-11 — the tiling-on gate has a FOURTH conjunct** both findings' quotes
   omitted: `&& normalizedArea != 0` (a null rect never starts tiling; it routes those
   preloads to a discard branch). Caught independently by two audit lanes, confirmed by the
   orchestrator's own read of line 1326. The hysteresis itself stands.
4. **S-01**: whole-doc search is event-loop-chunked but **not streaming** — highlights render
   only in the terminal branch. "First matches appear immediately" is a bench *proposal*.
5. **S-06**: the 5%-visibility jump rule carries a second conjunct (`moveViewport`) — only the
   findbar and presentation search move the viewport; the sidebar filter never scrolls.
6. **TG-11 port-critical**: divider guessing consumes **per-character + synthetic-space
   entities**, not words (`m_words` is a misnomer). A words-only port fails.
7. **TG-13**: the bridge appends `\n` at **every line end** (word with no successor), not at
   page end — Okular's own hyphenation handling depends on it.
8. **GEN-06+GEN-07 joined**: text-extraction piggyback is threaded-generators-only, so the
   markdown/epub family pays a synchronous first-search text-page build.
9. **AU-01**: **four** form-edit command paths, not five; and "UI code never mutates state
   directly" is falsified by `annotationpropertiesdialog.cpp:168-169` (prepare/snapshot-then-
   commit, not command-performs-mutation).
10. **AU-12**: "Page::removeAnnotation destroys the object" is refuted by `page.cpp:668-692` —
    the sweep inherited a **stale comment in Okular's own source** (`document.cpp:1038`). The
    tree contradicting its own comment is docs/45 Family-1's shape, in someone else's codebase.
11. **GEN-05/GEN-10/OBS-1/OBS honest-nulls**: a census said 43 where the tree says 42; a
    DjVu-cache contrast is void (`setCacheEnabled(false)` at construction); "30+ emission
    points" reproduces at 16–22 by named greps; one absence-search sentence was written
    broader than the search that grounds it (KMessageWidget also lives in
    `ui/annotationwidgets.cpp` — the conclusion survives, the sentence as written does not).
12. **Port-consequential batch, surfaced by the critic pass**: the 512 px preload expansion is
    **vertical-only** and preloading is **skipped entirely under Low** (scannav-09/LAT-03);
    the current-page notification **includes the sender** — exclude-self is the port's job
    (scannav-09); with the OSD off, **warnings are dropped entirely**, and clearing the banner
    re-shows an empty one — a port inherits both unless fixed (OBS-7); the render-abort path
    is compile-time conditional on `HAVE_POPPLER_0_63` (LAT-10); Normal's memory budget takes
    the **larger** of its two clauses, not their sum (OBS-9); and AU-13 repeats AU-12's
    inherited stale-comment error in its "before destroying" phrasing.

**Tag downgrades (23 filed — GEN-05's is a number correction, its tag already Observed)**: the
dominant defect class across all lanes was **"caller+callee read" presented as a second
method** — one instrument (source reading) applied to two sites of one
call chain. The audits let genuinely different second methods stand (autotests, kcfg schema,
cross-module consumers) and downgraded the rest to Observed: LAT-12/14, S-01/06/10, TG-11/13,
GEN-02/05/10, AU-01/03/04/06/07/10/11/12, OBS-5/7, scannav-01/02/03. **No finding was
fabricated; no citation failed.** The lesson is the House's own SYM-001 at fleet scale, and it
held even with the law's preamble in every prompt: lanes tag honestly under pressure, but
"differently-shaped" needs enforcement teeth, not prose.

## §3 What Okular does NOT have (measured absences worth knowing)

Each absence was grounded by a named search in a lane whose instrument passed both calibration
probes; the searches are in the evidence dump.

- **No match counter anywhere** — no "N of M" UI exists; feedback is the red field + wrap
  toast. (The bench can do better cheaply; Okular chose not to.)
- **No percent progress for document open in core/part** — only a busy state and page-count
  toast after (the generators/ subtree was NOT searched for internal progress — that half is
  UNREAD, not absent; the sweep's own honest-null says so).
- **No wall-clock debounce on main-view pixmap requests** — scroll-settle gating replaces
  timers (and thumbnail scroll has none at all — see LAT-12's correction).
- **No undo depth limit** — the QUndoStack is unbounded (`setUndoLimit` = 0 hits).
- **No TextPage persistence** — text layers are rebuilt per session, never serialized.
- **No persistent on-disk pixmap/tile cache** — FP's server-side PNG cache is a capability
  Okular *lacks*, not one to copy.
- **No incremental pagination in TextDocumentGenerator** — layout is whole-document at load;
  the null that makes server-side pagination the safe port for §1 candidate 13.
- **No use of poppler's native search, embedded thumbnails, or (in qt5) tagged-PDF structure**
  — PW-07/08/09: upstream capabilities Okular leaves on the table that FP can take directly.
- **No GPU/OpenGL page compositing in the desktop view** (latency lane's absence probe) — all
  the latency wins in §1 are CPU + scheduling discipline. Encouraging for a browser bench.

## §4 The findings, by lane

*Tags are post-audit. `↓` = downgraded (reason inline). Full mechanisms, all citations,
second methods, per-lane negative controls, honest nulls, and residues: the evidence dump
(`dumps/evidence/`, this commit's ledger row has the digest).*

### Latency & rendering (sweep: Fable; audit: Opus 5, 67 citations, 67 MATCHES)

| id | tag (post-audit) | finding | load-bearing numbers | anchor citation |
|---|---|---|---|---|
| LAT-01 | Verified | Single priority-sorted request queue: visible=1, thumbnails=2, presentation=0, preloads=3/4/5 | Priorities 0-5 = relative rank constants (ui/priorities.h:14-19); lower number wins. | `ui/priorities.h:14` |
| LAT-02 | Verified | Requests gated on scroll-settle: kinetic scrolling suppresses pixmap requests until it stops | 0 timers; gating is purely QScroller state (pageview.cpp:4365). | `ui/pageview.cpp:4365` |
| LAT-03 | Verified | Neighbour preload: viewColumns() pages each side at priority 4, dropped if they would evict closer pages | viewColumns() pages preloaded per side (pageview.cpp:4469); 512 px viewport expansion margin (pageview.cpp:4379); priority 4 (priorities.h:15). | `ui/pageview.cpp:4469` |
| LAT-04 | Verified | Tiled rendering activates above 4x screen pixels, deactivates below 3x (hysteresis); visible area must be <75% of page — audit (two lanes independently): the on-gate has a FOURTH conjunct the quote omits — `&& normalizedArea != 0` | ON > 4x screenSize device pixels AND normalizedArea < 0.75 (document.cpp:1326); OFF < 3x screenSize (document.cpp:1373); screenSize = dpr^2 * screen w*h pixels (document.cpp:1304). | `core/document.cpp:1326` |
| LAT-05 | Verified | Tile store: 4x4 grid quadtree, 2,000,000 px max per tile, eviction by Manhattan distance, visible tiles immune | 16 initial tiles = 4x4 grid of 0.25-normalized cells (tilesmanager.cpp:101-106); TILES_MAXSIZE 2,000,000 = max pixels per tile pixmap before split (tilesmanager.cpp:18); 4 = bytes per pixel in memory accounting (tiles… | `core/tilesmanager.cpp:18` |
| LAT-06 | Verified | Memory profiles: Low frees all, Normal caps at RAM/3, Aggressive/Greedy free half the overshoot; free-RAM probe cached 2 s — audit: free-RAM probe window is 1900 ms (document.cpp:462, kMemCheckTime-100), not 2 s; profiles/budgets exact | RAM/3 Normal budget (document.cpp:268); /2 halving of overshoot (273,279,286); RAM/2 Greedy floor (284); 2000 ms probe cache + cleanup cadence (171, 2443); 1 MiB preventive-cleanup trigger, pixmap bytes = 4*w*h (1406-… | `core/document.cpp:264` |
| LAT-07 | Verified | Whole-page eviction picks the page farthest from the viewport; the view vetoes unloading visible (+/-1) pages | +/-1 neighbour protection radius under Aggressive/Greedy (pageview.cpp:1380); farthest-page-number distance metric (document.cpp:401). | `core/document.cpp:401` |
| LAT-08 | Verified | Progressive rendering: poppler streams partial images after 500 ms, painted as partial pixmaps | 500 ms = suppression window before the first partial update is reported (generator_pdf.cpp:1026-1027). | `generators/poppler/generator_pdf.cpp:1026` |
| LAT-09 | Verified | Placeholder paint: rescale the nearest existing pixmap from any observer; blank+icon only beyond 20x/0.25x rescale | 20.0 / 0.25 = max up/down rescale ratios before blanking; 60,000,000 px source-size guard (pagepainter.cpp:113-115). | `ui/pagepainter.cpp:105` |
| LAT-10 | Verified | Stale-render cancellation: abort flag polled by poppler, queue purge per observer on every new batch | 30 ms = retry poll when the generator is busy (document.cpp:1441). | `core/document.cpp:3141` |
| LAT-11 | Verified | Threaded pixmap generation with parallel text-page pre-extraction; rotation off the UI thread | 1 render thread + 1 text thread per generator (generator.cpp:67-77 lazily creates single mPixmapGenerationThread). | `core/generator.cpp:257` |
| LAT-12 | Observed ↓ | Thumbnail lane: own observer at priority 2, visible-only, debounced 200/500/2000 ms; preload priority defined but unused — audit: 200/2000 ms labels swapped; thumbnail scroll is UNdebounced; second method non-probative | 200 ms setup (thumbnaillist.cpp:356), 500 ms (629), 2000 ms resize (595); scroll itself undebounced (277) | `ui/thumbnaillist.cpp:654` |
| LAT-13 | Observed | Scroll input mechanics: QScroller kinetics (decel 0.3), wheel = finalPosition-delta/4 at 0 ms, resize debounced 200 ms | decel 0.3, max velocity 1 (pageview.cpp:420-421); wheel offset = angleDelta/4 px, 0 ms duration (3137); 100 px per wheel detent (4768); 200 ms resize debounce (1840); 60 fps drag-scroll (3523). | `ui/pageview.cpp:420` |
| LAT-14 | Observed ↓ | Dequeue guards: satisfied-skip, in-flight tile dedup, and a 100x-screen oversize drop (except Greedy) — audit: cited autotest cannot reach the guards described | 100x screenSize = max request pixel area outside Greedy (document.cpp:1381); warning emitted once per document (1383-1387). | `core/document.cpp:1312` |

### Search (audit: 64/64 MATCHES)

| id | tag (post-audit) | finding | load-bearing numbers | anchor citation |
|---|---|---|---|---|
| S-01 | Observed ↓ | Whole-doc search yields one page per event-loop turn via 0ms singleShot — audit: same-file second method; matches render only at search end (not streamed) | 0 ms singleShot interval = one page per event-loop iteration (document.cpp:1739) | `core/document.cpp:3607` |
| S-02 | Verified | Find-as-you-type: 700 ms debounce timer, min-length gate, red field below minimum | 700 ms debounce (searchlineedit.cpp:143); min 3 chars for sidebar filter (searchwidget.cpp:43); default FindAsYouType=true (okular.kcfg:354) | `ui/searchlineedit.cpp:143` |
| S-03 | Verified | Concurrent named searches: 4 fixed search IDs, per-ID RunningSearch state, per-ID colors | 4 search IDs (document.h:65-68); findbar color rgb(255,255,64) yellow, sidebar rgb(0,183,255) cyan (findbar.cpp:49, searchwidget.cpp:46) | `core/document.cpp:135` |
| S-04 | Verified | Per-page resume cursors (SearchPoint) make next/prev incremental within a page | 8 next/prev transition cases enumerated in the autotest matrix (autotests/searchtest.cpp:143-155, counting TEST_NEXT_PREV invocations) | `core/textpage.cpp:702` |
| S-05 | Verified | Cross-page traversal with wrap-around and a 3-second wrap notice | 3000 ms notice duration (document.cpp:1606); wrap sets page to 0 or pageCount-1 (document.cpp:1605,1608) | `core/document.cpp:1606` |
| S-06 | Observed ↓ | Viewport jumps only when the match (plus 5% margin) is not already visible, then centers it — audit: mechanism drops the moveViewport conjunct (sidebar filter never scrolls) | 0.05 normalized (5% of page) visibility buffer on each side (document.cpp:1664); scrollTo duration 0 when smoothMove false (pageview.cpp:4020) | `core/document.cpp:1664` |
| S-07 | Verified | Highlights are paint-time multiply-blended overlays, never baked into the page raster | darker(150) = frame 1.5x darker than fill (pagepainter.cpp:360); repaint rect expanded -1,-1,+3,+3 px around the page item (pageview.cpp:1343) | `core/page.cpp:590` |
| S-08 | Verified | Three whole-doc modes: exact phrase, all-words, any-words with per-word hue-rotated colors | 60 degrees max hue spread divided across wordCount-1 words (document.cpp:1803); default mode GoogleAll (searchwidget.cpp:44,66) | `core/document.cpp:1803` |
| S-09 | Verified | Thumbnail sidebar doubles as the results list: filters to matching pages after whole-doc search | Thumbnail pixmap re-request delayed 200 ms after rebuild (thumbnaillist.cpp:356) | `core/document.cpp:1872` |
| S-10 | Observed ↓ | Page text extracted lazily during search, cached in a RAM-scaled FIFO — audit: same-file second method; textGenerationDone caller uncited (generator.cpp:428) | Cache cap per 512MB RAM: 2 (Low) / 50 (Normal) / 250 (Aggressive) / 1250 (Greedy) text pages (document.cpp:5011-5027); counts cached TextPage objects | `core/document.cpp:1720` |
| S-11 | Verified | Cancellation is a cooperative flag checked between pages; a cancel still delivers a just-found match | 1 global cancel flag covering all 4 search IDs (document.cpp:3714-3717 vs document.h:65-68) | `core/document.cpp:3716` |
| S-12 | Verified | Not-found feedback = red input field; busy indicator only after 100 ms | 100 ms delay before showing the busy indicator (searchlineedit.cpp:305); 22x22 px indicator (searchlineedit.cpp:286) | `ui/searchlineedit.cpp:254` |
| S-13 | Verified | Matching is Unicode-NFKC-normalized and hyphenation-aware across line breaks | 70 = percent Y-overlap threshold distinguishing same-line hyphen from line-break hyphen (textpage.cpp:772) | `core/textpage.cpp:807` |
| S-14 | Verified | Persisted search options and standard keybinding wiring around the findbar | Defaults: case-sensitive false, from-current-page true, find-as-you-type true (okular.kcfg:347-355) | `conf/okular.kcfg:350` |

### Scan, navigation & reading UX (audit: 59/59 MATCHES)

| id | tag (post-audit) | finding | load-bearing numbers | anchor citation |
|---|---|---|---|---|
| scannav-01 | Observed ↓ | DocumentViewport = page index + normalized re-position point, with a compact string serialization — audit: cited test never round-trips a viewport string | rePos defaults normalizedX=0.5, normalizedY=0.0 (document.cpp:5116-5117) | `core/document.h:1301` |
| scannav-02 | Observed ↓ | Viewport history: append only on page CHANGE, same-page scrolls overwrite in place; 100 in RAM, 10 persisted — audit: three functions in one file = one instrument | 100 = max in-memory history entries; 10 = entries saved to docdata XML | `core/document.cpp:167` |
| scannav-03 | Observed ↓ | Per-document view-state restore via docdata XML: viewport history, rotation, zoom value+mode, continuous, viewMode, trimMargins; autosaved every 5 minutes — audit: serializer-vs-deserializer mirror check = consistency, not corroboration | 5*60*1000 ms autosave interval (document.cpp:2436); 10 history steps saved (see scannav-02) | `core/document.cpp:2436` |
| scannav-04 | Verified | Zoom: 16-step ladder 12%-10000% with fit-width/fit-page factors SORTED INTO the ladder; clamps 0.1 and 4.0 (100.0 with tiles) | 16 ladder steps (kZoomValues, pageview.cpp:105); clamp min 0.1 / max 4.0 or 100.0 (3755-3759); drag zoom gain deltaY/500 (2024) | `ui/pageview.cpp:105` |
| scannav-05 | Observed | Auto-fit decides fit-height vs fit-width vs fit-page by comparing UI and page aspect ratios against a 1.25 threshold | 1.25 aspect-ratio threshold (3437); 6 px column margin, 12 px row margin (3653-3654) | `ui/pageview.cpp:3437` |
| scannav-06 | Verified | Trim Margins: bounding box auto-measured from the RENDERED image by scanning for non-paper-color pixels, then expanded 4% and capped at 50% shrink | 0.04 crop expand ratio; 0.5 min crop ratio (margins), 0.20 (selection) - fractions of page dimension (pageview.cpp:3385-3399) | `core/utils.cpp:90` |
| scannav-07 | Verified | Trim To Selection: one user-dragged normalized rect applied to ALL pages, via a dedicated one-shot mouse mode | 0.20 min crop ratio for selection mode (pageview.cpp:3399) | `ui/pageview.cpp:2538` |
| scannav-08 | Verified | Page layout is a virtual table: per-column max width x per-row max height, pages centered in cells; non-continuous renders ONE row; wheel at scroll edge turns the page | ViewColumns default 3 (kcfg:297-298); ScrollOverlap default 0 percent of viewport height retained between page-steps (kcfg:292, pageview.cpp:4057) | `ui/pageview.cpp:4181` |
| scannav-09 | Verified | Scroll-to-current-page sync: nearest-to-center page (4px left bias) plus the page fraction under the center, broadcast to all panels excluding the sender | 4 px leftward center bias (4452); 512 px preload margin around viewport (4379); preload depth = viewColumns() pages each direction (4469) | `ui/pageview.cpp:4452` |
| scannav-10 | Verified | Thumbnail panel follows the viewport: select + ensureVisible with a quarter-viewport vertical margin, behind a default-on setting — audit (latency lane): the 200/2000 ms labels are swapped (200=setup, 2000=resize) and thumbnail SCROLL is undebounced (thumbnaillist.cpp:277) | yOffset = max(panel/4, thumb/2) px (380-381); request debounce 200/500/2000 ms per event type (356, 629, 595) | `ui/thumbnaillist.cpp:379` |
| scannav-11 | Verified | TOC sync is highlight-only (bold current branch), driven by viewport, with a filter-search box over the tree | — | `ui/toc.cpp:99` |
| scannav-12 | Verified | Minibar swaps in a page-LABEL editor (roman numerals etc.) when any label differs from its ordinal; label-to-page map with completion | validator range 1..pages (minibar.cpp:446-452); slider tick interval max/10 (part.cpp:2167) | `ui/minibar.cpp:91` |
| scannav-13 | Verified | Bookmarks are per-VIEWPORT, not per-page: the exact scroll position lives in a KBookmark URL fragment; fuzzy-matched at 1e-6; inline rename | 1e-6 normalized-coordinate tolerance for viewport equality (bookmarkmanager.cpp:76-79) | `core/bookmarkmanager.cpp:436` |
| scannav-14 | Verified | Magnifier renders a 10x page through the normal request pipeline but fetches only the viewed region +50% margin; accessibility color modes are post-raster CPU image ops | SCALE 10x (magnifierview.cpp:29); request margin +-50 percent of viewed rect (138-143); luma coefficients 0.2126/0.7152/0.0722 (pagepainter.cpp:332); 8 pixel-op modes + Paper (317-343) | `ui/magnifierview.cpp:29` |

### Text geometry & selection (audit: 42/42 MATCHES)

| id | tag (post-audit) | finding | load-bearing numbers | anchor citation |
|---|---|---|---|---|
| TG-01 | Verified | Universal text-geometry currency: 0..1 page-normalized doubles (NormalizedRect), zoom-independent | — | `core/area.h:71` |
| TG-02 | Observed | Text model: flat list of per-character TinyTextEntity (text + rect only), NFKC-normalized | — | `core/textpage.cpp:123` |
| TG-03 | Verified | Reading order fixed once per page at setTextPage: remove spaces, build words, XY-cut, re-insert spaces, re-flatten | — | `core/page.cpp:568` |
| TG-04 | Observed | Word assembly thresholds: 60% y-overlap AND exactly zero horizontal gap | — | `core/textpage.cpp:1143` |
| TG-05 | Observed | Line assembly: sort by top, join at 70% y-overlap, sort each line by left | — | `core/textpage.cpp:1235` |
| TG-06 | Observed | Page segmentation: XY-cut with per-region statistical thresholds (word_spacing*2, line_spacing*2, 10% noise floor) | — | `core/textpage.cpp:1482` |
| TG-07 | Observed | Space insertion: synthetic ' ' entities with real gap rects, inserted wherever in-line gap != 0 | — | `core/textpage.cpp:1700` |
| TG-08 | Verified | Selection algorithm: two normalized cursor points -> nearest entities in reading order -> every entity between the two list positions | — | `core/textpage.cpp:535` |
| TG-09 | Observed | Multi-page drag: per-page RegularAreaRect list; middle pages select whole page via null points | — | `ui/pageview.cpp:3565` |
| TG-10 | Observed | Selection/highlight rendering: multiply-blend fill plus darker frame over the raster | — | `ui/pagepainter.cpp:357` |
| TG-11 | Observed ↓ | Table tool full mechanics: drag region, auto-guess dividers by whitespace tick sweep, click to add/remove (3 px snap) — audit: consumes per-CHAR + synthetic-space entities, not words; second method proves reachability only | — | `ui/pageview.cpp:3020` |
| TG-12 | Observed | Table cell extraction: per-cell rect intersection -> text(CentralPixel), TSV + HTML clipboard, in-cell newlines flattened | — | `ui/pageview.cpp:2822` |
| TG-13 | Observed ↓ | Poppler bridge: lazy per-page textList(Rotate0), per-CHAR boxes divided by page size; text pages evicted under memory pressure — audit: newline is per LINE-end, not page-end; second method covers lazy half only | — | `generators/poppler/generator_pdf.cpp:1637` |
| TG-14 | Verified | Search matches: cross-entity incremental matcher with per-searchID resume point; match area = merged per-char rects | — | `core/textpage.cpp:885` |

### Annotations, undo & review panel (audit: 42/42 MATCHES)

| id | tag (post-audit) | finding | load-bearing numbers | anchor citation |
|---|---|---|---|---|
| AU-01 | Observed ↓ | One document-level QUndoStack; every annotation and form mutation is a pushed command — audit: FOUR form-edit paths, not five; 'UI never mutates directly' falsified (annotationpropertiesdialog.cpp:168) | — | `core/document.cpp:2133` |
| AU-02 | Verified | Typing coalescing with no timers: mergeWith by state-adjacency plus edit-type classification | — | `core/documentcommands.cpp:337` |
| AU-03 | Observed ↓ | Dirty state is the undo stack's clean marker; save/close UX falls out for free — audit: caller+callee = one instrument, not a second method | — | `core/document.cpp:2138` |
| AU-04 | Observed ↓ | Reviews panel = one flat annotation model + three stacked, individually-toggleable proxy models — audit: kcfg corroborates toggle persistence, not the proxy stack | — | `ui/side_reviews.cpp:124` |
| AU-05 | Observed | Jump-to-annotation: activated row maps back through proxies and centers viewport on the item's rect | — | `ui/side_reviews.cpp:250` |
| AU-06 | Observed ↓ | Live panel refresh is an incremental per-page diff, never a full rebuild — audit: caller+callee = one instrument | — | `core/document.cpp:3253` |
| AU-07 | Observed ↓ | Annotations composite as overlays on the cached raster; only ExternallyDrawn types force re-render — audit: Multiply citation is the selection path, not annotation highlights; one instrument | — | `ui/pagepainter.cpp:213` |
| AU-08 | Verified | Provenance stamped at creation from config identity; serialized with the annotation | — | `ui/pageviewannotator.cpp:836` |
| AU-09 | Verified | Stable identity for every undoable object: okular-{UUID} assigned at attach, resolved by name everywhere | — | `core/page.cpp:653` |
| AU-10 | Observed ↓ | Undo history survives save/reload: commands re-bind their pointers by uniqueName or the swap aborts — audit: caller+callee = one instrument | — | `core/document.cpp:4437` |
| AU-11 | Observed ↓ | Drag coalescing: command id + completeDrag terminator makes a whole gesture one undo step — audit: caller+callee = one instrument (mechanism itself re-verified, ids 1/5 exact) | — | `core/documentcommands.cpp:222` |
| AU-12 | Observed ↓ | Deleted-object ownership flips with undo state via a m_done flag on each command — audit: 'removeAnnotation destroys the object' refuted by page.cpp:668-692 (stale source comment) | — | `core/documentcommands.cpp:71` |
| AU-13 | Observed | Mutation gating by per-annotation flags: DenyWrite/DenyDelete and External-with-capability | — | `core/document.cpp:3273` |
| AU-14 | Observed | Dual-path persistence with graceful fallback, and macro grouping for batch operations | — | `core/document.cpp:4786` |

### Observability & robustness (audit: 74/74 MATCHES)

| id | tag (post-audit) | finding | load-bearing numbers | anchor citation |
|---|---|---|---|---|
| OBS-1 | Verified | DocumentObserver: 7 notify methods + one veto, with typed change flags — audit: '30+ emission points' sentence unsupported (16-22 by named greps); finding otherwise exact | Flag values 1/2/4/8/16/32/64 from observer.h:48-54 (bitmask of what changed); 13 implementors counted from grep of 'public Okular::DocumentObserver' in ui/*.h + part.h | `core/observer.h:48` |
| OBS-2 | Verified | File watch: KDirWatch with 750 ms restart-debounce, deletion-aware, symlink-aware | 750 ms = debounce window between last file event and reload attempt (part.cpp:1874); WatchFile default true (okular.kcfg:196) | `part.cpp:578` |
| OBS-3 | Observed | Reload preserves viewport, sidebar tab, TOC expansion, rotation, presentation mode; retries on failure | — | `part.cpp:1905` |
| OBS-4 | Observed | Unsaved-changes vs external-change conflict: mtime snapshot decides which dialog you get | — | `part.cpp:1362` |
| OBS-5 | Observed ↓ | SwapBackingFile: post-save hot-swap that keeps undo stack, Page pointers, and viewport alive — audit: three reads of source = one instrument; content held under independent 110-line read | — | `core/generator.h:213` |
| OBS-6 | Verified | PageViewMessage OSD: corner toast with icon, length-based timeout, click-dismiss, resize-follow | duration = 500 + 100*chars ms when caller passes -1 (pageview.cpp:842-844); 60% of font height as message/details line spacing (pageviewutils.cpp:303); OSD default position 10,10 px (pageviewutils.cpp:210) | `ui/pageviewutils.cpp:220` |
| OBS-7 | Observed ↓ | Three-severity signal ladder: generator error/warning/notice, rendered as inline banner vs toast — audit: same defect; ladder itself reproduced exactly | — | `core/generator.h:475` |
| OBS-8 | Verified | docdata: per-document XML keyed by size+filename; viewport history, rotation, per-view zoom; three write triggers | 10 viewports persisted, 100 kept in memory (document.cpp:167-168); autosave every 5*60*1000 ms = 5 min (2436); filename = document byte size + '.' + name + '.xml' (2170) | `core/document.cpp:2170` |
| OBS-9 | Verified | Memory pressure: four profiles as fractions of measured free RAM, evicting farthest-from-viewport first | check cadence 2000 ms (171); floor 1 MiB allocated (1264); Normal cap totalRAM/3 (268); Greedy cap min(max(free,total/2),free+swap) (284); free-RAM probe cached kMemCheckTime-100 ms (462); oversize refusal >100x scree… | `core/document.cpp:171` |
| OBS-10 | Verified | Shell: DBus single-instance and cross-window tab adoption; recent files in config | — | `shell/shell.cpp:132` |
| OBS-11 | Observed | Open failure surfaces are context-aware; no percent progress for document open exists | — | `part.cpp:1144` |
| OBS-12 | Observed | OSD doubles as mode instruction channel: every tool switch posts a pinned how-to toast | 4000 ms for the page-count load confirmation (pageview.cpp:1116); -1 duration = pinned-or-length-based for mode instructions (4667, 4689, 4711) | `ui/pageview.cpp:1116` |

### Generators & the TextDocument pattern (audit: 56/56 MATCHES)

| id | tag (post-audit) | finding | load-bearing numbers | anchor citation |
|---|---|---|---|---|
| GEN-01 | Verified | TextDocumentGenerator: reflowable text becomes a paged book by fixed page size + y-slice clipping | markdown page = 980x1307 layout units, margin 45 (converter.cpp:112,119); txt/epub/fictionbook/mobipocket pages = 600x800, margin 20 (txt/converter.cpp:30,33; epub/epubdocument.cpp:25; fictionbook/converter.cpp:85,88;… | `generators/markdown/converter.cpp:112` |
| GEN-02 | Observed ↓ | Search comes free from one primitive: per-page TextPage; core loops pages, lazily extracting — audit: absence claim had no named search (claim itself re-verified true) | — | `core/document.cpp:1619` |
| GEN-03 | Verified | TOC and links come free from cursor-position signals; fractional page coordinates | — | `core/textdocumentgenerator.h:69` |
| GEN-04 | Observed | Format cost floor: a complete new format = one converter; txt is 41 lines, markdown 277 | wc -l this run: txt/converter.cpp=41, txt/generator_txt.cpp=31, markdown/converter.cpp=211 + markdown/generator_md.cpp=66 (=277 .cpp lines), epub/converter.cpp=450, fictionbook/converter.cpp=852 (lines of code per fil… | `core/textdocumentgenerator.h:52` |
| GEN-05 | Observed | Capability matrix: 11 feature flags; poppler declares 9, TDG family 3, comicbook 3 — audit: setFeature census is 42, not 43 (matrix itself correct; tag was already Observed) | 11 enum values counted at core/generator.h:203-215 (Threaded, TextExtraction, ReadRawData, FontInfo, PageSizes, PrintNative, PrintPostscript, PrintToFile, TiledRendering, SwapBackingFile, SupportsCancelling). Grep 'se… | `core/generator.h:203` |
| GEN-06 | Observed | Request lifecycle: sync/async split, priority-carrying requests, text extraction piggybacked on visible-page rendering | priority 0 = maximum (generator.h:677, ordering of PixmapRequest priority); request width/height are ceil(px * devicePixelRatio) (generator.cpp:563-564, pixel dimensions). | `core/generator.cpp:257` |
| GEN-07 | Verified | TextDocumentGenerator is NOT threaded: the free features cost main-thread rendering | 7 grep hits for the macro (occurrence count, all guards); 0 #define sites. | `core/textdocumentgenerator.cpp:264` |
| GEN-08 | Observed | Text geometry granularity: per-character normalized rects, computed from the live layout | 3 layout units = pseudo-character width for line breaks (textdocumentgenerator_p.h:58); 1-char cursor steps (i to i+1) define granularity. | `core/textdocumentgenerator.cpp:102` |
| GEN-09 | Verified | DjVu hidden text layer: s-expression tree filtered by granularity, word-first with line fallback | — | `generators/djvu/generator_djvu.cpp:202` |
| GEN-10 | Observed ↓ | ComicBook: pages stream lazily from archive entries; load probes only image headers — audit: djvu-cache contrast falsified (setCacheEnabled(false) at generator_djvu.cpp:76) | — | `generators/comicbook/document.cpp:182` |
| GEN-11 | Observed | Tiles are a core policy, not a generator one: auto-switch above 4x screen area — audit: same fourth conjunct — the real line 1326 has four clauses, not three | 4L * screenSize = tile-on threshold, 3L * screenSize = tile-off threshold (both compare requested pixmap pixel area to screen pixel area); 0.75 = max visible normalized page area for tiling (document.cpp:1326,1373). | `core/document.cpp:1326` |
| GEN-12 | Observed | Export falls out of the document model: PlainText/PDF/ODF/HTML for every TDG format | — | `core/textdocumentgenerator.cpp:475` |
| GEN-13 | Observed | Progressive render and cancellation are first-class request contract, opt-in per generator | — | `core/generator.h:214` |

### Poppler through the bridge + upstream docs (no audit lane; web partially blocked, declared)

| id | tag (post-audit) | finding | load-bearing numbers | anchor citation |
|---|---|---|---|---|
| PW-01 | Verified | Poppler partial-update render callbacks: bridge consumes them; armed only for first paint; 500 ms suppression | 500 ms = partial-update suppression interval (generator_pdf.cpp:1026-1027, timer.setInterval(500)) | `generators/poppler/generator_pdf.cpp:1116` |
| PW-02 | Verified | renderToImage sub-rect (x,y,w,h) is poppler's native tile primitive; Okular gates tiles at 4x screen pixels and <75% visible | 4L*screenSize = raster-pixel threshold; 0.75 = normalized visible-area ceiling (core/document.cpp:1326); tiles since poppler-qt 0.16 per generator.h:212 | `generators/poppler/generator_pdf.cpp:1104` |
| PW-03 | Verified | Cooperative cancellation callbacks exist for BOTH render and text extraction (poppler 0.63+), and the bridge wires them | since 0.63 = poppler-qt5 version introducing abort callbacks (qt5 Page docs) | `generators/poppler/generator_pdf.cpp:1064` |
| PW-04 | Observed | Continuous zoom via computed DPI: bridge derives fake DPI from requested pixel size, no fixed steps | 72.0 pt/inch implicit in pageSizeF units (loadPages line 714 divides by 72.0) | `generators/poppler/generator_pdf.cpp:1081` |
| PW-05 | Observed | qt5 TextBox is geometry-only: bridge consumes per-char boxes and synthesizes spaces; font/size/color exist in core TextWord but never cross the qt5 boundary | — | `generators/poppler/generator_pdf.cpp:1637` |
| PW-06 | Inferred | Poppler text ordering has three modes - reading order (default, undoes columns), physical layout, raw stream - and Okular exports in physical layout | 26.01 = poppler version adding ReadingOrder TextLayout; 0.16 = version adding text(rect, textLayout) (qt5 Page docs) | `generators/poppler/generator_pdf.cpp:1587` |
| PW-07 | Observed | Okular never calls Poppler::Page::search - poppler's search offers IgnoreDiacritics and AcrossLines flags Okular reimplements without | 0.73 = IgnoreDiacritics since-version; 21.05.0 = AcrossLines since-version (qt5 Page docs) | `generators/poppler/generator_pdf.cpp:253` |
| PW-08 | Observed | Page::thumbnail() - embedded PDF thumbnails, free of rendering cost - exists since poppler 0.12 and Okular never touches it | since 0.12 = thumbnail() introduction (qt5 Page docs); dpi 30 = current bench thumb raster (GROUND brief) | `https://poppler.freedesktop.org/api/qt5/classPoppler_1_1Page.html:0` |
| PW-09 | Inferred | Tagged-PDF structure tree (true reading order) is exposed by poppler's glib frontend only - qt5 has no structure classes and Okular has zero hits | — | `https://poppler.freedesktop.org/api/glib/PopplerStructureElement.html:0` |
| PW-10 | Observed | OCG layers: Okular consumes optionalContentModel and applies layer-state links; rendering honors layer visibility | — | `generators/poppler/generator_pdf.cpp:988` |
| PW-11 | Observed | SwapBackingFile: save/reload replaces the document underneath the view without re-rendering, regenerating only link rects | — | `generators/poppler/generator_pdf.cpp:573` |
| PW-12 | Observed | Poppler render-error stream is capturable: setDebugErrorFunction routes per-document parse/render complaints into the host's log | — | `generators/poppler/generator_pdf.cpp:580` |

## §5 Touchpoints with VW-E2-R2 (data-level only)

Codex's Visual Witness E2-R2 (docs/contracts/, in flight this same S112) captures page
primitives, candidates, tables, and text-overlap geometry. This lane makes **no claims about
that implementation** — these are shared-currency observations for whenever both bodies of
work sit on the table:

- **0..1 page-normalized rects (TG-01) are the natural shared coordinate space** — Okular,
  the bench overlays, and witness capture boxes become directly comparable if all three emit
  normalized-to-page geometry.
- Okular's word/line grouping thresholds (60% y-overlap + zero-gap for words, 70% for lines —
  TG-04/05) and the synthetic-space-rect trick (TG-07) are tested constants for grouping any
  char/word boxes, including witness-captured ones.
- **Central-pixel inclusion (TG-12)** is a clean membership rule for assigning glyphs to
  table cells/tracks — deterministic, no straddle double-counting.
- The XY-cut column-gap histogram move (TG-06) and pdftotext's default reading-order mode
  (PW-06) are independent oracles a witness-based table/column claim could be diffed against.
- Poppler's capturable render-error stream (PW-12) is witness-shaped evidence: the renderer
  complaining about a page is a mechanical damage signal.

## §6 Method, limits, residue

- **Fleet:** 8 sweep lanes (claude-fable-5) + 7 audit lanes (claude-opus-5), run
  `wf_61b440a5-0c1`, 2026-08-30; 1,580,245 + 793,482 subagent tokens and 396 + 145 tool uses
  across two waves (`Observed` from the orchestrator's own run notifications — the first audit
  wave died on the Fable session usage cap; re-run on Opus with sweeps replayed from cache).
  Sweep prompts carried docs/47 §3 in full; audits each carried a distinct lens and the
  sweep's verbatim JSON. A third pass — an independent Opus completeness critic over this
  digest against the evidence JSON — filed 22 defects (2 critical, on this document's own
  framing), all folded in before this text was committed.
- **Static reading only.** Nothing was compiled or executed; autotest corroboration means the
  test was READ, not run. Claims are about what the 20.08.0 tree says, not about runtime
  behavior measured live.
- **Poppler internals partially UNREAD:** gitlab.freedesktop.org (anti-bot), fossies (401)
  refused the web lane; upstream claims rest on poppler.freedesktop.org API docs and are
  tagged Inferred/External-Doc where the page text was not directly fetched. PW-06/PW-09 are
  Inferred. No Poppler source tree exists locally.
- **Okular 20.08.0 is five years old.** Upstream Okular/poppler have moved (e.g. poppler
  26.01's ReadingOrder). Constants quoted here are that tag's, deliberately: it is the tree on
  this machine, and the mechanisms — not the exact numbers — are the digest's cargo.
- **Lane residues** (full lists in the evidence dump): findTextInternalBackward's body,
  presentationwidget internals, mobile/ entirely, synctex, the forms/scripting subsystem
  (kjs), video/sound, generators {chm, xps, dvi, spectre, plucker, fax, ooo, mobipocket}
  beyond capability declarations, calculateStatisticalInformation's body (TG-06's histogram
  builder — read at call site only), and whether QTextDocument pagination cost is acceptable
  at book length (GEN residue: layout-once was read, never timed).
- **This digest is one lane's synthesis.** The findings are the fleet's; the ranking in §1 is
  mine (Fable lane, this sitting), and reasonable people could rank differently. Rab ranks
  last and best.

## §7 Disposition

- **Adopted: nothing.** No product, pipeline, bench, widget, vault, or lever changed. The
  Okular tree was read, never written. VW-E2-R2 paths untouched.
- **Registers:** one OPEN-TASKS §A row added at close pointing Rab at this digest's §1 for
  signature-level choices. No symptom rows changed (SYM-003/B22 are *addressed by* candidates
  here but remain open until something ships).
- **Where the evidence lives:** the full fleet JSON (sweeps + audits, ground digests,
  corrected downgrade metadata) is **`dumps/evidence/D0005-…okular-fleet-evidence-v2….json`**,
  sha256 `981f2959…`, 441,639 bytes — bytes are LOCAL (dumps private layer, gitignored); the
  tracked `dumps/LEDGER.md` row carries pointer + digest, and so does `MSG-FAB-0045`.
  **D0005 supersedes D0004** (same sweep/audit payload; D0004's derived downgrade map predated
  the critic pass, and its subject line ended in a clumsy clause — read D0005). The run
  journal remains in the session transcript dir. This document quotes ≤15-word source
  fragments only (GPL-2.0 tree, research use).
- **Next honest steps** (unsigned, in value order per §1): viewport sidecar (S), placeholder
  paint (S), trim (S), search suite (M), text-layer sidecar (M–L), table tool (M), unified
  undo + review panel (M–L), paged reading surface (L). None started, per the commission's
  boundary — this was the complete search, digested.

⟨claimed: Fable lane · Okular digest complete · adoption remains Rab's · 2026-08-30⟩
