---
title: Desktop Pipeline
section: Pipeline
last-verified: 2026-08-31
verified-against: f045a66
sources:
  - windows-converter/watch_and_convert.py
  - windows-converter/watch_and_convert_selftest.py
  - windows-converter/convert_and_ship.py
  - windows-converter/convert_and_ship_selftest.py
  - windows-converter/analyst.py
  - windows-converter/fidelity_audit.py
  - windows-widget/src-tauri/src/line.rs
  - windows-widget/src-tauri/src/watcher.rs
  - windows-widget/src/event-vocab.js
  - docs/11-gpu-pipeline-revamp.md
  - OPEN-TASKS.md
  - SYMPTOM-INDEX.md
---

# Desktop Pipeline

**The Windows GPU lane turns a PDF dropped into `drop/` into a shipped bundle on the
ThinkPad. Intake is now a durable, observable conveyor: Windows directory notifications wake
it quickly, a five-second filesystem reconciliation remains truth, one worker preserves GPU
single-flight, and `.intake-state.json` tells the Dock and Room whether each PDF is receiving,
settling, ready, deferred, or running. A positive "converting" claim requires the fresh
receipt, kernel card ownership, and `.gpu-lock` to agree. `convert_and_ship.py` then probes,
routes, runs Marker under semantic liveness monitoring, optionally runs the fenced analyst,
audits, bundles, and ships by atomic remote rename. Every converter entry still serializes on
`Local\file-portal-card`; the RTX 3080's 10 GB fits Marker or an 8B model, never both
(docs/11-gpu-pipeline-revamp.md:12; watch_and_convert.py:124-214;
windows-widget/src-tauri/src/line.rs:69-202).**


> **S108→S113 update:** the five core modules resolve pipeline paths through `fp_paths.py` +
> `roots.json`; S113 added the named `intake_state` root. The scratch-root tripwire now passes
> 23/23 roots and 26/26 owned constants under an isolated `FP_PIPELINE` (command:
> marker-env Python `windows-converter/fp_paths.py`, 2026-08-31). The SYM-050 page-map repair
> remains wired (`0fbb6e3`): IV 220/269 = 0.8178 vs naive 0.1115.

## 1. Conveyor State — `watch_and_convert.py`

`ReadDirectoryChangesW` is only a wake hint; `wake.wait(delay)` always returns to a periodic
filesystem reconciliation, so lost notifications cannot lose a PDF
(`watch_and_convert.py:243-281,588`). `IntakeTracker` is non-blocking and requires three
conditions before `ready`: same byte size, same `mtime_ns`, and one quiet second; then a
Windows `CreateFileW` probe that deliberately denies write-sharing proves no producer still
owns a write handle (`watch_and_convert.py:78-121,124-212`). The real negative control holds
a writer open through a pause longer than the quiet window and remains `receiving`
(`watch_and_convert_selftest.py:78-98`).

- **Durable order and one worker:** `_next_dispatch` admits only the filename-sorted queue
  head; a later ready file cannot bypass an earlier receiving file. `_Worker` lets intake keep
  reconciling while exactly one conversion blocks (`watch_and_convert.py:464-518`; negative
  control `watch_and_convert_selftest.py:112-126`).
- **Atomic operator receipt:** watcher-only `.intake-state.json` is dot-then-`os.replace`,
  versioned, and carries writer PID, card state, active name, waiting count, bytes, mtime,
  first-seen time and phase. Active is excluded from waiting. Restart restores the detected
  clock only when bytes+mtime still match, but re-proves readiness
  (`watch_and_convert.py:132-241,539-584`; selftest `:40-75`). Rust accepts it only while ≤300
  seconds old, from a live writer, with schema/order/count/bytes/mtime matching `drop/`; else
  it projects `UNREAD` (`windows-widget/src-tauri/src/line.rs:15,69-158`).
- **Three-signal conversion truth:** `.gpu-lock` alone is never a positive claim. Fresh
  receipt + `card_state=busy` + identical active/lock filename must agree; the stale-lock
  negative control proves matching and ghost locks cannot create activity
  (`windows-widget/src-tauri/src/line.rs:189-202,640-670`).
- **Ownership and stop truth:** the real Python interpreter owns a named watcher mutex. The
  widget reads its fresh receipt PID, kills that real process tree even if a launcher shim has
  already exited, verifies death, and renders `stop-failed` rather than lying "stopped"
  (`watch_and_convert.py:283-333`; `windows-widget/src-tauri/src/watcher.rs:95-128,182-212,268-325`).
- **Existing gates remain:** chat-hold deferral, analyst-mode routing, done/failed archive,
  and the eight-hour outer child backstop remain in `convert_one`
  (`watch_and_convert.py:378-461`).

## 2. probe() → route(): engine choice — `convert_and_ship.py`

