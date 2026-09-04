export const meta = {
  name: 'lead-hunt-read',
  description: "Read the leads Rab hunted against the six-row conversion spec: tests first, then the line where the number is computed; measure what can be measured on his specimens; Fable verifies licence/VRAM/offline claims against the repos' own files",
  phases: [
    { title: 'Read', detail: 'five lanes by spec row, in parallel', model: 'sonnet' },
    { title: 'Verify', detail: 'Fable: every licence/VRAM/offline claim checked at source; measurements re-run; ranked list', model: 'fable' },
  ],
}

const REPO = 'C:/Users/Bndit/Projects/file-portal'
const OUT = 'C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/d6f7a30f-66e5-40d2-a905-b2dd64ee7f44/scratchpad/leads'
const MENV = 'C:/Users/Bndit/ml/marker-env/Scripts/python.exe'
const PAPER_TXT_CMD = `PYTHONIOENCODING=utf-8 ${MENV} "C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/d6f7a30f-66e5-40d2-a905-b2dd64ee7f44/scratchpad/pdf_text.py" "C:/Users/Bndit/Downloads/2401.11874v2.pdf" <lo> <hi>`

const GROUND = `
GROUND. File Portal (Rab's local-first document-conversion pipeline: Marker 1.10.2 + surya 0.17.1 →
markdown; a local qwen3:8b analyst; a fidelity audit against a pymupdf witness; Obsidian vault).
One RTX 3080, 10 GB VRAM (~8.3 GB free when idle). Offline by design. Rab hunted twenty leads;
your job is to READ, not to trust. Repo: ${REPO}.

THE SPEC — a lead is only a lead if it lands on one of these rows with a measurement on Rab's
own specimens through Rab's own audit. Otherwise it is a vendor quoting itself.
 #1 TABLES in born-digital UNTAGGED PDFs — rebuild grids from glyph geometry / rulings, not only
    layout-model boxes. Specimen: held Damodaran 4e (C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e).
    Measure: SYM-056's 61 unterminated \\begin{array} → how many with candidate X (latex_balance).
 #2 DEGENERATION PRECISION (SYM-067) — a loop detector that is table-aware. Planted pair: must NOT
    flag Damodaran's empty-cell grid, must STILL flag the S27 Beer OCR loops.
 #3 SCAN-vs-CLEAN LANE — detect OCR overlays by TEXT RENDER MODE 3/7 per span (ISO 32000-2 9.3.6),
    replacing a font-name regex at convert_and_ship.py:744-779. Measure: 10 of 10 lanes correct
    on the anchor corpus (C:/Users/Bndit/ml/library/anchor/*/manifest.json carries the lane).
 #4 READING ORDER WITHOUT A TREE — column/flow ordering from geometry. Ground truth: the tagged
    specimens in C:/Users/Bndit/Downloads (Well-Tagged-PDF-WTPDF-1.0.pdf, ISO_32000-2_sponsored_EC3.pdf)
    whose structure tree declares the order (docs/52 measured divergence 2/57 and 15/60 pages
    against Marker's geometric order). Marker's block records now persist page+bbox (J24,
    windows-converter/marker_blocks.py) — an XY-cut over those is a few dozen lines.
 #5 BLANK CROPS (SYM-053) — needs building, not a lead. Note anything that helps, do not chase.
 #6 A BETTER RECONSTRUCTOR — same books, same fidelity_audit.py, same denominators. Chandra OCR 2
    weights are on disk (10.6 GB BF16, unloadable by marker-env's transformers 4.57.6);
    docling is installed in C:/Users/Bndit/ml/docling-env.

MECHANICAL TRIAGE, already measured 2026-09-04 via the GitHub API (stars · days since push · licence · language):
  PdfPig 2556·0·Apache-2.0·C#   surya 21346·13·Apache·py   PaddleOCR 88836·43·Apache·py
  EasyOCR 29968·272·Apache·py   Qwen3-VL 19900·216·Apache·ipynb   deepdoctection 3257·1·Apache·py
  unstructured 15389·0·Apache·HTML   marker 39505·3·Apache·py (Rab's baseline)
  DISCARDED on facts: zerox (cloud), llama-parse-py (cloud), colpali (retrieval), xy-cut-tree
  (2886 d, no licence), BobLd/DLA (1068 d, no licence, C# resources), inuwamobarak/nougat
  (notebook, 1055 d), anyantudre/Florence-2 (notebook, 792 d), PDFImageRetriever (755 d, 3★),
  ReadingBank (dataset), qyhou/curated-DLA (list), go-exiftool (GPL, Go, metadata), the
  YousifHisham table notebook (4 d, 0★, no licence).
  THE PAPER: arXiv 2401.11874v2 "Detect-Order-Construct" (Wang, Hu, Zhong, Sun, Huo — MSRA,
  2024): page-object detection → reading order → hierarchy construction; benchmark Comp-HRDoc
  (github.com/microsoft/CompHRDoc). Text: ${PAPER_TXT_CMD} (35 pages, "--------- PAGE n ---------" markers).

HOW YOU READ A REPO (Rab's sixty-second rule, then the deep read):
  1. LICENSE file itself, not the API field. requirements/pyproject: what it pulls (torch? CUDA?).
  2. Does it run OFFLINE on ≤ 10 GB VRAM or CPU? Find the model sizes in the code/model card.
  3. THE TESTS FIRST. Does it plant a known input and assert a known output? A repo that only
     has green checkmarks is a tautology. Quote a test that would catch a real regression.
  4. THE LINE WHERE THE HEADLINE NUMBER IS COMPUTED. If the README says 95 %, find the eval
     script and name the denominator. No denominator, no trust.
  5. Fetch via WebFetch (github.com raw/blob URLs work; use raw.githubusercontent.com for files).
     gh is NOT authenticated here. Do not clone into the repo; clone into ${OUT}/<name> if you
     must, and say so.

HOW YOU WORK — this project's signed law for subagents:
  TAG EVERY CLAIM (Observed / Verified / Inferred / Intended / Unknown). A number is re-measured,
  never quoted. DEVIATION IS THE REPORT. A failed fetch is UNREAD, never "no". NEGATIVE CONTROL:
  if you measure something on a specimen, also measure the case that must fail. DECLARE YOUR
  RESIDUE. NO GPU: the pipeline is idle and stays idle; anything you run is CPU-only pymupdf /
  python on already-converted files. Write ${OUT}/<lane>.md (create ${OUT}). Do not touch
  ${REPO} except to READ.
`

