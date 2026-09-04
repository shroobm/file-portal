# Lane E — Frameworks and the Honest Discard List

GROUND: File Portal, offline-by-design, one RTX 3080 (10 GB VRAM, ~8.3 GB free idle).
Job: read deepdoctection and Unstructured-IO/unstructured as FRAMEWORKS (not tables — Lane B
has that), read UglyToad/PdfPig for low-level PDF access pymupdf might lack, write the discard
list for everything the mechanical triage rejected, and open the YousifHisham table notebook.

All repo facts below are **Observed** (fetched from source, dated 2026-09-03/04 via WebFetch /
GitHub API — `gh` is unauthenticated here, so plain HTTPS + `api.github.com` was used
throughout; nothing was cloned). One measurement below is **Verified** — run on Rab's own files.

---

## 1. deepdoctection (`deepdoctection/deepdoctection`, default branch `master`)

**License**: `LICENSE` at repo root — Apache License, Version 2.0, January 2004. Clean.

**What it pulls** (repo split into 4 sub-packages under `packages/` — `dd_core`, `dd_datasets`,
`deepdoctection`, `shared_test_utils` — each with its own `pyproject.toml`):
- `dd_core[full]` base: pikepdf, pypdf, jsonlines, scipy, pypdfium2 — light.
- `deepdoctection[full]` (the actual analyzer): `pdfplumber`, `pycocotools`, `timm>=0.9.16`,
  `transformers>=5.2.0`, `accelerate>=0.29.1`, `python-doctr>=1.0.0`.
- **Not in any pip extra** — pinned instead in the repo's own `environment.yml` as a *conda*
  dependency: `pytorch>=2.6`, `torchvision`, and `detectron2@git+https://github.com/deepdoctection/detectron2.git`
  (their own fork, built from source — Detectron2 has no official PyPI wheel for recent
  torch/CUDA, so this is a from-source compile step, not a pip install).
- README states plainly: "Python ≥ 3.10, PyTorch ≥ 2.6, GPU recommended for fine-tuning."

**Offline / VRAM**: runs offline once weights are cached (HF Hub pulls at first use, then
local). No stated VRAM budget in the README; Detectron2 layout models + a DETR-family table
model (`hfdetr.py`) + LayoutLM (`hflayoutlm.py`) stacked together is a heavier resident set than
Marker+surya alone, and installing it means compiling a Detectron2 fork against Rab's exact
torch/CUDA pin — a real, non-trivial offline-build risk on a machine that already has one
finely-tuned marker-env. **Inferred**, not measured: no VRAM figure ships in the docs.

**Pipeline abstraction**: `dd.get_dd_analyzer()` — "orchestrates Scan and PDF document layout
analysis, OCR and document and token classification" as one call. This is the same shape as
Marker's own `convert_and_ship.py` orchestration; adopting it would mean replacing, not
augmenting, the existing pipeline.

**Evaluation tooling — the one genuinely interesting part.** `packages/deepdoctection/src/
deepdoctection/eval/` ships:
- `eval.py` — generic `Evaluator` class: "For a given model, a given dataset and a given
  metric, this class will stream the dataset, call the predictor(s) and will evaluate the
  predictions against the ground truth with respect to the given metric."
- `cocometric.py` — COCO-style mAP (object detection).
- `tedsmetric.py` — **TEDS (Tree-Edit-Distance-based Similarity)**, the standard table-structure
  fidelity metric from the IBM/PubTabNet lineage.
- `accmetric.py` — plain accuracy.
- Named benchmark in the docstring example: PublayNet (`get_dataset('publaynet')`).

This is a real evaluator with a real metric and a named denominator — not a bare claim. It is
the one piece of deepdoctection actually worth stealing, and it is not a dependency: TEDS is a
published, well-defined algorithm (tree edit distance between predicted and ground-truth table
HTML/structure), small enough to reimplement directly inside `fidelity_audit.py` without
pulling any of deepdoctection's stack. That is a concrete, scoped idea for whoever owns SPEC #1
(table reconstruction) — a fidelity score for *table structure specifically*, distinct from the
existing pymupdf-witness prose-fidelity score.

