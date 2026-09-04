# Lane B — Tables in born-digital untagged PDFs (spec #1)

GROUND. File Portal, Marker 1.10.2 + surya 0.17.1. Read-only against
`C:/Users/Bndit/Projects/file-portal`; all execution is CPU-only, on files already on disk.
No GPU touched, pipeline stayed idle throughout.

## 0. DEVIATION — the mission's own premise does not match the specimen (report this first)

The commission said: *"Measure: SYM-056's 61 unterminated `\begin{array}` -> how many with
candidate X. Specimen: held Damodaran 4e. Rab's failing pages are dense financial tables with
empty cells."* I ran `latex_balance` (verbatim copy of `fidelity_audit.py:373-424`, SYM-056's
own report-only method) against the actual held bundle
(`C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e/Investment Valuation, University Edition _
Tools and -- Aswath Damodaran -- Four.md`, 29,697 lines, source_sha256 `14c66834b...`).

**Observed: Damodaran 4e carries 3 unterminated `\begin{array}` opens, not 61** —
`{"array": {"begin": 87, "end": 84, "unterminated": 3, "stray_end": 0}}`, `unterminated_total`
across ALL LaTeX envs (array/align*/aligned/bmatrix/cases) = 5 of 173 begins seen.

**Verified (independent cross-check, not just my own arithmetic):**
`SYMPTOM-INDEX.md`'s own SYM-056 row, written before this session, already recorded *"the
anchored `Investment Valuation` bundle reads begin=43 end=40 (**delta 3**, already vaulted)"*
— a different absolute begin/end pair (their literal count vs my whitespace-aware `\s*`
regex) but the **same delta of 3**. Two differently-shaped methods agree. The **61** (and the
nearby 60/40 figures in the same SYMPTOM-INDEX row) belong to a **different book — Ashby's
`Cybernetics: A Very Short Introduction`** ("In Ashby's 112 chunks: 28 chunks unbalanced...
corpus totals begin=79 vs end=39, DELTA 40 unterminated... `2401.11874`-unrelated specimen
`i=105`: `$$\\begin{array}{c*36}$$`"). Damodaran's own delta has been small (3) since before
this session and is still 3 now — **it never was 61, and it never was Damodaran's**.

**Second, sharper deviation — the "dense financial tables with empty cells" framing doesn't
fit the array pathology either way.** I extracted the LaTeX colspec (`\begin{array}{<spec>}`)
for all 87 occurrences and measured column-count width. Damodaran's colspecs are **all narrow**
(65 of 87 are `{lll}`/3-column, 17 are 2-column, 4 are 1-column, 1 uncaptured) — **zero** match
SYM-056's signature degenerate shape (Ashby's `{cccccccccccccccccccccccccccccccccccc}`, 36
identical repeated columns). Damodaran's `\begin{array}` blocks read as small inline equation
systems (piecewise formulas, 2-3 column layouts), not mis-recognized wide financial grids.

**What IS true and dense-financial-table-shaped in this book:** the body carries 4,580
markdown pipe-table rows (`|...|`) across 235 distinct pages, and 4,712 "adjacent-empty-cell"
markers (`| |`) across 217 pages — genuine dense, empty-cell-heavy financial tables, just not
expressed as unterminated LaTeX. **This is the real spec-#1 target in this book; SYM-056's
counter measures something else (math-mode LaTeX hallucination) that happens to share a
`\begin{array}` regex with real tables but is a different failure with a different owner.**
Tag: **Observed**, both counts reproducible from the script below.

Residue for whoever runs the bake-off: score candidates against the **pipe-table pages**
(list below), not against the unterminated-array line list — the array list is real but small
and mostly benign in this specimen.

## 1. The measurement (method, script, negative control)

Script: `C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/map_array_pages.py`
(latex_balance reimplemented verbatim from `fidelity_audit.py:373` — no pymupdf/rapidfuzz
import needed for this CPU-only text measurement) +
`array_colspecs.py` + `table_empty_cells.py` in the same directory. Raw JSON outputs sit
alongside them (`array_page_map.json`, `array_colspecs.json`, `table_empty_cells.json`).

