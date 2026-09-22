# -*- coding: utf-8 -*-
"""table_shape.py — THE STRUCTURAL-TABLE MEASURE (S209 E11; the frontier's item 1, the bank tables: 17 of 35 NBC tables
flagged, RBC 25/30, CIBC 21/22, Scotia 31/33, TD 11/29 — survival could say a table page lost words, never its SHAPE).

For every Table block Marker wrote (blocks.json: `page`, `bbox` in PDF points, `html`), the source's own table geometry
INSIDE the block's box, read by pymupdf's `find_tables`: the LINES strategy (a witness for rows and columns — ruled
statements, the Canadian banks'), else the TEXT strategy (rows only: it over-splits columns, TD p.44 read 20 for 11), else no
witness. A witness counts only when its cells AGREE with Marker's cell text — CELL_AGREE of Marker's non-empty cells found
inside the witness's joined cell text, normalised — because a geometry that disagrees with Marker in both directions (RBC:
8 columns lost, 183 gained) is no witness, and the scan lane's layer (Scotia: 1 of 81 cells) is none either.

Report-only (docs/15 §12: the gates are two and signed): `columns_lost` and `rows_lost` per page and per document,
`tables_witnessed_lines` / `tables_witnessed_text` / `tables_disagree` / `tables_unread` beside `tables_total` (docs/34: a
number names its population), the worst pages with their shapes. Prototyped over four banks whole (S209 E10,
`columns_lost_proto.py`): NBC 102 columns lost over 24 pages, p.26 `14×26 → 11×9`. The reader's number, the build's target.

S211 Lane A (Rab's word 2026-09-21: "anything falsified needs to be secured and fix so it cannot be false about what there
is, and if it's not capable of doing so, we should know prior than later"): RBC's 2025 Annual Report manifest read
tables_witnessed_lines 5 of tables_total 223 and printed columns_lost 0 — a zero over that small a population is
UNSUPPORTED, not "no columns lost". `columns_lost` and `rows_lost` now read None (never 0) when their own population —
`columns_lost_population` / `rows_lost_population`, both the count of LINES-witnessed tables — is 0; the code only ever
sums rl/cl inside the `strat == "lines"` branch, so rows_lost's real witness is lines alone, not "both" as this file
previously claimed (that claim was itself unsupported prose, fixed here, never a code behavior change). A measured zero
over a real (nonzero) population still reads 0. `tables_agree_population` stays None always: `_witness` tries one
strategy per table (lines, else text) and returns at the first hit, so no table is ever checked by both — not
derivable from this implementation, not invented as a count.
"""
from __future__ import annotations

import re

CELL_AGREE = 0.5           # the floor on Marker's non-empty cells found in the witness's text; below it the witness is none
ROW_TOL = 0.25             # a lines witness whose row count is off Marker's by more than this share (or 2 rows) is no witness
                           # for columns: RBC's sparse rulings read 4 × 17 against Marker's 20 × 13 with the cells agreeing
STRATEGIES = ("lines", "text")
# S211 E4 (SYM-172): a cell holding only a unit sign — the gutter beside a figure, never a column of its own
_UNIT_ONLY = re.compile(r"[%$€£¥¢×x]|bps?|pts?|pp|mm|bn|k")
WORST_CAP = 10
TABLE_TYPES = ("Table", "TableGroup")   # S209 E13 (SYM-147, Codex MSG-CDX-0085): NBC p.57's damage sat in a TableGroup the measure never read