const LEAD = {
  type: 'object', additionalProperties: false,
  required: ['name', 'spec_rows', 'verdict', 'licence_at_source', 'offline_vram', 'test_quality',
             'headline_number_and_denominator', 'what_it_gives_file_portal', 'smallest_measurement', 'tag'],
  properties: {
    name: { type: 'string' },
    spec_rows: { type: 'array', items: { type: 'string' } },
    verdict: { type: 'string', enum: ['MEASURE_NEXT', 'PORT_THE_ALGORITHM', 'BAKE_OFF_CANDIDATE', 'IDEA_ONLY', 'DISCARD'] },
    licence_at_source: { type: 'string', description: 'from the LICENSE file, quoted' },
    offline_vram: { type: 'string', description: 'model sizes / CPU-able, with the file you read it in' },
    test_quality: { type: 'string', description: 'one test that would catch a real regression, quoted, or "none found"' },
    headline_number_and_denominator: { type: 'string' },
    what_it_gives_file_portal: { type: 'string' },
    smallest_measurement: { type: 'string', description: 'the exact command/specimen/metric that would make it a lead' },
    tag: { type: 'string', enum: ['Observed', 'Verified', 'Inferred', 'Unknown'] },
  },
}
const LANE_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['lane', 'leads', 'measured_on_specimen', 'report_file', 'residue'],
  properties: {
    lane: { type: 'string' },
    leads: { type: 'array', items: LEAD },
    measured_on_specimen: { type: 'string', description: 'anything you actually ran on one of Rab\'s files: command, result, negative control - or "nothing run" and why' },
    report_file: { type: 'string' },
    residue: { type: 'string' },
  },
}

