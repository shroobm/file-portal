"""What the stext STRUCT block does NOT carry, and can xref walking supply it?

1. Dump one raw STRUCT block dict verbatim (all keys).
2. Walk /StructTreeRoot by xref: count StructElem, harvest /Alt /ActualText
   /Lang /A (attributes) /Pg, and find the Figure.
3. Negative control: a PDF with no StructTreeRoot.
"""
import sys, json, re, collections
import pymupdf

P = r"C:/Users/Bndit/Downloads/Well-Tagged-PDF-WTPDF-1.0.pdf"
FLAGS = pymupdf.TEXTFLAGS_DICT | pymupdf.TEXT_COLLECT_STRUCTURE
doc = pymupdf.open(P)

# ---- 1. raw struct block dict, keys only (text elided) ----
d = doc[10].get_text("dict", flags=FLAGS)


def find_struct(blocks):
    for b in blocks:
        if b.get("type") == 2:
            return b
        for sub in b.get("blocks", []) or []:
            r = find_struct([sub])
            if r:
                return r
    return None


sb = find_struct(d["blocks"])
shallow = {k: (("<%d children>" % len(v)) if k == "blocks" else v)
           for k, v in sb.items()}
print("=== 1. RAW STRUCT BLOCK DICT (top level) ===")
print(json.dumps(shallow, indent=2, default=str))
print("ALL KEYS PRESENT:", sorted(sb.keys()))
print("Alt present?", "alt" in sb or "Alt" in sb)
print("ActualText present?", any(k.lower() == "actualtext" for k in sb))
print("lang present?", any(k.lower() == "lang" for k in sb))
print("page/Pg present?", any(k.lower() in ("pg", "page") for k in sb))

# ---- 2. xref walk of StructTreeRoot ----
print()
print("=== 2. XREF WALK OF /StructTreeRoot ===")
cat = doc.pdf_catalog()
str_ref = doc.xref_get_key(cat, "StructTreeRoot")
print("catalog /StructTreeRoot ->", str_ref)
root_xref = int(str_ref[1].split()[0])
print("root keys:", doc.xref_get_keys(root_xref))
print("root RoleMap:", str(doc.xref_get_key(root_xref, "RoleMap"))[:300])
print("root ParentTree:", doc.xref_get_key(root_xref, "ParentTree"))


def as_xref(v):
    if v and v[0] == "xref":
        return int(v[1].split()[0])
    return None


def kids_of(x):
    """Return list of child StructElem xrefs (skip MCR ints / dicts)."""
    k = doc.xref_get_key(x, "K")
    out = []
    if not k:
        return out
    kind, val = k
    if kind == "xref":
        out.append(int(val.split()[0]))
    elif kind == "array":
        for m in re.finditer(r"(\d+)\s+(\d+)\s+R", val):
            out.append(int(m.group(1)))
    return out


seen = set()
tally = collections.Counter()
alt_ct = 0
actual_ct = 0
lang_ct = 0
attr_ct = 0
pg_ct = 0
figures = []
stack = kids_of(root_xref)
while stack:
    x = stack.pop()
    if x in seen:
        continue
    seen.add(x)
    typ = doc.xref_get_key(x, "Type")
    s = doc.xref_get_key(x, "S")
    if s:
        tally[s[1].lstrip("/")] += 1
    if doc.xref_get_key(x, "Alt"):
        alt_ct += 1
    if doc.xref_get_key(x, "ActualText"):
        actual_ct += 1
    if doc.xref_get_key(x, "Lang"):
        lang_ct += 1
    if doc.xref_get_key(x, "A"):
        attr_ct += 1
    if doc.xref_get_key(x, "Pg"):
        pg_ct += 1
    if s and s[1].lstrip("/") == "Figure":
        figures.append(x)
    stack.extend(kids_of(x))

print("StructElem objects reached by xref walk:", len(seen))
print("with /Alt:", alt_ct, "| /ActualText:", actual_ct, "| /Lang:", lang_ct,
      "| /A attributes:", attr_ct, "| /Pg:", pg_ct)
print("top S types:", tally.most_common(12))
for f in figures:
    print("FIGURE xref", f, "keys", doc.xref_get_keys(f))
    for k in ("Alt", "ActualText", "Pg", "A", "K"):
        print("   ", k, "=", str(doc.xref_get_key(f, k))[:300])

# a table cell with attributes
print()
print("=== sample /A attribute object ===")
for x in list(seen)[:4000]:
    a = doc.xref_get_key(x, "A")
    if a:
        print("elem xref", x, "S=", doc.xref_get_key(x, "S"), "A=", str(a)[:300])
        ax = as_xref(a)
        if ax:
            print("   A obj:", doc.xref_object(ax)[:400])
        break
else:
    print("NO /A attribute object found on any StructElem")

# TH scope/headers
print()
print("=== TH elements: Scope / Headers / ColSpan ===")
n_th = 0
for x in seen:
    s = doc.xref_get_key(x, "S")
    if s and s[1].lstrip("/") in ("TH", "TD"):
        n_th += 1
        if n_th <= 3:
            print(" ", s[1], "keys:", doc.xref_get_keys(x),
                  "| A=", str(doc.xref_get_key(x, "A"))[:200],
                  "| ID=", doc.xref_get_key(x, "ID"))
print("total TH/TD reached:", n_th)
