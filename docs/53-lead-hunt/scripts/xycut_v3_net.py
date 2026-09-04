"""Net-payoff test: on the pages where Marker's OWN baseline (raw content-stream / pdftext
order) already DISAGREES with the declared structure-tree order, does the v2 margin-excluded
XY-cut FIX any of them (agree with declared where geometric did not), or does it only ADD new
mismatches of its own? This is the number that actually answers spec #4's question -- not the
aggregate same/reorder count, which is dominated by pages Marker already gets right for free.
"""
import pymupdf
from xycut_probe import xy_cut, geom_blocks, declared_frags, compare
from xycut_v2 import xy_cut_v2

def run(path, max_pages):
    doc = pymupdf.open(path)
    N = min(doc.page_count, max_pages)
    geom_wrong_pages = []
    xy_fixes = []
    xy_breaks = []  # pages geometric got RIGHT that v2 gets WRONG
    for i in range(N):
        p = doc[i]
        gblocks = geom_blocks(p)
        if not gblocks:
            continue
        for j, b in enumerate(gblocks):
            b["idx"] = j
        decl = declared_frags(p)
        geom_frags = [b["text"] for b in gblocks]
        r_geom = compare(geom_frags, decl, "geom", "decl", i, False)
        v2 = xy_cut_v2(list(gblocks), p.rect.height)
        v2_frags = [b["text"] for b in v2]
        r_v2 = compare(v2_frags, decl, "v2", "decl", i, False)
        if r_geom == "reorder":
            geom_wrong_pages.append(i)
            if r_v2 == "same":
                xy_fixes.append(i)
        elif r_geom == "same" and r_v2 == "reorder":
            xy_breaks.append(i)
    print("=== %s ===" % path.split("/")[-1])
    print("  pages where Marker's geometric order != declared: %d -> %s" % (len(geom_wrong_pages), geom_wrong_pages))
    print("  of those, v2 XY-cut FIXES (matches declared):      %d -> %s" % (len(xy_fixes), xy_fixes))
    print("  pages geometric got RIGHT that v2 XY-cut BREAKS:   %d -> %s" % (len(xy_breaks), xy_breaks))
    doc.close()

run(r"C:/Users/Bndit/Downloads/Well-Tagged-PDF-WTPDF-1.0.pdf", 57)
run(r"C:/Users/Bndit/Downloads/ISO_32000-2_sponsored_EC3.pdf", 60)