const LANES = [
  { key: 'A-reading-order', model: 'sonnet', brief: `LANE A — READING ORDER WITHOUT A TREE (spec #4) — and the paper.
Read: (1) the paper 2401.11874v2 in full (35 pp, the text command is in GROUND) — what Detect-Order-
Construct actually does for ORDER (the relation-prediction head, the inputs it needs, whether
weights/code exist beyond the Comp-HRDoc benchmark repo — check github.com/microsoft/CompHRDoc);
(2) UglyToad/PdfPig's Document-Layout-Analysis wiki and the algorithms it names (XY-cut, Docstrum,
RLSA, nearest-neighbour ordering, RecursiveXYCut in PdfPig.DocumentLayoutAnalysis) — these are
PORTABLE ALGORITHMS, not a dependency (C#); (3) datalab-to/surya's reading-order / layout model:
what it orders, on what input, and whether Marker 1.10.2 already uses it (read marker's
providers/builders for 'order' or surya layout usage — the installed package is at
C:/Users/Bndit/ml/marker-env/Lib/site-packages/marker/).
THEN MEASURE: J24 persists Marker's blocks with page+bbox. Write a ~50-line recursive XY-cut over
block bboxes (CPU, python, no GPU) and run it on the WTPDF specimen's pages using pymupdf
get_text("dict") blocks as stand-ins; compare its order to the DECLARED order from the structure
tree (docs/52's probe_k_order.py in ${REPO}/prototypes/pdf-structure/probes/ already extracts the
declared order — reuse it). Report pages-differing / pages-total for XY-cut vs Marker's geometric
order vs declared. Negative control: a synthetic two-column page where naive top-to-bottom is
provably wrong and XY-cut is right.` },
  { key: 'B-tables', model: 'sonnet', brief: `LANE B — TABLES IN BORN-DIGITAL UNTAGGED PDFs (spec #1).
Read: PaddlePaddle/PaddleOCR (PP-StructureV3 / SLANet table recognition: model sizes, CPU viability,
what it outputs — HTML? cells with spans?), deepdoctection (which table detectors/recognisers it
wraps — Table Transformer? — and its weights' sizes and licences), Unstructured-IO/unstructured
(its table strategy: hi_res uses which model? does it need the cloud for tables?), datalab-to/surya's
table_rec (Rab's baseline already ships it — is Marker 1.10.2 using it? read marker's table
processor), and docling's TableFormer (installed at C:/Users/Bndit/ml/docling-env — read its
package, do not run it on GPU).
THEN MEASURE what can be measured without a GPU: on the held Damodaran bundle, count the
\\begin{array} environments per page from the markdown (latex_balance's method,
${REPO}/windows-converter/fidelity_audit.py) and map them to source pages; render NOTHING. Report
which pages carry the 61 unterminated arrays so a bake-off knows where to look. The question each
candidate must answer: does it rebuild a grid from GLYPH GEOMETRY (rulings, x-alignment) or only
from a layout model's box? Rab's failing pages are dense financial tables with empty cells.` },
  { key: 'C-scan-lane', model: 'sonnet', brief: `LANE C — THE SCAN-vs-CLEAN LANE (spec #3) and the OCR engines.
The principled test from ISO 32000-2 9.3.6: an OCR overlay is text drawn in render mode 3 (or 7),
invisible. Rab's converter decides the lane with a font-name regex /glyphless|invisible|ocr/ plus an
invisible-span ratio (convert_and_ship.py:744-779, read it).
MEASURE FIRST, on Rab's corpus, CPU-only pymupdf 1.28 (${MENV}): does pymupdf expose the render
mode? Try page.get_texttrace() (spans carry a 'type' / render field) and get_text("rawdict") flags,
on one scan-lane work and one clean-lane work from C:/Users/Bndit/ml/library/anchor/ (the
manifest's 'lane' field tells you which is which; the source PDFs are referenced there — if a
source PDF is not on disk, say UNREAD). Report per work: spans with render mode 3/7 over total
spans, and whether that alone reproduces the manifest's lane for all 10 works. Negative control:
a born-digital clean PDF must read ~0 invisible spans.
THEN READ the engines: JaidedAI/EasyOCR and PaddleOCR's PP-OCRv4/v5 — sizes, CPU speed claims WITH
denominators, licences at source, whether either is a plausible second OCR reader for a scan
(the only way a scan gets a witness that is not itself). Also the exiftool idea: PDF Producer /
Creator metadata as a scan signal — pymupdf's doc.metadata already has it; measure it on the 10
works and say whether it discriminates. No repo needed for that.` },
  { key: 'D-reconstructors', model: 'sonnet', brief: `LANE D — RECONSTRUCTORS AND VLMs FOR THE BAKE-OFF (spec #6).
Read: QwenLM/Qwen3-VL — which sizes exist, which fit 8.3 GB free at 4-bit, whether GGUF/llama.cpp
mmproj builds exist, the document-parsing prompt the model card recommends, and the licence at
source. Then the discards Rab handed over, each in two lines WITH the reason and anything worth
stealing: getomni-ai/zerox (cloud, but read its page-image → markdown prompt), run-llama/
llama-parse-py (cloud), illuin-tech/colpali (retrieval — but ColPali's page-image embeddings could
be a SYM-053 blank-page detector: say whether that is real or a stretch), anyantudre/Florence-2
(the notebook is dead; is Microsoft's Florence-2 itself — MIT, ~0.8 B — a document OCR reader
worth a bake-off slot on this card?), inuwamobarak/nougat (dead notebook; is facebookresearch/
nougat alive, and what does it do for MATH-heavy pages that Marker does not?).
Produce THE BAKE-OFF ROSTER: for each candidate — VRAM at the precision that fits, licence, what
it emits (markdown? bboxes? confidence?), and whether it can be scored by fidelity_audit.py's
witness comparison unchanged. Chandra OCR 2 is already on the roster (on disk, 5B, needs a
separate env). Marker is the baseline. Nothing runs on the GPU in this lane.` },
  { key: 'E-frameworks', model: 'sonnet', brief: `LANE E — THE FRAMEWORKS AND THE HONEST DISCARD LIST.
Read deepdoctection and Unstructured-IO/unstructured as FRAMEWORKS (not for tables — Lane B has
that): what they add over Marker for a local-first pipeline — layout detection models (which,
sizes, licences), the pipeline abstraction, evaluation tooling (does either ship a benchmark
runner with denominators?), and the honest cost (dependency weight: count what pip would pull).
Then UglyToad/PdfPig as a C# port of PDFBox: is there anything in its low-level PDF access
(render modes, marked content, structure tree) that pymupdf lacks — or is it Lane A's algorithms
only? Then write the DISCARD LIST for every lead the mechanical triage rejected, one line each,
with the fact that rejects it and one sentence on whether any idea inside is worth stealing
(e.g. go-exiftool → the Producer-metadata scan signal, which Lane C measures). Finally: the
YousifHisham table notebook — open it (raw .ipynb via WebFetch), say in three lines what it does
and whether any cell contains a technique Rab's pipeline lacks.` },
]

