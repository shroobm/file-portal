"""CROSS-CHECK (second, differently-shaped method).

Method A: pymupdf stext with TEXT_COLLECT_STRUCTURE -> a tree whose element bboxes
          are DERIVED (union of the glyph/image boxes MuPDF places under the element).
Method B: raw xref walk of /StructTreeRoot -> the element's own /A /Layout /BBox,
          which is AUTHOR-DECLARED, and its /Pg page reference.

If A and B agree on the same element, the stext tree really is the structure tree and
not a geometric re-guess. Run on the WTPDF Figure whose Alt is ' cube root of x '.

NEGATIVE CONTROL: the same code on a PDF with no structure tree must return nothing,
and the same comparison on a DELIBERATELY WRONG element must disagree.
"""
import re, sys
import pymupdf

P = r"C:/Users/Bndit/Downloads/Well-Tagged-PDF-WTPDF-1.0.pdf"
doc = pymupdf.open(P)
FL = pymupdf.TEXTFLAGS_DICT | pymupdf.TEXT_COLLECT_STRUCTURE


def get(x, k):
    v = doc.xref_get_key(x, k)
    return None if (not v or v[0] == "null") else v


def kids(x):
    k = get(x, "K")
    if not k:
        return []
    if k[0] == "xref":
        return [int(k[1].split()[0])]
    if k[0] == "array":
        return [int(m.group(1)) for m in re.finditer(r"(\d+)\s+(\d+)\s+R", k[1])]
    return []


cat = doc.pdf_catalog()
root = int(get(cat, "StructTreeRoot")[1].split()[0])
seen, stack, elems = set(), list(kids(root)), []
while stack:
    x = stack.pop()
    if x in seen:
        continue
    seen.add(x)
    stack.extend(kids(x))
    if get(x, "S"):
        elems.append(x)

# --- Method B: the declared BBox on the /Figure that is not on the cover ---
target = None
for x in elems:
    if (get(x, "S") or ("", ""))[1] != "/Figure":
        continue
    a = get(x, "A")
    ax = int(a[1].split()[0]) if a and a[0] == "xref" else None
    if ax and "BBox" in doc.xref_get_keys(ax):
        bb = doc.xref_get_key(ax, "BBox")[1]
        nums = [float(v) for v in re.findall(r"-?[\d.]+", bb)]
        if max(abs(n) for n in nums) < 10000:  # skip the degenerate placeholder
            pgx = int(get(x, "Pg")[1].split()[0])
            pno = next(i for i in range(doc.page_count) if doc[i].xref == pgx)
            target = (x, tuple(nums), pno, (get(x, "Alt") or ("", ""))[1])
            break

print("=== METHOD B (raw xref, author-declared) ===")
print("Figure StructElem xref=%d  page_index=%d  Alt=%r" % (target[0], target[2], target[3]))
print("declared /A /Layout /BBox (PDF user space, y-up):", target[1])
pg = doc[target[2]]
print("page rect:", tuple(round(v, 3) for v in pg.rect))

# PDF BBox is y-up from the page bottom; pymupdf stext bbox is y-down from the top.
H = pg.rect.height
dx0, dy0, dx1, dy1 = target[1]
declared_topdown = (dx0, H - dy1, dx1, H - dy0)
print("declared BBox converted to pymupdf top-down coords:",
      tuple(round(v, 2) for v in declared_topdown))

# --- Method A: stext structure tree on the same page ---
print()
print("=== METHOD A (pymupdf stext TEXT_COLLECT_STRUCTURE, derived) ===")
found = []


def walk(bl, path=()):
    for b in bl:
        if b.get("type") == 2:
            p = path + (b.get("raw"),)
            if b.get("raw") == "Figure":
                found.append((p, tuple(b["bbox"])))
            walk(b.get("blocks", []), p)


walk(pg.get_text("dict", flags=FL)["blocks"])
print("Figure structs stext reports on page %d: %d" % (target[2], len(found)))
for p, bb in found:
    print("   path=%s  derived bbox=%s" % ("/".join(p), tuple(round(v, 2) for v in bb)))

if found:
    a = found[0][1]
    b = declared_topdown
    dev = max(abs(a[i] - b[i]) for i in range(4))
    print()
    print("MAX PER-EDGE DEVIATION (derived vs declared): %.3f pt" % dev)
    print("AGREE within 2 pt?", dev <= 2.0)
else:
    print()
    print("METHOD A RETURNED NOTHING for this element -> A and B DISAGREE (A is lossy)")

# --- NEGATIVE CONTROL 1: deliberately wrong element ---
print()
print("=== NEGATIVE CONTROL 1: compare declared Figure BBox to a DIFFERENT element ===")
other = None


def walk2(bl):
    global other
    for b in bl:
        if b.get("type") == 2 and b.get("raw") == "P" and other is None:
            other = tuple(b["bbox"])
        if b.get("type") == 2:
            walk2(b.get("blocks", []))


walk2(pg.get_text("dict", flags=FL)["blocks"])
if other:
    dev2 = max(abs(other[i] - declared_topdown[i]) for i in range(4))
    print("first <P> on page bbox:", tuple(round(v, 2) for v in other))
    print("deviation vs declared Figure BBox: %.1f pt -> agree within 2pt? %s" % (dev2, dev2 <= 2.0))
    print("(a control that FAILED to disagree would mean the comparison is vacuous)")

# --- NEGATIVE CONTROL 2: an untagged PDF ---
print()
print("=== NEGATIVE CONTROL 2: untagged PDF must yield no structure ===")
NEG = r"C:/Users/Bndit/Downloads/Ashby - An Introduction to Cybernetics (1956).pdf"
nd = pymupdf.open(NEG)
ncat = nd.pdf_catalog()
nst = nd.xref_get_key(ncat, "StructTreeRoot")
print("Ashby /StructTreeRoot:", nst)
cnt = 0


def cnt3(bl):
    global cnt
    for b in bl:
        if b.get("type") == 2:
            cnt += 1
            cnt3(b.get("blocks", []))


for i in range(min(20, nd.page_count)):
    cnt3(nd[i].get_text("dict", flags=FL)["blocks"])
print("stext STRUCT blocks over Ashby pages 0-19:", cnt, "(expected 0)")
print("Ashby page 0 text chars (proves the file IS readable, control is not vacuous):",
      len(nd[0].get_text()))
