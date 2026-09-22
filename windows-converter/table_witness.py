# -*- coding: utf-8 -*-
"""table_witness.py — THE CELL-LEVEL WITNESS (S211 Lane C: table_shape.py's geometry says a table lost rows or columns;
this module says WHICH row, and how — dropped whole, merged into a neighbour, split across two, echoed, a header cut
mid-word, or carried onto the next page). Report-only, stdlib + pymupdf, standing alone (nothing here is imported from
fidelity_audit.py — the two functions it would otherwise share, `_numeric_word` and the `_NUM_TOKEN` regex, are copied
verbatim below with their own citation).

For every Table / TableGroup block Marker wrote (blocks.json: `page` 0-based, `bbox` in PDF points, `html`), the
source's own words INSIDE the block's box (pymupdf `get_text("words")`, clipped the same way figure_text.py clips —
`fitz.Rect(*bbox) & page.rect`), clustered into ROW BANDS by y-centre: a word joins the open band when its centre sits
within BAND_Y_FRACTION of the table's own median word height of the band's running mean centre, else it opens a new
band. Each band carries `label` (its leading non-numeric words, at most LABEL_MAX_WORDS — the same test
`fidelity_audit._row_label` uses, `_numeric_word` copied) and `figures` (its number-shaped tokens, `_NUM_TOKEN`
copied).

The RENDERED rows come from the same block's html: each `<tr>` its cells (`<td>`/`<th>`, every other tag stripped, a
`<br>` kept as a ` <BR> ` marker so a cell that merged two labels can be told from one that never held two), the row's
first cell, its own figures (`_NUM_TOKEN` over the row's whole text), and its whole text.

Per LABELLED, FIGURE-BEARING layer band, the four readings, checked in this order (each strictly narrower than the
one before, so the more specific finding wins): MERGED — the label sits inside a rendered row's first cell that ALSO
holds a second FIGURED band's label DISJOINTLY (a nested shorter label is one label; a figure-less band's label folded
in — a section header, a wrapped units line — is a LABEL_JOINED reading beside the match, never a row lost); SPLIT — the band's figures are spread whole across two
ADJACENT rendered rows (neither alone carrying every figure) and at least one of the two carries no label of its own
— checked before a plain match so a labelled-but-incomplete row is not claimed as a full match; MATCHED — a rendered
row's first cell holds the label word-bounded (the band's OWN row: its figures agreeing, else one no twin band of the
same label claims), or that row's own text holds every one of the band's figures; DROPPED — none of
the above, no rendered row anywhere in the table carries the label or the figures. A rendered cell holding COLLAPSE_MIN_BANDS or more bands' labels is a COLLAPSE (the
table in one cell — RBC AR p.147: 31 bands in row 0, 47 empty rows after it), reported as one reading with its band count,
never as that many merges. A band qualifies for the four readings only with a DATA figure — a bare year is none (a
column-header line, a note naming years). Two further readings read the rendered rows
themselves, not the bands: ECHO (a row's whole text is a near-duplicate of the row directly before it — difflib's
ratio at or above ECHO_SIMILARITY — or its figures are the row before's with digits swapped and most of them in none
of the box's own words, kind "figures") and HEADER_CUT (a `<th>` cell — or, when the table has none, a first-row cell —
whose text is a proper prefix or suffix, 3+ letters, of some word the layer itself carries in the table's box: `Tra`
/ `ansfer`). A fifth, CROSS_PAGE, is tagged Inferred and reported as a bool only when it could be evaluated at all: a
block whose bbox bottom sits within CROSS_PAGE_MARGIN_PT of the page bottom (else None, the reading never applied)
reads True only when its own last band carries no figures AND the immediately following page's first Table/
TableGroup block's first band does — a candidate this module can raise, never confirm alone.

Report-only (docs/15 §12: the gates are two and signed, this key is neither); docs/34: every number names its
numerator, denominator and conditions. A `*_total` reads None when its own population, `tables_read`, is 0 — no
table was measured, never a zero over nothing. `tables_unread` names each table's own reason (no words inside the
box; the box off the page; an html without a `<tr>`; a block on a page index the document does not have)."""
from __future__ import annotations

import difflib
import re

BAND_Y_FRACTION = 0.6          # a word joins the open band when its y-centre sits within this fraction of the
                                # table's median word height of the band's own running mean centre
