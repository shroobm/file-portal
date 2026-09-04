# LANE F — Improving Document Layout Analysis Using Synthetic Data Generation and Convolutional Models

Pronina, Xia, Sheliah, Piatykop, Efremenko, Balalayeva. *Appl. Sci.* 16(6):3089, MDPI,
published 2026-03-23. CC BY. 29 pages, read whole (PYTHONIOENCODING=utf-8 `pdf_text.py` on
`applsci-16-03089.pdf`, pp.1-15 then 16-29, all clause/page cites below are page-of-29 unless noted).

**VERDICT: IDEA_ONLY** — a mathematically-specified bbox-placement algorithm (real, portable in
principle) wrapped in a paper that ships **no code, no weights, no dataset link**, that
**explicitly disclaims reading-order** as out of scope, and that never once models table-internal
structure. It does not touch Rab's two failing cases (dense empty-cell financial tables; reading
order) and there is nothing downloadable to run against his corpus. Kept as a citable idea for
"synthetic ground-truth layout" thinking, not as a build lead.

## Lead table

| Field | Value |
|---|---|
| name | Pronina et al. 2026, synthetic-layout-generation DLA paper (Appl. Sci. 16(6):3089) |
| verdict | IDEA_ONLY |
| tag | Observed (paper text, cross-checked against its own reference list) |
| licence_at_source | Paper: CC BY (Observed, p.1 masthead). Code/data: **none released** — Data Availability Statement (p.22, quoted below) names no repo, so no artifact exists to license. |
| offline_vram | Main training: NVIDIA GTX 1080 Ti, **11 GB VRAM**, batch 16 @ 640×640, 20 epochs (Observed, p.7-8 §2.4) — exceeds Rab's RTX 3080 10 GB nominally but batch/res are both reducible; paper never tests a smaller-VRAM config, so fit under 10 GB is **Unknown**. MinerU fine-tune stage: batch size 1 (Observed p.18) — trivially light, but paper reports no VRAM figure for it either. |
| test_quality | **Low.** One training run per of the 4 generation-strategy configs, no repeats, no variance/CI — paper's own admission (p.21): *"multivariate variance analysis and formal statistical significance testing were not performed."* The one real-document validation (MinerU/arXiv stage) reports **zero quantitative metric** — a single qualitative figure only (p.18, Fig.15). |
| headline_number_and_denominator | mAP@50 = 0.8836, mAP@50:95 = 0.7351, precision = 0.8429, recall = 0.7879 — all measured on the **1000-image validation split of the researchers' own best synthetic dataset** (median-split + shuffled-pool strategy; dataset = 10,000 generated layouts → 8000 train/1000 test/1000 val), single run, no held-out real corpus (Observed, p.15-16 §3.2). Never measured on DocBank's real test set, never on any table-specific subset, never on Rab's specimen. |
| what_it_gives_file_portal | Nothing runnable. No repo, no checkpoint, no dataset export — only equations (Eq.1-6) for a greedy bbox-placement geometry, reproducible in principle for the *placement* step only; the pixel/content-rendering step that turns placed boxes into an actual page image is never described (Unknown/gap, see residue). |
| smallest_measurement | Real-document fine-tune corpus: **83 train / 12 test / 24 validation images**, drawn from 10 arXiv papers (5 hand-annotated via Roboflow as ground truth, 5 held out for "system testing") — and for this exact stage, **no accuracy number is reported at all** (Observed p.17-18 §3.3; the only output is Fig.15, a qualitative recognized-blocks + generated-markdown screenshot). |
| spec_rows | #1 tables (NOT addressed — see below); #4 reading order (explicitly disclaimed by the paper itself); #6 MinerU bake-off (integration described, zero metric attached) |

## Measured — every number with its denominator (Rab's law, docs/34 / manual ch.18)

All of these are the paper's own numbers, re-stated here with the denominator the paper itself
gives (or the absence of one, marked BASELESS):

1. **Worst config** (constant-threshold division + threshold extraction), validation split of its
   own 1000-image val set: precision **0.8229**, recall **0.7551**, mAP@50 **0.8502**, mAP@50:95
   **0.6968** (Observed, p.14, §3.2, one run).
