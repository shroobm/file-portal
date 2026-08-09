# Changelog

All notable changes to File Portal are recorded here.
The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **S67 — THE CLOSEOUT CONTRACT, THE SYMPTOM INDEX, AND CI THAT ACTUALLY RUNS (2026-08-09,
  ThinkPad/receiver lane).** Full narrative in `sessions/S67-thinkpad-2026-08-09.md` — this entry
  covers the source changes only.
  - **Added `docs/21-session-closeout-contract.md`** — every session now ends structured: six
    epistemic tags with admission prices (`Verified` requires a second check that cannot fail the
    same way as the first), 6 core / 12 extended sections with an abort clause, derived-vs-authored
    split, and the rule that inference is never promoted to fact.
  - **Added `SYMPTOM-INDEX.md`** (repo root) — failures keyed on *what the system does when it's
    wrong*, for retrieval backward from a symptom without knowing which session produced it. Seeded
    with 17 rows from the Change Ledger and `docs/19`'s laws; grew to 20 during this session. Read
    at session open; `CLAUDE_README.md` §4 now binds the close ceremony to it.
  - **Fixed — CI had not run since 2026-07-13** (205 commits, ~4 weeks). It triggered only on push
    to `master` plus `pull_request`, while all work is direct-pushed to `feat/library-pipeline`.
    `.github/workflows/ci.yml` now runs on the feature branch and additionally lints
    `linux-converter` and runs its **51 tests** — the largest uncovered area and the code that
    writes the vault. Green on run `31336207277` (24 + 51). Filed SYM-018.
  - **Fixed — `linux-converter/converter/exporter.py`**: a committed `ruff format` violation in the
    `_receipt("supersede-held", …)` call. Formatting only, no behaviour change; it had been
    invisible because CI never covered that project.
  - **Fixed — unpinned linter made CI nondeterministic.** CI resolved ruff 0.16.2 from `ruff>=0.4`
    while local venvs held 0.15.20, and the newer default rule set failed code that lints clean
    locally. `ruff==0.15.20` pinned in `linux-receiver/requirements-dev.txt` and
    `linux-converter/requirements-dev.txt`, with the reason inline. Filed SYM-019.
  - **Guarded — `linux-receiver/allocator/rules.py`**: `_expand()`'s naive `datetime.now()` is
    deliberate; `{yyyy}/{mm}/{dd}` are folder names a human browses, so they must match the day the
    file was dropped. Satisfying ruff 0.16's DTZ005 with `tz=UTC` would file evening drops under
    tomorrow's date west of Greenwich. Comment + `noqa` at the call site; **no behaviour change**.
  - **Scoped — the `rust:` CI job** stays on `master` + `pull_request` via an `if:`. Enabling the
    branch surfaced pre-existing drift (`cargo fmt --check` fails across 8 files / 36 hunks in
    `windows-widget/src-tauri/src/`), which rotted because the desktop rebuild ritual runs
    `cargo clippy --all-targets -- -D warnings` and never `cargo fmt`. Left to the desktop lane
    with the five-step re-enable procedure in the workflow comment; Rust gating is unchanged from
    before, not newly red. Filed SYM-020. `cargo test` remains absent from CI for the same
    reason — unverifiable from Linux.
  - **Docs — the front door described a project that no longer exists.** `README.md` called
    `linux-converter` a "log-only skeleton" and the project an "early scaffold"; `docs/00`–`docs/09`
    contained zero mentions of the vault, Marker, the analyst pass, the audit or the bench; and
    `docs/20`, the accurate manual, had no inbound link from anywhere. README rewritten with an
    honest two-era Status and all seven code areas; scope banners added to all ten first-era docs;
    `docs/00`'s false skeleton claim deleted; `docs/01`'s transport line corrected to match
    `transfer.rs` (it documented a `--` the code deliberately omits); `docs/07` extended to the four
    subprojects it never mentioned, including `linux-converter`'s previously undocumented tests.

- **S66 — THE DUMMY-PROOF PASS: simulated first, then fixed (2026-08-07 → 08).** Rab's
  commission: "simulate the interactions and experience beforehand… frictionless… update the
  UI… open files via clicking the icon… engineering access via the widget… not so dense."
  Every change below traces to a friction point found by actually DRIVING the bench in a
  browser as a fresh user (Gate 1's list, in the session log).
  - **Bench UX (found → fixed):** the coach floated OVER the stage toolbar → now a docked
    band that can't cover controls; zone chips collided numbers and leaked table junk →
    clean tokens ("✓ Zone 1 · p396 · 5.6k", excerpt in the tooltip); the ⌖ badge was clipped
    to 56 px → a full-width info line ("located by text evidence: p396 (confidence 0.4)" /
    an honest ratio hint); ✂ never explained itself → the button narrates its own state
    ("drag a region first" → "insert crop at zone N"); search auto-jumped you away from your
    zone → results wait for your click (hit-count in the tab, clearable highlights); the
    Pages rail opened at page 1 → opens centered on YOUR page; the AI toast died at 7 s
    during a 60 s job → a live elapsed clock on the button and a sticky status; the 326-char
    instruction wall left the footer for the ? help; ⓘ shows everything about the patient
    (paths, sha16, survival, repair log, mode) straight from /api/state.
  - **The ◆ icon opens things ("Select a PDF"):** a server-enumerated picker over held /
    pending / anchor bundles and done-tray PDFs — bundles open repairable, **bare PDFs open
    in READING MODE** (browse/outline/search; every write path refuses with a plain
    sentence). `/api/open` is allowlist-contained to the pipeline's own roots (System32
    refused, proven).
  - **Widget 🗁 (Room header): engineering quick-access** — named allowlist targets only
    (events.jsonl, conversion ledger, all four last-words logs, receipts cache, held/
    pending/anchor/drop, the pipeline root, the Library clone, the repo) opening in
    Notepad/Explorer via `line::open_engineering`.

  **Proofs:** the fixes re-verified by a second simulated walkthrough (coach docked, badges
  readable, reader-mode writes refused, outside-path open refused, 0 console errors) ·
  acceptance **26/26** · clippy `-D warnings` clean · 20/20 tests · `node --check` clean ·
  build green — **exe `F28C58A8` staged for RAB** (supersedes 3DCDF88E; adds the 🗁 menu).
  Also this session: Rab's call executed — the Valentine rerun copy deleted, her repaired
  bundle verified in the slot first.

