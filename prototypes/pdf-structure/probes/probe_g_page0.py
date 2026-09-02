"""Page 0 of WTPDF: two /Figure StructElem with /Alt are declared there.
Does the stext structure view show them? Does get_images? Does plain text?
This is the SYM-053 shape: declared asset + declared words vs. what extraction sees.
"""
import pymupdf, collections

P = r"C:/Users/Bndit/Downloads/Well-Tagged-PDF-WTPDF-1.0.pdf"
doc = pymupdf.open(P)
FL = pymupdf.TEXTFLAGS_DICT | pymupdf.TEXT_COLLECT_STRUCTURE
pg = doc[0]

print("page 0 xref:", pg.xref, "StructParents:", doc.xref_get_key(pg.xref, "StructParents"))
print("get_images():", pg.get_images(full=True))
print("get_image_info() count:", len(pg.get_image_info()))
for ii in pg.get_image_info():
    print("   bbox", tuple(round(v, 1) for v in ii["bbox"]), "xref", ii.get("xref"))
print()
d = pg.get_text("dict", flags=FL)


def dump(blocks, dep=0):
    for b in blocks:
        t = b.get("type")
        bb = tuple(round(v, 1) for v in b["bbox"]) if b.get("bbox") else None
        if t == 2:
            print("  " * dep + "<%s> std=%s bbox=%s" % (b.get("raw"), b.get("std"), bb))
            dump(b.get("blocks", []), dep + 1)
        elif t == 0:
            txt = "".join(s["text"] for l in b.get("lines", []) for s in l["spans"])
            print("  " * dep + "[TEXT] %s %r" % (bb, txt[:70]))
        elif t == 1:
            print("  " * dep + "[IMAGE] %s" % (bb,))
        else:
            print("  " * dep + "[type%s]" % t)


dump(d["blocks"])
print()
print("--- plain get_text() page 0 (the CURRENT fidelity witness) ---")
print(repr(pg.get_text()[:400]))
print()
print("--- the two Alt strings the structure tree declares for page 0 ---")
print("   'Creative Commons'   'PDF Association logo'")
print("--- are those strings present in the witness text? ---")
w = pg.get_text()
for s in ("Creative Commons", "PDF Association logo"):
    print("   %-24r in witness: %s" % (s, s in w))

# whole-document: every Alt / ActualText string vs the whole witness text
print()
print("=== WHOLE-DOC: declared Alt/ActualText vs pymupdf witness text ===")
import re


def get(x, k):
    v = doc.xref_get_key(x, k)
    return None if (not v or v[0] == "null") else v


def kids_of(x):
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
seen, stack = set(), list(kids_of(root))
alts, acts = [], []
while stack:
    x = stack.pop()
    if x in seen:
        continue
    seen.add(x)
    stack.extend(kids_of(x))
    a = get(x, "Alt")
    if a:
        alts.append((x, a[1]))
    a2 = get(x, "ActualText")
    if a2:
        acts.append((x, a2[1]))
witness = "".join(doc[i].get_text() for i in range(doc.page_count))
miss_alt = [s for _, s in alts if s.strip() and s.strip() not in witness]
miss_act = [s for _, s in acts if s.strip() and s.strip() not in witness]
print("declared /Alt strings: %d ; ABSENT from witness text: %d" % (len(alts), len(miss_alt)))
for s in miss_alt[:10]:
    print("    MISSING:", repr(s[:90]))
print("declared /ActualText strings: %d ; ABSENT from witness text: %d" % (len(acts), len(miss_act)))
for s in miss_act[:10]:
    print("    MISSING:", repr(s[:90]))
