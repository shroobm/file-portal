# The Repair Bench — prototype (Stage G, docs/19 §7)

**"The human IS the vision model."** (Rab, docs/18.) The Survival Audit can say *where* a
conversion went wrong — degeneration zones with line numbers, omission runs with pages — but
not what the page really held. A human can, in one glance. This bench puts the source-PDF page
and the markdown at the flagged zone side by side and makes the repair one gesture.

## What it does

- **Navigate by evidence**: the damage map + zone chips come straight from the held bundle's
  `manifest["fidelity"]` block; clicking a zone opens the page the line ratio predicts
  (`line / md_lines × pages`) — a seed for the human to refine with ◂ ▸, not a claim.
- **Repair = one gesture**: drag a rectangle on the page (server crops the 220-dpi raster), or
  Ctrl+V a screenshot. Either way the image lands in the bundle's `assets/` as
  `_repair_pN_k.png` (collision-safe), embedded at the zone as `![[assets/…]]` — the vault's
  own reference style — with a provenance record appended to `manifest["repairs"]`
  (`ts / zone_line / page / asset / mode / note / by`).
- **Re-score is a PREVIEW**: it re-runs `fidelity_audit.degeneration()` on the current text and
  reports repairs-vs-zones — it writes **no** fidelity block and changes **no** verdict.
  Whether a repair image earns audit credit is an **unsigned policy question**; Rab signs it
  (docs/19 §10) before any such credit exists in the real pipeline.
- **Inspect source evidence (OK-15 quarantine prototype)**: **◉ evidence** measures five
  independent PDF signals page by page — MuPDF warnings, logical page labels, a PyMuPDF/Xpdf
  reading-order comparison, a disposable all-OCG-off raster counterfactual, and embedded
  `/Thumb` metadata. Affected page buttons jump back to the source page. `partial` and
  `UNREAD` show their exact probe reasons; an absent `/Thumb` is measured absence, not failure.
  Every page-level `UNREAD` reason remains available in a bounded scroll surface. Pixels and
  extracted text are hashed/count-only in the report and are not retained.
- **Sandbox mode** (`--sandbox`) copies the bundle under `.sandbox/` and repairs the copy —
  how the acceptance harness runs, and how a first trial should.

## Run

```bash
# from prototypes/repair-bench, with the marker-env python (pymupdf lives there):
C:\Users\Bndit\ml\marker-env\Scripts\python.exe bench.py b6fbdd75f6242f53 --sandbox --token local-only-secret
# then open http://127.0.0.1:7077/?token=local-only-secret
```

The positional argument is a bundle directory or a bare sha16 resolved against
`ml\library\held\`. The source PDF is auto-found in `drop\done\` (override with `--pdf`).
Drop `--sandbox` to repair the real held bundle — Valentine is the designated first patient.

`acceptance.py` proves the loop end to end on a sandbox copy of the real Valentine (real
zones, real rasters, real stamps; the real bundle hash-verified untouched).

The token is required for every mutation and for the expensive evidence GET. The widget
generates and supplies its own token. The reading-order probe records the installed
`pdftotext` implementation and version; this Windows host currently supplies Xpdf 4.06, not
Poppler. Missing, failed, timed-out, non-UTF-8, or wrong-page-count oracle output is `UNREAD`.
A failed collection is cached in process as an explicit `UNREAD` report so repeated clicks do
not repay a 900-second failure; **↻ retry collection** is the deliberate retry. A concurrent
request returns `IN-PROGRESS` immediately and never starts a duplicate child.

## Quarantine (prototypes/ convention)

Disposable, zero pipeline coupling: nothing in the pipeline imports this; this imports only
`fidelity_audit` read-only for the preview. Graduation criteria (docs/19 §7): Rab uses it on
Valentine successfully — then it earns a widget surface and the audit-credit policy discussion.
OK-15 evidence is likewise held only in Bench process memory. It does not alter the source PDF,
Marker input, bundle/manifest, audit verdict, pipeline, vault, or frozen Visual Witness path.
Persisting these signals into conversion bundle evidence is a separate, unsigned graduation.
