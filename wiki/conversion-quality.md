---
title: Conversion Quality & OCR
section: Pipeline
last-verified: 2026-08-23
verified-against: 1790554
sources: [windows-converter/fidelity_audit.py, windows-converter/figure_coverage.py, windows-converter/backend_parity.py, windows-converter/convert_and_ship.py, linux-converter/converter/engines.py, docs/11-gpu-pipeline-revamp.md, docs/34-measurement-language.md, docs/41-conversion-completeness-plan.md, docs/42-conversion-completeness-findings.md, SYMPTOM-INDEX.md, OPEN-TASKS.md, prototypes/docling-calibration/README.md, sessions/S106-desktop-2026-08-20.md]
---

**Conversion quality is measured by three report-only instruments — `fidelity_audit.py` (did
the text survive?), `figure_coverage.py` (did the figures survive?), `backend_parity.py` (may
a new analyst backend ship?) — under one vocabulary law (docs/34: every number names its
numerator, denominator and conditions). Two facts dominate everything else on this page. First:
across the entire recorded event stream the survival audit has returned 24 fail + 8 flag and
ZERO pass — the verdict has never once come back clean. Second: the figure instrument's
headline was measured on a poisoned corpus (SYM-050 — pre-S60 doubled-offset bundles still sit
in `anchor/`; 19 of 20 adjudicated "uncovered" verdicts were false), and the S106 page-map
repair that fixes this is still NOT wired into the shipped tool. Quality numbers from this
pipeline are only as good as the map they were measured on — check the map first.**

## The three instruments

**`fidelity_audit.py` — the survival audit** (491 lines, `wc -l`). Measures how much of the
source PDF survives into Marker markdown, and how much of that survives the analyst pass,
by window-survival containment against an ephemeral pymupdf witness — deterministic, CPU-only,
report-only (fidelity_audit.py:1-8). Verdicts are `pass|flag|fail` (fidelity_audit.py:11), and
by the signed policy only TWO signals reach "fail": degeneration (zlib+trigram AND-gate) and
analyst near-exact containment (fidelity_audit.py:34-36, :411-437). Everything else — low
survival, page flags, omission runs, garbage rate — is a report-only localizer, at most "flag"
(fidelity_audit.py:421-423), because acceptable books measured 0.76–0.96 survival and gating
on survival would false-fail legitimate reflow. Whether a "fail" parks a bundle is the separate
report↔enforce lever in `convert_and_ship.py` (fidelity_audit.py:36-37).

**The verdict census — zero passes, ever.** From the live event stream (external to the repo:
`C:\Users\Bndit\ml\library\events.jsonl`, 137 lines on 2026-08-23), by
`grep -o '"verdict": "[a-z]*"' events.jsonl | sort | uniq -c`:
- **24 fail + 8 flag + 0 pass** — numerator: event lines by verdict value; denominator: all 32
  verdict-carrying lines (verdicts ride `scored`, `flagged` AND `held` events, so one failing
  audit emits up to three lines — this count is per-line, not per-book).
- **9 fail + 4 flag + 0 pass** — the same census restricted to `"event": "scored"` (one line
  per audit measurement): 13 scored events over 6 distinct source PDFs (10 distinct `source`
  strings — four books are logged both with and without the `.pdf` suffix), 2026-07-21 →
  2026-08-14. Probe controls: 35 total `"stage": "audit"` lines, of which 3 (`supersede`)
  correctly carry no verdict — the pattern does not match everything.
Both denominators agree on the load-bearing fact: the audit has never emitted "pass". A verdict
that always says fail-or-flag routes every book toward the bench; it currently discriminates
severity, not acceptability.

**`figure_coverage.py` — P-1, the figure instrument** (678 lines + 279-line selftest, `wc -l`).
Answers, per source page bearing ≥1 figure-like region, whether the bundle has ≥1 asset
attributed to that page — numerator: figure-bearing pages with 0 output assets; denominator:
figure-bearing pages; conditions printed per run (figure_coverage.py:5-10). Coverage is
per-page, not per-figure — a page with three source figures and one asset counts COVERED, a
stated sensitivity ceiling (figure_coverage.py:18-21). It is report-only by doctrine (docs/15
§6) and deliberately unwired: it writes no manifest key and sets no verdict
(figure_coverage.py:31-36). Callers: `git grep -ln figure_coverage` returns only prose files
plus its own selftest — zero code callers. And the S106 page-map repair
(`true_page = id + 1 − 200×(id÷400)`, sessions/S106-desktop-2026-08-20.md:93) is NOT in the
shipped tool: `git grep -n true_page` has exactly one hit, that closeout line — the tool still
reports IV uncovered 239 / coverage 0.1115 instead of 49 / 0.8178 (OPEN-TASKS.md A18).

