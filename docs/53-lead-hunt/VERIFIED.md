# VERIFIED — the verifier's pass over Lanes A–F (Fable, 2026-09-04 UTC / local evening 2026-09-03)

GROUND. Read all six lane reports in full (A, B, C, D, E, and F — F was in the folder but not in
the digest). Then, myself: every licence claim re-fetched at `raw.githubusercontent.com` / the
HuggingFace API, every size claim re-fetched from the model tree or measured on disk, every
"offline" claim read at the code that loads weights, every headline number read at its
denominator, and every specimen measurement re-run under
`C:/Users/Bndit/ml/marker-env/Scripts/python.exe` (pymupdf 1.28.0, transformers 4.57.6), CPU only,
GPU untouched, `C:/Users/Bndit/Projects/file-portal` read-only. My scripts and raw outputs:
`C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/leads/`
(`verify_lanes_c_e.py`, `verify_lane_b.py`, `verify_sym067_pair.py`, `verify_sym067_residual.py`,
`audit_pos_verify.json`, `audit_neg_verify.json`). Tags: Observed / Verified / Inferred / Unknown.

---

## 1. Findings, most-severe-first

### F1 — Lane A's account of Marker's block order is INVERTED; the "Marker baseline" nobody measured is Marker's (Verified, source)
Lane A §3.0: *"OrderProcessor overwrites [surya's position] for every page that is not OCR'd and
not layout_sliced … Marker's final order is pdftext's own span order."*
`C:/Users/Bndit/ml/marker-env/Lib/site-packages/marker/processors/order.py:17-22` reads:
```
if page.text_extraction_method != "pdftext": continue
if not page.layout_sliced: continue
```
It re-sorts ONLY sliced pages. For every ordinary page, `builders/layout.py:140` inserts blocks
`sorted(layout_result.bboxes, key=lambda x: x.position)` — surya-layout's autoregressive
`position=z` (`surya/layout/__init__.py:97`, Lane A's own citation) — and nothing reorders them
afterwards (`grep "page.structure = "` → only `order.py:65`). So Marker's order on Rab's books is
the layout model's learned emission order, not the content stream. Consequence: pymupdf
`get_text("dict")` raw block order — what `probe_k_order.py::geom_frags()`, docs/52's "2/57 and
15/60", GROUND's "against Marker's geometric order", and Lane A all call Marker's baseline — is a
proxy for the content stream, not for Marker. Lane A's XY-cut numbers stand as XY-cut vs
content-stream and vs declared; the sentence "XY-cut breaks 3 pages Marker got right" is UNREAD as
regards Marker. Marker's real order vs the declared tree has never been measured; it needs a J24
`blocks.json` for WTPDF/ISO (a GPU run, not this session's).

### F2 — Lane D "corrected" the spec's Chandra size to 9B by reading the WRONG repo (Verified, HF API + disk)
Lane D fetched `datalab-to/chandra` (v1: 8,767,123,696 params, `model_type qwen3_vl`,
`Qwen3VLForConditionalGeneration`). The weights on disk are `chandra-ocr-2`
(`C:/Users/Bndit/ml/chandra/chandra-ocr-2/`, `settings.py` default checkpoint
`datalab-to/chandra-ocr-2`). `huggingface.co/api/models/datalab-to/chandra-ocr-2`: **5.3 B params
BF16, `Qwen3_5ForConditionalGeneration`, `model_type qwen3_5`, `mamba_ssm_dtype float32`,
`linear_num_key_heads 16`** — byte-for-byte what the on-disk `config.json` says. Arithmetic:
`model.safetensors` = **10,591,220,088 B** (my `du -b`) ÷ 2 B/param = 5.30 G params. The spec's
"5B" was right; Lane D's "9B, HF card" is wrong; Lane D's "unresolved qwen3_5 vs qwen3_vl" is
resolved (two different models). Lane D's "model.safetensors = 10,611,947,865 bytes" is the folder
total (difference 20,727,777 B ≈ tokenizer.json 19,989,343 + the PNG/JSON sidecars; Inferred from
arithmetic). What survives and is now stronger: Chandra-OCR-2 IS a Qwen3.5 hybrid
(linear-attention/Mamba fields present) — Lane D's llama.cpp-support risk on the third-party GGUF
is real. Also missed: `mradermacher/chandra-ocr-2-GGUF` ships an **mmproj** (Q8_0 366,894,368 B)
that a vision run needs; Q4_K_M 3,066,385,440 + mmproj = ~3.43 GB, not 2.86. And `docling-env`
already holds transformers **5.14.1** + torch 2.11+cu128 — an existing env past the config's
`transformers_version 5.2.0`, which Lane D's "upgrade marker-env's transformers" path overlooked.

### F3 — The RUNNING pipeline is GPL-3.0 + OpenRAIL-M $2M, not the Apache the triage table says (Verified, dist-info METADATA vs upstream)
`marker_pdf-1.10.2.dist-info/METADATA:5` = `License: GPL-3.0-or-later`; line 93: weights "modified
AI Pubs Open Rail-M license (free for research, personal use, and startups under **$2M**)".
`surya_ocr-0.17.1.dist-info/METADATA:5` identical (`$2M`, line 95). Upstream HEAD today:
`datalab-to/marker/master/LICENSE` and `datalab-to/surya/master/LICENSE` are Apache-2.0 and both
READMEs say $5M. GROUND's "marker · Apache" / "surya · Apache" are true of upstream HEAD and false
of the versions on Rab's machine. Lane B found surya; marker is the same. Personal use clears
both — but "Apache" must not be written about the installed pipeline.

### F4 — GROUND's spec-#1 measurement names the wrong specimen (Verified, the repo's own function)
Real `fidelity_audit.latex_balance` (imported, not re-typed) on the held Damodaran Univ 4e
(`C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e/…Four.md`, 29,698 lines): `array` begin **87** /
end **84** / unterminated **3** (lines 8776, 17966, 22953), zero colspecs ≥ 6 identical letters,
65 of 87 are `{lll}`. The same function on the **Ashby** anchor bundle: begin **127** / end **66** /
unterminated **61**, six `\begin{array}{c…c}` colspecs of 30+ `c`s — exactly SYM-056's
"semantic 61 / 127 opens / 66 closes". The "61" is Ashby's, a **clean-lane** book (manifest
`text_layer_present`, producer Acrobat Distiller 3.0) — Lane B's "presumably OCR-lane" is wrong too.
Damodaran's real spec-#1 target is pipe tables: 4,580 rows on 235 anchor-pages, 4,712 `| |`
markers on 217; densest pages 805 (130), 564 (122), 757 (101), 779 (95), 579 (90). Lane B's
anchor bookkeeping is off (it wrote 1,277 anchors / 0 violations; there are **1,393**, with
**2** order violations at lines 19069→19103 and 23800→23801, largest gap 839 lines) — its "± a few
pages" caveat stands, its numbers on the anchors do not.

### F5 — The held Damodaran's `fail` = 24 table false-positives + ONE real LaTeX loop, and that loop IS one of the three unterminated arrays (Verified, measured this pass)
`compute_verdict` (`fidelity_audit.py:545`): `degeneration` is the only convert-stage path to
`fail`. Re-running `degeneration()` on the held body: RAW flagged, 25 blocks, `repeated_lines 0`.
With pipe-table rows stripped first: **1 block survives** — raw line **8776**, 21,870 chars on one
line, zlib 0.011, `max_trigram 441`; its tail repeats `& - & {\rm Int}\left( {1 - t} \right)/{\rm E} \\`
440 times and it opens `\begin{array}{lll}` with no `\end{array}` — i.e. the first of Lane B's three
unterminated arrays. A genuine decoder runaway (SYM-056's family), not a table. SYM-067's row
("counterfactual with `_strip_markdown` first → 0 paragraphs trip" in *both* 4e audits) is true for
the 2025 4e anchor (26 → **0**, flagged=false) and **false** for the University 4e (25 → 1). The
Beer Brain-of-the-Firm anchor keeps tripping under every variant (`The Stage of the Stage of the…`,
max_trigram 2,267; the other bundle 143) — the planted negative control holds. This pair is
measured and on disk; it is the build-first (§5).

### F6 — Lane C's "the font regex never had to fire" is overstated (Verified, my re-run)
Reproducing `probe()` including `_OCR_FONT`: Brain of the Firm short-circuits on **`GlyphLessFont`**,
Diagnosing on **`InvisibleOCR`**; both also read ratio 1.0. Both signals agree on all 9 works; the
regex fires and is recorded in the evidence dict — it is simply not load-bearing. 9/9 routing
CONFIRMED (clean 6 at 0.0; scan 2 at 1.0; Valentine `chars_pp 1.43` → `no_text_layer`).

### F7 — PaddleOCR's table "accuracy" has a proprietary denominator (Verified, the doc page)
`docs/version3.x/module_usage/table_structure_recognition.md`: SLANeXt 69.65 / SLANet_plus 63.69
/ SLANet 59.52 are measured on an "internal self-built high-difficulty Chinese table recognition
dataset". Lane B's Inferred "likely PubTabNet-style" is wrong; the numbers are the vendor quoting
itself and score nothing on Rab's pages.

### F8 — Smaller corrections
- Lane D: "run via `llama-mtmd-cli` … documented" — the official `Qwen3-VL-4B-Instruct-GGUF`
  README gives no command; it says the files are "compatible with llama.cpp, Ollama". Inferred,
  not documented. Sizes byte-exact CONFIRMED (Q4_K_M 2,497,281,664 + mmproj Q8_0 453,974,304).
- Lane B: `docling-project/docling-models` licence field is `["cdla-permissive-2.0","apache-2.0"]`,
  not CDLA alone; TableFormer sizes CONFIRMED byte-exact (accurate 212,758,388 B, fast
  145,453,276 B) under today's filenames `tableformer_{accurate,fast}.safetensors`, not the
  `.check` name cited.
- Lane D: nougat-base is 348,736,012 params ("0.3B" understated); pushed 2025-02-21, 559 days
  — CONFIRMED.
- Lane C's UNREAD EasyOCR sizes, now READ: `craft_mlt_25k.zip` 77,251,756 B, `english_g2.zip`
  14,040,947 B (GitHub release assets); first-use download from github.com releases, then offline.
- Lane D's fidelity numbers re-run exactly (0.9271 / 1372 positive; 0.0 / 1372 negative) and the
  stored manifest says 0.9334 — the version-drift note is real and stays Unknown.

---

## 2. Claims checked (adversarial selection; ≥12)

| # | lane | claim | checked against | verdict |
|---|---|---|---|---|
| 1 | GROUND | marker 1.10.2 / surya 0.17.1 are Apache | `marker_pdf-1.10.2.dist-info/METADATA:5,93`; `surya_ocr-0.17.1.dist-info/METADATA:5,95` (GPL-3.0-or-later; OpenRAIL-M $2M) vs upstream LICENSE (Apache-2.0, $5M) | WRONG for the installed versions |
| 2 | B | installed surya is GPL + $2M OpenRAIL-M, upstream is Apache + $5M | same files + `datalab-to/surya/master/LICENSE`, README | CONFIRMED (and extends to marker) |
| 3 | D | Chandra is 9B params per the HF card | `api/models/datalab-to/chandra-ocr-2` (5.3B, Qwen3_5ForConditionalGeneration) + `du -b model.safetensors` 10,591,220,088 ÷ 2 | WRONG (read `datalab-to/chandra` v1) |
| 4 | D | `model.safetensors` = 10,611,947,865 B | `du -b` = 10,591,220,088 B; the delta is the sidecar files | WRONG (folder total) |
| 5 | D | Chandra weights OpenRAIL-M, $2M, "cannot be used competitively with our API" | `C:/Users/Bndit/ml/chandra/chandra-ocr-2/LICENSE` §(a)(b) `$2,000,000`; README line 218; `settings.py` (`VLLM_API_BASE localhost`, `VLLM_API_KEY "EMPTY"`, `--method hf` local) | CONFIRMED; offline-capable CONFIRMED |
| 6 | D | Qwen3-VL Apache-2.0; 4B Q4_K_M 2,497,281,664 B + mmproj 453,974,304 B; 8B 5,027,784,800 + 752,289,728 | `QwenLM/Qwen3-VL/main/LICENSE`; HF tree API both repos | CONFIRMED byte-exact |
| 7 | D | third-party Chandra GGUF Q4_K_M 3,066,385,440 B, would fit "if it loads" | `mradermacher/chandra-ocr-2-GGUF` tree (+ mmproj Q8_0 366,894,368 B omitted) | CONFIRMED, OVERSTATED as complete |
| 8 | D | nougat: code MIT, weights CC-BY-NC-4.0, 0.3B, pushed 2025-02-21 | `facebookresearch/nougat/main/LICENSE`, README, `api/models/facebook/nougat-base` (348,736,012 params), GitHub API | CONFIRMED |
| 9 | D | Florence-2-large MIT, 0.77B | `api/models/microsoft/Florence-2-large` (776,721,497 params, `mit`) | CONFIRMED |
| 10 | D | fidelity_audit CLI is candidate-agnostic: 0.9271/1372 positive, 0.0/1372 negative | re-run, `audit_pos_verify.json` / `audit_neg_verify.json` | CONFIRMED |
| 11 | B | PaddleOCR Apache-2.0; SLANet 6.9 MB, SLANeXt 351 MB; accuracy denominator "likely PubTabNet" | `PaddleOCR/main/LICENSE`; `table_structure_recognition.md` ("internal self-built … Chinese" set) | licence/sizes CONFIRMED; denominator WRONG (proprietary) |
| 12 | B | TATR MIT, 28.8M params; `test_table_prediction_with_ocr_tokens` asserts `<th rowspan="2">` and `<td>Blind</td><td>5</td>…` | `microsoft/table-transformer/main/LICENSE`; HF API 28,847,819; `unstructured-inference/main/test_unstructured_inference/models/test_tables.py` (33 tests); `tables.py` DEFAULT_MODEL, no non-HF network | CONFIRMED |
| 13 | B | TableFormer 213/145 MB, MIT code, CDLA weights; test asserts only presence | `docling-ibm-models/main/LICENSE`; HF tree (212,758,388 / 145,453,276 B); `api/models/docling-project/docling-models` (`cdla-permissive-2.0` AND `apache-2.0`); `tests/test_tf_predictor.py` (6 asserts, all field-presence) | CONFIRMED; licence OVERSTATED as single |
| 14 | B | docling-env has only docling_core, no docling / docling-ibm-models | `ls C:/Users/Bndit/ml/docling-env/Lib/site-packages` | CONFIRMED (+ transformers 5.14.1, torch 2.11+cu128, pymupdf 1.28.2) |
| 15 | B | Damodaran array 87/84/3, not 61; the 61 is Ashby's | real `fidelity_audit.latex_balance` on held md and on the Ashby anchor md (127/66/61, six 30+-`c` colspecs) | CONFIRMED (GROUND's spec-#1 line is wrong-specimen) |
| 16 | B | 1,277 page anchors, monotonic, 0 violations | my count: 1,393 anchors, 2 violations | WRONG (minor) |
| 17 | C | 9/9 lanes route correctly; render-mode ratio bimodal 0.0/1.0; "font regex never had to fire" | `verify_lanes_c_e.py` reproducing `probe()`+`route()` verbatim | CONFIRMED; the regex fires on both scan works (`GlyphLessFont`, `InvisibleOCR`) — OVERSTATED |
| 18 | C | `rawdict` flags = 12 carries no render mode; Beer page 10 empty in both APIs | re-run pages 10/30/50/100/150 | CONFIRMED |
| 19 | C | EasyOCR Apache-2.0; requirements torch/torchvision…; pickle known-answer test; sizes UNREAD | `JaidedAI/EasyOCR/master/LICENSE`, `requirements.txt`, `unit_test/unit_test.py` (`lzma`+`pickle`, `test == solution`); release assets 77,251,756 + 14,040,947 B | CONFIRMED; UNREAD → READ |
| 20 | C | PaddleOCR requirements omit paddlepaddle; `test_tipc/compare_results.py` `assert_allclose` atol/rtol 1e-3 | both raw files | CONFIRMED (function default 1e-7, CLI default 1e-3) |
| 21 | A | Comp-HRDoc MIT; "Due to company policy, we cannot release the code"; no weights | `microsoft/CompHRDoc/main/LICENSE` ("MIT License … Jarvis"), `UniHDSA/README.md`, top README (images not released) | CONFIRMED |
| 22 | A | REDS 0.9319/0.8637 vs Lorenzo† 0.7741/0.8583; 500 test docs; 8× V100 32 GB; "prone to failure" quote | paper text `paper_p25_35.txt` Table 6, `paper_p13_24.txt:740,774`, `paper_p1_12.txt:253` | CONFIRMED |
| 23 | A | Marker's OrderProcessor overwrites order on non-sliced pages; baseline = pdftext order | `marker/processors/order.py:17-22`, `builders/layout.py:140` | WRONG (inverted) — see F1 |
| 24 | A | docs/52: 19 pages of 4,307 (0.44 %) reach a structure tree | `docs/52-pdf-structure-study/design.md:20-24` | CONFIRMED |
| 25 | E | PdfPig Apache-2.0 + BSD notices; `UnsupervisedReadingOrderDetector.cs` cites Klampfl et al. and Todoran et al., Allen's interval relations | raw LICENSE and .cs | CONFIRMED |
| 26 | E | deepdoctection Apache-2.0; `eval/tedsmetric.py` exists (APTED) ; unstructured Apache-2.0 | raw LICENSE files; `tedsmetric.py` (`from apted import APTED`) | CONFIRMED |
| 27 | F | mAP@50 0.8836 / 0.7351 / P 0.8429 / R 0.7879; no code released; ref [39] is a wiring-harness paper | `pdf_text.py` on `applsci-16-03089.pdf` pp. 5, 15-16, 22, 28 | CONFIRMED |
| 28 | SYM-067 row | `_strip_markdown` first → 0 paragraphs trip in both 4e audits | `verify_sym067_pair.py` | CONFIRMED for 2025 4e (26→0), WRONG for Univ 4e (25→1, a real LaTeX loop at line 8776) |
| 29 | C/E | PaddleOCR first-use model download host / offline caching | `installation.en.md` says nothing | UNREAD |

---

## 3. Measurements re-run (command → their result → mine → match?)

| lane | what | theirs | mine | match |
|---|---|---|---|---|
| A | `xycut_probe.py` negative controls | determinism True; two-column `[L0,L1,L2,R0,R1,R2]` True, naive False | identical | yes |
| A | v1 XY-cut vs declared | WTPDF 55/57, ISO 59/60 | 55/57, 59/60 | yes |
| A | content-stream ("geometric") vs declared | 2/57, 15/60 | 2/57, 15/60 | yes (but it is not Marker — F1) |
| A | `xycut_v2.py` margin-excluded | 2/57, 18/60 | 2/57, 18/60 | yes |
| A | `xycut_v3_net.py` net | 0 fixed / 0 broken WTPDF; 0 fixed / 3 broken ISO `[15,38,47]` | identical | yes |
| B | `latex_balance` on held Damodaran | array 87/84/3; total 5 of 173 | real function: 87/84/3; 5/173; lines 8776/17966/22953 → anchor pages 439/832/1057 | yes |
| B | colspecs | 65×3, 17×2, 4×1, 1 uncaptured, 0 degenerate | identical | yes |
| B | pipe tables | 4,580 rows / 235 pages; 4,712 `\| \|` / 217 pages; top 805/564/757/779/579 | identical | yes |
| B | page anchors | 1,277, 0 violations | 1,393, 2 violations | NO (minor) |
| B | Ashby (the real SYM-056 book) | not run | array 127/66/**61**, six 30+-`c` colspecs | new |
| C | `probe()` loop, 9 works | 6×0.0 clean, 2×1.0 scan, Valentine 13 spans | identical + font triggers `GlyphLessFont` / `InvisibleOCR` | yes |
| C | producer metadata | calibre on 5/9 across both lanes | identical | yes |
| C | `rawdict` flags | 12 on pp. 30/50/100/150 | 12 | yes |
| D | `fidelity_audit.py --pdf --md --lane clean` | 0.9271 / 1372, verdict fail | 0.9271 / 1372 / 257 flagged / verdict fail | yes |
| D | negative control (filler md) | 0.0 / 1372 | 0.0 / 1372 / 1372 flagged / verdict flag | yes |
| E | Damodaran p10 | 30 spans, all type 0, no StructTreeRoot, calibre 8.4.0 | identical | yes |
| E | Beer pp. 0/1/5/7/8 | 15/255/4/36/92 type-3 | identical (+ p9 23, p11 119) | yes |
| new | `degeneration()` planted pair | SYM-067 row: 0 trip after strip (both 4e) | 2025 4e 26→0 (false); Univ 4e 25→1 (line 8776 real loop); Beer 20/19 blocks stay flagged, max_trigram 2,267 | pair holds; row half-wrong |

---

## 4. Ranked leads — (what it fixes on Rab's ACTUAL failing pages) ÷ (cost to measure); audit-scoreable first

| rank | lead | spec row | verdict I endorse | the ONE measurement | why this rank |
|---|---|---|---|---|---|
| 1 | Table-aware `degeneration()` (strip pipe rows before the trigram/zlib test) | #2 SYM-067 | BUILD (gate change = Rab's signature) | the measured pair above: 2025 4e 26→0, Univ 4e 25→1 (line 8776 must STAY flagged), Beer must still trip | it is the only convert path to `fail`, it is why the maiden voyage is HELD, it is scored by `fidelity_audit.py` itself, CPU-only, hours |
| 2 | Qwen3-VL-4B-Instruct GGUF (official, Apache-2.0, 2.95 GB) | #6 | MEASURE_NEXT | render held Damodaran anchor-page 805 (130 empty markers) → markdown → `fidelity_audit --pdf/--md` + `latex_balance`; negative control the filler md (0.0) | cheapest real reconstructor test, fully audit-scoreable, ~5 GB VRAM headroom; needs Rab to sign one ~2.95 GB download and a GPU session |
| 3 | Chandra-OCR-2 (on disk, 5.3B, OpenRAIL-M $2M) | #6 / J25 | BAKE_OFF_CANDIDATE, licence for Rab's eyes | same page-805 protocol, loaded INT4 via `docling-env` (transformers 5.14.1 ≥ config's 5.2.0) or the third-party GGUF+mmproj (3.43 GB, hybrid-arch risk) | highest expected fidelity (vendor's 85.8 vs 76.5, unverified) but does not fit BF16, one more env, a licence clause to read |
| 4 | nougat-base (0.35B, CC-BY-NC weights) | #1 (LaTeX arrays) / #6 | BAKE_OFF_CANDIDATE on the RIGHT book | Ashby anchor's array pages → `.mmd` → `latex_balance` unterminated vs 61 | the only candidate trained on the exact failure (`\begin{array}` runaway) — but Ashby, not Damodaran, is that failure's specimen; dormant 559 d, own env |
| 5 | docling TableFormer (145/212 MB, MIT code, CDLA/Apache weights) | #1 | MEASURE_NEXT | install into `docling-env`, run pages 805/564/757 CPU, diff cell grid vs surya's; needs a TEDS scorer (deepdoctection's `tedsmetric.py` idea) and hand-made ground truth | architecturally different in kind, but emits structure not page markdown — needs a wrapper before `fidelity_audit.py` can see it; its own test is a tautology |
| 6 | TATR via unstructured-inference (28.8M, MIT) | #1 | BAKE_OFF_CANDIDATE | same as 5 | same kind as surya table_rec (box detector + separate text); best test suite of the four; same wrapper gap |
| 7 | PaddleOCR PP-StructureV3 / SLANeXt (351 MB, Apache-2.0) | #1 | LOW | same as 5 | proprietary denominator (F7); a second DL framework (paddlepaddle, not in requirements); download host UNREAD |
| 8 | EasyOCR (Apache-2.0, ~91 MB zipped) | #3 witness | DEFER | Beer Brain p1 (255 invisible spans) OCR'd by EasyOCR vs the embedded layer vs surya | spec #3 is shipped and 9/9; a second witness helps scan-lane auditing only — not a spec row that is failing |
| 9 | XY-cut over J24 blocks (55 lines, on disk) | #4 | DISCARD as measured; re-open only with (a) Marker's real order via a `blocks.json` on WTPDF/ISO and (b) a multi-column ground-truthed specimen | net 0 fixed / 3 broken vs content-stream order; both ground-truthed specimens are single-column | cannot be scored by `fidelity_audit.py`; 0.44 % of Rab's pages carry a tree (docs/52); F1 removes even the baseline it was compared to |
| 10 | PdfPig interval-algebra / Docstrum (citation only, C#) | #4 | IDEA_ONLY | same gate as 9 | — |
| — | Detect-Order-Construct (no code, no weights, 8× V100), deepdoctection & unstructured frameworks, Florence-2 (no page reconstruction), colpali (no text), zerox (steal the prompt only), llama-parse (cloud, deprecated), exiftool/Producer metadata (calibre on both lanes), `rawdict` flags, Lane F's paper (no artifacts, reading order disclaimed) | — | DISCARD | — | — |

---

## 5. Build first — one sentence for Rab

**Build the table-aware degeneration gate for SYM-067 — strip markdown pipe-table rows before
`degeneration()` runs in `windows-converter/fidelity_audit.py` — measured on the pair already on
disk: the anchored Damodaran 2025 4e must go from `flagged=true` / 26 blocks to `false` / 0, the
held University 4e (`14c66834bdfeaa2e`) from 25 blocks to exactly 1 — raw line 8776, the real
440-repeat `{1 - t}` runaway that is also SYM-056's unterminated `\begin{array}` and must STAY
flagged — and the Beer Brain-of-the-Firm anchor (`The Stage of the Stage of the…`, max_trigram
2,267) must still trip; CPU-only, scored by the audit itself, the gate change is yours to sign.**

---

## 6. Residue (declared, not chased)
- Marker's actual block order on WTPDF/ISO vs the declared tree: UNREAD — needs a GPU
  `marker_blocks.py` run on those two PDFs (F1). Until then every "Marker diverges N/57" sentence
  in docs/52, GROUND and Lane A describes the content stream.
- PaddleOCR / EasyOCR / TableFormer were not installed or run; no CPU-s/page on Rab's hardware.
- PaddleOCR's first-use model host and offline caching: UNREAD (installation doc silent).
- Whether llama.cpp runs the Qwen3.5-hybrid Chandra GGUF correctly: Unknown; not downloaded.
- The Qwen3-VL document-parsing cookbook prompt: not fetched; zerox's prompt (quoted by Lane D,
  re-fetched by me verbatim) is the stand-in.
- `fidelity_audit` version drift (manifest 0.9334 vs fresh 0.9271 on identical md/pdf): real,
  cause Unknown (the manifest records `marker_version: "unknown"`).
- Lane B's anchor-gap page numbers are ± the local gap; exact pages need a `blocks.json` that this
  held bundle does not have (J24 was built after this conversion).
- Designing with Freedom (Beer): source PDF absent from disk; its scan-lane routing stays
  unverified by render mode (Lane C's UNREAD stands).
- Lane F's paper: I re-checked four of its numbers and two of its defects; the rest of its 29 pages
  I did not re-read.