`probe()` (`convert_and_ship.py:638`) measures chars/page via `page.get_text()` and detects an OCR overlay two ways: spans with text render mode 3 (invisible text painted over a scan; `get_texttrace` span `type == 3`) by **majority of spans** (> 0.5), plus a secondary font-name check `glyphless|invisible|ocr`. Verified live: the Beer book's 2013 Archive.org layer is 100 % type-3 "Courier"; a born-digital Chromium print is type 0 (`convert_and_ship.py:638-662`).

`route()` (`convert_and_ship.py:665`) yields exactly three rows (`MIN_CHARS_PER_PAGE = 100` at `:91`, `RECOGNITION_BATCH = 32` at `:92`):

| Condition | Extra Marker args | Lane | Reason |
|---|---|---|---|
| chars ≥ 100 AND ocr fonts | `--strip_existing_ocr --recognition_batch_size 32` | scan | `untrusted_ocr_layer` (`:668-669`) |
| chars ≥ 100 | `--recognition_batch_size 32` | clean | `text_layer_present` (`:670-676`) |
| chars < 100 | `--recognition_batch_size 32` | scan | `no_text_layer` (`:677`) |

The clean lane is capped too: uncapped, Marker auto-scales its batch to fill the card — a figure-dense born-digital book ballooned to the ~10 GB ceiling and thrashed to a 60-min DNF at 91 pp (Cybernetics models book, `:556-560`).

## 3. _run_marker(): one engine launch, semantic liveness

`_run_marker()` (`convert_and_ship.py:755`) is the only engine launch site. `MARKER` remains
the private marker-env `marker_single.exe` (`:84`); exact argv is source + output directory +
markdown format + route flags + optional page range (`:790-803`). The draining reader thread,
UTF-8 replacement decoding, and tree-kill boundary are unchanged (`:771-805,816-821`).

Progress is now a v2 receipt with writer PID and structured page range, slice, attempt, batch,
and split context (`convert_and_ship.py:143-187,932-943`). Liveness is the in-memory semantic
`(stage,n,total)` tuple: any change—including count regression or total change—refreshes it;
an identical tuple does not. Marker process completion/stall is checked every 5 seconds, while
the subprocess-based GPU sample remains every 30 seconds; 900 seconds of unchanged semantic
progress kills the tree, while the page-scaled hard cap remains `max(3600,pages×20)`
(`convert_and_ship.py:812-856`). The quarantined suite proves tuple semantics, the 5s/30s split,
and that both stdout-drain paths survive (`convert_and_ship_selftest.py:121-136,293-301`).

Dock and Room share one `event-vocab.js`; recovery states can no longer silently diverge
between surfaces (`windows-widget/src/event-vocab.js:1-45`; imports at
`windows-widget/src/main.js:15` and `windows-widget/src/room.js:10`).

## 4. The analyst pass — `analyst.py` (docs/12)

Reformats the markdown for readability without ever touching packaging: every asset embed is swapped for an opaque `⟦IMG-n⟧` token before the model sees text; a chunk that returns an altered token multiset is rejected and ships un-analyzed (`analyst.py:3-7`).

