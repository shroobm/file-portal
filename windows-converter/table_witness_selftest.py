# -*- coding: utf-8 -*-
"""table_witness_selftest.py — the cell-level witness's tripwires. Hermetic: every fixture PDF is DRAWN here by
pymupdf (labelled rows with figures, placed by hand at known coordinates); nothing is read from disk, no pipeline, no
GPU. Every defect case is paired with its own negative control on the SAME layer — the clean html that must read 0
for that one signal — so a case that could pass by construction (a measure that always says "dropped") is caught by
its own pair failing. Prints `==== table_witness selftest: N/N ====`, exit 0 green · 1 red."""
import os
import sys

import fitz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table_witness as tw  # noqa: E402

ok = n = 0


def case(name, cond, detail=""):
    global ok, n
    n += 1
    ok += 1 if cond else 0
    print("  [%d] %s %s%s" % (n, "ok " if cond else "RED", name, ("  <- " + str(detail)[:300]) if (detail and not cond) else ""))


def row_html(cells):
    return "<tr>" + "".join("<td>%s</td>" % c for c in cells) + "</tr>"


def table_html(*rows):
    return "<table>" + "".join(rows) + "</table>"


FS = 10
X0, Y0, RH = 72, 100, 24
LABEL_X, FIG1_X, FIG2_X = X0, X0 + 150, X0 + 250

# ---- PAGE A: three labelled rows, two figure columns each (Net income / Revenue / Expenses) ----
ROWS_A = [("Net income", "1,307", "1,065"), ("Revenue", "4,053", "3,449"), ("Expenses", "2,093", "1,925")]
docA = fitz.open()
pageA = docA.new_page(width=612, height=792)
for r, (label, f1, f2) in enumerate(ROWS_A):
    y = Y0 + r * RH + 16
    pageA.insert_text((LABEL_X, y), label, fontsize=FS)
    pageA.insert_text((FIG1_X, y), f1, fontsize=FS)
    pageA.insert_text((FIG2_X, y), f2, fontsize=FS)
BBOX_A = [X0 - 4, Y0 - 4, FIG2_X + 60, Y0 + len(ROWS_A) * RH + 4]


def block_a(html):
    return [{"page": 0, "block_type": "Table", "bbox": BBOX_A, "html": html}]


HTML_A_CLEAN = table_html(*(row_html([label, f1, f2]) for label, f1, f2 in ROWS_A))

# 1 · clean match: everything present, matched 3, dropped/merged/split/echo/header_cut all 0 — the shared baseline
# every later case's negative control refers back to
outA_clean = tw.table_witness(docA, block_a(HTML_A_CLEAN))
tA_clean = outA_clean["tables"][0]
case("clean match: rows_layer 3, rows_rendered 3, matched 3, dropped/merged/split/echo/header_cut all 0, unread None",
     tA_clean["unread"] is None and tA_clean["rows_layer"] == 3 and tA_clean["rows_rendered"] == 3
     and len(tA_clean["matched"]) == 3 and tA_clean["dropped"] == [] and tA_clean["merged"] == []
     and tA_clean["split"] == [] and tA_clean["echo"] == [] and tA_clean["header_cut"] == [], tA_clean)
case("document totals over one clean table: rows_dropped_total 0, rows_merged_total 0, rows_split_total 0 (a measured "
     "zero over a real population, never None) — the negative control docs/34 asks the measure itself to pass on a "
     "clean specimen",
     outA_clean["tables_read"] == 1 and outA_clean["rows_dropped_total"] == 0 and outA_clean["rows_merged_total"] == 0
     and outA_clean["rows_split_total"] == 0 and outA_clean["echo_total"] == 0 and outA_clean["header_cut_total"] == 0,
     outA_clean)

