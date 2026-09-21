# -*- coding: utf-8 -*-
"""table_shape_selftest.py — the structural-table measure's tripwires (S209 E11). Hermetic: the fixture PDF is DRAWN here by
pymupdf (a ruled 5 × 4 table with cell text; an unruled text grid), never read from disk; no pipeline, no GPU. Each case
violates the property its rule stands for: a ruled table Marker wrote two columns narrow reads columns_lost 2 (rows 0); a
block whose cells share no text with the page is no witness (disagree, no count); the scan lane reads every table unread; an
unruled grid is witnessed by the text strategy for rows only; a page with no Table block reads zeros with tables_total 0.
Prints `==== table_shape selftest: N/N ====`, exit 0 green · 1 red."""
import os
import sys

import fitz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table_shape as ts  # noqa: E402

ok = n = 0


def case(name, cond, detail=""):
    global ok, n
    n += 1
    ok += 1 if cond else 0
    print("  [%d] %s %s%s" % (n, "ok " if cond else "RED", name, ("  <- " + str(detail)[:200]) if (detail and not cond) else ""))


ROWS, COLS = 5, 4
X0, Y0, CW, RH = 72, 100, 110, 24
CELLS = [["Item", "2026", "2025", "Change"], ["Net income", "1307", "1065", "23"], ["Revenue", "4053", "3449", "18"],
         ["Expenses", "2093", "1925", "9"], ["Provisions", "246", "149", "65"]]


def ruled_page(doc):
    page = doc.new_page(width=612, height=792)
    for r in range(ROWS + 1):
        page.draw_line((X0, Y0 + r * RH), (X0 + COLS * CW, Y0 + r * RH), width=0.8)
    for c in range(COLS + 1):
        page.draw_line((X0 + c * CW, Y0), (X0 + c * CW, Y0 + ROWS * RH), width=0.8)
    for r, row in enumerate(CELLS):
        for c, txt in enumerate(row):
            page.insert_text((X0 + c * CW + 4, Y0 + r * RH + 16), txt, fontsize=10)
    return page, [X0, Y0, X0 + COLS * CW, Y0 + ROWS * RH]


def html(rows, ncols):
    return "<table>" + "".join("<tr>" + "".join("<td>%s</td>" % x for x in row[:ncols]) + "</tr>" for row in rows) + "</table>"


# 1 · a ruled table Marker wrote two columns narrow: witnessed by lines, columns_lost 2, rows_lost 0
doc = fitz.open()
page, bbox = ruled_page(doc)
blocks = [{"page": 0, "block_type": "Table", "bbox": bbox, "html": html(CELLS, 2)}]
out = ts.table_shape(doc, blocks, "clean")
case("a ruled table two columns narrow: lines witness, columns_lost 2, rows_lost 0",
     out["tables_witnessed_lines"] == 1 and out["columns_lost"] == 2 and out["rows_lost"] == 0 and out["tables_total"] == 1
     and out["pages_with_columns_lost"] == 1 and out["worst"][0]["page"] == 1 and out["worst"][0]["shapes"] == ["5x4->5x2"], out)
# 2 · the same table written whole: nothing lost, nothing gained
out2 = ts.table_shape(doc, [{"page": 0, "block_type": "Table", "bbox": bbox, "html": html(CELLS, 4)}], "clean")
case("the same table written whole: columns_lost 0, columns_gained 0, pages_with_columns_lost 0",
     out2["columns_lost"] == 0 and out2["columns_gained"] == 0 and out2["pages_with_columns_lost"] == 0 and out2["tables_witnessed_lines"] == 1, out2)
# 3 · a block whose cells share no text with the page: the geometry is no witness — disagree, no count
alien = [["Apples", "Pears"], ["Plums", "Figs"], ["Kiwi", "Lime"], ["Yuzu", "Date"], ["Nashi", "Sloe"]]
out3 = ts.table_shape(doc, [{"page": 0, "block_type": "Table", "bbox": bbox, "html": html(alien, 2)}], "clean")
case("cells that disagree with the page: tables_disagree 1, columns_lost 0 (a disagreeing geometry is no witness)",
     out3["tables_disagree"] == 1 and out3["columns_lost"] == 0 and out3["tables_witnessed_lines"] == 0, out3)