- **S65 — THE BENCH TEACHES, THE PARK LEARNS RESPECT, AND VALENTINE'S FIRST REPAIR
  SURVIVES ITS FIRST THREAT (2026-08-06 → 07).** The session of the graduation: Rab
  performed **Valentine's first real repair** (zone @1579 cropped from p234 — the ratio
  guess said ~120; the human vision model out-ranged it by 114 pages on a raw scan), and
  the arc's last unproven joint — the Bench window opening from the widget — was proven by
  his click.
  - **The bench teaches itself now** (Rab: "the information is lost… teach me, or create a
    help section"): a **? help sheet** (anatomy, the repair loop, the AI's rules, the
    safety net) and a **☰ step-by-step coach** — five steps checked off from REAL actions,
    auto-opens until one full loop is completed, then retires. The UI is served fresh per
    request, so F5 always gets the latest bench.
  - **`_enforce_hold` learned to respect human work**: held bundles can carry Repair Bench
    repairs now, and the park's rmtree-and-replace would have destroyed them. A
    repairs-bearing occupant keeps its slot; the incoming copy parks BESIDE it,
    timestamped. Found by chasing an anxiety **hours before Rab's live ⟲ re-run would have
    deleted his first repair**; proven on temp git-free dirs before the run ended.
  - **The docs/20 manual**: the complete user textbook + developer reference, committed as
    its own docs commit (`258cedc`).
  - **Acceptance harness matured**: baseline-aware (a live patient's prior repairs are the
    new normal, measured relative to what it copied) and moved to OS-assigned ports after
    the hardcoded port dialed Rab's LIVE bench through Windows SO_REUSEADDR — where his
    fail-closed `/api/repair` refused the stray probe. 26/26 green again.

  **The ⟲ live fire, end to end (Rab's click, 09:57–11:18 UTC):** Valentine's analyst-only
  re-run — 266 chunks, **249✓ / 16🛡 / 1✗ in 4,859 s**, one monster chunk pushing the
  heartbeat past a 300 s watch (lesson: the analyst's stall doctrine is 900 s, same as the
  converter's). Verdict stayed **fail** (her degeneration lives in the convert phase, as
  forecast) → the enforce gate parked it — and because the RUNNING process predated the
  fix, its old code overwrote the held slot exactly as predicted. **Nothing was lost**:
  the repaired bundle had been hash-verified into safekeeping first, and after the run it
  was restored to its slot (hash-identical, repairs + .bench-bak intact) with the rerun
  copy preserved beside it as `held/<sha16>--rerun-<ts>` — precisely the layout the fixed
  code now produces on its own. The night also produced Stage F's first unprompted
  production use: Rab ⚑-acknowledged the Damodaran alert himself at 09:51.

- **S64 — FOLDER MODE + THE AI ASSIST (built live 2026-08-04, closed 2026-08-06).** Rab's
  dawn commission: "open up any of the previous works… ITS ONLY THE FOLDER THAT MATTERS…
  implement an AI feature… a button that does an ctrl z on the ai models changes."
  - **Folder mode:** the bench opens ANY folder holding exactly one `.md` — held bundles,
    anchor copies, pending bundles, mid-conversions. `manifest.json` is now optional: without
    it there are no audit zones and no source lookup (said plainly on the glass), pages come
    from the PDF itself when one is found, and a minimal manifest is created on the first
    repair so provenance never goes unrecorded.
  - **The AI assist (`/api/assist`):** type an instruction → LOCAL qwen3:8b (the analyst's
    exact Ollama contract: `think: false`, `keep_alive: 0`, num_ctx 8192 — the Gemini API
    stays off by Rab's standing rule) rewrites ONLY the visible passage. **The analyst's
    link-fence applies verbatim**: every embed becomes an opaque ⟦IMG-n⟧ token before the
    model sees the text, and a reply that damages the token multiset is REFUSED, never
    patched. A no-op answer ("nothing to fix") is reported honestly and burns no undo slot.
  - **The ctrl-Z (`/api/undo`):** every applied AI change pushes a full body snapshot
    (bounded, 20 deep); ↩ restores the file BYTE-IDENTICALLY. AI line-drift is folded into
    the same zone-anchor arithmetic the repairs use, so zones below an edit stay addressable.
  - Python/HTML only — the staged widget exe `3DCDF88E` is unaffected and stays valid.

  **Proven live on the Damodaran sandbox:** a real qwen3 edit applied (5 lines → 7, the
  instruction followed), **all 313 embeds intact through the fence**, and undo restored the
  body **byte-identically**; the no-op path proven first by accident (the model correctly
  declined to change clean text — the assertion was wrong, the code was right). Acceptance
  stayed **26/26** after the rewrite. UI verified in-browser, 0 console errors.

- **S63 — THE BENCH GRADUATES: the Apple pass + the widget's fourth surface (2026-08-04).**
  Commissioned goodnight ("make it look like an app that could look aesthetically applicable
  on apple products… map it and make it real… I want the widget running with the repair bench,
  along with the dock, room, wall").
  - **The Okular pass (S62b live iteration, committed at this open):** the bench's reader grew
    real anatomy — a Contents/Search/Pages sidebar (the PDF's own 295-entry outline on
    Damodaran; full-text search over a whitespace-normalized, de-hyphenated per-page index
    with Okular-yellow hit highlights; a lazy thumbnail rail), page input + zoom, and
    **⌖ locate**: a zone's true page found by mining prose needles around the wreck and
    letting the text layer's pages vote — **9/10 of Damodaran's zones located by evidence**
    (corrections up to ~39 pages off the old line-ratio guess), the tenth falling back to
    ratio *labeled as such*. Raw scans (no text layer) degrade honestly. Plus a cp1252
    banner crash found by the preview launcher's console and fixed (`errors="replace"`).
  - **The Apple pass:** HIG-informed skin — system type stack (SF-first), translucent
    saturated-blur chrome materials on header/toolbars/footer, an Apple segmented control for
    the sidebar, hairline separators, the #f5f5f7 canvas with a Preview.app-style page stage,
    a toast pill, true dark mode. The factory's law survives the skin: terracotta still means
    exactly one thing.
  - **The graduation (docs/19 §7's own criteria-shaped step):** new `windows-widget/src-tauri/
    src/bench.rs` — the widget resolves a held bundle by the rows' existing `manifest.source`
    contract, finds a free port (7077–7096), spawns `prototypes/repair-bench/bench.py`
    detached (null stdio + a `bench-stderr.log` last-words file, `CREATE_NO_WINDOW`,
    `PYTHONIOENCODING`), **adopts it into the watcher's kill-on-close Job Object** (no
    orphaned bench servers by ANY widget exit — the S37 guarantee extended), waits for the
    server, and opens a dedicated **Repair Bench window** (created on the main thread; an
    existing window is renavigated + refronted, no label race). Surface row reads
    **Dock · Room · Wall · Bench**; every held row on both surfaces gains **🔧** beside
    ⟳ ⟲ ✓ (the S58 per-bundle law). The QUARANTINE SURVIVES GRADUATION: nothing imports the
    prototype — the coupling is one spawned, supervised, job-owned child process. The slow
    spawn+wait runs off the UI thread (the vault_check lesson).

  **Proofs:** 20/20 rust tests (4 new: the resolution contract, calm refusal on empty held/,
  port-scan skipping a bound port, script-path derivation from the repo layout) · clippy
  `-D warnings` clean (two real catches: an E0597 guard-lifetime and a needless borrow) ·
  `npm run build` green, exe **`3DCDF88E`** staged for RAB's adoption · **the exact spawn
  command proven against the REAL held Damodaran** (served its real dir, 10 zones, 1,356 pp,
  PDF found; killed clean) · harness render 0 errors with 🔧 invoking `bench_open` with the
  row's exact source · the Apple-skinned bench live in a browser, 0 console errors, light and
  dark. Honest bound: the WebviewWindow-open click itself is the one joint only Rab's adopted
  launch can prove live — a Claude-launched widget stays barred by law 3.

- **S62 — THE GATES: Stage E (queue + promises + light theme), Stage F (the algedonic line),
  Stage G (the Repair Bench) — one solo overnight, all proven on the real thing (2026-08-03).**
  - **Stage E — the ledger's promises reach the glass (docs/19 §5).** `convert()` files its
    PROMISE at probe time — `_write_estimate_safe()` writes `.convert-estimate.json`
    (`estimate_from_ledger`'s output verbatim) plus a `convert/estimate` event — and the
    `converted` event now carries `promised_s_per_page` / `promised_eta_s` / `estimate_basis`
    beside the actual: the promise-vs-actual pairing, in the permanent record (docs/19 §6
    hygiene). Python is the ONE authority on the number; `line.rs` projects the sidecar
    verbatim and only while the lock names the same source (blind spot #1: never derive the
    same figure twice in two languages). **The queue panel**: `line_state` gains `queue`
    (drop/*.pdf in the watcher's own name-sorted order — read-only: the ORDER control is a
    watcher-contract change that awaits Rab's signature, so the design ships in the morning
    note, not the code) and the Room renders ▶ converting + waiting rows with sizes and the
    promise. **The slice batch became a live lever** — 8 | 16 | 32 buttons in the Convert
    policy row → `chunk_batch_set` (whitelist identical to Python's) → `chunk-batch.txt`,
    re-read per slice. **The light theme is finished**: the ◐ choice persists via
    `localStorage` and is applied at boot, both surfaces, token-complete.
  - **Stage F — the algedonic line (docs/19 §6), PROVISIONAL by design.** New `algedonic.rs`:
    unresolved pain — `convert/stalled`, `intake|gate|ship failed`, `audit/held` from
    events.jsonl, plus `supersede-held` / `bless-invalid` / `failed` from the receipts cache —
    becomes an alert with a stable id (`ts|kind|bundle`). A LATER success retires a failure; a
    park is retired only by a human; dedupe keeps the newest occurrence per (kind, bundle);
    7-day window. Unacknowledged alerts older than **M minutes ESCALATE**: a terracotta banner
    in the Room with per-alert ⚑ ack, a quiet chip on the Dock (click → Room), a flag under
    the Wall's verdict. M (`algedonic-minutes.txt`, default 30) and the append-only ack ledger
    (`algedonic-acks.jsonl`) are **PROVISIONAL — Rab signs both** (docs/19 §6) and the banner
    says so on the glass. Acking silences an occurrence, never the class: a newer occurrence
    carries a new id and re-alarms (proven in tests). Five new unit tests (16 total), incl.
    an ISO-8601 ↔ epoch round-trip without a date crate.
  - **Stage G — the Repair Bench prototype (docs/19 §7), under `prototypes/repair-bench/`.**
    Rab's design: **"the human IS the vision model."** `bench.py` (stdlib http + pymupdf,
    zero new deps) + `bench.html`: the source-PDF page and the markdown at the flagged zone
    side by side, navigated by the manifest's real zones (page seeded by line-ratio, refined
    by the human with ◂ ▸); repair = drag a rectangle (server crops the 220-dpi raster) or
    Ctrl+V a screenshot → `assets/_repair_pN_k.png` (collision-safe) → embedded `![[…]]` at
    the zone — the vault's own reference style — with provenance appended to
    `manifest["repairs"]`. Insertion offsets are server-tracked so later zones stay
    addressable; a `.bench-bak` precedes the first write; `--sandbox` repairs a copy. The
    re-score button is a **PREVIEW** (re-runs `fidelity_audit.degeneration` on the current
    text, writes nothing): whether a repair image earns audit credit is an unsigned policy —
    Rab signs it (docs/19 §10).

  **Proofs, all against the real thing.** Repair Bench acceptance **26/26** on a sandbox copy
  of the REAL held Valentine: real zones, a real page-120 raster from her source PDF, both
  gestures, the offset arithmetic under out-of-order repairs, the HTTP layer, the preview
  honestly answering "STILL FLAGGED — repairs on 3/4 zones" (images don't delete degenerate
  text), and the real held bundle hash-verified untouched; then the served UI drove live in a
  browser (zone chips, re-score) with 0 console errors. Widget: `clippy --all-targets -D
  warnings` clean, 16/16 tests, `npm run build` green (exe SHA-8 `91F190AB` staged for RAB's
  adoption), and a render harness over real-shaped S62 state — banner, queue, levers, promise
  row, Wall flag all render; ⚑ ack and batch clicks invoke with exactly the right payloads;
  the theme persists — 0 console errors, dark AND light. **Live fire:** bojieli (19 pp)
  re-converted through the changed converter (`--dry-run`, 89.7 s): `convert/estimate` fired
  (promised 32 s, `similar ×1`), `converted` carried the promise (1.689) beside the actual
  (4.72 s-pp) — the FIRST promise-vs-actual pair on record, honestly bad because the ledger's
  only neighbour was a 1,356-pp chunked monster — and the ledger now holds a second clean-lane
  point, so the very next small book gets a sane promise. The estimator was watched learning
  inside a single session.

- **S61 — ANALYST chunk-level resume: a power cut costs one chunk, not an afternoon
  (2026-08-01 → 2026-08-03).** `analyst.process()` held every finished chunk in memory and wrote
  the markdown only at the end, so the S61 power cut at **chunk 936 of 969 — nine minutes from
  done** — erased ~4 hours of qwen3 work while the bundle sat intact beside it. The analyst now
  journals every completed chunk as it finishes and resumes from the journal after any death
  (`windows-converter/analyst.py`, mirroring Stage D's slice resume one stage over).
  - **The journal** — `.analyst-work/<key16>/chunks.jsonl`, one JSON line per completed chunk
    (`i`, input hash, status, output), **fsync'd per line**: surviving power cuts is the whole
    point, and an OS write cache would defeat it.
  - **The key binds everything that changes the output** — fenced source text + backend +
    program + `CHUNK_TARGET`. Any change ⇒ a different key ⇒ no stale reuse, by construction.
  - **Trust is re-earned at resume:** each record's input hash is re-validated against the
    recomputed chunk at that index before it is believed; a torn final line (power cut
    mid-write) fails to parse and that one chunk is redone — the events.jsonl discipline.
  - **Failed chunks are deliberately NOT journalled** — a transient backend error must be
    retried on resume, not remembered as a permanent failure.
  - Pass/reject/fail counts are recovered from the journal so the frontmatter stays truthful,
    and the heartbeat's rate counts only chunks generated THIS run (resumed ones excluded), so
    the Room's ETA does not lie after a resume — the S60 conversion-ledger honesty lesson
    applied to the analyst. Journal removed on success. Always-on, no new parameter: the
    pending-card resume, the inline `--analyst` convert, and `--reanalyze` are all protected.

  **Verified by a 21-check harness** (backend faked at the process boundary): journal shape,
  hash-mismatch rejection, torn-line tolerance, key isolation, and a simulated mid-run kill —
  the resumed book **byte-identical** to an uninterrupted run. **Then verified by the real
  thing:** the arc's third power cut killed Damodaran's live pass at chunk 688/969; the restart
  re-validated all 688 journalled chunks and lost **~16 seconds** where the pre-build cut had
  lost ~4 hours. The pass completed 945 ✓ / 24 🛡 / 0 ✗ (688 resumed, 6,561.7 s total).

- **S60 — STAGE D: `--page_range` chunking, the slice lever, and the conversion ledger
  (2026-08-01).** Long books were the last failure class that could still eat a night: over
  ~600 pages a single Marker run balloons its batch, thrashes VRAM and dies hours in, taking
  every converted page with it. Books now convert in **200-page slices** per the spec Rab signed
  at S57 (docs/18 §5.2), built to it verbatim.
  - **Lane-aware threshold** — clean >600 pp, scan >400 pp (scan runs hotter: Valentine peaked
    ~8 GB at 465 pp), page counts from the pymupdf probe, never metadata.
  - **Resume is the point.** Each finished slice is published into
    `.chunk-work/<sha16>/slice-<start>-<end>/` **outside** the run's temp dir, keyed by
    (source_sha, page_range), by dot-dir-then-rename so a half-written slice can never be
    mistaken for a finished one. A killed slice costs only that slice; the re-run converts the
    missing ones and skips the rest. The whole book's slice dir is removed once the merge
    succeeds — the bundle holds everything by then, and these are gigabytes.
  - **Assets renumbered to absolute pages.** Marker numbers images by page *within its own run*,
    so every slice emits `_page_0_Picture_0.jpeg` and a naive merge would silently overwrite
    figures. Filenames and their markdown references are shifted by the slice offset — and the
    shift touches image links only, never free text, because a library of software books legibly
    contains strings like `_page_12_`.
  - **Seams recorded, never smoothed.** `manifest["chunking"] = {slice_size, batch, seams}`
    (1-based first pages of slices 2..n) travels with the book forever, for the audit and the
    Repair Bench. No overlap reconciliation in v1: it trades a tidy seam for the risk of silent
    text loss, which is the one trade this factory refuses.
  - **The slice batch is a USER LEVER** — `chunk-batch.txt` (8 | 16 | 32, default 16), re-read
    per slice so an edit mid-book takes effect at the next one; off-menu or unparseable values
    fall back to the default rather than handing Marker a number nobody chose. Unchunked books
    keep batch 32. The Convert station's policy row now states the real behaviour and the live
    lever value — it had read "chunking pending spec review" for three sessions after the spec
    was signed.
  - **Progress + events**: the progress file's stage gains a `slice 3/7 · ` prefix (the Room
    renders it verbatim, so slice-level progress needed no widget change), `convert/chunking`
    and per-slice `convert/slice` events, and the final `converted` event carries `slices` and
    `peak_vram_mib`.
  - **The conversion ledger** (Rab's S57 requirement): every successful conversion appends a
    learning record to `conversion-ledger.jsonl` — pages, lane, chars/pp, wall, s/page, chunked,
    slices, batch, peak VRAM (sampled by the stall monitor, which was already the thing watching
    the GPU). `estimate_from_ledger()` turns it into a **similarity-based** estimate: same lane
    first, then the three nearest chars/pp neighbours, median of their rates — and it returns
    `None` rather than guessing when there is no evidence. Surfacing it on the card, with the
    promise-vs-actual pairing, is Stage E's job per the spec.
  - **One refactor to make it possible:** the monitored Marker run is now `_run_marker()`, shared
    by the whole-book and slice paths, so the draining reader (S48's pipe deadlock), the
    tree-kill (S48's orphan), the kill-early stall signature (S45/S48) and the page-scaled
    timeout (S45) have exactly one implementation — each slice gets its own proportionate bound
    and a killed slice fails alone.

  **Verified without spending a GPU-hour**: 25 checks driving the REAL `convert()` over a
  synthetic 610-page PDF with Marker faked at the process boundary — slice ranges and argv
  (including `--page_range` and the lever's batch), merge order, asset renumbering with no
  collisions, the manifest's seams, a killed slice aborting the book, exactly the two good
  slices published for resume, the re-run skipping them, and **the resumed book byte-identical
  to one converted in a single pass**; plus the lever's refusals, the ledger record, the
  estimator's neighbour selection (and its refusal to borrow across lanes), and a short book
  still taking the single-run path with batch 32 and no chunking block. Gates: clippy
  `-D warnings`, `node --check`, 11/11 rust tests.

  **ACCEPTANCE RUN — Damodaran, 1,356 pp, live (2026-08-01).** 7 slices, merged in **2,290 s
  (1.69 s/page)**, anchored, pending card parked, slice work dir cleaned. **Resume proven under
  a real kill**: slice 2's Marker tree was `taskkill /T`'d mid-conversion — the book aborted
  rather than continuing with a hole, no `.part-` survived, no orphan held the GPU (all three
  process levels died, the S48 lesson holding), and the re-run reported `SLICE 1/7 … RESUMED`
  and converted only 2–7. An unplanned power cut during an earlier attempt tested the same
  discipline harder still and left no half-written slice, no stale lock, and no corruption.
  The wedge class that made this book unconvertible is extinct.

  **Two defects the synthetic harness could not have caught, both fixed:**
  1. **Asset page numbers were inflated.** Marker's `--page_range` already numbers assets by
     ABSOLUTE page; the offset was added on top, so a 1,356-page book produced asset pages up to
     **2553** in bands of 400-599, 800-999, 1600-1799, 2400-2599. Nothing was lost (filename and
     reference shifted together, so every image resolved), but every page number above slice 1
     was wrong — and that is what the Repair Bench will navigate by. The merge now keeps
     Marker's own names and rewrites nothing, with a tripwire (`convert/asset_range_warning`) if
     an asset ever falls outside its slice's range. **The harness confirmed the broken merge
     because its fake Marker was written from the same wrong assumption as the code** — a stub
     that shares the code's assumptions proves nothing; it now emits absolute names measured
     from the real run, and asserts no asset may claim a page beyond the book.
  2. **The ledger flattered itself on resumed runs** — Damodaran filed 1.69 s/pp having truly
     spent **1.94**, because the resumed slice's 342.7 s was invisible to the re-run. It now
     records the book's TOTAL cost (reading each resumed slice's `wall_s` from its `.done`),
     keeps this run's elapsed as `run_wall_s`, and counts `resumed_slices`. Otherwise every
     retry teaches the estimator to promise more than the GPU can deliver. 30 checks now pass.

  **Two findings for the operator.** **Peak VRAM 9,786 MiB of 10,240** even sliced at batch 16
  (card-wide, so less ~1.4 GB baseline) — thin margin, the first hard argument for batch 8 on
  long clean-lane books, and a number that was invisible before the ledger existed. And **the
  audit failed the book** (survival 0.927, 25 omission runs, degeneration true) — verified NOT
  a seam artifact: the nearest zone is 357 lines from a seam, most are 700–12,000 away, and
  every excerpt is a table row. It is the Beer/Valentine table-loop disease in a finance
  textbook full of tables. Parked in `pending/`; nothing shipped.

### Fixed

- **S59 — the Room stopped waking the ThinkPad every four seconds (2026-07-31).** `gatherVM()`
  awaited `call("vault_check")` on every Room poll — every 4 s while converting, 9 s idle — and
  `vault::check` runs `git fetch --quiet origin`, a real round trip to the ThinkPad over
  tailscale ssh. Verification before the fix (standing rule) found the result was **never
  read**: the binding was carried into the view-model and nothing consumed it, because the Vault
  tile's count comes from `room_metrics`' local `count_library`. So an open Room was waking the
  ThinkPad's sshd ~10x more often than the Dock's deliberate 45 s poll purely to discard the
  answer, and blocking a worker thread for the dial timeout whenever the host was asleep. The
  remedy was therefore a deletion, not the cached projection the task suggested — no new
  command, no TTL, no API surface. Vault freshness is unchanged: the Dock's `vaultLoop` re-arms
  regardless of which surface is showing. The removal leaves a comment stating the rule (the
  Room's loop may not touch the network; read a cached projection if a future panel needs live
  vault state) so it cannot be quietly restored. Proved by recording the commands one real
  `gatherVM()` poll invokes: nine calls, none network-touching, receipts still rendering from
  their local cache. Gates: `node --check`, clippy `-D warnings`, 11/11 rust tests, Room render
  pass unchanged.

### Added

- **S58 — docs/19 §3 STAGE C2 SHIPPED: the analyst-only re-run, per-bundle targeting, and the
  seam receipts (2026-07-31).** Three gaps closed at once, all of them things the factory had
  learned it needed the hard way.

  **1. `⟲ re-analyze` — the analyst-only re-run.** `convert_and_ship.py --reanalyze <source>`
  re-runs the analyst over an already-converted bundle and ships the result as a supersede;
  **Marker never runs**, so remedying an ANALYST-phase failure no longer costs the GPU-hours of
  re-reading a PDF whose convert-phase audit already passed (the claude-code book, vault note 5:
  convert survival 0.9913 with no degeneration, analyst `fail` from qwen3 looping in its own
  notes). Eligibility lives in Python alone — the re-run must start from a bundle whose markdown
  is Marker output (a manifest with no `analyst` block), and when only analyst OUTPUT survives it
  refuses out loud as an `analyst/rerun_refused` event rather than feeding a model its own
  degenerated text. The bundle name is read from the `.md` inside the directory, never from the
  directory (`unique_anchor` suffixes those with " (1)"), and the supersede provenance records
  the verdict of the **vaulted** generation, not whichever record happened to be newest on disk.
  Progress needed no new plumbing: `apply_analyst` already writes the S56 analyst heartbeat, so
  the Room shows a re-run live. Widget side: `assay::reanalyze` validates only its own action
  (legal source name, configured paths, script present) and **refuses while `.gpu-lock` is
  held** — starting qwen3 underneath a running Marker is the S45 VRAM-thrash wedge signature.

  **2. Per-bundle targeting.** `⟲` and `✓ bless` now render on EVERY held row with their own
  `data-src`, on both surfaces (per-row `⟳` landed S52). Until now bless had exactly the reach
  the remedy button had before S52 — the card's newest-audited subject only — so blessing a held
  bundle meant flipping the card onto it first, and losing that race is what made the guard
  refuse Valentine twice in S56.

  **3. Seam receipts — the vault's answers, brought home.** Every `EXPORT-*` outcome used to
  exist only in the ThinkPad's systemd journal, a machine the desktop cannot read, so the
  widget's story of a book ended at `shipped`. The exporter now appends one JSON line per
  outcome (`exported`, `exported-supersede`, `skip`, `supersede-held`, `supersede-miss`,
  `supersede-noop`, `blessed`, `bless-invalid`, `failed`) to `~/file-portal/receipts.jsonl`, and
  the widget's new `receipts.rs` tails it over `tailscale ssh` on the vault bar's existing 45 s
  poll, caching to its OWN dot-prefixed file; the Room merges the two streams **at render time**
  so each file keeps exactly one writer. Rab's call among three designs: receipts stay OUT of
  the vault repo — the exporter's change is an append to a plain file, so the module that writes
  the vault got no new git code, and the notes' own history gets no machine records.

  **Verified:** clippy `-D warnings` clean, `node --check` on both touched JS files, **11/11**
  Rust tests (3 new receipts tests + a re-run refusal test incl. the `.gpu-lock` guard), an
  **8-case seam proof driving the REAL exporter against real git repos** (every outcome's
  receipt, provenance surviving the seam, a bless-on-`fail` rejected, and — the fail-open case —
  an unwritable receipts path costing a warning while the book still reaches the vault), and a
  **5-part orchestration proof** of the re-run with the analyst and ship stubbed (pre-analyst
  selection, supersede stamp, originals untouched, enforce-park, refusals). The
  exporter↔widget seam is proved on REAL BYTES: the receipt line in `receipts.rs`'s test was
  produced by the shipping `_receipt` and pasted in verbatim. Still owed: the live claude-code
  re-run (~17 min of GPU, Rab's go) and the ThinkPad deploy that puts the receipts on the wire.

- **S57 — the chunking spec SIGNED + docs/19: the Opus 5 execution plan (2026-07-31).** Stage
  D's parameters decided live with Rab and written into docs/18 §5.2: lane-aware thresholds
  (clean >600 pp / scan >400 pp), 200-page slices, clean cuts with every seam page recorded in
  the manifest, slice recognition-batch as a USER LEVER (`chunk-batch.txt`: 8|16|32, default
  16 — Rab: 8 "keeps it actually useful", 32 "if I really want to"), resume by (source_sha,
  page_range), slice-prefixed progress, absolute-page asset renumbering, whole-book audit —
  plus Rab's **conversion ledger** requirement: every successful vault conversion files a
  learning record (pages/lane/chars-pp/s-pp/wall/chunked/slices/batch/peak-VRAM) and the
  estimator upgrades from a global median to similarity-based, with every promise later paired
  to its actual. And **docs/19 — a dummy-proof, context-free execution plan for an Opus 5
  session** covering everything that remains: the twelve laws (each with its scar), the
  measured machine map, current truth, Stages C2/D/E/F/G step-by-step with named STOP-for-Rab
  points, the docs/17 remainders, and how to fail well. Docs only; no pipeline/GPU/source
  changes. Cookie #50 — the fiftieth — commissioned it; the tally's #47–49 entries were
  backfilled the same hour (headers had moved, entries hadn't — the flight recorder is whole
  again).

- **S56 — docs/18 STAGE C (first half) SHIPPED: the human-bless rail + the analyst heartbeat
  (2026-07-31).** The vault's constitution amended per Rab's signed sentence — **"pass, or flag
  with bless"**: the exporter's supersede guard now accepts a `flag` verdict when a valid
  human-bless marker (`bless.json` beside the manifest, sha-bound to the source) is present,
  folding the bless provenance into the committed manifest so the vault never pretends a blessed
  note passed on its own; degeneration `fail`s stay refused even WITH a marker (defense in
  depth), and the marker survives failed exports for retry sweeps. Author side: `assay.rs::bless`
  — the ONLY author — validates eligibility backend-side against the event stream (newest scored
  verdict must be `flag` with `degeneration: false`; a shipped record must exist), then scp's the
  marker into the bundle's ThinkPad staging dir over the existing channel (async + spawn_blocking
  — the vault_check UI-freeze lesson applied); ✓ bless button on flag-verdict audit cards, both
  surfaces. **Proven by a 5-case seam test driving the REAL exporter on temp git repos**: valid
  bless → vaulted+pushed with provenance; no marker / sha-mismatch / fail-with-marker → all held
  with logged warnings; pass regression holds. Design pivot recorded honestly: the S50 refusal
  kept Cybernetics' only good bundle in ThinkPad staging (the desktop's anchor still holds the
  old degenerate copy), so bless targets staging and the exporter's startup sweep is the
  acceptance trigger — one ThinkPad deploy (pull + restart) both ships the new guard AND vaults
  her. Also: **analyst per-chunk heartbeat** — `analyst.py` writes `.analyst-progress.json`
  every chunk (S42 pattern, zero flight-recorder growth, cleared in a `finally`), `line.rs`
  projects it only while fresh (<300 s), the Room's Convert panel renders `analyst: n/total ·
  s/chunk · ✓ live / frozen ⚠`. Blind spot #6 closed. C2 (analyst-only re-run + seam-events
  return channel) remains.
  **LIVE-FIRE RESULT (same day): Cybernetics VAULTED as note 6** — journal:
  `EXPORT-BLESSED … accepted on human bless (by=rab)` → `SUPERSEDE-MISS … creating a new note` →
  `EXPORTED … commit 70c60e61 pushed + blob-verified`. The field gauntlet found and fixed three
  real defects on the way: (1) the bless button originally rendered on `flag` cards only, but
  local manifests can LAG the staged truth (Cybernetics' desktop copies all say `fail`) — now
  renders on `flag`+`fail` with the backend event-stream validation as the real gate; (2) scp's
  modern **SFTP mode takes remote paths literally** — the defensive embedded quotes became
  filename characters (marker never landed); (3) **System32 OpenSSH keeps its own `known_hosts`**
  (git ships a separate ssh), so the widget's scp hung forever at an invisible host-key prompt —
  NINE zombie scp+ssh pairs accumulated before Rab's Task-Manager instinct cracked it; fixed
  with `BatchMode=yes` + `StrictHostKeyChecking=accept-new` + `ConnectTimeout=10` (the hang
  class is now extinct for bless). Along the way the guard twice refused correctly under fire:
  Valentine's degeneration-fail (a click that raced the card flip) and every marker-less sweep.
  Exe lineage BA23940B→BCD7C018→4F1C00F1→1C0A2319→**7D403BD6 (adopted)**.

- **S53 — docs/18 STAGE B SHIPPED: time on the glass — staleness rendering + policy rows
  (2026-07-31).** `line.rs` projects `progress_age_s` (mtime age of `.convert-progress.json`
  while the lock is held — the exact derivative the Stage A killer watches at 900 s); the Room's
  Convert station renders it as a liveness row: "✓ Ns ago" green while Marker's stream breathes,
  **"frozen Ns ⚠" in clay past 120 s** — the human sees a freeze thirteen minutes before the
  killer acts. Policy stepped out of the config files: the audit lever now wears its current
  mode's sentence ("report: fails ship with the verdict filed" / "enforce: a fail parks in
  held/ — nothing ships unproven") and the Convert station carries the standing policy line
  (kill-early stall + chunking-pending-review, docs/18 §5). Stage A's deferred styling landed
  (`.died` clay ⏻, held rows). Gates: clippy `-D warnings`, `node --check`, `tauri build`
  green; adopted `0356FC34` by Rab's hand, verified visually (the policy rows exist only in the
  new build). Read-only projection throughout — pipeline untouched.

- **S52 — docs/18 STAGE A SHIPPED: death certificates + the stall detector, proven by live
  murder (2026-07-31).** Converter (`convert_and_ship.py`, live immediately): the blind
  `proc.wait(timeout)` is now a 30 s monitor loop enforcing the decided kill-early stall policy —
  progress-file mtime frozen >900 s while Marker runs → GPU triage signature (util/mem via
  nvidia-smi, best-effort) → **tree-kill** → `convert/stalled` event; the latent orphan bug fixed
  in the same stroke (isolated test proved `proc.kill()` leaves the console-script launcher's
  real python alive — `taskkill /T` took the whole tree, 2→0); all monitoring fail-safe per the
  S42 rule, scaled hard timeout preserved as outer bound. Widget (`watcher.rs`/`main.rs`/
  `main.js`/`room.js`, exe `3571F771` adopted by Rab's hand): the ⏻ is backed by an honest 5 s
  liveness poll; a dead watcher files a **death certificate** — exit code remembered after reap
  (blind spot #2), tooltip "Conveyor DIED (exit N)", status line + widget-boot.log entry — and
  its stderr now lands in a truncate-per-spawn `watcher-stderr.log` (blind spot #3: the 0x67
  launcher error died unheard into NUL for five days); deliberate stops file no certificate.
  Plus **per-held-item ⟳ remedy buttons on both surfaces** (the S50 shadowing gap; task chip
  retired). Gates: clippy `-D warnings`, `node --check` ×2, 6/6 rust tests, `tauri build` green.
  **Live acceptance:** `taskkill /t` on the watcher pair → ⏻ flipped within 5 s with the exit
  code; ⏻ restart cleared the certificate and brought a fresh pair. Bonus forensic: tauri's
  bundler patches the exe post-build — the S48 `D4B50F23`-vs-`38CC4D72` hash mystery explained.

- **S51 — docs/18 "Levers and Heartbeats": the observability + control design brief, and four
  standing policies DECIDED (2026-07-31).** Rab's decisions, now spec: stall policy = kill early
  on the stall signature (frozen progress >15 min + lock held → kill + death certificate); large
  books = `--page_range` chunking primary with slice-level batch caps, mandatory spec review
  before build; Valentine retries next pipeline session; figure-heavy flag ceiling = human-bless
  override (widget-authored marker, exporter `blessed` path — Cybernetics first customer). The
  brief merges the S48 ten-blind-spot survey with a lever inventory (every autonomous behavior
  gets a visible per-stage lever), five observability stages (death certificates → heartbeats →
  seam events → algedonic line → hygiene), a seven-stage build plan, an assessment of Rab's
  relayed ChatGPT UI mockups (keepers: policy-as-UI, queue panel, risk strip, light theme;
  fictions rejected — including any auto-purge retention), and **the Repair Bench**: Rab's
  human-in-the-loop repair surface, centered on his insight that *the human is the vision model*
  — screenshot → `assets/` → embedded reference at the flagged zone, provenance-stamped, audit
  re-scored with image credit. Docs only; no pipeline, GPU, or source changes.

- **S50 — the supersede rail's FIRST PRODUCTION RUN: proven at every joint, ending in the guard's
  designed refusal (2026-07-31).** Rab clicked ⟳ on the held Cybernetics bundle
  (`c5afd9edcf620fc6`): the marker was authored before the PDF (S44's load-bearing ordering),
  consumed exactly once, and the `audit/supersede` stamp rode the manifest with
  `from_verdict: fail`. The re-convert (91 pp, 210 s) came back **without the original
  degeneration** — Marker behaved — but survival re-scored 0.6884 ≈ the held copy's 0.688, now as
  25 *omission* runs → verdict `flag`: measured twice, the score is the figure-heavy book's
  structural ceiling in markdown, not a conversion defect. Shipped as-is (no analyst); the
  ThinkPad exporter answered with the rail's last untested joint working as signed:
  `EXPORT-SUPERSEDE-HELD … incoming verdict 'flag' is not pass — vault untouched, staging copy
  kept` (confirmed from the ThinkPad journal — the desktop sees a refusal only as absence;
  observability blind spot #8 live). Findings filed: figure-heavy books are **un-remediable to
  `pass`** under the current contract (policy: human-blessing override or figure-aware lane —
  Rab's call); the assay card's ⟳ can only target the newest-audited bundle, shadowing held items
  (worked around via mtime touch; per-held-item remedy buttons queued as a task chip). The
  replace-in-place case remains Beer's vaulted specimen. No source changes this session — docs +
  memory only; pipeline left up.

- **S49 — Gate 4 ✅ + Gate 5 in-home stream ✅: Sunshine is live, scoped at birth (2026-07-31).**
  Rab installed Sunshine 2026.516.143833 from an elevated shell (winget), disabled both
  auto-created allow-any firewall rules and added the two tailnet-scoped rules in the same
  breath (verified from his window: originals `Enabled=False`, scoped pair live, service
  Running, all four TCP ports listening); web-UI creds set at `https://localhost:47990` →
  password manager. Field notes into docs/17: the web UI's **CSRF guard** rejects POSTs from
  non-default origins (tailnet-IP access needs `csrf_allowed_origins` — deferred), and the
  "Fatal: ViGEmBus" banner is gamepad-passthrough-only (kernel driver, upstream discontinued —
  deliberately skipped). Then the ThinkPad paired `moonlight-qt` and the **first in-home
  desktop stream ran clean**: 1 NVENC session, ~0.25 ms average encode latency, GPU 11 %/65 °C
  — streaming costs the 3D engine essentially nothing. §9 checklist reconciled (Gates 1–2
  boxes belatedly ticked, Gate 4 ticked). Remaining: HDMI dummy plug, out-of-home
  qualification (direct path, ~70 % upload bitrate), Gate 6 (WoL) deferred.

- **S48 — Gate 3 closed end-to-end + the double-ghost exhumation + converter deadlock fix
  (2026-07-30).** The first queued remote drop ran the whole line with the SSH session closed:
  ThinkPad `scp` → watcher → Marker (104 pp, 141 s) → local analyst (37 chunks, 1052.6 s vs a
  1022 s ETA) → ship → ThinkPad exporter → **vault note 5** (`289dcbc`). Getting there took a
  forensic afternoon: the widget-spawned watcher had been dying **silently since ~Jul 24** —
  Security-log 4689 auditing (Rab, elevated) caught **exit 0x67 (venv launcher "no Python")**,
  and a PYTHONPATH sitecustomize birth-logger proved the interpreter never reached site init.
  Root causes, both S29-class MSIX ghosts: (a) uv's managed CPython (`%APPDATA%\uv\python\…`,
  marker-env's `pyvenv.cfg` home) existed **only in the desktop-app sandbox mirror** — every
  packaged Claude shell saw it and "worked"; the unpackaged widget found nothing (fix: Rab ran
  `uv python install 3.12.13` for real); (b) S45's widget-exe adoption never landed — the real
  exe was still the installer's `D4B50F23`; Rab copied the true S44 `38CC4D72` from his own
  shell and hash-verified it. Then the drop test immediately caught a THIRD latent bug: the S42
  progress reader opened Marker's pipe `text=True` with no encoding → cp1252 strict decode died
  on surya's tqdm block glyphs → the daemon reader exited → the full 64 KB pipe **blocked Marker
  at zero CPU** (S42's 3-pp test had never filled the pipe; S45's 5 h "VRAM wedge" is possibly
  compound with this). Fix in `convert_and_ship.py` (fail-safe per the S42 rule):
  `encoding="utf-8", errors="replace"` + the reader now drains to EOF on parse faults. Also
  recorded: the analyst-phase Survival Audit **failed the analyst's own notes** (0.9493, 14
  repetition runs — qwen3 looping in summaries; book text clean at 0.9913) and report-mode
  shipped it with the verdict filed in the manifest — surfacing that the remedy loop lacks an
  analyst-only re-run (⟳ re-converts). New standing rule (memory:
  `file-portal-verify-before-instruct`): File Portal operating instructions get verified against
  current source before being given. Machine handed to Rab's brother clean at close (GPU
  baseline, empty queue, no locks).

- **S47 — remote access LIVE: docs/17 Gates 1–3(install) executed (2026-07-30).** Rab ran both gate
  scripts (elevated + unpackaged, per the S46 standing rule — the desktop-app session guided and
  verified read-only, wrote no system state): Gate 1 sshd scoped-at-birth (allow-any rule verified
  disabled from the elevated shell — `Get-NetFirewallRule` is Access-denied from the sandboxed
  surface), Gate 2 key-only auth (password AND keyboard-interactive both probed refused; scp
  round-trip hash-identical on both machines). Two field lessons folded into docs/17: **key
  material travels by file, never clipboard** (hand-pasted pubkey silently truncated 73/106 bytes →
  key rejected with no passphrase prompt), and kbd-interactive stays *advertised* after
  `PasswordAuthentication no` but is dead on this build (probed, not assumed). Gate 3 install half:
  Claude Code CLI 2.1.220 for `bndit` + persistent PATH via ExpandString-preserving HKCU write from
  the SSH session; a **MUSTER-clean verify-only Claude session ran over SSH end to end** (clocks
  agreed; pen respected — first two-live-sessions night). Remaining: Gate 3 queued-drop done-when,
  then Gates 4–5 (Sunshine + Moonlight). The S29 ghost class ends at the SSH prompt.

- **S46 — remote access: docs/17 runbook + `windows-remote/` gate scripts (2026-07-28).** Rab's
  SSH + Sunshine brief re-grounded against the measured machine (S46 preflight) and redesigned into a
  verification-gated runbook (`docs/17-remote-access-runbook.md`): corrections ledger (dead
  `Rabbiallah` account, Gmail-mangled `100.64.0.0/10` firewall blocks, the never-disabled allow-any
  auto rule, lockout-unsafe key rollover, wrong UAC-over-SSH diagnosis, missing `claude` CLI / tailnet
  ACL / DERP + upload-bandwidth / host-key pinning / coexistence + audit accounting), gates 0–6 with
  done-when + rollback, security-model delta (extends docs/06), remote ops cookbook, diagnostics
  playbook, standing coexistence laws. New `windows-remote/gate1-bootstrap.ps1` (enable sshd scoped
  to the tailnet at birth; self-asserts elevation + non-MSIX-sandboxed shell; prints host-key
  fingerprints; transcript) and `gate2-lockdown.ps1` (two-run key-install → proven-login →
  password-auth lockout; BOM-free writes; prepend-not-append sshd_config guard). Both parse clean
  (PS language parser, 0 errors). **No system state changed by S46 itself** — the session's measured
  surface (Medium IL, MSIX-redirected) is exactly what the new standing rule forbids from doing
  system configuration; Gate 1 is Rab's, elevated + unpackaged.

- **S44 — the Desktop half of the supersede seam: the remedy loop is now wired end to end
  (2026-07-25).** docs/15 §14.2/§14.6/§14.7, docs/16 §8 #5. S43 taught the ThinkPad exporter to
  *replace* a vaulted note; nothing yet **authored** the `manifest["supersede"]` block it keys on, so
  the flow was inert. The widget's ⟳ re-convert is now that sole author, and the converter carries the
  intent through to the bundle.
  - **`assay.rs::reconvert` authors the intent.** It reads the source's newest manifest from
    `anchor/`/`pending/`/`held/` for `source_sha256` + `fidelity.verdict` (backend-authoritative — the
    frontend `invoke("assay_reconvert", { source })` signature is unchanged), then writes
    `drop/.supersede/<source>.json` **before** copying the PDF into `drop/`. Ordering is load-bearing:
    the watcher polls every 5 s, and a convert that began before the intent existed would ship as an
    ordinary create and the remedy would be **silently lost** to dedup. If the PDF copy fails the
    marker is rolled back; if the marker cannot be written the re-queue is refused outright (queueing
    a convert that provably cannot supersede would burn a GPU run to no effect).
  - **The marker is invisible to every existing scan, by construction.** A dot-prefixed
    *subdirectory* of `drop/`: the watcher skips non-files, dotfiles and non-`.pdf`; `line.rs`'s
    `count_pdfs` counts only `.pdf`, so `drop_waiting`/`failed_count` cannot be inflated; `room.rs`'s
    `file_nodes` lists only files, so no phantom node appears in the Convert or Intake drill trees.
    **No watcher, counter, or projection change was needed.**
  - **`convert_and_ship.py` carries it.** `_take_supersede_marker()` is **consume-once** — read and
    deleted at the top of `convert()`, before any work — so an intent can never outlive the click that
    authored it and latch onto a later drop of the same filename; losing one (crash, failed convert)
    is the safe direction, since the remedy then behaves exactly as before.
    `_stamp_supersede_safe()` folds it into `manifest["supersede"]` once the sha is known, dropping
    the intent if the file actually converted is not the one the widget pointed at. Both are wrapped
    so they **can never change a conversion's outcome** (the S42 fail-safe rule for the core
    converter). One stamp point suffices: the anchor copy, the `pending/` card + resume, and all three
    ship sites carry that same on-disk manifest.
  - New `audit/supersede` + `audit/supersede_ignored` events, with phrases in the Dock ticker and the
    Room stream (deliberately not named `failed`, which `events.rs` counts into the day's failures).
  - Verified: **6 new Rust tests** (the widget crate's first — this is the one path that can cause a
    vault note to be *replaced*, so it earns them) covering intent contents, intent-without-record,
    refusals leaving neither intent nor trigger, refusal when the intent cannot be recorded, and the
    invisibility property. `cargo clippy --all-targets -D warnings` clean, `py_compile` +
    `node --check` clean, `tauri build` green. **A 21-check end-to-end seam proof** drove the marker
    the *real Rust code* wrote through the *real S43 exporter* against temp git repos: consume-once
    holds, the sha guard drops a mismatched intent, a still-`fail` remedy is refused with staging
    kept, and a passing remedy **replaced a note that had been filed out of `Inbox/`** — old `.md`
    name preserved, assets swapped, no new Inbox note, commit `supersede: … (audit-remedy, fail→pass)`.
    No GPU, no vault write, no real-state pollution (real `events.jsonl` untouched).

- **S43 — the exporter supersede flow: closing the Beer remedy loop (2026-07-25).** docs/15 §14,
  docs/16 §8 #5 (THE SUPERSEDE GAP). The exporter (`linux-converter/converter/exporter.py`) can now
  **replace an already-vaulted note in place** with a deliberate remedy re-convert — but only under a
  named, opt-in, fail-closed contract, so the create-only guarantee for every ordinary conversion is
  untouched.
  - **The seam is one manifest field.** A manifest may carry `"supersede": {"reason": …,
    "from_verdict": …}`, authored by **nothing but the widget's ⟳ re-convert**. No field ⇒ the
    exporter dedups exactly as before (a matching `source_sha256` is a create-only no-op). Accidental
    re-drops of the same PDF stay safe *by construction* — they carry no field.
  - **Verdict guard first (SIGNED, fail-closed).** Supersede proceeds only if the *incoming* bundle's
    own `fidelity.verdict == "pass"`. A still-failing remedy, or one whose audit never ran (a
    **missing** fidelity block is not `"pass"`), is held: `EXPORT-SUPERSEDE-HELD`, staging kept, vault
    untouched. The guard is deliberately **not** widened to force the Beer specimen to land (§14.5).
  - **Locate-don't-assume.** The live note is found by its full `source_sha256` via `git grep -l` in
    the **bare** repo (the `main:` prefix stripped) — never by recomputing `Inbox/<slug>--<sha8>/`,
    since the Desktop may have filed the note elsewhere. **0** matches ⇒ fall through to a normal
    create (`EXPORT-SUPERSEDE-MISS`); **>1** ⇒ `EXPORT-FAIL`, staging kept (never guess).
  - **Replace-in-place, identity preserved.** The existing note's `.md` filename and folder are kept
    (read from the committed tree); the remedy's markdown is written under the **old** name so a
    differing new slug can never rename the note or break `[[wikilinks]]`. `assets/` is fully swapped
    and the manifest overwritten. A **no-op guard** (only the manifest changed ⇒ identical note bytes)
    avoids an empty commit; a **resume** path (committed-but-unpushed) re-pushes rather than
    re-committing. The **L12 deletion gate is unchanged** — push, then `cat-file -e` the commit and
    every *actually-committed* blob in the bare repo (iterating `git ls-tree` of the commit, because
    the `.md` basename changed) before the staging copy is removed.
  - Verified: `linux-converter/tests/test_exporter.py` grew from 8 to 18 real-git tests (replace after
    the note was filed out of `Inbox/`; old `.md` name preserved on a differing slug; assets swapped;
    `fail` refuses + keeps staging; missing fidelity refuses; >1 match fails; 0 matches creates; no-op
    identical bytes; no-field still skips; commit-without-push resumes). Full suite **51 passed**,
    `ruff check` + `ruff format` clean, `file-portal-converter` restarted onto the new code.
  - **Not in this session:** the Desktop half (`assay.rs` ⟳ writes `drop/X.supersede.json`;
    `convert_and_ship.py` folds it into the manifest) and any real-vault supersede of the Beer
    specimen — both require the Desktop pipeline (shut down for gaming) and are Rab's call.

- **S42 — true per-page / per-stage convert progress (2026-07-23).** docs/16 §8 #3. The Room's
  Convert station now shows the **real current Marker stage + item count** streamed live (e.g.
  "Recognizing Layout · 2/3"), not just an elapsed-time estimate. This is the **first change to the
  core converter** since the projection law — done fail-safe.
  - `convert_and_ship.convert` (`windows-converter`): dropped `--disable_tqdm` and switched
    `subprocess.run` → `Popen` with a **daemon reader thread** that parses surya's tqdm bars
    (regex validated against real captured output) into `…\library\.convert-progress.json`
    `{stage,pct,n,total,frac}`. **Everything about progress is best-effort and cannot change the
    conversion:** identical returncode check, 3600 s timeout (kill on expiry), markdown still read
    from the output file; any reader/parse/IO fault is swallowed; the progress file is cleared when
    the convert ends (or times out).
  - `line.rs`: reads the progress file **only while the `.gpu-lock` is held** (a stale file from a
    crash is ignored) → adds `convert_stage` / `convert_frac` / `convert_n` / `convert_total` to
    `line_state`.
  - `room.js` (Convert panel): shows the live stage + per-page count; the progress bar stays the
    forward-only elapsed÷ETA estimate (a clean monotonic overall % isn't derivable from surya's
    *multi-stage* bars — layout/OCR/tables each restart 0→100), so the honest per-page detail lives
    in the stage row.
  - Validated: an isolated `convert()` on a 3-page test PDF wrote real stages, produced correct
    markdown (3721 chars), cleared the progress file, and polluted no events; `clippy -D warnings`
    clean; convert-panel harness rendered "Recognizing Layout · 2/3" with 0 console errors;
    `tauri build` green and the new build boots.

- **S41 — the GPU telemetry stream is complete: util + temp sparklines (2026-07-23).** docs/16 §8 #4.
  S38 shipped the VRAM sparkline; the `gpu_vram` probe already reported utilization + temperature (as
  numbers only). Now a unified **GPU telemetry strip** in the Room shows all three as fixed-scale
  rolling sparklines — **VRAM %** (0–100), **GPU util %** (0–100), **Temp °C** (30–95) — each with its
  current value and a clay stroke under pressure (VRAM >92 %, util >95 %, temp >83 °C), else flow. The
  sampler (`room.js`) now feeds three rings (`vramHist` / `utilHist` / `tempHist`) from the same one
  read per poll — still no always-on backend thread. The VRAM sparkline graduated from the KPI tile
  into the strip (the tile reverts to an at-a-glance gauge — no duplication). New `.room-gpu` / `.rg-*`
  CSS (mirrors the KPI-tile idiom, theme-token colors). Read-only projection; pipeline untouched.
  Harness-verified (0 console errors; all three sparklines accumulate on their fixed scales — the temp
  Y-coords confirm the 30–95 domain; util clay at 98 %; dark + light), `tauri build` green.

- **S40 — the widget opens centered on the primary monitor (2026-07-23).** Rab-requested follow-up
  to S39: since sizes don't persist, every launch should start in a predictable place — centered on
  monitor 1 (his primary). New `main.js::centerOnPrimary()` runs once at boot (just after the initial
  reflow settles the height): reads `primaryMonitor()` (position + size) and the window's
  `outerSize()`, then `setPosition`s to the monitor-center — all in physical pixels, so it's correct
  at any DPI and lands on the primary regardless of a second monitor's offset. Only at launch; the
  user can still drag it anywhere (moves aren't tracked). Adds the `core:window:allow-set-position`
  capability. Verified live: the relaunched window's center measured `(1280,720)` — exactly the
  2560×1440 primary's center — on DISPLAY1. `node --check` clean, `tauri build` green.

- **S38 — GPU telemetry sparkline in the Control Room (2026-07-23).** docs/16 §8 #4. The Room's
  GPU VRAM KPI tile now draws a **rolling sparkline** rather than a bare instantaneous gauge.
  - `room.js`: a bounded module-scoped ring (`vramHist`, 48 samples) fed once per `gatherVM()` —
    the poll loop is the sampler, no always-on background thread (the sparkline is unviewable with
    the Room closed). `sparkSvg(series, col, domain?)` gained an optional fixed `{min,max}` domain;
    the VRAM sparkline uses a **fixed 0–100 % scale** so height = true card-fullness (idle low, a
    convert spikes) — unlike the autoscaled throughput/median tiles. Gauge stays as the first-poll
    fallback (until ≥2 samples); clay stroke when the card is under pressure (>92 %), else flow.
  - `room.rs`: `gpu_vram()` extended to also report **utilization + temperature**
    (`--query-gpu=…,utilization.gpu,temperature.gpu` → `{used,total,util,temp}`; both optional,
    `Null` when there is no probe). Surfaced on the header GPU stat (`4.2/10 GB · 41% · 62°`).
  - Read-only projection; the pipeline is untouched. Verified in a browser harness (0 console
    errors; the VRAM ring accumulated across polls; fixed-scale Y-coords matched exactly;
    gauge→sparkline transition; util/temp in dark+light; throughput/median sparklines unregressed),
    `clippy -D warnings` clean, `tauri build` green (release exe + MSI + NSIS). Still deferred: an
    always-on backend sampler, and re-backing the throughput/median sparklines with a rolling window.

- **S37 — a live convert progress bar (2026-07-22).** The Room's Convert station now draws a live
  progress bar + `%` from measured data — `elapsed ÷ (elapsed + estimated-remaining)`, where
  elapsed is the `.gpu-lock` age (new `convert_elapsed_s` in `line_state`) and the estimate is the
  existing measured-median ETA. Capped at 95 % until the `converted` event actually fires (it's an
  estimate, kept honest), smooth width transition + a gentle pulse (reduced-motion-safe). No
  converter change — true per-page % stays a converter installment (Marker runs with
  `--disable_tqdm` + buffered output; per-page would need fragile streamed-tqdm parsing of surya's
  multi-stage bars).

- **S36 — the drill-down observation system: station → live on-disk tree (2026-07-22).**
  Continuing docs/16 §8 (#2). Clicking a Room station flip-expands into an accurate, live file
  tree read straight from disk — a real granularity/observation surface, not a simulation.
  - New read-only `room::station_tree(seg)` (`room.rs`) walks the real directories per station:
    vault → `Library/Inbox/*` bundles; assay → `held/*` (with the manifest's real degeneration
    zones) + recent verdicts; convert → `drop/`, `.gpu-lock`, `drop/done/`, `anchor/`; gate →
    `pending/*` + analyst-mode; ship → last-shipped (from `events.jsonl`) + invariants; intake →
    `drop/` + `drop/failed/`. Each node carries true byte sizes, manifest fields
    (lane/pages/sha/engine), the analyst pass/reject/fail summary, and — for audited bundles —
    the verbatim degeneration zones (zlib/tri×/chars/excerpt) with survival/verdict colour-coding.
  - Frontend (`room.js`): the flip-open overlay (transform-origin at the click), a recursive
    flattened tree with collapse/expand (stable name-hash ids so state persists), Esc / backdrop /
    × to close, and a 4 s live re-read while open. Room station click now opens the drill (the
    Room is observation-first; controls stay in the Dock + the assay panel).
  - Read-only projection; the converter/formatter are never touched. Verified in the harness
    (0 console errors) and **live in the real widget**: the Assay drill showed the held
    Cybernetics bundle's real `.md` (155 KB) + `assets/` (92 files) + zones at lines 1014/2400
    matching the on-disk manifest; the Convert drill showed anchor bundles with the real analyst
    summary (270✓ 22🛡 10✗). `clippy -D warnings` clean, `tauri build` green.

- **S35 — the surface trio completed: the Wall + the canvas transit belt (2026-07-22).**
  Continuing docs/16 §8. Frontend-only, projection-safe (no pipeline touch); design lifted from
  the source object (`prototypes/control-panel/control-room/`).
  - **Wall surface** — a third density in the `Dock ⇄ Room ⇄ Wall` switch: a glanceable
    across-the-room projection (giant system verdict — terracotta only when your hand is required
    — the six stations as big dots, three hero numbers: survival avg / throughput / vault). The
    window resizes into it (900×500).
  - **Canvas transit belt** — under the Room's station rail: an *ambient activity projection*
    whose chip count and tint reflect real in-flight work (drop_waiting / converting / gate /
    held), empty when the watcher is down. Reduced-motion-safe, palette-cached, redraws through
    the Room's poll without resetting (persistent chip state across `innerHTML`). Invents no
    traffic — it visualises the line's real state.
  - The Room header's system verdict now reflects real state (`viable` / `attention` / `paused`)
    instead of a constant. Verified in the harness (0 console errors, dark+light) and **live in
    the real widget** (belt animating; Wall "ATTENTION" on the real Cybernetics hold; live VRAM,
    survival average, vault count). Next: the drill-down file explorer (docs/16 §8 #2).

- **S34 — the Control Room becomes the widget's face (2026-07-22).** Graduated the merged
  Claude-Design *Control Room* artifact into the live widget as a second surface, wired to real
  pipeline data. Design record + build audit: `docs/16-control-room-face.md`.
  - **Surface switch (`Dock ⇄ Room`)** in the titlebar. Dock is the narrow floating widget
    (unchanged); Room is a wider operations dashboard that the window resizes into — one
    projection, two densities (docs/13 law #3).
  - **The Room** (`windows-widget/src/room.js` + Room styles): the six-station rail, a
    golden-signal KPI band (throughput, median s/page, GPU VRAM, queue depth, survival average,
    shipped-today), the convert station, the full Survival-Audit evidence card (verdict, damage
    map, verbatim degeneration zones, held tray, report⇄enforce, re-convert), and the live event
    stream. Every value is a projection of an existing `invoke()` command — the Room owns no
    state and writes only through the Dock's existing intent commands. Framework-free; no build
    step or dependency added to the frontend (the lift, not the React bundle).
  - **Token layer** in `styles.css` (lifted from the source object): `--clay/--ok/--warn/--flow`
    + surfaces/text scale, dark **and** light themes, clay/indigo/teal accents. The Dock's
    hardcoded hexes stay pixel-stable (no regression).
  - **Two read-only backend projections** (`windows-widget/src-tauri/src/room.rs`):
    `room_metrics` (throughput, median s/page, survival average, recent audits, vault count —
    derived from `events.jsonl` + the anchor/pending/held manifests + the vault Library clone)
    and `gpu_vram` (live `nvidia-smi`; null when there is no probe). Both pure projections; the
    converter/formatter are never touched.
  - Verified live in the real Tauri app: Room renders true state (VRAM from nvidia-smi, vault
    count from the Library, survival average from the manifests, the real Cybernetics `fail` in
    terracotta), clean boot (no JS errors), `clippy -D warnings` clean, `tauri build` green.
    Deferred to the next installment (docs/16 §8): the Wall surface, the canvas transit belt,
    the drill-down file explorer, and live convert page %.

### Fixed

- **S45 — the conversion timeout no longer makes long books unconvertible (2026-07-25).** Found while
  estimating a run, not by a report: `convert_and_ship.convert()` hard-killed Marker at a **flat
  3600 s**. At the measured 1.5–3.4 s/page for the clean lane, that made **any book over roughly 1,000
  pages structurally impossible to convert** — it would always be killed mid-run and surface as a
  generic "marker timed out" rather than a size limit. A 1,356-page *Investment Valuation* (Damodaran
  4e) straddles the cap exactly at 34–77 min.
  - The cap now scales with the book: `max(3600, pages * 20)`. Twenty seconds per page is ~2.5× the
    worst rate ever measured on this machine (8.08 s/page, a dense 439-pp scan), so it still catches a
    genuine hang while never punishing a book for being long. The error message now reports both the
    cap and the page count.
  - `watch_and_convert.convert_one()`'s outer wrapper went **7200 s → 21600 s**. It is a backstop
    against a wedged child blocking the queue, so it must sit *above* the inner cap — at 7200 s it
    would silently have become the real limit and the inner fix would have been useless on the normal
    drop-folder path.
  - Caveat recorded honestly: raising a timeout does not make a large book *succeed*. The same session's
    attempt on that 1,356-page book **stalled** at the VRAM ceiling (9,469 MiB of 10,240 used, 100 %
    utilization, 20,858 s of CPU, and the live progress frozen at `Recognizing Text 0/1747` for 5 h) and
    was killed deliberately. Mitigations proposed but **not** applied unattended: a page-count-aware
    recognition-batch cap (below the current flat 32 for very large books), or `--page_range` chunking
    so a long book is restartable instead of all-or-nothing.

- **S39 — the widget window now respects a manual resize (2026-07-23).** Rab reported the widget
  "defaults to a size" — dragging an edge to enlarge it reverted within a moment. Cause: `reflow()`
  (`main.js`) re-asserted `setSize(480, content-height)` on nearly every poll (via
  `pfCheck → pfRender → pfResize → reflow`, even with an empty queue), pinning the width to 480 and
  the height to content, and it fired **regardless of surface** (so it also yanked Room/Wall back
  toward Dock dimensions). The window was already `resizable: true` — the frontend was fighting the
  user. Fix (frontend-only, no Rust): a manual resize is now detected via `getCurrentWindow().onResized`
  (the event dims compared against the last size we set, with a short suppress-window after our own
  `applySize` to ignore the settle echo) and **remembered per surface** (`userSize.{dock,room,wall}`).
  `reflow()` is now Dock-only and, once the user has sized the Dock, only **grows** height to prevent
  a content clip — it never shrinks and never touches width. Surface switches restore the remembered
  size (else the default: Dock content-fit, Room 760×600, Wall 900×500). Verified live on the real
  widget: a programmatic resize to 796×639 **held across 13 s of polling** (was reverting to ~496),
  and the boot log recorded the `onResized` beacon (`user-sized dock → 780×631`). `node --check`
  clean, `tauri build` green.

- **S37 — the orphan-watcher shutdown: a force-killed / crashed widget can no longer leave a
  watcher running (2026-07-22).** Found by the S36 live PDF test: `watcher::stop` only ran on a
  graceful shutdown (the ⏻ button or the window-`Destroyed` event), so `Stop-Process -Force` or a
  crash skipped it — the Python watcher lived on, kept polling `drop/`, and kept spawning converts;
  several such orphans racing the same file thrashed the 10 GB GPU (four concurrent Marker
  instances, lock held for minutes, no completion). Fix (`watcher.rs`): the watcher — and, by job
  inheritance, its Marker convert subprocesses — is assigned to a **Windows Job Object with
  `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`**. The widget holds the only handle to that job for its whole
  life, so when the widget process ends by **any** means (clean close, force-kill, or crash) the OS
  closes the handle and terminates the whole job tree. Verified live: a `Stop-Process -Force` of the
  widget — including **mid-convert** — takes the watcher *and* the running Marker convert to zero.
  The ⏻ "pause intake" path is unchanged (the widget stays alive → the job handle stays open → an
  in-flight convert still finishes); only widget **exit** tears the tree down. Adds `windows-sys`
  (already in the lock via tauri — no new version).

- **S32 — four defects found while live-testing the Assay (2026-07-21).** All surfaced by
  running the pipeline end to end (Rab installed the widget and dropped real documents);
  all fixed and verified.
  - **Widget auto-start crash on a Start-menu launch.** A GUI (windows-subsystem) process has
    no console, so the spawned Python watcher inherited invalid std handles and died on
    startup before it could log — the drop queue filled but nothing converted ("auto-start
    runs, nothing happens"). `watcher.rs` and `preflight.rs` now spawn children with explicit
    `Stdio::null()`. Masked previously because terminal/dev launches supplied a console to inherit.
  - **Widget freeze while the vault host is offline.** `vault_check`/`vault_pull` run
    `git fetch` over tailscale ssh with no timeout, and Tauri runs synchronous commands on the
    main UI thread — so an unreachable ThinkPad hung the whole window ("not responding") every
    45 s poll. `main.rs` now makes both `async` + `tauri::async_runtime::spawn_blocking`, moving
    the blocking git off the UI thread.
  - **Clean-lane VRAM thrash / timeout on figure-dense PDFs.** The clean lane ran Marker
    uncapped; a diagram-heavy born-digital book (91 pp) auto-scaled its batch to fill the 10 GB
    card, thrashed, and hit Marker's 1-hour timeout (DNF). Only the OCR lanes were capped.
    `convert_and_ship.route()` now applies `--recognition_batch_size 32` to the clean lane too.
    Live-verified: the same book re-converted at ~8.0 GB peak (was 9.9), no thrash.
  - **Survival-Audit degeneration false positives.** The tripwire fired `fail` on a legitimate
    table-and-template-heavy book: dense markdown tables tripped the zlib half, and repeated
    section headings (`#### a. goal of model` ×48) tripped the repeated-line check.
    `fidelity_audit.degeneration()` recalibrated (docs/15 §9.2): the block rule is now
    `zlib < 0.20 AND trigram ≥ 40` (a real loop is both crushed-compressible and word-repetitive;
    tables have low trigram), and the repeated-line check measures the longest CONTIGUOUS run,
    not the total (loops repeat contiguously; headings/table rows are distributed). Re-verified
    over all five books — Brain of the Firm still flags (zlib 0.003, trigram ×2,267); Cybernetics
    and the other three clear. Zero false positives, true positive preserved.

### Changed

- **S30 — the Survival Audit's enforcement policy is SIGNED; `compute_verdict` gates on the two unambiguous signals (2026-07-20).**
  Closes the S28 "awaiting threshold sign-off" gate (docs/15 §12). `windows-converter/fidelity_audit.py`
  `compute_verdict` rewritten: **degeneration** (OCR/LLM repetition loops — witness-free, so it
  gates on either lane) and **analyst near-exact loss** (`doc < 0.995 OR run ≥ 25`) are now the
  only signals that reach `fail`; survival/agreement score, page flags, omission runs, and
  garbage rate are report-only **localizers** (`flag` at most) — acceptable books measure
  0.76–0.96 survival (legitimate reflow), so gating on them would false-fail good work and erode
  the terracotta signal. A clean-lane survival gate was explicitly considered and rejected.
  **Verified** over all four vaulted books: Brain of the Firm → `fail` (degeneration; worst block
  zlib 0.003, trigram ×2,267), the other three → `pass` — zero false positives; the prototype's
  loose-threshold Textor false alarm is cleared at the production thresholds. The verdict is
  always computed and recorded honestly; **enforcement is a separate, default-off lever**
  (`audit-mode.txt` `report`|`enforce`; a `fail` under `enforce` parks the bundle in `held/`
  rather than shipping — contract in docs/15 §12, wired in the dedicated widget-build session).
  Widget projection designed and specced as **§13 (The Assay)**: a `◎ assay` line station + an
  evidence card (damage map + verbatim runs) + the `report ⇄ enforce` control, terracotta
  reserved for `fail` only. No pipeline behavior changes yet (verdict-only; enforce defaults off).

### Added

- **S33 — the Opsroom, a quarantined control-panel dashboard prototype (2026-07-21).**
  A professional, self-contained, zero-dependency dashboard representation of the pipeline,
  under a new `prototypes/` **quarantine section** (category/name convention; no pipeline
  coupling; CI untouched — see `prototypes/README.md`).
  `prototypes/control-panel/opsroom/opsroom.html` renders the 6-station line, a live canvas
  **transit viewer**, golden-signal KPI tiles, a convert-station progress panel with live
  ETA, the **Survival Audit** (verdicts + damage map), and a live event stream — driven by a
  self-contained simulation on realistic figures; theme-aware, `prefers-reduced-motion`-safe,
  palette-cached for a light 60 fps loop. Design lineage (see `DESIGN.md`): Project Cybersyn's
  Operations Room (Beer + Bonsiepe) × ISOTYPE × modern observability practice × Linear × the
  Claude Design System. **Quarantined and disposable** — it reads no pipeline state and
  triggers nothing; graduating it into the widget would be a separate, explicit decision.

- **S31 — the Assay: the Survival Audit's widget projection (docs/15 §13, 2026-07-20).**
  The audit becomes a see-and-steer channel in the widget. A new `◎ assay` line station
  (between gate and ship) carries the last conversion's verdict as a dot — green pass, amber
  flag, **terracotta fail, the only pulse** — with the survival number beside it. On flag/fail
  it opens an evidence card: a book-length **damage map** (OCR-loop zones as terracotta bands
  from the manifest's `degeneration_detail.worst` line positions ÷ a new `md_lines` field;
  omission runs as amber bands by page), the worst runs **verbatim** (chars/trigram/excerpt),
  a `report ⇄ enforce` control, and a `⟳ re-convert` remedy. Pure projection: new Rust
  `assay.rs` (`status` reads the newest anchor/pending/held `manifest.json` fidelity block +
  the held queue; `get_mode`/`set_mode` on `audit-mode.txt`; `reconvert` re-queues
  `drop/done/<src>` → `drop/`), four commands in `main.rs`, and the station + card + poll in
  `index.html`/`main.js`/`styles.css`. **Enforcement wired, default off:**
  `convert_and_ship.audit_mode()` + `_enforce_hold()` park a `fail` verdict in `held/<sha16>/`
  (with its manifest) instead of shipping, at all three ship sites (direct / defer-auto-local
  / resume); `report` mode is a verified no-op. The remedy's vault swap is still a manual
  content-replace (THE SUPERSEDE GAP). Verified: `cargo clippy -D warnings` clean, Python
  `py_compile` + `audit_mode()` → `report`, `main.js` parses. Live Beer flag→re-convert→
  re-audit test + `npm run tauri build` / relaunch pending (the rebuild ritual, Rab-driven).

- **S28 — the Survival Audit: a conversion-fidelity gate (`windows-converter/fidelity_audit.py`, 2026-07-20).**
  Implements docs/15. Measures how much of a source PDF survives into the Marker markdown
  (convert stage) and how much of the Marker markdown survives the qwen pass (analyst stage),
  by window-survival containment against an **ephemeral pymupdf witness** (extracted, scored,
  discarded — nothing doubled or vaulted). Deterministic, CPU-only, long-path-safe (`\\?\`),
  CJK-aware (space-free char-window matching). Recall-first: it asks "is every window of the
  source findable in the output?", localizes misses into per-page **runs** with excerpts, and
  runs §5 tripwires (degeneration via per-paragraph zlib + repeated-trigram; page-coverage;
  informational asset-delta; reverse-containment anti-hallucination sample; scan-lane
  garbage-token rate). Per-stage asymmetry per docs/15 §6: clean lane = `fidelity`, scan lane
  = `agreement` (imperfect witness, never hard-fails), analyst stage = near-exact (the Marker
  doc is the reference). Writes a `fidelity` block into `manifest.json` (schema §7) that rides
  the unchanged exporter, and emits `stage:"audit"` events. **Wired report-only into
  `convert_and_ship.py`** (convert stage after Marker; analyst stage inline + in `apply_analyst`)
  — every hook is crash-wrapped so an audit failure can never fail a conversion; the verdict is
  recorded but **gates nothing** until thresholds are signed off (docs/15 §9). Activates on the
  next watcher restart. Widget projection (terracotta-on-fail) deferred to a post-sign-off slice.
  Calibrated over the vaulted books: the degeneration tripwire cleanly flags Brain of the Firm's
  two loop zones and none of the other three at the §9.1 priors (zlib<0.20 OR trigram≥40);
  survival/runs validated as a localizer (findings in the S28 Session Log).

- **S18 — pre-flight analyst card in the widget + `windows-converter/` GPU lane (2026-07-19).**
  The Phase 4 intake inversion's Desktop half (docs/11+12): a new top-level
  `windows-converter/` (Python, runs in the `marker-env` outside the repo) converts
  documents on the Desktop GPU with Marker — policy-routed via a text-render-mode-3 OCR-layer
  probe (default vs `--strip_existing_ocr` + capped batches) — assembles bundles
  format-identical to `linux-converter`'s, and ships them to ThinkPad staging over
  tar-through-`tailscale ssh` (dot-dir + atomic `mv`); the unchanged exporter commits them
  (cross-machine dedup live-proven: EXPORTED `6008eb66`, re-ship + Beer both EXPORT-SKIP).
  Optional link-fenced analyst pass (`analyst.py`): every embed becomes an opaque
  `⟦IMG-n⟧` token before the LLM sees text and must survive verbatim, or that chunk ships
  un-analyzed — two backends behind one flag, local `qwen3:8b` (air-gapped, 138 chars/s
  measured) and `gemini-flash-latest` (cloud, 186.7 chars/s, 13 s pacing + backoff under
  the measured free-tier 20-request window), both book-proven (44/47 with 3 fence-saves;
  7/7). `watch_and_convert.py` watches `drop/` (dotfile skip, stability wait, sequential
  single-flight, done/failed archiving; live E2E drop→convert→ship→EXPORT-SKIP in 52 s).
  **Widget:** new `#preflight-cards` panel (vault-bar's Claude Code styling) rendering
  `analyst.preflight()` JSON per parked bundle — measured ETAs, chunk/token counts,
  GPU-busy flag, free-tier warning, privacy labels, terracotta-highlighted recommendation —
  with three routes (🔒 Local / ☁ Flash / Ship as-is); a click spawns the converter's
  `--resume` detached (`preflight.rs`, `CREATE_NO_WINDOW`) and the card tracks
  running/failed states until the queue clears and the vault bar takes over. New config
  keys (all `serde(default)`, feature hidden when unset): `gpu_pipeline_dir`,
  `gpu_python_exe`, `gpu_converter_dir`. Window grows per visible card
  (`core:window:allow-set-size`). Watcher analyst-mode gains `ask` = park for the card.
- **W8 — "Add to Library" button in the widget (2026-07-12).** New `#vault-bar` under the
  tiles (Claude Code-styled: near-black panel, terracotta `#D97757` accent, monospace, ✳
  glyph) backed by a new `src-tauri/src/vault.rs`: `vault_check` (git fetch + behind-count +
  new `Inbox/<slug>/manifest.json` slugs vs `origin/main`) and `vault_pull` (fetch +
  `merge --ff-only`, then reports exactly which bundles arrived). The clone's persisted
  `core.sshCommand="tailscale ssh"` carries all transport; the widget never talks to the
  host itself and never initializes a repo (Decision #4). Button states: hidden when
  `vault_library_dir` (new config key, `serde(default)` so old configs parse) is unset; dim
  "Library · up to date"; glow-pulse "Add N new note(s) to Library" when the ThinkPad has
  pushed bundles this machine hasn't pulled; spinner while pulling; green "✓ Added: <slugs>".
  Polls every 45s, tightens to 10s for 3 minutes after any drop allocated to
  `pipeline/convert*` (a conversion is ~1–2 min away from landing). Window height 186 → 224.
  All git calls pass `-c core.longpaths=true` — the first live pull failed checkout on
  bundle-interior filenames longer than Windows' 260-char MAX_PATH (see L15 coordination
  message; that message also asks the converter to shorten interior names at the source).
  Also fixed while in there: pull errors are now classified fetch-vs-merge so a local
  checkout failure no longer reads as "vault host unreachable", and the exe is built
  `windows_subsystem = "windows"` so no console window spawns behind the widget.
  Live-verified end to end: the Textor ingest (`fd0e50a`) lit the button with its slug
  within one poll, one click pulled + checked out the bundle (note + 4 assets + manifest),
  and the bar settled back to "up to date".

- **Vault exporter (library pipeline, Part 4 — L11/L12).** `linux-converter/converter/exporter.py`,
  a second watch inside the existing converter service (no new unit): `library/staging/` bundle
  arrivals — plus a startup sweep for bundles that landed while the service was down — are
  committed into the working clone `~/file-portal/vault-work` at
  `Library/Inbox/<slug>--<sha256[:8]>/` and pushed to the local bare repo `~/file-portal/vault.git`
  (the transport resolved + wired in Open Decision #4). Per Decisions #5/#6: no tag/folder
  placement, no minted `[[links]]`, assets stay inside the bundle folder. Invariants enforced in
  code: creates new notes only (pathspec-scoped commits, committed paths never overwritten);
  re-ingest of an identical `source_sha256` is a no-op log line, deduped by `git grep` over
  committed `manifest.json` files in the **bare** repo so notes the Desktop has filed out of
  `Inbox/` still count; the staging copy is deleted only after the push succeeded AND
  `git cat-file -e` confirms the commit and every bundle file's blob in the bare repo — never on
  write-success alone (L12). Any git failure logs `EXPORT-FAIL` and keeps staging for the next
  sweep; a commit that pushed but crashed pre-verify resumes at push, not re-commit. Ingest
  commits are self-identifying (`user.name=file-portal-converter`). 8 unit tests against real
  temp git repos. Live-verified 2026-07-11 including the dedup no-op and blob-verified deletion.

### Fixed

- **Ship stage: an offline ThinkPad was masked as a tar timeout (2026-07-19, `e7ea85a`).**
  During the first ⚡ production run (Brain of the Firm), the ThinkPad going dark mid-ship
  surfaced as `tar … timed out after 60 seconds` (the 17:57 UTC `gate/failed` event): ssh
  died on the dead tailnet dial, leaving the local tar wedged writing into a dead pipe, and
  tar's own 60 s timeout fired first — burying the real network error. `ship()` now wraps
  the ssh run in try/finally, kills the wedged tar whenever ssh fails or times out so the
  actual error propagates, and the tar wait is 60 → 600 s for large bundles. The book
  recovered and vaulted the same night (20:49 UTC, `f310f759`). *Entry written
  retroactively in S27 — the fix was committed after S26's close and §4 accounting caught
  it with no CHANGELOG entry.*

- **CI first-contact failures on PR #1 (2026-07-13).** The workflow (written 2026-07-05 on
  master) had never run against the branch's code. Two independent breaks: (1) `CI / python` —
  pytest collection died with `No module named 'allocator'` because the runner pip-installs
  only requirements and bare `pytest` doesn't put the package root on `sys.path` (local venvs
  never hit this). Fixed with `[tool.pytest.ini_options] pythonpath = ["."]` in
  `linux-receiver/pyproject.toml` and `linux-converter/pyproject.toml` (converter tests aren't
  in CI yet — same latent bug fixed while there); reproduced and verified in a fresh
  requirements-only venv (collection error → 24 tests collected). (2) `CI / rust` —
  `cargo fmt --check` diffs in `config.rs`/`main.rs`/`status.rs`/`vault.rs`, all code written
  after the July 5 formatting pass. Fixed with `cargo fmt` (style-only, zero behavior change);
  `cargo clippy --all-targets -- -D warnings` verified clean locally so the never-reached
  clippy step doesn't become the next surprise. Known-red follow-ups, not fixed tonight:
  CI doesn't run `linux-converter`/`linux-dashboard` tests, and `actions/checkout@v4` +
  `setup-python@v5` emit Node 20 deprecation warnings (bump to current majors later).

- **Bundle-interior filenames blew past Windows' 260-char MAX_PATH on the consuming end
  (L15, found by W8's first live click, 2026-07-12).** The bundle directory was already
  slug-clamped in the vault, but the names *inside* it re-derived from the raw source stem:
  a 200-byte-clamped `.md` plus engine-named asset PNGs (`<full-source-name>-<page>-<idx>.png`,
  ~230 bytes for real Anna's Archive names) pushed full vault paths past 330 chars — the
  Desktop needed `core.longpaths=true` to check the Textor bundle out at all. Fixed at the
  source, both halves: (1) the converter now hands the engine a short, sanitizer-proof
  hardlink (`<slugify(stem)[:40]><ext>`, hardlink with copy fallback) inside the sha-keyed
  assembly dir — pymupdf4llm derives image names from the document path it opens (its
  `filename=` kwarg is ignored for path-opened docs), so asset basenames drop to ≤ ~61 bytes;
  the link is removed before publish and is never part of the bundle. This also closes a
  latent Linux-side overflow: a >243-byte source name + `-0001-00.png` would have exceeded
  ext4's 255-byte component limit and quarantined, L13-style. (2) `bundle.clamp_name`'s
  budget drops 200 → 80 bytes, so the worst-case vault-relative note path
  `Inbox/<slug60>--<sha8>/<stem80>.md` is exactly 160 bytes — inside MAX_PATH with margin
  for real vault prefixes. Regression test (red-first on both halves): a 230-byte spaced
  stem with an embedded image converts, every emitted vault-relative path ≤ 160 bytes, the
  bundle root holds exactly note + manifest + assets/, and every embed resolves on disk.

- **Black console window flashing every 45 seconds (W8 follow-up, 2026-07-12, user-reported).**
  W8's `windows_subsystem = "windows"` removed the widget's own console — which the child
  processes (`git` vault polls, `tailscale ssh` status/transfer calls) had been silently
  attaching to. Orphaned, each spawn opened its own console window for the duration of the
  command, most visibly the 45s vault poll. All three spawn sites (`vault.rs`, `status.rs`,
  `transfer.rs`) now pass `CREATE_NO_WINDOW` (0x08000000). Verified across a live poll
  cycle: no window, bar still reports fresh state.

- **Spaced filenames with images quarantined every time (L13, found by the first real
  document 2026-07-12).** pymupdf4llm sanitizes the entire image output path it is given —
  spaces become underscores in *directory components* too — while the converter built its
  assembly temp dir from the source stem verbatim, so the engine wrote images into a
  sibling directory that never existed and the first image write failed the whole
  conversion. The assembly dir is now keyed on the source SHA-256
  (`.part-<sha256[:16]>`), which is sanitizer-proof by construction and immune to
  filename-length pressure; the published bundle keeps the original stem, spaces and all.
  While in there, bundle names are clamped to a 200-byte budget (`bundle.clamp_name`) —
  ~225-byte Anna's Archive stems plus the derived `.part-<name>.staging-copy` suffix
  brushed ext4's 255-byte component limit. Regression-tested with a spaced-name+image
  fixture that reproduces the exact field failure, and live-verified end to end.
- **Exporter placed bundles at `Library/Library/Inbox/` in the vault (L14, cosmetic).**
  Decision #6's `Library/Inbox/<slug>--<sha8>` is a *vault-relative* path, but the repo
  root already IS the vault's Library folder (Decision #4), so `exporter.py`'s
  `INBOX_REL` doubled the level; the L11 tests asserted the same misreading and stayed
  green. Now `Inbox/<slug>--<sha8>` repo-relative. No migration: the Desktop had already
  filed the one affected bundle to repo-root `Inbox/` as a normal Decision #6 filing move.
- **Exporter event stall (found live 2026-07-11, fixed same session).** The converter assembles
  two dot-prefixed temp dirs inside `library/staging/` per bundle; their `created` events each
  held the watchdog dispatch thread for the full 60s stability timeout (the dir is renamed away,
  so its `manifest.json` never appears and `rglob` on the missing dir spins yielding `[]`),
  delaying every export by 2×60s. Dot-dirs are now skipped before the stability wait, and the
  wait bails when the directory vanishes. Export latency measured after the fix: ~25ms.

- **Conversion engine (library pipeline, Part 3 — L7-L10).** `linux-converter` now converts
  instead of logging "would convert". Dispatch is first-match by extension, mirroring the
  allocator's rules idiom: `.pdf`/`.epub` → PyMuPDF4LLM (layout mode; `import pymupdf.layout`
  is ordered before `import pymupdf4llm` in `converter/engines.py` because pymupdf4llm decides
  OCR availability at import time), `.docx` → Pandoc (`-t gfm`, media extracted and flattened
  into the bundle's assets). Clean-lane `.pdf`/`.epub` files are pre-probed for a real text
  layer (`chars_per_page`, logged on every conversion); sub-threshold files reroute to
  `pipeline/convert-scan-inbox/` as a normal `allocated` status event. The Scan lane
  (`use_ocr=OCRMode.FORCE_DROP_OLD` at `ocr_dpi` — NOT the plan doc's `force_ocr=True`, which
  in pymupdf4llm 1.28 maps to `FORCE_KEEP_OLD` and would *keep* a bad prior OCR layer; in 1.28
  layout mode OCR is need-based and automatic in every lane, and the modes only control prior
  OCR spans) is terminal: sub-threshold OCR yield quarantines the source
  with a `rejected` event — no retry cycle is possible by construction (Open Decision #3,
  resolved 2026-07-09). Event model, verified empirically: the allocator hop is a rename whose
  source is outside the converter's watch, which inotify reports as an unpaired `IN_MOVED_TO`
  = a plain `created` event (never `moved`, never `close_write`) — so the handler reacts to
  `created` with a size-stability wait, plus `moved` (the reroute) and `closed` (in-place
  writes), deduped by consuming the source on success.
  Output is a bundle folder (`<name>.md` + `assets/` + `manifest.json`
  with source SHA-256), assembled in a dot-prefixed temp dir and published by atomic rename to
  both `library/anchor/` (immutable snapshot) and `library/staging/` (transient export queue);
  image links are rewritten to Obsidian embeds (`![[assets/…]]`) and every markdown output is
  frontmatter-stamped with engine/lane/`lane_reason`/OCR provenance. Tuning lives in
  `linux-converter/config/converter.toml` (`min_chars_per_page` seed 100 — provisional),
  re-read per event like `rules.toml`. 26 unit tests added.
- **`convert-scan` category routing.** `rules.toml` routes `convert-scan` drops (`*.pdf`,
  `*.epub` — no `.docx`, Pandoc has no OCR) to `pipeline/convert-scan-inbox/`. This is the
  destination for the Desktop's W7 tile, whose meaning is now *force-OCR override* rather than
  "the lane for scans" (the probe detects scans itself) — see
  `coordination/messages/2026-07-09T23-05--linux-to-desktop--w7-semantics-force-scan.md`.
- **"Force OCR → Vault" widget tile (W7).** Sixth portal (`category = "convert-scan"`, 🔍)
  added to `config.rs` `AppConfig::default()` and the `portals.json` reference copy (and the
  live `%APPDATA%\file-portal\config.toml`). Per the 2026-07-09T23-05 coordination message the
  label is deliberately NOT "Scan → Vault": the Clean lane detects scans itself, so the tile is
  the user override that discards a garbled embedded OCR layer and re-OCRs at 300 dpi. No
  `main.js` change — the reroute/reject paths reuse the existing `allocated`/`rejected` events.

### Fixed

- **Hardcoded service paths (Defect A, flagged 2026-06-25, since duplicated).** Both
  `file-portal-allocator.service` and `file-portal-converter.service` hardcoded
  `%h/file-portal-src/...` while their `install.sh` copied the unit verbatim, breaking any
  other clone path. Both installers now `sed`-substitute `__WORKDIR__`/`__EXEC_PATH__`
  placeholders, matching `linux-dashboard/scripts/install.sh`.

- **Status feed regression on `feat/library-pipeline` (widget ✓/✗ feedback dead).** The
  `logs/status.json` writer was implemented on `master` (`0c3a074`) but never merged into the
  branch, so the widget's v2 feedback loop stalled at "allocator pending" the moment the ThinkPad
  service restarted onto branch code (found by W5 E2E, 2026-07-08). Ported `allocator/status.py`,
  the CLOSE_WRITE/`on_closed` completion handling with the non-inotify size-stability fallback,
  the per-file exception guard, quarantine collision-renames, and the 24-test suite
  (`tests/`, `requirements-dev.txt`) into the branch, reconciled with the L1 quarantine location
  (`root/quarantine` kept; master's `inbox/quarantine` discarded). Rejection semantics decided
  per the W5 coordination message: `rejected` = quarantine only; unmatched extensions are
  `allocated` to `sorted/misc` (the widget shows `dest`).

- **Widget showed nothing on launch (blank/invisible window).** `windows-widget/src/main.js`
  imported the Tauri JS API with bare ES-module specifiers
  (`import { invoke } from "@tauri-apps/api/core"`). The project intentionally ships no
  frontend bundler (see `docs/07-development-guide.md`), so the WebView cannot resolve those
  specifiers; the module failed to load, `init()` never ran, and no portal tiles were rendered.
  Because the window is transparent and undecorated, this looked like the app failing to open at
  all. Fixed by enabling `app.withGlobalTauri` in `src-tauri/tauri.conf.json` and reading the API
  off the injected `window.__TAURI__` global (`core`, `webview`) instead of importing it.
- **Invalid dev configuration.** Removed `build.devUrl: "../src"` from
  `src-tauri/tauri.conf.json`; `devUrl` expects a dev-server URL, not a static directory, and the
  widget is run from the built `frontendDist` assets.
- **Drag-and-drop hit-testing was wrong under display scaling.** `tileForPosition()` compared the
  drag event's physical-pixel coordinates against `getBoundingClientRect()` CSS/logical pixels, so
  tiles were mis-targeted on any DPI scale other than 100%. Coordinates are now divided by
  `window.devicePixelRatio` before the hit-test.
- **First drag frame was ignored.** The drag handler only reacted to `over`; it now also handles
  the initial `enter` event so highlighting starts immediately.
- **File transfer transport could not work as written.** `src-tauri/src/transfer.rs` shelled out to
  `rsync`/`scp` over `tailscale ssh`. `rsync` is not present on stock Windows, and `scp`/plain `ssh`
  fail host-key verification against Tailscale SSH's managed keys. Rewrote `send_one_file()` to
  stream each file's bytes through `tailscale ssh <user>@<host> "mkdir -p … && cat > .part-<name> &&
  mv -f .part-<name> <name>"`, removing the rsync/scp dependency. Writing to a `.part-` temp and
  renaming into place makes arrival a single atomic `on_moved` event (the allocator never picks up a
  half-written file), and the bytes are streamed with `std::io::copy` instead of being buffered in
  RAM. Remote paths are shell-quoted (with `~/` preserved for expansion) to handle filenames
  containing spaces or quotes.
- **A malformed `config.toml` silently reverted to `CHANGE_ME` defaults.** `src-tauri/src/config.rs`
  now surfaces the TOML parse error (naming the file) and exits, and only seeds defaults when the
  config is genuinely absent — a present-but-unparseable config no longer masquerades as a working
  install pointed at the placeholder host/user.

### Added

- **`convert` category routing (library pipeline, Part 2).** `linux-receiver/config/rules.toml`
  routes `convert` drops (`*.pdf`, `*.epub`, `*.docx`) to `pipeline/convert-inbox/` — a process
  mouth for the converter, deliberately outside `sorted/`. Unmatched extensions still fall through
  to `sorted/misc`. Verified live on the ThinkPad allocator.
- **`linux-converter/` service skeleton (library pipeline, Part 2).** A second `systemd --user`
  watcher (`file-portal-converter`) mirroring the allocator's structure and event model (prefer
  `on_moved`, fall back to `on_created`, skip `.part-*` dotfiles). Watches
  `~/file-portal/pipeline/convert-inbox` and, for now, only logs `would convert <path>` to
  `logs/converter.log` — the conversion engine (PyMuPDF4LLM/Pandoc, Clean/Scan lanes) is Part 3.
  Installed, enabled, and verified end-to-end (allocator hop → converter log) on the ThinkPad.

### Fixed (linux)

- **Quarantine loop.** `allocator/config.py` moved quarantine from `inbox/quarantine/` (inside the
  watched tree — quarantining fired another event and re-processed the file forever) to
  `~/file-portal/quarantine/` at the root. Verified live: an oversized file is rejected once and
  stays quarantined. Docs (`docs/05`, `linux-receiver/README.md`) updated to match.
- **`linux-converter/scripts/install.sh` was not executable** (mode 100644 vs the receiver's
  100755), so the documented `./scripts/install.sh` invocation failed.

- **Widget titlebar with drag and minimize.** The frameless window gains a `data-tauri-drag-region`
  titlebar (grab cursor) with a minimize button wired to `getCurrentWindow().minimize()`;
  `src-tauri/capabilities/default.json` grants `core:window:allow-start-dragging` and
  `core:window:allow-minimize`, and the window height goes 160→186 so the bar doesn't crowd the
  tiles.
- Surfaced transfer errors to the UI and the console (`send_to_portal failed`, per-file failure
  details) and a clearer "dropped outside any portal" status message.
- Enabled the Tauri `devtools` feature in `src-tauri/Cargo.toml` for in-app debugging of the
  WebView during development.

> Note: the widget binary must be rebuilt for these changes to take effect
> (`cd windows-widget && npm install && npm run tauri build`, or `npm run tauri dev` for a
> hot-reloading dev run). The previously running `target/debug` binary predates this fix.
