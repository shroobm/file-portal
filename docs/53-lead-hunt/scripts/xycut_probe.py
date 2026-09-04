"""Lane A measurement: a ~50-line recursive XY-cut over block bboxes, CPU-only, no GPU.

Ground truth (declared order) reused verbatim from probe_k_order.py's declared_frags()
(structure-tree pre-order, Door A). "Marker's geometric order" reused verbatim from probe_k's
geom_frags() (pymupdf get_text("dict") raw block-emission order == what pdftext / Marker's
OrderProcessor inherits for non-sliced non-OCR pages, verified by reading
marker/processors/order.py and marker/builders/layout.py this session).

XY-CUT ALGORITHM (recursive, geometry only -- no text, no model):
  1. Project block bboxes onto the Y axis. If there is a horizontal band of the page height
     touched by NO block ("white space" gap) taller than GAP_PX, cut there: split the block
     set into a top group and a bottom group, recurse on each, concatenate top-then-bottom.
  2. If no such Y-gap exists (blocks form one row-band -- e.g. side-by-side columns), project
     onto the X axis instead. If a vertical white-space gap wider than GAP_PX exists, cut
     there: split into a left group and a right group, recurse, concatenate left-then-right.
  3. Base case: neither axis has an internal gap (a single irreducible cluster) -- return the
     blocks sorted by (round(y0/ROW_TOL), x0), i.e. plain row-major order, which is the
     textbook XY-cut leaf rule for a solid text column.

This is deliberately the na\u00efve 1982 Nagy/Seth XY-cut (Meunier 2005, ref [53] in
2401.11874v2) -- no learned model, no ML. ~55 lines including comments below.
"""
import re
import difflib
import sys
import pymupdf

GAP_PX = 4.0     # minimum white-space band (pt) to count as a cut -- avoids cutting on kerning
ROW_TOL = 3.0    # y-tolerance (pt) for "same row" in the leaf rule

NORM = lambda s: re.sub(r"\s+", " ", s).strip()


def _gaps(intervals, lo, hi):
    """Given [(a,b), ...] sub-intervals of [lo,hi], return internal gaps >= GAP_PX wide,
    as a sorted list of (gap_start, gap_end)."""
    ivs = sorted(intervals)
    merged = []
    for a, b in ivs:
        if merged and a <= merged[-1][1] + 1e-6:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    gaps = []
    for i in range(len(merged) - 1):
        g0, g1 = merged[i][1], merged[i + 1][0]
        if g1 - g0 >= GAP_PX:
            gaps.append((g0, g1))
    return gaps


def xy_cut(blocks):
    """blocks: list of dict with 'bbox'=(x0,y0,x1,y1) and 'idx' (original index, opaque payload
    carried through). Returns blocks reordered by recursive XY-cut."""
    if len(blocks) <= 1:
        return blocks
    y0 = min(b["bbox"][1] for b in blocks)
    y1 = max(b["bbox"][3] for b in blocks)
    ygaps = _gaps([(b["bbox"][1], b["bbox"][3]) for b in blocks], y0, y1)
    if ygaps:
        cut = ygaps[0][0] + (ygaps[0][1] - ygaps[0][0]) / 2
        top = [b for b in blocks if (b["bbox"][1] + b["bbox"][3]) / 2 <= cut]
        bot = [b for b in blocks if (b["bbox"][1] + b["bbox"][3]) / 2 > cut]
        if top and bot:
            return xy_cut(top) + xy_cut(bot)
    x0 = min(b["bbox"][0] for b in blocks)
    x1 = max(b["bbox"][2] for b in blocks)
    xgaps = _gaps([(b["bbox"][0], b["bbox"][2]) for b in blocks], x0, x1)
    if xgaps:
        cut = xgaps[0][0] + (xgaps[0][1] - xgaps[0][0]) / 2
        left = [b for b in blocks if (b["bbox"][0] + b["bbox"][2]) / 2 <= cut]
        right = [b for b in blocks if (b["bbox"][0] + b["bbox"][2]) / 2 > cut]
        if left and right:
            return xy_cut(left) + xy_cut(right)
    return sorted(blocks, key=lambda b: (round(b["bbox"][1] / ROW_TOL), b["bbox"][0]))


# ---------------------------------------------------------------------------------------------
# probe_k_order.py's extractors, reused verbatim (not retyped-and-drifted -- imported by value
# since probe_k is a standalone script, not a package)

FL = pymupdf.TEXTFLAGS_DICT | pymupdf.TEXT_COLLECT_STRUCTURE


def declared_frags(page):
    out = []

    def w(bl):
        for b in bl:
            if b.get("type") == 2:
                w(b.get("blocks", []))
            elif b.get("type") == 0:
                out.append("".join(sp["text"] for l in b.get("lines", []) for sp in l["spans"]))
    w(page.get_text("dict", flags=FL)["blocks"])
    return [NORM(x) for x in out if NORM(x)]


def geom_blocks(page):
    """Text blocks with bbox, in pymupdf's raw (content-stream) order -- Marker's baseline."""
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") == 0:
            txt = "".join(sp["text"] for l in b.get("lines", []) for sp in l["spans"])
            if NORM(txt):
                out.append({"bbox": b["bbox"], "text": NORM(txt)})
    return out


def stream(frags):
    return NORM(" ".join(frags)).replace(" ", "")


def compare(a_frags, b_frags, label_a, label_b, page_no, show):
    sa, sb = stream(a_frags), stream(b_frags)
    if not sa and not sb:
        return None
    if sa == sb:
        return "same"
    if sorted(sa) == sorted(sb):
        sm = difflib.SequenceMatcher(None, sa, sb)
        if show:
            print("    page %d: TRUE ORDER DIFF %s vs %s (similarity %.3f)"
                  % (page_no, label_a, label_b, sm.ratio()))
        return "reorder"
    return "content_diff"  # different character sets -- not a pure order question


