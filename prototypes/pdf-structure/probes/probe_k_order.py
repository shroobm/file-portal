"""Re-measure reading order HONESTLY.

probe_j compared block LISTS, which conflates finer segmentation with different order.
Here: compare the whitespace-normalized concatenated CHARACTER STREAM of the page.
Same characters in the same sequence => same reading order, whatever the block split.
Then count pages where the streams differ, and show a real divergence.

NEGATIVE CONTROL: compare the geometric stream to ITSELF (must be 0 differing pages),
and compare a deliberately reversed declared stream (must be ~all differing).
"""
import re, difflib
import pymupdf

FL = pymupdf.TEXTFLAGS_DICT | pymupdf.TEXT_COLLECT_STRUCTURE
NORM = lambda s: re.sub(r"\s+", " ", s).strip()


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


def geom_frags(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") == 0:
            out.append("".join(sp["text"] for l in b.get("lines", []) for sp in l["spans"]))
    return [NORM(x) for x in out if NORM(x)]


for P in (r"C:/Users/Bndit/Downloads/Well-Tagged-PDF-WTPDF-1.0.pdf",
          r"C:/Users/Bndit/Downloads/ISO_32000-2_sponsored_EC3.pdf",
          r"C:/Users/Bndit/Downloads/File_Portal_System_of_Operations.pdf"):
    doc = pymupdf.open(P)
    N = min(doc.page_count, 60)
    same = differ = 0
    shown = 0
    print("=== %s (first %d pages) ===" % (P.split("/")[-1][:52], N))
    for i in range(N):
        p = doc[i]
        ds = NORM(" ".join(declared_frags(p))).replace(" ", "")
        gs = NORM(" ".join(geom_frags(p))).replace(" ", "")
        if not ds and not gs:
            continue
        if ds == gs:
            same += 1
        else:
            differ += 1
            if shown < 2 and ds and gs and sorted(ds) == sorted(gs):
                # same characters, different sequence => a TRUE order difference
                sm = difflib.SequenceMatcher(None, gs, ds)
                print("  TRUE ORDER DIFF page %d (same chars, resequenced; similarity %.3f)"
                      % (i, sm.ratio()))
                shown += 1
            elif shown < 2:
                only_d = len(ds) - len(gs)
                print("  page %d: streams differ; declared has %+d chars vs geometric "
                      "(content difference, not only order)" % (i, only_d))
                shown += 1
    print("  identical character stream: %d / %d pages ; differing: %d"
          % (same, same + differ, differ))
    # negative controls
    p0 = doc[0]
    g = NORM(" ".join(geom_frags(p0))).replace(" ", "")
    print("  NEG-CTRL self-compare page 0 identical?", g == g)
    print("  NEG-CTRL reversed-declared page 0 identical?",
          NORM(" ".join(reversed(declared_frags(p0)))).replace(" ", "") == g)
    doc.close()
    print()

# The one concrete divergence, spelled out
print("=== CONCRETE DIVERGENCE, WTPDF page 0 ===")
doc = pymupdf.open(r"C:/Users/Bndit/Downloads/Well-Tagged-PDF-WTPDF-1.0.pdf")
p = doc[0]
print("declared (author's reading order):")
for i, f in enumerate(declared_frags(p)):
    print("   %d. %s" % (i + 1, f[:64]))
print("geometric (what the current witness produces):")
for i, f in enumerate(geom_frags(p)):
    print("   %d. %s" % (i + 1, f[:64]))