def _norm(s: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", (s or "").lower())


def _marker_cells(html: str) -> tuple[int, int, list[str]]:
    """rows, width (the widest row), the non-empty normalised cell texts of a Table block's html."""
    rows = re.split(r"(?i)<tr[^>]*>", html or "")[1:]
    widths, cells = [], []
    for r in rows:
        tds = re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", r)
        widths.append(len(tds))
        for c in tds:
            t = _norm(re.sub(r"<[^>]+>", " ", c))
            if t:
                cells.append(t)
    return len(rows), (max(widths) if widths else 0), cells


def _witness(page, clip):
    """(strategy, rows, cols, joined normalised cell text) of the largest table pymupdf finds inside the box, or None."""
    for strat in STRATEGIES:
        try:
            tf = page.find_tables(clip=clip, strategy=strat)
        except Exception:  # noqa: BLE001 — a geometry the library cannot read is no witness, never a crash at ship
            continue
        if not tf.tables:
            continue
        t = max(tf.tables, key=lambda t: t.row_count * t.col_count)
        try:
            ext = t.extract()
            text = "".join(_norm(str(x)) for row in ext for x in row if x)
        except Exception:  # noqa: BLE001
            ext, text = [], ""
        # S209 E13 (SYM-145; Codex's counterexample MSG-CDX-0085, replayed): the lines strategy splits a column at every ruling
        # it finds — NBC p.32's nine-column table read 20×19 with nine columns EMPTY in every row (the shading's edges), and
        # the measure called ten columns lost where none were. A column with no text in any row is a ruling, not a column;
        # a row with no text in any cell is a rule, not a row. The witness counts what carries text.
        if ext:
            # S211 E4 (SYM-172, NBC AR p.212 read straight): a ruled table whose `%` and `$` signs sit in their own ruled
            # gutters read 43×20 to the lines witness — the gutters carry text, so SYM-145's rule kept them — and Marker's
            # clean rendering (`2.7 %` in one cell, every figure whole: 11 columns) read 9 columns lost while the original's
            # OCR rendering, garbage-split into 17 columns ('•', 'S', '_', '1.1.1.1111'; `5,781` read as `5,78`), read 3:
            # the witness rewarded the garbage. A column whose every non-empty cell is a UNIT SIGN is the unit gutter of its
            # neighbour, not a column; a dash is a value (a nil cell) and stays a column.
            cols = sum(1 for c in range(t.col_count)
                       if any(row[c] not in (None, "") for row in ext if c < len(row))
                       and not all(_UNIT_ONLY.fullmatch(str(row[c]).strip()) for row in ext if c < len(row) and row[c] not in (None, "")))
            rows = sum(1 for row in ext if any(x not in (None, "") for x in row))
        else:
            cols, rows = t.col_count, t.row_count
        return strat, rows, cols, text
    return None


def _finish(out: dict) -> dict:
    """the population keys and the None-for-unwitnessed rule, applied at every return point (S211 Lane A; docs/34;
    Rab's word 2026-09-21: a measure may never assert a number it cannot support — an unwitnessed columns_lost /
    rows_lost is None, never 0). Both `_lost` counters are summed only inside the `strat == "lines"` branch below,
    so both share the same population: tables_witnessed_lines."""
    pop = out["tables_witnessed_lines"]
    out["columns_lost_population"] = pop
    out["rows_lost_population"] = pop
    if pop == 0:
        out["columns_lost"] = None
        out["rows_lost"] = None
    return out


def table_shape(doc, blocks: list[dict], lane: str) -> dict:
    """`doc` an open pymupdf document (the source) or its path, `blocks` blocks.json's list, `lane` "clean" or "scan"."""
    tables = [b for b in blocks if b.get("block_type") in TABLE_TYPES and b.get("bbox") and b.get("page") is not None]
    worst: list[dict] = []                # the worst pages, appended at the end (a list the returned block names)
    out = {"meaning": "the source's table geometry inside each Marker table box against Marker's rows and width; "
                      "columns_lost and rows_lost both come from the lines-witnessed tables only (the text witness "
                      "names a table present but gives no shape number to either, over-splitting both rows and "
                      "columns); a witness whose cells disagree is none; a *_lost value is None, never 0, when its "
                      "own *_lost_population is 0 — unwitnessed, not a measured zero; tables_agree_population is "
                      "always None (not derivable: _witness tries one strategy per table and stops at the first "
                      "hit, so no table is ever checked by both)",
           "cell_agree_floor": CELL_AGREE, "tables_total": len(tables), "tables_witnessed_lines": 0,
           "tables_witnessed_text": 0, "tables_disagree": 0, "tables_agree_population": None, "tables_unread": 0,
           "columns_lost": 0, "columns_lost_population": 0, "columns_gained": 0, "rows_lost": 0,
           "rows_lost_population": 0, "pages_with_columns_lost": 0, "worst": worst}
    if lane != "clean":
        out["tables_unread"] = len(tables)
        out["reason"] = "the scan lane's layer is no witness for geometry"
        return _finish(out)
    import fitz  # the converter already runs on marker-env; kept local so a reader of the block needs no pymupdf

    if isinstance(doc, (str, bytes)) or hasattr(doc, "__fspath__"):
        try:
            doc = fitz.open(doc)
        except Exception:  # noqa: BLE001 — a source the library cannot open: every table unread, never a crash at ship
            out["tables_unread"] = len(tables)
            out["reason"] = "the source could not be opened for its geometry"
            return _finish(out)
    per_page: dict[int, dict] = {}
    for b in tables:
        p = b["page"]
        if p < 0 or p >= len(doc):
            out["tables_unread"] += 1
            continue
        m_rows, m_width, m_cells = _marker_cells(b.get("html", ""))
        page = doc[p]
        clip = fitz.Rect(*b["bbox"]) & page.rect
        if clip.is_empty or m_rows == 0:
            out["tables_unread"] += 1
            continue
        w = _witness(page, clip)
        if w is None:
            out["tables_unread"] += 1
            continue
        strat, l_rows, l_cols, text = w
        found = sum(1 for c in m_cells if c in text)
        agree = (found / len(m_cells)) if m_cells else 0.0
        if agree < CELL_AGREE:
            out["tables_disagree"] += 1
            continue
        if strat == "lines" and (abs(l_rows - m_rows) > max(2, ROW_TOL * m_rows) or l_cols < m_width):
            # the rulings misread: the cells agree, the shape does not — rows far off Marker's, or a geometry NARROWER
            # than Marker's own width (RBC's sparse rulings: 13 × 3 against 11 × 17) — no witness for columns
            out["tables_disagree"] += 1
            out["columns_gained"] += max(0, m_width - l_cols)   # the document-level tell of partial rulings, kept
            continue
        entry = per_page.setdefault(p + 1, {"page": p + 1, "columns_lost": 0, "rows_lost": 0, "shapes": []})
        if strat == "lines":
            out["tables_witnessed_lines"] += 1
            rl = max(0, l_rows - m_rows)
            cl = max(0, l_cols - m_width)
            out["rows_lost"] += rl
            out["columns_lost"] += cl
            out["columns_gained"] += max(0, m_width - l_cols)
            entry["rows_lost"] += rl
            entry["columns_lost"] += cl
            entry["shapes"].append("%dx%d->%dx%d" % (l_rows, l_cols, m_rows, m_width))
        else:
            # the text strategy over-splits both ways (a wrapped line is a row, a gap a column): it says a table is
            # there and its cells agree — no number is taken from it
            out["tables_witnessed_text"] += 1
            entry["shapes"].append("text->%dx%d" % (m_rows, m_width))
    out["pages_with_columns_lost"] = sum(1 for v in per_page.values() if v["columns_lost"])
    for v in sorted(per_page.values(), key=lambda v: -(v["columns_lost"] * 10 + v["rows_lost"]))[:WORST_CAP]:
        worst.append({"page": v["page"], "columns_lost": v["columns_lost"], "rows_lost": v["rows_lost"], "shapes": v["shapes"]})
    return _finish(out)