def run(path, max_pages, negative_control_reversed=True):
    doc = pymupdf.open(path)
    N = min(doc.page_count, max_pages)
    print("=== %s (first %d pages) ===" % (path.split("/")[-1], N))
    xy_vs_geom = {"same": 0, "reorder": 0, "content_diff": 0, "skip": 0}
    xy_vs_decl = {"same": 0, "reorder": 0, "content_diff": 0, "skip": 0}
    geom_vs_decl = {"same": 0, "reorder": 0, "content_diff": 0, "skip": 0}
    shown = 0
    for i in range(N):
        p = doc[i]
        gblocks = geom_blocks(p)
        if not gblocks:
            xy_vs_geom["skip"] += 1
            xy_vs_decl["skip"] += 1
            geom_vs_decl["skip"] += 1
            continue
        for j, b in enumerate(gblocks):
            b["idx"] = j
        xy_ordered = xy_cut(gblocks)
        xy_frags = [b["text"] for b in xy_ordered]
        geom_frags_ = [b["text"] for b in gblocks]
        decl_frags = declared_frags(p)

        r1 = compare(xy_frags, geom_frags_, "xy-cut", "geometric", i, shown < 3)
        r2 = compare(xy_frags, decl_frags, "xy-cut", "declared", i, False)
        r3 = compare(geom_frags_, decl_frags, "geometric", "declared", i, False)
        if r1:
            xy_vs_geom[r1] += 1
            shown += (r1 == "reorder")
        else:
            xy_vs_geom["skip"] += 1
        if r2:
            xy_vs_decl[r2] += 1
        else:
            xy_vs_decl["skip"] += 1
        if r3:
            geom_vs_decl[r3] += 1
        else:
            geom_vs_decl["skip"] += 1

    total_scored = N - xy_vs_geom["skip"]
    print("  pages scored (non-blank): %d / %d" % (total_scored, N))
    print("  xy-cut  vs geometric : same=%d reorder=%d content_diff=%d"
          % (xy_vs_geom["same"], xy_vs_geom["reorder"], xy_vs_geom["content_diff"]))
    print("  xy-cut  vs declared  : same=%d reorder=%d content_diff=%d"
          % (xy_vs_decl["same"], xy_vs_decl["reorder"], xy_vs_decl["content_diff"]))
    print("  geometric vs declared: same=%d reorder=%d content_diff=%d"
          % (geom_vs_decl["same"], geom_vs_decl["reorder"], geom_vs_decl["content_diff"]))
    doc.close()
    return xy_vs_geom, xy_vs_decl, geom_vs_decl


# ---------------------------------------------------------------------------------------------
# NEGATIVE CONTROL 1: self-compare (xy_cut is deterministic; must be identical to itself)
def negctrl_self(path):
    doc = pymupdf.open(path)
    p = doc[0]
    gblocks = geom_blocks(p)
    for j, b in enumerate(gblocks):
        b["idx"] = j
    a = xy_cut(gblocks)
    b = xy_cut(gblocks)  # re-run, fresh list objects but same input
    ok = [x["text"] for x in a] == [x["text"] for x in b]
    print("NEG-CTRL self-compare (xy_cut deterministic on page 0):", ok)
    doc.close()
    return ok


# NEGATIVE CONTROL 2: synthetic two-column page. Left and right columns are CONTIGUOUS
# (touching, zero inter-row gap) and share the SAME y-extent (10-130), so the merged y-projection
# of all 6 blocks has NO internal gap -- the honest geometric signature of two full-height
# parallel columns (a real two-column article page looks exactly like this in projection: the
# columns fill the same vertical band). A naive top-to-bottom y-sort is provably wrong here
# (ties on identical y0 fall back to input order and interleave the columns); XY-cut must instead
# fail the Y-gap test, fall through to the X-projection, find the column gutter, and recover
# true column-major order.
def negctrl_two_column():
    left = [{"bbox": (10, 10 + k * 40, 90, 50 + k * 40), "text": "L%d" % k, "idx": k}
            for k in range(3)]   # x 10-90, y 10-50 / 50-90 / 90-130 (contiguous, no row gap)
    right = [{"bbox": (140, 10 + k * 40, 220, 50 + k * 40), "text": "R%d" % k, "idx": k}
             for k in range(3)]  # x 140-220 (50pt gutter from left's x1=90), same y-bands
    # Interleave input order (simulating a content stream that emits column-by-column oddly)
    blocks = [left[0], right[0], left[1], right[1], left[2], right[2]]
    naive = sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))  # naive y-then-x sort
    naive_order = [b["text"] for b in naive]
    xy_order = [b["text"] for b in xy_cut(blocks)]
    expected = ["L0", "L1", "L2", "R0", "R1", "R2"]  # true column-major reading order
    print("NEG-CTRL two-column synthetic (contiguous full-height columns, 50pt gutter):")
    print("  naive y-sort order :", naive_order, " correct?", naive_order == expected)
    print("  xy-cut order       :", xy_order, " correct?", xy_order == expected)
    return naive_order != expected and xy_order == expected


if __name__ == "__main__":
    print("### NEGATIVE CONTROLS ###")
    negctrl_self(r"C:/Users/Bndit/Downloads/Well-Tagged-PDF-WTPDF-1.0.pdf")
    nc2 = negctrl_two_column()
    print()
    print("### MEASUREMENT ###")
    run(r"C:/Users/Bndit/Downloads/Well-Tagged-PDF-WTPDF-1.0.pdf", 57)
    print()
    run(r"C:/Users/Bndit/Downloads/ISO_32000-2_sponsored_EC3.pdf", 60)
