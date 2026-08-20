# 41 · Conversion completeness — the integration plan

**Status: OPEN — nothing in this file is signed.** The signature slots are docs/37 §3 items
6–9. Filed S97 (Desktop, 2026-08-20), inside the open think-tank session.

**Provenance.** Rab's commission, his words: *"Read this against file portal, and see what
should be planned and integrated, goal is to have a very successful turnout for conversions,
while specifying options and variability for determining decisions, based on differing
reasons."* Inputs: the external research artifact (**docs/42**, archived from Downloads) and a
grounding investigation run by an Opus agent in an isolated worktree against the **installed**
stack (marker-pdf 1.10.2 · surya-ocr 0.17.1 · pymupdf 1.28.0), full report **Appendix A**.
Epistemic tags in the appendix (`[O]` Observed / `[V]` Verified / `[I]` Inferred) are the
investigator's; the orchestrator independently re-verified four load-bearing claims at filing
(marked ✓ in §1). Design frame per the commission: **decision variables with the reasons that
pick between them — not a single prescription.**

---

## §0 The goal, decomposed

"A very successful turnout for conversions" is four measurable properties, in order of how
well the pipeline serves them today:

1. **Text survives.** SERVED — Survival Audit + degeneration gate, calibrated (docs/15 §9.2),
   live, and `audit-mode.txt` currently reads `enforce` ✓ with 4 bundles in `held/`.
2. **Figures survive.** UNSERVED — no coverage semantics anywhere. The one raw count that
   exists (`asset_delta`/`embedded_images`, in every manifest since 2026-07-20) renders
   nowhere: two of the glass detector's 64 unsigned glitches. And it is a category error as a
   gate (§2 P-1).
3. **Nothing transmutes silently.** UNSERVED — the #598 class (figure OCR'd into prose) defeats
   both existing gates *by construction*: more text, not less; no repetition. Our corpus
   already holds a specimen (§1, `bojieli`).
4. **Every knob is a measured operating point, not a belief.** PARTLY — DPI is at marker
   defaults; grounding shows the default is *already clipping* one of our seven books (§2 P-5).

