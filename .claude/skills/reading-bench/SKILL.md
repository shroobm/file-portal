---
name: reading-bench
description: Build The Reading Bench — the two-panel assembly-line page that shows what File Portal's converter READ (a real page drawn to scale from the geometry it captured, every block, a reading head stepping block by block) beside what it WROTE (the block's text and its full record), with dials from the bundle's own manifest. Use whenever Rab asks to SEE what the model is looking at, to explain the polygon/bbox geometry, to review a bundle's layout pass page by page, or to refresh the published bench for a new book. Not for editing bundles, blessing, or the Repair Bench (that is the widget's).
---

# The Reading Bench — the skill

*Born S128–S129 (2026-09-10), from Rab's words after "wanna just talk": the converter should feel like "a pop up window,
showcasing two panels, the section the model reads, the section the model is inputting. Like an assembly plant, the
gauge reads fidelity, omissions, and you can see what the model is currently looking at slice by slice, chunk by chunk."
And: "we should capture the polygon numbers, the geometry, explain that a bit more so I can understand." Then: "You're
going to have to make an artifact that shows what you're describing using what's available to you." And: "name it …
according to your understanding of it, and its purpose, make it into a literal skill, based on what you did and did not
do, and what the importance and reason why this skill was made."*

## Why this exists — the importance, in one paragraph

For months the converter has CAPTURED the geometry of every block on every page (J24: id, type, polygon, bbox, section
hierarchy — `blocks.json` beside every bundle's manifest) and nobody had ever DRAWN it. The Reading Bench is the first
surface where a human can see what the machine saw: the page at true scale, every block it found, the one it is reading
now, and what it wrote for that block — with the book's own fidelity dials from its manifest. It matters beyond the
picture: it is the seed of three things Rab described in one breath. The reading panel (this page). The crop tool (a
human draws a polygon with a label — the SAME record type a block already is). The training panel (a pile of those
records is a labeled set for a small layout detector, the only kind of model that is allowed to be collection-specific).
One record type serves all three, which is why the geometry is the keel and not a detail. The name says what it is in
the project's own vocabulary (the Bench is where a human works on a page) and what it is for (reading).

## The three laws of this bench (what it must show, what it must never fake)

1. **Real bytes only.** Every number on the page comes from a bundle on disk: `blocks.json` for the geometry, the census,
   the timing and the corrected page numbers; `manifest.json` for the dials (convert `doc_survival`, pages flagged, the
   analyst's chunks passed/rejected and goodput, the verdict). No mock rows, no invented scores. A dial whose number the
   manifest does not carry renders `UNREAD`, never 0 and never a plausible placeholder (docs/32 §5 rule 4).
2. **Drawn to scale from geometry; the real page is a layer UNDER it, never instead of it.** The page is an SVG whose
   `viewBox` is the page box in PDF points (72 to the inch); each block is its bbox. A bundle ships figure crops as
   assets, not page renders — so the render comes from the SOURCE PDF (`--pdf`, PyMuPDF, 96 dpi by default), sits under
   the block rectangles at an operator-set opacity, and the page names its source and dpi (Rab, S129: "embed the real
   pages underneath each of those page sections … treat it as an overlay"). Without the PDF the bench draws geometry
   alone and the render reads `UNREAD`. The block page box is checked against the PDF's own page rect and a mismatch is
   printed beside the slider, never hidden (DDIA: 504 × 662 against 504 × 661.5 — a match within a point).
3. **The reading head is honest about what it knows.** It steps blocks in the order the layout stage emitted them — the
   order the text reaches the analyst. The analyst's per-chunk scores exist in its journal but are NOT yet joined to
   block ids; the page says so in its notes and shows book-level dials. When that join is built, per-block scores replace
   the note — the note is not to be deleted quietly.

The projection law holds here too (docs/19 §0.2): the bench READS; Python owns pipeline truth. It never writes into a
bundle.

## Run it

```bash
# 1. pull a real, compact dataset out of a bundle (read-only on the bundle); --pdf renders the chosen pages from the source PDF
python .claude/skills/reading-bench/extract_geometry.py "<bundle dir with blocks.json + manifest.json>" .claude/skills/reading-bench/out/geometry.json --pdf "<the source .pdf>" --render 96
# 2. build the page with the data inlined (about 1 MB with six page renders)
python .claude/skills/reading-bench/build_page.py .claude/skills/reading-bench/out/geometry.json .claude/skills/reading-bench/out/reading-bench.html
# 3. look once: preview_start "reading-bench" (launch.json serves out/ on 127.0.0.1:7141) and open /reading-bench.html —
#    the blocks must land on the printed table, caption and paragraphs; a file:// open is refused by the pane
# 4. publish with the Artifact tool (title lives in the HTML: The Reading Bench), or SendUserFile the HTML
# tripwire — run whenever either script changes; under the marker-env, so the render cases run (without PyMuPDF they SKIP and say so)
python .claude/skills/reading-bench/selftest.py
```

`extract_geometry.py` picks a handful of pages that show the block families (the first page with a Table, a FigureGroup,
Code, a TableOfContents, a ListGroup, and a plain text page with header and footer) — pass `--pages 161,31` to choose.
Use the marker-env interpreter (`C:\Users\Bndit\ml\marker-env\Scripts\python.exe`): the scripts are stdlib except the
render, which needs PyMuPDF (`fitz`, in the marker-env). `out/` is gitignored — the published artifact is the copy that
lasts. The DDIA source is in the library's `drop/done/`; a bundle's `manifest.json` names its source file.

## What was done and what was not (S128–S129, the first build)

**Done:** the DDIA bundle in `anchor/` read (5,716 blocks, 673 pages, page box 504 × 662 pt = O'Reilly's 7 × 9.19 in;
one Table and three TableGroups in the whole book — the layout stage under-reads tables on a clean PDF, before scans);
Marker's page field wrong on 5,689 blocks and corrected from the id (J24), the bench shows both; the dials from the
manifest (convert `doc_survival 0.8559` over 662 scored, **144** pages flagged — mostly the index; the first draft of this
file said 139, a number written from memory and corrected at S129's second pass by re-reading the manifest — rule 3; `qwen3:8b`, 492 chunks,
481 passed, 11 rejected: fence 8, survival 3; 57.76 tok/s); the explainer figure (points, inches, origin top-left,
polygon vs bbox); the page published as **The Reading Bench** and sent as a file. **Second pass, same day** (Rab: "embed
the real pages underneath … as an overlay"): the six chosen pages rendered from the source PDF at 96 dpi (672 × 882 px
each) and laid UNDER the blocks with an opacity slider; the page box checked against the PDF rect on every page (six of
six match); the look taken on the local build through the preview server — on p.161 the Table block sits on the printed
`fact_sales_table`, the Caption on "Figure 4-7", the Text blocks on their paragraphs; the selftest grew to 21 cases (the
render path, its dpi, the rect check, a missing PDF as a negative) and a cp1252 console no longer crashes it.

**Not done, named:** no per-block fidelity (the journal→block join is unbuilt); the published artifact itself was not
screenshotted (the pane is not signed in) — the local build was, and the artifact is the same bytes; the crop tool and
the training panel are described, not built; the render is a raster at one dpi, not the PDF's vectors. The guard
(`guard_git.py`) false-denied an inline `python -c` with braces during the build — the sixth shape of SYM-110's family;
the remedy was the project's own rule (scripts in files), and a guard case is owed.

## The record type, so the next builder does not have to rediscover it

One block: `id` (`/page/161/Table/1` = page 161, the second Table there), `block_type`, `polygon` (four `[x, y]` corners,
points, origin top-left, y downward), `bbox` (`[left, top, right, bottom]`; equal to the polygon's extremes on a square
block, different on a skewed scan), `page` (corrected) and `page_field_raw` (Marker's, wrong), `section_hierarchy`
(`{"1": header id, "2": header id}`), `html`, `image_refs`. The bundle's `page_info` carries each page's box. A human crop
is the same record with a human's label — that sentence is the whole vision, kept mechanical.
