# Lane C — scan-vs-clean (spec #3) + OCR engines

GROUND read: `windows-converter/convert_and_ship.py:744-779` (`_OCR_FONT` regex + `probe()`),
`:781-` (`route()`, reads `MIN_CHARS_PER_PAGE = 100` at line 114).

## 0. What's actually shipped right now (read, not assumed)

The commission text frames this as "replacing a font-name regex... with render mode 3/7."
Reading the live code says that repair already happened, in S113, and is *documented in the
docstring itself*:

> "OCR layers paint invisible text over the scan image: text render mode 3 (`get_texttrace`
> span type 3)... Majority-of-spans rule so a stray invisible watermark can't flip a real
> layer; the font-name check (tesseract's GlyphLessFont etc.) is kept as a secondary."
> — NUM-5, signed 2026-08-31, census N054

`probe()` (lines 760-778) already computes `invisible_spans / total_spans` from
`page.get_texttrace()`'s `type` field across every page, and `route()` (782-790) ORs that
against the font regex. So the render-mode signal is PRIMARY in fact (an OR means either one
alone can trigger `scan`); the font regex is not load-bearing for any of the 9 works measured
below — it never had to fire, the ratio already decided every case. **This is not a lead to
port in. It is a claim to verify.** Verified below.

## 1. MEASURE FIRST — render mode 3/7 on Rab's own corpus

CPU-only, `C:/Users/Bndit/ml/marker-env/Scripts/python.exe` (pymupdf **1.28.0**, confirmed by
`pymupdf.__version__`), reproducing `probe()`'s own loop exactly: `for page in doc: for span in
page.get_texttrace(): ...`, **full document, every page**, no sampling.

Script: `scratchpad/leads/measure_lanes.py`. Raw output:
`scratchpad/leads/lane_measurements.json`.

Source PDFs live at `C:/Users/Bndit/ml/library/drop/done/*.pdf` (not inside the `anchor/`
work folders — those hold only the converted `.md` + `manifest.json`). Matched each of the 10
`anchor/` manifests' `source` field against that folder.

| work (manifest lane) | pages | total spans | type-3/7 spans | ratio | render-mode verdict | matches manifest lane? |
|---|---:|---:|---:|---:|---|---|
| Ashby, *Intro to Cybernetics* (clean) | 156 | 13,537 | 0 | 0.0 | clean | MATCH |
| Best Practices, Valentine (**scan**/no_text_layer) | 465 | 13 | 0 | 0.0 | clean | **NO — see below** |
| bojieli agent-book (clean) | 19 | 4,088 | 0 | 0.0 | clean | MATCH |
| Brain of the Firm, Beer (**scan**/untrusted_ocr_layer) | 439 | 170,132 | 170,132 | **1.0** | scan | MATCH |
| claude-code-up-and-running (clean) | 104 | 3,830 | 0 | 0.0 | clean | MATCH |
| Cybernetics Book of Models v4.6b (clean) | 91 | 2,319 | 0 | 0.0 | clean | MATCH |
| Diagnosing the System, Beer (**scan**/untrusted_ocr_layer) | 184 | 68,632 | 68,632 | **1.0** | scan | MATCH |
| Investment Valuation, Damodaran 4e 2025 (clean) | 1,356 | 212,394 | 0 | 0.0 | clean | MATCH |
| Investment Valuation, Univ. Ed. 4e 2023 (clean) | 1,377 | 157,924 | 0 | 0.0 | clean | MATCH |
| Designing with Freedom, Beer (manifest: scan/untrusted_ocr_layer) | — | — | — | — | — | **UNREAD — source PDF not on disk** (searched all of `C:/Users/Bndit/ml`, not in `drop/done`, not in `held/`; only the converted `.md` survives under `anchor/`) |

