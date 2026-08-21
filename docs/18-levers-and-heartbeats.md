# 18 — Observability + Control: the Levers-and-Heartbeats Overhaul (design brief)

*Design brief of record, S51 (2026-07-31). Implementation goes to dedicated sessions per the
build cadence — this document is the spec their plans expand from. Two ChatGPT-generated mockup
sets (relayed by Rab, assessed on merits per the external-AI-relay protocol) served as visual
aids for §7; every claim about the current system in this doc was verified against source, not
mockups.*

---

## 0. Why — and why now

S48 spent a forensic afternoon discovering that the widget's watcher had been dying **silently at
every spawn for five days** while a green button said "running." S50 confirmed the exporter's
refusal of a supersede was visible from the desktop **only as absence**. Between them, one night
produced ten distinct observability failures — and Rab, reviewing the control side, named the
missing principle for the other half:

> **Every autonomous behavior gets a visible, per-stage manual lever.**

Observability and control are two faces of one design: the system must continuously *confess its
state*, and the operator must be able to *reach into any stage* without editing config files in a
terminal. This brief merges the S48 observability survey with the control-surface overhaul.

## 1. The ten blind spots (each observed live, S45–S50)

1. **Status flags are claims, not evidence** — the ⏻ stayed green over a dead watcher; the Room
   header disagreed with it (two derivations of one fact).
2. **Discarded death certificates** — `try_wait()` learns exit codes and throws them away; exit
   `0x67` had to be recovered via a temporary Security-log 4689 audit.
3. **Lost last words** — child stderr goes to NUL; the venv launcher's "No Python at…" died unheard.
4. **Progress without a derivative** — both wedge species share one signature (progress mtime
   frozen while the lock is held); nothing watches for it.
5. **Vantage-blind verification** — S45's exe adoption was written AND SHA-verified inside the
   sandbox mirror; false sight is worse than blindness.
6. **Units of work without heartbeats** — the analyst logs `start` and `done` with 20 silent
   minutes between; GPU rhythms had to be read like tea leaves.
7. **Promises never audited** — ETAs are learned but no promise-vs-actual line is ever filed.
8. **The cross-machine seam** — exporter outcomes live only in the ThinkPad's journal; the
   desktop sees refusals as absence (S50, live).
9. **No pain channel** — five silent days of failure escalated to no surface anyone reads.
10. **The unbounded flight recorder** — `events.jsonl` grows forever with no rotation or
    corruption story, and everything reads it.

## 2. Design principles

- **Liveness is proven, never remembered.** Heartbeats (file mtimes, events) with rendered *age*;
  a state without a timestamp is a claim.
- **Every observation carries its vantage.** Writes verified only from an independent surface
  (the MSIX lesson, twice over); manifests grow a `verified_from` stamp.
- **One truth source per fact.** The ⏻ and the Room header must derive from the same read.
- **Every autonomous behavior has a lever, every lever has a surface.** `analyst-mode.txt`,
  `audit-mode.txt`, and their successors stay the backend truth (single-writer files), but the
  widget renders each as a labeled, clickable policy row — no more terminal-only policy.
- **Policy is visible before it acts.** "Survival < 0.7 requires remedy" belongs on the card, not
  in a doc the operator has to remember.
- **The projection law stands.** All new UI is read-only projection; levers write only the
  backend's own config/marker files, exactly as the existing gate/audit toggles do.
