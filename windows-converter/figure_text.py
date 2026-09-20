# -*- coding: utf-8 -*-
"""figure_text.py — CHART TEXT AS TEXT, the measure (S209 E13; B41; the frontier's item 9: a chart's legend, axis labels and data
labels are text the source's layer carries and Marker's blocks drop — the AI Index: 10,551 layer words inside 479 figure
boxes, 680 shipped; the MPR: 409 against 8).

For every Figure / Picture block Marker wrote (blocks.json: `page`, `bbox` in PDF points, `html`), the words the source's own
layer carries INSIDE the block's box (pymupdf `get_text("words", clip=…)`) against the words Marker shipped for that block
(its html: the caption, the alt text, any text). A figure is SILENT when the layer has words inside it and Marker shipped
none. On the scan lane the layer is an OCR of a picture and no witness for what is text: every figure reads unread.

Report-only (docs/15 §12): `figures_total`, `figures_with_layer_words`, `layer_words_in_figures`, `marker_words_for_figures`,
`figures_silent`, `figures_unread`, the worst pages with a sample of the words the reader never gets. The reader's number: how
much of the source's own text sits inside its figures and never reaches the markdown.
"""
from __future__ import annotations

import re

FIG_TYPES = ("Figure", "Picture", "FigureGroup", "PictureGroup")
WORST_CAP = 10
SAMPLE_WORDS = 8
_WORD = re.compile(r"[^\W\d_]{3,}")


def _words(text: str) -> list[str]:
    return _WORD.findall(text or "")


def figure_text(doc, blocks: list[dict], lane: str) -> dict:
    """`doc` an open pymupdf document (the source) or its path, `blocks` blocks.json's list, `lane` "clean" or "scan"."""
    figs = [b for b in blocks if b.get("block_type") in FIG_TYPES and b.get("bbox") and b.get("page") is not None]
    worst: list[dict] = []                # the worst pages, appended at the end (a list the returned block names)
    out = {"meaning": "the source's own words inside each Marker figure box against the words Marker shipped for the figure; "
                      "a silent figure has layer words and no shipped words",
           "figures_total": len(figs), "figures_with_layer_words": 0, "layer_words_in_figures": 0,
           "marker_words_for_figures": 0, "figures_silent": 0, "figures_unread": 0, "worst": worst}
    if lane != "clean":
        out["figures_unread"] = len(figs)
        out["reason"] = "the scan lane's layer is an OCR of the picture, no witness for what is text"
        return out
    import fitz  # the converter already runs on marker-env; kept local so a reader of the block needs no pymupdf

    if isinstance(doc, (str, bytes)) or hasattr(doc, "__fspath__"):
        try:
            doc = fitz.open(doc)
        except Exception:  # noqa: BLE001 — a source the library cannot open: every figure unread, never a crash at ship
            out["figures_unread"] = len(figs)
            out["reason"] = "the source could not be opened for its words"
            return out
    per_page: dict[int, dict] = {}
    for b in figs:
        p = b["page"]
        if p < 0 or p >= len(doc):
            out["figures_unread"] += 1
            continue
        page = doc[p]
        clip = fitz.Rect(*b["bbox"]) & page.rect
        if clip.is_empty:
            out["figures_unread"] += 1
            continue
        try:
            layer = [w[4] for w in page.get_text("words", clip=clip)]
        except Exception:  # noqa: BLE001
            out["figures_unread"] += 1
            continue
        layer = [w for w in layer if _WORD.search(w)]
        shipped = _words(re.sub(r"<[^>]+>", " ", b.get("html", "") or ""))
        if layer:
            out["figures_with_layer_words"] += 1
        out["layer_words_in_figures"] += len(layer)
        out["marker_words_for_figures"] += len(shipped)
        if layer and not shipped:
            out["figures_silent"] += 1
        e = per_page.setdefault(p + 1, {"page": p + 1, "figures": 0, "layer_words": 0, "marker_words": 0, "sample": []})
        e["figures"] += 1
        e["layer_words"] += len(layer)
        e["marker_words"] += len(shipped)
        if layer and len(e["sample"]) < SAMPLE_WORDS:
            e["sample"].extend(layer[:SAMPLE_WORDS - len(e["sample"])])
    for v in sorted(per_page.values(), key=lambda v: -(v["layer_words"] - v["marker_words"]))[:WORST_CAP]:
        worst.append({"page": v["page"], "figures": v["figures"], "layer_words": v["layer_words"],
                      "marker_words": v["marker_words"], "sample": v["sample"]})
    return out