**Verdict: DISCARD as a framework** (GPU-heavy, from-source Detectron2 fork, replaces rather
than augments the pipeline, no offline-VRAM figure to hold it to). **Its TEDS metric is
IDEA_ONLY** — worth porting as code, not worth the dependency.

---

## 2. Unstructured-IO/unstructured (default branch `main`)

**License**: `LICENSE.md` — Apache License, Version 2.0. Clean. (`unstructured-inference`,
the layout-model sub-package it depends on for `hi_res` mode, is also Apache-2.0 per its own
`LICENSE` file.)

**What it pulls**: base install (`beautifulsoup4`, `lxml`, `spacy`, `numpy`, `rapidfuzz`, …) is
light and CPU-only. The document-layout path is opt-in via extras:
- `pdf`/`image` extras pull `unstructured-inference>=1.6.12`, which in turn supports both
  **Detectron2** and **YOLOX** as swappable layout backbones — its own README states
  "Detectron2 is required for using models from the layoutparser model zoo but is not
  automatically installed with this package," i.e. YOLOX (an ONNX-exportable, much lighter
  model family) is the practical default, Detectron2 an opt-in heavier alternative.
- The HF extra pulls `torch>=2.10.0,<3.0.0` and `transformers>=5.2.0,<6.0.0`.
- The `paddleocr` extra pulls `paddlepaddle>=3.3.0,<4.0.0` and `unstructured-paddleocr==2.10.0`
  — a **second** full deep-learning framework (PaddlePaddle, not PyTorch) alongside torch, if
  both OCR paths are wanted. That is real dependency weight: two DL frameworks resident at once
  for one pipeline stage.

**Offline / VRAM**: no VRAM budget stated for either backbone. YOLOX-family layout models are
typically small (tens of MB, ONNX-runnable on CPU) — lighter than deepdoctection's Detectron2
requirement — but this is **Inferred** from general knowledge of the YOLOX family, not measured
against a stated number in Unstructured's own docs; nothing in the fetched README or
pyproject.toml names a specific checkpoint size.

**Pipeline abstraction**: `partition()` — a single dispatch function, file-type auto-detected,
with a `strategy` parameter (`hi_res` / `fast` / `ocr_only` / `auto`) picking the backend per
call. Cleaner as an interface than deepdoctection's analyzer object, but it is again a
replacement abstraction for the whole convert stage, not a layer that sits inside Marker.

**Evaluation tooling**: none found in the fetched README or pyproject.toml. No metrics module,
no named benchmark, no denominator — unlike deepdoctection, there is nothing here to steal on
the measurement side.

**Verdict: DISCARD.** Two swappable DL backbones (YOLOX/Detectron2) plus an optional second
framework (PaddlePaddle) for OCR is dependency weight File Portal does not need — Marker/surya
already is the layout+OCR stack, and this would sit alongside it, not inside it, with no
evaluation tooling to justify the swap.

---

## 3. UglyToad/PdfPig (default branch `master`) — low-level access vs pymupdf

**License**: `LICENSE` at repo root — Apache-2.0 for PdfPig's own code, with BSD notices for
inherited PDFBox/FontBox contributions and the bundled Adobe AFM/CMap resources. Clean, and
notably it is the only one of the three repos in this lane whose LICENSE lists provenance for
what it absorbed from other projects.

**The actual question**: does PdfPig's low-level PDF access (render modes, marked content,
structure tree) give File Portal anything pymupdf lacks?

Repo layout (`src/`, confirmed via `api.github.com` contents listing, not guessed):
`UglyToad.PdfPig.Core`, `.DocumentLayoutAnalysis`, `.Fonts`, `.Tokenization`, `.Tokens`,
`.PdfPig` (main). Inside `.PdfPig/Graphics/Operations/TextState` there is a dedicated
`SetTextRenderingMode` operation class (`Mode = (TextRenderingMode)mode`) — genuine per-span
Tr-operator tracking. Inside `.PdfPig/Content` there is `MarkedContentElement.cs` (`Tag`,
`Properties`, `Children`, and a real `MarkedContentIdentifier` / MCID) plus a dedicated
`ArtifactMarkedContentElement.cs` — meaning PdfPig distinguishes real content from
Artifact-tagged content (headers/footers/watermarks/page furniture) at the marked-content level.
No `StructTreeRoot`/`StructElem` walker exists anywhere in the tree — PdfPig gives MCID and
marked-content tags, not a parsed structure tree with role mapping.

