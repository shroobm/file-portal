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
2. **The ThinkPad is unverified for the enrichment role.** phi4-mini (3.8B, ~2.5 GB q4) on CPU is plausible for async tagging; MiniLM embeddings + ChromaDB are light — but RAM and tokens/sec are unbenchmarked until it's online. Hard gate for Phase 3 only; Phases 0–2 are all Desktop-side. **RESOLVED 2026-07-19: Phase 3 measured and PASSED — enrichment sidecars yes, product-analyst stage no (see Phase 3 results).**

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
- [x] **Phase 2 — VRAM handoff:** install Ollama, scripted sequence Marker → unload → generate → Marker again.
  **Gate:** no OOM; VRAM returns to baseline between stages. **PASSED 2026-07-18 — see results below.**
- [x] **Phase 3 — ThinkPad sidecars** (needs it online): spec check, phi4-mini tok/s benchmark, ChromaDB + MiniLM over the existing vault.
  **Gate:** tagging fast enough for async per-document use; embeddings + search over the real vault work. **PASSED 2026-07-19 — see results below** (with one role boundary: the product-analyst stage stays on the Desktop GPU).
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

---

## Phase 1.5 results (Desktop, 2026-07-18, same day)

### 1.5a — `--strip_existing_ocr` + `--recognition_batch_size 32`, Beer pages 0–15: **the fix works**

