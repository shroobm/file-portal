# -*- coding: utf-8 -*-
"""figure_text_selftest.py — the chart-text measure's tripwires (S209 E13). Hermetic: the fixture PDF is DRAWN here by pymupdf (a
page with a chart's legend words inside a rectangle and prose outside it), never read from disk; no pipeline, no GPU. Each
case violates the property its rule stands for: a figure whose box holds six layer words and whose caption ships two reads
6 against 2 and is not silent; a figure with no caption is silent; words outside the box are never counted; the scan lane
reads every figure unread; no Figure block reads zeros; a page past the document reads unread. Prints
`==== figure_text selftest: N/N ====`, exit 0 green · 1 red."""
import os
import sys

import fitz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figure_text as ft  # noqa: E402

ok = n = 0


def case(name, cond, detail=""):
    global ok, n
    n += 1
    ok += 1 if cond else 0
    print("  [%d] %s %s%s" % (n, "ok " if cond else "RED", name, ("  <- " + str(detail)[:200]) if (detail and not cond) else ""))


BOX = [72, 100, 400, 300]
LEGEND = ["Goods", "excluding", "food", "energy", "Durable", "Services"]


def page_with_chart(doc):
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 60), "The monetary policy report discusses inflation and growth", fontsize=10)
    page.draw_rect(fitz.Rect(*BOX), width=0.5)
    for i, w in enumerate(LEGEND):
        page.insert_text((BOX[0] + 10, BOX[1] + 20 + i * 18), w, fontsize=9)
    page.insert_text((72, 400), "Prose below the chart continues with the outlook for the year", fontsize=10)
    return page


doc = fitz.open()
page_with_chart(doc)
fig = {"page": 0, "block_type": "Figure", "bbox": BOX, "html": "<p>Chart legend</p>"}
out = ft.figure_text(doc, [fig], "clean")
case("a figure whose box holds six layer words and whose caption ships two: 6 against 2, not silent",
     out["figures_total"] == 1 and out["layer_words_in_figures"] == 6 and out["marker_words_for_figures"] == 2
     and out["figures_silent"] == 0 and out["figures_with_layer_words"] == 1 and out["worst"][0]["sample"][:2] == ["Goods", "excluding"], out)
out2 = ft.figure_text(doc, [{"page": 0, "block_type": "Picture", "bbox": BOX, "html": ""}], "clean")
case("a figure with no caption is silent", out2["figures_silent"] == 1 and out2["marker_words_for_figures"] == 0 and out2["layer_words_in_figures"] == 6, out2)
out3 = ft.figure_text(doc, [{"page": 0, "block_type": "Figure", "bbox": [72, 500, 400, 600], "html": ""}], "clean")
case("words outside the box are never counted (an empty box reads 0 layer words, not silent)",
     out3["layer_words_in_figures"] == 0 and out3["figures_silent"] == 0 and out3["figures_with_layer_words"] == 0, out3)
out4 = ft.figure_text(doc, [fig], "scan")
case("the scan lane reads every figure unread with its reason", out4["figures_unread"] == 1 and out4["layer_words_in_figures"] == 0 and "reason" in out4, out4)
out5 = ft.figure_text(doc, [{"page": 0, "block_type": "Text", "bbox": BOX, "html": "<p>prose</p>"}], "clean")
case("no Figure block: figures_total 0 and every count 0", out5["figures_total"] == 0 and out5["layer_words_in_figures"] == 0 and out5["worst"] == [], out5)
out6 = ft.figure_text(doc, [{"page": 5, "block_type": "Figure", "bbox": BOX, "html": ""}], "clean")
case("a block on a page the document does not have reads unread", out6["figures_unread"] == 1 and out6["figures_silent"] == 0, out6)
print("==== figure_text selftest: %d/%d ====" % (ok, n))
sys.exit(0 if ok == n else 1)
