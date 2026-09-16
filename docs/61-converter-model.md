# 61 — The converter, modeled: one model of the chain, a universal terminology for its slots, and how the conclusion differs by the tenant of each

*Born whole in S158 (2026-09-15, Fable lane, Claude Opus 5), on Rab's commission (Desk 26ab29a4): "research the converter, everything about it then modeled and then given its universal terminology so any of its kind can be placed and its conclusion differs amongst each variation within that chain. Marker becomes VLLM Model, so on." Append-only after its birth. Built from a five-lane read of the ground (`sessions/S158` §6: the code, the audit and Linux code, the docs, the record's numbers, the engines on disk — every plant caught, 42/44 adjudicated) and the lane's own sweep of the field (§7: eighteen sources, quoted). Tags per `docs/21`: **Observed** = read this sitting with the command named; **Historical** = the record's or the source's own number on its own date; **Inferred** = reasoned, with what would falsify it; **UNREAD** = no probe ran. Every number names its numerator, denominator and conditions (`docs/34`) or is not stated.*

## §0 Reading map

- **§1** the chain as built, one table: the project's word · the universal slot name · the tenant on each lane.
- **§2** the model: every slot with its inputs, outputs, invariants, levers, failure classes (with their LEVEL) and engine binding.
- **§3** the universal terminology: the slot names no engine owns, the kinds that can occupy each, and the words this project already uses ambiguously.
- **§4** the variation table: per slot, the variants on this machine · in the record · in the field, and how the conclusion differs — measured with conditions where the shelf carries it, UNREAD where it does not.
- **§5** the failure classes by level (kind · instance · version · chain).
- **§6** the chooser, as a frame of questions, never a decision (the decisions are Rab's).
- **§7** what this document cannot see.

One sentence first. **The converter is a chain of thirteen slots; the engine is one of them; Marker is one tenant of that one slot, of the kind the field calls a *pipeline tool*; the phrase "VLLM Model" names two other things at once — a *kind* (an end-to-end vision-language model, which Marker 1.10 is not and Chandra 2 on this disk is) and a *serving* (vLLM, which the field's newest engines use and no environment on this machine holds) — and the rest of the chain (the probe, the audit, the repairs, the analyst, the acceptor, the gate, the transport, the vault gate) stays the same whichever tenant sits in the engine's slot, which is what makes a terminology possible.**

## §1 The chain as built (Observed, S158 E1; the order is `convert_and_ship.py`'s and `linux-converter/converter/main.py`'s)

| # | the project's word | the universal slot | tenant, GPU lane (Windows, `marker-env`) | tenant, Linux lane (ThinkPad) |
|---|---|---|---|---|
| 0 | the watcher · the allocator | **intake queue** | `watch_and_convert.py` (polls `drop/`, one worker, filename order, the card mutex) | `linux-receiver/allocator/main.py` (rules.toml router) → `convert-inbox` / `convert-scan-inbox` |
| 1 | the probe | **routing probe** | `pymupdf` chars/page + page count → lane clean/scan → Marker's OCR mode | `engines.probe_chars_per_page` → lane; Scan is terminal |
| 2 | the engine · Marker | **page-to-structure engine** (the slot the commission names) | Marker 1.10.2 = pdftext text layer + surya 0.17.1 (five specialist models) → markdown + assets (+ blocks via `marker_blocks.py`) | `pymupdf4llm` 1.28.0 + `pymupdf-layout` (a GNN over PDF internals) + Tesseract fallback; Pandoc for `.docx` |
| 3 | the blocks · J24 | **geometry sidecar** | `marker_blocks.py`: per-block polygons/bboxes, the page re-derived from the block id | none |
| 4 | the audit (convert stage) · the witness | **witness comparison** | `fidelity_audit.audit_convert`: doc_survival, degeneration, latex_balance, coverage floor; figure coverage (P-1, unwired) | `degeneration.py` only (a port without the table-row blanking); no fidelity block written |
| 5 | the table layer · the geometry pass | **structural repair pass** (invariant-gated) | `table_geometry.geometry_pass` (split · trim · leak · rails · index guard · dots), called from the analyst when `ANALYST_TABLES` | none |
| 6 | the vision route · the reading | **second-reader sidecar** | `vision.json` from a sub-agent panel, consumed by the table layer (S156) | none |
| 7 | the analyst | **LLM rewrite pass** | `analyst.py`: the fence, ~4,000-char chunks, per-chunk gates, the resume journal; `qwen3:8b` via Ollama or Gemini Flash | none |
| 8 | the acceptor · J46 | **edit whitelist** (faithfulness by construction) | `edit_whitelist.reconcile`: FULL = escape · link · markup · hyphen · ligature · reflow; punctuation/case reverted | none |
| 9 | the audit (analyst stage) | **near-exact containment** | `fidelity_audit.audit_analyst` against the retained Marker body (J33 sidecar) | none |
| 10 | the verdict · the gate · audit_mode | **verdict gate** | `compute_verdict` pass/flag/fail; `audit-mode.txt` report/enforce; `pending/`, `held/` | verdict absent (no fidelity block); degeneration report-only |
| 11 | ship | **transport** | tar/SSH over Tailscale to the ThinkPad's staging | `bundle.publish` (atomic rename) to anchor + staging |
| 12 | the exporter · L11/L12 | **vault gate** | — (the ThinkPad's) | `exporter.py`: dedup on source sha, supersede opt-in, bless, the L12 blob check; `fail` refused, `flag` ships, missing ingests |
| 13 | fixity | **preservation check** | — | `fixity.py`: weekly `git fsck --strict --no-dangling` |

Cross-cutting: `events.py` (**telemetry**, best-effort), `fp_paths.py`/`roots.json` (**the path registry**, SYM-010's countermeasure), the card and its two signals (`.gpu-lock` a signal, the kernel mutex the lock — SYM-032/033), the lever files (`analyst-mode.txt`, `audit-mode.txt`, `chunk-batch.txt`, `figure-triage.txt`).

## §2 The model — each slot with what it takes, gives, refuses, tunes, and breaks on

The fields are the same for every slot so a tenant can be swapped by re-filling them. *Level* of a failure class: **K** = the kind's (any engine of that kind), **I** = the instance's (this engine), **V** = the version's (this build), **C** = the chain's (ours, not the engine's).

### 2.0 Intake queue
- **takes** a file arriving in a watched directory; **gives** the file to the probe in filename order, one at a time; a moved source to `done/` or `failed/`.
- **invariants** one worker; a single watcher (kernel mutex `Local\FilePortalWatcher`, exit 3 if held); a file is dispatched only when size+mtime hold for `QUIET_S` and it opens without write sharing; a later-arriving ready file never bypasses an earlier one still settling; a failure is an event and a log line, never a bare traceback (S141).
- **levers** `POLL_S = 5`, `QUIET_S = 1.0`, `TIMEOUT_S = 28,800` (OK-17: 6 h + the Damodaran's worst ladder spend), `PATTERNS = {.pdf}`.
- **failure classes** C: a pre-empted dispatch losing the event stream (S141); the POSIX `os.kill(pid, 0)` idiom as a murder weapon on Windows; a stale lock reaped only when the mutex disagrees (SYM-032).
- **engine binding** none in logic; the interpreter is marker-env's and the docstring names Marker's VRAM.

### 2.1 Routing probe
- **takes** the PDF; **gives** `pages_total` (never from metadata, "which lies"), chars/page, the lane (`clean` ≥ `MIN_CHARS_PER_PAGE = 100` else `scan`), and the engine's OCR mode.
- **invariants** the probe is CPU-only and never the engine; an unreadable file quarantines rather than converts (Linux).
- **levers** `MIN_CHARS_PER_PAGE = 100` ("provisional"); Linux `settings.min_chars_per_page`, `ocr_dpi`, `ocr_language`.
- **failure classes** K: a page with a *garbled* text layer reads as clean (the text exists, the words do not) — the reason the field's engines carry an OCR-error detector (Marker's `ocr_error_detection` model) and the reason `--strip_existing_ocr` exists; I: pymupdf4llm's `force_ocr=True` KEEPS the old layer (SYM-012; the honest spelling is `OCRMode.FORCE_DROP_OLD`).
- **engine binding** the mode names are the tenant's (`--strip_existing_ocr` vs `OCRMode.*`).

### 2.2 Page-to-structure engine — the slot
- **takes** a PDF (or a page image); **gives** structured text (markdown / HTML / JSON), assets (figures as files), and — depending on the kind — block geometry (polygons/bboxes), a layout label per block, table structure, formulas as LaTeX, a reading order.
- **inside a pipeline tool** (Marker 1.10.2, Observed from `converters/pdf.py` and the five model dirs in the datalab cache): (a) **text-layer extraction** — pdftext over pypdfium2, per line, `text_extraction_method = 'pdftext'` when usable; (b) **layout analysis** — surya `layout` (a vision model over the rendered page; in 0.17.1 also the reading-order source); (c) **text detection** — surya `text_detection`; (d) **text recognition** — surya `text_recognition` on a shared FoundationPredictor, the fallback when (a) is unusable (`'surya'`); (e) **table structure recognition** — surya `table_recognition`; (f) **formula recognition** — `processors/equation.py` runs the same recognition model over equation blocks (Observed: it imports `surya.recognition.RecognitionPredictor`; no texify package on this disk; Marker: "Equations and inline math are recognized by the VLM"); (g) **OCR-error detection** — surya `ocr_error_detection`, the classifier that decides when full-page OCR is necessary; (h) **the in-engine LLM pass** — `--use_llm` with Gemini/Vertex/Ollama/Claude/OpenAI/Azure/OpenRouter (unused here; our analyst is outside); (i) **rendering** — builders → ~23 processors → renderers (markdown · html · json · chunk · ocr_json).
- **inside an expert VLM** (Chandra 2 on this disk, unwired; dots.ocr; DeepSeek-OCR; MinerU2.5): (b)–(g) collapse into one forward pass, image in → markup out; the variation axis becomes *vision tokens per page* (DeepSeek: 64–400; "< 10× compression → 97 % precision, 20× → ~60 %") and the failure class becomes the decoder's (§5).
- **inside a text-layer extractor with a structure-side layout model** (pymupdf4llm + pymupdf-layout, the Linux lane): (a) the text layer; (b′) layout by a GNN over the PDF's internals (ONNX, CPU); (d′) Tesseract only when a page has no text; no (e)–(g).
- **invariants (the slot's, whatever the tenant)** the output's image embeds are the tenant's naming convention and nothing downstream may re-target them (the link fence); the tenant's page numbering may be wrong and the chain re-derives it (2.3); the tenant never gates a conversion — an engine failure is a timeout, a stall, or an exit code, and the chain's ladder answers it.
- **levers (Marker's, as bound here)** `RECOGNITION_BATCH = 32` (the shipped `--recognition_batch_size`); `CHUNK_THRESHOLD_PAGES = {clean: 600, scan: 400}`, `SLICE_PAGES = 200`, `CHUNK_BATCH_ALLOWED = (8, 16, 32)`, default 16; the stall ladder `STALL_FROZEN_S = 900`, `STALL_RETRY_SPLIT_MIN_PAGES = 50`, `STALL_RETRY_MAX_SPLITS = 2` (≤ 9 invocations per slice), `STALL_RECOVERY_BATCH = 4`; `CEILING_FRACTION = 0.80`; Marker's layout pixel ceiling 1,048,576 px (docs/41, not RF-DETR's 6.29 MP); `lowres_image_dpi` headroom −9 % … +228 % (docs/41, geometry-determined).
- **failure classes** K: the autoregressive repetition loop (Nougat: "the model degenerates into repeating the same sentence over and over again. The model can not recover from this state by itself"; ours: docs/15 §9, Brain of the Firm zlib 0.003, trigram ×2,267); K: the scan column (olmOCR-bench "Old Scans": Marker 1.10 32.3, Chandra 2 51.1 — every kind is worst here); I: table fusion of stacked tables and trailing-column padding (S157 E1/E3: "Marker's fusion of stacked tables", "Marker's padding, not the page's"); I: asset names `_page_N_(Figure|Picture)_M` as the only figure identity; V: `FlatBlockOutput.page` is a per-page creation counter, not a page (measured 2026-09-01: true pages 0,1,2,3 → 8, 8, 10, 26); C: the doubled asset offset of pre-S60 chunked bundles (SYM-050); C: the card's ceiling reached by the sidecar alone (SYM-132: 8,321–8,327 MB committed through recognition, Beer).
- **engine binding** total on the GPU lane: `MARKER = marker-env\Scripts\marker_single.exe`, the CLI flags (`--output_dir`, `--output_format markdown`, `--page_range`, `--strip_existing_ocr`, `--recognition_batch_size`), the version probe (`marker-pdf 1.10.2` for the `.done` identity gate, SYM-044), and `marker_blocks.py` in full.

### 2.3 Geometry sidecar
- **takes** the engine's in-memory Document (Marker's, re-rendered once as chunks); **gives** `<stem>.blocks.json`: id, block_type, html, page (corrected), page_field_raw, polygon, bbox, section hierarchy, image refs, timing.
- **invariants** the markdown is written and complete BEFORE any block work; "a book can lose its blocks; a book must never fail because of them"; the page is re-derived from the block id and NEVER guessed (None over a wrong page); merging is plain concatenation because every page is absolute.
- **levers** `BLOCKS_SCHEMA = 1` (a version, not a threshold).
- **failure classes** V: the page-field counter (above); C: a stale prior attempt's file adopted (guarded: dest cleared first).
- **engine binding** total (imports `marker.*`); a tenant without an in-memory document to re-render has no sidecar — the slot is then UNREAD, and figure coverage falls back to page-level.

### 2.4 Witness comparison (convert stage)
- **takes** the PDF and the engine's markdown; **gives** `fidelity.convert`: `doc_survival` = Σ(page score × windows) / Σ windows over SCORED pages (12-word windows, fuzzy ≥ 90 up to `FUZZY_ANCHOR_CAP`; blank and image pages excluded); `pages_scored / pages_total`; `runs` (capped at 25 for wire compatibility, `runs_total` beside it — SYM-066); tripwires `degeneration` (zlib ratio < 0.20 OR max trigram ≥ 40 on ≥ 200-char paragraphs, table rows blanked first — SYM-067), `page_coverage`, `asset_delta`, `embedded_images`, `reverse_sample` (200 output windows found in the witness), `dict_hit`, `garbage_rate` (scan: no-vowel alpha tokens ≥ 4 chars / all such tokens); `latex_balance` (unterminated / begins, report-only).
- **the witness itself** is a tenant of a sub-slot: pymupdf's text layer (clean lane), the embedded OCR layer (scan lane), or a *gauge* (Tesseract, S144 E3: pairs 0.930 over 442 pages, control 0.252) — a scan with no OCR layer has NO witness and the floor (`WITNESS_COVERAGE_FLOOR = 0.50`, Rab's word S144 E2) caps the verdict at flag: Valentine's fresh anchor scores 1 of 465 pages (docs/60 §2.2).
- **invariants** report-only except two gates: only `degeneration` and analyst near-exact loss may FAIL (docs/15 §12, signed 2026-07-20); an unmeasurable result never looks clean (SYM-057; `None` never `0.0`); the numbers carry their denominators (docs/34).
- **levers** `CLEAN_PAGE_FLAG 0.85 · CLEAN_DOC_FLAG 0.97 · CLEAN_RUN_WORDS 50 · SCAN_PAGE_FLAG 0.70 · SCAN_GARBAGE_FLAG 0.20 · DEGEN_ZLIB_MAX 0.20 · DEGEN_TRIGRAM_MAX 40 · DEGEN_BLOCK_MIN_CHARS 200 · DEGEN_LINE_REPEAT 20 · WITNESS_COVERAGE_FLOOR 0.50 · REVERSE_SAMPLE_N 200 · REVERSE_SEED 20260720`.
- **failure classes** C: the instrument manufactures the finding (docs/58 S15 — the ladder stripping an escape before unescaping, SYM-076; empty table cells driving the trigram, SYM-067); C: the 25-run cap hiding 634 (SYM-066); C: perfect fidelity reported on an unmeasurable book (SYM-057, latent).
- **engine binding** none by name; the thresholds are calibrated on Marker's failure shapes (docs/15's corpus) — a different tenant's degeneration signature is UNREAD.

### 2.5 Structural repair pass (the table layer)
- **takes** the markdown (and optionally a resolver, the book's lexicon, the vision sidecar); **gives** the markdown with tables repaired and a record (tables, proposals, applied, refused, splits/trims/leaks with their refusals, unresolved rails, invariant checks).
- **invariants** pure functions, no I/O, no model; "nothing here changes a byte" unless an invariant admits it — `grid_invariant` (one table before and after; same columns; same rows but a title lifted to a caption; every cell outside column 1 byte-identical or a stray bullet normalised; column 1 changed only where a run of letter cells became one label fitting the letters), `split_invariant`, `leak_invariant`, `trim_invariant`.
- **levers** `TITLE_MIN = 20`, `SEGMENT_MIN_SCORE = 1.25` and `GAP_COST = 1.0` (Rab's word, S151 E1, Valentine's three rotated rails), `TRIM_MIN_COLS = 2` (S157 E3), `ANALYST_TABLES = True` (S154, "all signed").
- **failure classes** I: the repairs are calibrated to Marker's fusion/padding/leak; C: the index guard (a matrix's single-glyph row labels rewritten into a word, SYM-133, fixed S157 E15).
- **engine binding** none in code; the levers are Marker-calibrated — a new tenant needs its own shelf probe before the passes are trusted.

### 2.6 Second-reader sidecar (the vision route)
- **takes** rendered pages read by a panel (three readers, unanimity per page); **gives** `vision.json` (words lent, spans, rails, figures left alone); consumed by 2.5.
- **invariants** a disputed page is left out, never averaged; every claim passes the invariant; the sidecar travels with the book.
- **failure classes** C: the sidecar lost on the deferred-analyst path (caught by the S156 verifier fleet's plant).
- **engine binding** none.

### 2.7 LLM rewrite pass (the analyst)
- **takes** the markdown after 2.5; **gives** rewritten chunks that passed every gate, plus meta (chunks passed/rejected/failed by reason, edits by class, goodput, sampler, backend failures).
- **the pass** the fence (every `![[..]]` / `![](..)` → `⟦IMG-n⟧`, restored verbatim; a candidate whose token multiset differs is rejected whole) → ~4,000-char chunks on paragraph boundaries → per chunk: truncated (`done_reason == length`) → think-leak → fence → `chunk_survival ≥ 0.80` → `word_ratio ≤ 1.5` → the acceptor (2.8) → the resume journal (fsynced, keyed by sha256 of fenced text + backend + program + chunk target).
- **backends** local: `qwen3:8b` via Ollama `/api/generate` (`think: false`, `num_ctx 8192`, `keep_alive 30m`, unloaded in `finally`); cloud: `gemini-flash-latest` (≥ 13 s between calls, 3 retries on 429/500/503, an 18-chunk free-tier window). The in-engine alternative (Marker's `--use_llm`) is the same slot inside the engine, unused here.
- **invariants** the link fence is non-negotiable; a chunk is accepted or its input is kept, never a splice of a different text; the model is unloaded whatever happens.
- **levers** `CHUNK_TARGET 4000 · NUM_CTX 8192 · ANALYST_CHUNK_SURVIVAL_MIN 0.80 (0.50 → 0.80, 2026-09-09) · ANALYST_CHUNK_INFLATION_MAX 1.5 (J34) · ANALYST_NUM_PREDICT_FACTOR 2.0 / MIN 512 (SYM-129) · ANALYST_SAMPLER withheld (J49, Rab's) · programs readability / grid-word`.
- **failure classes** K: the runaway (chunk 296: 681 in → 5,170 out, 7.59×; SYM-129) and the verbatim duplicate (SYM-090); I: qwen3's `/think` `//no_think` leaks (SYM-115) and `</think>` (SYM-074); C: whole sections dropped pre-acceptor (S157 E28: the University Edition's 349/277 missing lines, 1.29 %/1.02 %, each a 300–600-word section); C: the stalled call (SYM-034/056).
- **engine binding** to the MODEL, never to the converter (the embed syntax is the only coupling).

### 2.8 Edit whitelist (the acceptor)
- **takes** input chunk and candidate; **gives** the reconciled chunk and an edit log by class (accepted / reverted).
- **the classes** accepted by construction under FULL: quotes/NFKC (always), escape, link (re-syntax only; the ORDERED URL sequence and bracket balance never change), markup, hyphen joins, ligature garbles (ffi/ffl/ff/fi/fl/ft/fk/fj/fb/fh/st/Th/th, replacement required), reflow; always reverted: substitution, deletion, insertion, numeral change (digit-for-digit), punctuation-only, case (Rab's slot). Tables under FULL_TABLES judged whole by `grid_invariant`.
- **failure classes** C: a contraction's apostrophe as a ligature candidate (`wasn't → wasnfft`, fixed S140); C: two links swapping targets under a multiset (fixed: ordered).
- **engine binding** none in code; the ligature and hyphen classes are Marker's OCR artifacts and qwen3's habits.

### 2.9 Near-exact containment (analyst stage)
- **takes** the retained Marker body (the J33 sidecar, sha-verified) and the analyst's output; **gives** `fidelity.analyst`: `doc_survival` = passed windows of the masked reference / total reference windows (near-exact, no fuzzy), `runs`, the normalisation ladder's rung.
- **the ladder** v2 as shipped 0.9718/49 → v3 escape-first 0.9756/46 → v3b + ligature-blind 0.9808/33 → v3c + cite-anchor collapse 0.9897/20 (held DDIA; re-measured S157 E50 to the digit; v3b counterfactual until gated).
- **invariants** the reference is the pre-analyst text, not the held text (SYM-073's "two texts, named"); FAIL at doc < 0.995 or any run ≥ 25 words.
- **failure classes** C: the ladder manufacturing loss (SYM-076); C: the same bundle scoring differently on re-audit (SYM-073, fixed by J33).

### 2.10 Verdict gate
- **takes** the fidelity block; **gives** pass / flag / fail and the bundle's place: anchor + ship, `pending/` (deferred analyst), `held/` (enforce mode).
- **invariants** only degeneration and analyst near-exact loss may fail; `enforce` is the only sanctioned writer of the mode's reading path (SYM-131); an audit failure never fails a conversion (docs/15 §8).
- **the one lever that is a policy** `audit-mode.txt` report | enforce — D1 (`ship-with-losses-named` vs `audit-must-be-green`) is Rab's and moves the north star.

### 2.11 Transport
- **takes** the bundle; **gives** the same bytes at the ThinkPad's staging (the `.part-` invariant, W1); Linux: `bundle.publish` by atomic rename to anchor + staging.
- **failure classes** C: names past MAX_PATH 260 on the vault-consuming end (L15: `clamp_name` 80 bytes, worst case 160 vault-relative).

### 2.12 Vault gate (the exporter)
- **takes** a published bundle; **gives** a commit in the bare vault (`Inbox/<slug>--<sha8>/`) and a receipt (exported · exported-supersede · skip · supersede-held · ingest-held · bless-invalid · blessed · failed).
- **invariants** dedup on the full source sha; create-only except an explicit supersede; supersede fail-closed (`pass`, or `flag` with a valid sha-bound `bless.json`); a first ingest refuses `fail` (S146 E6, Ashby's lesson), ships `flag` (D1's current reading), ingests a MISSING fidelity block; the L12 gate: staging removed only after push AND `git cat-file -e` on the commit and every blob.
- **levers** `SHIP_BLOCKS_TO_VAULT = False` (J28, Rab 2026-09-03), `SHIP_MARKER_BODY_TO_VAULT = False` (J33, 2026-09-05), `SPOT_CHECK_EVERY = 10`.
- **failure classes** C: a degeneration-failing book reaching the vault by a first ingest that never read the verdict (SYM-130); C: create and supersede disagreeing on what they ship (J28/J33).
- **the divergence** the Linux lane writes no fidelity block, so this gate sees a verdict only on Windows-converted bundles (S158 E1, L2; Inferred that a Linux-converted book always enters as "missing"; falsified by a Linux manifest carrying `fidelity`).

### 2.13 Preservation check
- weekly `git fsck --strict --no-dangling` over the bare vault; report-only ("repair of a corrupt vault is archaeology with Rab, never automation"); NDSA level 3, PREMIS "fixity check".

## §3 The universal terminology

### 3.1 The slot names (no engine owns one)

| universal slot | takes → gives | kinds that can occupy it | the invariant that survives any tenant |
|---|---|---|---|
| **intake queue** | files → one file at a time | a directory watcher; a message queue; a hand | one worker; order is the law; a failure is an event |
| **routing probe** | a file → lane + mode | a text-layer count; an OCR-error classifier; a page classifier | CPU-only; never the engine; unreadable → quarantine |
| **page-to-structure engine** | pages → structured text + assets (+ geometry) | **pipeline tool** (layout detector + OCR + table/formula models + reading order: Marker, MinerU-pipeline, docling, Unstructured, PP-StructureV3) · **expert VLM** (one end-to-end model: Chandra, dots.ocr, DeepSeek-OCR, MinerU2.5, PaddleOCR-VL, GOT-OCR2.0, Nougat, granite-docling) · **general VLM** (Gemini, Qwen3-VL, GPT, olmOCR's base) · **text-layer extractor**, bare (pdftext, pypdfium2, pdfminer) or with a **structure-side layout model** (pymupdf4llm + pymupdf-layout's GNN) · a **declared-structure reader** (a tagged PDF's logical structure tree, docs/52 — proposed, not built) | the link fence; page numbers re-derived, never trusted; the engine never gates |
| — its **serving** (an independent axis) | a model → tokens | in-process torch (Marker's CLI here) · **vLLM** (the field's recommended server for surya-current, Chandra, olmOCR, dots.ocr, DeepSeek-OCR; absent on this machine) · **llama.cpp** (binaries present; a shelved candidate) · **Ollama** (serves the analyst; runs llama-server inside) · a **hosted API** (Gemini; Datalab's; Mistral's) | one model process on the card; a probe reads `.gpu-lock`, never takes it |
| **geometry sidecar** | the engine's document → blocks with bboxes | Marker's chunk render; a VLM's layout prompt (dots.ocr `prompt_layout_only`); a JSON renderer | markdown first; blocks may be lost, never fatal |
| **witness comparison** | source + output → survival, degeneration, coverage | a text-layer witness; an OCR-layer witness; a gauge (Tesseract); a second engine; a human reading | report-only except the two gates; an unmeasurable number is `None` |
| **structural repair pass** | markdown → markdown + record | table geometry; a heading folder; a link fixer | invariant-gated: nothing changes a byte unless admitted |
| **second-reader sidecar** | rendered pages → a reading | a sub-agent panel; a VLM; a human at the bench | unanimity per page; the reading travels with the book |
| **LLM rewrite pass** | text → text | a local model (qwen3:8b) · a hosted model (Gemini Flash) · the engine's own `--use_llm` | the fence; accept-or-keep, never splice |
| **edit whitelist** | input + candidate → reconciled + log | a class list (FULL / STRICT / FULL_TABLES) | link structure never changes; reverted classes are Rab's |
| **near-exact containment** | reference + output → survival | window containment on the pre-analyst text | the reference is the retained body, not the held text |
| **verdict gate** | fidelity → pass/flag/fail + place | report / enforce | only two signals may fail; the policy lever is his |
| **transport** | bytes → the same bytes elsewhere | tar over SSH; atomic rename | `.part-` then rename; names ≤ 80 bytes |
| **vault gate** | a bundle → a commit or a held receipt | dedup + supersede + bless + blob check | fail refused; missing ingests; delete only after the blob check |
| **preservation check** | the vault → a receipt | `git fsck`; a checksum sweep | report-only |

### 3.2 The kinds, defined by what happens between the page and the text

- **pipeline tool** — a chain of specialist models, each answering one sub-task the field names (document layout analysis · text detection · text recognition · table structure recognition · mathematical expression recognition · reading order · OCR-error detection), joined by heuristics and a renderer. Its failure classes are per sub-task and per model; its cost is per model call and scales with the batch levers; its output carries geometry for free. Marker, MinerU-pipeline, docling, Unstructured, PP-StructureV3.
- **expert VLM** — one vision-language model trained for documents, page image in, markup out, no explicit OCR step ("OCR-free"). Its failure classes are the decoder's (repetition, hallucination, dropped regions) and the compression's (vision tokens per page); its cost is tokens; its geometry is whatever the prompt asks for. Chandra 2, dots.ocr, DeepSeek-OCR, MinerU2.5, PaddleOCR-VL (with a layout detector in front), GOT-OCR2.0, Nougat, granite-docling.
- **general VLM** — a frontier multimodal model prompted to transcribe. Same failure classes as the expert kind plus instruction drift; cost and rate limits are the API's. Gemini, GPT, Qwen3-VL; olmOCR is a fine-tune of one.
- **text-layer extractor** — no vision at all: the PDF's own content stream, ordered and rendered; optionally a **structure-side layout model** (pymupdf-layout: a GNN over the internals, CPU, ONNX) and an OCR fallback for pages with no text. Its failure class is the text layer's (garbled fonts, wrong order, math absent); its cost is milliseconds.
- **declared-structure reader** — reads what a tagged PDF *declares* rather than what any model *reconstructs* (docs/52's words); 19 of 4,307 converted pages (0.44 %) reach conforming structure on this shelf, so it is a witness at best today.

### 3.3 Words this project uses for more than one thing (disambiguated here, binding from this document on)

| word | meaning 1 | meaning 2 | meaning 3 | the rule |
|---|---|---|---|---|
| **chunk** | the analyst's ~4,000-char request unit (docs/34 §6, canonical) | a repair-ledger diff excerpt (docs/28) | Marker's *chunk renderer* / a 200-page *slice* (never "chunk" for a slice) | "chunk" = the analyst's unit; say "excerpt" and "slice" for the others |
| **lane** | `clean` / `scan` (the probe's routing; a manifest key) | the GPU lane / the Linux lane (a machine) | the Fable / Codex lanes (docs/46's LANE, a seat) | qualify it: routing lane · machine lane · model lane |
| **witness** | pymupdf's text layer (clean) | the embedded OCR layer (scan) | a gauge (Tesseract) or a second reader | "the witness" names the sub-slot; the tenant is named beside it |
| **engine** | the page-to-structure tenant (Marker, pymupdf4llm) | the LLM behind the analyst (qwen3:8b) | the server (llama-server inside Ollama) | engine = the page-to-structure tenant; model = the analyst's; server = the serving |
| **VLM / VLLM / vLLM** | a vision-language model (a kind) | vLLM, the serving library ("a fast and easy-to-use library for LLM inference and serving") | — | write **VLM** for the kind and **vLLM** for the server; "VLLM Model" is retired |
| **the card** | the RTX 3080, 10 GiB (docs/34) | — | — | unchanged |
| **the fence** | the image-embed multiset check | the link fence (asset immutability) | — | "the fence" = the embed check; "the link fence" = the rule |
| **the gate** | an acceptance criterion (docs/34) | the verdict gate (2.10) | the vault gate (2.12); the relay gate | qualify it |
| **Verified** | Observed + an independent second method (the muster's tag) | — | — | a lane never self-applies it; the adjudicator does (this sitting's rule, beside docs/46's list) |

## §4 The variation table — how the conclusion differs by the tenant

Every row: the slot · the variants (on this machine **M**, in the record **R**, in the field **F**) · the measured difference with its numerator, denominator and conditions · or **UNREAD** with what would read it. Field numbers are the source's own on the source's own bench and date (Historical) and are never this machine's.

### 4.1 The engine's kind

| variant | where | the conclusion |
|---|---|---|
| Marker 1.10.2 (pipeline tool) | M, R | the shelf's only engine: 25 anchor manifests, `engine: marker` on every one (Observed). Convert-stage `doc_survival` by book (weighted windows over scored pages, pymupdf witness): claude-code 0.9913 (flag) · Zero to One 0.9955 · IV University Edition 0.9333/0.9334 · IV 4e 0.927 · DDIA 0.8559 · Ashby 0.8582 (1956 OCR, the loss is Marker's) · Book of Models 0.6884 · Diagnosing (scan) 0.9558 · Valentine (scan) 1 on 1 of 465 pages scored (the floor); degeneration TRUE on most table-heavy books before SYM-067 (Damodaran 26 → 0 false blocks after). Field: OmniDocBench v1.6 Marker 1.8.2 Overall 78.44 / text edit 0.157 / CDM 85.24 / TEDS 65.77; olmOCR-bench Marker 1.10.0 76.5 (Old Scans 32.3, Tables 74.8); Marker's own bench balanced 76.0 % at 2.9 pg/s (GPU). |
| Marker fast mode (rf-detr layout, per-block OCR) | F | 66.6 % at 7.4 pg/s vs balanced 76.0 % at 2.9 pg/s (Marker's README, olmocr-bench) — **UNREAD here**: whether 1.10.2 carries the fast/balanced modes at all is unread (the README is the current release's; the changelog between 1.10.2 and it was not opened). |
| pymupdf4llm + pymupdf-layout (text-layer + GNN layout) | M (Linux) | **UNREAD on the shelf**: no Linux-converted bundle among the 25 anchors; no fidelity block is ever written on that lane. The field's bench has no row for it. What would read it: one clean book through the Linux lane with the Windows audit run out-of-band on the result. |
| Chandra 2 (expert VLM, 10.6 GB, Qwen3.5-based) | M (unwired), F | F: olmOCR-bench 85.8 (Old Scans 51.1, Tables 92.1) vs Marker 1.10 76.5 / 32.3 / 74.8 on the same bench and date — the scan column is where the kinds diverge most. M: **UNREAD** — never run here (the card is Rab's; ~5.3 B parameters in bf16 would not fit 10 GiB without quantisation — Inferred from the byte count). |
| granite-docling-258M (expert VLM, the bench's reading eye) | M | runs as a process-per-request reader of page crops, refuses while `.gpu-lock` exists; **UNREAD as a converter** (never run on a whole book). |
| MinerU pipeline vs MinerU2.5 VLM | F | one project, two kinds: 86.47 vs 95.39 Overall on OmniDocBench v1.6 for 4 GB vs 8 GB minimum VRAM (MinerU's README) — the cleanest field instance of "the conclusion differs by the variation". |
| docling (pipeline tool: RT-DETR layout at 72 dpi + TableFormer) | F | 1.27 pages/s on an M3 Max, 4 threads, native backend, OCR off, 6.20 GB (the report's Table 1); 2–6 s per table on CPU; Marker's bench puts docling (GPU) at 50.3 % / 2.1 pg/s. **Not installed here** (docling-env holds docling_core only). |
| dots.ocr / DeepSeek-OCR / olmOCR / Nougat / GOT-OCR2.0 | F | dots.mocr TextEdit 0.031 on v1.5; DeepSeek-OCR "< 10× compression → 97 %", 200k+ pages/day on one A100-40G; olmOCR 82.4 at ≥ 12 GB VRAM, "< $200 per million pages"; Nougat edit distance 0.071 vs the embedded text's 0.255, 19.5 s/page; GOT 580M. None on this machine. |

### 4.2 The engine's serving

| variant | where | the conclusion |
|---|---|---|
| in-process torch (`marker_single.exe`) | M | the shipped path; the sidecar owns the ceiling alone (SYM-132: 8,321–8,327 MB committed through recognition, Beer, batch 8). |
| vLLM | F | recommended by surya-current ("served either by vllm (GPU) or llama.cpp"), Chandra 2, olmOCR, dots.ocr, DeepSeek-OCR; **absent here** (Observed: `find C:/Users/Bndit/ml -maxdepth 4 -iname "vllm*"` empty). Its promise is throughput under concurrency (PagedAttention, continuous batching) — UNREAD for a one-book-at-a-time conveyor. |
| Ollama (the analyst) | M | production; `keep_alive 30m`, unloaded in `finally`; SYM-034/056 stalls; runs llama-server as its engine. |
| llama.cpp (the analyst) | M (binaries), R | S79 "+27 % tok/s" does NOT reproduce (backend_parity.py: slower on both phases at S81; SYM-035 arm-order artefact r = −0.78); the comparison's premise is one engine under two flag sets. Shelved. |
| a hosted API (Gemini Flash) | M, R | ≥ 13 s between calls (~4.6 RPM), 18 chunks per free-tier window, 3 retries; the analyst's cloud arm. |

### 4.3 OCR mode and the probe

| variant | where | the conclusion |
|---|---|---|
| keep the text layer (clean lane) | M, R | the default; chars/page ≥ 100. |
| `--strip_existing_ocr` (scan lane, Marker) | M, R | re-OCR by surya; Valentine 20 pages at 13.2 s/page and 6,177 MiB (S144), 200-page slices timing out at 4,003 s at the ceiling (9,515 of 10,240 MiB, 100 % util); Beer 184 pp at 4.72 s/page, 9,495 ± 20 MiB, batch 8 (S146 E8, dry run). |
| `force_ocr` | M (banned), F | pymupdf4llm's `force_ocr=True` KEEPS the old layer (SYM-012); the honest spelling is `FORCE_DROP_OLD`; Marker's `--force_ocr` is a different flag with a different meaning ("even for pages that might contain extractable text") — the same word, two tenants, two semantics: the rule is to name the tenant's flag, never "force OCR". |
| the OCR-error classifier as the probe | F | Marker's own probe ("an error-detection model assists in deciding when full-page OCR is necessary") vs ours (chars/page) — **UNREAD**: how often the two disagree on this shelf. |

### 4.4 Batch, slice, ceiling

| variant | where | the conclusion |
|---|---|---|
| recognition batch 32 (shipped) · 16 · 8 · 4 (recovery) | M, R | 9.8/10.2 GB peaks at batch 16 (docs/20); Beer at batch 8 held 9.5 GB (the sidecar alone); the ladder drops to 4 only on FROZEN progress or the budget's timeout (OK-17) — the ceiling-crawl (100 % util below the ceiling for hours) triggers nothing (`converter/ceiling-crawl-triggers-the-ladder`, open, his). |
| slices of 200 pages over 600 (clean) / 400 (scan) | M, R | ~18 % slice overhead at clean-lane rates (docs/18, S51 estimate); the doubled asset offset of pre-S60 chunked bundles (SYM-050) is this lever's own failure class. |
| layout resolution | M, F | Marker's ceiling 1,048,576 px (docs/41, measured) vs docling's 72 dpi vs DeepSeek's 64–400 vision tokens — the same axis in three vocabularies; **UNREAD**: the shelf's TEDS vs `lowres_image_dpi` (headroom −9 % … +228 %). |

### 4.5 Tables

| variant | where | the conclusion |
|---|---|---|
| Marker's own tables | R | Valentine anchor mean TEDS 0.672 over 14 hand-truthed tables (S157 E1 baseline, `--vision none`); F: Marker 1.8.2 TEDS 65.77 on OmniDocBench. |
| + the split pass (E1) | R | 0.672 → 0.745 (p200-t3 0.149 → 0.996); held 0.735 → 0.783. |
| + the trim pass (E3) | R | → 0.818 (p204-t1 0.550 → 1.000; up/same/down 6/8/0); held → 0.856. |
| + the leak pass (E20) | R | p200-t1 0.571 → 0.955; the other 13 unchanged. |
| + the vision reading (S156) | R | on the raw baseline 0.672 → 0.679 (2 of 14 tables touched: p.72 0.892 → 0.994, p.108 0.998 → 1.000); rails 5/7 → 7/7. |
| the index guard (E15) | R | Ashby's false labels 4 → 0; Valentine unchanged. |
| the field's other kinds | F | MinerU-pipeline TEDS 81.88; expert VLMs 90+ (Chandra 2 "Tables 92.1" on olmOCR-bench's scale); **UNREAD**: any of them on Valentine's 14 truths. |

### 4.6 Figures

| variant | where | the conclusion |
|---|---|---|
| figure coverage as shipped (P-1, unwired) | R | Cybernetics 57/1/0.9825 → after the anchored-lines fix 71/3/0.9577 (uncovered/figure pages; S157 E25); Ashby 23/9/0.6087; DDIA 104/2; IV 4e 269/49/0.8178 of which 10 real losses after a 49-page adjudication (E30); IV University Edition 293/76 (65 vector-only); the shipped IV figure is 239 (never 309) and POISONED (19 of 20 adjudicated FALSE, SYM-050). Cost 37 ms/page (IV) · 72 (Cybernetics) · 4.6 (a scan) — never 5.6. |
| the frame veto calibrated | R | a 0.35 line would veto 63 of 104 boxes and hide 0 of 203 figures; 0.30 → 80 / 0 (0.03 margin); 0.25 hides 2 real figures; the lever left at 0.60 (his). |
| scan-lane coverage | R | NOT APPLICABLE by construction (every page one raster region killed by `max_page_fraction`) — a reading, never "0 uncovered". |
| an expert VLM's figures | F | Chandra 2 "Extracts images and diagrams, with captions and structured data" — **UNREAD** on any book here. |

### 4.7 The analyst and the acceptor

| variant | where | the conclusion |
|---|---|---|
| analyst off | M, R | the Marker body ships as converted; the pre-acceptor losses do not occur; the ligature/hyphen repairs do not occur either. |
| analyst on, pre-acceptor (before S140) | R | whole sections dropped (IV UE 349/277 missing lines of 27,087 = 1.29 %/1.02 %; 4e held 349/27,830 = 1.25 %; the 4e pair isolates 204 prose lines on 19 pages as the analyst's own). |
| analyst on, with the acceptor (FULL) | R | DDIA 492 pairs: shipped 0.9718/49 → FULL 0.9822/24 (v3c body 0.9969/1); 1,914 accepted incl. 669 hyphen joins, 1,397 reverted; STRICT 1.0/0; Zero to One's missing lines 11 → 1 with identical survival scores (0.9955/0.9947) — the acceptor reverts drops the score cannot see. |
| the tables lever on | R | Valentine's rails on their row 2/7 → 5/7 (the span rule) → 7/7 (vision). |
| qwen3:8b vs Gemini Flash | R | **UNREAD as a paired comparison** on one book; the rates differ (local unpaced vs ≥ 13 s/call). |
| the in-engine LLM (`--use_llm`) | F | Marker's own pass "merge tables across pages, handle inline math, format tables properly, and extract values from forms" — **UNREAD here** (never enabled; it would run inside the engine, before the audit, with no acceptor). |

### 4.8 The witness and the degeneration detector

| variant | where | the conclusion |
|---|---|---|
| text-layer witness (clean) | M, R | the shipped witness; survival 0.69–0.99 by book (4.1). |
| embedded-OCR witness (scan) | M, R | agreement never hard-fails (docs/15); a scan with no layer scores 1 of 465 pages (Valentine) — "a scan-lane book CANNOT pass today" (docs/60 §2.2). |
| a Tesseract gauge (S144 E3) | R | 0.930 over 442 pages vs a control at 0.252 — a second witness exists for scans and is unwired. |
| degeneration, Windows (table rows blanked) | M, R | Damodaran 2025 4e 26 → 0 false blocks (SYM-067, J29). |
| degeneration, Linux (no blanking) | M | **a dense pipe table can still false-fire** (S158 E1, L2; Observed by comparison: no `_blank_table_rows` in `linux-converter/converter/degeneration.py`) — a ticket for his word (`linux-converter/port-the-table-row-blanking`). |
| Nougat's logit-variance detector | F | the same class detected on the model side (window 15, threshold 6.75; anti-repetition training cut failed conversions 32 % out of domain) — a design the field uses inside the engine and we implement on the text. |

### 4.9 The vault gate

| variant | where | the conclusion |
|---|---|---|
| `fail` on first ingest | M, R | refused since S146 E6 (Ashby 54b471d7 had reached the vault on 2026-09-13 11:31Z). |
| `flag` | M | ships (D1's current reading: ship-with-losses-named) — the policy lever is Rab's. |
| missing fidelity block | M | ingests — every Linux-converted book, by 2.12's divergence (Inferred). |
| supersede | M | opt-in, `pass` or `flag`+bless only; the commit message states the effective verdict (J40). |

## §5 The failure classes, by level

| level | class | instances (the rows) | who repairs it |
|---|---|---|---|
| **K — the kind's** | the autoregressive repetition loop | docs/15 §9 (Brain of the Firm); SYM-003; SYM-114 (J70); Nougat's paper | the engine's decoder (the field: anti-repetition training, logit-variance stops); ours: the text-side tripwire + the Repair Bench |
| K | the scan column (every kind is worst on old scans) | olmOCR-bench Old Scans 32.3 (Marker) … 54.6 (Datalab API); Valentine/Beer | a better tenant for the scan lane, or a gauge witness |
| K | the runaway / the duplicate (an LLM rewrite) | SYM-129 (7.59×), SYM-090 | the per-chunk gates (J34) |
| K | the text layer that exists but lies (garbled fonts) | the OCR-error classifier's reason to exist; SYM-105 (ligature glyphs `rst`, `proles`) | the probe; the acceptor's ligature class |
| **I — the instance's** | table fusion, padding, leaks | S157 E1/E3/E20; `analyst/stub-tables-are-prose-in-a-frame` (64 of 2,513 shelf tables with no body cell); `converter/table-crammed-into-one-cell` | the structural repair pass |
| I | asset naming as the only figure identity | `_ASSET_RE`; SYM-050's page attribution | the geometry sidecar (bboxes) |
| I | qwen3's think leaks | SYM-115, SYM-074 | the think-leak gate |
| **V — the version's** | the page-field creation counter | `marker_blocks.py` docstring (8, 8, 10, 26) | the sidecar's re-derivation; re-measure on every engine bump (SYM-044's identity gate) |
| V | `force_ocr` keeping the old layer | SYM-012 (pymupdf4llm 1.28) | the honest OCRMode spelling |
| **C — the chain's** | the doubled asset offset | SYM-050 (pre-S60 chunked bundles; 19/20 FALSE) | the in-memory page-map repair; never trust the poisoned count |
| C | the instrument manufactures the finding | SYM-067, SYM-076 (docs/58 S15) | table-row blanking; the ladder's order |
| C | the 25-run cap | SYM-066 | `runs_total` beside `runs` |
| C | perfect fidelity on an unmeasurable book | SYM-057 (latent) | `None`, never `0.0`; the coverage floor |
| C | a verdict never read | SYM-130 (first ingest) | the exporter's refusal |
| C | the sidecar lost on one path | S156 (deferred analyst) | the verifier fleet's plant |
| C | the lever nobody can write | SYM-131 (`audit-mode.txt`) | the sanctioned writer |
| C | the card's ceiling with no name | SYM-132 | `_gpu_top_committers` |
| C | whole sections dropped, unseen by survival | S157 E28/E36; SYM-104 | the acceptor (J46) + the digit multiset (J45) |

## §6 The chooser — a frame of questions, not a decision

For a book, ask in this order; each answer names the slot whose tenant matters, and the measured or UNREAD conclusion above.

1. **Does the page carry a text layer that tells the truth?** (2.1) If yes → a text-layer extractor is already most of the answer at milliseconds, and the engine's vision models are spent on layout, tables and math; if the layer lies (garbled fonts, 1956 OCR) → the probe must say `scan`, and the scan column (4.1, 4.3) is the whole game.
2. **Is it a scan?** Then no witness exists (4.8) and the verdict is capped at flag whatever the engine; the choice is between a pipeline tool's re-OCR (Marker: 13 s/page at 6.2 GB, 4.7 s/page at 9.5 GB by batch) and an expert VLM (Chandra 2's Old Scans 51.1 vs Marker's 32.3 on the field's bench — UNREAD on this card), and a gauge witness (Tesseract, 0.930 over 442 pages) would give the audit something to measure.
3. **Is it table-heavy?** Then the structural repair pass is worth more than the engine swap on this shelf (0.672 → 0.818 mean TEDS from four invariant-gated passes vs an UNREAD swap), and the degeneration detector must blank table rows (4.8).
4. **Is it figure-heavy?** Then the geometry sidecar decides whether coverage can be measured per bbox or only per page, and the frame veto's lever (0.60, his) decides how many boxes are called figures.
5. **Is it math-heavy?** The project has NO formula measure (CDM UNREAD); the field's expert VLMs lead on CDM; Marker's `latex_balance` only counts unterminated environments.
6. **Does it need the rewrite?** The analyst's gain is readability and ligature/hyphen repair; its cost is the pre-acceptor losses (now caught by the whitelist) and wall time (a 47 % wall tax measured S79 on the held book); the backend (local vs Gemini) is a rate decision, UNREAD as a quality pair.
7. **How long is it?** Over 600 (clean) / 400 (scan) pages the slice lever enters with its own class (SYM-050) and the ladder's budget (OK-17).
8. **Whose card is it?** Every engine of every kind above shares one 10 GiB card that is Rab's; a swap is a measurement first (a dry run on the anchors, the audit out-of-band, the shelf's TEDS on the 14 truths), never an adoption — and the adoption is his hand.

## §7 What this document cannot see

- The Linux lane has never been measured on the shelf (no Linux-converted anchor; no fidelity block on that lane) — every conclusion about pymupdf4llm as a converter is UNREAD here.
- No expert VLM has run on this machine as a converter (Chandra 2 unwired; granite-docling a crop reader) — every kind-vs-kind conclusion is the field's, on the field's bench.
- Formula recognition and reading order have no measure in the project; the field's CDM and reading-order edit distance are named here so their absence is visible.
- surya's current master (one 650M VLM) is not the surya on this disk (0.17.1, five models); a Marker upgrade changes the kind's shape inside the slot, and this document's 2.2 is 1.10.2's.
- The vision route is measured on 2 of 14 tables of one book; the acceptor's effect on 492 pairs of one book and 11 lines of another.
- The chooser is a frame; D1, `reanalyse Valentine`, the frame veto's lever, the tables lever's future, the engine swap and the experiment's end are Rab's words, none given here.
- This document was written by one lane and verified by a fleet with a plant (S158 E4); what the fleet did not read is in its residue, in the record.

## §8 Corrections (appended 2026-09-15 22:3xZ after the S158 E4 verifier fleet; the lines above stand as written — append-only)

1. **§2.4 and the degeneration rule: AND, not OR.** The text above says "zlib ratio < 0.20 OR max trigram ≥ 40". The code says AND: `windows-converter/fidelity_audit.py:254-258` — "AND, not OR (docs/15 §9.2): a loop is BOTH crushed-compressible AND has an extreme repeated word-trigram … The old zlib-OR path false-fired on the Cybernetics table-dense book" — `if ratio < DEGEN_ZLIB_MAX and mx >= DEGEN_TRIGRAM_MAX`; the Linux port `degeneration.py:13` carries the same AND. `docs/15` holds both spellings: §9.1 states the production prior as OR (Historical), §9.2 amends it to AND ("Block rule OR → AND: flag only when a block is BOTH"), and §12 still says "OR … per §9.1" — the code is the law; a reader of docs/15 §12 alone would be wrong. Found by lane V2 (Observed, the code's lines); confirmed by the lane (`grep -n "AND, not OR" fidelity_audit.py`). Every mention of the rule in this document reads AND from here.
2. **§4.7: 670 hyphen joins, not 669.** `sessions/S140-desktop-2026-09-12.md:101` (F4, Observed then): "1,914 accepted incl. 670 hyphen joins; 1,397 reverted". The 669 above came from the E1 lane's reading (Reported), copied without opening S140 — the pre-fix commit's 669 (of 1,919 accepted) is a different measurement. Found by lane V1; confirmed by the lane.
3. **§4.8's "anti-repetition training cut failed conversions 32 % out of domain"** was carried from the lane's fetch of the Nougat paper's full text (arXiv:2308.13418) and was not in the private sweep the document cites as its source of field numbers; the sweep now carries it with its source (S158 E4). The number stands.
4. **What the fleet did not find wrong.** Eighteen of the sixty claims the lane packeted for verification were refused as NOT-IN-DOC — the packet's claims packaged facts from the sources that this document states only in part or not at all (the builders' names, ocr2-env, the OmniDocBench Overall formula, the TEDS definition, SYMPTOM-INDEX statuses in §5 …). Those are the packet's overreach, not the document's errors; the document says what it says. The fleet's residue names two field numbers of the sweep the document dropped (MinerU pipeline 72.7 % at 0.54 pg/s on Marker's bench; EasyOCR's 30 s/page) — omissions, not errors; the sweep carries them.

## §9 The version axis (appended 2026-09-15 22:3xZ, S158 E5) — the engine on this disk against the engine the field ships today

The variation table's §4.1 left one row UNREAD: what Marker's current release would change. Read from PyPI's release history and the GitHub release notes (the lane's own fetch; Historical, the sources' dates):

- **marker-pdf**: 1.10.0 (2025-09-24) · 1.10.1 (2025-09-30) · **1.10.2 (2026-01-31 — this disk)** · **2.0.0 (2026-07-20 — the current release)**. **surya-ocr**: 0.17.0 (2025-09-23) · **0.17.1 (2026-01-30 — this disk)** · 0.20.0 (2026-05-27) · 0.21.x (2026-07) · **0.22.1 (2026-07-20)**.
- **What 2.0.0 changes inside the slot** (the release notes, quoted): three modes — "balanced" (76.0 % olmOCR-bench; the surya VLM for layout and full-page OCR), "fast" (66.6 %; "lightweight rf-detr/onnx layout + pdftext"), "--disable_ocr" (43.6 %; the text layer alone, CPU); "Mode now defaults by device automatically — balanced on GPU, fast on CPU/MPS"; "Marker reads the PDF text layer with pdftext and only calls the VLM where it's needed — garbled/scanned pages, equations, low-confidence tables"; "Many thin CPU workers share a single surya inference server; the parent process budgets VLM concurrency"; PyPI's own sentence: marker "is a pipeline built around the surya VLM, served by a local inference server". Breaking: Python 3.10+; Poetry → uv; "Structured-extraction converter/extractors were removed"; the mode default is device-dependent.
- **What that means in this document's terms.** The KIND does not change — 2.0.0 is still a **pipeline tool** (text layer first, models where needed) — but the engine's *shape* inside the slot does: five in-process specialist models (§2.2's (b)–(g)) become **one ~650M VLM behind a local inference server**, and the **serving axis gets a tenant** (vLLM on a GPU, llama.cpp on CPU/Metal — §3.1's row that reads "absent here" today). The accuracy conclusion on the field's bench is a wash — Marker 1.10.0 at 76.5 (Chandra 2's card, Datalab's own run) vs 2.0.0 balanced at 76.0 (its own release notes), the same bench at different dates — and the throughput and CPU conclusions are the release's gains (2.9 pg/s balanced, 7.4 fast, "a GPU" unnamed; a CPU path that did not exist in 1.10).
- **What a bump would touch in the chain** (Observed bindings, §2.2/§2.3): `MARKER`'s CLI flags (`--recognition_batch_size` and the `RECOGNITION_BATCH = 32` lever presume the in-process models; a served VLM budgets concurrency instead); `marker_blocks.py` in full (it imports `marker.converters`, `marker.renderers.chunk`, `marker.schema` — every class name is 1.x's); the `.done` identity gate that names `marker-pdf 1.10.2` (SYM-044: a bump re-keys every identity); the card's one-lab-process law (SYM-022) meeting a resident inference server; the routing probe (`MIN_CHARS_PER_PAGE = 100`) beside 2.0.0's own selective OCR; the table layer's levers, calibrated on 1.10.2's fusion/padding shapes (§2.5) — a different renderer's tables need a new shelf probe before the passes are trusted; `figure_coverage`'s asset regex if the naming changed. Every one of these is a measurement on the anchors (the 14 TEDS truths; the survival by book; the coverage by book) before it is anything else — and the run is on his card.
- **Tags.** The versions and dates: Historical (PyPI, fetched ~22:27Z). The bindings: Observed (E1, adjudicated). The bench comparison: the sources' own; not this machine's. The consequences: Inferred, each falsified by the dry run named.

## §10 Root origins on and against the evidence (appended 2026-09-16 02:4xZ, S159 E3) — the terminology and the reasoning corrected

*Rab's word (Desk c898160c, 02:03:40Z): "Conduct scope on and against evidences, discover root origins and correct terminology and reasoning based on task." The evidence: the 25 anchor manifests read whole (S159 E1), Marker 1.10.2's and surya 0.17.1's source, the chain's code and its git history, the S157/S144/S146/S104 records, the private prose probe — read by five Sonnet lanes with a plant each (S159 E2, run `wf_ae37b4a4-070`; 42 entries, 38 Observed / 4 Inferred) and re-measured by the lane at 27 cited lines (27/27 in substance). The sections above stand as written; this section says where they were wrong and why. A root origin is the STAGE and the LINE where a defect is born, with a level.*

### 10.1 The level key, extended — W and P

§2's key had four levels (K the kind's · I the instance's · V the version's · C the chain's) and filed every instrument-side class under C. Two more are needed and used from here: **W — the witness's / the instrument's** (the audit, the probe, the coverage tool — not the engine and not the chain's conversion code), and **P — the page's** (the input's own design or repetition: an index, a template, a worked-example frame, a real repeated protocol). Re-filed by this key: SYM-067 (empty table cells driving the trigram), SYM-076 (the ladder stripping an escape before unescaping), SYM-066 (the 25-run cap), SYM-057 (perfect fidelity on an unmeasurable book) and SYM-049 (zero-area paths dropped before clustering) are **W**, not C; the frame veto's false "uncovered" is **P+W**; the illustration boxes, the indexes, the generated template and Ashby's protocol are **P** before anything else. A level answers one question — *what would have to change for this class to go away* — and W and P are the two answers ("the instrument" and "nothing; the book is like that") the four-level key could not give.

### 10.2 Survival is disagreement, not loss — §4.1's row, corrected

§4.1 presents `doc_survival` by book as the engine's conclusion and writes of Ashby "the loss is Marker's". The manifests say otherwise:

| book | survival | what the run-mass actually is (Observed in the bundle) | missing prose lines (S157 E28, the prose probe) |
|---|---|---|---|
| Ashby (clean, 1956 OCR layer) | 0.8582 | **2,232 of 4,498 run-words (49.6 %) are the CONTENTS page** — split letter-by-letter across `<br>`-joined table cells (`Pre<br>fac<br>e`) — **and the INDEX**, rendered as a multi-column pipe table whose row-major order interleaves entries ('Coffee, 123 \| Degrees of freedom, 129 \| …'); the rest is symbol tables and math (p.55 `↓δ ε g h j k β α`), a re-lettered list, and one genuinely dropped paragraph (p.56) | 231 / 8,182 = 2.82 % |
| DDIA (clean, born-digital) | 0.8559 | **all 25 capped runs (of 299) sit on the INDEX, pp.634–669; 40 of the 41 index pages are flagged** — the table pass merged parallel index sub-columns into single `<br>` cells ('mergesort, 120, 471<br>relation to batch processing, 477-478<br>…') | 132 / 18,112 = 0.73 % |
| Diagnosing (scan, `lane_reason untrusted_ocr_layer`) | 0.9558 | the runs are the WITNESS's own garbage (p.77 'cl$ms£ct4 <xi)v/^fc-c4fe…', p.33 'r/auk£ 2, to^l industry') where Marker's text is clean prose — **the witness lies** | — (scan; no probe) |
| Cybernetics Book of Models (clean) | 0.6884 | **the source is an unfinished generated template**: 'Side bar infomation text size' ×20, 'Main Text Area', a draft editorial note left in the text, headings duplicated around one sentence (p.71); 77 of 85 scored pages flagged | 28 / 1,735 = 1.61 % |
| IV 4e 2025 / University Edition (clean) | 0.927 / 0.9333 | formula and calculation blocks (LaTeX vs the layer's glyphs), the crammed table | 0.52 % / 1.29 % |
| Zero to One (clean) | 0.9955 | two 24-word runs | 0.33 % |
| claude-code (clean) | 0.9913 | two 24-word runs (a `<div class="counter"` code line; a style-file line) | 0.71 % |

Across the seven books the two instruments rank the books with **Spearman ρ ≈ −0.68** (survival vs missing-line share): Ashby is the survival's third-worst and the probe's worst; Book of Models the survival's worst and the probe's second-worst. The signed criteria already knew: docs/15 §12 — "Acceptable books measured 0.76–0.96 survival (legitimate reflow)… They localize, they do not judge."

**The corrected terminology.** `doc_survival` is **window containment against a witness** — the share of the witness's 12-word windows found (fuzzily, ≥ 90) somewhere in the output; its deficit is **disagreement**, of which loss is one cause among nine (Observed on this shelf, `text_norm.py` / `fidelity_audit.py`): reordering across a window · table pipes and `<br>` flattened to spaces · LaTeX vs the layer's glyphs · dot leaders re-tokenised · newline-only dehyphenation · column interleaving · an index rendered as a table on one page and as prose on the next · a duplicated or interposed heading · and the fuzzy anchor cap (`FUZZY_ANCHOR_CAP = 50`: a common anchor word can hide its true match). **Loss** is the prose probe's number (a witness line ≥ 40 chars whose three 8-word windows are all absent) and has its own denominator. The witness itself has two failure classes: **no witness** (Valentine: the scan carries almost no OCR layer, 1 of 465 pages scored, the floor caps at flag) and **the witness lies** (Diagnosing: a layer exists, scores 156 of 184 pages, and is wrong where the engine is right) — coverage alone cannot tell them apart. §4.1's row reads, from here: *Ashby 0.8582 — half its deficit is its contents and index reformatted, not lost; DDIA 0.8559 — index-dominated; Diagnosing 0.9558 — the witness lies; Book of Models 0.6884 — the page's own template.* The words "the loss is Marker's" are withdrawn.

### 10.3 The loop — the mechanism, and §5's K row corrected

The recognition model in surya 0.17.1 is a vision encoder over an autoregressive decoder (`SuryaModelConfig.vision_encoder` / `.decoder`; `prediction_loop` decodes token by token with a KV cache). A loop on a degraded line runs **until Marker's own cap: `max_tokens=2048`** (`marker/builders/ocr.py:186-189`) — every genuine specimen on the shelf ends mid-word at ~2,048 characters: Diagnosing's `the state of the` ×~130 → `th Ex S` (a Text block); Zero to One's `# INTERNATIONAL PROPERTY AND ROUTE AND …` — **202 repeats in exactly 2,048 chars** (a SectionHeader); Ashby's `A B A B B B A B` — a real 50-transition protocol the decoder extends to ~495 tokens (**P then K**: the page's own repetition primes the decoder); Valentine's `of the control` ×100+ buried inside a list block whose eight-word excerpt reads as prose. Nothing content-aware stops it in Marker: surya carries a decode-time cycle detector **wired ON** (`drop_repeated_tokens=True`, `foundation/__init__.py`; `util.detect_repeat_token`: the last 40 tokens with ≤ 5 unique) and a block-level discard switch that **Marker ships OFF** (`OcrBuilder.drop_repeated_text = False`, `ocr.py:72`) — a loop the detector catches mid-decode still ships as truncated garbage instead of a blank. That switch is a lever; turning it is his word (a book could lose a block that was never a loop).

**Why a born-digital book reached the decoder at all.** Whether a page is OCR'd is decided **per page by four joint gates** (`marker/builders/line.py:148-169`: provider lines exist · the OCR-error classifier (a DistilBERT two-class head, argmax, no threshold, ≤ 512 tokens of the page) says good · layout coverage · line overlaps) — any one failing sends the WHOLE page to surya; there is no line-level or block-level re-OCR on a good page. Zero to One's page 1 is a title page (a large Figure, a sparse heading, an empty second heading) — the Inferred route (the `blocks.json` record carries no extraction-method field; a run would settle it, and the card is his). §4.3's row ("the OCR-error classifier as the probe") reads, from here: the classifier is one of four page-level gates, and the unit of the decision is the page.

**The instrument's eras (W).** The shelf's `degeneration: true` verdicts are three instruments' by date: Cybernetics' 07-21 copy fired on table rows at trigram 28 and 10 under the OR rule — converted at 05:27:45Z, **34 minutes before the AND commit `eb4dd87`** (06:01:29Z), whose message names this book as the false fire it fixed; its 07-31 copy is FALSE. IV 4e's 08-01 copy fired on four pipe-table rows **34 days before J29's blanking** (`8aa89360`, 2026-09-04; the manifest has no `table_rows_stripped` key); Valentine's 07-31 copy carried two table-row fires the 09-13 copy dropped (blanked 1,190 rows) while its real loop survived the blanking — J29 is selective. A worst-block excerpt is the block's **first eight words** (`fidelity_audit.py:261`), which can sit far from the loop inside a merged paragraph. docs/15 §9's founding specimen (Brain of the Firm, zlib 0.003, trigram ×2,267, two `##` headings) is not verbatim in today's anchor copy — the same vocabulary at other lines, lowercase, a third instance — the loop recurs nondeterministically across conversions of one source.

**§5's K row reads, from here:** *K — the autoregressive repetition loop — born in surya's recognition decoder on a degraded or self-repeating line, bounded only by Marker's `max_tokens=2048` (`ocr.py:188`); surya's own cycle detector is on, Marker's discard switch is off (`ocr.py:72`); a primed variant (Ashby) is P then K; the shelf's flags before `eb4dd87` (07-21) and before `8aa89360` (09-04) are the instrument's (W).* "Nougat's paper" stays as the field's name for the class; the named mechanism is surya's.

### 10.4 Tables — §5's I row split by stage

None of the table classes is the renderer's; `tablecell.py:36`'s `"<br>".join` and `renderers/markdown.py` serialise what the two upstream stages hand them. The origins:

| class | born at | level | what a swap changes |
|---|---|---|---|
| fusion of stacked tables (Valentine p.175) | **the layout stage's block boundary** — one Table block (`blocks.json /page/200/Table/3`) drawn across both tables, overlapping the neighbouring `TableGroup/57` by ~15 %; table_rec received one crop and built one grid inside it (`processors/table.py:87-99, 117-121`) | K,I | a different **layout** model draws different boundaries; a different table model changes nothing here |
| the leaked head (p.200) | the same overlap band, claimed by both crops' independent text assignment (`assign_text_to_cells`, `align_table_cells`) | K,I | as above |
| trailing padding (622 trims shelf-wide; 15 of 82 Valentine tables) | **table_rec's grid construction** — rows and columns predicted independently, then every row × column pair emitted as a cell (`surya/table_rec/__init__.py:301-334`); an over-predicted trailing column pads every row; Marker has no trim (`processors/table.py` whole) | K,V | a different **table-structure** model (or a trim pass) changes this; the layout model does not |
| the crammed cell (IV UE p.308, 1 of 1,662) | table_rec under-segmentation (one cell for the body) escaping Marker's own `split_combined_rows` (`table.py:314-425`, `row_split_threshold = 0.5`, a uniform-line-count precondition) | K,I | as above |
| the 64 stubs and prose framed as a table (Cybernetics' 'Participant A \| Participant B') | **the layout stage's Table-vs-Text decision** — table_rec runs only on blocks already labelled Table/TableOfContents/Form (`table.py:33`) and never votes on whether a region is a table | K,P | a different layout model changes this directly; the page's column-aligned design is the P half |

§5's row "I — table fusion, padding, leaks — the instance's" reads, from here: **K,I for fusion and the leak (the layout boundary), K,V for padding (table_rec's grid), K,I for the crammed cell, K,P for the stubs**; `table_geometry.py`'s "Marker's fusion / Marker's padding" is right as a chain attribution and imprecise as a stage attribution. The variation table's §4.5 gains the reasoning it lacked: **the conclusion differs by WHICH model is swapped** — the layout model moves fusion, leaks and stubs; the table model moves padding and cramming; the repair passes move both after the fact (0.672 → 0.818 on 14 truths).

### 10.5 The analyst — "pre-acceptor" was the wrong word

The gates' timeline, from git (`windows-converter/analyst.py`): the fence 2026-07-18 (`45e5995`) · **the per-chunk survival gate 2026-09-05 (`ad5e667`, J32-B, at 0.50)** · the think-leak gate 09-05 (`72a6ba9`) · the inflation gate 09-05 (`50242a8`, J34) · **survival 0.50 → 0.80 on 09-09 (`aa93818`)** · `/no_think` 09-12 (`4b7740f`) · **the acceptor 09-12 (`d874cab`, J46)** · the `num_predict` bound 09-13 (S146 E5). Against the shelf's conversions: IV 4e (08-01, analyst ~08-03), IV University Edition (08-31, 09-01) ran with **the fence only — no content gate of any kind**; DDIA (09-06) under 0.50, DDIA (09-09) under 0.80 (survival rejects 3 → 12); Zero to One copy A (09-12 03:39Z) under 0.80 before the `/no_think` fix; copy B (09-12 ~16:50 local) under the full stack with the acceptor.

Every whole-section drop on the shelf (IV UE 588 / 576 / 432 / 348 / 324 / 312 and 576 / 372 / 312 / 240 words; IV 4e 624 / 432) sits in the no-gate window and is **the model's omission, ungated (C+P)** — the 576/624-word runs are a LaTeX block dropped whole; 'A Postscript on Value Enhancement' vanished in three independent conversions of two editions (a P signal about the passage's position). The arithmetic (Inferred from `text_norm.py`'s rule; a re-run on the retained chunks would settle it): a ~650-word chunk holds 54 twelve-word windows; a contiguous loss of S words breaks ⌈S/12⌉ (+1) of them; **the 0.50 gate fires at S ≈ 313–325, the 0.80 gate at S ≈ 109–121** — the shelf's drops (312–624 words, 50–95 % of a chunk) would have been caught by EITHER gate. The 0.80 raise matters for partial degradation, not for this class. **The acceptor's real job is the small loss inside a passing chunk** (SYM-104, OPEN): Zero to One copy A lost a 48–60-word paragraph ("Did Bill Gates simply win the intelligence lottery?…") at survival 0.9947 — above any gate — and copy B restored it byte-for-byte from the `.marker.txt` through the `deletion` class. §4.7's row and §2.7's class read, from here: *whole sections dropped **pre-survival-gate** (before 2026-09-05), caught since by the survival gate; the small in-chunk loss caught since 09-12 by the acceptor.* Also corrected: the runaway is **K+C** (J34 rejects the over-length OUTPUT; S146 E5's `num_predict` stops the WAIT — two guards, eight days apart); the leaked token is `/no_think` (one slash; `analyst.py:222`); the University Edition's 588-word run is p.1036 and the 432-word run p.1174 (S157 E31 had them reversed; its own V3-08 corrected it; this sitting's packet carried the reversed pair once more).

### 10.6 Figures — SYM-050's mechanism, the flattened figure, the frame veto

**SYM-050 is C, from the fix's diff** (`6d0a560`, 2026-08-01, "Marker already numbers slice assets by absolute page"): the pre-S60 slice merge called `shift_asset_name(name, start)` on asset names Marker had already numbered by absolute page, doubling the offset for every slice after the first (a 1,356-page book produced asset pages up to 2,553). The asset name's N is the block's own absolute `page_id` (`renderers/html.py:101` → `BlockId.to_path()`; `groups/page.py:110-116`; `builders/document.py:41-50`) and is **independent of** the chunk renderer's page field, which reads the wrong id segment (`renderers/chunk.py:54-59`, `int(block.id.split("/")[-1])` — the per-page block counter; V, narrower than §2.3 implied). **The flattened figure** — a diagram's internal labels shipped as prose or a pipe table beside, not inside, its Figure — is **half of every lost figure on the Damodaran books** (6 of 11 on the University Edition, 6 of 10 on the 4e; S157 E24/E30) and was absent from §5: surya's layout labels are one flat set of 15 with no nesting (`surya/layout/label.py`, `schema.py`), and Marker's `add_blocks_to_pages` (`builders/layout.py:131-160`) adds every region as a sibling and never folds a Text/Table region back into the Figure that encloses it — **K+I** (the K half Inferred from the label schema; a run would show the classification). The frame veto's false "uncovered" is **P+W**: Damodaran's worked-example frames (P) meeting a density-only discriminator (`figure_coverage.py:673`), 41 of 104 boxes unreachable by any density line. SYM-049 is **W** (zero-area paths dropped before clustering, fixed S157 E25) — and its row's "neither has an asset in the bundle" is false at page level: p.34 and p.78 of the Book of Models carry five assets between them, thematically matching; whether they ARE the traced diagrams is UNREAD without the PDF.

### 10.7 The chooser (§6), re-reasoned

1. *Does the page carry a text layer that tells the truth?* now has a second half: **does the WITNESS?** Ashby's 1956 layer routed clean (chars/page ≥ 100) and became its own witness; Diagnosing's layer was judged untrusted, routed scan, and became the witness anyway under the agreement kind; a fresh scan (Valentine) audits against nothing. None of those three numbers is the engine's.
2. *Is it a scan?* The two witness classes need two remedies: no witness → a gauge (Tesseract, S144 E3); the witness lies → a second reading, not the layer.
3. *Is it table-heavy?* Name the stage before the swap: a layout swap moves fusion/leaks/stubs; a table-model swap moves padding/cramming; the repair passes move both after the fact.
4. *Is it figure-heavy?* Ask which class: absent (coverage sees it) or flattened (coverage cannot — the text is there, as prose).
5. *Does it need the rewrite?* The survival gate, not the acceptor, closes the whole-section class; the acceptor closes the small in-chunk loss; the `num_predict` bound closes the wait.
6. *Is it a bad scan?* The loop class is bounded only by `max_tokens=2048`; the discard switch (`drop_repeated_text`) exists and is off — a lever for his word before any engine swap.

### 10.8 What only a run would settle (UNREAD by name, the card his)

Zero to One's page-1 extraction method (pdftext or surya) · whether the shelf's loops trigger surya's ≤ 5-unique-token detector (the tokenizer's split) · whether p.34/p.78's existing assets are the traced diagrams · a re-audit of the pre-AND (07-21) and pre-J29 (08-01) manifests under today's rule · the chunk-survival breakeven on the real retained chunks (no `.marker.txt` for the University Edition) · the flattened-figure class on a second layout model · the loop with `drop_repeated_text=True` on one anchor.

### 10.9 Provenance and the lane's own errors

S159 E1 (the shelf read whole; the evidence map), E2 (the fleet: five lanes, five plants — four caught by id, D-07 refuted and misfiled; the lane's 27 probes), the record `sessions/S159-desktop-2026-09-15.md`. The lane's own errors, named by the lanes: a page mapping carried backwards from S157 E31 (corrected by S157's V3-08 and again here); an "adds" framing on an Ashby block that was already in the first manifest; a fourth worst entry omitted from a specimen; two Cybernetics fragments juxtaposed as one; a wrong section pointer. Nothing was run; no PDF was opened; the anchor shelf was read, never written.
