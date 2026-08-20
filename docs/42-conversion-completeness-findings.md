# 42 · Conversion-completeness research findings — the S97 external artifact

> **Provenance.** Archived verbatim (below the rule) from
> `C:\Users\Bndit\Downloads\conversion-completeness-audit-FINDINGS.md`, brought back by Rab on
> 2026-08-20 into the open S97 think-tank session. Produced OUTSIDE this repo by a 6-lane +
> 9-agent adversarial research effort; its claims describe marker/surya **in general**, not
> necessarily our installed versions.
>
> **Read docs/41 §1 before acting on anything in this file.** Grounding against our installed
> stack (marker-pdf 1.10.2 · surya-ocr 0.17.1) CONFIRMED its core completeness claims (the
> vector blind spot, the #598 transmutation hole, coverage-not-equality, both gate thresholds)
> and REFUTED or materially changed five others (no `page_needs_highres()` in our marker; our
> layout path is the VLM `FoundationPredictor`, not RF-DETR; the layout pixel ceiling is
> ~1.05 MP, not 6.29 MP; the ThinkPad placement for the audit is architecturally impossible —
> the source PDF never crosses the seam; and `asset_delta`/`embedded_images` are already
> computed on every book, unrendered). The integration plan is **docs/41**.

---

# Convert-stage research findings: upscale-for-layout, and source↔output completeness

**Method:** 6 parallel evidence lanes + a 9-agent adversarial panel (3 lenses × 3 propositions:
empirical / engineering-cost / already-solved). Every finding carries a retrieved URL.
**Result:** 9/9 propositions refuted as stated. One component survives in narrowed form and is
genuinely unserved by any shipping tool.

---

## P1 — "Upscaling an old scan improves how the LAYOUT model reads structure"

### REFUTED on this stack, 3/3 lenses

The pixels never arrive.

- `marker/builders/layout.py:136` → `images = [p.get_image(highres=False) for p in pages]` —
  **unconditional**. The layout builder never sees the high-res render.
- `surya/settings.py`, verbatim:
  - `IMAGE_DPI: int = 96   # used for layout + text detection (coarse structure)`
  - `IMAGE_DPI_HIGHRES: int = 192  # used for recognition + table rec (fine glyphs)`
- The conditioning runs **opposite to the intuition**: layout is given *fewer* pixels than
  recognition, deliberately.
- Surya's fast-layout path (RF-DETR) resizes every page to a fixed **704×704, aspect ratio
  destroyed** — a 96 DPI and a 300 DPI render produce a **byte-identical tensor**.
- MinerU is worse: PP-DocLayoutV2 preprocessing runs
  `tvF.resize(..., size=[800,800], interpolation=BICUBIC, antialias=False)`. A higher-DPI source
  raises the decimation ratio with antialiasing off — pre-upscaling makes aliasing *worse*.
- Other fixed-square resizers: PP-DocLayout-L 640×640 (`keep_ratio: false`), Docling 640×640,
  DocLayout-YOLO imgsz 1024, LayoutLMv3 224×224 (real signal comes from 0–1000-normalised boxes).

### Not novel

- **MinerU2.5** (arXiv 2509.22186, 1.2B, Apache-2.0) — this *is* its headline architecture:
  "layout analysis on downsampled images to identify structural elements… then targeted content
  recognition on native-resolution crops extracted from the original image."
- **DeepSeek-OCR** conditions the operating point on document class: Tiny 512²/64 tokens,
  Small 640²/100, Base 1024²/256, Large 1280²/400, Gundam = n×640² tiles + 1024² global. Slides
  need 64 tokens, books ~100, newspapers require Gundam (4,000–5,000 text tokens).
- **Eynollah** (Berlin State Library) has shipped `SBB/eynollah-enhancement` since ~2021 —
  described verbatim as upscaling "targeting documents with suboptimal resolution," applied when
  "detection of document layout exhibits inadequate performance." Upscale-for-layout, explicitly.

### Never measured

No published ablation varies input resolution against layout-detection mAP. DocLayout-YOLO,
PP-DocLayout and Docling each report mAP at exactly one fixed input size. The effect size of this
half is **unmeasured** — not small, not contested, simply never run.

### What survives: *reach the operating point*, not *upscale*

| Evidence | Number |
|---|---|
| DeepSeek-OCR reading-order edit distance (pure structure metric), 512px → 1024px canvas | **0.283 → 0.064** (4.4× fewer structure errors) |
| ModernVBERT document retrieval, 512px → 1024px | **+11.5 nDCG@5** (natural-image classification *drops* 41.4 → 33.7) |
| Qwen2-VL InfoVQA across 64/576/1600/3136 visual tokens | 28.85 → 65.72 → 74.99 → 77.27 |
| Qwen2-VL **OCRBench** across the same sweep | 572 → **828** → 824 → **786** — peaks at 576 tokens, then declines |

Qwen2-VL's authors: excessive enlargement "causes these images to deviate from the training data
distribution." Combined with Tesseract's cap-height finding (optimum ~30px, errors rise above it):
**resolution is an operating point, not a quantity.** It helps below the model's trained-for glyph
size, is discarded when the model resizes to a fixed square, and hurts when it pushes a
native-resolution VLM out of distribution.

### Actionable levers on your stack

1. `highres_image_dpi` (192) — note it only fires on Tables / Forms / TOC / Equations /
   ChemicalBlocks via `page_needs_highres()`.
2. `lowres_image_dpi` (96) — **only** meaningful on the default VLM `LayoutPredictor` path, up to
   the ~6.29 MP / ~260 DPI ceiling in `scale_to_fit`. Worthless on the fast-layout path.
3. For **born-digital** PDFs raising render DPI adds real pixels (vector source). For an already
   rasterised 200 DPI scan embedded in a PDF it only interpolates.

---

## P2 — "A model reading source + output, ignoring layout, finds missing characters and figures"

### REFUTED, 3/3 lenses — and this one is architectural

**The exact design has been benchmarked and fails.** AbsenceBench (arXiv 2506.11440) gives models
the original *and* modified document in context and asks what was removed.

- Best of 14 frontier models (GPT-4, Claude-3.7-Sonnet, Gemini-2.5-flash, o3-mini, DeepSeek-R1):
  **69.6% F1 — at ~5K tokens of context.**
- Average drop from the same models' Needle-In-A-Haystack scores: **56.9 F1 points.**
- Mechanism is architectural, not promptable: **an omission has no key for attention to attend to.**
- Reasoning bought +7.9% for ~8,000 extra thinking tokens. Model scale bought <4 F1 points
  going Qwen2-VL 7B → 72B.
- The benchmark contains **no images and no PDF conversion** — poetry, numeric sequences, GitHub
  diffs. So 69.6% is a ceiling on a task strictly *easier* than a book-length PDF↔markdown diff.

**The visual half fails harder.** MissingBench-Verified, 10 VLMs on detecting removed visual content:

- Accuracy on missing parts: **44.1% – 75.4%** (median band 47.5–58.5%).
- The same models identify those objects at **93.2–98.3% when present.** The deficit is specific to
  absence, not to seeing.
- Documented existence bias: Qwen 3.5 Flash answered "clearly visible" in **51.7%** of cases,
  exceeding its 47.5% correct-detection rate.

**Deterministic wins the head-to-head.** Consensus Entropy (pairwise normalised edit-distance
agreement — pure arithmetic, no judge) beats VLM-as-Judge on OCR quality verification by
**+15.2 F1, a 42.1% relative gain**: 48.0 vs 40.0 (GPT-4o), 51.3 vs 36.1 (Qwen2-VL-7B),
51.0 vs 39.8 (Qwen2-VL-72B).

### Datalab built this exact thing and then deleted it

`benchmarks/overall/scorers/llm.py` in **Marker v1.8.2** defines `LLMScorer`: renders the source PDF
with pypdfium2 (`doc[0].render(scale=96/72)`), sends `[img, markdown]` to gemini-2.0-flash-001 at
temperature 0 with a structured JSON schema. Its prompt: *"If text that is important to the meaning
of the document is missing, do not score higher than 3/5"*, plus a dedicated `images` sub-score
("if images are identified and placed correctly") and a 1/5 band for "major missing text segments."

Two things killed it:

1. It never ran alone — the harness always paired it with `HeuristicScorer`, a rapidfuzz alignment
   over ground-truth blocks weighted by block length plus a Kendall-tau order term. That's why
   Marker 1's README always reported a pair (heuristic 95.67, LLM 4.24).
2. **Marker 2 deleted it.** `benchmarks/overall/scorers/*` 404s on master; `benchmarks/README.md`
   now says quality "is measured with olmOCR-bench" — which states: *"We stay away from soft metrics
   like edit distance comparisons"* and *"All facts checked about documents are either pass/fail."*

The people who wrote your converter implemented your idea and replaced it with deterministic checks.

### The inversion that survives — measured

- **Pre-mark the gaps.** AbsenceBench's own ablation: inserting explicit placeholder tokens at
  omitted positions raised performance **+35.7% on average.**
- **Cascade, don't judge holistically.** LongRecall's decompose → lexical filter → semantic filter →
  entail beat holistic LLM judging *on the identical model* by **+0.34 to +0.37 F1**
  (QAMPARI 0.86 vs 0.52; challenging subset 0.65 vs 0.28; RoMQA 0.80 vs 0.36).
- **Per-page or per-span, never per-document.** All measured degradation is in context length and
  omission sparsity. A converter dropping one paragraph from a 300-page book is the *worst* point on
  that curve — and is exactly what the gate exists to catch.
- **Supply layout, don't strip it.** Marker's shipping `LLMPageCorrectionProcessor` passes bboxes
  normalised 0–1000, block ids and reading order. "Ignoring layout" is the one design choice in the
  proposal with **no implementation behind it anywhere.**

### The deterministic locator

- **RETAS** (Yalniz & Manmatha) — unique-word anchoring + LCS, O(nK). Aligns a full book in ~1
  second; **200 books of ~600K chars in 220 seconds**, holding **≥99% character alignment accuracy
  at 20% noise.**
- **Flexible Character Accuracy** — the CER variant explicitly built to be reading-order-tolerant.
  This *is* your "ignore layout" requirement, already named and published.
- **Free second lane on born-digital PDFs:** the embedded text layer. olmOCR calls this *document
  anchoring* and falls back to `pdftotext` outright.
- Your existing degeneration gate does **not** overlap with any of this. Nougat-style logit-variance
  detection (window 15, threshold 6.75, ~1.5% of pages) catches babble. A cleanly dropped paragraph
  produces no babble. The two failure modes are disjoint.

---

## P3 — "The combination is a competitive advantage"

### REFUTED as stated, 3/3 — but with a real positive inside it

Half one is a 2026 commodity (see P1). The halves are **not synergistic** — they're independent, and
one is worth nothing. And "competitive advantage" is the wrong frame: a single-user personal library
competes with nothing. The correct comparison class is **"my Marker output with no QA."**

### What genuinely survives: the figure/vector completeness audit

**Nothing does this. Two independent searches for source-vs-output image inventory diffing returned
only converter marketing.**

Why the gap exists, stated precisely:

- **OmniDocBench scores text, formula, table and reading order — and has no figure-extraction metric
  at all.** No converter is penalised for silently dropping a figure.
- **Docling's confidence report** has exactly four components — `layout_score`, `ocr_score`,
  `parse_score`, `table_score` (marked "not yet implemented"). Every one is computed **from what the
  pipeline found**, which by construction cannot see what it never found.
- **olmOCR** validates a page only by `total_tokens > 16384` and `finish_reason != "stop"`.
- **Marker has open, untriaged reports of exactly this failure:**
  - #526 — images "entirely skipped, with no references or placeholders left in the Markdown output"
  - #617 — the batch entrypoint drops images that `marker_single` keeps
  - #598 — figures containing text OCR'd into prose instead of emitted as an image reference

> ### ⚠ #598 is a live hole in the Survival Audit
> A figure OCR'd into prose produces **more** text, not less. Higher entropy, no repetition.
> It sails through a `zlib<0.20 AND trigram≥40` degeneration check and through a
> `doc<0.995 OR run≥25 words` near-exact-loss check, because nothing was lost — it was
> *transmuted*. The figure is gone and every existing gate reports clean.

### It costs zero VRAM

Everything here runs CPU-side on the ThinkPad and never touches the 3080 — the one-process law is
untouched.

| Instrument | Job | Cost |
|---|---|---|
| `pdfimages -list` (poppler) | **Spine.** Only tool giving xref (object ID) *and* a type column separating image / mask / smask / stencil in one pass — dedupe on object ID, drop non-image types, no decoding | CPU, ~instant |
| PyMuPDF `get_image_info(hashes=True, xrefs=True)` | Cross-check. Covers *displayed* images incl. inline; MD5 collapses the repeated-header-logo case | CPU |
| PDFFigures 2.0 | **Vector figures.** Parses drawing operators, clusters bboxes. Precision 0.936 / recall 0.897 (CS-Large), 0.980 / 0.961 (CS-150) | JVM, CPU-only |
| pdfplumber `.curves` / `.rects` | Cheap vector-presence signal (inventory/geometry only) | CPU |
| RETAS | Text-side candidate-loss locator | ~1 s/book |

**Do not build on `get_images()` alone** — the maintainer states it misses inline images, vector
drawings and annotation-fill images. But *do* discard the common myth that it misses Form XObjects:
it returns those, tagged via the `referencer` field.

### Two design corrections before you build it

**1. Coverage, not equality.** Marker, docling and MinerU **do not extract embedded image objects** —
they run layout detection and *crop the rendered page*. The source inventory and the output
inventory are not the same kind of object and will never hash-match (PyMuPDF explicitly warns
extracted bytes "may differ visually from displayed versions"). Build: *does each source figure
region have some output image whose bbox overlaps it?*

**2. Vector figures are the real blind spot.** A chart drawn with path operators has **zero image
XObjects**. Every raster enumerator reports "no images lost" while the figure is gone. This needs
PDFFigures 2.0 or a curves/rects density heuristic, not an XObject count. Caveat: PDFFigures 2.0 is
tuned for "Figure N:" captions in CS papers; recall on uncaptioned book plates is untested.

**False-positive traps to encode before the gate goes live:** the same logo image appearing on 300
pages (dedupe on object ID + MD5); SMask alpha channels counted as images; tiled/split images;
images used as backgrounds or masks; `--disable_image_extraction` runs.

---

## Vocabulary — the words for each stage

You said the hard part was the language. Five of seven stages have real citable names. Two do not,
and the honest answer matters more than a plausible coinage.

| Stage | Correct term | Note |
|---|---|---|
| Cleaning before recognition | **image preprocessing** (phase); *document image enhancement* (literature synonym) | OCR-D step names are canonical: **binarization, cropping, denoising, deskewing, dewarping** |
| Deciding whether a PDF has a usable text layer | **no term of art exists** | Usable vocabulary: *extractable text* (the tested property), *OCR routing* (the decision); four-way TextBased / Scanned / ImageBased / Mixed is the closest shared label |
| Text layer present but broken | **no name — but an exact description:** missing or incorrect **ToUnicode CMap** | Standards hook: **PDF/A conformance level "u"** exists specifically to forbid it. Detection lineage: Taghva "garbage string detection" (2001) → Datalab's shipped `ocr_error_detection` classifier. **Marker already implements this and calls the failure "garbled."** |
| Reading the page structure | **geometric (physical) vs logical layout analysis** → *page segmentation*, *region classification*, *reading order detection* | Classical algorithms benchmarked on UW-III: Voronoi 4.79% error, docstrum 5.16%, X-Y cut 8.76%, whitespace 10.48%, RLSA 13.73% |
| Comparing derived artifact vs source | **completeness** (the noun); NARA's QA / QC / validation distinction as the frame | OHRBench's *Semantic Noise* vs *Formatting Noise* names what your gate actually catches |
| Fixing recognition errors with language context | **post-OCR text correction** | ICDAR 2017/2019 two-task setup: error *detection* scored by F-measure, error *correction* by weighted Levenshtein |
| Governing standards | **FADGI ≈ ISO 19264-1 Level A ≈ Metamorfoze Full** — all govern *capture-device performance* | **NDSA Levels governs nothing in this pipeline** — it is a bit-preservation matrix with no image-quality content. Worth killing before it costs you time. |

Two things that bear on the build: the broken-text-layer failure has **two distinct modes** —
*missing* mapping extracts nothing, *wrong* mapping extracts **confident garbage**, and only the
second threatens a fidelity gate. Operator-presence triage cannot see the second, so those must be
**separate gates**.

**And the real resolution variable is `cap-height in pixels`, not DPI** — Tesseract's measured
optimum is ~30px, with errors rising above it. A 9pt footnote and a 14pt body line at the same DPI
are different problems.

### The 300 DPI rule is normative, not empirical

- It traces to Cornell's **Quality Index**, `QI = (dpi × .039h)/3` bitonal — a formula inherited
  from **microfilm** legibility standards. The OCR engine never appears in the derivation.
- FADGI asserts 3-star "has been tested with OCR" and publishes **no engine, corpus, error rate or
  comparison DPI**.
- Holley 2009, the most-cited library paper on the subject, recommends 300 dpi with **no
  DPI-vs-accuracy experiment in it.**
- Where DPI *was* actually varied (GPO/govinfo), downsampling 400/600 dpi captures to 300 or 200
  **did not improve** recognition. The dominant variable was capture mode: **RGB 98.26% vs bitonal
  77.12%** on the same aged, stained material.

### Generative super-resolution destroys text

| Real-CE 4×, OCR accuracy | Score |
|---|---|
| Real-ESRGAN (GAN) | 0.693 / 56.0% |
| StableSR / SupIR | 0.359 / 27.8% |
| SeeSR | 0.218 / 37.4% |
| DiffBIR / OSEDiff | 0.244 |

Both papers describe the failure as **fabricated glyphs**. Hallucination Score confirms diffusion SR
hallucinates more than regression SR, with "textual artifacts" as a named category. This is the
failure mode a compression-ratio/trigram gate **cannot** catch, because fabricated text is fluent.

The one positive for learned enhancement is **document-domain restoration**, not photo SR:
PreP-OCR's ResShift trained on document degradations halved CER **5.91% → 2.81%** on 13,831 real
historical pages — but deblur/destain does most of the work, and the baseline was Tesseract 5.

---

## Corpus reality check

Your corpus is the hard case, and the evidence is blunt about it.

- **Every** system is weak on old scans: **Marker peaks at 43.2%**, olmOCR 47.7%, against 83–99% on
  born-digital.
- On archival scanned newspapers, **classical detect-then-OCR beats end-to-end VLMs 10× on error
  rate** (SpACER 0.009 vs 0.097). The "newer VLM = better on old scans" assumption came out
  **negative** when searched for evidence.
- **MPDocBench-Parse** (433 PDFs / 3,246 pages / 15 types *including books*) is the benchmark that
  matches your corpus: PaddleOCR-VL-1.5 **80.80**, MinerU2.5 76.70, DeepSeek-OCR2 75.64,
  Qwen3-VL-235B 73.98, Gemini-3.1-pro 71.79. Absolute scores drop ~14 points vs page-level
  benchmarks.
- **Heading-hierarchy recovery tops out at 46.78%.** For an Obsidian vault of book-length markdown,
  chapter structure is roughly a coin flip *regardless of converter*.
- OmniDocBench is **saturated** — top models cluster within 0.12 points. Don't let it drive a
  decision.

### What fits 10GB (the 2026 frontier moved *down* in size)

| Model | Size | Fits? |
|---|---|---|
| GLM-OCR | 0.9B, 2.2GB BF16 / 1.6GB q8_0 | ✅ room to spare — OmniDocBench v1.5 leader (94.62) |
| PaddleOCR-VL-1.5 | 0.9B, ~2GB FP16 | ✅ (94.50; **wins MPDocBench-Parse**) |
| MinerU2.5 | 1.2B | ✅ Apache-2.0; **wins tables that span pages** (TEDS 88.14 vs 83.54) |
| MonkeyOCR-pro | 1.2B / 3B | ✅ only one with a published RTX 3090 figure: **0.49–0.69 pages/s** |
| Unlimited-OCR | 3B MoE, 500M active, MIT | ✅ but drop SGLang `--mem-fraction-static 0.8` and `--concurrency 8` |
| olmOCR | — | ❌ official minimum **12GB** |
| Chandra OCR 2 | 5B on Qwen3.5 | ❌ maintainer says **18GB+** unquantized |

**Ampere sm_86 has no FP8 compute** — vLLM runs FP8 checkpoints as weight-only W8A16 via Marlin.
Prefer INT4 / AWQ / GGUF when shrinking. Marker publishes **no VRAM number anywhere** — an evidenced
gap; your levers are `SURYA_INFERENCE_PARALLEL` and `--workers`, not weights (Surya 2 is 650M,
~1.3GB).

---

## Build order

1. **Figure/vector completeness audit, CPU-side on the ThinkPad.** `pdfimages -list` spine +
   PyMuPDF `get_image_info(hashes=True, xrefs=True)` cross-check + PDFFigures 2.0 for vector.
   Coverage semantics (bbox overlap), not equality. Zero VRAM, never competes for the card.
   **This is the only component with no prior art and a documented, unmeasured failure class.**
2. **Close the #598 hole** — figure-transmuted-to-prose defeats both existing Survival Audit
   signals. It needs its own tripwire: a source figure region with no corresponding output image
   reference *and* an unexplained text-density spike in that region.
3. **RETAS-style text alignment as the loss locator**, with Flexible Character Accuracy for the
   reading-order-tolerant comparison, and the embedded text layer as the free second lane on
   born-digital PDFs.
4. **LLM only as adjudicator** over spans the aligner has already marked, per-page, with layout
   supplied. Never as searcher, never per-document, never layout-blind.
5. **DPI as a measured experiment, not a belief.** If you touch it: `lowres_image_dpi` on the VLM
   layout path only, up to the ~260 DPI `scale_to_fit` ceiling, A/B'd against a fixed-DPI baseline on
   your own corpus. Nobody has published that delta — measuring it on your own library would be the
   genuinely new thing here.
6. **Never admit generative SR** without a held-out ground-truth set, and if any SR is admitted the
   gate needs a near-exact character diff against a no-SR lane — the failure is plausible wrong
   glyphs, not degeneration.