**8/9 measurable works: exact 0.0-or-1.0 bimodal split, zero ambiguous middle case.** Every
type-3/7 span in the corpus is either 0% or 100% of that document's spans — the "majority of
spans" rule in the docstring is undersold; on this corpus it's not a majority, it's unanimous
either way. Negative control (spec's own ask): the 6 born-digital clean works, including the
two 1,300+-page Damodaran editions with 200k+ spans apiece, all measured **exactly 0.0** —
zero false positives at scale.

**The 1 non-match (Best Practices, Valentine) is not a render-mode failure — it's a different
branch of `route()` entirely.** 13 spans total across 465 pages (`chars_per_page_detected:
1.43` in its manifest, vs `MIN_CHARS_PER_PAGE = 100` at line 114) — this is a scan with **no
text layer at all**, not an OCR overlay to detect. `route()`'s `chars >= MIN_CHARS_PER_PAGE`
gate (already shipped, already correct, nothing to do with fonts or render mode) is what
correctly routes it to `scan`/`no_text_layer`. Render-mode-3 detection and the
chars-per-page gate are answering two different questions; conflating them would be the
mistake here, not fixing.

**Combined verdict: 9/9 of the measurable works route correctly under the code as shipped
today** (8 by the render-mode/OCR-overlay branch, 1 by the pre-existing chars-threshold
branch), 1/10 UNREAD for lack of a specimen.

### `get_text("rawdict")` does NOT expose render mode — a negative finding worth recording

The commission text says "try... `get_text('rawdict')` flags" too. Measured on Brain of the
Firm pages 30/50/100/150 (all confirmed OCR-overlay pages, `type==3` in `get_texttrace()`):
`rawdict` spans carry a `flags` field, but it decodes to **`12`** on every one of them — pymupdf's
documented font-style bitmask (`TEXT_FONT_SERIFED=4 | TEXT_FONT_MONOSPACED=8`), i.e. "this is a
serifed monospace font," which is true of `GlyphLessFont` incidentally but says nothing about
render mode. `rawdict` simply does not carry the PDF render-mode operator (`Tr`) at all —
`get_texttrace()`'s `type` field is the only pymupdf 1.28 API surface that does. (One page,
`page[10]`, had zero text blocks in `rawdict` and zero spans in `get_texttrace()` — it's a
pure-image page with no OCR text laid down on it at all, an internal negative control that
both APIs agree on.)

### PDF Producer/Creator metadata as a scan signal — measured, DISCARD

`doc.metadata['producer']` / `['creator']` on the same 9 works:

| work | lane | producer |
|---|---|---|
| Ashby | clean | Acrobat Distiller 3.0 for Power Macintosh |
| Best Practices | scan | Foxit Phantom - Foxit Corporation |
| bojieli | clean | Skia/PDF m150 |
| Brain of the Firm | scan | calibre (5.27.0) |
| claude-code-up-and-running | clean | **calibre 7.6.0** |
| Cybernetics Book of Models | clean | Adobe PDF Library 9.9 |
| Diagnosing the System | scan | calibre (5.9.0) |
| Damodaran 4e 2025 | clean | **calibre 7.21.0** |
| Damodaran Univ. Ed. 4e 2023 | clean | **calibre 8.4.0** |

`calibre` is the producer for 5 of the 9 works — 3 clean, 2 scan. **It does not discriminate at
all; it's the ebook-management tool that repackaged the file, orthogonal to whether an OCR pass
was ever run.** (There's a spurious-looking version split — the 2 scan-lane calibre files are
both v5.x, the 3 clean-lane ones are v7-8.x — but n=5 with an obvious confound, calibre version
tracks *when* the file was touched, not *whether* it carries an OCR layer. Not a signal; noted
only so nobody re-discovers this coincidence and mistakes it for one.) DISCARD.

## 2. The engines

### JaidedAI/EasyOCR
- **Licence at source** (`LICENSE`, raw-fetched): Apache License, Version 2.0.
- **Deps** (`requirements.txt`): `torch`, `torchvision>=0.5`, `opencv-python-headless`, `scipy`,
  `numpy`, `Pillow`, `scikit-image`, `python-bidi`, `PyYAML`, `Shapely`, `pyclipper`, `ninja`.
  Torch is a hard dependency — but marker-env already carries torch for Marker/surya, so this
  is not a new multi-GB install, just a new checkpoint set.
- **CPU-able**: README states plainly — `gpu=False` runs CPU-only. Model weights auto-download
  to `~/.EasyOCR/model`; **exact file sizes UNREAD** — the README states no MB figures, the
  release-assets page (`github.com/JaidedAI/EasyOCR/releases`) failed to render asset sizes
  through WebFetch, and `model_hub.py`'s model-zoo dict carries filename/URL/md5 but no
  `filesize` field. Would need an actual `pip install` + download to measure, not done (GPU
  stays idle per ground rules; the download itself doesn't need the GPU, but I didn't spend the
  bandwidth/time without Rab's go-ahead on a live download).
- **Tests**: `unit_test/unit_test.py` — real mechanism, not a tautology: loads a pickled
  known-answer file (`./data/EasyOcrUnitTestPackage.pickle`) and validates with `test == solution`
  for strings, `abs(1 - test/solution) < 0.1` for numerics. Planted-input/known-output, exact
  match on text. **Can't quote the actual expected string** — it's inside the binary pickle, not
  human-readable in the repo.
- **Verdict for file-portal**: `BAKE_OFF_CANDIDATE` — the only way a scan-lane document gets a
  witness that isn't itself (spec #3's stated point: OCR text vs. `fidelity_audit.py`'s pymupdf
  witness is currently comparing OCR against nothing independent for scan-lane works). Worth a
  head-to-head against surya's own OCR on one scan-lane specimen (Brain of the Firm) before
  building anything.

