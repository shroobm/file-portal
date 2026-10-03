"""WHAT THIS FILE DOES: a one-off inspection script (run directly, no arguments). On page 10 of the WTPDF
sample (path hard-coded) it prints the catalog and page keys, and compares what get_text("dict") returns
with and without structure collection (block types and key names), then the rawdict keys and the length and
head of xml / xhtml output. Read-only; stdout only; needs pymupdf; no callers.
"""
import pymupdf, json, collections
P = r"C:/Users/Bndit/Downloads/Well-Tagged-PDF-WTPDF-1.0.pdf"
d = pymupdf.open(P)
print("pages", d.page_count, "is_pdf", d.is_pdf)
print("markinfo:", d.markinfo)
cat = d.pdf_catalog()
print("catalog xref", cat)
print("catalog keys:", d.xref_get_keys(cat))
print("StructTreeRoot:", d.xref_get_key(cat, "StructTreeRoot"))
print("MarkInfo:", d.xref_get_key(cat, "MarkInfo"))
print()
pg = d[10]
print("page keys:", d.xref_get_keys(pg.xref))
print("StructParents:", d.xref_get_key(pg.xref, "StructParents"))
print()
# compare the dict output with the default flags and with structure collection added
base = pymupdf.TEXTFLAGS_DICT
for label, fl in (("default", base), ("+COLLECT_STRUCTURE", base | pymupdf.TEXT_COLLECT_STRUCTURE)):
    t = pg.get_text("dict", flags=fl)
    btypes = collections.Counter(b.get("type") for b in t["blocks"])
    keys = set()
    for b in t["blocks"]:
        keys |= set(b.keys())
        for l in b.get("lines", []):
            keys |= {"line." + k for k in l.keys()}
            for s in l.get("spans", []):
                keys |= {"span." + k for k in s.keys()}
    print(label, "blocks", len(t["blocks"]), "types", dict(btypes))
    print("   keys:", sorted(keys))
t = pg.get_text("rawdict", flags=base | pymupdf.TEXT_COLLECT_STRUCTURE)
ks = set()
for b in t["blocks"]:
    ks |= set(b.keys())
print("rawdict block keys:", sorted(ks))
for mode in ("xml", "xhtml"):
    s = pg.get_text(mode, flags=base | pymupdf.TEXT_COLLECT_STRUCTURE)
    print(mode, "len", len(s), "| head:", s[:200].replace(chr(10), " "))