**Page mapping method and its own limit (state this, don't hide it):** the body carries
`<span id="page-N-M"></span>` anchors, but they are emitted only where Marker placed a
cross-reference target (empirically: immediately before an embedded image/figure — e.g. line
943 `<span id="page-41-1"></span>![[assets/_page_41_Figure_3.jpeg]]`), **not one per physical
page**. 1,277 anchors of that exact 2-group shape are found for 1,377 pages, monotonic in the
1,277 checked (0 order violations), but the gaps between them are uneven — the largest is 839
lines (front matter, before the first image on page 34; my own negative-control check caught
this: a naive "page 1" bucket wrongly absorbed the entire pre-page-34 front matter, including
457 ToC pipe-rows, because nothing anchors it more precisely). **So: page numbers below are
"nearest preceding image-anchor page," accurate near any anchor, and only as precise as the
local gap elsewhere** — a few pages of slop is possible in text-only stretches. The precise
version needs `windows-converter/marker_blocks.py`'s per-block page+bbox persistence (J24,
cited in GROUND spec #4); **no such blocks JSON exists in this held bundle's directory**
(checked: only `manifest.json` + the one `.md` + `assets/`) — that infrastructure wasn't run
for this conversion. Tag: **Observed** (method), **Unknown** (exact page for any one occurrence
that falls in a large gap).

**Negative control performed:** the `latex_balance` function's *other* four environments
(`align*`, `aligned`, `bmatrix`, `cases`) do NOT uniformly read "unterminated" the way `array`
does — `aligned` (56 begins/58 ends) and `cases` (0/1) show only **stray closes**, zero
unterminated opens; only 1 of the other 4 envs (`bmatrix`, 1 of 2) is actually unterminated.
This is the control the mission asked for: a method that flags everything indiscriminately
would be worthless, and this one doesn't.

### The 3 unterminated `\begin{array}` (the literal "SYM-056 count" for this book)
| line | nearest page anchor |
|---|---|
| 8776 | 439 |
| 17966 | 832 |
| 22953 | 1057 |

### Pages carrying the most `\begin{array}` opens overall (68 distinct pages, 87 opens)
page 553 (4) · 752, 1118 (3 each) · then 13 pages with 2 each (396, 450, 536, 559, 560, 569,
661, 748, 785, 824, 877, 1057). All narrow colspecs (see §0) — likely legitimate math, not
mis-rendered tables.

### Pages carrying the densest / emptiest markdown tables (the real spec-#1 target)
By empty-cell-marker count (financial-statement shape — many blank cells in a wide grid):
**page 805** (130 empty markers / 43 rows) · **page 564** (122/35) · **page 757** (101/21) ·
**page 779** (95/32) · **page 579** (90/20) · **page 888** (83/34) · **page 1012** (82/32) ·
**page 854** (81/45) · **page 860** (76/39) · **page 600** (73/38). By raw row count: page 150
(81 rows), page 404 (53), page 698 (48), page 970 (46), page 854 (45). **Hand these page
numbers (± a few, per the anchor-gap caveat above) to whoever renders crops for a visual
bake-off — I rendered nothing, per instruction.**

## 2. Candidates read (source, not vendor prose)

### 2a. PaddlePaddle/PaddleOCR — PP-StructureV3 / SLANet family
Fetched: `docs/version3.x/module_usage/table_structure_recognition.md`,
`docs/version3.x/pipeline_usage/PP-StructureV3.md`, `LICENSE` (all `main` branch, raw.
githubusercontent.com). **Verified** — LICENSE file quoted directly: "Apache License /
Version 2.0, January 2004" (matches GROUND's mechanical-triage row).

**Model sizes (module doc's own comparison table, quoted):**
| model | size | reported "accuracy" |
|---|---|---|
| SLANet | 6.9 MB | 59.52 |
| SLANet_plus | 6.9 MB | 63.69 (better on borderless) |
| SLANeXt_wired | 351 MB | 69.65 (border-line-aware) |
| SLANeXt_wireless | 351 MB | 69.65 |

Denominator for "69.65/63.69/59.52" is **Unknown** — the fetched doc states the number but not
the eval-set name; do not quote these as TEDS without finding the source table (tag:
**Inferred**, likely PubTabNet-style, unconfirmed). PP-StructureV3 pipeline total (layout
`PP-DocLayout_plus-L` 126 MB + table-type classifier `PP-LCNet_x1_0_table_cls` 6.6 MB +
structure `SLANeXt_*` 351 MB + cell detector `RT-DETR-L` ~124 MB) ≈ **~608 MB all-in** — trivial
against the 10 GB budget, and the doc's own device parameter (`gpu:0` / `cpu`) confirms CPU
execution is supported, not just tolerated. Tag: **Verified** (sizes, license), **Observed**
(CPU-support claim, from doc prose not a live run).

**Output shape — the one architectural fact that matters for spec #1:** structure comes out as
an **HTML token sequence** (`<table><tr><td colspan="4">...`), not free LaTeX and not a raw
box list for SLANeXt. A constrained output grammar (valid HTML tags) is structurally harder to
leave "unterminated" than free-form LaTeX math mode — this is the closest any candidate gets to
addressing SYM-056's specific failure *shape* (though see §0: that failure shape wasn't
Damodaran's problem to begin with). The **wired vs wireless** model split is the closest thing
to "ruling-awareness" among any candidate read — it's still a learned model, not literal PDF
line-vector detection, but it is explicitly trained to treat bordered and borderless tables as
different problems, which none of the other three candidates do.

Test quality: **Unknown** — I did not reach a PaddleOCR unit test with a planted table image
and asserted structural output in this pass (a github.com tree browse and two searches came
back without one); this is UNREAD, not "no test exists." Flagged, not chased further (budget).

Verdict: **BAKE_OFF_CANDIDATE** — real, small, Apache-2.0, CPU-viable, structurally the
best-differentiated of the four (wired/wireless split + bounded-grammar output). Not installed
anywhere in Rab's environment; would need a fresh venv.

### 2b. deepdoctection/deepdoctection
`raw.githubusercontent.com/.../main/README.md` → **404**. `LICENSE` on `master` fetched
successfully: "Apache License / Version 2.0" (Verified, matches GROUND's mechanical table).
A WebSearch (not a source read) surfaces that deepdoctection wraps **the same
`microsoft/table-transformer-structure-recognition` (TATR)** model as unstructured (below) —
consistent across a GitHub issue (#295, "Table Transformer model is not being loaded") and a
repo discussion (#116, "Script for pipeline with structure recognition using table-transformer
available here"). I could not confirm this from deepdoctection's own source in this pass — its
README/docs 404'd on the branch I tried and I did not chase further branch names given the
redundancy with 2c below. Tag: **Unread** (deepdoctection's own docs/tests), **Inferred**
(that it wraps TATR, from search results only, not source).

Verdict: **DISCARD for this bake-off, not the technology** — if it wraps the identical TATR
model as 2c, there's no reason to carry two wrappers of one model into a bake-off; 2c is the
better-verified entry point for that model. Re-open only if deepdoctection turns out to wrap a
*different* structure model than TATR (unconfirmed either way — this is the honest gap).

### 2c. Unstructured-IO/unstructured (+ unstructured-inference) — Table Transformer (TATR)
Fetched `unstructured/partition/pdf.py` (main) and
`unstructured-inference/unstructured_inference/models/tables.py` (main), both **Verified**
from source, not docs. `infer_table_structure` routes through
`unstructured_inference.inference.layout`, which is a **local package call**
(`@requires_dependencies("unstructured_inference")`), not a cloud API — this directly answers
GROUND's "does it need the cloud for tables?": **no, not on this codepath.**

`tables.py`'s `DEFAULT_MODEL = "microsoft/table-transformer-structure-recognition"` (quoted
from source). Cross-checked against the model itself:
**HuggingFace card (Verified):** 28.8 M params, MIT license, DETR-family object detector
("equivalent to DETR... for detecting the structure (like rows, columns) in tables"),
trained on PubTables-1M. **Microsoft's own repo LICENSE (Verified, quoted):** "MIT License /
Copyright (c) Microsoft Corporation." 28.8 M params at fp32 is on the order of 100-120 MB —
trivially CPU-viable, an order of magnitude smaller than the 10 GB budget.

**Architecturally this is the same KIND of thing Marker already runs**: TATR's own README
(Verified, quoted) says *"TATR is an object detection model... inference code built on TATR
needs text extraction (from OCR or directly from PDF) as a separate input"* — i.e. bbox
detection for structure + a **separate** glyph/OCR text-assignment step, which is *exactly*
marker's own pattern (see §3). This is not a new architecture; it is a different training
corpus (PubTables-1M) behind the same box-detector-plus-separate-text-assignment design.

**Test quality — the one real regression test found in this whole lane (quoted, Verified):**
`test_table_prediction_with_ocr_tokens` in
`unstructured-inference/test_unstructured_inference/models/test_tables.py`:
```
prediction = table_transformer.predict(example_image, ocr_tokens=mocked_ocr_tokens)
assert '<table><thead><tr><th rowspan="2">' in prediction
assert "<tr><td>Blind</td><td>5</td><td>1</td><td>4</td><td>34.5%, n=1</td>" in prediction
```
A planted fixture image (`table-multi-row-column-cells.png`) + mocked OCR tokens, asserting
exact cell text AND a `rowspan` attribute survives round-trip. This is the one test in this
lane that would actually catch a real regression (wrong text, wrong span, wrong tag) rather
than just checking the response isn't empty.

Verdict: **BAKE_OFF_CANDIDATE** — best-verified of the four (source read + real test read +
license chain all Verified, not Inferred), local-only, small, MIT+Apache-2.0. Same caveat as
2b/PP-Structure: it is a learned box detector, not a ruling/glyph-geometry reconstructor —
spec #1's ideal (rebuild grids from rulings/x-alignment) is not what TATR does either.

### 2d. docling's TableFormer (docling-ibm-models)
**Deviation from GROUND's premise:** GROUND states "docling is installed in
`C:/Users/Bndit/ml/docling-env`." **Observed, directly, by listing the venv:** only
`docling_core` (2.91.0, the DoclingDocument schema/serialization library) is installed —
**neither `docling` (the conversion pipeline) nor `docling-ibm-models` (where TableFormer
actually lives) is present.** Full site-packages listing (139 entries) has torch 2.11+cu128,
transformers 5.14.1, pymupdf, tokenizers — the *ingredients* for running TableFormer are
there, but not TableFormer itself or its weights. **TableFormer cannot be run in this venv
today; it would need `docling-ibm-models` installed and its checkpoint fetched, both offline
prep steps not yet done.** Tag: **Observed** (venv contents), correcting GROUND's **Inferred**
premise.

What docling_core DOES already confirm (Verified, from its own schema, `types/doc/items/
table/table_data.py`): `TableCell` carries `row_span`, `col_span`, `start_row_offset_idx`,
`end_row_offset_idx`, `text`, `column_header`/`row_header`/`row_section` flags — a full
grid-reconstruction schema, and its `from_dict_format` validator explicitly reads the
**bbox/token dict shape that `docling-ibm-models`'s raw output emits** (i.e. this schema was
built to receive TableFormer's actual output shape, confirming what TableFormer emits even
though the model isn't installed here to run it).

**From source (docling-ibm-models README, Verified, quoted):** *"TableModel04rs (OTSL) is our
SOTA method that using transformers in order to predict table structure and bounding box"* —
this is architecturally **different in kind** from TATR/surya: an autoregressive
sequence-to-sequence decoder producing OTSL tokens **plus** per-cell bbox regression, not a
single-pass object detector. This is the one candidate in the lane that isn't just "another
box detector."

**Model size / license (WebSearch-sourced, not source-file-quoted — tag Inferred for the exact
number, Verified for the license file text separately fetched):** accurate checkpoint
`otslp_all_standard_094_clean.check` = 213 MB, fast variant = 145 MB, both hosted on HF under
`docling-project/docling-models`; **weights license is CDLA-Permissive-2.0** (a data/model
license, distinct from the code). **Code license, fetched directly from `docling-ibm-models/
LICENSE` (Verified, quoted):** "MIT License / Copyright (c) 2024 International Business
Machines." Note the split: MIT code, CDLA-Permissive-2.0 weights — worth carrying into any
sign-off since it's not simply "MIT."

**Test quality (Verified, read the actual test file
`docling-ibm-models/tests/test_tf_predictor.py`):** `test_tf_predictor` asserts only
`tf_responses is not None`, `isinstance(tf_responses, list)`, and that a `'bbox'` key is
present — **no planted-input/known-output assertion, no row/column count, no cell text
check.** This is exactly the tautology shape GROUND warned against: green, but proves nothing
about correctness. Weaker test coverage than 2c's TATR test.

Verdict: **MEASURE_NEXT** — genuinely the most architecturally different candidate (sequence
decoder + bbox regression vs pure box detection), CPU-viable size, clean MIT/CDLA licensing,
but requires an install this session didn't do (deliberately — no GPU work, and installing a
new package into `docling-env` beyond reading it wasn't this lane's mandate) and its own test
suite gives no confidence signal either way. The next concrete step is mechanical: `uv pip
install docling-ibm-models` into `docling-env`, fetch the "fast" 145 MB checkpoint, run it
CPU-only against the page list in §1 (financial tables), and diff its output against surya's
current markdown for the same pages.

## 3. What Marker/surya ALREADY do (read from the installed pipeline, not memory)

`C:/Users/Bndit/ml/marker-env/Lib/site-packages/marker/processors/table.py` (Verified, source
read, this is the code Rab's own converts run): imports `surya.table_rec.TableRecPredictor`
directly (`from surya.table_rec import TableRecPredictor`) — **answers GROUND's question
directly: yes, Marker 1.10.2 already uses surya's table_rec model.** The processor:
1. Runs `TableRecPredictor` over each detected table image → cell polygons with
   `rowspan`/`colspan`/`row_id`/`col_id` (a learned box detector, architecturally the same kind
   of thing as TATR — see 2c).
2. For pages where `page.text_extraction_method in ["surya"]` is False and no OCR errors were
   flagged (i.e. the "clean" lane, matching Damodaran's own `manifest.json`:
   `"lane": "clean", "lane_reason": "text_layer_present"`), it calls
   `self.assign_pdftext_lines(...)` → `pdftext.extraction.table_output`, which is **genuine
   glyph-level PDF text extraction**, then `assign_text_to_cells` maps that glyph text into
   the model-detected cell boxes by geometry.

**So Marker's current design is already a hybrid**: structure/grid from a learned box
detector (surya table_rec), cell TEXT from actual PDF glyphs when a text layer exists (not
OCR). The gap spec #1 names — "rebuild grids from glyph geometry (rulings, x-alignment), not
only layout-model boxes" — is specifically about the **structure** half, which is
model-detected in Marker today, same as in every one of the four candidates read above. **None
of PaddleOCR/deepdoctection/unstructured/docling does true ruling/x-alignment grid
reconstruction either** — they are all learned detectors or sequence decoders, differing in
training data and output grammar, not in kind from what's already running. Tag: **Verified**
(Marker's own mechanism, from source), **Inferred** (that this generalizes to "none of the
four candidates is fundamentally different" — a synthesis claim across four separate reads,
not a single measurement).

No hardcoded `\begin{array}` template exists anywhere in marker's own source
(`grep -rln "begin{array}" .../marker` → 0 hits) — the malformed LaTeX in SYM-056 is emitted
by the OCR/recognition step's own learned text output on OCR-lane pages, not a marker
post-processing template. Consistent with §0's finding that Damodaran (a `"lane": "clean"`
book, mostly non-OCR) has almost no array pathology, while Ashby (presumably OCR-lane or
math-dense) has the large one. Tag: **Observed**.

## 4. Residue (declared, not chased)
- PaddleOCR's own unit-test coverage for table structure: **UNREAD**, not chased past two
  search passes — budget.
- deepdoctection's own README/tests: **UNREAD** — 404 on `main`, didn't retry other branch
  names given redundancy with 2c.
- TATR's published GriTS/accuracy benchmark number + denominator: **UNREAD** — not fetched
  from the table-transformer paper/eval script in this pass.
- TableFormer's own published TEDS number + denominator: **UNREAD** — same reason.
- Whether the page numbers in §1 are exact vs anchor-interpolated: **explicitly flagged
  Unknown above**, not resolved — needs `marker_blocks.py`'s page+bbox JSON, which does not
  exist for this held bundle.
- **A genuine surprise outside this lane's brief, worth a line to Rab directly:** the
  *installed* `surya_ocr-0.17.1` package's own METADATA states `License: GPL-3.0-or-later`
  for the code and *"a modified AI Pubs Open Rail-M license (free for research, personal use,
  and startups under $2M funding/revenue)"* for the weights — **not** the plain Apache-2.0
  the GROUND mechanical-triage table lists. I fetched the **current** `datalab-to/surya`
  GitHub `LICENSE` (Apache-2.0) and README (now says "$5M" threshold) separately — the
  **currently-installed version and the current upstream repo disagree with each other**, and
  the version actually running Rab's pipeline is the older, more restrictive one. This is
  Observed from `surya_ocr-0.17.1.dist-info/METADATA` directly, not inferred, and outside
  Lane B's spec but load-bearing enough (licensing of the ALREADY-RUNNING pipeline) that it
  should not sit buried in a residue line only.
