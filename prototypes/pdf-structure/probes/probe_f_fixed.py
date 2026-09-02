"""Re-measure with the null-tuple bug fixed, and settle the Figure discrepancy.

pymupdf's Document.xref_get_key returns ('null','null') for an ABSENT key, which
is truthy. probe_e counted every element as having /Alt. Fixed here.
"""
import re, json, collections
import pymupdf

P = r"C:/Users/Bndit/Downloads/Well-Tagged-PDF-WTPDF-1.0.pdf"
doc = pymupdf.open(P)


def get(x, k):
    v = doc.xref_get_key(x, k)
    if not v or v[0] == "null":
        return None
    return v


def as_xref(v):
    if v and v[0] == "xref":
        return int(v[1].split()[0])
    return None


def kids_of(x):
    k = get(x, "K")
    if not k:
        return []
    kind, val = k
    if kind == "xref":
        return [int(val.split()[0])]
    if kind == "array":
        return [int(m.group(1)) for m in re.finditer(r"(\d+)\s+(\d+)\s+R", val)]
    return []


cat = doc.pdf_catalog()
root_xref = int(get(cat, "StructTreeRoot")[1].split()[0])

seen, elems = set(), []
stack = list(kids_of(root_xref))
while stack:
    x = stack.pop()
    if x in seen:
        continue
    seen.add(x)
    stack.extend(kids_of(x))
    if (get(x, "Type") or ("", ""))[1] == "/StructElem" or get(x, "S"):
        elems.append(x)

print("=== FIXED XREF WALK ===")
print("objects reached:", len(seen), "| StructElem (has /S or Type=/StructElem):", len(elems))

feat = collections.Counter()
Sct = collections.Counter()
for x in elems:
    s = get(x, "S")
    Sct[s[1].lstrip("/") if s else "<no S>"] += 1
    for k in ("Alt", "ActualText", "Lang", "E", "A", "C", "Pg", "ID", "T", "Ref"):
        if get(x, k):
            feat[k] += 1
print("StructElem feature counts (numerator / denominator = %d StructElem in this file):" % len(elems))
for k, v in feat.most_common():
    print("   /%-11s %5d  (%.1f%%)" % (k, v, 100.0 * v / len(elems)))
print()
print("S-type tally:", len(Sct), "distinct")
for k, v in Sct.most_common(40):
    print("   %-14s %5d" % (k, v))

# ---- attribute objects: what do they actually contain? ----
print()
print("=== /A ATTRIBUTE OBJECT CONTENTS (by owner) ===")
owners = collections.Counter()
attrkeys = collections.Counter()
samples = {}
for x in elems:
    a = get(x, "A")
    if not a:
        continue
    ax = as_xref(a)
    objs = []
    if ax:
        objs = [ax]
    elif a[0] == "array":
        objs = [int(m.group(1)) for m in re.finditer(r"(\d+)\s+(\d+)\s+R", a[1])]
    for o in objs:
        ks = doc.xref_get_keys(o)
        own = doc.xref_get_key(o, "O")
        owners[own[1] if own else "?"] += 1
        for k in ks:
            attrkeys[k] += 1
        src = doc.xref_object(o)
        key = (own[1] if own else "?")
        if key not in samples:
            samples[key] = (x, get(x, "S"), src[:260])
print("attribute-object /O owners:", owners.most_common())
print("attribute keys seen:", attrkeys.most_common())
for k, v in samples.items():
    print("  owner %s  on S=%s ->  %s" % (k, v[1], v[2]))

# ---- BBox: is any declared? ----
print()
print("=== DECLARED /BBox (Layout attribute) SEARCH ===")
nb = 0
for x in elems:
    a = get(x, "A")
    if not a:
        continue
    ax = as_xref(a)
    cands = [ax] if ax else ([int(m.group(1)) for m in re.finditer(r"(\d+)\s+(\d+)\s+R", a[1])] if a[0] == "array" else [])
    for o in cands:
        if "BBox" in doc.xref_get_keys(o):
            nb += 1
            if nb <= 3:
                print("  BBox on S=%s ->" % (get(x, "S"),), doc.xref_object(o)[:220])
print("StructElem with a declared /BBox layout attribute: %d / %d" % (nb, len(elems)))

# ---- Figure discrepancy: xref says N, stext says M ----
print()
print("=== FIGURE COUNT: xref vs stext ===")
figs = [x for x in elems if (get(x, "S") or ("", ""))[1] == "/Figure"]
print("xref /Figure StructElem:", len(figs))
for f in figs:
    pg = as_xref(get(f, "Pg"))
    pno = None
    for i in range(doc.page_count):
        if doc[i].xref == pg:
            pno = i
            break
    print("   xref %d  page_xref=%s -> page_index=%s  Alt=%r  K=%s"
          % (f, pg, pno, (get(f, "Alt") or ("", ""))[1], get(f, "K")))

FL = pymupdf.TEXTFLAGS_DICT | pymupdf.TEXT_COLLECT_STRUCTURE
print("TEXTFLAGS_DICT =", pymupdf.TEXTFLAGS_DICT,
      "| PRESERVE_IMAGES set?", bool(pymupdf.TEXTFLAGS_DICT & pymupdf.TEXT_PRESERVE_IMAGES))


def count_std(blocks, ct, want):
    for b in blocks:
        if b.get("type") == 2:
            if b.get("raw") == want:
                ct[0] += 1
            count_std(b.get("blocks", []), ct, want)
        elif b.get("type") == 1:
            ct[1] += 1


for flagname, fl in (("TEXTFLAGS_DICT|STRUCT", FL),
                     ("|IMAGES", FL | pymupdf.TEXT_PRESERVE_IMAGES)):
    ct = [0, 0]
    for i in range(doc.page_count):
        count_std(doc[i].get_text("dict", flags=fl)["blocks"], ct, "Figure")
    print("  stext %-24s Figure structs=%d  image blocks=%d" % (flagname, ct[0], ct[1]))