- **Backends** (`:279-289`): `local` = qwen3:8b via Ollama `http://localhost:11434/api/generate` (`:24-25`); `gemini` = `gemini-flash-latest` (`:45-46`). Chunks target 4,000 chars inside `num_ctx` 8192 (`:47-48`).
- **GEMINI_API_KEY is a header, never argv**: read from the environment (`:116-118`) and sent as `x-goog-api-key` (`:132`) — it never appears in a process command line.
- **The keep_alive tax, measured** (`:26-30`, on the S76 Beer book with this module's own program and chunker): `keep_alive 0` → mean **21.47 s/chunk** (model load 9.62 s = 44.8 %); `keep_alive 5m` → mean **11.75 s/chunk** (load 0.21 s = 1.8 %); generation 75.7 vs 76.0 tok/s — identical. Every chunk was reloading the model for nothing. Fix: `KEEP_ALIVE_HOLD = "30m"` (`:44`) held for the phase, then released by an **explicit** unload (`keep_alive: 0` POST) in `process()`'s `finally`, local backend only (`:197-205`, `:374-378`) — an act, not a timer.
- **Chunk journal + fsync resume**: each finished chunk is appended to `<work_dir>/chunks.jsonl` and `os.fsync`'d — "the whole point is surviving a power" cut (`:267-274`). The work dir key binds everything that changes output: fenced source text, backend, prompt program, chunk size (`:228-234`) — a stale journal can never leak across configs. Backend errors ship the original chunk un-analyzed and are deliberately NOT journalled (`:341-344`), so a retry re-attempts them.
- **Throughput** (chars of input markdown per second, all-in: chunking + load + generation + fence checks): local **138.0**, gemini **186.7** — sources: agent book 28,441 chars / 206.5 s (S15); Gemini S16 live test (`:53-56`).

## 5. Fidelity audit, bundle, ship

`fidelity_audit.py` measures how much of the source PDF survives into Marker's markdown and how much of that survives the analyst pass — window-survival containment against an ephemeral pymupdf witness; deterministic, CPU-only, report-only (`fidelity_audit.py:1-17`). Verdict is `pass|flag|fail`; per the signed policy (docs/15 §12) only degeneration + analyst near-exact can produce `fail`; everything else localizes as `flag` (`:33-37`). `convert_and_ship.py` wraps it crash-safe (`:39-80`) and reads the enforcement lever per bundle: `audit-mode.txt` = `report` (default: record and ship anyway) or `enforce` (`audit_mode()` at `:423-434`); under enforce a `fail` parks the bundle in `held/<sha16>/` instead of shipping (`_enforce_hold`, `:465-505`).

The bundle contract (`<name>/<name>.md + assets/ + manifest.json`) is **mirrored** from `linux-converter/converter/bundle.py` (`convert_and_ship.py:577`) — two implementations, no parity test. `ship()` (`:1347`) streams `tar -cf - | tailscale ssh rab@archlinux` into `~/file-portal/library/staging/.part-<sha16>` and then `mv`-renames it visible — atomic publish on the remote (`:1351-1362`); a dead ssh kills the wedged tar so a tar timeout never masks the real network error (`:1363-1374`).

## 6. Concurrency: one process on the card, ever

- **The card mutex**: `CARD_MUTEX_NAME = Local\file-portal-card` (`convert_and_ship.py:290`, env-overridable via `FP_CARD_MUTEX`). A named OS mutex the kernel enforces for **every** converter entry — watcher child, `--resume`, `--reanalyze`, hand runs (`:282-333`). Held for process lifetime; a dead holder surrenders it as `WAIT_ABANDONED`, safe to inherit because slice publish is atomic. This closed SYM-042's blind spot; `.gpu-lock` remains a corroborated display signal only (SYM-032).
- **Chunking + identity-gated resume**: books over 600 pages (clean) / 400 (scan) convert in 200-page slices (`should_chunk`, `convert_and_ship.py:335-345`). A finished slice's `.done` is reused only when `source_sha256`, `engine_args`, and `marker_version` match (`_done_identity_mismatch`, `:1008-1025`). `batch` remains a live performance lever, not identity. Slices publish by atomic rename (`:1136`); `chunk-batch.txt` is 8/16/32, default 16, re-read per slice (`:245-280,1091-1104`).

## 7. Measured costs (numerator / denominator / conditions)

| Figure | Conditions | Cite |
|---|---|---|
| `--force_ocr`: **27+ min, no output**, killed | GPU 100 %, peak 9,939 MiB, full-book re-OCR of 1,281 text regions (Beer book) vs 97 s default; hence the ban on this 10 GB card | docs/11:86 |
| ~1.5 s/page | born-digital, Marker default, RTX 3080 | docs/11:122-126 |
| ~4 s/page | scan lanes (`--strip_existing_ocr` batch 32; raw scan "expected"), RTX 3080 | docs/11:122-126 |
| 8.08 s/page worst ever measured | dense 439-pp scan; basis of the 20 s/page timeout scale | convert_and_ship.py:685-689 |
| ~7.9 GB VRAM peak | Beer, 439 figure-heavy pp, scan lane, batch capped 32 | convert_and_ship.py:559 |
| 91 pp → 60-min DNF | uncapped batch, figure-dense born-digital (Cybernetics models book) — why the clean lane is capped too | convert_and_ship.py:556-560 |
| 21.47 vs 11.75 s/chunk | analyst mean s/chunk, keep_alive 0 vs 5m, S76 Beer, this module's program + chunker | analyst.py:26-30 |
| 138.0 / 186.7 chars/s | analyst input-markdown chars per wall-second, all-in; local (S15) / Gemini (S16) | analyst.py:53-56 |

The GPU budget rule behind all of it: RTX 3080 **10 GB** fits Marker (~5 GB peak) OR an 8B q4 model (~5-7 GB) — never both at once (docs/11:12, :20).

## Open items

- **OPEN-TASKS.md §A**: A2 (Stage 2 GO — converter tests + CI), A4 (P-1 HOST placement, in-converter vs out-of-band), A29 (governance suites in CI — nothing runs windows-converter's selftests), A42 (the windows-converter test decision, awaiting Rab since S86).
- **OPEN-TASKS.md §B**: B4 (`windows-converter/` outside CI's lint set entirely), B19 (analyst has no llama.cpp path; any build must carry `enable_thinking:false`).
- **SYMPTOM-INDEX.md**: SYM-047 (an orphan watcher survives widget force-kill — census parents before adoption), SYM-049 (zero-area connectors invisible to figure coverage), SYM-032/-033/-042 (the mutex lineage — prevention built S94, rows still marked open).
- **docs/37 §1** Stage 2 (converter test lane) and **docs/41** (conversion-completeness slate) govern what this lane does next.
