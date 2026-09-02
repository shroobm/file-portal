"""Artifact separation, declared vs heuristic.

fidelity_audit.prepare_witness() strips a line when it appears on >= max(2, 40% of pages).
A tagged PDF instead DECLARES running heads/folios as artifacts: their content sits
OUTSIDE any StructElem. Measure agreement between the two on real tagged specimens.
"""
import re, sys, collections
sys.path.insert(0, r"C:/Users/Bndit/Projects/file-portal/windows-converter")
import pymupdf

FL = pymupdf.TEXTFLAGS_DICT | pymupdf.TEXT_COLLECT_STRUCTURE
NORM = lambda s: re.sub(r"\s+", " ", s).strip()


def split_page(page):
    """-> (tagged_fragments, untagged_fragments). Untagged == outside every StructElem."""
    tagged, untagged = [], []

    def w(bl, inside):
        for b in bl:
            if b.get("type") == 2:
                w(b.get("blocks", []), True)
            elif b.get("type") == 0:
                s = NORM("".join(sp["text"] for l in b.get("lines", []) for sp in l["spans"]))
                if s:
                    (tagged if inside else untagged).append(s)
    w(page.get_text("dict", flags=FL)["blocks"], False)
    return tagged, untagged


def heuristic_repeated(pages_norm):
    """fidelity_audit.prepare_witness's step-5 rule, reimplemented on normalized lines."""
    n = len(pages_norm)
    ct = collections.Counter()
    for p in pages_norm:
        for ln in set(p):
            ct[ln] += 1
    thr = max(2, int(round(0.4 * n)))
    return {ln for ln, c in ct.items() if n >= 3 and c >= thr}


for P in (r"C:/Users/Bndit/Downloads/Well-Tagged-PDF-WTPDF-1.0.pdf",
          r"C:/Users/Bndit/Downloads/Tagged-PDF-Best-Practice-Guide.pdf",
          r"C:/Users/Bndit/Downloads/ISO-14289-2-2024-sponsored.pdf"):
    doc = pymupdf.open(P)
    N = doc.page_count
    all_tagged, all_untagged, per_page = [], [], []
    for i in range(N):
        t, u = split_page(doc[i])
        all_tagged += t
        all_untagged += u
        per_page.append(t + u)
    rep = heuristic_repeated(per_page)
    U = set(all_untagged)
    print("=== %s (%d pages) ===" % (P.split("/")[-1][:52], N))
    print("  fragments INSIDE the structure tree : %d" % len(all_tagged))
    print("  fragments OUTSIDE it (declared artifacts): %d  (%d distinct)"
          % (len(all_untagged), len(U)))
    print("  sample untagged:", [x[:50] for x in list(U)[:4]])
    print("  heuristic 40%%-repeat set: %d distinct lines" % len(rep))
    # Does the heuristic catch what the tree declares, and vice versa?
    caught = sum(1 for f in all_untagged if f in rep)
    print("  artifact fragments the heuristic ALSO strips: %d / %d (%.0f%%)"
          % (caught, len(all_untagged), 100.0 * caught / max(1, len(all_untagged))))
    over = [r for r in rep if r not in U]
    print("  lines the heuristic strips that are REAL tagged content: %d" % len(over))
    for o in over[:4]:
        print("      OVER-STRIPPED:", o[:70])
    doc.close()
    print()