2. **Best config** (median division + shuffled-pool extraction), validation split of its own
   1000-image val set: precision **0.8429**, recall **0.7879**, mAP@50 **0.8836**, mAP@50:95
   **0.7351** (Observed, p.15-16, one run).
3. **"2-4% improvement" claim** (abstract; p.17; p.21 conclusions #2): re-measured by me as the
   absolute point-deltas between rows 1 and 2 above — precision +2.00pp, recall +3.28pp, mAP@50
   +3.34pp, mAP@50:95 +3.83pp. This is **absolute percentage-point delta on an already-fractional
   0-1 metric, not relative percent gain** (relative gain would run 2.4%–5.5%, a materially
   different-shaped claim) — the paper never states which it means; I disambiguated by computing.
   Flag for `measurement-language`: the paper's own "2–4%" is exactly the kind of bare improvement
   figure the project's law forbids quoting without stating basis — I did the computation so this
   lane's number carries its basis, but the paper's own text (abstract, conclusions) does not.
4. **Comparison to Ultralytics' own YOLO11m baseline** "mAP@50 of 0.50-0.52... reported by
   Ultralytics for YOLO11m when trained on extensive multi-class datasets [46]" (p.19) — ref [46]
   is the Ultralytics YOLO11 GitHub repo (COCO benchmark table), an **80-class natural-image
   detection task**, not a document-layout task. Different classes, different domain, different
   image distribution. This comparison is presented as if it were a fair baseline; it is not — the
   two mAP@50 numbers do not share a denominator (different class count, different dataset). I
   tag the paper's own framing of this comparison **BASELESS AS PRESENTED**.
5. **Comparison to LayoutLM** "precision of 0.7677 and recall of 0.8195 [38]... on the full DocBank
   dataset" vs. the paper's own 0.8429/0.7879 (p.19) — ref [38] is LayoutLM (Xu et al. 2020), a
   token/sequence-classification model evaluated under an entirely different protocol (not IoU-
   based object-detection P/R at all), on the *full* DocBank (400k pages) vs. this paper's
   resampled-and-regenerated 10k-layout subset. Not a common denominator. Same flag: **BASELESS AS
   PRESENTED** — the paper juxtaposes two numbers from incompatible evaluation protocols without
   saying so.
6. **"previous studies reported improvements of 2.1% on financial documents [9] and a 3.6%
   increase in mAP [11]"** (p.19) — cited with no restatement of ref [9]/[11]'s own base metric or
   n. **BASELESS AS PRESENTED** in this paper's text (their denominators live only in the cited
   papers, not here).
7. **Table 2's own self-summary**: "Using efficient YOLO11m with input data optimization to
   achieve mAP **0.85–0.90**" (p.20) — the paper's own measured ceiling in the body text is mAP@50
   **0.8836** (row 2 above). The summary table overstates its own measured result by rounding up
   to 0.90. Internal inconsistency, Observed by cross-reading Table 2 against §3.2.
8. **DocBank citation mismatch** (Observed, cross-checked in-text ref number against the numbered
   bibliography): body text says *"The DocBank dataset [39] was selected..."* (p.5, §2.1) — but
   reference **[39]** in this paper's own reference list (p.28) is *"Nguyen, H.G.; Bründl, P.;
   Franke, J. Synthetic Image Data Generation for Wiring Harness Component Detection Using Machine
   Learning"* — completely unrelated (industrial component detection, not document layout). The
   actual DocBank citation (Li et al., *DocBank: A Benchmark Dataset for Document Layout
   Analysis*, arXiv:2006.01038) is reference **[47]** in their own list. This is a real citation
   bug in the published paper, not a PDF-extraction artifact — verified by reading both the running
   text mention and the full numbered reference list.
9. **DocBank corpus size as used**: 400,000 images / ~50 GB total (Observed p.5) → subsampled to
   50,000 train + 10,000 test/val (~7 GB) because a GTX 1080 Ti pass over the full set was
   infeasible (Observed p.5). The *generated synthetic* datasets are a further, separate
   resampling: 4 strategies × 10,000 layouts each × 8000/1000/1000 split (Observed p.8 §2.3) — two
   different "10,000" numbers in this paper refer to different populations; don't conflate them.