**`backend_parity.py` — may a candidate backend replace Ollama?** (705 lines, `wc -l`). Two
gates in strict order: the TOKEN GATE (same output size, stops on its own, passes the image
fence) before the THROUGHPUT ARM — "a fast backend that writes the wrong thing is not a faster
backend" (backend_parity.py:7-13). It is docs/34's first consumer: prefill and decode never
blended, unreported durations render UNREAD rather than 0.0, and "if this harness and docs/34
ever disagree, THIS FILE IS WRONG" (backend_parity.py:15-20).

## The eval-corpus problem — SYM-050

Pre-S60 bundles number their assets by a doubled page index, so `_ASSET_RE` attributes every
asset to the wrong page and the per-page presence question is answered against a scrambled map
(SYMPTOM-INDEX.md row SYM-050). Measured on Investment Valuation: **19 of 20 adjudicated
uncovered verdicts FALSE** — denominator: a seeded random sample of 15 of the 239 plus a
census of the 5 in the one correctly-mapped slice; conditions: IV bundle of 2026-08-01, shipped
thresholds, seed 20260820, every page rendered at 1.5× and visually adjudicated (SYM-050 row).
Region-level detection is separately fine: 13.3 % false alarms (2 of 15 sampled regions). The
poisoned bundle is still there: `anchor/Investment Valuation - Aswath Damodaran (4e, 2025)`
(anchor/ lives outside the repo, under `C:\Users\Bndit\ml\library\`)
(converted 2026-08-01) carries 313 assets with page ids up to `_page_2553_` on a 1,356-page
book (`ls .../assets | sed -E 's/.*_page_([0-9]+)_.*/\1/' | sort -n | tail -1` → 2553;
docs/41-conversion-completeness-plan.md:475 names the hazard). The tool detects the signature
and prints "report not trustworthy (SYM-050)" (figure_coverage.py:644) — but the warning does
not reach the `--json` payload, and the standing rule is never to quote a per-page number from
a bundle that trips the flag, until the map repair is wired (SYMPTOM-INDEX.md SYM-050 row;
OPEN-TASKS.md A18).

## What is banned or fenced — each with its measurement

- **`--force_ocr` at Marker defaults**: with models warm it saturated the GPU at 100 % for
  27+ minutes with no output (vs 97 s default) at a 9,939 MiB peak against the 10 GB card —
  Marker auto-scales recognition batches to fill VRAM and full-book re-OCR (1,281 text
  regions) thrashes the ceiling. "Rules out force-OCR at defaults as a pipeline lane on this
  card" (docs/11-gpu-pipeline-revamp.md:86). No code passes it: `grep -rn force_ocr
  windows-converter/*.py` finds nothing — the only mention is the hyphenated "force-OCR" in
  convert_and_ship.py:14's docstring; the shipped route for a bad OCR layer is
  `--strip_existing_ocr` (convert_and_ship.py:554).
- **Generative super-resolution**: no SR exists anywhere in the pipeline, and docs/41 §P-6
  calls that the correct state — fabricated glyphs are fluent, "the one failure our
  compression/trigram gate cannot see by design" (docs/41:249-250; evidence
  docs/42-conversion-completeness-findings.md:284-286). Note the ban itself is NOT yet
  recorded as signed doctrine — that is decision A7 (OPEN-TASKS.md A7, E-slate P-6 row).
- **LLM adjudication — adjudicator, never searcher** (docs/41:207-224, P-4): deterministic
  alignment beats a VLM judge by +15.2 F1 (docs/41:210); AbsenceBench 69.6 F1 and MissingBench
  44–75 % argue the LLM must never be the detector (docs/41:774). It may only adjudicate spans
  a deterministic pass has already marked, per-page, with layout — and never inside the
  converter process, which competes for the 3080 (docs/41:215). Whether an LLM verdict may
  ever gate is unsigned (docs/41:224).

## OCR today

The GPU lane's OCR is **surya inside Marker** on the RTX 3080 — marker-env carries
`marker-pdf 1.10.2` with `surya-ocr 0.17.1` (docs/11:60); the converter parses surya's tqdm
bars into a progress file the widget's stage display reads (convert_and_ship.py:97-103). Routing is probe-driven: `probe()` detects an
embedded OCR layer via text render mode 3 — invisible text painted over the scan image
(convert_and_ship.py:523-526) — and `route()` sends an untrusted layer to the scan lane with
`--strip_existing_ocr` so surya re-reads the pages (convert_and_ship.py:550-554). The
ThinkPad's CPU lane is the fallback: pymupdf4llm with `OCRMode.FORCE_DROP_OLD` at a configured
dpi for scans (linux-converter/converter/engines.py:78-96), which requires tesseract language
data (linux-converter/tests/test_main.py:3). A third engine, **granite-docling-258M**, was
calibrated in `prototypes/docling-calibration/` before use and holds a zone-scope precedent:
crop scope ~2–3 s at ~650–750 MiB (Bench-viable, 220 dpi) versus page scope 29–86 s at 144 dpi
(README.md:45-51) — it reads zones a human chose in the repair bench, in its own venv, never
marker-env, and is not a pipeline lane.

## The figure-triage lever file (external to the repo)

`C:\Users\Bndit\ml\library\figure-triage.txt` (20 lines; signed Rab, S106) is the operator's
file for P-1: `mode=caption` plus 7 thresholds — `min_area_pt2`, `vector_min_paths`,
`cluster_gap_pt`, `text_coverage`, `words_per_line`, `table_overlap`, `accounted_for` — with
ranges enforced; anything unparseable falls back to the signed default AND is named in the
report, never used silently (its own header). Read at figure_coverage.py:156. Two limits:
caption triage keys on a `FIGURE N.N` caption regex
(figure_coverage.py:169), so it is **publisher-convention-dependent** — inert on books that
never print "FIGURE N.N" (recorded for Cybernetics, sessions/S106-desktop-2026-08-20.md:144) —
and it **only discriminates on a correct page map**: on the unrepaired IV map the same triage
promotes 167 of 239 uncovered pages (numerator: pages promoted; denominator: 239 uncovered;
conditions: shipped tool, unrepaired map), so treat caption mode as an ordering, not a
precision claim, until the SYM-050 repair is wired (figure-triage.txt header).

## The measurement-language law — docs/34

"A rate must carry its numerator, its denominator, and its conditions, or it may not be stated
at all" (docs/34-measurement-language.md:23-24). Prefill and decode are different physics —
prefill routinely runs 3–10× decode tok/s, so a blended "tok/s" says almost nothing
(docs/34:43-44). The standing unit trap: ollama's API reports every duration in
**nanoseconds** (docs/34:128-133) while llama.cpp's `timings.*_ms` are **milliseconds**
(docs/34:141-143) — a converter that assumes one for the other is wrong by 10⁶. This page's
own numbers follow that law; where a denominator is genuinely two-valued (the verdict census)
both are printed.

## SYM-049 — diagrams can fragment before clustering

Zero-area paths are dropped before clustering (`if _rect_area(r) <= 0: continue`,
figure_coverage.py:451 — the docstring's `:300` and SYM-049's `:428` are stale line refs to
the same statement). A pure horizontal/vertical connector has zero area, so it never joins the
boxes it connects; a spread-out flow diagram fragments into sub-threshold pieces and is missed
entirely — a false negative inside the instrument built to find false negatives. Two measured
specimens: Cybernetics p34 (54 drawings, 27 zero-area, largest cluster 541 pt² vs
`min_area_pt2` 4900) and p78 (clusters of 2 paths vs `vector_min_paths` 4), with p35 as the
control that DOES flag (SYMPTOM-INDEX.md row SYM-049; figure_coverage.py:37-46). The fix is
clustering that follows stroke geometry — not a threshold nudge (OPEN-TASKS.md B10).

## Open items

- OPEN-TASKS.md **A18** — wire the SYM-050 page-map repair into the shipped tool.
- OPEN-TASKS.md **A4** — P-1's host (in-converter vs out-of-band re-score): Rab's signature.
- OPEN-TASKS.md **A7** / E-slate **P-6** — record (or defer-with-criteria) the generative-SR ban.
- OPEN-TASKS.md **B4** — `windows-converter/` (all three instruments) is outside CI's lint set.
- OPEN-TASKS.md **B10** — stroke-geometry clustering for SYM-049.
- OPEN-TASKS.md **B23** — 219 of 239 IV uncovered pages never adjudicated; other anchors unmeasured.
- OPEN-TASKS.md **D2** — re-measure P-1 on a clean post-S60 bundle (delegated, never collected).
- E-slate **P-2** — the #598 tripwire, not built; specimen count contested.
- SYMPTOM-INDEX.md rows **SYM-049**, **SYM-050** — both OPEN.