phase('Read')
log(`Read: ${LANES.length} lanes`)

const read = await parallel(LANES.map((L) => () =>
  agent(`${GROUND}\n\n${L.brief}\n\nWrite ${OUT}/${L.key}.md and return the structured object.`,
    { label: `read:${L.key}`, phase: 'Read', model: L.model, schema: LANE_SCHEMA })
))
const lanes = read.filter(Boolean)
log(`${lanes.length}/${LANES.length} lanes returned`)

const digest = lanes.map((l) => `--- ${l.lane} (${l.report_file}) ---
${(l.leads || []).map((x) => `  [${x.verdict}] ${x.name} · ${x.spec_rows.join(',')} · ${x.tag} · lic: ${String(x.licence_at_source).slice(0, 60)} · vram: ${String(x.offline_vram).slice(0, 80)}`).join('\n')}
measured: ${String(l.measured_on_specimen).slice(0, 500)}
residue: ${String(l.residue).slice(0, 300)}`).join('\n\n')

phase('Verify')

const VERIFY_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['claims_checked', 'measurements_rerun', 'ranked_leads', 'build_first', 'report_file', 'residue'],
  properties: {
    claims_checked: {
      type: 'array', description: 'at least 12: every licence, VRAM, offline and headline-number claim, checked at the repo\'s own files',
      items: {
        type: 'object', additionalProperties: false,
        required: ['lane', 'claim', 'checked_against', 'verdict'],
        properties: {
          lane: { type: 'string' }, claim: { type: 'string' }, checked_against: { type: 'string' },
          verdict: { type: 'string', enum: ['CONFIRMED', 'WRONG', 'OVERSTATED', 'UNREAD'] },
        },
      },
    },
    measurements_rerun: { type: 'array', items: { type: 'string' }, description: 'every specimen measurement a lane ran, re-run by you: command -> result -> matches?' },
    ranked_leads: {
      type: 'array', description: 'most valuable first, each with the spec row, the verdict you endorse, and the ONE measurement that makes it a lead',
      items: {
        type: 'object', additionalProperties: false,
        required: ['rank', 'name', 'spec_row', 'verdict', 'one_measurement', 'why_this_rank'],
        properties: {
          rank: { type: 'integer' }, name: { type: 'string' }, spec_row: { type: 'string' },
          verdict: { type: 'string' }, one_measurement: { type: 'string' }, why_this_rank: { type: 'string' },
        },
      },
    },
    build_first: { type: 'string', description: 'the single thing to build next, bounded, with its specimen and its planted negative control' },
    report_file: { type: 'string' },
    residue: { type: 'string' },
  },
}