ECHO_SIMILARITY = 0.85         # difflib.SequenceMatcher ratio at/above which a rendered row is a near-duplicate
# S211 E5 (the verifier's item 3, read on Desjardins p.249): the OCR echo of a row is NOT a near-duplicate string — its
# label is garbled and its FIGURES are the real row's with swapped digits (3,136 → 3,130; 1,286 → 1,200; 6,469 → 0,407;
# 8,866 → 0,000), the same count and the same lengths. difflib read those pairs 0.48–0.64 and the threshold was never
# lowered blind: the figure-echo is its own shape — aligned figures of equal length sharing most characters in place.
# Calibrated on the read pairs and on every adjacent rendered-row pair of five bank annual reports (15,394 pairs): digit
# similarity ALONE called 56–146 legitimate pairs echoes (Amortized cost / Fair value; Total / Canadian equivalent) — so
# the echo is anchored to the LAYER: an echoed row's corrupted figures exist nowhere in the box's own words (row 7's
# 3,130 · 1,200 · 2,137 · 7,100 · 23,041 are in no band; a legitimate near-equal row has every figure in the layer).
# Under that anchor the shape reads 3 of the 4 hand-read pairs and ONE control pair in 15,394 — NBC AR p.209's
# 'Options written 50,168 57,188 28,410 7,577' echoed as 30,100 37,100 20,410 1,511, an OCR echo the control found.
ECHO_MIN_FIGURES = 3           # both rows carry at least this many figures for the figure-echo test to apply
ECHO_FIGURE_CHAR_SHARE = 0.5   # an aligned pair of equal-length figures is "the same digits swapped" at/above this share
ECHO_FIGURE_PAIR_SHARE = 0.5   # the row is a figure-echo when this share of its aligned pairs read so ...
ECHO_FIGURE_ABSENT_SHARE = 0.5  # ... AND this share of its figures are in none of the box's own words
BOX_PAD_PT = 6.0               # the box padded by this before its words are read: a word straddling the edge is its own
COLLAPSE_MIN_BANDS = 3         # a rendered cell holding this many bands' labels is a COLLAPSE (the table in one cell), not merges
_YEAR = re.compile(r"(19|20)\d\d")   # a band whose only figures are years is a header or a note, never a data row
ROTATED_LINE_SHARE = 0.5       # a box whose lines are this share (or more) non-horizontal is rotated text — UNREAD
BOX_SHORT_MIN_FIGURES = 2      # this many figures the rendered rows carry lying OUTSIDE the box read the box short — UNREAD
CROSS_PAGE_MARGIN_PT = 36.0    # a block within this many PDF points of the page bottom (0.5in) is a cross-page candidate
HEADER_CUT_MIN_LETTERS = 3     # a layer word must carry at least this many letters to be a header-cut match
HEADER_CUT_MIN_CELL_LETTERS = 2  # a header cell must carry at least this many letters to be tested at all
LABEL_MAX_WORDS = 6            # a band's label stops after this many leading non-numeric words
WORST_CAP = 10
TABLE_TYPES = ("Table", "TableGroup")

# copied from fidelity_audit.py (S211 E3), not imported, so this module stands alone
_NUM_TOKEN = re.compile(r"(?<![\d,])\d{1,3}(?:,\d{3})+(?![\d,])|(?<![\d,.])\d{4,}(?![\d,])")   # grouped thousands, or 4+ digits


def _numeric_word(word: str) -> bool:
    """copied from fidelity_audit._numeric_word: a word that IS a figure — a number token whole, digits and their
    punctuation only, or a figure with its unit glued (`1000nm`, `12%`, `4.5x`) — a word that begins with a digit is
    a figure, never a label word."""
    s = word.strip("()$,;:.")
    if _NUM_TOKEN.fullmatch(s) or re.fullmatch(r"[\d,.()$%–-]+", word):
        return True
    return bool(s) and s[0].isdigit()


def _label_in(label: str, text: str) -> bool:
    """whether `label` appears in `text` as a whole phrase, word-boundary safe on both ends — a naive substring test
    would read a short label as present inside an unrelated LONGER label that merely contains it as a raw substring
    (Scotiabank p.51: 'Secured funding' is a substring of 'Unsecured funding' and would otherwise be read as merged
    into it, hiding the row that carries 'Secured funding' on its own, whole and correctly)."""
    if not label or not text:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(label.lower()) + r"(?![a-z0-9])"
    return bool(re.search(pattern, text.lower()))


def _remove_label(text: str, label: str) -> str:
    """`text` with every word-bounded occurrence of `label` blanked (case-insensitive) — what is left of a first cell
    once one of its labels is taken out."""
    if not label or not text:
        return text or ""
    pattern = r"(?<![a-zA-Z0-9])" + re.escape(label) + r"(?![a-zA-Z0-9])"
    return re.sub(pattern, " ", text, flags=re.I)


def _merge_evidence(fc: str, label: str, others: list[tuple]) -> "tuple | None":
    """what a rendered first cell holding `label` also holds, or None: ("merged", other label) when a second FIGURED
    band's label is present DISJOINTLY — the shorter of the two still there once the longer is blanked — two data
    rows in one cell, a row lost as a row; ("joined", other label) when
    the disjoint other is a figure-less band (a section header glued to its first row, a units line wrapped over two
    layer lines) — a label join, the row's own figures intact, reported apart. A shorter label nested inside a longer
    one ('AUA' inside 'Average AUA', 'Interest rate derivatives' inside 'Total interest rate derivatives', 'FVTPL
    securities' inside 'Total FVTPL securities') is ONE label, not two (S211 E5, the verifier's item 2: five false
    merges on CIBC p.162, seven on RBC p.41, and the control page BMO Q3 p.63 named a shape it does not carry). The
    `<BR>` marker alone is no evidence: a two-line label wraps over a `<br>` too."""
    found = None
    for ol, figured in others:
        if ol.lower() == label.lower() or not _label_in(ol, fc):
            continue
        longer, shorter = (ol, label) if len(ol) >= len(label) else (label, ol)
        if _label_in(shorter, _remove_label(fc, longer)):      # the shorter survives the longer's removal: two labels
            if figured:
                return "merged", ol
            found = found or ("joined", ol)
    return found


_TR_SPLIT = re.compile(r"(?i)<tr[^>]*>")
_CELL_RE = re.compile(r"(?is)<(t[dh])[^>]*>(.*?)</t[dh]>")
_BR_RE = re.compile(r"(?i)<br\s*/?>")
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_cell(fragment: str) -> str:
    """a cell's inner html: `<br>` kept as a ` <BR> ` marker (so a merge across a line break can be told from one
    that never held two labels), every other tag stripped to a space, entities unescaped, whitespace collapsed."""
    from html import unescape
    marked = _BR_RE.sub(" <BR> ", fragment)
    text = unescape(_TAG_RE.sub(" ", marked))
    return re.sub(r"\s+", " ", text).strip()


