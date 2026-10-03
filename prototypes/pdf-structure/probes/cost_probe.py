"""WHAT THIS FILE DOES: a timing script (run directly, no arguments). For four named books in Downloads it
times, per page, plain get_text, get_texttrace and the structure-collecting dict extraction on up to 25
sampled pages, plus the catalog /StructTreeRoot lookup, and prints one tab-separated row per book.
Read-only; stdout only; needs pymupdf; no callers.

COST: what the tagged-lane probe adds to convert_and_ship.probe(), re-measured.

Three operations timed separately on the same pages of the same real books:
  A  page.get_text()                              -- probe()'s chars/page half
  B  page.get_texttrace()                         -- probe()'s OCR-vote half
  C  page.get_text("dict", flags=+COLLECT_STRUCTURE)   -- the PROPOSED addition
  D  catalog /StructTreeRoot lookup (whole doc, once)  -- the cheap pre-gate

numerator = seconds; denominator = pages timed; conditions = CPU, pymupdf 1.28.0 in
marker-env, cold-ish (each op runs on a freshly opened doc), no GPU.
"""
import time
from pathlib import Path

import pymupdf

FL = pymupdf.TEXTFLAGS_DICT | pymupdf.TEXT_COLLECT_STRUCTURE
DL = Path(r"C:\Users\Bndit\Downloads")

BOOKS = [
    "Ashby - An Introduction to Cybernetics (1956).pdf",
    "Investment Valuation - Aswath Damodaran (4e, 2025).pdf",
    "DIAGNOSING THE SYSTEM FOR ORGANIZATIONS STAFFORD BEER.pdf",
    "claude-code-up-and-running.pdf",
]

# file name -> first path found under Downloads
index = {}
for p in DL.rglob("*.pdf"):
    index.setdefault(p.name, p)

N = 25  # pages sampled per book


# -- timing helpers --
def timeit(path, fn):
    """Open the PDF at `path`, call fn(page) on up to N evenly spaced pages; return (ms per page, pages timed)."""
    with pymupdf.open(path) as doc:
        n = doc.page_count
        step = max(1, n // N)
        idxs = list(range(0, n, step))[:N]
        t0 = time.perf_counter()
        for i in idxs:
            fn(doc[i])
        return (time.perf_counter() - t0) / len(idxs) * 1000.0, len(idxs)


def struct_root_ms(path, reps=5):
    """Open `path` `reps` times and look up /StructTreeRoot; return (mean ms per open, tree present?)."""
    t0 = time.perf_counter()
    for _ in range(reps):
        with pymupdf.open(path) as doc:
            cat = doc.pdf_catalog()
            v = doc.xref_get_key(cat, "StructTreeRoot")
            present = bool(v) and v[0] != "null"
    return (time.perf_counter() - t0) / reps * 1000.0, present


# -- driver: time operations A-D on each book and print one row --
print("book\tpages_timed\tA_get_text_ms/pp\tB_texttrace_ms/pp\tC_dict+struct_ms/pp"
      "\tC_minus_A_ms/pp\tD_StructTreeRoot_ms/doc\ttree?")
for name in BOOKS:
    p = index.get(name)
    if p is None:
        print(name[:40] + "\tNOT-FOUND")
        continue
    a, n = timeit(p, lambda pg: pg.get_text())
    b, _ = timeit(p, lambda pg: pg.get_texttrace())
    c, _ = timeit(p, lambda pg: pg.get_text("dict", flags=FL))
    d, present = struct_root_ms(p)
    print("\t".join([name[:38], str(n), "%.2f" % a, "%.2f" % b, "%.2f" % c,
                     "%+.2f" % (c - a), "%.1f" % d, "YES" if present else "no"]))