**So: does pymupdf actually lack this? Checked, not assumed** — this was the one place in this
lane where the prompt's own framing ("or is it Lane A's algorithms only") could have been wrong,
so it was run down rather than taken on faith:

- **Render mode**: pymupdf's documented `TextPage`/`get_text("dict")` API does *not* expose
  render mode (confirmed via the readthedocs `textpage.html` page — no `Tr` field). But
  `Page.get_texttrace()` — a real, separate pymupdf method, undocumented on that same page but
  real — returns a `"type"` field per span that *is* the render mode (0 fill / 1 stroke / 2
  fill+stroke / 3 invisible, etc.), confirmed by a PyMuPDF maintainer discussion ("Render mode 3
  is very often used by OCR"). **Verified directly** against Rab's own files (see §Measured
  below): pymupdf already carries this signal, no PdfPig or other library needed.
- **Marked content / MCID**: not exposed through pymupdf's high-level text API either, but the
  raw dictionary is reachable — `doc.xref_get_key(catxref, "StructTreeRoot")` /
  `doc.xref_object(n)` give manual access to the same `/StructTreeRoot`, `/MCID`,
  `/Artifact` machinery PdfPig wraps in classes. It is rawer (manual dictionary walking vs.
  PdfPig's typed `MarkedContentElement` tree) but present, and it is exactly the raw access
  spec #4 already used to build docs/52's ground-truth divergence measurement (2/57, 15/60 pages)
  on the WTPDF/ISO-32000-2 tagged specimens — i.e. this capability is not a gap, it is already
  in use elsewhere in the project.

**Verdict on the framework itself: DISCARD** — PdfPig is a .NET/C# library; nothing in it is
directly callable from Rab's Python pipeline (no Python bindings found, none searched-for
because the language barrier alone is dispositive), and everything it exposes at the raw-PDF
level, pymupdf already exposes too (more rawly for structure/marked-content, more cleanly for
render mode via `get_texttrace`). This confirms the prompt's second alternative: it is Lane A's
*algorithms* only, not new low-level access.

