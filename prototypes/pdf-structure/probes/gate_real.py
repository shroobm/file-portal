"""The proposed lane gate, run over the operator's REAL converted corpus.

Same four tests the design specifies, in the order it specifies them, so the gate can be
watched REFUSING real files -- especially the Beer 'Diagnosing' book, whose tree is present
and large (2276 StructElem) but is 179 Figures and nothing else.

Read-only. CPU. No GPU.
"""
import json
import re
import time
from pathlib import Path

import pymupdf

ANCHOR = Path(r"C:\Users\Bndit\ml\library\anchor")
SEARCH = [Path(r"C:\Users\Bndit\Downloads"), Path(r"C:\Users\Bndit\ml\library")]
_REF = re.compile(r"(\d+) 0 R")

# Marker's own 28 BlockTypes have a declared counterpart for 24 of them (mapping.md 3).
# These are the roles that carry DOCUMENT SEMANTICS -- Figure/Span/NonStruct deliberately
# excluded, because a per-page Figure wrapper is what a scanned book gets from a bad
# exporter and is the exact case this gate must refuse.
SEMANTIC_ROLES = {"P", "H", "H1", "H2", "H3", "H4", "H5", "H6", "Title", "L", "LI",
                  "LBody", "Lbl", "Table", "TR", "TH", "TD", "THead", "TBody", "TFoot",
                  "Caption", "Code", "Formula", "TOC", "TOCI", "Sect", "Part", "Div",
                  "Note", "FENote", "Reference", "BibEntry", "BlockQuote", "Quote",
                  "Aside", "Link"}

T1_MIN_ELEM_PER_PAGE = 5.0     # density
T2_MIN_SEMANTIC_TYPES = 6      # richness
T3_MAX_NONSTRUCT_SHARE = 0.5   # rot: roles
T4_MIN_MCID_RESOLVE = 0.90     # rot: content-stream reachability


def read_tree(path, mcid_pages=25, elem_cap=40000):
    rec = {"tagged": False, "elems": 0, "roles": {}, "alt": 0, "actualtext": 0,
           "mcids": 0, "mcids_ok": 0, "capped": False, "pages": 0}
    with pymupdf.open(path) as doc:
        rec["pages"] = doc.page_count
        cat = doc.pdf_catalog()
        v = doc.xref_get_key(cat, "StructTreeRoot")
        if not v or v[0] == "null":
            return rec
        rec["tagged"] = True
        m = _REF.search(v[1])
        if not m:
            return rec
        n = doc.page_count
        step = max(1, n // mcid_pages)
        live = set()
        for i in list(range(0, n, step))[:mcid_pages]:
            for cs in doc[i].get_contents():
                try:
                    for mm in re.finditer(rb"/MCID\s+(\d+)", doc.xref_stream(cs)):
                        live.add(int(mm.group(1)))
                except Exception:
                    pass
        seen, stack = set(), [int(m.group(1))]
        while stack:
            if len(seen) >= elem_cap:
                rec["capped"] = True
                break
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            s = doc.xref_get_key(x, "S")
            if s and s[0] != "null":
                role = s[1].lstrip("/")
                rec["elems"] += 1
                rec["roles"][role] = rec["roles"].get(role, 0) + 1
            for key, field in (("Alt", "alt"), ("ActualText", "actualtext")):
                a = doc.xref_get_key(x, key)
                if a and a[0] != "null":
                    rec[field] += 1
            k = doc.xref_get_key(x, "K")
            if k and k[0] != "null":
                for r in _REF.findall(k[1]):
                    stack.append(int(r))
                for num in re.findall(r"\b(\d+)\b", _REF.sub(" ", k[1])):
                    rec["mcids"] += 1
                    if int(num) in live:
                        rec["mcids_ok"] += 1
    return rec


def gate(rec):
    """-> (lane, reason). Order matters: cheapest refusal first."""
    if not rec["tagged"]:
        return "clean-or-scan", "no_structure_tree"
    if rec["elems"] == 0:
        return "clean-or-scan", "tree_hollow_zero_elements"
    # CORRECTION, forced by the corpus (see design.md 2.4): NonStruct is a STRUCTURALLY
    # TRANSPARENT grouping element (ISO 32000-2 14.8.4.3) -- its children are read as the
    # parent's. Counting its share as "rot" refused bojieli, a genuinely structured file,
    # at 51.1%. It is FLATTENED here, not scored: density and richness are measured over
    # semantically-bearing elements only.
    sem_elems = sum(n for r, n in rec["roles"].items() if r in SEMANTIC_ROLES)
    epp = sem_elems / max(1, rec["pages"])
    if epp < T1_MIN_ELEM_PER_PAGE:
        return "clean-or-scan", "tree_density_%.2f_below_%.1f" % (epp, T1_MIN_ELEM_PER_PAGE)
    sem = {r for r in rec["roles"] if r in SEMANTIC_ROLES}
    if len(sem) < T2_MIN_SEMANTIC_TYPES:
        return "clean-or-scan", "tree_semantic_types_%d_below_%d" % (
            len(sem), T2_MIN_SEMANTIC_TYPES)
    if rec["mcids"] and rec["mcids_ok"] / rec["mcids"] < T4_MIN_MCID_RESOLVE:
        return "clean-or-scan", "tree_mcid_resolve_%.2f" % (rec["mcids_ok"] / rec["mcids"])
    return "tagged", "structure_tree_conforming"


works = {}
for d in sorted(ANCHOR.iterdir()):
    m = d / "manifest.json"
    if m.is_file():
        j = json.loads(m.read_text(encoding="utf-8"))
        works.setdefault(j.get("source"), {"lane": j.get("lane"), "pages": j.get("pages"),
                                           "bundles": 0})
        works[j["source"]]["bundles"] += 1

index = {}
for root in SEARCH:
    if root.is_dir():
        for p in root.rglob("*.pdf"):
            index.setdefault(p.name, p)

print("work\tlane_today\tbundles\tpages\telems\tsem_types\talt\tactual\tmcid_ok\t"
      "gate_lane\tgate_reason\tgate_ms")
tot_pages = tagged_pages = 0
for src, w in sorted(works.items()):
    p = index.get(src)
    if p is None:
        print(src[:34] + "\tSOURCE-NOT-FOUND")
        continue
    t0 = time.perf_counter()
    rec = read_tree(p)
    lane, reason = gate(rec)
    ms = (time.perf_counter() - t0) * 1000
    sem = len({r for r in rec["roles"] if r in SEMANTIC_ROLES})
    mres = ("%.2f" % (rec["mcids_ok"] / rec["mcids"])) if rec["mcids"] else "-"
    print("\t".join(str(x) for x in [src[:34], w["lane"], w["bundles"], rec["pages"],
                                     rec["elems"], sem, rec["alt"], rec["actualtext"],
                                     mres, lane, reason, "%.0f" % ms]))
    tot_pages += rec["pages"]
    if lane == "tagged":
        tagged_pages += rec["pages"]

print()
print("PAGES: tagged-lane %d / corpus %d = %.2f%%" % (
    tagged_pages, tot_pages, 100.0 * tagged_pages / tot_pages))