- **A number that decides something is a LEVER, not a constant.** *(Signed Rab, S106,
  2026-08-21: "determine if it's a feature deep work, or it should have the capability to be
  modular, and change in numbers from an operator. This should also be a framework when
  creating features or new implementation.")* **This is the modularity gate, and every new
  feature passes it at design time**, before the first line is written:

  1. **Does it carry a number or a policy choice that changes what a human is shown or what
     the system does?** If no — it is deep work, hard-code it, done. If yes, continue.
  2. **Then it ships as a lever**, not a constant: a single-writer file the operator edits,
     a documented menu or numeric range, and a fallback to the signed default for anything
     unparseable or out of range — *named in the output, never silently ignored* (the
     `chunk_batch()` contract).
  3. **The report states the EFFECTIVE values it ran on**, not the defaults. A number that
     travels without its configuration is the failure `docs/45` §1 names Family 1.
  4. **Report-only until calibrated** (`docs/15` §6), and **every lever gets a surface** —
     the row above. A lever with no surface is half a law; if the surface is blocked on an
     unsigned decision, say so in the inventory rather than pretending it is done.
  5. **A constant is still admissible — with a written waiver** naming who may change it and
     what evidence would move it. The gate forces the choice to be *made*, not to go one way.

  Enforced mechanically: `close.sh` reports threshold-shaped constants added since the pin
  that have no lever and no waiver. It reports VALUES and never blocks — the judgment is the
  author's, but it can no longer be silent.

## 3. The lever inventory

| Lever | Exists today | Surface today | Target |
|---|---|---|---|
| Analyst routing (`ask/local/gemini/off`) | ✅ | ✳ gate selector + file | keep; add per-card override (exists) |
| Audit `report ⇄ enforce` | ✅ | lever on assay card + file | keep; label with its policy sentence |
| Re-convert remedy (⟳) | ✅ newest-only | assay card | **per-held-item buttons** (chip filed S50) |
| Stall policy | ❌ (decided §5.1) | — | policy row + per-event alert |
| Human-bless override | ❌ (decided §5.4) | — | button on flag-verdict cards + exporter contract |
| Analyst-only re-run | ❌ (gap, S48) | — | second remedy button: "re-analyze" (no re-convert) |
| Queue order / priority | ❌ (queue is FIFO mtime) | — | queue panel actions (§7) — needs design care: the watcher's sorted-iterdir IS the queue |
| `keep_alive` middle (analyst VRAM courtesy vs speed) | ❌ (hardcoded 0) | — | policy row, default unchanged |
| Sunshine remote-origin (`csrf_allowed_origins`) | ❌ (deferred, docs/17) | — | out of widget scope; runbook item |
| **P-1 figure triage + its 7 thresholds** (`figure-triage.txt`) | ✅ S106 | **file only — no surface yet** | assay policy row **when P-1's host is signed** (docs/41 §2 variable 4, still OPEN). First feature built under the modularity gate above; `mode=caption\|off` plus seven numeric thresholds, ranges enforced, effective values printed in `conditions`. **Blocked on the host decision, and said so rather than claimed done.** |

## 4. Observability stages (build order)

- **Stage A — death certificates + stall detector (converter/watcher; small).** Watcher captures
  every child's exit code + a stderr tail ring into `watcher.log` + an `intake/died` event.
  `watcher_status` re-runs `try_wait` per poll and reports honestly. Stall detector: progress
  mtime frozen > **15 min** while `.gpu-lock` held → kill, `failed/`, `convert/stalled` event
  with the triage signature (CPU-flat = deadlock class; GPU-pinned = VRAM class). *Highest value
  per line of code; do first.*
- **Stage B — heartbeats + staleness rendering (widget; pure projection).** Room/Dock render age
  ("watcher ✓ 4 s ago", "progress **frozen 90 s** ⚠"), one shared derivation for ⏻ and header.
- **Stage C — per-unit events + the seam.** `analyst/chunk` heartbeat events (n/total,
  s_per_chunk); exporter outcome events (`EXPORT-*`) travel back over the existing channel so
  refusals are *positive* desktop facts; promise-vs-actual line in every `done` event.
- **Stage D — the algedonic line.** Any `died`/`stalled`/`fail` unacknowledged for M minutes
  escalates to surfaces Rab actually reads: Room banner + morning note + Gmail draft (per the
  overnight-report protocol). Makes five-silent-days structurally impossible.
- **Stage E — hygiene.** `events.jsonl` rotation at session close (ledger row = the summary);
  `verified_from` vantage stamps; heartbeat for the flight recorder itself.

## 5. Decided policies (Rab, S51, 2026-07-31)

1. **Stall policy: kill early on stall signature.** Frozen progress >15 min + lock held → kill,
   file to `failed/`, death-certificate event. (Zero-CPU deadlocks: already fixed at the root, S48.)
2. **Large books: `--page_range` chunking as primary** — restartable slices, merged markdown —
   **with a conservative recognition-batch cap applied inside slices** of very large books.
   **STAGE D SPEC — SIGNED (S57, 2026-07-31, decided with Rab):**
   - **Threshold (lane-aware):** clean lane > 600 pp; scan lane > 400 pp (scan runs hotter —
     Valentine peaked ~8 GB at 465 pp). Page counts from the probe (pymupdf), never metadata.
   - **Slice size: 200 pages.** A lost slice costs ~10 min; each slice re-pays ~90 s model load
     (~18 % overhead at clean-lane rates); Damodaran = 7 slices.
   - **Seams: clean cuts, recorded.** No overlap reconciliation in v1 (silent-text-loss risk).
     Every seam page is recorded in `manifest["chunking"] = {slice_size, batch, seams: [pages]}`
     — findable forever by the audit and the Repair Bench.
   - **Slice recognition batch: A USER LEVER, default 16.** Rab's call, verbatim intent: 8 =
     "keeps it actually useful" (max headroom), 16 = the go-faster default, 32 = "if I really
     want to" (user knows their system). Backend truth = `chunk-batch.txt` (8|16|32, default 16,
     re-read per slice); rendered on the Convert station's policy row; a proper selector joins
     Stage E. Unchunked books keep batch 32.
   - **Resume:** completed slices persist in the work dir keyed by (source_sha, page_range);
     a re-run converts only missing slices. The S52 stall killer supervises each slice; a killed
     slice fails alone.
   - **Progress:** the S42 progress file gains a slice prefix ("slice 3/7 · Recognizing …");
     `convert/slice` events per slice completion; the final `converted` event carries
     `slices: n`.
   - **Assets:** renumbered by absolute page offset, markdown refs rewritten at merge — slice
     runs can never collide.
   - **Audit:** the Survival Audit scores the MERGED whole book, exactly as today.
   - **THE CONVERSION LEDGER (Rab's S57 requirement):** every successful vault conversion files
     a learning record — pages, lane, chars/pp, s/pp, wall, chunked?, slices, slice batch, and
     peak VRAM (the stall monitor's GPU sampler already sees it — record the max). Estimates for
     new books come from SIMILAR past works (same lane, nearest chars/pp band) instead of one
     global median, and every estimate is paired with its eventual actual (the promise-vs-actual
     line, Stage E) so the tracker's reliability is itself visible. The events stream already
     holds most fields — Stage D formalizes the record and upgrades the card's estimator to
     similarity-based.
3. **Valentine: retry next pipeline session.** Scan lane, 465 pp, ~30–60 min; vault note 6
   candidate.
4. **Figure-heavy flag ceiling: human-bless override.** A per-book lever: Rab explicitly
   approves a `flag`-verdict ingest/supersede after reviewing the evidence card. Exporter grows
   a `blessed` path (marker authored ONLY by the widget's bless click — same authoring discipline
   as supersede); UI grows the button on flag-verdict cards. Cybernetics is the first customer.

## 6. The Repair Bench (Rab's expansive idea, thought through)

The bless override accepts a book *as markdown could carry it*. The Repair Bench goes further:
**a human-in-the-loop surface for repairing what conversion structurally lost.**

**Concept:** a side-by-side view, navigated by the audit's own flagged zones/pages:
- **Left: the actual PDF page** (pymupdf raster — already in the stack) at the flagged location.
- **Right: the converted markdown** for the same zone, editable.
- **Corner: a scratch LLM panel** wired to local Ollama, where Rab pastes selected source text
  (or attaches the page image) and drafts a faithful reconstruction — figures become described
  figures, mangled tables become rebuilt tables — then commits the repaired passage into the
  markdown.

**The core insight (Rab, S51): the human IS the vision model.** The essential capability is not
an LLM panel — it is **screenshot-and-embed**: Rab screenshots a diagram from the PDF pane, drops
it into the flagged zone, and the Bench (a) saves it into the bundle's `assets/` under a
collision-safe repair name (e.g. `_repair_p45_1.png`), (b) inserts the
`![repair](assets/_repair_p45_1.png)` reference into the markdown at that zone, (c) stamps the
provenance. The vault already speaks this language — every bundle ships `assets/` + relative
links, and Obsidian renders them natively. A figure-heavy book's note stops *describing* the loss
and starts *containing the figures*. This alone justifies the Bench; everything below is garnish.

**Honest technical notes:**
- **No vision model needed.** The human curates visually; text-only qwen3:8b remains available as
  an optional drafting assistant for prose/table reconstruction (paste text in, get a faithful
  rebuild out). The qwen2.5-VL idea is retired unless a future need revives it.
- Repairs are **provenance-stamped**: `manifest["repairs"] = [{page, zone, by, ts, model?}]` —
  the vault never pretends a human-repaired passage is raw Marker output.
- The audit **re-scores after repair** — survival is recomputed on the repaired note; embedded
  repair images count toward what survived (the scorer must learn to credit them — a small,
  honest extension), so a well-repaired figure-heavy book can legitimately climb toward `pass`,
  making bless unnecessary for some books.
- It lives **outside the conversion path**: a post-audit remedy surface feeding the existing
  bless/supersede rails. Zero pipeline coupling.
- Build path: **prototype first** under `prototypes/` (the quarantine convention) to find the
  right UX — this is the largest UI item in the brief and the most novel; it earns a feasibility
  pass before any widget integration.

## 7. UI overhaul direction (from the mockups, filtered)

**Adopt:** the richer Dock (station rail + live-conversion card with per-stage progress +
next-in-queue); a real **queue panel** (order, priority, est. start from the ETA learner —
depends on §3's queue-lever design); **policy rows with their sentences visible** ("Survival <
0.7 requires remedy" · report ⇄ enforce · Configure); per-item ⋮ menus; the **page-level risk
strip** on the audit card (the flagged-pages heatmap — also the Repair Bench's navigation);
**light theme** (the S34 token layer already carries dark/light — this is finishing work, not new
architecture); "View in Room →" cross-surface links.

**Reject (mockup fictions):** invented numbers/files; "engine: claude-*" (the engine is Marker —
a stamping press, not promptable); "AI Agent" as the SHIP station (it's tar-over-tailscale);
"Retention 90 days auto purge" (**explicitly rejected**: the vault is an archive; nothing
auto-purges); any control that writes pipeline state from the UI in violation of the single-
writer file pattern.

## 8. Staged build plan (each stage = one dedicated session, projection law + rebuild ritual +
unpackaged-adoption rule apply throughout)

| Stage | Contents | Size |
|---|---|---|
| A | Death certificates + stall detector (§4A, §5.1) — **✅ SHIPPED S52** (2026-07-31, adopted `3571F771`, acceptance-tested live: deliberate watcher kill → certificate in ≤5 s; includes the per-held-item remedy buttons pulled forward from Stage C) | S |
| B | Heartbeats + staleness + policy rows (§4B, §3) — **✅ SHIPPED S53** (2026-07-31, adopted `0356FC34`: convert liveness row "✓ Ns ago"/"frozen Ns ⚠" at 120 s clay from the new `progress_age_s` projection; audit lever wears its mode sentence; standing policy line on the Convert station; Stage A styling landed. Liveness row's live proof rides the next real convert) | M |
| C | ~~Per-held remedies~~ (✅ S52) + ~~bless lever~~ + ~~analyst per-chunk heartbeat~~ (**✅ S56**: the bless rail end-to-end — widget-authored sha-bound `bless.json` scp'd into ThinkPad staging, exporter guard amended to the signed "pass, or flag with bless", 5-case seam proof on temp repos; analyst `.analyst-progress.json` per chunk + Room render. Cybernetics = first customer, vaults on the next ThinkPad deploy sweep) · ~~C2~~ (**✅ SHIPPED S58**, docs/19 §3: the analyst-only re-run `--reanalyze` — Marker never runs, eligibility and refusals are Python's, the `.gpu-lock` guard is the widget's; per-bundle ⟲/✓ on every held row, killing the card-flip race; and the **seam receipts** — the exporter files one line per `EXPORT-*` outcome to a plain `receipts.jsonl` (kept OUT of the vault, Rab's call) and the widget tails it over `tailscale ssh` on the vault poll, the two streams merged only at render time. Awaits Rab's ThinkPad deploy + widget adoption) | M–L |
| D | ~~`--page_range` chunking (spec review w/ Rab first; §5.2)~~ — **✅ CONVERTER SIDE SHIPPED S60** (2026-08-01, built to §5.2 verbatim: lane-aware threshold, 200-pp slices, resume keyed by (source_sha, page_range) published outside the temp dir, absolute-page asset renumbering, seams in `manifest["chunking"]`, `chunk-batch.txt` lever + live policy row, slice-prefixed progress + `convert/slice` events, and the conversion ledger with a similarity-based `estimate_from_ledger()`). Proved by 25 checks on a synthetic 610-pp book with Marker faked at the process boundary — including a killed slice resuming byte-identically. **REMAINING: the Damodaran acceptance run** (1–2 h GPU, Rab's go) and Stage E's promise-vs-actual surfacing | L |
| E | Queue panel + Dock refresh + light theme (§7) | M |
| F | Algedonic line + hygiene (§4D–E) | M |
| G | Repair Bench prototype (quarantined; §6) | L |

Valentine's retry (§5.3) rides whichever pipeline session comes first and needs no build.

**Done-when for the brief itself:** every stage above has shipped or been consciously retired;
blind spots 1–10 each map to a shipped mitigation; every lever in §3 renders on a surface.
