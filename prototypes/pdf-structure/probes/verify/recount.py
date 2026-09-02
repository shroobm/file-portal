"""Verifier: recount survey.tsv, diff it against the live Downloads listing, read WTPDF's
RoleMap, and count the marker package's structure-tree references. Read-only."""
import sys, io, os, glob, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
OUT = r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/d6f7a30f-66e5-40d2-a905-b2dd64ee7f44/scratchpad/pdfua/out/"

rows = [l.rstrip("\n").split("\t") for l in open(OUT + "survey.tsv", encoding="utf-8", errors="replace")]
hdr, data = rows[0], rows[1:]
print("survey.tsv data rows:", len(data))
yes = [r for r in data if r[3] == "YES"]
no = [r for r in data if r[3] == "-"]
print("STRoot=YES rows:", len(yes), "| STRoot=- rows:", len(no))
print("YES with elems<=17 (hollow):", [(r[0][:40], r[4]) for r in yes if int(r[4]) <= 17])
# distinct by (pages, elems) signature to see if the author deduplicated copies
sig = collections.Counter((r[1], r[4]) for r in yes)
dups = {k: v for k, v in sig.items() if v > 1}
print("YES rows sharing identical (pages, elems) signature (probable duplicate copies):", dups)
print("YES distinct-by-signature:", len(sig))
marked_false_yes = [(r[0][:40], r[2], r[4]) for r in yes if r[2] == "False"]
print("YES rows with Marked=False:", marked_false_yes)

live = sorted(os.path.basename(p) for p in glob.glob(r"C:/Users/Bndit/Downloads/*.pdf"))
print("live Downloads *.pdf count:", len(live))
surv = [r[0] for r in data]
# survey names are truncated to 58 chars
live58 = [n[:58] for n in live]
missing_now = [s for s in surv if s not in live58]
new_now = [n for n in live58 if n not in surv]
print("in survey but not live now:", missing_now)
print("live now but not in survey:", new_now)

import pymupdf
doc = pymupdf.open(r"C:/Users/Bndit/Downloads/Well-Tagged-PDF-WTPDF-1.0.pdf")
cat = doc.pdf_catalog()
root = int(doc.xref_get_key(cat, "StructTreeRoot")[1].split()[0])
rm = doc.xref_get_key(root, "RoleMap")
print("WTPDF RoleMap:", rm)
print("WTPDF MarkInfo:", doc.xref_get_key(cat, "MarkInfo"))
# std vocabulary size claim: count FZ_STRUCTURE-like names exposed by pymupdf
names = [n for n in dir(pymupdf) if n.startswith("STRUCTURE") or "STRUCT" in n]
print("pymupdf names containing STRUCT:", len(names), names[:12])

# marker package grep (design.md 0)
mk = r"C:/Users/Bndit/ml/marker-env/Lib/site-packages/marker"
hits = []
for dp, dn, fn in os.walk(mk):
    for f in fn:
        if f.endswith(".py"):
            p = os.path.join(dp, f)
            try:
                t = open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            if re.search(r"StructTreeRoot|StructElem|COLLECT_STRUCTURE", t):
                hits.append(os.path.relpath(p, mk))
print("marker .py files mentioning StructTreeRoot|StructElem|COLLECT_STRUCTURE:", len(hits), hits)
try:
    from marker.schema import BlockTypes
    print("marker BlockTypes count:", len(list(BlockTypes)))
except Exception as e:
    print("BlockTypes import failed:", e)
