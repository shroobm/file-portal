# -*- coding: utf-8 -*-
"""page_geometry_selftest.py — the page-geometry predictors' tripwires (S209 E13; SYM-142 / SYM-143). Hermetic: the fixture PDF
is DRAWN here by pymupdf (a prose page, a page stored Rotate-90 with a Table block on it, a page of 48 ± glyphs — a symbol the
base font can draw; the check mark's category is the same), never read from disk; no pipeline, no GPU. Each case violates the
property its rule stands for: the rotated table page counts once and leads the worst list; a rotated page without a table is
rotated and not a rotated table; the flagged crossing follows the list handed in; a plain document reads zeros with an empty
list; the scan lane reads the rotation and leaves the symbols unread; a source that cannot be opened reads None everywhere
with its reason; nine glyphs are counted and are not a symbol page; a 270° page is a rotated page. Prints
`==== page_geometry selftest: N/N ====`, exit 0 green · 1 red."""
import os
import sys

import fitz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import page_geometry as pg  # noqa: E402

ok = n = 0


def case(name, cond, detail=""):
    global ok, n
    n += 1
    ok += 1 if cond else 0
    print("  [%d] %s %s%s" % (n, "ok " if cond else "RED", name, ("  <- " + str(detail)[:200]) if (detail and not cond) else ""))


def fixture(glyphs=48, rotation=90):
    doc = fitz.open()
    p = doc.new_page(width=612, height=792)
    p.insert_text((72, 72), "The framework compares implementations and impacts across the case projects", fontsize=10)
    p = doc.new_page(width=612, height=792)
    p.insert_text((72, 72), "Engineering and Design Phase Schematic Design Design Development", fontsize=10)
    p.set_rotation(rotation)
    p = doc.new_page(width=612, height=792)
    p.insert_text((72, 72), "Type of Project Delivery Method Project Size", fontsize=10)
    p.insert_text((72, 100), " ".join(["±"] * glyphs), fontsize=10)   # ± is Sm, as √ is
    return doc


TABLE = {"page": 1, "block_type": "Table", "bbox": [16, 118, 771, 305], "html": "<table><tr><td>in</td></tr></table>"}
doc = fixture()
out = pg.page_geometry(doc, [TABLE], "clean", pages_flagged=[2])
case("three pages, one stored Rotate-90 with a Table block and flagged: rotated 1 · with tables 1 · flagged 1 · list [2]",
     out["pages_total"] == 3 and out["pages_rotated"] == 1 and out["rotated_pages"] == [2] and out["rotated_with_tables"] == 1
     and out["rotated_flagged"] == 1 and out["pages_unread"] == 0, out)
case("the page of 48 ± glyphs is the one symbol page and the glyphs are counted whole",
     out["symbol_pages"] == 1 and out["symbol_glyphs_total"] == 48, out)
case("the worst list holds the rotated table page (flagged, tables 1, 90°); symbol_worst holds the symbol page with its glyphs and a sample",
     [r["page"] for r in out["worst"]] == [2] and out["worst"][0]["tables"] == 1 and out["worst"][0]["flagged"] == 1 and out["worst"][0]["rotation"] == 90
     and [r["page"] for r in out["symbol_worst"]] == [3] and out["symbol_worst"][0]["symbol_glyphs"] == 48 and out["symbol_worst"][0]["sample"] == "±", out)
plus = fitz.open()
plus.new_page(width=612, height=792).insert_text((72, 72), " ".join(["+"] * 48) + " " + " ".join(["="] * 20), fontsize=10)
outp = pg.page_geometry(plus, [], "clean")
case("ASCII symbols (+ =) are glyphs every recogniser reads: 0 symbol glyphs, no symbol page",
     outp["symbol_glyphs_total"] == 0 and outp["symbol_pages"] == 0 and outp["symbol_worst"] == [], outp)
out2 = pg.page_geometry(doc, [{"page": 0, "block_type": "Table", "bbox": [0, 0, 1, 1], "html": ""}], "clean", pages_flagged=[2])
case("a rotated page without a Table block is rotated and not a rotated table", out2["pages_rotated"] == 1 and out2["rotated_with_tables"] == 0, out2)
out3 = pg.page_geometry(doc, [TABLE], "clean", pages_flagged=None)
case("no flagged list handed in: rotated_flagged 0, the rotation still read", out3["rotated_flagged"] == 0 and out3["pages_rotated"] == 1, out3)
plain = fitz.open()
plain.new_page(width=612, height=792).insert_text((72, 72), "A plain page of prose and nothing else", fontsize=10)
out4 = pg.page_geometry(plain, [], "clean", pages_flagged=[])
case("a plain document reads zeros and an empty worst list, never None",
     out4["pages_rotated"] == 0 and out4["symbol_glyphs_total"] == 0 and out4["symbol_pages"] == 0 and out4["worst"] == [], out4)
out5 = pg.page_geometry(doc, [TABLE], "scan", pages_flagged=[2])
case("the scan lane reads the rotation and leaves the symbols unread with a reason (no symbol page can be named there)",
     out5["pages_rotated"] == 1 and out5["symbol_glyphs_total"] is None and out5["symbol_pages"] is None and "symbols_reason" in out5
     and out5["worst"][0]["page"] == 2 and out5["worst"][0]["symbol_glyphs"] is None and out5["symbol_worst"] == [], out5)
out6 = pg.page_geometry(os.path.join(os.path.dirname(os.path.abspath(__file__)), "no-such-source.pdf"), [TABLE], "clean")
case("a source that cannot be opened reads None on every count with its reason — never a zero",
     out6["pages_total"] is None and out6["pages_rotated"] is None and out6["rotated_pages"] is None and out6["symbol_glyphs_total"] is None
     and "reason" in out6, out6)
out7 = pg.page_geometry(fixture(glyphs=9), [], "clean")
case("nine glyphs are counted and are not a symbol page (the line is %d)" % pg.SYMBOL_MIN,
     out7["symbol_glyphs_total"] == 9 and out7["symbol_pages"] == 0, out7)
out8 = pg.page_geometry(fixture(rotation=270), [], "clean")
case("a page stored at 270° is a rotated page in the worst list (no table on it: tables 0); the symbol page sits in symbol_worst",
     out8["pages_rotated"] == 1 and out8["rotated_pages"] == [2] and [r["page"] for r in out8["worst"]] == [2]
     and out8["worst"][0]["rotation"] == 270 and out8["worst"][0]["tables"] == 0 and [r["page"] for r in out8["symbol_worst"]] == [3], out8)
# the order of the worst list: a flagged rotated table leads, then a rotated table unflagged, then a rotated page without a table
three = fitz.open()
for k in range(3):
    pk = three.new_page(width=612, height=792)
    pk.insert_text((72, 72), "a rotated page number %d" % k, fontsize=10)
    pk.set_rotation(90)
out9 = pg.page_geometry(three, [{"page": 0, "block_type": "Table", "bbox": [0, 0, 1, 1], "html": ""},
                               {"page": 2, "block_type": "TableGroup", "bbox": [0, 0, 1, 1], "html": ""}], "clean", pages_flagged=[3])
case("worst is ordered: the flagged rotated table (p.3) first, the unflagged rotated table (p.1) next, the rotated page without a table (p.2) last",
     [r["page"] for r in out9["worst"]] == [3, 1, 2] and out9["rotated_with_tables"] == 2 and out9["rotated_flagged"] == 1, out9)
print("==== page_geometry selftest: %d/%d ====" % (ok, n))
sys.exit(0 if ok == n else 1)