The first property is why the factory works. The second and third are why this plan exists:
they are the only components of docs/42 with **no prior art anywhere and a documented failure
class live in our own anchor/**.

## §1 What grounding changed — read this before trusting docs/42

Confirmed **on our stack** (installed-source citations in Appendix A):

| docs/42 claim | Status |
|---|---|
| Layout gets `highres=False` unconditionally | CONFIRMED — `marker/builders/layout.py:89` (1.10.2; the doc's `:136` is another version) |
| surya `IMAGE_DPI 96` / `IMAGE_DPI_HIGHRES 192` | CONFIRMED verbatim, `surya/settings.py:15-16` |
| Marker crops the rendered page; never extracts XObjects → coverage-not-equality | CONFIRMED — `marker/renderers/__init__.py:49-53`, mode `highres` |
| Only `Picture`/`Figure` blocks become images; a chart classified `Text`/`ComplexRegion` is prose by construction | CONFIRMED — `marker/renderers/__init__.py:18-20`. This IS the #598 surface |
| Degeneration thresholds `zlib<0.20 AND trigram≥40` | CONFIRMED — `fidelity_audit.py:57-60,287` (plus a second signal the doc missed: repeated-line run >20) |
| Analyst thresholds `doc<0.995 OR run≥25 words` | CONFIRMED — `fidelity_audit.py:68-69,428-432` (analyst stage only; convert stage is report-only by signed policy) |
| The vector blind spot | CONFIRMED LIVE — `Cybernetics`: **0** embedded rasters, **92** figures found by Marker. Every raster enumerator reports "nothing to lose" on our most common case |
| The #598 hole | CONFIRMED LIVE — `bojieli`: 105 source rasters → 4 output images, `degeneration=False`, verdict `flag` (never parks, never pulses) |

Refuted or materially changed **on our stack**:

1. **Bug #617 (batch entrypoint drops images) is moot** — we invoke `marker_single.exe`
   (`convert_and_ship.py:82` ✓), never the batch CLI.
2. **`page_needs_highres()` does not exist in marker-pdf 1.10.2** — both renders are built for
   every page unconditionally (`marker/builders/document.py:41-47`). The doc's "lever 1"
   describes a different marker.
3. **We are NOT on the RF-DETR fast-layout path.** surya 0.17.1 ships only the VLM
   `FoundationPredictor` layout task with aspect-preserving `scale_to_fit`. The "byte-identical
   tensor at any DPI" argument does not apply to us — the DPI lever is live here.
4. **The layout pixel ceiling is 1024×1024 = 1,048,576 px, not 6.29 MP.** Measured on the real
   corpus: usable `lowres_image_dpi` headroom runs **−9 % to +228 %**, determined by page
   geometry. One book (Beer, *DIAGNOSING THE SYSTEM*, 9.44×14.64 in) is **already downscaled
   at the default 96 DPI** (ceiling 87.1). A global DPI bump is the wrong shape of lever.
5. **"CPU-side on the ThinkPad" is architecturally impossible as written.** The source PDF
   never crosses the seam — `ship()` tars only the bundle; the PDF stays in desktop
   `drop/done/`. The ThinkPad also lacks every named instrument (no declared poppler, Java,
   pdfplumber — not even rapidfuzz). The desktop already has pymupdf + rapidfuzz installed
   *and load-bearing*.
6. **"Nothing does this" overstates it by half for us** — the xref-deduped source raster count
   has been measured on every book for a month (`fidelity_audit.py:344,383-384` ✓), stored in
   every manifest, and shown to nobody. Item 1 is partly a *wiring* job.

Bonus defect found on the way, filed as **SYM-044**: both `marker_version` stamp sites do
`getattr(marker, "__version__", "unknown")`, and marker-pdf 1.10.2 has no `__version__` (the
package has no `__init__.py` at all ✓) — so every manifest ever written carries
`"marker_version": "unknown"`, and one third of the F-02 `.done` identity gate is inert
(`"unknown" == "unknown"` matches across engine upgrades). One-line fix
(`importlib.metadata.version("marker-pdf")`), slots naturally into Stage 2.

## §2 The decision frames

Constraints that bind every frame: projection law (Python computes, widget renders) · converse
projection law (docs/29 — a new key that renders nowhere is a new GLITCH) · card mutex (time
inside `convert_and_ship.py` is card-lock time) · docs/34 measurement language · docs/15 §8 (an
audit crash never fails a conversion) · docs/15 §12 is SIGNED (exactly two signals may reach
`fail`; adding one is a signature event) · docs/15 §9 step 3 (false alarms shown to Rab
verbatim before anything may pulse terracotta).

### P-0 · The wiring slice — surface what is already measured

*What:* disposition and render `asset_delta` + `embedded_images` (manifest keys since
2026-07-20; glass glitches today). *Effort S. Zero new measurement, zero risk.*

| Option | Reason to pick it |
|---|---|
| **(a) Render on the Assay card** (delta chip beside the survival line) | The number starts teaching us its false-positive shapes *before* P-1 designs the real semantics; converse-projection debt paid |
| (b) Sign REPORT-silent in `observability/dispositions.json` | If Rab judges the raw delta too misleading to show (see the `Best Practices` −416 case) — an honest "measured, deliberately not surfaced" |

*Recommendation:* (a), labeled with its own caveat (informational, not a verdict input — the
docstring at `fidelity_audit.py:152-156` already says this correctly).
*Rab signs:* which option; nothing else.

### P-1 · The figure/vector completeness audit — the unserved survivor

*What:* per-book coverage check — does each source figure region have some output asset whose
page+region overlaps it? Coverage by bbox overlap, **never** count equality (`Best Practices`:
465-page scan, delta −416 means "OCR worked", not "figures lost"). Vector figures need
`page.get_drawings()` clustering — our most common case has zero raster XObjects.

**Decision variable 1 — host** (the load-bearing one):

| Option | Reason to pick it | Cost |
|---|---|---|
| **(a) Desktop, in-converter** at the `_audit_convert_safe` seam (`convert_and_ship.py:998`) | Only point where source PDF + markdown + assets are all in scope; zero new plumbing; verdict lands in the same manifest pass | Every audit second extends the card-lock (mutex held for process lifetime) |
| (b) Desktop, out-of-band re-score over `anchor/<bundle>` × `drop/done/<pdf>` (the `fidelity_audit.main()` shape) | No card-lock cost; the only shape that can also **back-fill the existing corpus**; where a JVM pass could live without punishing conversions | Needs an orchestration trigger + a rule for joining bundle↔source; verdicts arrive after ship |
| (c) ThinkPad, with a **precomputed source inventory** (small JSON of figure regions, computed desktop-side, carried in the manifest) | Preserves docs/42's zero-desktop-time intent without shipping gigabytes | Changes the bundle contract three modules depend on; ThinkPad deps undeclared; the seam's "exporter copies bytes, does not read them" doctrine bends |

**Decision variable 2 — instrument:**

| Option | Reason to pick it |
|---|---|
| **PyMuPDF-only**: `get_image_info(hashes=True, xrefs=True)` + `get_drawings()` density clustering | Already installed, already load-bearing; needs no new platform dependency; covers raster AND a vector heuristic |
| + PDFFigures 2.0 | Best published vector-figure recall (0.936–0.980 precision on CS corpora) — but needs a **JVM on the desktop** (absent today, its own adoption ritual), and its recall on uncaptioned book plates is untested — our corpus is exactly book plates |
| + poppler `pdfimages -list` | The doc's "spine" — but poppler is absent on both hosts, and pymupdf's xref walk already gives us object-ID dedup |

**Decision variable 3 — verdict posture:** report-only (→ at most `flag`) vs gate (→ `fail`).
docs/15 §6's law: *all thresholds ship report-only until calibrated*. And note the live state:
`audit-mode.txt` = `enforce` — a gating signal parks books **on day one**.

**Decision variable 4 — back-fill:** pre-S60 anchored bundles carry doubled asset page numbers
(`Investment Valuation`: assets to `_page_2553_` on 1,356 pages). Any corpus back-fill must
gate on `converted_at` or re-run the `out_of_range_assets` tripwire, or it poisons itself.
Also: three page namespaces coexist (0-indexed assets, 1-based audit pages, 1-based seams) —
the join must reconcile them explicitly.

*Effort:* M (PyMuPDF-only) / L (JVM admitted). *Design home:* docs/15 §5's existing "Asset
ledger" bullet, corrected from count-equality to coverage; coordinated edits §6, §7, §9, §12.
*Recommendation:* host (a) + PyMuPDF-only + report-only, with (b) added later purely for
back-fill; measure our own vector-recall before admitting a JVM.
*Rab signs:* all four variables.

### P-2 · The #598 tripwire — figure transmuted to prose

*What:* a source figure region with **no** overlapping output asset **and** an unexplained
text-density spike in that region → a named tripwire. Both halves computable from data already
in hand once P-1 exists (witness pages are already extracted per-page).

| Option | Reason to pick it |
|---|---|
| **Flag-only localizer** (joins the report-only tripwire list) | §12 stays untouched; the Bench gains a new zone class to show Rab; zero risk of parking good books on an uncalibrated signal |
| Gate (third member of §12's fail list) | Only if calibration shows near-zero false alarms AND Rab decides a transmuted figure is worse than a held book. §12 is SIGNED at exactly two fail signals — this is a signature event by constitution |
| A third framing Rab may prefer: **is it even wrong?** | For a text-first Obsidian vault, a chart rendered as prose is arguably degraded-but-searchable. If Rab rules it acceptable-with-a-note, the tripwire becomes a receipt field, not a verdict |

*Effort:* M (the calibration per §9 step 3 is the real cost). *Depends on P-1.*
*Recommendation:* flag-only until §9 calibration has run on the full anchor corpus.
*Rab signs:* gate vs localize vs receipt-note; thresholds; whether the Assay card grows a new
zone `kind`.

### P-3 · RETAS / Flexible Character Accuracy — the text-loss locator

*Grounding's key fact:* the existing scorer is already a near-sibling (12-word windows, anchor
index with frequency cap, rapidfuzz ≥90, run merging, CJK path, reverse-containment
anti-hallucination). RETAS would add an LCS backbone and reading-order tolerance — it is a
*refinement of a served property*, not a gap.

| Option | Reason to pick it |
|---|---|
| **Defer behind P-1/P-2** | The unserved gap is figures, not text; replacing a calibrated scorer re-opens §9 across the corpus and breaks comparability of every recorded `doc_survival` |
| Add-a-lane (second scorer beside the first) | Two independent checks; but doubles audit time under the card mutex |
| Replace | Only with a re-calibration budget and a `SCHEMA_VERSION` bump so old numbers aren't silently reinterpreted |

*Recommendation:* defer, recorded here so it isn't re-discovered.
*Rab signs:* only if promoted out of deferral.

### P-4 · LLM as adjudicator — never as searcher

docs/42's own evidence is the constraint: AbsenceBench 69.6 F1 ceiling, MissingBench 44–75 %,
deterministic beats VLM-judge by +15.2 F1. The LLM may only *adjudicate spans a deterministic
locator has already marked*, per-page, layout supplied.

*The natural home already exists:* the Repair Bench (`prototypes/repair-bench/bench.py`) —
source PDF, zone cards, evidence-voting locate, page renders, an Ollama assist call. The
converter is the wrong host (one-process law; the adjudicator competes for the 3080).

| Option | Reason to pick it |
|---|---|
| **Advisory-only in the Bench** (verdict never touches `fidelity.verdict`) | Honest to the measured ceiling; GPU use is interactive and Rab-present, so the mutex/chat-hold machinery already governs it |
| Verdict-influencing | Requires everything docs/42 says fails; would need its own signature and calibration |
| Local qwen3 vs Gemini | Local: one-process law + no key handling. Gemini: F-13 key rules + link-fence; only if local recall proves insufficient |

*Effort:* M on Bench scaffolding. *Recommendation:* advisory-only, local, after P-1/P-2 give
it marked spans to adjudicate. *Rab signs:* whether an LLM verdict may ever gate; engine
choice; GPU budget.

### P-5 · DPI as a measured experiment — the sharpened version

Grounding flipped this from "maybe useless" to "live lever, wrong shape": the VLM layout path
makes `lowres_image_dpi` real, but the ceiling is ~1.05 MP and one book is already clipped at
the default. `marker_single` accepts `--lowres_image_dpi` today — zero marker-side changes.

| Option | Reason to pick it |
|---|---|
| **(i) Cheap measured probe** on the clipped book (Beer *DIAGNOSING*, ceiling 87.1 DPI): convert at default vs at-the-budget, score both with the existing audit | One book, bounded GPU time, answers "does clipping cost us anything" — the delta nobody has published; docs/42's own build-order 5 says measuring it on our corpus is the genuinely new thing |
| (ii) Per-page render-to-the-budget (`dpi = sqrt(budget / page_area_in²)`) | The *correct* lever the measurement points at — but a converter change, and only justified if (i) shows a real delta |
| (iii) Leave it | If (i) shows nothing, record the null result in docs/15 §9 style and stop |

*Constraints:* docs/34 (numerator/denominator/conditions, A-B-A discipline where order effects
bite — SYM-035's lesson) · GPU time serialized under the mutex · **SYM-039**: the `ocr_dpi`
frontmatter stamp is derived-not-typed; any DPI override must rework that derivation in the
same commit or the stamp becomes a lie.
*Effort:* S for (i), M to docs/34 standard. *Recommendation:* (i) first; (ii) only on evidence.
*Rab signs:* GPU budget, corpus subset, what "better" means (doc_survival? figure coverage
once P-1 exists? heading recovery?), and (i)→(ii) promotion.

### P-6 · Generative SR — the standing ban

No SR exists anywhere in the pipeline, and that is the correct state (docs/42: fabricated
glyphs are fluent — the one failure our compression/trigram gate cannot see by design).

| Option | Reason to pick it |
|---|---|
| **Standing ban, force_ocr-style** (a sentence in docs/15 §10 + the register) | The failure mode is invisible to every gate we own; a ban is the only zero-cost defense |
| Deferred-with-criteria | If Rab wants the PreP-OCR-style document-restoration door left ajar: admission requires a held-out ground-truth set AND a near-exact character diff against a no-SR lane |

*Effort:* S — a documentation act. *Rab signs:* which force.

## §3 Sequencing — three options, picked by what hurts most

The Stage 2 slot (docs/37 §1) already queues "asset tripwire · out-of-range posture" — this
slate **expands an existing open item**, it does not jump the queue.

- **Option A — completeness-first** (recommended if unseen figure loss is the pain, and the
  corpus census says it is: two live specimens): P-0 wiring (one sitting) → P-1 PyMuPDF-only
  report-mode + §9 calibration → P-2 flag-only → fold results into Stage 2's asset-posture
  signature. SYM-043's one-line fix rides the first converter commit.
- **Option B — Stage-2-first** (if regression risk is the pain): converter tests + CI land
  before any new audit code enters `convert_and_ship.py`; the completeness slate becomes
  Stage 2's second half, protected by the tests it waited for.
- **Option C — measurement-first** (if scan-lane quality is the pain): P-5(i) probe on the
  clipped Beer book next GPU sitting; completeness follows. Cheapest first result, and the only
  one that could change *conversion* quality rather than *accounting* quality.

These are not exclusive — A and C compose in one sitting (P-0 is CPU-side while the P-5 probe
holds the card). B is the only one that sequences *against* the others.

## §4 Explicitly not planned

- **#617 mitigation** — moot on `marker_single` (§1.1).
- **A marker/surya upgrade** — nothing here needs one; SYM-043's fix makes a future upgrade
  *safe* (the `.done` gate starts working), which is prerequisite, not motive.
- **Poppler/pdfimages adoption** — pymupdf's xref walk already serves; revisit only if P-1
  calibration finds pymupdf missing inline images that matter.
- **RETAS now** (P-3 deferred) · **LLM-as-searcher** (never, by evidence) · **SR** (banned or
  gated, P-6).

---

## Appendix A — the grounding report, verbatim

*Opus investigator, isolated worktree, S97 2026-08-20. Read-only; no GPU touched. Its worktree
was checked out at an ancient merge, so all citations are against the live checkout and the
live marker-env — noted in its own scope note.*

# Grounding report: `conversion-completeness-audit-FINDINGS.md` vs. the File Portal codebase

**Scope note:** the assigned worktree (`.claude/worktrees/agent-add27e72b4365dbcd`) is checked out at commit `7c006f2`, an ancient merge that predates `windows-converter/`, `SYMPTOM-INDEX.md`, `sessions/`, and `docs/11`–`39`. All citations below are against the **live checkout** `C:\Users\Bndit\Projects\file-portal\` and the **live marker-env** `C:\Users\Bndit\ml\marker-env\`. Nothing was modified; no GPU process was started.

**Epistemic tags** per docs/21 §1: `[O]` Observed (read in source) · `[V]` Verified (I ran a probe) · `[I]` Inferred.

---

## A) CONVERT STAGE FACTS

### A1. Where marker is invoked — and which entrypoint

**We use `marker_single`, not the batch `marker` CLI.** `[O]`

- `C:\Users\Bndit\Projects\file-portal\windows-converter\convert_and_ship.py:82`
  ```python
  MARKER = Path(r"C:\Users\Bndit\ml\marker-env\Scripts\marker_single.exe")
  ```
- Single invocation site: `convert_and_ship.py:671-681` (`subprocess.Popen`), called from `_run_marker()` (`:636`), which is itself the *only* Marker launcher — used by both the whole-book path (`:927-928`) and every chunked slice (`:833-835`).
- The chain above it: `watch_and_convert.py:152-166` spawns `convert_and_ship.py` as a child with `PYTHONIOENCODING=utf-8`; the widget spawns the watcher (`windows-widget/src-tauri/src/watcher.rs:152`).
- `marker.exe`, `marker_chunk_convert.exe`, `marker_server.exe`, `marker_gui.exe` all exist in the env `[V]` but appear nowhere in the repo `[O]`.

> **Verdict on marker bug #617 (batch entrypoint drops images `marker_single` keeps):** **does not apply to us.** We are on the `marker_single` side of that bug.

### A2. Every marker/surya config we set

The **complete** argv, assembled at `convert_and_ship.py:671-674` + `route()` at `:550-562`: `[O]`

```
marker_single.exe <engine_src.pdf>
  --output_dir <work>/marker-out
  --output_format markdown
  --recognition_batch_size 32          # RECOGNITION_BATCH, :90 (or 8/16/32 per-slice lever, :827-828)
  [--strip_existing_ocr]               # only on lane=scan/untrusted_ocr_layer, :554
  [--page_range <start>-<end>]         # 0-indexed, chunked books only, :674 / :835
```

That is **all of it.** Everything else is marker/surya defaults.

| Lever the findings doc names | Our setting | Citation |
|---|---|---|
| `highres_image_dpi` | **not set** → default **192** | `marker/builders/document.py:22-25`; read back for the frontmatter stamp at `convert_and_ship.py:960-962` |
| `lowres_image_dpi` | **not set** → default **96** | `marker/builders/document.py:18-21` |
| `disable_image_extraction` | **not set** → `extract_images = True` | `marker/renderers/__init__.py:21`; parser at `marker/config/parser.py:56-61,106-107` |
| `force_ocr` | **never passed.** Policy is `--strip_existing_ocr` on untrusted layers only | `convert_and_ship.py:12-14, 553-554`; banned per memory `segment-convert-marker` |
| OCR-layer detection (render mode 3) | **ours, not marker's** — `probe()` uses `pymupdf.get_texttrace()` span `type == 3`, majority-of-spans rule + font-name secondary | `convert_and_ship.py:520-547` |
| `--disable_tqdm` | **deliberately NOT set** — the stall monitor and Room progress bar parse surya's tqdm lines | `convert_and_ship.py:101-103` (`_TQDM_RE`), `:649-658` |
| `--workers` / `--disable_multiprocessing` | not set. `--workers` is a `marker` (batch) flag; `marker_single` has none | `marker/config/parser.py:51-55` |
| `SURYA_INFERENCE_PARALLEL` / any `SURYA_*` / `TORCH_*` env | **none set anywhere** in repo or widget spawn env | `[V]` grep over `windows-converter/*.py`, `windows-widget/src-tauri/src/*.rs` — the only env var set is `PYTHONIOENCODING=utf-8` |
| Batch sizes | `recognition_batch_size` 32 (unchunked) / 8·16·32 lever (chunked); layout batch = marker default 12 on CUDA | `convert_and_ship.py:90, 177-191`; `marker/builders/layout.py:59-63` |

**Also relevant:** `marker_single` auto-exposes **every** builder/processor/renderer attribute as a CLI flag via `CustomClickPrinter.parse_args` (`marker/config/printer.py:46-58, 82-92`) `[O]`. So `--lowres_image_dpi`, `--highres_image_dpi`, `--extract_images`, `--disable_tqdm` are all reachable **without any change to marker** — the DPI experiment (build item 5) is a pure argv change.

### A3. Installed versions + validation of the doc's P1 claims ON OUR STACK

Interpreter: `C:\Users\Bndit\ml\marker-env\Scripts\python.exe`, **CPython 3.12.13** `[V]`

| Package | Version | Evidence |
|---|---|---|
| **marker-pdf** | **1.10.2** | `[V]` `marker_pdf-1.10.2.dist-info`; `importlib.metadata.version('marker-pdf')` |
| **surya-ocr** | **0.17.1** | `[V]` `surya_ocr-0.17.1.dist-info` |
| pymupdf | 1.28.0 (MuPDF 1.29.0) | `[V]` |
| pypdfium2 | 4.30.0 · pdftext 0.6.3 · rapidfuzz 3.14.5 | `[V]` |
| torch | 2.11.0+cu128 · torchvision 0.26.0+cu128 · transformers 4.57.6 | `[V]` |
| **pdfplumber** | **absent** | `[V]` `ModuleNotFoundError` |

Now the four specific checks:

**(i) Does `marker/builders/layout.py` use `highres=False` unconditionally? — YES.** `[O]`
```
C:\Users\Bndit\ml\marker-env\Lib\site-packages\marker\builders\layout.py:87-92
    def surya_layout(self, pages):
        self.layout_model.disable_tqdm = self.disable_tqdm
        layout_results = self.layout_model(
            [p.get_image(highres=False) for p in pages],     # ← line 89, unconditional
            batch_size=int(self.get_batch_size()),
        )
```
The doc cited `layout.py:136`; on **1.10.2 it is line 89**. The claim itself is **CONFIRMED on our stack.**

**(ii) Does `page_needs_highres()` exist? — NO.** `[V]` Grep for `page_needs_highres|needs_highres` across the entire installed `marker/` tree returns **zero hits.** Instead, `marker/builders/document.py:41-47` builds **both** renders for **every** page unconditionally:
```python
lowres_images  = provider.get_images(provider.page_range, self.lowres_image_dpi)
highres_images = provider.get_images(provider.page_range, self.highres_image_dpi)
```
> **REFUTED on our stack:** the findings doc's "Actionable lever 1" — *"`highres_image_dpi` only fires on Tables / Forms / TOC / Equations / ChemicalBlocks via `page_needs_highres()`"* — describes a marker version we do not run. On 1.10.2, every page gets a 192-DPI render, and it is consumed by OCR (`builders/ocr.py:125`), equations (`processors/equation.py:63`), tables (`processors/table.py:93,96,105,148`), LLM processors (`processors/llm/__init__.py:77`) **and figure extraction** (`renderers/__init__.py:49-53`).

**(iii) `surya/settings.py` IMAGE_DPI values — CONFIRMED verbatim.** `[O]`
```
C:\Users\Bndit\ml\marker-env\Lib\site-packages\surya\settings.py:15-16
    IMAGE_DPI: int = 96            # Used for detection, layout, reading order
    IMAGE_DPI_HIGHRES: int = 192   # Used for OCR, table rec
```
(Our converter does not read these directly — it reads marker's `DocumentBuilder.highres_image_dpi`, `convert_and_ship.py:960-962`. The comment there is accurate.)

**(iv) Which layout predictor is default in OUR version? — the VLM/foundation path, NOT RF-DETR.** `[O]`

`surya/layout/__init__.py:16-24` — `LayoutPredictor.__init__(self, foundation_predictor: FoundationPredictor)`; `__call__` (`:38-62`) runs `self.foundation_predictor.prediction_loop(..., task_names=[TaskNames.layout], max_sliding_window=576, max_tokens=500, tqdm_desc="Recognizing Layout")`. There is **no RF-DETR module** in surya 0.17.1 (`surya/layout/` contains only `__init__.py`, `label.py`, `schema.py`) `[V]`.

> **This flips the doc's P1 conclusion for us.** The doc's core mechanical argument — *"Surya's fast-layout path (RF-DETR) resizes every page to a fixed 704×704, aspect ratio destroyed — a 96 DPI and a 300 DPI render produce a byte-identical tensor"* — **does not describe our installation.** We are on the path the doc itself calls "the one where `lowres_image_dpi` is meaningful."

**The real ceiling, measured.** Resizing is `scale_to_fit` (`surya/common/surya/processor/__init__.py:154-190`) — a **pixel-budget, aspect-preserving** resize via `cv2.INTER_LANCZOS4`, applied at `surya/foundation/__init__.py:184-187` with `max_size = self.tasks[task]["img_size"]`. For layout that is `(1024, 1024)` (`surya/foundation/__init__.py:95-99`) `[O]` — a budget of **1,048,576 px**, not 6.29 MP.

Measured on the real corpus (`C:\Users\Bndit\ml\library\drop\done\*.pdf`, page-1 MediaBox via pymupdf) `[V]`:

| Book | Page size (in) | px @ 96 DPI | Layout budget | Ceiling DPI |
|---|---|---|---|---|
| DIAGNOSING THE SYSTEM (Beer) | 9.44 × 14.64 | **1,274,169** | 1,048,576 | **87.1 — already clipped** |
| Cybernetics Book of Models | 11.00 × 8.50 | 861,696 | " | 105.9 |
| Investment Valuation (Damodaran) | 8.50 × 11.00 | 861,696 | " | 105.9 |
| claude-code-up-and-running | 8.50 × 11.00 | 861,696 | " | 105.9 |
| BRAIN OF THE FIRM (Beer) | 6.11 × 9.31 | 524,342 | " | 135.8 |
| Best Practices for Equity Research | 2.47 × 4.29 | 97,441 | " | 314.9 |

*Numerator: rendered page pixels at the stated DPI. Denominator: 1024×1024 = 1,048,576 px, the `TaskNames.layout` `img_size` product. Conditions: surya-ocr 0.17.1 foundation `LayoutPredictor`, aspect ratio preserved, `scale_to_fit` clamps only when over budget; page geometry from page 1 MediaBox, pymupdf 1.28.0; n = 7 books, the full `drop/done/` corpus at 2026-08-20.*

> **The honest operating-point statement for build item 5:** usable `lowres_image_dpi` headroom on our own corpus ranges from **−9 % (one book is already being downscaled at the default)** to **+228 %**, and is determined entirely by page geometry, not by anything a global DPI setting can know. A single global `lowres_image_dpi` bump is the wrong shape of lever; a per-book "render to the budget" computation is the right one. Nobody has measured what that is worth — the doc is correct that this is unpublished.

### A4. Where converted output lands

**Marker's own output** (`marker/output.py:80-101`) `[O]`: into `<work>/marker-out/<engine_stem>/` —
- `<stem>.md`, `<stem>_meta.json`, and one `.jpeg` per extracted image (`settings.OUTPUT_IMAGE_FORMAT = "JPEG"`, `marker/settings.py:23`).

**Our bundle** — assembled at `convert_and_ship.py:944-1020` in `<work>/.part-<sha16>/`, containing **exactly three things** `[O]`:
1. `assets/` — only `.jpeg/.jpg/.png` copied over (`:949-951`)
2. `<clamped bundle name>.md` — frontmatter (`render_frontmatter`, `:497-515`) + link-rewritten body (`:1019`)
3. `manifest.json` (`:1020`)

Verified on disk `[V]`: `C:\Users\Bndit\ml\library\anchor\Cybernetics_Book_of_Models-v4.6b-complete\` = `{...}.md` (159 KB) + `assets/` (92 files) + `manifest.json` (6.8 KB).

**Manifest fields** (`convert_and_ship.py:970-989`) `[O]`: `source`, `source_sha256`, `engine`, `lane`, `lane_reason`, `chars_per_page_detected`, `pages`, `converter_version`, `marker_version`, `converted_at`; plus optional `chunking` (`:986`), `supersede` (`:449-452`), `fidelity` (`:46`), `analyst` (`:1006`).

**Downstream**: `ANCHOR` copytree → `C:\Users\Bndit\ml\library\anchor\<bundle>` (`:1330-1333`) → `_enforce_hold` (`:1339`) → `ship` (`:1340`).

**`.done` marker semantics** — this is the **chunk-slice resume marker**, not a bundle marker `[O]`:
- Written at `convert_and_ship.py:857-861` into `.chunk-work/<sha16>/slice-<start>-<end>/.done`, carrying `{source_sha256, page_range, wall_s, batch, engine_args, marker_version}`.
- Published atomically: `staging.rename(slice_dir)` (`:862`) — *".done exists only on a complete slice"*.
- Read back by `_done_identity_mismatch` (`:752-763`): a slice is resumable only if `source_sha256`, `engine_args`, **and** `marker_version` all match. `batch` is deliberately **excluded** (it is a perf knob, docs/37 §4 T2c).
- Legacy/unparseable `.done` → treated as mismatch → loud re-convert (`:812-820`).

> ### ⚠ BONUS FINDING — the `marker_version` identity gate is inert
> `convert_and_ship.py:781` and `:979` both do `getattr(marker, "__version__", "unknown")`. **marker-pdf 1.10.2 has no `__version__` attribute** `[V]`:
> ```
> has __version__: False   ·   getattr default: 'unknown'   ·   importlib.metadata.version('marker-pdf') = '1.10.2'
> ```
> Confirmed in the live corpus `[V]`: every anchored manifest reads `"marker_version": "unknown"`.
> **Two consequences:** (1) the manifest's engine-provenance stamp — the bundle's "papers", dispositioned **REPORT** at `observability/dispositions.json` — is blank on every book we have ever converted; (2) F-02's repair is **one-third inert**: a marker upgrade will not invalidate a stale `.done`, because `"unknown" == "unknown"`. Fix is one line (`importlib.metadata.version("marker-pdf")`). This is a clean **SYM-043** candidate.

### A5. Image handling today

**Yes — our output includes extracted figure images, and the references are written into the markdown.** `[O]`/`[V]`

The chain, end to end:
1. **Marker crops the rendered page** — it does **not** extract embedded image XObjects. `marker/renderers/__init__.py:49-53`:
   ```python
   def extract_image(self, document, image_id, to_base64=False):
       image_block = document.get_block(image_id)
       cropped = image_block.get_image(document, highres=self.image_extraction_mode == "highres")
   ```
   with `image_extraction_mode = "highres"` (`:22-25`) → **crops the 192-DPI page render at the layout bbox**.
   > This **CONFIRMS the doc's design correction #1** ("Coverage, not equality… the source inventory and the output inventory are not the same kind of object and will never hash-match") on our exact stack.
2. **Only two block types become images**: `image_blocks = (BlockTypes.Picture, BlockTypes.Figure)` (`marker/renderers/__init__.py:18-20`). Everything else — including a chart that the layout model classified as `Text` or `ComplexRegion` — is rendered as prose. **This is precisely the #598 surface.**
3. **Filenames carry the absolute source page.** `BlockId.to_path()` (`marker/schema/blocks/base.py:79-80`) → `_page_{page_id}_{BlockType}_{block_id}` + `.jpeg`. Verified on disk `[V]`: `_page_10_Figure_6.jpeg`, `_page_13_Picture_10.jpeg`, types ∈ {`Figure`, `Picture`}.
4. **Marker writes `![](_page_N_Figure_M.jpeg)`** into the `.md` (`marker/output.py:87-101`).
5. **We rewrite to Obsidian embeds** — `rewrite_image_links()`, `convert_and_ship.py:464-474`:
   ```python
   _IMAGE_LINK = re.compile(r"!\[[^\]]*\]\(\s*<?([^)>\s]+)>?(?:\s+\"[^\"]*\")?\s*\)")
   ...
   return f"![[assets/{Path(target).name}]]"
   ```
   Called once at `:995`, before the audit and before the analyst.
6. Verified in the vaulted markdown `[V]`: 92 `![[assets/...]]` references against 92 files in `assets/` — a 1:1 match on that book.

**The page-number namespace trap (important for any source↔output join):** `[V]`
- `_page_N_` is **0-indexed** — `claude-code-up-and-running` (104 pp) has `min_page=0`.
- `fidelity_audit` page numbers are **1-based** — `enumerate(witness_pages, start=1)` (`fidelity_audit.py:355`).
- `chunking.seams` are **1-based absolute** (`convert_and_ship.py:887-889`).
- Three page namespaces already coexist in one manifest. Any completeness audit joining source pages to output assets must reconcile them explicitly.

**And one live data hazard** `[V]`: the anchored `Investment Valuation` bundle (1,356 pages, converted `2026-08-01`) has assets numbered up to **`_page_2553_`**, in bands `0,2,4,6,8,10,12` (×200) — the doubled-offset signature described in the comment at `convert_and_ship.py:260-272`. The current code adds no offset and carries the `out_of_range_assets` tripwire (`:282-287`), so today's behaviour is correct — but **pre-fix bundles with lying page numbers are sitting in `anchor/` right now**. A completeness audit that back-fills over the existing corpus would be poisoned by them unless it gates on `converted_at` or re-runs the tripwire.

---

## B) EXISTING GATES

### B6. The degeneration gate

**Location:** `C:\Users\Bndit\Projects\file-portal\windows-converter\fidelity_audit.py:264-313` (`degeneration()`). CPU-only by design (docs/15 §8:157-158). `[O]`

**Thresholds — the doc's "`zlib<0.20 AND trigram≥40`" is CORRECT for the block rule:** `[O]`
```
fidelity_audit.py:57-60
    DEGEN_ZLIB_MAX      = 0.20
    DEGEN_TRIGRAM_MAX   = 40
    DEGEN_BLOCK_MIN_CHARS = 200
    DEGEN_LINE_REPEAT   = 20
fidelity_audit.py:287
    if ratio < DEGEN_ZLIB_MAX and mx >= DEGEN_TRIGRAM_MAX:
```
Per-paragraph (`markdown.split("\n\n")`, `:270`), blocks < 200 chars skipped, trigram is word-level or char-level for CJK (`:279-281`).

**Second, independent signal the doc does not mention:** a **contiguous repeated-line run** — `max_run > DEGEN_LINE_REPEAT (20)` over non-blank, non-table lines of length > 20 (`:298-306`). Either signal sets `flagged`.

**Documentation discrepancy worth knowing:** docs/15 **§12:274** (SIGNED 2026-07-20) still states the gate as `zlib < 0.20 **OR** trigram ≥ 40`; **§9.2:231** (measured 2026-07-21) supersedes it with **AND**, which is what the code does. §12 was never back-propagated. `windows-widget/src-tauri/src/room.rs:383` carries a comment recording that S78 caught the same label saying OR.

**What it flags / where verdicts land:** `[O]`
- Returns `{flagged, repeated_lines, md_lines, worst[:10]}` — each `worst` entry `{line, chars, zlib, max_trigram, excerpt}`.
- Lands in `manifest["fidelity"]["convert"]["tripwires"]["degeneration"]` + `["degeneration_detail"]` (`:379-381`), assembled by `build_fidelity_block` (`:454-459`).
- **It is one of exactly two signals that can reach `"fail"`** — `compute_verdict:436-437`, gating on either lane.
- Events: `audit/scored`, `audit/flagged` (`convert_and_ship.py:49-54`), plus `audit/verdict_fail` (`:344-345`) and `audit/held` — all into `C:\Users\Bndit\ml\library\events.jsonl` (`events.py:14`).
- **A byte-faithful port runs on the ThinkPad too**, report-mode only: `linux-converter/converter/degeneration.py:26-29,56`, invoked at `linux-converter/converter/main.py:188-201`.

### B7. The Survival Audit

**Location:** `C:\Users\Bndit\Projects\file-portal\windows-converter\fidelity_audit.py` (479 lines). Design record: `docs/15-survival-audit.md`. `[O]`

**Where it runs: on the DESKTOP, inside `convert_and_ship.py`, not on the ThinkPad.** `[O]`
- Convert stage: `_audit_convert_safe(src, body, lane, tmp_dir, manifest)` — `convert_and_ship.py:37-56`, called at **`:998`**, after `rewrite_image_links` and **before** any analyst pass.
- Analyst stage: `_audit_analyst_safe` — `:59-79`, called at `:1007` (inline) and `:1098` (the `--resume`/`--reanalyze` path).
- Both wrapped so an audit crash can never fail the conversion (docs/15 §8:162-164).

**Checks — the doc's "`doc<0.995 OR run≥25 words`" is CORRECT but applies only to the ANALYST stage:** `[O]`
```
fidelity_audit.py:68-69     ANALYST_DOC_FAIL = 0.995 ; ANALYST_RUN_WORDS = 25
fidelity_audit.py:428-432   if analyst_block ... doc_survival < 0.995 or any run.words >= 25 → "fail"
```
The **convert** stage has different, **report-only** numbers (`:63-67`): clean lane `CLEAN_PAGE_FLAG 0.85 / CLEAN_DOC_FLAG 0.97 / CLEAN_RUN_WORDS 50`; scan lane `SCAN_PAGE_FLAG 0.70 / SCAN_GARBAGE_FLAG 0.20`. These can only reach `"flag"` (`:439-450`), never `"fail"` — signed policy, docs/15 §12:278-281, *"They localize, they do not judge."*

**Per-page AND per-doc:** `[O]` per-page scores at `:355-368` (12-word non-overlapping windows, rapidfuzz `partial_ratio ≥ 90`), doc score = window-weighted mean (`:369`), omission runs = ≥2 adjacent failed windows merged (`_merge_runs`, `:218-237`).

**Enforce vs report lever:** `audit_mode()` reads `C:\Users\Bndit\ml\library\audit-mode.txt`, values `report`|`enforce`, default `report` (`convert_and_ship.py:306-317`). `_enforce_hold` (`:350-393`) parks a `fail` in `held/<sha16>/`. The `audit/verdict_fail` alarm is raised **before** the lever is consulted (`:319-348`, docs/30 §5.4).

> **LIVE STATE `[V]`:** `C:\Users\Bndit\ml\library\audit-mode.txt` currently reads **`enforce`**. `held/` currently contains 4 parked bundles. A new gating signal would therefore start parking books **immediately**, not theoretically.

### B8. Existing image/figure accounting anywhere in the pipeline

**Not absent — but weaker than the doc assumes, and currently invisible.** `[V]`

Exhaustive grep for `pdfimages|get_image_info|get_images|pdfplumber|PDFFigures|\.curves|\.rects|fitz|xref` across all `*.py` in the repo returns exactly two clusters:

1. **`fidelity_audit.py:151-165` — `extract_witness()`**, the only inventory in the pipeline:
   ```python
   for im in page.get_images(full=True):
       xrefs.add(im[0])
   return pages, len(xrefs)
   ```
   with an already-honest docstring (`:152-156`): *"Images are deduped by xref — `get_images` repeats an xref on every page it appears on, and Marker deliberately drops decorative/inline rasters, so this is an informational signal only (never a verdict input)."*
   → surfaces as two manifest keys, `fidelity_audit.py:383-384`:
   ```python
   "asset_delta": (asset_count - embedded_images) if asset_count is not None else None,
   "embedded_images": embedded_images,
   ```
   `asset_count` is supplied by `convert_and_ship.py:43-45` (a plain `len(assets/)`).
2. **`prototypes/repair-bench/bench.py:417-418, 869-875, 925-931`** — `fitz` used to *render* page crops for the Bench UI and `page.search_for()` highlight rects. Not inventory.

**Absent, confirmed `[V]`:** no `pdfimages`, no `get_image_info`, no `pdfplumber`, no PDFFigures, no curve/rect density anywhere in the pipeline.

**Design-doc precedent already exists.** docs/15 **§5:103-104** already names this dimension:
> *"**Asset ledger:** embedded raster count (pymupdf) vs. files in `assets/`. Report delta; images are out of scope for text survival but a large delta is a flag."*

> ### ⚠ CRITICAL — the existing image accounting is a **glass glitch**
> `[V]` I ran `observability/glass_detector.py` (read-only). It reports:
> ```
> ✗ 64 UNSIGNED GLITCH(ES) at 70 site(s) — computed, stored, reaching nobody:
>     ...
>     converter:asset_delta        windows-converter\fidelity_audit.py:383  (audit_convert)
>     converter:embedded_images    windows-converter\fidelity_audit.py:384  (audit_convert)
> ```
> Confirmed independently `[V]`: neither key appears in `windows-widget/src`, `windows-widget/src-tauri/src`, `prototypes/`, or `observability/dispositions.json` (which holds 10 signed dispositions, none of them these).
> **So: the pipeline has been measuring source-vs-output image counts on every book for a month, storing the number in every manifest, and showing it to nobody.** This is SYM-027's exact class, still live. Build item 1 is at least half a *wiring* job before it is a *building* job.

### The #598 hole — is it real on our stack? **Yes, and it is already measurable in our corpus.**

`[V]` Census of every anchored bundle (`C:\Users\Bndit\ml\library\anchor\*\manifest.json` + `len(assets/)`), 2026-08-20:

| bundle | lane | pp | assets | embedded (uniq xref) | asset_delta | doc_surv | degen | verdict |
|---|---|---|---|---|---|---|---|---|
| Best Practices for Equity Research | scan | 465 | 49 | **465** | **−416** | 1.0 | True | fail |
| DIAGNOSING THE SYSTEM (Beer) | scan | 184 | 91 | 348 | −257 | 0.9558 | True | fail |
| bojieli AI-agent-book | clean | 19 | 4 | **105** | **−101** | 0.7641 | **False** | **flag** |
| **Cybernetics Book of Models** | clean | 91 | **92** | **0** | **+92** | 0.6884 | True | fail |
| Investment Valuation (Damodaran) | clean | 1356 | 313 | 232 | +81 | 0.927 | True | fail |
| claude-code-up-and-running | clean | 104 | 12 | 9 | +3 | 0.9913 | False | flag |
| BRAIN OF THE FIRM · Designing with Freedom | scan | 439/116 | 63/36 | — | — | — | — | *(pre-audit, `fidelity: null`)* |

Three things this table proves on our own corpus, not in the abstract:

1. **The vector blind spot is real and is our most common case.** `Cybernetics`: **0 embedded raster XObjects, 92 figures found by Marker.** Every raster enumerator — `pdfimages -list`, `get_images`, `get_image_info` — would report *"no images to lose"* on this book. The doc's design correction #2 is confirmed live.
2. **The #598 class is real and the existing gates do not catch it.** `bojieli`: 105 source raster objects, 4 output images, `degeneration = False`, verdict **`flag`** — the softest possible outcome, and `flag` never parks a bundle and never pulses terracotta (docs/15 §12:278-281). 101 rasters unaccounted for, and the system's loudest statement about it is a chip nobody renders.
3. **`asset_delta` in its current form cannot be a gate.** `Best Practices` is a 465-page scan where *every page is one image* — `−416` means "OCR worked", not "figures lost". The count is a category error against a coverage question. This is exactly why the doc says **coverage semantics, bbox overlap, not equality** — and why the existing code correctly refuses to let it vote.

---

## C) THINKPAD / CPU-SIDE HOOK POINTS

### C9. Where a CPU-side source↔output audit could hook

> ### ⛔ THE LOAD-BEARING FINDING: **the source PDF never reaches the ThinkPad.**

The findings doc's build item 1 — *"Figure/vector completeness audit, **CPU-side on the ThinkPad**"* — is **architecturally impossible as written.** Four independent lines of evidence `[O]`:

1. `ship()` tars **only the bundle dir**: `convert_and_ship.py:1045-1047` → `tar -cf - -C <tmp_dir> .` where `tmp_dir = work / f".part-{sha16}"` (`:946`). The PDF working copy is its **sibling**, `work / f"{engine_stem}.pdf"` (`:914-916`) — outside the tar root.
2. `work` is a `TemporaryDirectory` (`:1326-1327`) — the copy is destroyed on process exit.
3. Only `(".jpeg", ".jpg", ".png")` enter `assets/` (`:949-951`).
4. Nothing in `linux-converter/converter/*.py` ever opens or expects a source PDF in a bundle.

**Where the source PDF actually lives after conversion:** `C:\Users\Bndit\ml\library\drop\done\<name>.pdf`, on the **Windows desktop only** — `watch_and_convert.py:169-173` (`shutil.move(pdf, DONE_DIR)`); failures to `drop/failed/`. `[O]`/`[V]` (7 PDFs present).

*(Caveat, for completeness: a PDF sent through the widget's `convert`/`convert-scan` tiles does briefly reach `~/file-portal/inbox/`, but the Linux converter **unlinks** it after publishing — `linux-converter/converter/main.py:232`, asserted by `tests/test_main.py:108`. The `documents` tile drops PDFs into `sorted/documents` but never touches the library pipeline.)*

**Which host holds what, at each stage:**

| Stage | Source PDF | Output .md | assets/ | manifest |
|---|---|---|---|---|
| Desktop, `convert()` in-flight (`convert_and_ship.py:998`) | ✅ `src` in scope | ✅ `body` in memory | ✅ `tmp_dir/assets` | ✅ in memory |
| Desktop, post-ship | ✅ `drop/done/` | ✅ `anchor/<bundle>/` | ✅ | ✅ |
| Desktop, `held/<sha16>/` | ✅ `drop/done/` | ✅ | ✅ | ✅ |
| **ThinkPad `library/staging/`** | ❌ **never** | ✅ | ✅ | ✅ |
| **ThinkPad vault (`Inbox/<slug>--<sha8>/`)** | ❌ **never** | ✅ | ✅ | ✅ |

> **Therefore the audit has exactly three viable placements, and only one is free:**
> **(a)** Desktop, inside `convert()` at the `_audit_convert_safe` seam (`convert_and_ship.py:998`) — the **only** point where source PDF, markdown body, and `assets/` are all simultaneously in scope. Zero new plumbing.
> **(b)** Desktop, a standalone re-scoring pass over `anchor/<bundle>/` × `drop/done/<source>` — the shape `fidelity_audit.py:465-479` (`main()`, `--pdf/--md/--lane/--asset-count`) already supports, and the shape the Repair Bench already uses.
> **(c)** ThinkPad — requires **either** shipping the PDF (new bytes over Tailscale, new vault-adjacent storage, and a change to a bundle contract that three modules depend on) **or** shipping a *precomputed source inventory* (a small JSON of figure regions computed on the desktop and carried in the manifest). (c)-with-inventory is the only version that preserves the doc's "zero VRAM on the ThinkPad" intent without moving gigabytes.

**The one-process constraint bites placement (a).** `[O]` `acquire_card_mutex()` is claimed at `main()` **before dispatch** (`convert_and_ship.py:1310`) and is *"Held for the process lifetime; the OS releases it at exit"* (`:200-203`). So **every second an audit spends inside `convert_and_ship.py` is a second the card stays locked against the next conversion and against the assistant.** The existing Survival Audit already pays this cost; a PDFFigures/JVM pass would compound it materially on a 1,356-page book. This is a genuine argument for placement (b) — a post-mutex, out-of-band re-score — and it is a decision only Rab can sign.

**ThinkPad exporter contract + `held/` mechanics** (for completeness) `[O]`:
- Exporter is a second watch inside the same converter process: `linux-converter/converter/main.py:304-311` → `linux-converter/converter/exporter.py`.
- Sequence: detect (`exporter.py:543-582`, atomic-rename publish + stability wait) → validate (`:223-234`) → git sync (`:239-240`) → supersede branch (`:247-316`) → dedup on full `source_sha256` against the **bare** repo (`:320-333`) → export to `Inbox/<slug60>--<sha8>/` (`:335-367`) → L12 gate (`:369-375`) → receipt (`:397-404`).
- **There is no `held/` on the ThinkPad.** A refused bundle simply *stays in `library/staging/`* (`exporter.py:258-265` `EXPORT-SUPERSEDE-HELD`, `:216-220` `EXPORT-FAIL`), retried by the **startup sweep** (`main.py:311`). Release is the sha-bound `bless.json` scp'd into the staging dir by `assay.rs:387-388`, honored at `exporter.py:256-287` — **`flag` only, never `fail`** (docs/15 §14.4, SIGNED 2026-07-25).
- Manifest fields the exporter reads: `source_sha256` (dedup key), `supersede{reason,from_verdict}`, `fidelity.verdict` (fail-closed — a *missing* block is not "pass", `:253`), `source`, `lane`, `degeneration.flagged` (→ receipt field). Everything else *"the exporter copies bundle bytes, it does not read them"* (`exporter.py:11-12`).
- Receipts: `~/file-portal/receipts.jsonl`, one JSON object per line `{ts, outcome, bundle, ...}` (`exporter.py:59,72-99`), torn-line healed (`:84-95`), pulled to the desktop by `receipts.rs:28,62-64`. **There is no `events.jsonl` on the ThinkPad.**

### C10. Tool availability

**On the Windows desktop, in/around the marker-env** `[V]`:

| Tool | Status | Evidence |
|---|---|---|
| **PyMuPDF / fitz** | ✅ **1.28.0** (MuPDF 1.29.0) — already a hard dependency, imported at `convert_and_ship.py:31` and `fidelity_audit.py` | `import pymupdf, fitz` OK |
| **rapidfuzz** | ✅ **3.14.5** — already the Survival Audit's matcher | `[V]` |
| **poppler / `pdfimages`** | ❌ **not present, not on PATH** | `command -v pdfimages` → nothing; `where pdfimages` → nothing |
| **`pdftotext`** | ⚠️ present but **xpdf 4.06 (Glyph & Cog)**, not poppler, at `C:\Program Files\Git\mingw64\bin\pdftotext.exe`. It is the **only** pdf tool in that dir — no `pdfimages`, `pdftoppm`, `pdffonts` | `pdftotext -v` |
| **pdfplumber** | ❌ absent | `ModuleNotFoundError` |
| **Java / JRE (for PDFFigures 2.0)** | ❌ **not present, not on PATH** | `command -v java` → nothing; `java -version` → not found |
| opencv-python-headless, numpy, scipy, scikit-learn, Pillow 10.4 | ✅ present (surya deps) | `[V]` dist-info |

**On the ThinkPad — repo evidence only, no ssh:** `[O]`

Declared: `watchdog >=4.0,<5`; `pymupdf4llm` pinned **1.28.0** (`linux-converter/requirements.txt:2`, `pyproject.toml:8`); **`pymupdf`/`fitz` used directly but never declared** — it arrives transitively via pymupdf4llm (`converter/engines.py:12,21,52,64`); `tesseract 5.5.2` + `tesseract-data-eng`, `pandoc 3.6` (`CLAUDE_README.md:1357`, `docs/10:87`); `git`, `python`, `rsync` (`scripts/linux/bootstrap-arch.sh:18`); Python `>=3.11` (`.pyc` are cpython-312).

**Unknown — not determinable from repo:** `pdfplumber` (zero hits), `poppler-utils`/`pdfimages` (zero hits), **`java`/JRE/JDK (zero hits)**, ghostscript/qpdf/pikepdf/ocrmypdf (zero hits). Notably **`rapidfuzz` is declared for the Desktop only** (`docs/20:241`) and appears in no linux requirements file — so even the *text-alignment* half of the doc's proposal has no declared dependency base on the ThinkPad. Actual installed versions there: Unknown; the repo says version truth lives in lockfiles that do not exist for the Linux lane (`docs/20:249-250`).

> **Net for build items 1 and 3:** every instrument the doc calls for is **absent on the host it names** and **present-or-one-`pip`-away on the host it rules out.** PyMuPDF + rapidfuzz — the two that matter most — are already installed, already imported, and already load-bearing on the desktop.

---

## D) FILING SURFACES

### D11. docs/37 §3 — the signature register

**Structural correction to the brief:** `docs/37-next-stage-plan.md` §3 is **not** a register of `F-xx` slots. It is a **5-item numbered list, lines 101–112**. "§3.1 / §3.2 / §3.3" are citation shorthand for *list items 1, 2, 3* — there is no `###` heading anywhere in docs/37. The `F-xx` ids live in **§2** (lines 76–99), a *verdict digest* table, not a signature register. Only **F-09** appears in both. `[O]`

§3 verbatim (101–112):
```
## §3 Signature register (Rab's, all OPEN at filing)

1. **F-09 semantics**: re-read per slice (...) ~or~ immutable-per-job (...).
   Fable recommends per-slice. **SIGNED per-slice (Rab, 2026-08-17, in-chat: "F-09
   per-slice signed") — built S94.**
2. **SYM-033 prevention + named mutex** (Stage 1's third bullet). **SIGNED (Rab,
   2026-08-17, in-chat: "Stage 1 GO with the mutex") — built S94.**
3. **Asset posture**: warn (today) vs fail/quarantine on out-of-range (Stage 2 encodes it).
4. Stage 2 GO · Stage 3 GO.
5. Standing from before tonight: docs/26 signature sheet (5) · stale-hold reap countersign ·
   docs/34 rule 8 · GLM second-reader · wrapper · SPOT_CHECK_EVERY 10→3–5.
```

**Entry format:** `N. **<bold subject>**: <option A> ~or~ <option B>. [Fable recommends X.] [**SIGNED <disposition> (Rab, <date>, in-chat: "<verbatim words>") — built S<n>.**]`
**Status vocabulary (complete):** `OPEN` (carried by the heading, not per-item) · `SIGNED` · `— built S<n>.` · `GO`. An unsigned item simply omits the SIGNED clause.

**§2 verdict vocabulary:** `CONFIRMED` / `PARTLY` / `KNOWN-SIGNED` (defined at 73–74), plus `CONFIRMED ×2`, `×4`, lowercase `confirmed`, `fair`. **Highest F-number: F-20** (line 96); **F-12 does not exist** (sequence jumps F-11 → F-13). Non-F ids: `C02`, `C25/C26`, `AppB`.

**The five stages** (§1, 27–69) and current GO state:
| Stage | GO state |
|---|---|
| Stage 0 — the truth repairs | executed S93 |
| Stage 1 — the hardening slice | SIGNED (§3.2), built S94, adopted |
| **Stage 2 — converter tests + CI** | **GO OPEN** (§3 item 4) — and §3 item 3 (asset posture) is its unsigned content |
| **Stage 3 — the verified seam** | **GO OPEN** (§3 item 4) |
| Stage 4 — the product | no GO recorded |
| Parked (SQLite, CDG, format expansion) | re-open only on stated criteria |

> **Directly relevant:** docs/37 line 50 already queues *"asset tripwire · out-of-range posture per Rab's warn-vs-fail word"* under **Stage 2**, and §3 item 3 is the **still-unsigned slot for it**. A figure-completeness proposal is not a new register entry — it is **an expansion of an existing, already-open one.**

### D12. SYMPTOM-INDEX.md

**Format:** six pipe-delimited columns, one physical line per row: `| ID | Symptom — what you notice | Root cause | Session | Status | Guard lives at |` (`SYMPTOM-INDEX.md:17`). `[O]`

**Filing rules:** header 1–15 (*"Read this file at every session open (it is part of MUSTER). A defect rediscovered is a MUSTER failure, not bad luck."*) and `## Adding a row`, lines 55–60: *"Write the Symptom column **for someone who has the symptom and not the cause**… If you cannot describe it without naming the cause, you don't yet understand the failure well enough to index it."* Append-only in spirit — revisions are appended in-cell as `**Update <date> (S<n>):** …`. File may be CRLF (SYM-029).

**Status vocabulary:** `` `Historical` `` · `` `fixed` `` / `` `fixed` <date> (S<n>) `` / `` `fixed` by rule `` / `` `fixed` by rule + guard `` · **`OPEN`** (bold) and `` `open` `` (lowercase) · `reference` · strikethrough-supersede. Session-column epistemic tags: `Observed` · `Verified` · `Intended` · `Historical` · `UNPROVEN` (ladder defined at `docs/21-session-closeout-contract.md:35-42`).

**Highest SYM in use: SYM-042** (`SYMPTOM-INDEX.md:70`, the no-lock `--resume` row). **→ next free id is SYM-043.** IDs 001–042 all present, no gaps, but **not in file order**; recent practice (040/041/042) appends at EOF, so a new row lands at line 71.

`SYM-027` (line 44) is the projection-glitch row and is **still OPEN** — its own closing criteria (2) and (3) are recorded as NOT MET. `SYM-041` and `SYM-042` are both OPEN-with-SIGNED-and-BUILT updates from S94.

### D13. docs/15 structure

Outline `[O]`: §0 Problem (9) · §1 Decision summary (24) · §2 Witness (49) · §3 Normalization (61) · §4 Core algorithm (73) · **§5 Tripwires (95)** · **§6 Stages and thresholds (112)** · **§7 Manifest schema (128)** · §8 Integration (155) · §9 Calibration plan (174) + §9.1 (187) + §9.2 (214) · §10 Deferred (248) · §11 External grounding (254) · **§12 Enforcement — SIGNED (266)** · §13 The Assay — widget projection (304) · §14 Supersede export (350).

**Where a completeness-audit extension would be documented — five coordinated places, in order:**
1. **§5 (95–110)** — the tripwire definition bullet. **The slot already exists**: *"**Asset ledger:** embedded raster count (pymupdf) vs. files in `assets/`. Report delta…"* (103–104). A figure/vector dimension is that bullet, corrected from *count-equality* to *coverage*.
2. **§6 (117–121)** — a Flag/Fail column entry, shipping report-only per §6:114 (*"ALL thresholds ship in report-only mode until calibrated"*).
3. **§7 (128–153)** — a key inside `"tripwires": { … }`; §7's title is the ownership rule: *"Python owns this; widget only renders."*
4. **§12 (271–281)** — the placement decision, **gates → `fail`** vs **report-only → at most `flag`**. §12 is **SIGNED**; promoting anything into the gating list needs Rab's signature. The report-only list is the default landing zone.
5. **§9 (174–246)** — calibration, with §9.1/§9.2 as the pattern for a dated subsection. **§9 step 3 is binding:** *"Present the flagged runs to Rab verbatim (excerpts, not just counts) — the tool must show its false alarms before it is allowed to pulse terracotta."*

Also: **§10 Deferred (248–252)** is where a dimension goes if it is *not* being built now; **§13 (315–329)** is where its Assay-card surfacing would be specced.

---

## E) INTEGRATION MAP — the doc's 6-item build order against our code

**Design laws that constrain every item:**
- **Projection law** — the widget reads; Python owns pipeline truth; levers write only single-writer files (`docs/20:372`, `docs/19:18`). Any new number is computed in Python, rendered in Rust/JS.
- **Converse projection law (docs/29)** — *every value the pipeline computes must reach a human or be signed silent*. Mechanically enforced by `observability/glass_detector.py` in the closeout ritual. **A new tripwire key that renders nowhere is a new GLITCH.** `convert_and_ship.py:338-339` names this: *"a new key would be a new undispositioned measurement (docs/29), which is the disease next door."*
- **One-process law / card mutex** — held from `main()` to process exit (`convert_and_ship.py:200-203, 1310`). Work added inside the converter extends the card lock.
- **Measurement language (docs/34)** — every number names numerator, denominator, conditions.
- **docs/15 §8** — an audit crash must never fail a conversion.
- **Nothing builds without a signed GO** — the slot for this work is **docs/37 §3 item 3 (Stage 2), currently unsigned.**

---

### ▸ Item 1 — Figure/vector completeness audit, CPU-side

| | |
|---|---|
| **Hook point** | `convert_and_ship.py:998` — the single `_audit_convert_safe(src, body, lane, tmp_dir, manifest)` call. Implementation lands in `fidelity_audit.py:341-393` (`audit_convert`), which already receives `pdf_path` and `asset_count`. Standalone re-score entry already exists at `fidelity_audit.py:465-479`. |
| **Already exists / overlaps** | `fidelity_audit.py:151-165` `extract_witness()` (xref-deduped raster count) · `fidelity_audit.py:383-384` `asset_delta`/`embedded_images` · `convert_and_ship.py:276-287` `asset_page()` + `out_of_range_assets()` — **page-attributed asset parsing already written and battle-tested** · docs/15 §5:103-104 the "Asset ledger" bullet · pymupdf 1.28 and rapidfuzz already installed. |
| **What blocks it** | **The ThinkPad placement in the doc is impossible** (§C9): no source PDF there, no poppler, no Java, no pdfplumber, `rapidfuzz` not even declared. On the desktop: poppler and Java are also absent — but `get_image_info(hashes=True, xrefs=True)` needs neither. |
| **Constraints** | Card mutex (audit time = card-lock time). docs/29 (must render or be dispositioned). docs/15 §8 (never raise). §9 step 3 (show false alarms before pulsing). |
| **Effort** | **M** for a PyMuPDF-only coverage audit (source figure regions from `get_image_info` ∪ vector-drawing clusters from `page.get_drawings()`, matched by bbox overlap against `_page_N_*` asset pages). **L** if PDFFigures 2.0 is admitted — that adds a JVM to the desktop, which is a new platform dependency with its own adoption ritual. **S** for the *wiring-only* slice: disposition `asset_delta`/`embedded_images` and render them on the Assay card. |
| **Decisions only Rab can sign** | (a) **Host**: desktop-in-converter (a) vs desktop-out-of-band re-score (b) vs ship-a-source-inventory-to-ThinkPad (c). (b) **Instrument**: PyMuPDF-only (`get_image_info` + `get_drawings` density) vs admit a JVM for PDFFigures 2.0. (c) **Semantics**: coverage-by-bbox-overlap vs the current count-delta. (d) **Coverage threshold** and whether it is per-page or per-doc. (e) **Report vs gate** — and note `audit-mode.txt` is **live at `enforce`**, so a gating signal parks books on day one. (f) **Back-fill posture** over `anchor/` — pre-S60 bundles carry doubled page numbers. |

---

### ▸ Item 2 — Close the #598 hole (figure-transmuted-to-prose)

| | |
|---|---|
| **Hook point** | Same as item 1, plus a second signal: text density per source page region. The witness text is already extracted per page (`fidelity_audit.py:151-165` returns `pages` list); `_score_page` (`:239-259`) already walks pages 1..N. The natural shape is a new key in the `tripwires` dict (`:379-391`) and a new clause in `compute_verdict` (`:411-451`). |
| **Already exists / overlaps** | **The doc's claim is CONFIRMED and measurable on our corpus** (§B8): `bojieli` — 105 embedded rasters, 4 assets, `degeneration=False`, verdict `flag`. Also confirmed: only `BlockTypes.Picture` and `BlockTypes.Figure` become images (`marker/renderers/__init__.py:18-20`) — a chart classified `Text` or `ComplexRegion` is prose by construction. Nothing today looks at that. |
| **Constraints** | docs/15 §12 is **SIGNED** and states exactly two signals may reach `fail`. Adding a third is a signature event, not a code change. The `flag`/`fail` split and the terracotta rule (docs/15 §8:168-170, *"terracotta ONLY on `fail`"*) both bind. |
| **Effort** | **M** — the two halves (no output image covering a source figure region **AND** unexplained text density in that region) are both computable from data already in hand. The calibration (§9) is the real cost, and §9 step 3 requires a verbatim false-alarm review with Rab before it may pulse. |
| **Decisions only Rab can sign** | (a) **Does it gate, or only localize?** — i.e. does it join degeneration + analyst-loss in §12's fail list, or the flag list. (b) Thresholds for "unexplained density spike". (c) Whether a `Text`-classified figure is even *wrong* for a text-first Obsidian vault, or an acceptable trade. (d) Whether the Assay card gets a new zone `kind` (the shape is `room.rs:290-300`, `kind:"zone"` children). |

---

### ▸ Item 3 — RETAS-style text alignment as the loss locator

| | |
|---|---|
| **Hook point** | `fidelity_audit.py:178-259` — `make_windows` / `_build_index` / `_fuzzy_hit` / `_merge_runs` / `_score_page`. This is **already a loss locator**, just a different algorithm. |
| **Already exists / overlaps** | Substantial. We already do: non-overlapping 12-word windows (`:41`, `:183-189`), an anchor index with a frequency cap (`FUZZY_ANCHOR_CAP = 50`, `:47`, `_build_index:192-201`), rapidfuzz `partial_ratio ≥ 90` (`FUZZY_PASS`, `:46`, `:202-216`), adjacent-failure run merging (`:218-237`), a CJK char-n-gram path (`:43-44, 179-182`), and reverse-containment anti-hallucination sampling (`:326-335`). **RETAS's "unique-word anchoring + LCS" is a near-sibling of what is already running** — the material additions would be reading-order tolerance (Flexible Character Accuracy) and the LCS backbone. |
| **Constraints** | docs/15 §12's calibration record (`0.76–0.96` survival on *acceptable* books) is the baseline any replacement must beat without re-failing good work. Changing the scorer changes every historical `doc_survival`, breaking comparability with the anchored corpus. |
| **Effort** | **M–L.** Not because RETAS is hard, but because replacing a calibrated scorer requires re-running §9 calibration across the corpus and re-interpreting every recorded number. |
| **Decisions only Rab can sign** | (a) **Replace vs. add-a-lane** — a second scorer beside the existing one is safer (two independent checks) but doubles the audit cost under the card mutex. (b) Whether `doc_survival` keeps its meaning across the change, or a new key + a schema version bump (`SCHEMA_VERSION = 1`, `fidelity_audit.py:39`). (c) Whether the born-digital embedded-text-layer "free second lane" is worth it given `probe()` already reads that layer (`convert_and_ship.py:523-547`). |

---

### ▸ Item 4 — LLM only as adjudicator, per-page, over marked spans

| | |
|---|---|
| **Hook point** | Not the converter. The natural home is **`prototypes/repair-bench/bench.py`**, which already has: the source PDF (`:417-418`), the markdown, zone/run cards, `locate_zone()` evidence-voting (`:481-491`), page-fraction highlight rects (`:471-479`), and an Ollama assist call (`:1134-1135`). Alternative: `windows-converter/analyst.py` — but that is a *rewriting* surface, not an adjudicating one, and its output is itself audited. |
| **Already exists / overlaps** | The Bench is already the "adjudicate a marked span, with layout, per-page" surface. The doc's constraint list ("never as searcher, never per-document, never layout-blind") describes what the Bench already is. |
| **Constraints** | **One-process law** — an LLM adjudicator competes for the 3080. The chat-hold / card-mutex machinery (`watch_and_convert.py:104-138`, `convert_and_ship.py:195-235`) already governs this and would have to be honored. **Link-fence** discipline from `analyst.py`. The doc's own evidence (AbsenceBench 69.6 F1; MissingBench 44–75 %) argues the LLM must never be the *detector*. |
| **Effort** | **M** given the Bench's existing scaffolding; **L** if it must serve the enforce lever. |
| **Decisions only Rab can sign** | (a) Whether an LLM verdict may ever influence `fidelity.verdict` at all, or is advisory-to-human only. (b) Local qwen3 vs Gemini (the link-fence and key-handling rules differ — F-13). (c) GPU budget and where it sits relative to the card mutex. |

---

### ▸ Item 5 — DPI as a measured experiment

| | |
|---|---|
| **Hook point** | `convert_and_ship.py:550-562` `route()` — append `--lowres_image_dpi <n>`. `marker_single` already accepts it (`marker/config/printer.py:46-58`). **Zero marker-side changes.** The A/B harness shape already exists: `backend_parity.py` (40 KB, measurement-language-enforcing, `docs/34`) and `fidelity_audit.main()` for scoring. |
| **Already exists / overlaps** | The doc's premise is **partly refuted and partly sharpened on our stack** (§A3): we run the VLM `LayoutPredictor`, not RF-DETR, so the lever *is* live — but the ceiling is **1,048,576 px (1024×1024)**, not 6.29 MP, and one of our seven books is **already over budget at the default 96 DPI**. Headroom on our corpus: **−9 % to +228 %**, geometry-determined. |
| **Constraints** | **docs/34 measurement language** — every number names numerator/denominator/conditions; no bare comparisons. **One-process law** — an A/B sweep is GPU time serialized against everything else. **`ocr_dpi` frontmatter stamp** (`convert_and_ship.py:954-964`) is derived-not-typed by design (SYM-039); if a DPI override is ever passed, that derivation becomes a lie and must be reworked in the same commit. |
| **Effort** | **S** to run the experiment (argv + existing scorer + existing harness). **M** to do it to docs/34 standard with a proper fixed-DPI baseline, n, and spread. |
| **Decisions only Rab can sign** | (a) GPU time budget for the sweep. (b) Corpus subset and what "better" means — `doc_survival`? figure-coverage (item 1)? heading-hierarchy? (c) **Global DPI vs. render-to-the-budget-per-page** — the measurement says the second is the real lever, and it is a different, larger change. (d) Whether the frontmatter DPI stamp changes shape. |

---

### ▸ Item 6 — Never admit generative SR without a ground-truth set

| | |
|---|---|
| **Hook point** | **None — and that is the correct state.** No SR, no upscaling, no image enhancement exists anywhere in the pipeline `[V]`. |
| **Already exists / overlaps** | The *policy* half already has a home and a precedent: `force_ocr` is a standing ban (memory `segment-convert-marker`; `convert_and_ship.py:12-14`), and the analyst stage already demonstrates the pattern the doc asks for — a near-exact character diff against a no-transform lane (`ANALYST_DOC_FAIL = 0.995`, `ANALYST_RUN_WORDS = 25`, `fidelity_audit.py:396-408, 428-432`). If SR were ever admitted, `audit_analyst()` is literally the function to point at it. |
| **Constraints** | docs/15 §12 is SIGNED; a new gate needs a signature. |
| **Effort** | **S** — this is a documentation act, not a build: a line in docs/15 §10 (Deferred) or a standing entry in the docs/37 §3 register recording the ban and its condition. |
| **Decisions only Rab can sign** | Whether to record the prohibition at all, and at what force (standing ban like `force_ocr`, vs. deferred-with-criteria like the §10 entries). |

---

## Summary of the corrections this grounding makes to the findings document

**Confirmed on our stack:** `layout.py` uses `highres=False` unconditionally (line 89, not 136) · surya `IMAGE_DPI 96 / IMAGE_DPI_HIGHRES 192` verbatim · marker crops the rendered page rather than extracting XObjects, so coverage-not-equality is right · the #598 class is real, and our own corpus contains a specimen (`bojieli`: 105 → 4, verdict `flag`) · the vector blind spot is real and is our *common* case (`Cybernetics`: 0 embedded, 92 figures) · degeneration thresholds `zlib<0.20 AND trigram≥40` are exactly as stated · analyst thresholds `doc<0.995 OR run≥25` are exactly as stated.

**Refuted or materially changed on our stack:**
1. **Bug #617 is moot** — we run `marker_single`, not the batch entrypoint.
2. **`page_needs_highres()` does not exist in marker-pdf 1.10.2** — both renders are built for every page, unconditionally.
3. **We are not on the RF-DETR fast-layout path.** surya 0.17.1 ships a VLM `FoundationPredictor` layout task with aspect-preserving `scale_to_fit`. The "byte-identical tensor at any DPI" argument does not apply to us.
4. **The scale_to_fit ceiling is ~1.05 MP, not 6.29 MP** — measured, that is ~106 DPI on a Letter page and **already exceeded at the 96-DPI default** on one of our seven books.
5. **The ThinkPad placement for item 1 is architecturally impossible** — the source PDF never crosses the seam, and the ThinkPad has no declared poppler, Java, pdfplumber, or even rapidfuzz. The desktop, by contrast, already has PyMuPDF and rapidfuzz loaded and load-bearing.
6. **"Nothing does this" overstates it for us by half** — `asset_delta` / `embedded_images` have been computed on every book since 2026-07-20. They are stored in every manifest, rendered nowhere, and undispositioned: two of the 64 unsigned glitches the glass detector reports today. Item 1 is partly a *wiring* job.

**Bonus finding, unrelated to the doc but found on the way:** `marker_version` is stamped `"unknown"` in every manifest ever written, because marker-pdf 1.10.2 has no `__version__` attribute — which also makes one third of F-02's `.done` identity gate inert. One-line fix; clean **SYM-043** candidate.

**Filing surfaces, ready:** next free symptom id is **SYM-043**; the signature slot for this work is **docs/37 §3 item 3 (asset posture, Stage 2) — already open, already Rab's, still unsigned**; the design home is **docs/15 §5** (the "Asset ledger" bullet already there), with coordinated edits to §6, §7, §12, §9.

**Live-state warnings for whoever builds this:** `audit-mode.txt` currently reads **`enforce`** and `held/` has 4 parked bundles — a new gating signal parks books immediately. Pre-S60 anchored bundles (e.g. `Investment Valuation`, 2026-08-01) carry doubled asset page numbers up to `_page_2553_` on a 1,356-page book, so any back-fill over `anchor/` must gate on that. And three page-number namespaces (0-indexed assets, 1-based audit pages, 1-based seams) coexist in one manifest today.