### PaddlePaddle/PaddleOCR (PP-OCRv4/v5/v6)
- **Licence at source** (`LICENSE`, raw-fetched): `Copyright (c) 2016 PaddlePaddle Authors. All
  Rights Reserved.` under Apache License Version 2.0.
- **PaddleOCR's own `requirements.txt` does NOT list `paddlepaddle`** — the inference framework
  is a separate install (confirmed via `docs/version3.x/installation.en.md`: "training depends
  on PaddlePaddle... follow PaddlePaddle Framework Installation"), with the well-known
  CPU-wheel/GPU-wheel split at that separate install step (not independently re-verified here —
  flagging as the one claim in this section carried at `Inferred` strength, everything else is
  `Verified` against fetched source).
- **Model sizes** (README, PP-OCRv6 tiers): **tiny 1.5M / small 7.7M / medium 34.5M parameters**
  — these are param counts, not MB; no explicit MB figure found in the fetched README slice.
  Trivially CPU-able at that parameter scale (tiny/small are sub-10M-param models; even medium
  is smaller than a single Marker layout-detection checkpoint).
- **Speed claims — vendor-quoting-itself, no absolute denominator**: README states "5.2× CPU
  speedup" (OpenVINO) and "6.1× on Apple M4 (tiny)" — both are *relative* speedups with no
  baseline ms/page or images/sec given in the fetched text, and no CPU model named for the 5.2×
  figure. Per the measurement-language law: no denominator, no trust — these numbers are
  reported here as what the vendor says, not as anything to act on.
- **Tests**: `test_tipc/` is a real numeric-regression harness, not a tautology —
  `compare_results.py` does `np.testing.assert_allclose(pred[k], gt[k], atol=1e-3, rtol=1e-3)`
  across fp32/fp16/int8 ground-truth dictionaries per key. Shell-script CI (`test_train_inference_python.sh`
  etc.), not pytest, but the pass/fail gate is a real numeric tolerance check against stored
  ground truth.
- **Verdict for file-portal**: `BAKE_OFF_CANDIDATE`, same slot as EasyOCR — second/independent
  OCR reader for scan-lane fidelity witnessing. Smaller model tiers than EasyOCR's torch-based
  stack (param counts alone say so; I did not measure either one's actual on-disk MB or a
  CPU-seconds/page number on Rab's hardware — that's the next real measurement, not done here,
  no GPU/CPU cycles were spent running either engine).

## 3. Negative controls run
- 6 born-digital clean PDFs (13,537 to 212,394 spans each) → **0.0 invisible-span ratio**,
  zero false positives on the render-mode signal at real production scale.
- 1 pure-image page (Brain of the Firm, page index 10) → zero spans in *both* `get_texttrace()`
  and `get_text('rawdict')` — internal agreement, not a scan-lane miss (that page just has no
  OCR text laid on it).
- PDF-metadata idea's own negative control is the DISCARD itself: `calibre` producing both
  lanes is the negative control that kills the idea.

## Residue / what I did not run
- Designing with Freedom (Beer) — UNREAD, source PDF absent from disk everywhere I searched
  (`drop/done`, `held/*`, `pending`, and a full `find` over `C:/Users/Bndit/ml`). Only its
  converted `.md` survives. Cannot measure its render-mode ratio; manifest says
  scan/untrusted_ocr_layer, unverified against the render-mode signal.
- Neither EasyOCR nor PaddleOCR was installed or run. No model was downloaded, no CPU-seconds
  were spent on either engine, no GPU cycles anywhere (ground rule: pipeline stays idle). Model
  sizes for EasyOCR specifically are UNREAD, not merely unverified — I looked and could not find
  the figure in what WebFetch returned.
- `get_text("rawdict")` was checked on one work (Brain of the Firm) at 5 page indices, not the
  full corpus — sufficient to answer the yes/no "does it carry render mode" question (no), not
  reused for a full-corpus pass since `get_texttrace()` already answers the real question.
- PyMuPDF's own licence (AGPL/commercial dual, publicly known) was not re-verified from source
  in this pass — it's an existing, already-accepted dependency of the shipped pipeline
  (`convert_and_ship.py`, `fidelity_audit.py` both already import it), not a new risk this lane
  introduces, so out of scope for "is this lead safe to adopt."
