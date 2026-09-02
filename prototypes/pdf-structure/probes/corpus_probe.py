"""Re-measure: of the operator's REAL converted corpus (anchor bundles), how many source
PDFs carry a structure tree, and how dense is it? Read-only. No GPU."""
import json, re, sys
from pathlib import Path
import pymupdf

ANCHOR = Path(r"C:\Users\Bndit\ml\library\anchor")
SEARCH = [Path(r"C:\Users\Bndit\Downloads"), Path(r"C:\Users\Bndit\ml\library"),
          Path(r"C:\Users\Bndit\Documents")]

# distinct works, keyed by source filename from the manifest
works = {}
for d in sorted(ANCHOR.iterdir()):
    m = d / "manifest.json"
    if not m.is_file():
        continue
    j = json.loads(m.read_text(encoding="utf-8"))
    src = j.get("source")
    if src not in works:
        works[src] = {"lane": j.get("lane"), "reason": j.get("lane_reason"),
                      "pages": j.get("pages"), "cpp": j.get("chars_per_page_detected"),
                      "bundles": 0, "sha": j.get("source_sha256")}
    works[src]["bundles"] += 1

print("anchor bundle dirs :", sum(w["bundles"] for w in works.values()))
print("distinct works     :", len(works))
print()

# find the source pdf on disk
index = {}
for root in SEARCH:
    if not root.is_dir():
        continue
    try:
        for p in root.rglob("*.pdf"):
            index.setdefault(p.name, p)
    except OSError:
        pass

STRUCT = re.compile(r"/StructTreeRoot\s+(\d+)\s+(\d+)\s+R")

def probe_tree(path):
    """(has_tree, n_structelem, n_types, marked, pages) — full xref walk for /S counts."""
    with pymupdf.open(path) as doc:
        pages = doc.page_count
        cat = doc.pdf_catalog()
        keys = doc.xref_get_keys(cat)
        has = "StructTreeRoot" in keys
        marked = None
        if "MarkInfo" in keys:
            marked = doc.xref_get_key(cat, "MarkInfo/Marked")
            marked = marked[1] if marked and marked[0] != "null" else None
        n = 0
        types = set()
        if has:
            # count StructElem objects by scanning every xref for /Type /StructElem
            for x in range(1, doc.xref_length()):
                try:
                    t = doc.xref_get_key(x, "Type")
                except Exception:
                    continue
                if t and t[0] != "null" and t[1] == "/StructElem":
                    n += 1
                    s = doc.xref_get_key(x, "S")
                    if s and s[0] != "null":
                        types.add(s[1])
        return has, n, len(types), marked, pages

rows = []
for src, w in sorted(works.items()):
    p = index.get(src)
    if p is None:
        rows.append((src, w, None, None, None, None, None, "SOURCE-NOT-FOUND"))
        continue
    try:
        has, n, ntypes, marked, pages = probe_tree(p)
        rows.append((src, w, has, n, ntypes, marked, pages, str(p)))
    except Exception as e:
        rows.append((src, w, None, None, None, None, None, "ERR:" + type(e).__name__ + ":" + str(e)[:80]))

hdr = ["work", "lane", "bundles", "pages", "tree?", "StructElem", "types", "Marked", "elem/pp", "found"]
print("\t".join(hdr))
for src, w, has, n, ntypes, marked, pages, where in rows:
    dens = ("%.2f" % (n / pages)) if (n and pages) else ("0.00" if has is not None else "")
    print("\t".join(str(x) for x in [
        src[:52], w["lane"], w["bundles"], w["pages"],
        ("YES" if has else ("no" if has is False else "?")),
        n if n is not None else "", ntypes if ntypes is not None else "",
        marked, dens, ("yes" if where and not where.startswith(("SOURCE", "ERR")) else where)]))
