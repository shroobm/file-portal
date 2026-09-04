"""v2: same xy_cut() core, but margin-band blocks (header/footer -- fully within the top 8% or
bottom 8% of the page height, a common running-header/footer convention) are excluded from the
recursive cut and re-spliced back at the position they held in pymupdf's raw content-stream
order. This tests whether the ONE confound found by inspection (WTPDF page 5: a footer block
geometrically at the bottom but content-stream-first and declared-first) explains most of v1's
55/57 and 59/60 mismatches, or whether the geometry itself is unreliable beyond that.
"""
import pymupdf
from xycut_probe import xy_cut, geom_blocks, declared_frags, stream, compare, NORM

MARGIN_FRAC = 0.08

def xy_cut_v2(blocks, page_height):
    lo, hi = MARGIN_FRAC * page_height, (1 - MARGIN_FRAC) * page_height
    margin = [b for b in blocks if b["bbox"][3] <= lo or b["bbox"][1] >= hi]
    body = [b for b in blocks if b not in margin]
    ordered_body = xy_cut(body) if body else []
    # re-splice margin blocks at their original geometric (content-stream) position
    out = []
    body_iter = iter(ordered_body)
    margin_by_idx = {b["idx"]: b for b in margin}
    consumed_body = set(id(b) for b in ordered_body)
    # simplest faithful splice: walk original geometric order; body blocks in that slot get
    # replaced by the xy_cut-ordered sequence the FIRST time any body block is encountered.
    body_placed = False
    for b in blocks:
        if b["idx"] in margin_by_idx:
            out.append(b)
        else:
            if not body_placed:
                out.extend(ordered_body)
                body_placed = True
    if not body_placed:
        out.extend(ordered_body)
    return out


def run(path, max_pages):
    doc = pymupdf.open(path)
    N = min(doc.page_count, max_pages)
    print("=== %s (first %d pages), v2 margin-excluded xy-cut ===" % (path.split("/")[-1], N))
    tallies = {"same": 0, "reorder": 0, "content_diff": 0, "skip": 0}
    shown = 0
    for i in range(N):
        p = doc[i]
        gblocks = geom_blocks(p)
        if not gblocks:
            tallies["skip"] += 1
            continue
        for j, b in enumerate(gblocks):
            b["idx"] = j
        v2 = xy_cut_v2(gblocks, p.rect.height)
        v2_frags = [b["text"] for b in v2]
        decl = declared_frags(p)
        r = compare(v2_frags, decl, "xy-cut-v2", "declared", i, shown < 5)
        if r:
            tallies[r] += 1
            shown += (r == "reorder")
        else:
            tallies["skip"] += 1
    print("  v2 xy-cut vs declared: same=%d reorder=%d content_diff=%d (skip=%d)"
          % (tallies["same"], tallies["reorder"], tallies["content_diff"], tallies["skip"]))
    doc.close()

run(r"C:/Users/Bndit/Downloads/Well-Tagged-PDF-WTPDF-1.0.pdf", 57)
print()
run(r"C:/Users/Bndit/Downloads/ISO_32000-2_sponsored_EC3.pdf", 60)