# 4 · the scan lane: every table unread, a reason said
out4 = ts.table_shape(doc, blocks, "scan")
case("the scan lane reads every table unread with its reason", out4["tables_unread"] == 1 and out4["columns_lost"] == 0 and "reason" in out4, out4)
# 5 · an unruled grid (text only): the text witness, rows only — columns never counted from it
doc5 = fitz.open()
page5 = doc5.new_page(width=612, height=792)
for r, row in enumerate(CELLS):
    for c, txt in enumerate(row):
        page5.insert_text((X0 + c * CW + 4, Y0 + r * RH + 16), txt, fontsize=10)
out5 = ts.table_shape(doc5, [{"page": 0, "block_type": "Table", "bbox": bbox, "html": html(CELLS, 2)}], "clean")
case("an unruled grid: the text witness counts rows only; columns_lost stays 0 though Marker is two columns narrow",
     out5["tables_witnessed_text"] == 1 and out5["tables_witnessed_lines"] == 0 and out5["columns_lost"] == 0, out5)
# 6 · no Table block at all
out6 = ts.table_shape(doc, [{"page": 0, "block_type": "Text", "bbox": bbox, "html": "<p>prose</p>"}], "clean")
case("no Table block: tables_total 0 and every count 0", out6["tables_total"] == 0 and out6["columns_lost"] == 0 and out6["worst"] == [], out6)
# 7b · a lines witness whose rows are far off Marker's (a sparse ruling read as a 2-row grid) is no witness for columns
out7b = ts.table_shape(doc, [{"page": 0, "block_type": "Table", "bbox": bbox, "html": html(CELLS * 4, 2)}], "clean")
case("a lines witness whose row count is off Marker's beyond the tolerance reads disagree, columns_lost 0",
     out7b["tables_disagree"] == 1 and out7b["columns_lost"] == 0 and out7b["tables_witnessed_lines"] == 0, out7b)
# 7c · a lines witness NARROWER than Marker's width (partial rulings) is no witness for columns; columns_gained keeps the tell
wide = [row + ["x1", "x2", "x3"] for row in CELLS]
out7c = ts.table_shape(doc, [{"page": 0, "block_type": "Table", "bbox": bbox, "html": html(wide, 7)}], "clean")
case("a lines witness narrower than Marker's width reads disagree, columns_lost 0, columns_gained 3",
     out7c["tables_disagree"] == 1 and out7c["columns_lost"] == 0 and out7c["columns_gained"] == 3 and out7c["tables_witnessed_lines"] == 0, out7c)
# 7 · a page index past the document: unread, never a crash
out7 = ts.table_shape(doc, [{"page": 7, "block_type": "Table", "bbox": bbox, "html": html(CELLS, 2)}], "clean")
case("a block on a page the document does not have reads unread", out7["tables_unread"] == 1 and out7["columns_lost"] == 0, out7)
# S209 E13 — SYM-145 (Codex's counterexample, MSG-CDX-0085, replayed): the lines strategy splits a column at every ruling it
# finds — NBC p.32's nine-column table read 20×19 with nine columns empty in every row. A ruled table drawn with an extra
# vertical line inside EVERY column (eight rulings, four columns of text) must read columns_lost 0 against Marker's four.
doc145 = fitz.open()
page145, bbox145 = ruled_page(doc145)
for c in range(COLS):
    page145.draw_line((X0 + c * CW + CW * 0.75, Y0), (X0 + c * CW + CW * 0.75, Y0 + ROWS * RH), width=0.8)
w145 = ts._witness(page145, fitz.Rect(*bbox145))
out145 = ts.table_shape(doc145, [{"page": 0, "block_type": "Table", "bbox": bbox145, "html": html(CELLS, COLS)}], "clean")
case("SYM-145: phantom rulings (an empty column drawn inside every column) are not columns — the witness counts the columns that carry text (4), columns_lost 0",
     w145 is not None and w145[0] == "lines" and w145[2] == COLS and out145["columns_lost"] == 0 and out145["tables_witnessed_lines"] == 1, (w145, out145))
print("==== table_shape selftest: %d/%d ====" % (ok, n))
sys.exit(0 if ok == n else 1)