# 2 · DROPPED: the "Revenue" row entirely absent from the html; its negative control is case 1 (same layer, dropped 0)
HTML_A_DROPPED = table_html(*(row_html([label, f1, f2]) for label, f1, f2 in ROWS_A if label != "Revenue"))
outA_dropped = tw.table_witness(docA, block_a(HTML_A_DROPPED))
tA_dropped = outA_dropped["tables"][0]
case("dropped: the Revenue row missing from the html reads dropped 1 (Revenue, its two figures) over the SAME layer "
     "case 1 read dropped 0 on — matched drops to 2",
     len(tA_dropped["dropped"]) == 1 and tA_dropped["dropped"][0]["label"] == "Revenue"
     and set(tA_dropped["dropped"][0]["figures"]) == {"4,053", "3,449"} and len(tA_dropped["matched"]) == 2, tA_dropped)

# 3 · MERGED: Net income and Revenue's labels and figures folded into one first cell over a <br>; negative control is
# case 1 on the identical layer (merged 0)
HTML_A_MERGED = table_html(
    "<tr><td>Net income<br>Revenue</td><td>1,307</td><td>1,065</td><td>4,053</td><td>3,449</td></tr>",
    row_html(["Expenses", "2,093", "1,925"]),
)
outA_merged = tw.table_witness(docA, block_a(HTML_A_MERGED))
tA_merged = outA_merged["tables"][0]
case("merged: Net income and Revenue folded into one <br>-joined first cell read merged 2 (both bands, the more "
     "specific finding over a plain match) over the layer case 1 read merged 0 on; Expenses stays matched",
     len(tA_merged["merged"]) == 2 and {m["label"] for m in tA_merged["merged"]} == {"Net income", "Revenue"}
     and len(tA_merged["matched"]) == 1 and tA_merged["matched"][0]["label"] == "Expenses", tA_merged)

# 4 · SPLIT: Net income's two figures rendered on two adjacent rows, the second with no label of its own; negative
# control is case 1 on the identical layer (split 0)
HTML_A_SPLIT = table_html(
    row_html(["Net income", "1,307"]),
    row_html(["", "1,065"]),
    row_html(["Revenue", "4,053", "3,449"]),
    row_html(["Expenses", "2,093", "1,925"]),
)
outA_split = tw.table_witness(docA, block_a(HTML_A_SPLIT))
tA_split = outA_split["tables"][0]
case("split: Net income's two figures spread over two adjacent rows (the second carrying no label) read split 1 "
     "over the layer case 1 read split 0 on; Revenue and Expenses stay matched",
     len(tA_split["split"]) == 1 and tA_split["split"][0]["label"] == "Net income"
     and tA_split["split"][0]["rows"] == [0, 1] and len(tA_split["matched"]) == 2, tA_split)

# ---- PAGE B: one labelled row, for ECHO ----
docB = fitz.open()
pageB = docB.new_page(width=612, height=792)
pageB.insert_text((LABEL_X, Y0 + 16), "Provisions", fontsize=FS)
pageB.insert_text((FIG1_X, Y0 + 16), "246", fontsize=FS)
pageB.insert_text((FIG2_X, Y0 + 16), "149", fontsize=FS)
BBOX_B = [X0 - 4, Y0 - 4, FIG2_X + 60, Y0 + RH + 4]

HTML_B_CLEAN = table_html(row_html(["Provisions", "246", "149"]))
HTML_B_ECHO = table_html(row_html(["Provisions", "246", "149"]), row_html(["Provisions", "246", "149"]))

# 5 · ECHO: a corrupted duplicate of the one real row emitted right after it; negative control the same html without
# the duplicate (echo 0)
outB_clean = tw.table_witness(docB, [{"page": 0, "block_type": "Table", "bbox": BBOX_B, "html": HTML_B_CLEAN}])
outB_echo = tw.table_witness(docB, [{"page": 0, "block_type": "Table", "bbox": BBOX_B, "html": HTML_B_ECHO}])
case("echo: a duplicated row reads echo rows [0, 1] kind text against its negative control (the same row alone) reading "
     "echo []; its three-digit figures are no _NUM_TOKEN figure, so the row readings read UNREAD by name while the echo still reads",
     [e["rows"] for e in outB_echo["tables"][0]["echo"]] == [[0, 1]] and outB_echo["tables"][0]["echo"][0]["kind"] == "text"
     and outB_clean["tables"][0]["echo"] == [] and outB_echo["tables"][0]["rows_unread"] is not None
     and outB_echo["tables"][0]["unread"] is None, (outB_echo["tables"][0], outB_clean["tables"][0]))

