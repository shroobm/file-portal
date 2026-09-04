# Lane A — Reading order without a tree (spec #4) — and the Detect-Order-Construct paper

GROUND for this lane: `C:/Users/Bndit/Projects/file-portal` read-only. Interpreter for every
measurement below: `C:/Users/Bndit/ml/marker-env/Scripts/python.exe` (pymupdf 1.28.0 / MuPDF
1.29.0, `TEXTFLAGS_DICT`/`TEXT_COLLECT_STRUCTURE` as in probe_k_order.py). No GPU touched by
anything in this lane — every script here imports only `pymupdf`, `re`, `difflib`; no `torch`.
Scripts written this session live in
`C:/Users/Bndit/AppData/Local/Temp/claude/.../scratchpad/leads/`: `xycut_probe.py`,
`xycut_v2.py`, `xycut_v3_net.py`, `diag.py`, `diag_p0.py`. Nothing in `file-portal` was touched.

## 1. The paper — arXiv 2401.11874v2, "Detect-Order-Construct" (Wang/Hu/Zhong/Sun/Huo, MSRA)

`Observed`, read in full (35 pp, `pdf_text.py`).

**What the Order stage actually is.** Not a geometric rule. It is a *trained* multi-modal
relation-prediction transformer: a shared CNN backbone (ResNet-18/50) feeds visual embeddings
per text-line/page-object; BERT-base supplies text embeddings; a 2D positional embedding encodes
the bbox; the three are concatenated and pushed through a lightweight Transformer encoder; a
dependency-parsing-style relation head then scores, for every ordered pair of regions, "is B the
successor of A" and the arg-max chain becomes the reading order (§4.3, eqs. 10-17). Table of
Contents construction (§4.4) reuses the same machinery plus RoPE positional encoding and a
tree-insertion algorithm (Algorithm 1). Training: PyTorch 1.10 on **8× Nvidia Tesla V100 32GB**
(§5.2) — nothing about this is a "few dozen lines," and nothing about it runs on a 3080.

**Headline number, with its denominator (Table 6, Comp-HRDoc benchmark):** Text Region REDS
**0.9319**, Graphical Region REDS **0.8637**, vs. the paper's own cited rule-based XY-cut
baseline (Quirós/Vidal, "Lorenzo et al." row) at **0.7741 / 0.8583** on the same benchmark. REDS
= `1 - D/N` where D is Hungarian-matched Levenshtein edit distance between predicted and
ground-truth reading-order sequences and N is the unit count (text-lines + graphical objects);
the benchmark itself is **500 held-out documents** from HRDoc-Hard (Comp-HRDoc test split,
§5.1). So the paper's own numbers say a rule-based XY-cut baseline already gets ~77-86% of the
way there on their benchmark, and the trained model buys another ~7-16 points — informative for
sizing what a geometric approach can realistically deliver, but not a reason to expect XY-cut to
be *right*, only *in the right neighborhood*, which is exactly what section 2 below re-measures
on Rab's own specimens.

