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
"""
from __future__ import annotations

import re

CELL_AGREE = 0.5           # the floor on Marker's non-empty cells found in the witness's text; below it the witness is none
ROW_TOL = 0.25             # a lines witness whose row count is off Marker's by more than this share (or 2 rows) is no witness
                           # for columns: RBC's sparse rulings read 4 × 17 against Marker's 20 × 13 with the cells agreeing
STRATEGIES = ("lines", "text")
WORST_CAP = 10
TABLE_TYPES = ("Table",)


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
            cols = sum(1 for c in range(t.col_count) if any(row[c] not in (None, "") for row in ext if c < len(row)))
            rows = sum(1 for row in ext if any(x not in (None, "") for x in row))
        else:
            cols, rows = t.col_count, t.row_count
        return strat, rows, cols, text
    return None


def table_shape(doc, blocks: list[dict], lane: str) -> dict:
    """`doc` an open pymupdf document (the source) or its path, `blocks` blocks.json's list, `lane` "clean" or "scan"."""
    tables = [b for b in blocks if b.get("block_type") in TABLE_TYPES and b.get("bbox") and b.get("page") is not None]
    worst: list[dict] = []                # the worst pages, appended at the end (a list the returned block names)
    out = {"meaning": "the source's table geometry inside each Marker table box against Marker's rows and width; "
                      "columns from the lines witness only, rows from both; a witness whose cells disagree is none",
           "cell_agree_floor": CELL_AGREE, "tables_total": len(tables), "tables_witnessed_lines": 0,
           "tables_witnessed_text": 0, "tables_disagree": 0, "tables_unread": 0, "columns_lost": 0,
           "columns_gained": 0, "rows_lost": 0, "pages_with_columns_lost": 0, "worst": worst}
    if lane != "clean":
        out["tables_unread"] = len(tables)
        out["reason"] = "the scan lane's layer is no witness for geometry"
        return out
    import fitz  # the converter already runs on marker-env; kept local so a reader of the block needs no pymupdf

    if isinstance(doc, (str, bytes)) or hasattr(doc, "__fspath__"):
        try:
            doc = fitz.open(doc)
        except Exception:  # noqa: BLE001 — a source the library cannot open: every table unread, never a crash at ship
            out["tables_unread"] = len(tables)
            out["reason"] = "the source could not be opened for its geometry"
            return out
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
    return out