# ---- PAGE C: a "Transfer" row, for HEADER_CUT ----
docC = fitz.open()
pageC = docC.new_page(width=612, height=792)
pageC.insert_text((LABEL_X, Y0 + 16), "Transfer", fontsize=FS)
pageC.insert_text((FIG1_X, Y0 + 16), "5,000", fontsize=FS)
BBOX_C = [X0 - 4, Y0 - 4, FIG1_X + 60, Y0 + RH + 4]

HTML_C_CUT = table_html("<tr><th>Tra</th><th>ansfer</th></tr>", row_html(["Transfer", "5,000"]))
HTML_C_WHOLE = table_html("<tr><th>Transfer</th></tr>", row_html(["Transfer", "5,000"]))

# 6 · HEADER_CUT: a two-header-cell split of "Transfer" ("Tra" / "ansfer") against the page's own whole word; negative
# control the same layer with the header written whole (header_cut 0)
outC_cut = tw.table_witness(docC, [{"page": 0, "block_type": "Table", "bbox": BBOX_C, "html": HTML_C_CUT}])
outC_whole = tw.table_witness(docC, [{"page": 0, "block_type": "Table", "bbox": BBOX_C, "html": HTML_C_WHOLE}])
case("header_cut: 'Tra'/'ansfer' each read as a proper prefix/suffix of the page's own 'Transfer' — header_cut 2 — "
     "against its negative control (the header written whole) reading header_cut 0",
     len(outC_cut["tables"][0]["header_cut"]) == 2 and outC_whole["tables"][0]["header_cut"] == [],
     (outC_cut["tables"][0], outC_whole["tables"][0]))

# 7 · UNREAD — an html without a <tr>: named, never a crash; its negative control is case 1 (the same shape of block,
# real <tr> rows, unread None)
outA_notr = tw.table_witness(docA, [{"page": 0, "block_type": "Table", "bbox": BBOX_A, "html": "<p>no rows here</p>"}])
case("unread — an html without a <tr>: named as the reason, rows_layer/rows_rendered None, against case 1's unread None",
     outA_notr["tables"][0]["unread"] == "an html without a <tr>" and outA_notr["tables"][0]["rows_layer"] is None
     and tA_clean["unread"] is None, outA_notr["tables"][0])

# 8 · UNREAD — a box with no words under it: named, never a crash
EMPTY_BBOX = [500, 700, 580, 780]
outA_empty = tw.table_witness(docA, [{"page": 0, "block_type": "Table", "bbox": EMPTY_BBOX, "html": HTML_A_CLEAN}])
case("unread — a box with no words inside it: named as 'no words inside the box', against case 1's unread None",
     outA_empty["tables"][0]["unread"] == "no words inside the box" and tA_clean["unread"] is None, outA_empty["tables"][0])

# 9 · UNREAD — a box entirely off the page: named, never a crash
OFF_PAGE_BBOX = [700, 900, 780, 980]
outA_off = tw.table_witness(docA, [{"page": 0, "block_type": "Table", "bbox": OFF_PAGE_BBOX, "html": HTML_A_CLEAN}])
case("unread — a box entirely off the page: named as 'the box off the page', against case 1's unread None",
     outA_off["tables"][0]["unread"] == "the box off the page" and tA_clean["unread"] is None, outA_off["tables"][0])

# 10 · S211 Lane C's own unwitnessed-zero negative control: no Table/TableGroup block at all reads every *_total None
# over a named population of 0 — never a measured-looking zero (table_shape_selftest.py's case 6, this module's own)
out_none = tw.table_witness(docA, [{"page": 0, "block_type": "Text", "bbox": BBOX_A, "html": "<p>prose</p>"}])
case("no Table block at all: tables_total 0, tables_read 0, every *_total None (not a measured zero), worst/tables empty",
     out_none["tables_total"] == 0 and out_none["tables_read"] == 0 and out_none["rows_dropped_total"] is None
     and out_none["rows_merged_total"] is None and out_none["echo_total"] is None
     and out_none["cross_page_candidates"] is None and out_none["worst"] == [] and out_none["tables"] == [], out_none)