63.3 s conversion for 16 pages (**~4 s/page → ~8 min for the full 116-page book**, vs the 27-min-and-killed force-OCR stall), peak VRAM **7 887 MiB** (down from the default run's 8 675 despite doing full re-OCR — the batch cap is what mattered). Quality is near-publication grade:

- `<sup>` artifacts: **0** (was 319 default / 37 pymu). Fake blockquotes: **0**. Word merges: **gone** ("how to learn", "someone").
- The TOC table renders **perfectly** — the exact structure that was `<br>`-scrambled in default mode and space-mangled in pymu.
- Italics recovered (*why*, *instability*) — neither earlier output had them.
- It even out-read both prior engines on ground truth: the copyright-page ISBNs come out complete ("ISBN 0 471 06220 0") where pymu dropped digits.
- Residue: a couple of mid-word splits inherited from the print's own line breaks ("unexpect edly") — deterministic post-pass territory; one Cyrillic homoglyph ("Ву" for "By") on a decorative title page.

**Conclusion: `--strip_existing_ocr` + capped `--recognition_batch_size` is the correct Scan-lane configuration** for PDFs with existing (untrusted) OCR layers, at a fully acceptable cost.

### 1.5b — born-digital A/B (webpage-printed PDF, 19 pp, mixed CJK/English, Chromium/Skia producer): **Marker wins outright**

Marker default: **27.3 s**, zero artifact noise, working **hyperlinks preserved** (pymu emits none), clean tables (the GitHub file listing), correct heading hierarchy, CJK + emoji intact, and **4 meaningful images vs pymu's 27** (it skipped the UI-icon spam pymu extracted as assets). pymu's version mashes the page nav into the first line and interleaves sidebar content mid-document. No contest — on born-digital input Marker's trusted-text-layer mode is both fast and clean.

### Engine policy that falls out of Phase 1 + 1.5

| Input class | Marker mode | Cost (3080) |
|---|---|---|
| Born-digital (good text layer) | default | ~1.5 s/page |
| Scan with existing OCR layer | `--strip_existing_ocr --recognition_batch_size 32` | ~4 s/page |
| Raw scan (no layer) | default (Marker OCRs what needs it) | ~4 s/page expected |

The existing converter probe (`probe_chars_per_page`) plus a check for **OCR-font spans** (pymupdf exposes whether text comes from an OCR layer) can pick the row automatically — same probe-and-route idiom the Clean/Scan lanes already use.

---

## Phase 2 results (Desktop, 2026-07-18, same day) — VRAM handoff: PASSED

Ollama **0.32.1** (winget) + **qwen3:8b** q4 (5.2 GB pull). Scripted sequence `ml\phase1\phase2_handoff.ps1`: Marker (Beer pages 0–5, warm) → Ollama generate with `keep_alive: 0` → Marker again, VRAM sampled at every boundary:

| Checkpoint | VRAM |
|---|---|
| Baseline | 623 MiB |
| After Marker stage 1 (17 s, exit 0) | 623 MiB |
| After generate (85 s wall, 1 228 tokens, **52.6 tok/s**) | 621 MiB — `ollama ps` empty (immediate unload) |
| After Marker stage 2 (18 s, exit 0) | 620 MiB |

Overall sequence peak **6 187 MiB** — each occupant fits with headroom **because they are serialized**; the scope's mutex requirement stands but the mechanism (`keep_alive: 0` + never-concurrent) is now *measured*, not assumed. No OOM anywhere. 52.6 tok/s means a full-book reformat pass is minutes, not hours.

**⚠️ Finding for the "product analyst" stage:** given a raw "reformat this markdown" prompt, qwen3:8b **rewrote image links** — `![](_page_0_Picture_2.jpeg)` came back as `![](https://example.com/_page_0_Picture_2.jpeg)` (invented URL — would break every bundle). The prose reformatting itself was good (clean headings, fixed hyphenation). Design consequence: the LLM pass must be **fenced** — either strip/re-inject asset links around the LLM call, or post-validate that every link in equals every link out and reject the pass otherwise. Never let the analyst touch the packaging.

Two Windows-side engineering notes learned the hard way (both matter for any future service wrapper): PS 5.1 turns Marker's stderr INFO logs into fake failures if you redirect (`2>$null`) inside PowerShell — spawn via `cmd /c` with native redirection; and PS 5.1 `Invoke-RestMethod` mangles non-ASCII JSON bodies — write UTF-8 to a file and POST with `curl.exe --data-binary`.

---

## Phase 3 results (ThinkPad, 2026-07-19) — sidecars: PASSED

The scope's red flag #2 ("the ThinkPad is unverified for the enrichment role") is now measured. Verdict up front: **the ThinkPad carries the enrichment sidecars (tag, embed, structure) comfortably — but the "product analyst" full-document LLM stage does NOT live here.** Numbers below.

### Spec check (the plan was written blind on this)

| Component | Value | Implication |
|---|---|---|
| CPU | i7-1265U (12th gen): 2 P-cores + 8 E-cores, 12 threads, 4.8 GHz max | Laptop U-class — fine for async work, not a throughput engine |
| RAM | 15.3 GiB total, ~13.5 GiB available at idle | phi4-mini (~3 GiB resident) + MiniLM (~1.2 GiB) fit together with room to spare |
| Disk | 233 GB NVMe, **199 GB free** | Models + vector store are noise (~4 GB total installed this phase) |
| Swap | 4 GiB zram (zstd), no disk swap | Already configured; untouched at 0B used throughout the benchmarks |

### Ollama on CPU — phi4-mini tagging benchmark

Ollama **0.32.1** (same version as the Desktop's Phase 2) + **phi4-mini** 3.8B q4 (2.5 GB pull). *Install divergence, noted per protocol:* no sudo credential was available in the session, so instead of the native Arch package this is the official release tarball run user-level from `~/ml/ollama` (`OLLAMA_MODELS=~/ml/ollama/models ./bin/ollama serve` — no systemd unit, nothing system-level, fully removable). If the ThinkPad takes the role permanently, `sudo pacman -S ollama` supersedes it.

Benchmark: real vault prose (Beer book body text) → "produce YAML frontmatter: tags, summary, reading_level". Timings from the API's own `*_duration` fields; RAM from the runner's `VmHWM`:

| Metric | Value |
|---|---|
| Model load | 3.5 s cold, 0.3 s warm |
| Prompt eval | **~29–31 tok/s** (422-tok and 1330-tok inputs, consistent) |
| Generation | **4.1–5.8 tok/s** |
| Wall per tagging call | 28 s cold / 9 s warm (1500-char excerpt); 56 s (6000-char excerpt) |
| Peak RAM (runner) | **3.06 GiB** RSS; system never approached swap |

**Tagging gate (async per-document, minutes OK): PASS.** A realistic excerpt-based tagging call is 10–60 s per document; even a generous multi-chunk pass stays under ~5 min. **But the same numbers rule out the full-document product-analyst role here:** a 116-page book (~45 K tokens) at ~30 tok/s prompt eval + ~5 tok/s generation is **~3 hours per book** vs minutes on the Desktop GPU (52.6 tok/s generation measured in Phase 2 — ~10× this CPU, with prompt eval faster still).

*Quality note for the tagging prompt design:* on a bare 1500-char excerpt phi4-mini took Beer's wave metaphor literally (tagged it `physics`, `oceanography`); the 6000-char run recovered the real topics (`dynamic systems`, `social institutions`). Tagging prompts should carry document context (title, TOC, several chunks) — excerpt-only tagging mislabels metaphor-heavy prose.

### ChromaDB + all-MiniLM-L6-v2 (384d) over the real vault

`uv` venv at `~/ml/chroma-env` (CPU torch), vault cloned read-only to `~/ml/vault` (the 2 real books: Beer "Designing Freedom", Textor "Judgement and Truth"), chunked at ~800 chars/paragraph boundary → **1218 chunks**:

| Metric | Value |
|---|---|
| MiniLM model load | 4.6 s |
| Embed 1218 chunks | **34.2 s (35.6 chunks/s)** — a full book indexes in ~20 s |
| Chroma add (persistent store, cosine) | 0.8 s |
| Query latency | **3–6 ms** |
| Peak RSS (whole process) | 1.16 GiB |

Relevance eyeball — 4 queries, all 4 hit the correct book with on-point passages: "bureaucracy threatening freedom" → Beer's institutions-survive-for-themselves passages; "Frege's account of judgement and assertion" → the Textor Frege chapter (top distance 0.209, clearly strongest match of the set); "computers regulating society in real time" → Beer's teleprocessing/economy passages; "theories of truth" → Textor's coherence/dependence-of-truth passages. **Embedding gate: PASS**, with margin — at vault scale this workload is trivial for the machine.

### Recommendation: where the product analyst lives

**Desktop GPU, with the Phase-2 mutex (`keep_alive: 0`, never concurrent with Marker).** The measured gap is decisive: 52.6 tok/s (qwen3:8b on the 3080) vs ~5 tok/s here means a full-book reformat pass is minutes vs hours — and the analyst stage is per-book full-document work by definition. GPU contention is real but already solved by serialization; hours-per-book is not solvable on this CPU. The ThinkPad's role in the inversion is exactly the sidecars proven here: **async tagging (phi4-mini, excerpt+context prompts), embeddings + semantic index (MiniLM + ChromaDB), and structure extraction** — all light on RAM, all zero-contention, all off the Desktop's critical path.

**Environment note:** everything this phase installed lives outside the repo — `~/ml/ollama` (server + models), `~/ml/chroma-env`, `~/ml/chroma-store`, `~/ml/vault` (read-only clone), bench scripts in `~/ml/`. The live converter/allocator/exporter services were not touched.

---

## Design note — the widget as factory control center (user vision, 2026-07-18; NOT yet implemented)

The user's framing for where this revamp ultimately lands, recorded here so every later phase builds toward it:

> Treat the entire project as factory process and production. The widget is the OS / command-and-control center — where files go, what happens to them, data-logistics measuring, ETA estimation. Allocator = **conveyor belt**. Marker = **processing plant**. Ollama = **product analyst** — the hand-away that smart-reformats the markdown for intelligibility and readability, with intent on the user experience. Final product ships to the **vault**, where it can be opened and seen. Modern, seamless look and feel, integrated slowly.

**Two load-bearing design principles from that brief:**

1. **Each segment can be turned off and evaluated independently.** Every station (allocate → convert → analyze/reformat → export) gets an on/off switch and an inspectable output. This is cheap to honor because the pipeline is already staged with file-drop handoffs; the missing piece is surfacing per-stage toggles + status to the widget instead of burying them in config files and journalctl.
2. **The widget reports logistics, not just success/failure.** Queue depth per station, per-document stage + progress, measured throughput (the s/page numbers in this doc make ETAs computable: ~1.5 s/page born-digital, ~4 s/page re-OCR, + LLM pass), and ETA per item. The converter already logs `chars_per_page` and wall times — the raw material for this exists; it needs a status feed the widget can poll, in the same spirit as the existing allocator `status.json` feed the tiles already consume.

**Sketch of the factory mapped to real components** (target state, phased):

| Factory station | Component | Runs on | Exists today? |
|---|---|---|---|
| Intake / conveyor | widget tiles → Tailscale transport → allocator | Desktop → ThinkPad | ✅ (production) |
| Processing plant | Marker (engine policy table above) | **Desktop GPU** | ✅ engine proven; not wired in |
| Product analyst | Ollama `qwen3:8b`, `keep_alive:0`, mutex with Marker | Desktop GPU | ✅ Phase 2 passed (link-fencing required) |
| Packaging | bundle format (manifest, SHA dedup, Windows-clean names) | unchanged | ✅ — **must not break** |
| Shipping / warehouse | vault git push → Add-to-Library button | ThinkPad → Desktop | ✅ (production) |
| Control room | the widget: toggles, gauges, ETAs, modern look-and-feel | Desktop | ❌ future work, integrate slowly |

**Explicitly deferred** (user said think, don't build yet): widget UI changes, per-segment toggle plumbing, ETA feed, any rewiring. Sequencing intent: Marker + Ollama functional in the current ecosystem first (done as of Phase 2), then the control-room features arrive incrementally — each one small, switchable, and evaluated before the next.
