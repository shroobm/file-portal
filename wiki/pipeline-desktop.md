---
title: Desktop Pipeline
section: Pipeline
last-verified: 2026-08-23
verified-against: 1790554
sources:
  - windows-converter/watch_and_convert.py
  - windows-converter/convert_and_ship.py
  - windows-converter/analyst.py
  - windows-converter/fidelity_audit.py
  - docs/11-gpu-pipeline-revamp.md
  - OPEN-TASKS.md
  - SYMPTOM-INDEX.md
---

# Desktop Pipeline

**The Windows GPU conversion lane turns a PDF dropped into `drop/` into a shipped bundle on the ThinkPad: a 5-second polling watcher (`watch_and_convert.py`) runs one conversion at a time; `convert_and_ship.py` probes the PDF's text layer, routes it to one of three Marker lanes, launches `marker_single.exe` (the repo's ONLY engine launch site) under a stall monitor, optionally runs the link-fenced analyst (`analyst.py`, local qwen3:8b or Gemini Flash), audits fidelity, assembles the bundle, and ships it `tar | tailscale ssh` into an atomically-renamed staging dir. Concurrency is kernel-enforced: every converter entry serializes on the OS mutex `Local\file-portal-card`, because the GPU is an RTX 3080 with 10 GB — Marker (~5 GB peak) or an 8B model fit alone, "never both at once" (docs/11:12).**

## 1. The watcher loop — `watch_and_convert.py`

One `while True` at `watch_and_convert.py:193` sleeps `POLL_S = 5` seconds per pass (`:44`, `:205`) and walks `sorted(DROP_DIR.iterdir())`, skipping dotfiles and non-`.pdf` (`:195-198`, `PATTERNS = {".pdf"}` at `:43`). Strictly sequential by design: "one conversion at a time (sequential loop = the Marker/Ollama single-flight guarantee on this GPU)" (`:11-12`), and `convert_one` runs the child with a **blocking** `subprocess.run(..., timeout=21600)` (`:165-166`) — the outer backstop deliberately sits above the inner page-scaled cap so it never becomes the real limit (`:161-164`).

- **Stability wait**: `stable_size()` (`:58`) blocks up to `timeout=120.0` s, returning True once the file size holds across one 1-s interval — a mid-transfer file is never touched.
- **Chat-hold deferral gate**: `convert_one` refuses to start while the Room assistant holds the card via `chat-hold.json` (`:141-149`); a stale hold from a dead pid is reaped mechanically (`:113-139`). Signed docs/33 §2.3.
- **Analyst mode**: `analyst-mode.txt` reads `off | local | gemini | ask` (`:37`); `ask` adds `--defer-analyst`, any live mode adds `--analyst --backend <mode>` to the child argv (`:151-156`).
- **Outcome**: exit 0 moves the PDF to `drop/done/`, anything else to `drop/failed/` with the error logged (`:169-179`).

## 2. probe() → route(): engine choice — `convert_and_ship.py`

`probe()` (`convert_and_ship.py:523`) measures chars/page via `page.get_text()` and detects an OCR overlay two ways: spans with text render mode 3 (invisible text painted over a scan; `get_texttrace` span `type == 3`) by **majority of spans** (> 0.5, `:546`), plus a secondary font-name check `glyphless|invisible|ocr` (`:520`, `:544-545`). Verified live: the Beer book's 2013 Archive.org layer is 100 % type-3 "Courier"; a born-digital Chromium print is type 0 (`:526-528`).

`route()` (`:550`) yields exactly three rows (`MIN_CHARS_PER_PAGE = 100` at `:89`, `RECOGNITION_BATCH = 32` at `:90`):

| Condition | Extra Marker args | Lane | Reason |
|---|---|---|---|
| chars ≥ 100 AND ocr fonts | `--strip_existing_ocr --recognition_batch_size 32` | scan | `untrusted_ocr_layer` (`:553-554`) |
| chars ≥ 100 | `--recognition_batch_size 32` | clean | `text_layer_present` (`:561`) |
| chars < 100 | `--recognition_batch_size 32` | scan | `no_text_layer` (`:562`) |

The clean lane is capped too: uncapped, Marker auto-scales its batch to fill the card — a figure-dense born-digital book ballooned to the ~10 GB ceiling and thrashed to a 60-min DNF at 91 pp (Cybernetics models book, `:556-560`).

## 3. _run_marker(): the one engine launch site

`_run_marker()` (`:636`) is the **only** place the repo launches the engine — `grep -rn marker_single --include="*.py" --include="*.rs" --include="*.js"` (excluding `src-tauri/target/`, `node_modules/`) hits exactly one line, `convert_and_ship.py:82`, and `grep -c "str(MARKER)" convert_and_ship.py` = 1 (`:672`). `MARKER = C:\Users\Bndit\ml\marker-env\Scripts\marker_single.exe` (`:82`) — a private venv **outside the repo** (no pyproject/requirements exists in `windows-converter/`; the interpreter path is named in `.claude/launch.json` and `watch_and_convert.py:15-16`, never pinned by a repo manifest). Marker runs surya's OCR/layout models internally (`:678` "surya's tqdm block glyphs"; docs/11:90 "let surya re-read").

Exact argv (`:672-674`): `marker_single.exe <src> --output_dir <out_root> --output_format markdown` + route()'s extra flags + `--page_range <range>` for chunked slices only.

