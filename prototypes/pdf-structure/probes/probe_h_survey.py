"""Survey: which PDFs on this machine actually carry a structure tree, and how rich.

Includes NEGATIVE CONTROLS (scanned / untagged corpus books) so the detector is
watched failing, per the brief's negative-control requirement.
"""
import glob, os, re, sys, collections, traceback
import pymupdf

FL = pymupdf.TEXTFLAGS_DICT | pymupdf.TEXT_COLLECT_STRUCTURE


def probe(path, max_pages=None):
    r = {"file": os.path.basename(path)}
    try:
        d = pymupdf.open(path)
    except Exception as e:
        r["error"] = repr(e)[:80]
        return r
    r["pages"] = d.page_count
    try:
        r["markinfo"] = d.markinfo.get("Marked") if d.markinfo else None
    except Exception:
        r["markinfo"] = "ERR"
    cat = d.pdf_catalog()
    st = d.xref_get_key(cat, "StructTreeRoot")
    r["StructTreeRoot"] = None if (not st or st[0] == "null") else st[1]
    if not r["StructTreeRoot"]:
        r["elems"] = 0
        r["stext_structs"] = 0
        d.close()
        return r

    def get(x, k):
        v = d.xref_get_key(x, k)
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

    root = int(r["StructTreeRoot"].split()[0])
    seen, stack = set(), list(kids(root))
    S = collections.Counter()
    feats = collections.Counter()
    n = 0
    while stack and len(seen) < 400000:
        x = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        stack.extend(kids(x))
        s = get(x, "S")
        if s:
            n += 1
            S[s[1].lstrip("/")] += 1
            for k in ("Alt", "ActualText", "Lang", "Pg", "A", "ID"):
                if get(x, k):
                    feats[k] += 1
    r["elems"] = n
    r["types"] = len(S)
    r["top"] = ",".join("%s:%d" % kv for kv in S.most_common(6))
    r["Alt"] = feats["Alt"]
    r["ActualText"] = feats["ActualText"]
    r["Pg"] = feats["Pg"]
    r["A"] = feats["A"]
    r["Table"] = S.get("Table", 0)
    r["Figure"] = S.get("Figure", 0)
    r["H"] = sum(v for k, v in S.items() if re.fullmatch(r"H[1-6]?", k))
    # stext struct count on a sample of pages
    ns = 0
    pages = range(min(d.page_count, max_pages or d.page_count))

    def cnt(bl):
        c = 0
        for b in bl:
            if b.get("type") == 2:
                c += 1 + cnt(b.get("blocks", []))
        return c

    for i in pages:
        try:
            ns += cnt(d[i].get_text("dict", flags=FL)["blocks"])
        except Exception:
            pass
    r["stext_structs"] = ns
    r["stext_pages_scanned"] = len(list(pages))
    d.close()
    return r


CANDIDATES = sys.argv[1:] or sorted(glob.glob(r"C:/Users/Bndit/Downloads/*.pdf"))
hdr = ("file", "pages", "Marked", "STRoot", "elems", "types", "H", "Table",
       "Figure", "Alt", "ActualText", "Pg", "A", "stext")
print("\t".join(hdr))
for p in CANDIDATES:
    r = probe(p, max_pages=25)
    if "error" in r:
        print("%s\tERROR %s" % (r["file"][:60], r["error"]))
        continue
    print("\t".join(str(x) for x in (
        r["file"][:58], r["pages"], r.get("markinfo"),
        "YES" if r["StructTreeRoot"] else "-",
        r.get("elems", 0), r.get("types", 0), r.get("H", 0), r.get("Table", 0),
        r.get("Figure", 0), r.get("Alt", 0), r.get("ActualText", 0),
        r.get("Pg", 0), r.get("A", 0), r.get("stext_structs", 0))))