**Is there code or weights beyond the benchmark?** `Verified`, two independent WebFetches against
`github.com/microsoft/CompHRDoc` (main README) and its `UniHDSA/` subfolder README:
- Top-level repo: `UniHDSA/`, `assets/`, `evaluation/`, `CompHRDoc.zip`, `LICENSE` (**MIT**),
  `README.md`. Released: benchmark **annotations** (zip) and an **evaluation** tool. Explicitly
  NOT released: the document images (redirect to HRDoc-Hard's own restricted download).
- `UniHDSA/README.md`, quoted verbatim: **"Due to company policy, we cannot release the code
  for the model. However, we provide the detailed configuration including the model
  architecture, training hyperparameters, and data processing methods. We also provide the code
  for the evaluation of the model."**

So: no training code, no inference code, no weights, anywhere in the linked repo. `UniHDSA` is
built on `detrex` (a Detectron2-family object-detection library) per its own README, which
confirms the "config + eval only" reading rather than contradicting it.

**Verdict for the paper as a component:** `DISCARD`. There is nothing installable — the model
does not exist outside Microsoft's internal repo, and even if it did, retraining it from
scratch would need V100-class multi-GPU compute this project does not have. What survives is
citable knowledge, already spent in §2-3 below: (a) the paper's own related-work section
(§2.2, ref. [50], [53], [59]) is the primary source for XY-cut/topological-sort/bidimensional-
relations as the *recognized-but-failure-prone* rule-based family, quoted at 15 words: **"these
rule-based methods can be prone to failure when confronted with out-of-domain cases"** — which
is exactly the failure mode measured below; (b) the REDS metric design (paragraph-boundary-
aware Levenshtein + Hungarian matching over two independently-scored group types) is a
genuinely better reading-order metric than probe_k's character-stream compare, worth stealing
as a *methodology* if File Portal ever wants a graded (not binary) reading-order score.

## 2. PdfPig's Document Layout Analysis wiki — portable algorithms, not a dependency

`Observed` via WebFetch of `github.com/UglyToad/PdfPig/wiki/Document-Layout-Analysis` (an
AI-summarized fetch, not hand-parsed — flagged, not independently re-verified against raw wiki
markdown this session). Confirmed classes and what each needs:

| PdfPig class | family | input |
|---|---|---|
| `RecursiveXYCut` | top-down recursive decomposition | word bboxes |
| `DocstrumBoundingBoxes` | bottom-up nearest-neighbour clustering | word bboxes |
| `UnsupervisedReadingOrderDetector` | graph/interval-algebra (Allen's relations, X/Y) | text-block bboxes |
| `RenderingReadingOrderDetector` | trivial — sorts by each block's average `Letter.TextSequence` | letter render order |
| `DefaultReadingOrderDetector` | no-op | — |

These are **portable algorithm descriptions**, C# under Apache-2.0 (license already logged in
GROUND's mechanical triage) — not something to FFI into a Python pipeline for a ~50-line
algorithm. `RecursiveXYCut` is what §3 below reimplements natively in Python and measures.
`DocstrumBoundingBoxes` and `UnsupervisedReadingOrderDetector` (interval-algebra between block
edges, closer to Breuel's and Aiello/Smeulders' topological-sort family the paper cites as [50]
and [51]) were **not** measured this session — they are candidates a nearest-neighbour or
interval-algebra approach might handle differently than pure axis-aligned gap-cutting,
specifically on the cover/title-page bbox anomalies §3 found (see residue).

**Verdict:** `MEASURE_NEXT` for Docstrum/interval-algebra specifically (unmeasured, plausible on
the failure mode found); `DISCARD` for treating PdfPig itself as a dependency (C#, no reason to
FFI when the ~55-line core algorithm ports natively).

## 3. THE MEASUREMENT — recursive XY-cut over J24 block bboxes vs. declared vs. Marker's baseline

### 3.0 Mechanism check first: what does Marker actually use for order today?

`Verified`, read `marker/processors/order.py` and `marker/builders/layout.py` directly
(`C:/Users/Bndit/ml/marker-env/Lib/site-packages/marker/`), and `surya/layout/__init__.py` /
`schema.py` (`.../site-packages/surya/`). Correcting an assumption in the commission brief:
Marker does **not** run an XY-cut, and its "geometric order" is not really geometric.

- `surya.layout.LayoutPredictor` DOES emit a `position` field per detected box — but it is
  `position=z`, the plain enumeration index of an **autoregressive token-decode sequence** (a
  vision-language foundation model emitting `(box, label)` tokens one at a time,
  `surya/layout/__init__.py:97`). It's a learned order, not a geometric rule, and it is opaque.
- Marker's `LayoutBuilder.add_blocks_to_pages` inserts blocks into `page.structure` sorted by
  that surya `position` — but then `OrderProcessor` (`marker/processors/order.py`) **overwrites
  it** for every page that is not OCR'd and not `layout_sliced`: it re-derives each block's
  order key from the **average span position pdftext already assigned it**, and blocks with no
  spans (pure images) get interpolated relative to their nearest neighbour. Surya's learned
  `position` only survives for the rare `layout_sliced` case (an over-tall page tiled for the
  layout model).
- So for ordinary single-page born-digital text — nearly everything in Rab's corpus — Marker's
  final order is **pdftext's own span order**, i.e. whatever internal sequencing pdftext (MuPDF)
  assigns while parsing the content stream. `probe_k_order.py`'s `geom_frags()` (pymupdf
  `get_text("dict")` raw block order) is a faithful proxy for this, confirmed by construction —
  both are "trust the PDF's own internal parse order," neither is geometry-first.

This matters for the verdict: spec #4 is right that there is no XY-cut in the pipeline today,
but wrong (as commissioned) to call the existing baseline "geometric" — it is stream-order, and
that distinction is exactly why §3.2's result below is not obvious in advance.

### 3.1 The algorithm

`xycut_probe.py::xy_cut()`, 55 lines, CPU-only, no imports beyond `pymupdf`/`re`/`difflib`: the
textbook Nagy/Seth top-down XY-cut (Meunier 2005, ref. [53] in 2401.11874v2) — project block
bboxes onto Y, cut at the first whitespace gap ≥4pt if one splits the set into two non-empty
groups, recurse; else project onto X and cut there; base case (no internal gap either axis) sorts
by row (`round(y0/3pt), x0`). Input: `pymupdf.Page.get_text("dict")` type-0 blocks — the same
shape as J24's persisted `marker_blocks.py` bbox field (`(x0,y0,x1,y1)`), so this ports directly
onto J24 block records without modification; pymupdf blocks were used here only because J24
`.blocks.json` sidecars exist solely for already-converted corpus books (none of which carry a
structure tree per docs/52's 19/4,307 finding — see §3.4), so there is no ground truth to score
J24 output against. WTPDF/ISO32000-2 (the only ground-truthed specimens) were never run through
Marker/J24, so `get_text("dict")` is the correct and only available stand-in — not a deviation.

### 3.2 Negative controls (run before trusting any real-page number)

Both `Verified`, re-run, `xycut_probe.py` output quoted:
1. **Determinism self-compare**: `xy_cut` on the same 7-block input twice → identical order.
   `True`.
2. **Planted two-column page** (the actual regression test): two full-height, contiguous,
   zero-internal-gap 3-row columns, 50pt gutter, fed in column-interleaved order `[L0,R0,L1,R1,
   L2,R2]`. A naive y-then-x sort (what a lazy "just sort by position" implementation would do)
   ties on identical y0 and falls back to input order: `['L0','R0','L1','R1','L2','R2']` —
   **wrong** (correct? `False`). `xy_cut` correctly fails the Y-gap test (no gap — both columns
   span the same y-range) and falls through to the X-gap test, finds the 50pt gutter, and
   returns `['L0','L1','L2','R0','R1','R2']` — **correct** (correct? `True`). This is the planted
   input/known-output test that would catch a real regression (e.g. someone "simplifying" the
   Y-before-X cut order, or dropping the gap-midpoint cut in favour of naive sort, breaks it
   immediately and visibly).

### 3.3 The real measurement — WTPDF 1.0 (57 pp) and ISO 32000-2 (60 pp)

Ground truth (declared order) and the "geometric"/stream-order baseline reused **verbatim** from
`prototypes/pdf-structure/probes/probe_k_order.py`'s `declared_frags()` / `geom_frags()`
(same character-stream, same-charset-resequencing test, same `NORM`) — not re-derived, so this
result composes with docs/52's already-`Verified` 2/57 and 15/60 numbers rather than duplicating
a different methodology under the same name.

**v1 (plain XY-cut, no special-casing) vs. declared order:** WTPDF disagrees on **55/57** pages;
ISO disagrees on **59/60**. Dramatically worse than the stream-order baseline's 2/57 and 15/60.
Diagnosed by dumping one page (`diag.py`, WTPDF p.6): the *entire* divergence on that page is one
running-footer block — content-stream-first AND declared-first, but geometrically at the bottom
of the page (y≈805 of ≈842) — so a pure-geometry sort puts it last, wrong both ways.

**v2 (margin-band header/footer excluded from the cut, re-spliced at their stream position — the
obvious fix once the above is seen):** WTPDF collapses to **2/57**, exactly matching the
stream-order baseline. ISO improves to **18/60** — still *worse* than the 15/60 baseline.

**The number that actually answers spec #4 (`xycut_v3_net.py`):** on precisely the pages where
Marker's existing baseline is *already wrong* against the declared order — WTPDF pages `[0, 56]`,
ISO pages `[0, 2, 9, 17, 18, 19, 21, 22, 23, 24, 25, 26, 27, 28, 34]` — margin-excluded XY-cut
fixes **0 of 2** on WTPDF and **0 of 15** on ISO, while breaking **3** ISO pages (`[15, 38, 47]`)
that the simple stream-order baseline got right for free. **Net: 0 pages gained, 3 pages lost,
across 117 measured pages.**

**Why, diagnosed on the actual pages (`diag_p0.py`):** the residual failures on both specimens
are **cover/title pages**, not multi-column body text — WTPDF p.0 (title block, version stamp,
license line) and ISO p.2 (the ISO cover: "INTERNATIONAL STANDARD" banner, part number, edition
line, bilingual title block, copyright). ISO page 2's raw geometric extraction even shows a
block with **y0 = -20.7** (a stylized/oversized title graphic bbox bleeding off-page) — no
axis-aligned gap rule fixes a block whose logical position and visual bbox are this decoupled.
Neither WTPDF nor ISO 32000-2 contains genuinely multi-column running body text in the pages
sampled, so **the actual case XY-cut is built for was never exercised by either ground-truthed
specimen** — the two available structure-tree specimens happen to be exactly the worst-case
demonstration for this algorithm (single-column body + decorative cover pages), not because the
algorithm is wrong in general but because these two documents don't contain its target failure
mode.

### 3.4 Why this can't be re-measured on Rab's real converted corpus

`Verified` (docs/52, VERIFIED.md §6, re-quoted not re-derived): **19 pages of 4,307 (0.44%)** of
Rab's actually-converted library reach a conforming structure tree; both 1,300-page Damodarans
have none. So a ground-truthed reading-order measurement on Rab's *own* books, at any scale, is
not currently possible — WTPDF/ISO are the only specimens with a declared order to check against,
by construction, and both are exhausted by this measurement.

## 4. What this lane actually recommends

- **Do not** adopt the paper's model (no code exists to adopt) — `DISCARD`.
- **Do not** ship a naive/margin-heuristic XY-cut over Marker or J24 blocks expecting it to beat
  the existing stream-order baseline "for free" — measured net **negative** on the only
  ground-truthed specimens available (0 fixed / 3 broken) — `DISCARD` as measured.
- **Do** keep the reusable pieces: `xycut_probe.py`'s `xy_cut()` is ~55 lines, portable onto
  J24's block bboxes verbatim, has a real negative-control regression test, and is a legitimate
  starting point *if* a genuinely multi-column ground-truthed specimen is ever found or built —
  `MEASURE_NEXT`, specifically gated on finding/constructing that specimen (candidates: hunt the
  27/56 Downloads-corpus tagged files for a two-column layout, or hand-build a synthetic
  multi-page ground truth the way §3.2's negative control already does at page scale).
- **Do** consider the REDS metric shape (paragraph-boundary-tagged Levenshtein + Hungarian
  matching, two independently-scored region types) over probe_k's binary same/reorder compare,
  the next time reading order needs a *graded* score rather than a yes/no — `IDEA_ONLY`, cheap to
  build, not built this session.