## Extraction (a)-(e), per the brief

**(a) The generation model — what's controllable, what's fixed (Eq.1-6, pp.5-6, §2.2):**
- Elements `e` (real bboxes, `w(e)`/`h(e)` normalized 0-1) are **read from DocBank**, not invented
  from a parametric distribution — this is a *rearrangement/recombination* algorithm over real
  element sizes, not a generative model of new element geometry. **This is an important
  distinction the paper's own language ("mathematical model of data generation") tends to blur.**
- `f(e)` (Eq.2) splits elements into small/large by either (i) a **fixed threshold** — width or
  height < 0.05 of page — or (ii) the **dataset median** width/height. Controllable: which of the
  two splitting rules to use. Fixed: the 0.05 threshold value itself (not swept/ablated).
- `g(E)` (Eq.3) sets how many small vs. large elements land in the final layout: either "mixing"
  (use the real counts `Ne,sm`/`Ne,lg` as observed) or a fixed 1%/99% split (`Nsm=0.01·Ne`,
  `Nlg=0.99·Ne`). Controllable: which rule; fixed: the 1%/99% constant.
- Placement (Eq.4-6): first element's center placed uniformly at random inside margin bounds
  (Eq.4); each subsequent element placed into the Cartesian-product grid cell (formed by the edges
  of already-placed elements) that (i) has zero IoU with existing elements and (ii) maximizes
  occupied-area ratio `F = Ae/Ac` (Eq.6) — a **greedy, not globally optimal**, packing (paper says
  so explicitly, p.6). Termination: no valid cells remain, no elements fit, or an unstated
  "predefined limit for small elements" is reached — **that limit's numeric value is never given**.
  Complexity stated as `O(Np·NE·Nc)` (paper's own claim, not independently re-derived by me).
- **Unknown/undocumented**: how the *pixel content* of each placed box is actually rendered into
  the final training image (text? cropped real content? solid color?). Figures 5 and 10 show
  populated-looking pages, but nowhere in the extracted 29 pages is a rendering/compositing step
  described. This gap means the paper is **not fully reproducible from its equations alone** — the
  geometry algorithm is specified; the appearance-generation step is not.
- `Nc` ("number of candidate fragments") is named as an input parameter but its actual run value
  is never stated.

**(b) Architectures, sizes, VRAM (pp.7-8 §2.4, p.18 §3.3):**
- Exactly **one** architecture used throughout: **YOLO11m** (Ultralytics implementation). No other
  CNN/transformer is trained in this paper (others appear only in the related-work table, Table 2,
  as citations, not as tested baselines here).
- **No parameter count or FLOPs figure for YOLO11m appears anywhere in this paper's text.** I did
  not import an outside number to fill this gap — tagging it **Unknown, paper-silent**, not
  answered by public Ultralytics docs I might recall (those weren't sourced from this document).
- Main training: batch 16, 640×640 input, 20 epochs, SGD, LR 0.002→0.0001 cosine, weight decay
  5e-4, on an **11 GB** GTX 1080 Ti (Observed p.7-8). Fine-tune stage: LR 0.05→0.0001, batch 1
  (Observed p.18) — no VRAM figure given for this smaller run.
- CPU-viable or fits-8GB: **not tested by the paper at all** — no ablation on batch size, input
  resolution, or a smaller GPU is reported.

**(c) Every metric with its denominator:** see the "Measured" section above (items 1-3, 9) — no
new numbers beyond what's captured there. Datasets used: DocBank only (own re-sampled/re-generated
subsets); no PubLayNet, no DocLayNet anywhere in this paper.

**(d) The MinerU validation (pp.17-18 §3.3):**
- Mechanism: load the synthetic-pretrained YOLO11m weights into MinerU's YOLO-based
  layout-detection module, let MinerU auto-redefine the final detection head to the target class
  count (via class list/order pulled from the PDF-Extract-Kit docs, ref [49]), fine-tune.
- Corpus: 10 recent arXiv papers, 5 hand-annotated with Roboflow as ground truth, 5 used for
  "system testing" (method unspecified). Images: 83 train / 12 test / 24 validation.
- **Result: zero quantitative metric.** The entire "validation" is Figure 15 — a single
  screenshot of recognized blocks plus a generated Markdown file. The paper says outright (p.18)
  that this stage "was not intended to provide exhaustive testing" and was only meant to
  "illustrate practical applicability" — i.e., the authors themselves label it non-rigorous.
- **Nothing about MinerU's tables specifically, nothing about reading order specifically** — the
  fine-tune targets whatever generic layout classes PDF-Extract-Kit defines (never enumerated in
  this paper's text), evaluated qualitatively only. Direct answer to the brief's question: this
  paper's MinerU validation says **nothing usable** about MinerU's table-handling or reading-order
  behavior.

**(e) "Layout-aware chunking for RAG" — method or sentence?**
**One sentence.** It appears exactly once, in the "Featured Application" call-out box on p.1:
*"...layout-aware chunking for search-augmented generation in large language models."* I read all
29 pages looking for any chunking algorithm, chunk-boundary rule, retrieval evaluation, or even a
second mention — there is none. No method, no experiment, no metric attached to "chunking"
anywhere in Introduction, Methods, Results, Discussion, or Conclusions. **Reported as baseless
because it is baseless** — a single unelaborated marketing-style sentence in the abstract-adjacent
front matter.

## Rab's angle: is this a planted-truth oracle for #1/#4?

**Partially, and only for the narrowest slice.** The greedy placement algorithm (Eq.4-6) *does*
produce bboxes+classes whose ground truth is known by construction, since you placed them — that
part genuinely could seed a **layout-detection mAP oracle** (spec #6-adjacent: "does the detector
find the boxes I put there"), IF reimplemented (equations are specific enough for that one piece)
and IF you supply your own content-rendering step (undocumented here).

It does **not** give you what Rab named as the two things he cares about most:
- **#1, tables**: DocBank's `table` class (used here only as one more opaque bbox category with no
  cell/row/column modeling) is placed exactly like any other block — no internal structure is
  generated or verified. Zero help for dense, empty-cell financial tables.
- **#4, reading order**: the paper says so itself (p.21, Discussion, limitations): evaluation was
  *"limited to standard object detection metrics..., without assessing structural coherence or
  reading order reconstruction."* The greedy placement *order* (large elements first, voids filled
  with small ones) is a packing order, not a reading order, and the paper never claims otherwise.
  This directly closes the door on using this generator as a reading-order oracle without
  additional, unvalidated assumptions layered on top by whoever ports it.

## Residue

- Read all 29 pages via the mandated `pdf_text.py` extraction (1-15, then 16-29); no OCR needed,
  text layer clean, no extraction artifacts noted beyond hyphenation/line-wrap that didn't affect
  meaning.
- No GPU used for this lane; no code executed; nothing under `file-portal` touched.
- The DocBank mis-citation ([39] vs. correct [47]) and the Table-2-vs-§3.2 self-inconsistency
  (0.85–0.90 claimed vs. 0.8836 measured) are both **Observed defects in the published paper
  itself**, found by cross-reading the paper against its own reference list and its own results —
  not inferred, not assumed; anyone can re-check p.5/p.28 and p.15-16/p.20 respectively.
- I did not attempt to independently verify Ultralytics' or LayoutLM's actual published numbers
  (refs [46], [38]) against their own source papers — I only flagged that the *comparison as this
  paper presents it* lacks a stated common denominator. Confirming or refuting refs [46]/[38]'s own
  numbers would need pulling those papers, which I did not do (out of scope for a single-paper
  lane; flagging for the coordinator in case a future circle wants it).
- No YOLO11m parameter count is stated in this paper; I deliberately did not import one from
  memory of Ultralytics' public docs to avoid dressing an outside recollection as this paper's
  claim — if the coordinator wants that number for the spec sheet, it should be sourced separately
  and tagged as such.
- Did not attempt to reimplement or test the placement algorithm — this is a reading lane, not a
  build lane, per the brief.