const verify = await agent(
  `${GROUND}

YOU ARE THE VERIFIER, AND YOU ARE FABLE. Five lanes have read twenty leads. Their digest:

${digest}

Read every lane report under ${OUT}/ in full. Then, YOURSELF, not by reading their reports:
  1. Check every licence claim against the repo's LICENSE file (raw.githubusercontent.com), every
     VRAM/size claim against the model card or the code that loads weights, every "offline" claim
     against requirements (does anything phone home? an API key in the config?), and every headline
     number against the eval script's denominator. At least 12 claims, chosen adversarially.
  2. Re-run every measurement a lane ran on Rab's specimens (Lane A's XY-cut vs declared order;
     Lane C's render-mode counts and the Producer-metadata test; Lane B's page map of the 61
     arrays). CPU only. Quote your result beside theirs.
  3. Rank the leads. The rank is by (what it fixes on Rab's ACTUAL failing pages) ÷ (cost to
     measure it), and a lead that cannot be scored by fidelity_audit.py on the held/anchor corpus
     ranks below one that can.
  4. Name the ONE thing to build first — bounded, with its specimen and a planted negative
     control — in the shape Rab signs things: one sentence he can say yes to.
Write ${OUT}/VERIFIED.md, most-severe-first, and return the structured object.`,
  { label: 'verify:fable', phase: 'Verify', model: 'fable', schema: VERIFY_SCHEMA }
)

return { lanes, verify }