Hard-won wrappers, all shared by whole-book and slice paths (`:641-645`): a draining reader thread (S48's 64 KB pipe deadlock — pipe decoded `utf-8, errors="replace"` because surya's tqdm bytes kill a cp1252 strict decode, `:675-679`), tree-kill of the child's real python, the stall signature (progress frozen `STALL_FROZEN_S = 900` s while Marker still runs → kill early, `:92-95`), and a page-scaled outer timeout `max(3600, pages × 20)` s (`:690`) — 20 s/page is ~2.5× the worst rate ever measured here (8.08 s/page on a dense 439-pp scan, `:685-689`).

## 4. The analyst pass — `analyst.py` (docs/12)

Reformats the markdown for readability without ever touching packaging: every asset embed is swapped for an opaque `⟦IMG-n⟧` token before the model sees text; a chunk that returns an altered token multiset is rejected and ships un-analyzed (`analyst.py:3-7`).

- **Backends** (`:279-289`): `local` = qwen3:8b via Ollama `http://localhost:11434/api/generate` (`:24-25`); `gemini` = `gemini-flash-latest` (`:45-46`). Chunks target 4,000 chars inside `num_ctx` 8192 (`:47-48`).
- **GEMINI_API_KEY is a header, never argv**: read from the environment (`:116-118`) and sent as `x-goog-api-key` (`:132`) — it never appears in a process command line.
- **The keep_alive tax, measured** (`:26-30`, on the S76 Beer book with this module's own program and chunker): `keep_alive 0` → mean **21.47 s/chunk** (model load 9.62 s = 44.8 %); `keep_alive 5m` → mean **11.75 s/chunk** (load 0.21 s = 1.8 %); generation 75.7 vs 76.0 tok/s — identical. Every chunk was reloading the model for nothing. Fix: `KEEP_ALIVE_HOLD = "30m"` (`:44`) held for the phase, then released by an **explicit** unload (`keep_alive: 0` POST) in `process()`'s `finally`, local backend only (`:197-205`, `:374-378`) — an act, not a timer.
- **Chunk journal + fsync resume**: each finished chunk is appended to `<work_dir>/chunks.jsonl` and `os.fsync`'d — "the whole point is surviving a power" cut (`:267-274`). The work dir key binds everything that changes output: fenced source text, backend, prompt program, chunk size (`:228-234`) — a stale journal can never leak across configs. Backend errors ship the original chunk un-analyzed and are deliberately NOT journalled (`:341-344`), so a retry re-attempts them.
- **Throughput** (chars of input markdown per second, all-in: chunking + load + generation + fence checks): local **138.0**, gemini **186.7** — sources: agent book 28,441 chars / 206.5 s (S15); Gemini S16 live test (`:53-56`).

## 5. Fidelity audit, bundle, ship

`fidelity_audit.py` measures how much of the source PDF survives into Marker's markdown and how much of that survives the analyst pass — window-survival containment against an ephemeral pymupdf witness; deterministic, CPU-only, report-only (`fidelity_audit.py:1-17`). Verdict is `pass|flag|fail`; per the signed policy (docs/15 §12) only degeneration + analyst near-exact can produce `fail`; everything else localizes as `flag` (`:33-37`). `convert_and_ship.py` wraps it crash-safe (`:37-68`) and reads the enforcement lever per bundle: `audit-mode.txt` = `report` (default: record and ship anyway) or `enforce` (`audit_mode()` at `:308-314`); under enforce a `fail` parks the bundle in `held/<sha16>/` instead of shipping (`_enforce_hold`, `:350-354`).

The bundle contract (`<name>/<name>.md + assets/ + manifest.json`) is **mirrored** from `linux-converter/converter/bundle.py` (`convert_and_ship.py:462`) — two implementations, no parity test. `ship()` (`:1037`) streams `tar -cf - | tailscale ssh rab@archlinux` into `~/file-portal/library/staging/.part-<sha16>` and then `mv`-renames it visible — atomic publish on the remote (`:1040-1043`); a dead ssh kills the wedged tar so a tar timeout never masks the real network error (`:1053-1058`).

## 6. Concurrency: one process on the card, ever

- **The card mutex**: `CARD_MUTEX_NAME = Local\file-portal-card` (`convert_and_ship.py:203`, env-overridable via `FP_CARD_MUTEX`). A named OS mutex the kernel enforces for **every** converter entry — watcher child, `--resume`, `--reanalyze`, hand runs (`:197-202`). Held for process lifetime; a dead holder surrenders it as `WAIT_ABANDONED`, safe to inherit because slice publish is atomic. This closed SYM-042's blind spot (file signals can't cover a path that doesn't write them); `.gpu-lock` remains a display signal only (SYM-032). History and diagnosis probes: SYMPTOM-INDEX.md rows SYM-032, SYM-033, SYM-042.
- **Chunking + identity-gated resume**: books over 600 pages (clean) / 400 (scan) convert in 200-page slices (`:170`, `:173`; Damodaran at 1,356 pp = 7 slices, `:172`). A finished slice's `.done` is reused only when its identity matches: `source_sha256`, `engine_args`, `marker_version` (`_done_identity_mismatch`, `:752-763`) — presence alone was F-02's bug. `batch` is deliberately NOT identity: it's a VRAM/speed knob, and gating on it would invalidate good slices at every mid-book lever change (`:756-760`). Slices publish by `staging.rename(slice_dir)` — `.done` exists only on a complete slice (`:862`). The slice batch is a user lever: `chunk-batch.txt` ∈ {8, 16, 32}, default 16, re-read per slice (`:174-179`).

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
