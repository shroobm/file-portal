# GPU Pipeline Revamp — Scope & Phase Plan

**Origin:** planning session 2026-07-18 (Desktop, post-reset), verified against the actual hardware and current upstream sources.
**Idea:** move document conversion off the ThinkPad's CPU stack (pymupdf4llm / Pandoc / tesseract) onto the Desktop's GPU with [Marker](https://github.com/datalab-to/marker), and demote the ThinkPad to enrichment (tagging, embeddings, structure). Add a local LLM (Ollama) on the Desktop and semantic sidecars on the ThinkPad.

---

## Verified hardware baseline (Desktop, 2026-07-18)

| Component | Value | Implication |
|---|---|---|
| GPU | RTX 3080 **10 GB** | Fits Marker (~5 GB peak) OR an 8B q4 model (~5–7 GB) — **never both at once** |
| Driver | 610.62 (Windows Update) | No separate CUDA toolkit needed; modern torch wheels bundle their CUDA runtime |
| System RAM | 16 GB | **One** Marker worker max; don't convert while gaming |
| CPU | i7-8700K | Fine as feeder |
| Python | Store stub only | Phase 0 installs a real Python via `uv` |

## The VRAM math

Marker peaks ~5 GB/worker (~3.5 GB average). An 8B model at q4 in Ollama takes ~5–7 GB with KV cache. Each fits alone in 10 GB with headroom; together they OOM — this is a [known Marker + local-LLM problem](https://github.com/datalab-to/marker/issues/1038). Resolution: `keep_alive: 0` on Ollama (~5–10 s model reload per generation — irrelevant for an async pipeline) plus a **tiny mutex/queue** (single worker; a lock file is enough) so a Marker job and a generation never overlap. Design item, not a risk.

## 🚩 Red flags

1. **Forgejo does not run on Windows.** [Officially unsupported since 2024](https://codeberg.org/forgejo/forgejo/issues/6103) — no binaries, no upstream interest. Options: host on the ThinkPad (Arch is first-class, and it already hosts the bare vault repo — the natural git host), WSL2/Docker on the Desktop (adds a VM layer to the most RAM-tight machine), or defer entirely (bare git over Tailscale SSH is the proven transport; Forgejo adds UI, not capability). **Recommendation: ThinkPad-hosted, and last in the build order.**
2. **The ThinkPad is unverified for the enrichment role.** phi4-mini (3.8B, ~2.5 GB q4) on CPU is plausible for async tagging; MiniLM embeddings + ChromaDB are light — but RAM and tokens/sec are unbenchmarked until it's online. Hard gate for Phase 3 only; Phases 0–2 are all Desktop-side.

## The design inversion

Today's intake converts **on the ThinkPad**. This revamp reverses the flow: PDF → Marker on the Desktop → push markdown to the ThinkPad → enrichment → vault push → back to Obsidian. The thing to protect while rewiring is everything L13/L14/L15 taught us: **SHA-based dedup (`EXPORT-SKIP`), the manifest format, atomic `.part-` transport, Windows-clean interior filenames**. Bundle-format compatibility is the single biggest design item — the new front end must not break the proven back half.

## Pre-answered small decisions

- **Embeddings:** 384d / `all-MiniLM-L6-v2`. At vault scale, re-embedding later costs minutes — fully reversible, must not gate anything.
- **8B generation model:** `qwen3:8b` or `llama3.1:8b` at q4 — both fit the budget.
- **ZenNotes:** unevaluated; revisit at Phase 3.

---

## Phases, gated by verification

- [x] **Phase 0 — Desktop ML baseline** (~30 min): `uv`, real Python, torch cu12x. **PASSED 2026-07-18.**
  **Gate:** `torch.cuda.is_available()` → `True` on the 3080. ✅
- [x] **Phase 1 — Marker vertical slice:** convert one clean-text PDF (Beer "Designing Freedom" — the first-ever real ingest, so known ground truth) and later one scanned PDF; measure wall time and peak VRAM; compare output quality against pymupdf4llm on the same input.
  **Gate:** visibly better markdown; VRAM ≤ ~6 GB. **MIXED PASS 2026-07-18 — see results below.**
- [ ] **Phase 2 — VRAM handoff:** install Ollama, scripted sequence Marker → unload → generate → Marker again.
  **Gate:** no OOM; VRAM returns to baseline between stages.
- [ ] **Phase 3 — ThinkPad sidecars** (needs it online): spec check, phi4-mini tok/s benchmark, ChromaDB + MiniLM over the existing vault.
- [ ] **Phase 4 — Pipeline rewiring:** the inversion above, bundle-format compatible.
- [ ] **Phase 5 — Forgejo:** ThinkPad-hosted, or consciously dropped.

**Environment note:** the Desktop ML environment lives at `C:\Users\Bndit\ml\` — outside this repo. Only docs and (later, Phase 4) pipeline code land here.

## Phase 0+1 results (Desktop, 2026-07-18)

### Phase 0 — PASSED

`uv` 0.11.29 (winget), CPython 3.12.13, torch **2.11.0+cu128** — `torch.cuda.is_available() → True`, device `NVIDIA GeForce RTX 3080`. Environments (outside the repo):

- `C:\Users\Bndit\ml\marker-env` — torch cu128 + `marker-pdf` 1.10.2 (surya-ocr 0.17.1)
- `C:\Users\Bndit\ml\pymu-env` — `pymupdf4llm` 1.28.0, the **exact ThinkPad pin**, for the baseline
- Marker models cache: `%LOCALAPPDATA%\datalab\datalab\Cache` (~2.4 GB, one-time download)
- Test artifacts kept for inspection: `C:\Users\Bndit\ml\phase1\` (`pymu\output.md`, `marker\…\*.md`, `run_pymu_baseline.py`)

### Phase 1 — the A/B on the Beer book (116 pp, Internet Archive scan with a 2013 OCR text layer)

The baseline replicated the ThinkPad Clean lane **exactly** (same version, same flags: `write_images=True, dpi=150, use_ocr=SELECT_KEEP_OLD`) and reproduced the recorded first-ingest probe to the decimal (1484.7 chars/page), so this is a faithful ground truth.

| Metric | pymupdf4llm 1.28.0 (CPU) | Marker 1.10.2 default (GPU) |
|---|---|---|
| Wall time | 74.8 s | **97.3 s** (251.5 s cold incl. model download) |
| Peak VRAM | — | **8 675 MiB** total (≈7.5 GB above the 1 156 MiB desktop baseline) |
| Output size | 179 068 chars | 177 204 chars (≈ same text recovered) |
| Images extracted | 24 | **36** (incl. cover + all end-matter sketches) |
| Image links | absolute local paths (rewritten later by `bundle.rewrite_image_links`) | **relative** (`_page_N_Picture_M.jpeg`) — bundle-friendly as-is |
| Paragraphs | page-shaped text blocks | **real paragraph breaks** |
| Misrendered blockquotes | 30 lines | **1 line** |
| Sketch pages | OCR gibberish injected as "picture text" (`aWsztiuaJkar…`) + garbled caption mash | **clean captions as body text**, images alongside |
| Spurious `<sup>` tags | 37 | **319** (isolated `I`/`a`/years wrapped as superscript) |
| TOC | table with missing spaces ("AllWe Hold Most Dear") | **scrambled** word-per-line `<br>` soup |
| Word spacing | mid-word splits ("unexpect edly", "atmos phere") | same splits **plus** merges ("tolearn", "itis", "issome") |
| Structural metadata | none | `_meta.json` with real TOC (titles, page ids, bboxes) |

**What went wrong, precisely:** every Marker regression traces to one cause — Marker *trusted the PDF's embedded 2013 Archive.org OCR text layer* (extracted via pdftext) instead of reading the pages itself. The `<sup>` wrapping is Marker's line formatter reacting to that layer's baseline/font-size noise; the word merges and the scrambled TOC table are that layer's character spans, faithfully reproduced. Everything Marker computed **itself** (layout, paragraphs, reading order, image regions, sketch captions via its own OCR of image-only regions) beat the baseline clearly.

**The `--force_ocr` attempt (the obvious fix) failed on cost:** with models warm it saturated the GPU at 100% for **27+ minutes** with no output (vs 97 s default) at a peak of **9 939 MiB** — Marker auto-scales recognition batch sizes to fill available VRAM and the full-book re-OCR (1 281 text regions) thrashes at the 10 GB ceiling. Killed. This is a settings/scale problem, not a hardware fault — but it rules out force-OCR at defaults as a pipeline lane on this card.

### Fix candidates, in test order (all flags verified against `marker_single --help`)

1. **`--strip_existing_ocr`** — discard the bad embedded layer and let surya re-read. This targets the root cause directly. Must be tested **with a capped `--recognition_batch_size`** (start ~32) so it doesn't repeat the force-OCR stall, and first on a `--page_range 0-15` subset to get a per-page cost before committing to a full book.
2. **Cap batch sizes generally** (`--recognition_batch_size`, `--layout_batch_size`, `--table_rec_batch_size`) to bring peak VRAM under the ~6 GB coexistence budget from the scope. The 8.7 GB default peak is auto-scaling, not a requirement.
3. **Deterministic post-pass** in the bundle normalizer (the pipeline already rewrites image links there): strip `<sup>…</sup>` wrappers and rejoin hyphenation splits. Cheap, engine-agnostic, and fixes the baseline's artifacts too.
4. **`--drop_repeated_text`** for OCR repeat noise; `--disable_tqdm` for service logs.
5. **Test a born-digital PDF next.** The Beer book is the *worst case* (scan + stale OCR layer). Most Anna's Archive drops are born-digital, where the trusted-text-layer failure mode doesn't exist — Marker default mode should win outright there. This is the missing half of the Phase 1 evidence.

### Verdict

Marker default mode is **already structurally better** than the current engine for the vault use-case (paragraphs, sketches, images, metadata) and its one real defect class is inherited from bad embedded OCR layers — fixable by `--strip_existing_ocr` (needs the timed retest above) and/or a deterministic post-pass. Wall time is fine (97 s warm). VRAM needs explicit batch caps before Phase 2's Ollama coexistence. **Phase 1 gate: mixed pass — proceed, but run the strip-existing-ocr + born-digital retests before any pipeline rewiring (Phase 4).**
