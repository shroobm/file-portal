# -*- coding: utf-8 -*-
"""page_geometry.py — THE PAGE'S GEOMETRY AND ITS SYMBOL GLYPHS, two predictors (S209 E13; B40; SYM-142 / SYM-143 — Stanford
CIFE's technical report: sixteen of 113 pages stored Rotate-90, and on eight of them Marker's one Table block per page held only
two-letter shards while the layer and Marker's own extractor read the page whole; on p.32 the layer's 48 check marks came out as
the word `second` written 291 times).

Per page of the source (pymupdf): the page's /Rotate (a landscape table stored in a portrait file), whether Marker drew a Table
block on it, whether survival flagged it; and on the clean lane the layer's SYMBOL glyphs (unicode categories Sm and So — check
marks, radicals, arrows, dingbats), the glyphs a recogniser has no word for. Neither number is a loss by itself: they name the
pages where the shards and the repeats were born, so a flagged rotated table page or a table of symbols reads as such in the
manifest before anyone opens the page. On the scan lane the layer is an OCR of a picture and its symbols are the OCR's, not
the source's: the symbol counts read unread there; the rotation is the file's and reads on every lane.

Report-only (docs/15 §12): `pages_rotated`, `rotated_pages`, `rotated_with_tables`, `rotated_flagged`, `symbol_pages`,
`symbol_glyphs_total`, `pages_unread`, the worst pages (a rotated table page first, then by symbol glyphs) with a sample of the
glyphs. A source the library cannot open reads every count None with its reason — UNREAD is never a zero.
"""
from __future__ import annotations

import unicodedata

TABLE_TYPES = ("Table", "TableGroup")
SYMBOL_CATS = ("Sm", "So")          # math symbols, other symbols: √ ✓ ≠ ∆ → ★ …
SYMBOL_MIN = 10                     # symbol glyphs on a page before it counts as a symbol page
WORST_CAP = 10
ROTATED_CAP = 50                    # rotated page numbers listed; the count is always whole
SAMPLE_GLYPHS = 8


def _symbols(text: str) -> list[str]:
    return [c for c in (text or "") if unicodedata.category(c) in SYMBOL_CATS]


def page_geometry(doc, blocks: list[dict], lane: str, pages_flagged=None) -> dict:
    """`doc` an open pymupdf document (the source) or its path; `blocks` blocks.json's list (`page` 0-based, `block_type`);
    `lane` "clean" or "scan"; `pages_flagged` survival's 1-based page numbers (None = not known)."""
    worst: list[dict] = []
    out = {"meaning": "the source's page rotation and its symbol glyphs, per page, as predictors of Marker's shards on a "
                      "rotated table page (SYM-142) and of a recogniser's one word repeated for a glyph (SYM-143)",
           "pages_total": 0, "pages_rotated": 0, "rotated_pages": [], "rotated_pages_capped_at": ROTATED_CAP,
           "rotated_with_tables": 0, "rotated_flagged": 0, "symbol_pages": 0, "symbol_glyphs_total": 0,
           "symbol_min": SYMBOL_MIN, "pages_unread": 0, "worst": worst}
    import fitz  # the converter already runs on marker-env; kept local so a reader of the block needs no pymupdf

    if isinstance(doc, (str, bytes)) or hasattr(doc, "__fspath__"):
        try:
            doc = fitz.open(doc)
        except Exception:  # noqa: BLE001 — a source the library cannot open: every count None, never a zero, never a crash
            for k in ("pages_total", "pages_rotated", "rotated_with_tables", "rotated_flagged", "symbol_pages",
                      "symbol_glyphs_total", "pages_unread"):
                out[k] = None
            out["rotated_pages"] = None
            out["reason"] = "the source could not be opened for its geometry"
            return out
    tables_on = {b.get("page") for b in (blocks or []) if b.get("block_type") in TABLE_TYPES and b.get("page") is not None}
    flagged = {int(p) for p in (pages_flagged or [])}
    scan = lane != "clean"
    if scan:
        out["symbol_pages"] = None
        out["symbol_glyphs_total"] = None
        out["symbols_reason"] = "the scan lane's layer is an OCR of the picture: its symbols are the OCR's, not the source's"
    out["pages_total"] = len(doc)
    for i in range(len(doc)):
        p1 = i + 1
        try:
            page = doc[i]
            rot = int(page.rotation or 0) % 360
            syms = None if scan else _symbols(page.get_text("text"))
        except Exception:  # noqa: BLE001
            out["pages_unread"] += 1
            continue
        n_sym = None if syms is None else len(syms)
        if rot:
            out["pages_rotated"] += 1
            if len(out["rotated_pages"]) < ROTATED_CAP:
                out["rotated_pages"].append(p1)
            if i in tables_on:
                out["rotated_with_tables"] += 1
            if p1 in flagged:
                out["rotated_flagged"] += 1
        if n_sym is not None:
            out["symbol_glyphs_total"] += n_sym
            if n_sym >= SYMBOL_MIN:
                out["symbol_pages"] += 1
        if rot or (n_sym is not None and n_sym >= SYMBOL_MIN):
            # appended to the list the returned block names (the glass detector reads a literal by the name it is appended to)
            worst.append({"page": p1, "rotation": rot, "tables": int(i in tables_on), "flagged": int(p1 in flagged),
                          "symbol_glyphs": n_sym,
                          "sample": "".join(dict.fromkeys(syms))[:SAMPLE_GLYPHS] if syms else ""})
    worst.sort(key=lambda r: (-(1 if r["rotation"] and r["tables"] else 0), -(r["symbol_glyphs"] or 0), r["page"]))
    del worst[WORST_CAP:]
    return out