# ---- PAGES D0/D1: a two-page document for CROSS_PAGE ----
docD = fitz.open()
pageD0 = docD.new_page(width=612, height=792)
pageD0.insert_text((LABEL_X, 770), "continued", fontsize=FS)   # a label-only band, no figure — the page's last band
BBOX_D0 = [X0 - 4, 750, X0 + 200, 785]   # bottom at 785, within CROSS_PAGE_MARGIN_PT (36pt) of the 792pt page bottom
pageD1 = docD.new_page(width=612, height=792)
pageD1.insert_text((LABEL_X, 108), "Balance", fontsize=FS)
pageD1.insert_text((FIG1_X, 108), "5,000", fontsize=FS)         # the next page's first band, with a figure
BBOX_D1 = [X0 - 4, 96, FIG1_X + 60, 116]
blocks_D = [{"page": 0, "block_type": "Table", "bbox": BBOX_D0, "html": row_html(["continued"])},
            {"page": 1, "block_type": "Table", "bbox": BBOX_D1, "html": row_html(["Balance", "5,000"])}]
outD = tw.table_witness(docD, blocks_D)
tD0 = outD["tables"][0]

# 11 · CROSS_PAGE True: a block near the page bottom whose last band lacks a figure, the next page's first band
# carrying one — cross_page_candidate True, tagged Inferred in the docstring, never asserted as a fact
case("cross_page_candidate True: a table hugging the page bottom with a label-only last band, the next page's first "
     "table opening on a figured band",
     tD0["cross_page_candidate"] is True, tD0)

# 12 · CROSS_PAGE's negative controls: (a) the same near-bottom table but the next page's first band ALSO carries no
# figure reads False, not True; (b) a table nowhere near the page bottom reads None, the reading never applied
blocks_D_nofig = [{"page": 0, "block_type": "Table", "bbox": BBOX_D0, "html": row_html(["continued"])},
                  {"page": 1, "block_type": "Table", "bbox": BBOX_D1, "html": row_html(["Balance"])}]
docD_nofig = fitz.open()
pD0 = docD_nofig.new_page(width=612, height=792)
pD0.insert_text((LABEL_X, 770), "continued", fontsize=FS)
pD1 = docD_nofig.new_page(width=612, height=792)
pD1.insert_text((LABEL_X, 108), "Balance", fontsize=FS)
outD_nofig = tw.table_witness(docD_nofig, blocks_D_nofig)
docE = fitz.open()
pageE = docE.new_page(width=612, height=792)
pageE.insert_text((LABEL_X, 316), "Mid table", fontsize=FS)     # real words, but nowhere near the page's bottom
pageE.insert_text((FIG1_X, 316), "1,234", fontsize=FS)
MID_PAGE_BBOX = [X0 - 4, 300, FIG1_X + 60, 330]   # bottom at 330, nowhere near the 792pt page's bottom margin
outD_mid = tw.table_witness(docE, [{"page": 0, "block_type": "Table", "bbox": MID_PAGE_BBOX, "html": row_html(["Mid table", "1,234"])}])
case("cross_page_candidate's negative controls: False when the next page's first band also lacks a figure; None "
     "when the block is nowhere near the page bottom margin (the reading never applied)",
     outD_nofig["tables"][0]["cross_page_candidate"] is False and outD_mid["tables"][0]["cross_page_candidate"] is None,
     (outD_nofig["tables"][0], outD_mid["tables"][0]))

