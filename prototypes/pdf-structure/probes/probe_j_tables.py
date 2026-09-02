"""Three things the mapping needs measured, not inferred:

 (1) TABLE: can a Markdown table be emitted straight from Table/TR/TH/TD without any
     geometric grid inference? (bears on SYM-056 and SYM-067)
 (2) READING ORDER: does the declared depth-first order differ from pymupdf's default
     geometric extraction order? (bears on the witness)
 (3) COST: seconds to read the whole structure tree, vs the current witness extraction.
"""
import re, time, collections
import pymupdf

FL = pymupdf.TEXTFLAGS_DICT | pymupdf.TEXT_COLLECT_STRUCTURE


def first_table_page(doc):
    for i in range(doc.page_count):
        d = doc[i].get_text("dict", flags=FL)

        def has(bl):
            for b in bl:
                if b.get("type") == 2:
                    if b.get("raw") == "Table":
                        return True
                    if has(b.get("blocks", [])):
                        return True
            return False
        if has(d["blocks"]):
            return i
    return None


def text_of(b):
    out = []
    for x in b.get("blocks", []) if b.get("type") == 2 else []:
        out.append(text_of(x))
    if b.get("type") == 0:
        out.append("".join(s["text"] for l in b.get("lines", []) for s in l["spans"]))
    return " ".join(t for t in out if t).strip()


def find(bl, tag, acc):
    for b in bl:
        if b.get("type") == 2:
            if b.get("raw") == tag:
                acc.append(b)
            find(b.get("blocks", []), tag, acc)
    return acc


P = r"C:/Users/Bndit/Downloads/Well-Tagged-PDF-WTPDF-1.0.pdf"
doc = pymupdf.open(P)
pno = first_table_page(doc)
print("=== (1) TABLE STRAIGHT FROM THE TREE  (page index %s) ===" % pno)
pg = doc[pno]
tables = find(pg.get_text("dict", flags=FL)["blocks"], "Table", [])
print("Table elements on page:", len(tables))
t = tables[0]
rows = find([t], "TR", [])
print("declared rows (TR):", len(rows))
md = []
for ri, r in enumerate(rows):
    cells = []
    for c in r.get("blocks", []):
        if c.get("type") == 2 and c.get("raw") in ("TH", "TD"):
            cells.append((c["raw"], text_of(c)))
    md.append(cells)
    if ri < 6:
        print("  TR%-2d %s" % (ri, [(k, v[:34]) for k, v in cells]))
print()
print("--- emitted Markdown, NO geometry used, NO \\begin{array} needed ---")
if md:
    w = max(len(r) for r in md)
    for ri, r in enumerate(md[:6]):
        cells = [v.replace("|", "\\|") for _, v in r] + [""] * (w - len(r))
        print("| " + " | ".join(c[:26] for c in cells) + " |")
        if ri == 0 and all(k == "TH" for k, _ in r):
            print("| " + " | ".join(["---"] * w) + " |")
print("cells declared TH:", sum(1 for r in md for k, _ in r if k == "TH"),
      "| TD:", sum(1 for r in md for k, _ in r if k == "TD"),
      "| EMPTY cells (still declared, i.e. not degeneration):",
      sum(1 for r in md for _, v in r if not v.strip()))

# ---- (2) reading order ----
print()
print("=== (2) READING ORDER: declared depth-first vs geometric default ===")


def declared_stream(page):
    out = []

    def w(bl):
        for b in bl:
            if b.get("type") == 2:
                w(b.get("blocks", []))
            elif b.get("type") == 0:
                out.append("".join(s["text"] for l in b.get("lines", []) for s in l["spans"]))
    w(page.get_text("dict", flags=FL)["blocks"])
    return out


agree = diff = nopages = 0
sample = []
for i in range(doc.page_count):
    p = doc[i]
    dec = [re.sub(r"\s+", " ", s).strip() for s in declared_stream(p) if s.strip()]
    geo = [re.sub(r"\s+", " ", "".join(sp["text"] for l in b.get("lines", []) for sp in l["spans"])).strip()
           for b in p.get_text("dict")["blocks"] if b.get("type") == 0]
    geo = [g for g in geo if g]
    if not dec:
        nopages += 1
        continue
    if dec == geo:
        agree += 1
    else:
        diff += 1
        if len(sample) < 3:
            sample.append((i, dec[:3], geo[:3], len(dec), len(geo)))
print("pages where declared order == geometric order: %d / %d scored (%d pages had no struct text)"
      % (agree, agree + diff, nopages))
for i, d, g, nd, ng in sample:
    print("  page %d  declared[0:3]=%s (n=%d)" % (i, [x[:40] for x in d], nd))
    print("           geometric[0:3]=%s (n=%d)" % ([x[:40] for x in g], ng))

# ---- (3) cost ----
print()
print("=== (3) COST (numerator seconds / denominator pages, this file, CPU) ===")
for label, fl in (("witness get_text() [today]", None),
                  ("get_text dict +STRUCT", FL)):
    t0 = time.perf_counter()
    n = 0
    for i in range(doc.page_count):
        if fl is None:
            doc[i].get_text()
        else:
            doc[i].get_text("dict", flags=fl)
        n += 1
    dt = time.perf_counter() - t0
    print("  %-28s %.3f s / %d pages = %.2f ms/page" % (label, dt, n, 1000 * dt / n))

# xref walk cost


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


t0 = time.perf_counter()
cat = doc.pdf_catalog()
root = int(get(cat, "StructTreeRoot")[1].split()[0])
seen, stack, ne = set(), list(kids(root)), 0
while stack:
    x = stack.pop()
    if x in seen:
        continue
    seen.add(x)
    stack.extend(kids(x))
    if get(x, "S"):
        ne += 1
        for k in ("Alt", "ActualText", "Pg", "A", "Lang"):
            get(x, k)
dt = time.perf_counter() - t0
print("  %-28s %.3f s / %d StructElem = %.3f ms/elem (%d pages)"
      % ("raw xref tree walk + attrs", dt, ne, 1000 * dt / ne, doc.page_count))