def _rendered_rows(html: str) -> list[dict]:
    """each `<tr>` of the block's html, in rendering order: idx (0-based), cells (tags stripped, `<br>` kept as
    ` <BR> `), is_header (the row carries a `<th>`), first_cell, figures (`_NUM_TOKEN` over the row's whole text),
    text (the row's cells joined). A `<tr>` with no `<td>`/`<th>` inside it is skipped (no cell, no row)."""
    rows: list[dict] = []
    for idx, frag in enumerate(_TR_SPLIT.split(html or "")[1:]):
        cell_matches = _CELL_RE.findall(frag)
        if not cell_matches:
            continue
        cells = [_strip_cell(c) for _tag, c in cell_matches]
        is_header = any(tag.lower() == "th" for tag, _c in cell_matches)
        text = " ".join(cells)
        rows.append({"idx": idx, "cells": cells, "is_header": is_header,
                     "first_cell": cells[0] if cells else "", "figures": _NUM_TOKEN.findall(text), "text": text,
                     "empty": not any(c.strip() for c in cells)})
    return rows


def _data_figures(figs: list[str]) -> list[str]:
    """the figures that are not bare years — a band carrying only years (a column-header line 'October 31 2025 2024',
    a note 'The total balances were 2025, 2024, 2023') is a header or prose, never a data row."""
    return [f for f in figs if not _YEAR.fullmatch(f)]


def _qualifies(band: dict) -> bool:
    return bool(band["label"]) and bool(_data_figures(band["figures"]))


def _band_label(words: list[tuple]) -> str:
    """the leading non-numeric words of a band (mirrors fidelity_audit._row_label's test on a layer line), at most
    LABEL_MAX_WORDS; empty when the band opens with a number."""
    label: list[str] = []
    for w in words:
        if _numeric_word(w[4]):
            break
        label.append(w[4])
        if len(label) >= LABEL_MAX_WORDS:
            break
    return " ".join(label)