# ---- PAGE F: two labelled rows whose labels are substrings of one another (Scotiabank p.51 read live: "Secured
# funding" is a raw substring of "Unsecured funding") ----
docF = fitz.open()
pageF = docF.new_page(width=612, height=792)
pageF.insert_text((LABEL_X, Y0 + 16), "Unsecured funding", fontsize=FS)
pageF.insert_text((FIG1_X, Y0 + 16), "11,008", fontsize=FS)
pageF.insert_text((LABEL_X, Y0 + RH + 16), "Secured funding", fontsize=FS)
pageF.insert_text((FIG1_X, Y0 + RH + 16), "3,901", fontsize=FS)
BBOX_F = [X0 - 4, Y0 - 4, FIG1_X + 60, Y0 + 2 * RH + 4]
HTML_F_CLEAN = table_html(row_html(["Unsecured funding", "11,008"]), row_html(["Secured funding", "3,901"]))
outF = tw.table_witness(docF, [{"page": 0, "block_type": "Table", "bbox": BBOX_F, "html": HTML_F_CLEAN}])
tF = outF["tables"][0]

# 14 · a label that is a raw substring of an unrelated longer label ("Secured funding" inside "Unsecured funding")
# must not read merged when both rows are in fact whole and clean — matched 2, merged 0 (this is the read live on
# Scotiabank p.51 before the word-boundary fix, which reported "Secured funding" merged into "Unsecured funding"
# and never found its own — correct — row)
case("a label that is a raw substring of a different, unrelated label (Secured/Unsecured funding) reads matched 2, "
     "merged 0 — not a false merge from substring containment",
     len(tF["matched"]) == 2 and tF["merged"] == [] and tF["dropped"] == [] and tF["split"] == [], tF)


# ---- S211 E5: the fixes read from the verifier's twelve pages, each with its negative control on the same layer ----