**One algorithm worth citing for spec #4 (reading order).** PdfPig's
`DocumentLayoutAnalysis/ReadingOrderDetector/UnsupervisedReadingOrderDetector.cs` does not use
XY-cut. Its doc-comment names two papers: Klampfl, Granitzer, Jack & Kern, *"Unsupervised
document structure analysis of digital scientific articles"* (§4.1), and Todoran, Worring,
Aiello & Monz, *"Document Understanding for a Broad Class of Documents."* The algorithm orders
blocks using **Allen's interval algebra** (spatial interval relations) plus optional render-order
(`TextSequence`) as a tie-breaker — a genuinely different, citable alternative to plain XY-cut
for whoever builds spec #4's ordering pass over Marker's now-persisted page+bbox block records.
Also present: `TextEdgesExtractor.cs` and `WhitespaceCoverExtractor.cs` — whitespace/column-gap
detectors, the classical Docstrum-family approach to column segmentation. None of this is
portable as code (C#, and a from-scratch reimplementation either way), but as a name-checked
algorithm family it is a legitimate pointer, distinct from the XY-cut approach spec #4's own
text already commits to.

---

## Measured on Rab's own specimen (the Verified claim above)

CPU-only, `marker-env`'s python 3.x, pymupdf 1.28.0 — pipeline was idle throughout, nothing GPU
touched. Script: `pymupdf_check.py` / `pymupdf_scan.py` in this leads/ folder.

**Positive case — clean born-digital text** (`Investment Valuation … Damodaran … Fourth
Edition, 2023.pdf`, the same source file behind the held Damodaran 4e specimen, page 10, 30
spans found): `get_texttrace()` present, every span carries `"type": 0` (normal fill) — matches
`manifest.json`'s own `"lane": "clean"` / `"ocr_font_trigger": null` classification for this
file. `metadata.producer` = `"calibre 8.4.0"` (this is a Calibre-repackaged copy of the Wiley
PDF, not the original — worth flagging separately, unrelated to this lane's question).
No `/StructTreeRoot` (`xref_get_key` returns `["null","null"]`) — expected, Calibre output isn't
tagged.

**Negative control — the same OCR-overlay book the SPEC names** (`BRAIN OF THE FIRM STAFFORD
BEER (WITH OCR) ISBN 13 9780471162131.pdf`, scanned across pages 0–8 for the first spans found):
`get_texttrace()` returns `"type": 3` (invisible OCR text) on **every single span found** —
15 of 15 on page 0, 255 of 255 on page 1, 4/4, 36/36, 92/92 on pages 5/7/8. Zero spans of any
other render-mode value in this sample. This is the clean two-value split (0 vs. 3) the SCAN-vs-
CLEAN lane (spec #3) needs, obtained from pymupdf alone, on the exact book named in the SPEC as
one of the S27 loop-detector planted pairs. It is not a full 10/10-anchor-corpus measurement —
that is Lane C's job and denominator, not this lane's — but it settles Lane E's own question:
pymupdf does not lack this signal, so nothing needs importing from PdfPig or any other framework
to get it.

No PDF file in this run was written to, mutated, or shipped anywhere; both files were opened
read-only from `C:/Users/Bndit/ml/library/drop/done/`.

---

## The Discard List

Every lead the mechanical triage (GROUND, stars/days-since-push/licence/language via GitHub
API) already rejected, with the fact that rejects it and whether anything inside is worth
stealing regardless.

| Lead | Rejecting fact | Worth stealing? |
|---|---|---|
| **zerox** | Cloud (vision-LLM API call per page) — violates offline-by-design | No unique idea: "render page → prompt a VLM for markdown" is the same architecture Qwen3-VL (already on the mechanical triage's *kept* list) would run locally; nothing zerox-specific to port. |
| **llama-parse-py** | Cloud (LlamaParse API wrapper) | No — thin API client, no algorithm inside to read. |
| **colpali** | Retrieval/embedding model (late-interaction page-image search), not a document-reconstruction tool — wrong problem for SPEC #1–#6 | No, for this lane's job. Might matter later if Rab builds vault *search* over the converted corpus, but that's a different commission than conversion fidelity. |
| **xy-cut-tree** | 2886 days since push (~8 years stale), no LICENSE file — legally unusable to derive from | No specific code to steal; XY-cut (Nagy & Seth 1984) is public-domain algorithm knowledge already, and spec #4's own text already points at implementing it directly over Marker's persisted block records — this repo adds nothing beyond the name. |
| **BobLd/DLA** | 1068 days stale, no LICENSE, C# | Same author lineage as parts of PdfPig's Docstrum-family layout code; whatever is useful in the approach is already reachable, with an actual license, through PdfPig's `DocumentLayoutAnalysis` package (§3 above) — no reason to touch this unlicensed repo directly. |
| **inuwamobarak/nougat** | Notebook (demo, not a library), 1055 days stale | No — it is a run-this-in-Colab wrapper around Meta's Nougat model; Nougat's image-to-markdown-transformer approach is already superseded for Rab's corpus by Marker+surya, and the notebook adds no technique beyond calling Nougat's own inference API. |
| **anyantudre/Florence-2** | Notebook, 792 days stale | No — Florence-2 is a general-purpose vision-language model (captioning/detection/grounding), not specialized for table or reading-order reconstruction; nothing document-specific in a usage demo. |
| **PDFImageRetriever** | 755 days stale, 3 stars | No — image extraction from PDF is already native to pymupdf (`page.get_images()`), already in the pipeline's own dependency; this tool has no additional capability. |
| **ReadingBank** | A dataset (Microsoft, backing the LayoutReader paper), not a runnable tool — no code to measure against Rab's specimens | Background literature only: LayoutReader frames reading order as a learned sequence-to-sequence relative-position problem. Contrast with §3's rule-based Allen's-interval alternative — worth knowing the learned approach exists, not worth building given spec #4 already commits to a geometric/rule-based route. |
| **qyhou/curated-DLA** | A curated list ("awesome-X" style), not code — nothing to run | No direct content; it is a pointer-of-pointers, useful only as a fallback bibliography if the five kept leads (spec #1–#5 candidates) all dead-end. |
| **go-exiftool** | GPL license (this project runs an Apache-only ecosystem) and Go (not bindable into the Python pipeline without a subprocess shim) | **Yes — the one real steal, and it's already redundant.** The Producer/Creator-metadata signal it would extract is exactly what `doc.metadata` already returns natively in pymupdf (confirmed above: `"producer": "calibre 8.4.0"` came back with zero extra dependency). Lane C should read this straight off pymupdf's existing `metadata` dict, not add exiftool as a dependency for it. |
| **YousifHisham table notebook** | See below — could not locate the repository at all | Unresolved; no content to judge. |

---

## The YousifHisham table notebook — UNREAD

Could not find it. This is reported as a failed fetch (UNREAD), not "no such thing exists."
What was tried:
- `api.github.com/users/YousifHisham/repos` (all types, per_page=100): **9 repos**, none
  PDF/table-related (`RTOS-`, `IoT-Telemetry-Protocol`, `Python-Compiler`,
  `University-Management-System`, `cse354-distributed-rag-llm`, `distributed-ai-inference`,
  `github-demo` [fork], `internet-programming-labs`, `pedestrian_classification`).
- `api.github.com/users/YousifHisham/gists`: empty.
- `api.github.com/search/repositories?q=user:YousifHisham`: 4 results, same non-table repos
  (search index apparently lags the full listing, but adds nothing new either way).
- `api.github.com/search/repositories?q=YousifHisham+table`: 0 results.
- WebSearch for `"YousifHisham" github`, `site:github.com YousifHisham ipynb table`, and
  `"Yousif" "Hisham" pdf table extraction notebook camelot pymupdf`: no exact-username match in
  any result; closest near-misses (`yousifh`, `yosefHesham`, `AhmedHisham552`, `hisham2k9`) are
  different people.

Possibilities, undetermined: the repo was renamed/deleted/made private between the mechanical
triage run and this read; the username in the GROUND brief has a transcription difference from
the real one; or it lives on a platform other than GitHub despite the triage line's
star/days-since-push framing implying GitHub. **Tag: Unknown.** Flagging back rather than
guessing at a substitute notebook.

---

## Residue

- `pymupdf_check.py`, `pymupdf_scan.py` — the two small scripts used for the Verified
  measurement above, left in this leads/ folder alongside other lanes' working files (this
  folder is evidently shared across lanes — `xycut_probe.py`, `lane_measurements.json`, and
  others from a different lane were already present on arrival and were left untouched).
- Did not chase exact model-checkpoint sizes (MB/GB) for deepdoctection's Detectron2/DETR/
  LayoutLM trio or Unstructured's YOLOX/Detectron2 backbones — neither repo's README or
  pyproject.toml names a concrete file size, and pinning one down would mean either running the
  installer (a real, uncontrolled download+compile on this machine) or trusting a third-party
  blog's number, which the GROUND rules for this lane don't ask for and the "no denominator, no
  trust" rule argues against guessing at.
- Did not attempt to actually install/build either framework (Detectron2-from-source, or the
  dual-torch/paddle Unstructured extra) — both verdicts are DISCARD before that point, so a
  build attempt would have spent real time confirming a conclusion already reached on license +
  dependency-weight + evaluation-tooling grounds alone.
- The Calibre-repackaged provenance of the Damodaran and Beer source PDFs (`producer: calibre
  ...`, not the original publisher's PDF) fell out of the measurement above as a side observation
  — noted here in case it matters to another lane, not chased further since it's off this lane's
  brief.