def _cluster_bands(words: list[tuple]) -> list[dict]:
    """pymupdf `get_text("words")` tuples clustered into row bands by y-centre (BAND_Y_FRACTION of the table's own
    median word height); each band a literal {words, label, figures, text}, its words left-to-right."""
    if not words:
        return []
    heights = sorted(w[3] - w[1] for w in words if w[3] > w[1])
    median_h = heights[len(heights) // 2] if heights else 1.0
    tol = max(1.0, median_h * BAND_Y_FRACTION)
    ordered = sorted(words, key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    raw_bands: list[list] = []
    current: list = []
    current_y = None
    for w in ordered:
        yc = (w[1] + w[3]) / 2
        if current and abs(yc - current_y) > tol:
            raw_bands.append(current)
            current = []
        current.append(w)
        current_y = sum((v[1] + v[3]) / 2 for v in current) / len(current)
    if current:
        raw_bands.append(current)
    bands: list[dict] = []
    for raw in raw_bands:
        row_words = sorted(raw, key=lambda w: w[0])
        text = " ".join(w[4] for w in row_words)
        bands.append({"words": row_words, "label": _band_label(row_words), "figures": _NUM_TOKEN.findall(text),
                      "text": text})
    return bands


def _classify_band(i: int, band: dict, bands: list[dict], rows: list[dict]) -> tuple[str, dict]:
    """one band already filtered to carry a label AND at least one figure, against the table's rendered rows.
    Checked in order MERGED, SPLIT, MATCHED, else DROPPED — each narrower than the one before it (SPLIT before
    MATCHED so a row that carries the label but only part of the figures, the rest on an adjacent unlabelled row,
    is not claimed as a full match).

    S211 E5 (the verifier's item 1, Scotiabank p.51 read straight): the label test is word-bounded on BOTH paths
    (`_label_in`, never a bare substring — 'Secured funding' is not inside 'Unsecured funding'), and the band's OWN
    row is preferred: among the rows whose first cell holds the label, the one whose figures hold the band's; failing
    that, one no TWIN band (the same label elsewhere on the page, its own figures) already accounts for. The page's
    second 'Secured funding' band, rendered nowhere, reads DROPPED — before this it was MATCHED to the first section's
    row on a substring hit and the loss was silent. A match carries `figures_agree` so a label found with other figures
    under it is visible as such."""
    label = band["label"]
    figs = band["figures"]
    fig_set = set(figs)
    others = [(b["label"], bool(b["figures"])) for j, b in enumerate(bands) if j != i and b["label"]]
    twin_figs = [set(b["figures"]) for j, b in enumerate(bands)
                 if j != i and b["figures"] and b["label"].lower() == label.lower()]

    def overlap(row, s=fig_set):
        return len(s & set(row["figures"]))

    def figs_in(row):
        return bool(fig_set) and fig_set.issubset(set(row["figures"]))

    label_rows = [r for r in rows if _label_in(label, r["first_cell"])]
    own: list[dict] = []
    if label_rows:
        best = max(overlap(r) for r in label_rows)
        if best > 0:
            own = [r for r in label_rows if overlap(r) == best]      # the row holding the most of the band's figures
        else:
            own = [r for r in label_rows if not any(overlap(r, s) for s in twin_figs)]   # a twin's row is not this band's
    figures_agree = bool(own) and figs_in(own[0])
    joined = None
    for row in own:
        ev = _merge_evidence(row["first_cell"], label, others)
        if ev and ev[0] == "merged":
            return "merged", {"label": label, "figures": figs, "row": row["idx"], "first_cell": row["first_cell"],
                              "evidence": "other:" + ev[1]}
        if ev and joined is None:
            joined = {"label": label, "row": row["idx"], "first_cell": row["first_cell"], "joined": ev[1]}
    if not figures_agree:
        for k in range(len(rows) - 1):
            r1, r2 = rows[k], rows[k + 1]
            combined = set(r1["figures"]) | set(r2["figures"])
            if fig_set and fig_set.issubset(combined) and not fig_set.issubset(set(r1["figures"])) \
                    and not fig_set.issubset(set(r2["figures"])):
                r1_labelled = bool(r1["first_cell"].split()) and not _numeric_word(r1["first_cell"].split()[0])
                r2_labelled = bool(r2["first_cell"].split()) and not _numeric_word(r2["first_cell"].split()[0])
                if not (r1_labelled and r2_labelled):
                    return "split", {"label": label, "figures": figs, "rows": [r1["idx"], r2["idx"]]}
    if own:
        entry = {"label": label, "figures": figs, "row": own[0]["idx"], "via": "label", "figures_agree": figures_agree}
        if joined:
            entry["label_joined"] = joined["joined"]
        return "matched", entry
    fig_rows = [r for r in rows if figs_in(r)]
    if fig_rows:
        return "matched", {"label": label, "figures": figs, "row": fig_rows[0]["idx"], "via": "figures",
                           "figures_agree": True}
    return "dropped", {"label": label, "figures": figs, "label_rendered_for_twin": bool(label_rows)}


def _row_key(first_cell: str) -> str:
    """the first cell's first four words, lower-cased and stripped of everything but letters and digits — the key a
    rendered row and a layer band share (an en-dash against a hyphen, a footnote mark, a wrapped tail: none of them
    breaks it)."""
    words = first_cell.split()[:4]
    return re.sub(r"[^0-9a-z]+", "", " ".join(words).lower())


def _figure_echo_share(fa: list[str], fb: list[str]) -> "float | None":
    """the share of two rows' aligned figures that are the same digits swapped (equal length, ECHO_FIGURE_CHAR_SHARE
    of the characters in place) — Desjardins p.249's shape; None when the test does not apply (fewer than
    ECHO_MIN_FIGURES on either row, or counts more than one apart)."""
    if len(fa) < ECHO_MIN_FIGURES or len(fb) < ECHO_MIN_FIGURES or abs(len(fa) - len(fb)) > 1:
        return None
    n = min(len(fa), len(fb))
    similar = 0
    for a, b in zip(fa[:n], fb[:n]):
        if len(a) == len(b) and sum(1 for x, y in zip(a, b) if x == y) / len(a) >= ECHO_FIGURE_CHAR_SHARE:
            similar += 1
    return similar / n


def _echo_pairs(rows: list[dict], layer_figs: set, bands: list[dict]) -> list[dict]:
    """adjacent rendered rows that echo one another, in rendering order — each {rows: [predecessor idx, row idx],
    kind, score}: kind "text" when the whole texts are near-identical (difflib at/above ECHO_SIMILARITY), the
    two first cells share their KEY (the first four words, normalised) AND the rendering holds more rows with that
    key than the layer holds bands with it — a row
    the rendering repeats and the layer has once (S211 E5, read on RBC AR p.147: two adjacent EMPTY rows are no echo,
    nor are 'income taxes – reported' / '– adjusted', two rows the layer has); kind "figures" when the row's figures
    are the row before's with digits swapped AND most of them are in none of the box's own words (`layer_figs`; the
    OCR echo, whose label is garbled so the text ratio never reaches the threshold, and whose corrupted figures the
    layer never carried)."""
    pairs: list[dict] = []
    for k in range(1, len(rows)):
        a, b = rows[k - 1], rows[k]
        if a["empty"] or b["empty"] or not a["text"].strip() or not b["text"].strip():
            continue
        ratio = difflib.SequenceMatcher(None, a["text"], b["text"]).ratio()
        key = _row_key(b["first_cell"])
        if ratio >= ECHO_SIMILARITY and key and key == _row_key(a["first_cell"]):
            n_rendered = sum(1 for r in rows if _row_key(r["first_cell"]) == key)
            n_layer = sum(1 for bd in bands if key in re.sub(r"[^0-9a-z]+", "", bd["text"].lower()))
            if n_rendered > n_layer:
                pairs.append({"rows": [a["idx"], b["idx"]], "kind": "text", "score": round(ratio, 3),
                              "rendered": n_rendered, "layer": n_layer})
            continue
        share = _figure_echo_share(a["figures"], b["figures"])
        if share is None or share < ECHO_FIGURE_PAIR_SHARE:
            continue
        absent = sum(1 for f in b["figures"] if f not in layer_figs) / len(b["figures"])
        if absent >= ECHO_FIGURE_ABSENT_SHARE:
            pairs.append({"rows": [a["idx"], b["idx"]], "kind": "figures", "score": round(share, 3),
                          "figures_absent_from_layer": round(absent, 3)})
    return pairs


def _is_proper_affix(cell_text: str, word: str) -> bool:
    c = cell_text.strip().lower()
    w = word.strip().lower()
    if len(c) < HEADER_CUT_MIN_CELL_LETTERS or len(w) < HEADER_CUT_MIN_LETTERS:
        return False
    if not c.isalpha() or not w.isalpha() or c == w:
        return False
    return w.startswith(c) or w.endswith(c)


def _header_cuts(rows: list[dict], bands: list[dict]) -> list[dict]:
    """header cells (every `<th>`, or — when the table carries none — the first rendered row's cells) whose text is
    a proper prefix or suffix of some word the layer carries anywhere in the table's box."""
    header_cells: list[tuple[int, str]] = []
    for row in rows:
        if row["is_header"]:
            header_cells.extend((row["idx"], c) for c in row["cells"])
    if not header_cells and rows:
        header_cells = [(rows[0]["idx"], c) for c in rows[0]["cells"]]
    layer_words = [w[4] for b in bands for w in b["words"]]
    cuts: list[dict] = []
    seen: set[tuple[int, str]] = set()
    for row_idx, cell in header_cells:
        if (row_idx, cell) in seen:
            continue
        for word in layer_words:
            if _is_proper_affix(cell, word):
                cuts.append({"row": row_idx, "cell": cell, "layer_word": word})
                seen.add((row_idx, cell))
                break
    return cuts


def _cross_page_candidate(bbox, page_height: float, bands: list[dict], next_first_band: "dict | None"):
    """None when the block's bbox bottom is not within CROSS_PAGE_MARGIN_PT of the page bottom (not applicable);
    else True only when this table's own last band carries no figures and the next page's first table's first band
    does — a candidate this module raises, never confirms alone (Inferred)."""
    if bbox[3] < page_height - CROSS_PAGE_MARGIN_PT:
        return None
    if not bands or bands[-1]["figures"]:
        return False
    if next_first_band is None:
        return False
    return bool(next_first_band["figures"])


def _unread_table(block: dict, reason: str) -> dict:
    return {"page": block["page"] + 1, "block_type": block.get("block_type"), "bbox": block.get("bbox"),
            "rows_layer": None, "rows_rendered": None, "rows_rendered_empty": None, "bands_qualifying": None,
            "bands": [], "matched": [], "dropped": [], "merged": [], "collapsed": [], "split": [], "echo": [],
            "header_cut": [], "label_joined": [], "cross_page_candidate": None, "unread": reason,
            "rows_unread": reason}


def _rotated_lines(page, clip) -> tuple[int, int]:
    """(non-horizontal lines, lines) inside the box, from the page's text dict — a 90° table (SYM-142's shards,
    McGill p.117's rotated row headers) clusters into single-word bands no reading can use; it is named UNREAD."""
    try:
        d = page.get_text("dict", clip=clip)
    except Exception:  # noqa: BLE001 — a geometry the library cannot read is no witness, never a crash at ship
        return 0, 0
    lines = [ln for b in d.get("blocks", []) for ln in b.get("lines", [])]
    rotated = sum(1 for ln in lines if abs(ln.get("dir", (1, 0))[1]) > 0.5)
    return rotated, len(lines)


def _figures_outside_box(page, clip, bands: list[dict], rows: list[dict]) -> list[str]:
    """figures the RENDERED rows carry that lie on a band's own line but OUTSIDE the box (the verifier's break
    attempt: a bbox drawn short of its table cut off a figure column, the band's remaining figure still matched and
    the truncation was invisible). Read from the page's words in each band's y-range beyond the clip's edges."""
    try:
        page_words = page.get_text("words")
    except Exception:  # noqa: BLE001
        return []
    rendered = set(f for r in rows for f in r["figures"])
    inside = set(f for b in bands for f in b["figures"])   # the whole box's figures: a header year on a band's line
    found: list[str] = []                                   # outside the box is the neighbour table's, not a short box
    for band in bands:
        if not _qualifies(band):
            continue
        ys = [(w[1] + w[3]) / 2 for w in band["words"]]
        y_lo, y_hi = min(ys), max(ys)
        hs = [w[3] - w[1] for w in band["words"] if w[3] > w[1]]
        tol = max(1.0, (sorted(hs)[len(hs) // 2] if hs else 2.0) * BAND_Y_FRACTION)
        for w in page_words:
            yc = (w[1] + w[3]) / 2
            if yc < y_lo - tol or yc > y_hi + tol:
                continue
            if clip.x0 <= w[0] and w[2] <= clip.x1:
                continue
            for f in _NUM_TOKEN.findall(w[4]):
                if f in rendered and f not in inside and f not in found:
                    found.append(f)
    return found


def _read_table(page, block: dict, next_first_band: "dict | None") -> dict:
    """one Table/TableGroup block against the page's own words inside its box. S211 E5 (the verifier's item 4): a
    table this witness cannot read says so by name, never a clean-looking zero — rotated text in the box, no band
    carrying both a label and a figure of _NUM_TOKEN's shape (a qualitative table, an engineering table of small
    values: a whole row deleted from it read exactly like a clean one), a box short of its own table."""
    import fitz

    bbox = block["bbox"]
    html = block.get("html", "") or ""
    if len(_TR_SPLIT.split(html)) < 2:
        return _unread_table(block, "an html without a <tr>")
    clip = fitz.Rect(*bbox) & page.rect
    if clip.is_empty:
        return _unread_table(block, "the box off the page")
    clip = (clip + (-BOX_PAD_PT, -BOX_PAD_PT, BOX_PAD_PT, BOX_PAD_PT)) & page.rect   # a word straddling the edge is the box's own
    words = page.get_text("words", clip=clip)
    if not words:
        return _unread_table(block, "no words inside the box")
    rotated, n_lines = _rotated_lines(page, clip)
    if n_lines and rotated / n_lines >= ROTATED_LINE_SHARE:
        return _unread_table(block, "rotated text in the box (%d of %d lines)" % (rotated, n_lines))
    bands = _cluster_bands(words)
    rows = _rendered_rows(html)
    # the ROW readings' own population: a band carrying both a label and a figure of _NUM_TOKEN's shape. A table with
    # none (a qualitative table, an engineering table of small values) has its rows UNREAD by name — echo, header_cut
    # and cross_page still read, they never needed a figured band
    rows_unread = None
    if not any(_qualifies(b) for b in bands):
        rows_unread = "no band carries both a label and a figure (the row readings need labelled, figured rows)"
    outside = _figures_outside_box(page, clip, bands, rows)
    if len(outside) >= BOX_SHORT_MIN_FIGURES:
        return _unread_table(block, "the box is short of its table: %d figures the rendered rows carry lie outside it (%s)"
                             % (len(outside), ", ".join(outside[:4])))
    matched: list[dict] = []
    dropped: list[dict] = []
    merged: list[dict] = []
    split: list[dict] = []
    label_joined: list[dict] = []
    for i, band in enumerate(bands):
        if not _qualifies(band):
            continue
        kind, entry = _classify_band(i, band, bands, rows)
        if kind == "matched":
            matched.append(entry)
            if entry.get("label_joined"):
                label_joined.append({"label": entry["label"], "row": entry["row"], "joined": entry["label_joined"]})
        elif kind == "merged":
            merged.append(entry)
        elif kind == "split":
            split.append(entry)
        else:
            dropped.append(entry)
    echo = _echo_pairs(rows, set(f for b in bands for f in b["figures"]), bands)
    # S211 E5 (RBC AR p.147/p.150, TD AR p.49/p.123 read straight): a rendered cell that swallowed the whole table —
    # 31 bands' labels in row 0's first cell, 47 empty rows after it — is a COLLAPSE, its own reading, not 31 merges
    by_row: dict[int, list[dict]] = {}
    for m in merged:
        by_row.setdefault(m["row"], []).append(m)
    collapsed: list[dict] = []
    for r_idx, ms in sorted(by_row.items()):
        if len(ms) >= COLLAPSE_MIN_BANDS:
            collapsed.append({"row": r_idx, "bands": len(ms), "labels": [m["label"] for m in ms[:3]],
                              "first_cell": ms[0]["first_cell"][:120]})
    collapsed_rows = {c["row"] for c in collapsed}
    merged = [m for m in merged if m["row"] not in collapsed_rows]
    header_cut = _header_cuts(rows, bands)
    cross = _cross_page_candidate(bbox, page.rect.height, bands, next_first_band)
    bands_compact = [{"label": b["label"], "figures": b["figures"], "text": b["text"]} for b in bands]
    return {"page": block["page"] + 1, "block_type": block.get("block_type"), "bbox": bbox, "rows_layer": len(bands),
            "rows_rendered": len(rows), "rows_rendered_empty": sum(1 for r in rows if r["empty"]),
            "bands_qualifying": sum(1 for b in bands if _qualifies(b)), "bands": bands_compact, "matched": matched,
            "dropped": dropped, "merged": merged, "collapsed": collapsed, "split": split, "echo": echo,
            "header_cut": header_cut, "label_joined": label_joined, "cross_page_candidate": cross, "unread": None,
            "rows_unread": rows_unread}


def table_witness(pdf_path, blocks: list[dict], pages: "list[int] | None" = None, lane: str = "clean") -> dict:
    """`pdf_path` a path to the source PDF (or an already-open pymupdf document, for a caller/selftest that has one
    open already), `blocks` blocks.json's list, `pages` an optional list of 1-indexed page numbers to restrict to
    (the CLI's `--pages`); None reads every Table/TableGroup block in `blocks`. `lane` "clean" or "scan": the scan
    lane's layer is its own OCR, no witness for rows — every table UNREAD with that reason (table_shape's rule)."""
    all_tables = [b for b in (blocks or []) if b.get("block_type") in TABLE_TYPES and b.get("bbox") is not None
                  and b.get("page") is not None]
    if pages is not None:
        page_set = {int(p) - 1 for p in pages}
        tables_blocks = [b for b in all_tables if b["page"] in page_set]
    else:
        tables_blocks = all_tables
    worst: list[dict] = []
    tables: list[dict] = []
    out = {"meaning": "the source's own words inside each Marker Table/TableGroup box, clustered into row bands and "
                      "read against that block's rendered <tr> rows; page is 1-indexed (blocks.json's own page + "
                      "1); a *_total is None when tables_read is 0 (no table was measured, never a zero over "
                      "nothing); rows_dropped/merged/split_total are over tables_rows_read (the read tables with "
                      "a labelled, figured band — the others carry rows_unread by name) and None when that is 0; "
                      "cross_page_candidates and cross_page_population are None only when tables_read "
                      "is 0 — cross_page_population itself names how many read tables sat within "
                      "cross_page_margin_pt of their page bottom (the population the True/False count is over), "
                      "and is a measured 0 when none did",
           "tables_total": len(tables_blocks), "tables_read": 0, "tables_unread": 0, "tables_rows_read": 0,
           "tables_rows_unread": 0, "rows_layer_total": 0,
           "rows_rendered_total": 0, "rows_dropped_total": 0, "rows_merged_total": 0, "rows_split_total": 0,
           "rows_collapsed_total": 0, "tables_collapsed": 0, "echo_total": 0, "header_cut_total": 0,
           "label_joined_total": 0, "cross_page_population": 0, "cross_page_candidates": 0,
           "worst": worst, "tables": tables,
           "constants": {"band_y_fraction": BAND_Y_FRACTION, "echo_similarity": ECHO_SIMILARITY,
                         "collapse_min_bands": COLLAPSE_MIN_BANDS,
                         "echo_min_figures": ECHO_MIN_FIGURES, "echo_figure_char_share": ECHO_FIGURE_CHAR_SHARE,
                         "echo_figure_pair_share": ECHO_FIGURE_PAIR_SHARE,
                         "echo_figure_absent_share": ECHO_FIGURE_ABSENT_SHARE, "rotated_line_share": ROTATED_LINE_SHARE,
                         "box_short_min_figures": BOX_SHORT_MIN_FIGURES, "box_pad_pt": BOX_PAD_PT,
                         "cross_page_margin_pt": CROSS_PAGE_MARGIN_PT,
                         "header_cut_min_letters": HEADER_CUT_MIN_LETTERS,
                         "header_cut_min_cell_letters": HEADER_CUT_MIN_CELL_LETTERS,
                         "label_max_words": LABEL_MAX_WORDS, "worst_cap": WORST_CAP}}
    if not tables_blocks:
        out["rows_layer_total"] = out["rows_rendered_total"] = out["rows_dropped_total"] = None
        out["rows_merged_total"] = out["rows_split_total"] = out["echo_total"] = out["header_cut_total"] = None
        out["label_joined_total"] = out["rows_collapsed_total"] = out["tables_collapsed"] = None
        out["cross_page_population"] = out["cross_page_candidates"] = None
        return out
    if lane != "clean":
        for b in tables_blocks:
            tables.append(_unread_table(b, "the scan lane's layer is no witness for rows"))
        out["tables_unread"] = len(tables)
        out["rows_layer_total"] = out["rows_rendered_total"] = out["rows_dropped_total"] = None
        out["rows_merged_total"] = out["rows_split_total"] = out["echo_total"] = out["header_cut_total"] = None
        out["label_joined_total"] = out["rows_collapsed_total"] = out["tables_collapsed"] = None
        out["cross_page_population"] = out["cross_page_candidates"] = None
        out["reason"] = "the scan lane's layer is no witness for rows"
        return out
    import fitz  # the converter already runs on marker-env; kept local so a reader of the block needs no pymupdf

    if isinstance(pdf_path, (str, bytes)) or hasattr(pdf_path, "__fspath__"):
        try:
            doc = fitz.open(pdf_path)
        except Exception:  # noqa: BLE001 — a source the library cannot open: every table unread, never a crash at ship
            out["tables_unread"] = len(tables_blocks)
            out["rows_layer_total"] = out["rows_rendered_total"] = out["rows_dropped_total"] = None
            out["rows_merged_total"] = out["rows_split_total"] = out["echo_total"] = out["header_cut_total"] = None
            out["label_joined_total"] = out["rows_collapsed_total"] = out["tables_collapsed"] = None
            out["cross_page_population"] = out["cross_page_candidates"] = None
            out["reason"] = "the source could not be opened"
            return out
    else:
        doc = pdf_path
    by_page: dict[int, list[dict]] = {}
    for b in all_tables:
        by_page.setdefault(b["page"], []).append(b)
    for p in by_page:
        by_page[p].sort(key=lambda b: b["bbox"][1])
    first_band_cache: dict[int, "dict | None"] = {}

    def _first_band_of_page(pn: int):
        if pn in first_band_cache:
            return first_band_cache[pn]
        blist = by_page.get(pn)
        result = None
        if blist and 0 <= pn < len(doc):
            pg = doc[pn]
            clip = fitz.Rect(*blist[0]["bbox"]) & pg.rect
            if not clip.is_empty:
                clip = (clip + (-BOX_PAD_PT, -BOX_PAD_PT, BOX_PAD_PT, BOX_PAD_PT)) & pg.rect
                words = pg.get_text("words", clip=clip)
                bands = _cluster_bands(words)
                result = bands[0] if bands else None
        first_band_cache[pn] = result
        return result

    for b in tables_blocks:
        p = b["page"]
        if p < 0 or p >= len(doc):
            tables.append(_unread_table(b, "the page index is past the document"))
            continue
        page = doc[p]
        entry = _read_table(page, b, _first_band_of_page(p + 1))
        tables.append(entry)
    read = [t for t in tables if t["unread"] is None]
    out["tables_read"] = len(read)
    out["tables_unread"] = len(tables) - len(read)
    if not read:
        out["rows_layer_total"] = out["rows_rendered_total"] = out["rows_dropped_total"] = None
        out["rows_merged_total"] = out["rows_split_total"] = out["echo_total"] = out["header_cut_total"] = None
        out["label_joined_total"] = out["rows_collapsed_total"] = out["tables_collapsed"] = None
        out["cross_page_population"] = out["cross_page_candidates"] = None
        return out
    out["rows_layer_total"] = sum(t["rows_layer"] for t in read)
    out["rows_rendered_total"] = sum(t["rows_rendered"] for t in read)
    rows_read = [t for t in read if t["rows_unread"] is None]
    out["tables_rows_read"] = len(rows_read)
    out["tables_rows_unread"] = len(read) - len(rows_read)
    if rows_read:
        out["rows_dropped_total"] = sum(len(t["dropped"]) for t in rows_read)
        out["rows_merged_total"] = sum(len(t["merged"]) for t in rows_read)
        out["rows_split_total"] = sum(len(t["split"]) for t in rows_read)
        out["rows_collapsed_total"] = sum(c["bands"] for t in rows_read for c in t["collapsed"])
        out["tables_collapsed"] = sum(1 for t in rows_read if t["collapsed"])
    else:
        out["rows_dropped_total"] = out["rows_merged_total"] = out["rows_split_total"] = None
        out["rows_collapsed_total"] = out["tables_collapsed"] = None
    out["echo_total"] = sum(len(t["echo"]) for t in read)
    out["header_cut_total"] = sum(len(t["header_cut"]) for t in read)
    out["label_joined_total"] = sum(len(t["label_joined"]) for t in rows_read) if rows_read else None
    evaluated = [t for t in read if t["cross_page_candidate"] is not None]
    out["cross_page_population"] = len(evaluated)
    out["cross_page_candidates"] = sum(1 for t in evaluated if t["cross_page_candidate"]) if evaluated else None
    def _score(t):
        return len(t["dropped"]) + len(t["merged"]) + len(t["split"]) + sum(c["bands"] for c in t["collapsed"])

    scored = sorted(read, key=lambda t: -_score(t))
    for t in scored[:WORST_CAP]:
        score = _score(t)
        if score <= 0:
            break
        worst.append({"page": t["page"], "dropped_merged_split_collapsed": score,
                       "collapsed": [c["bands"] for c in t["collapsed"]],
                       "dropped_labels": [d["label"] for d in t["dropped"][:2]]})
    return out


def _load_bundle(bundle_dir):
    import json
    import pathlib

    bundle_dir = pathlib.Path(bundle_dir)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    blocks_doc = json.loads((bundle_dir / "blocks.json").read_text(encoding="utf-8"))
    blocks = blocks_doc.get("blocks", []) if isinstance(blocks_doc, dict) else blocks_doc
    return manifest, blocks


def main(argv=None) -> int:
    import argparse
    import pathlib

    ap = argparse.ArgumentParser(description="table_witness — the cell-level table witness, report-only")
    ap.add_argument("bundle_dir", help="an anchor/held bundle directory (manifest.json + blocks.json beside it)")
    ap.add_argument("--pages", default=None, help="comma-separated 1-indexed page numbers to restrict to")
    ap.add_argument("--pdf-dir", default=None, help="override the drop/done directory holding the source PDF "
                                                      "(default: <bundle's grandparent>/drop/done)")
    args = ap.parse_args(argv)
    bundle_dir = pathlib.Path(args.bundle_dir)
    manifest, blocks = _load_bundle(bundle_dir)
    pdf_dir = pathlib.Path(args.pdf_dir) if args.pdf_dir else bundle_dir.parent.parent / "drop" / "done"
    pdf_path = pdf_dir / manifest["source"]
    pages = [int(x) for x in args.pages.split(",")] if args.pages else None
    result = table_witness(str(pdf_path), blocks, pages=pages)
    print("bundle: %s" % bundle_dir.name)
    print("source: %s" % pdf_path)
    print("tables_total=%s tables_read=%s tables_unread=%s" % (result["tables_total"], result["tables_read"], result["tables_unread"]))
    for t in result["tables"]:
        if t["unread"] is not None:
            print("  p.%d %s UNREAD: %s" % (t["page"], t["block_type"], t["unread"]))
            continue
        print("  p.%d %s rows_layer=%d rows_rendered=%d (empty %d) matched=%d dropped=%d merged=%d collapsed=%s split=%d "
              "echo=%d header_cut=%d cross_page_candidate=%s%s"
              % (t["page"], t["block_type"], t["rows_layer"], t["rows_rendered"], t["rows_rendered_empty"],
                 len(t["matched"]), len(t["dropped"]), len(t["merged"]), [c["bands"] for c in t["collapsed"]],
                 len(t["split"]), len(t["echo"]), len(t["header_cut"]), t["cross_page_candidate"],
                 (" ROWS UNREAD: " + t["rows_unread"]) if t["rows_unread"] else ""))
        for d in t["dropped"]:
            print("      DROPPED  %r figures=%s" % (d["label"], d["figures"]))
        for m in t["merged"]:
            print("      MERGED   %r into row %d first_cell=%r (%s)" % (m["label"], m["row"], m["first_cell"], m["evidence"]))
        for s in t["split"]:
            print("      SPLIT    %r across rows %s" % (s["label"], s["rows"]))
        for c in t["collapsed"]:
            print("      COLLAPSED  %d bands into row %d %r" % (c["bands"], c["row"], c["first_cell"][:60]))
        for e in t["echo"]:
            print("      ECHO     rows %s (%s %.3f)" % (e["rows"], e["kind"], e["score"]))
        for h in t["header_cut"]:
            print("      HEADER_CUT  cell %r ~ layer word %r (row %d)" % (h["cell"], h["layer_word"], h["row"]))
        for j in t["label_joined"]:
            print("      LABEL_JOINED  %r with the figure-less %r (row %d)" % (j["label"], j["joined"], j["row"]))
    print("==== table_witness: %s/%s tables read, %s unread; rows read on %s ====" % (
        result["tables_read"], result["tables_total"], result["tables_unread"], result["tables_rows_read"]))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