def draw(rows, x_label=LABEL_X, y0=Y0, rh=RH, fig_xs=(FIG1_X, FIG2_X, FIG2_X + 80)):
    """a page with labelled rows (label, fig, fig, ...) at known coordinates; returns (doc, bbox)."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    for r, cells in enumerate(rows):
        y = y0 + r * rh + 16
        page.insert_text((x_label, y), cells[0], fontsize=FS)
        for x, f in zip(fig_xs, cells[1:]):
            page.insert_text((x, y), f, fontsize=FS)
    return doc, [X0 - 4, y0 - 4, fig_xs[len(max(rows, key=len)) - 2] + 60, y0 + len(rows) * rh + 4]


def one(doc, bbox, html, lane="clean"):
    return tw.table_witness(doc, [{"page": 0, "block_type": "Table", "bbox": bbox, "html": html}], lane=lane)["tables"][0]


# 15 · the twin label (Scotiabank p.51 read live): two sections each with a 'Secured funding' row in the layer, the
# second rendered NOWHERE — it reads DROPPED with label_rendered_for_twin True, never MATCHED to the first section's row
# on a substring or a label hit; the negative control renders both and reads matched 4, dropped 0
docG, BBOX_G = draw([("Unsecured funding", "11,008"), ("Secured funding", "3,901"),
                     ("Unsecured funding", "12,500"), ("Secured funding", "4,763")])
HTML_G_FULL = table_html(row_html(["Unsecured funding", "11,008"]), row_html(["Secured funding", "3,901"]),
                         row_html(["Unsecured funding", "12,500"]), row_html(["Secured funding", "4,763"]))
HTML_G_TWIN = table_html(row_html(["Unsecured funding", "11,008"]), row_html(["Secured funding", "3,901"]),
                         row_html(["Unsecured funding", "12,500"]))
tG_full, tG_twin = one(docG, BBOX_G, HTML_G_FULL), one(docG, BBOX_G, HTML_G_TWIN)
case("the twin label: the second section's 'Secured funding' rendered nowhere reads dropped 1 (label_rendered_for_twin "
     "True), its twin's row never stolen; the same layer fully rendered reads matched 4, dropped 0",
     len(tG_twin["dropped"]) == 1 and tG_twin["dropped"][0]["label"] == "Secured funding"
     and tG_twin["dropped"][0]["figures"] == ["4,763"] and tG_twin["dropped"][0]["label_rendered_for_twin"] is True
     and len(tG_twin["matched"]) == 3 and len(tG_full["matched"]) == 4 and tG_full["dropped"] == [], (tG_twin, tG_full))

# 16 · the nested label (RBC p.41, BMO Q3 p.63's control): 'AUA' and 'Average AUA' both figured, rendered as two clean
# rows — merged 0; the negative control folds both labels and both figure sets into one first cell — merged 2
docH, BBOX_H = draw([("AUA", "236,600", "211,300"), ("Average AUA", "214,000", "201,100")])
HTML_H_CLEAN = table_html(row_html(["AUA", "236,600", "211,300"]), row_html(["Average AUA", "214,000", "201,100"]))
HTML_H_MERGED = table_html("<tr><td>AUA Average AUA</td><td>236,600</td><td>211,300</td><td>214,000</td><td>201,100</td></tr>")
tH_clean, tH_merged = one(docH, BBOX_H, HTML_H_CLEAN), one(docH, BBOX_H, HTML_H_MERGED)
case("the nested label: 'AUA' inside a clean 'Average AUA' row is one label — merged 0, matched 2; the same two labels "
     "DISJOINTLY in one cell with both figure sets read merged 2",
     tH_clean["merged"] == [] and len(tH_clean["matched"]) == 2 and len(tH_merged["merged"]) == 2
     and {m["label"] for m in tH_merged["merged"]} == {"AUA", "Average AUA"}, (tH_clean, tH_merged))

# 17 · a figure-less band's label folded into a row's first cell (CIBC p.162 row 12: the section header glued to its
# first row; RBC p.41: a units line wrapped) is a LABEL JOIN, the row's own figures intact — merged 0, label_joined 1
docI, BBOX_I = draw([("Derivative Assets",), ("Interest rate contracts", "1,234", "5,678")])
HTML_I_JOIN = table_html("<tr><td>Derivative Assets<br>Interest rate contracts</td><td>1,234</td><td>5,678</td></tr>")
HTML_I_CLEAN = table_html(row_html(["Derivative Assets"]), row_html(["Interest rate contracts", "1,234", "5,678"]))
tI_join, tI_clean = one(docI, BBOX_I, HTML_I_JOIN), one(docI, BBOX_I, HTML_I_CLEAN)
case("a figure-less band's label folded in reads label_joined 1, merged 0, matched 1 (its figures intact) — the `<br>` "
     "alone is no merge; the clean rendering reads label_joined 0",
     tI_join["merged"] == [] and len(tI_join["matched"]) == 1 and len(tI_join["label_joined"]) == 1
     and tI_join["label_joined"][0]["joined"] == "Derivative Assets" and tI_clean["label_joined"] == []
     and tI_clean["merged"] == [], (tI_join, tI_clean))

# 18 · the figure echo (Desjardins p.249 read live): the real row's figures with digits swapped on the row after it,
# in none of the layer's words — echo kind figures; the negative control: a second row whose figures the layer DOES
# carry (a second band) is no echo, however similar its digits (Amortized cost / Fair value)
docJ, BBOX_J = draw([("Residential mortgages", "3,510", "6,469", "13,093")])
HTML_J_ECHO = table_html(row_html(["Residential mortgages", "3,510", "6,469", "13,093"]),
                         row_html(["Consumer credit", "3,310", "0,407", "10,070"]))
tJ = one(docJ, BBOX_J, HTML_J_ECHO)
docK, BBOX_K = draw([("Amortized cost", "3,510", "6,469", "13,093"), ("Fair value", "3,310", "6,407", "13,070")])
HTML_K = table_html(row_html(["Amortized cost", "3,510", "6,469", "13,093"]), row_html(["Fair value", "3,310", "6,407", "13,070"]))
tK = one(docK, BBOX_K, HTML_K)
case("the figure echo: a row after the real one carrying its figures with digits swapped, none of them in the layer, "
     "reads echo kind figures; two layer rows with near-equal figures (Amortized cost / Fair value) read echo 0",
     len(tJ["echo"]) == 1 and tJ["echo"][0]["kind"] == "figures" and tJ["echo"][0]["rows"] == [0, 1]
     and tK["echo"] == [], (tJ, tK))

# 19 · the text echo anchored to the layer (RBC p.30, NBC p.218 read live): 'LRCN Series 1' / 'LRCN Series 2' with the
# same figures are two rows the layer holds — echo 0 at a 0.9+ text ratio; case 5's exact duplicate still reads
docL, BBOX_L = draw([("LRCN Series 1", "500,000", "500"), ("LRCN Series 2", "500,000", "500")])
HTML_L = table_html(row_html(["LRCN Series 1", "500,000", "500"]), row_html(["LRCN Series 2", "500,000", "500"]))
tL = one(docL, BBOX_L, HTML_L)
case("the text echo needs a row the layer holds ONCE: 'LRCN Series 1' / 'LRCN Series 2' (two layer bands, text ratio "
     "0.9+) read echo 0, against case 5's duplicated row reading echo 1",
     tL["echo"] == [] and len(outB_echo["tables"][0]["echo"]) == 1, tL)

# 20 · the COLLAPSE (RBC AR p.147/p.150, TD AR p.49/p.123 read live): three bands' labels and figures in ONE cell read
# collapsed [3] and merged 0; two bands in one cell stay merged 2, collapsed []
docM, BBOX_M = draw([("Net income", "1,307", "1,065"), ("Revenue", "4,053", "3,449"), ("Expenses", "2,093", "1,925")])
HTML_M_COLLAPSE = table_html("<tr><td>Net income Revenue Expenses</td><td>1,307 1,065 4,053 3,449 2,093 1,925</td></tr>")
HTML_M_TWO = table_html("<tr><td>Net income Revenue</td><td>1,307</td><td>1,065</td><td>4,053</td><td>3,449</td></tr>",
                        row_html(["Expenses", "2,093", "1,925"]))
tM_c, tM_2 = one(docM, BBOX_M, HTML_M_COLLAPSE), one(docM, BBOX_M, HTML_M_TWO)
case("the collapse: three bands in one cell read collapsed [3] (row 0), merged 0; two bands in one cell read merged 2, "
     "collapsed []",
     [c["bands"] for c in tM_c["collapsed"]] == [3] and tM_c["collapsed"][0]["row"] == 0 and tM_c["merged"] == []
     and len(tM_2["merged"]) == 2 and tM_2["collapsed"] == [], (tM_c, tM_2))

# 21 · a band whose only figures are years does not qualify (a column-header line): rendered nowhere it reads dropped 0
# and bands_qualifying counts the data rows only; the same band with a data figure DOES qualify and reads dropped 1
docN, BBOX_N = draw([("October 31", "2025", "2024"), ("Net income", "1,307", "1,065")])
HTML_N = table_html(row_html(["Net income", "1,307", "1,065"]))
tN = one(docN, BBOX_N, HTML_N)
docO, BBOX_O = draw([("Balance at", "2025", "5,000"), ("Net income", "1,307", "1,065")])
tO = one(docO, BBOX_O, HTML_N)
case("a year-only band is a header, not a data row: dropped 0, bands_qualifying 1; the same line carrying a data "
     "figure qualifies and reads dropped 1",
     tN["dropped"] == [] and tN["bands_qualifying"] == 1 and len(tO["dropped"]) == 1
     and tO["dropped"][0]["label"] == "Balance at", (tN, tO))

# 22 · rotated text in the box reads UNREAD by name (McGill p.117, SYM-142's shards); the scan lane reads UNREAD by name
docP = fitz.open()
pageP = docP.new_page(width=612, height=792)
pageP.insert_text((LABEL_X, Y0 + 100), "Net income", fontsize=FS, rotate=90)
pageP.insert_text((LABEL_X + 20, Y0 + 100), "1,307", fontsize=FS, rotate=90)
tP = one(docP, [X0 - 10, Y0 - 10, X0 + 60, Y0 + 120], HTML_A_CLEAN)
tQ = one(docA, BBOX_A, HTML_A_CLEAN, lane="scan")
case("rotated text in the box reads unread 'rotated text in the box (...)'; the scan lane reads unread 'the scan lane's "
     "layer is no witness for rows' — never a clean-looking zero",
     (tP["unread"] or "").startswith("rotated text in the box") and tP["rows_unread"] == tP["unread"]
     and (tQ["unread"] or "").startswith("the scan lane"), (tP, tQ))

# 23 · a box short of its own table (the verifier's break attempt): the rendered rows carry the second figure column
# the bbox cuts off — unread 'the box is short of its table'; the full bbox reads the same html clean (matched 3)
BBOX_A_SHORT = [X0 - 4, Y0 - 4, FIG1_X + 60, Y0 + len(ROWS_A) * RH + 4]   # ends after the FIRST figure column
tR_short, tR_full = one(docA, BBOX_A_SHORT, HTML_A_CLEAN), one(docA, BBOX_A, HTML_A_CLEAN)
case("a box drawn short of its table: the rendered rows' figures lying outside it read unread 'the box is short of its "
     "table: ...' (3 figures named); the full box reads matched 3, unread None",
     (tR_short["unread"] or "").startswith("the box is short of its table: 3 figures")
     and tR_full["unread"] is None and len(tR_full["matched"]) == 3, (tR_short, tR_full))

# 24 · a table with no qualifying band: the row readings UNREAD by name (rows_unread), the table itself read (echo and
# header_cut still read) — and the document totals over their own population: rows_dropped_total None when no read
# table has a qualifying band, tables_rows_read 0, tables_read 1
docS, BBOX_S = draw([("Pseudonym", "Alpha"), ("Type", "Newspaper")])
outS = tw.table_witness(docS, [{"page": 0, "block_type": "Table", "bbox": BBOX_S, "html": table_html(row_html(["Pseudonym", "Alpha"]))}])
case("no qualifying band (a qualitative table with a row deleted): rows_unread named, unread None, tables_read 1, "
     "tables_rows_read 0, rows_dropped_total None — a whole row lost there is not read as a clean zero",
     outS["tables"][0]["unread"] is None and (outS["tables"][0]["rows_unread"] or "").startswith("no band carries")
     and outS["tables_read"] == 1 and outS["tables_rows_read"] == 0 and outS["rows_dropped_total"] is None, outS)

# 25 · the figure echo needs the REAL row in the layer (the third pass, Automate p.384): a table whose rows the layer
# never had (an OCR'd screenshot — the box holds only a caption) with consecutive IDs reads echo 0, however similar
# the digits; case 18's echo (the real row present) still reads 1
docT, BBOX_T = draw([("Figure 12-1. The spreadsheet", "1,000")])
HTML_T = table_html(row_html(["9841", "06075010500", "2,685"]), row_html(["9842", "06075010600", "3,894"]))
tT = one(docT, BBOX_T, HTML_T)
case("the figure echo needs the real row in the layer: an OCR'd screenshot's consecutive IDs (9841 / 9842, none in the "
     "layer) read echo 0; case 18's echo with the real row present still reads 1",
     tT["echo"] == [] and len(tJ["echo"]) == 1, (tT, tJ))

# 26 · a /Rotate page reads UNREAD as the PAGE's rotation (the third pass, Ashby 1956: the layer's geometry in the
# unrotated space); the same content on an unrotated page reads
docU = fitz.open()
pageU = docU.new_page(width=612, height=792)
pageU.insert_text((LABEL_X, Y0 + 16), "Net income", fontsize=FS)
pageU.insert_text((FIG1_X, Y0 + 16), "1,307", fontsize=FS)
BBOX_U = [X0 - 4, Y0 - 4, FIG1_X + 60, Y0 + RH + 4]
tU_flat = one(docU, BBOX_U, table_html(row_html(["Net income", "1,307"])))
pageU.set_rotation(90)
tU_rot = one(docU, BBOX_U, table_html(row_html(["Net income", "1,307"])))
case("a /Rotate 90 page reads unread 'the page is rotated (/Rotate 90) ...'; the same page unrotated reads matched 1",
     (tU_rot["unread"] or "").startswith("the page is rotated (/Rotate 90)") and tU_flat["unread"] is None
     and len(tU_flat["matched"]) == 1, (tU_rot, tU_flat))

print("==== table_witness selftest: %d/%d ====" % (ok, n))
sys.exit(0 if ok == n else 1)
