"""WHAT THIS FILE DOES: a one-off verification script (run directly, no arguments) for the LaTeX
"array" shapes in one held Markdown book (Damodaran, Investment Valuation, University Edition).
It calls windows-converter/fidelity_audit.latex_balance on it, counts begin/end{array} pairs, page
anchors, column-spec widths and empty pipe-table cells per page, then runs latex_balance on the
matching Markdown files under C:/Users/Bndit/ml/library/anchor for comparison. Reads files, prints
to stdout, writes nothing. Hard-coded Windows paths; nothing imports it.
"""
import sys, re, json, glob
from collections import Counter
from pathlib import Path
sys.path.insert(0, r"C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa            # the REAL function, not a reimplementation

MD = Path(r"C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e/Investment Valuation, University Edition _ Tools and -- Aswath Damodaran -- Four.md")
md = MD.read_text(encoding="utf-8")
lines = md.splitlines()
print("md lines:", len(lines))
lb = fa.latex_balance(md)
print("REAL fidelity_audit.latex_balance:", json.dumps(lb))

# -- page anchors: (line number, page number) of every <span id="page-N-M"> marker --
PAGE_ANCHOR = re.compile(r'<span id="page-(\d+)-\d+"></span>')
anchors = sorted((md.count("\n", 0, m.start()) + 1, int(m.group(1))) for m in PAGE_ANCHOR.finditer(md))
print("anchors:", len(anchors), "first", anchors[0], "last", anchors[-1])
viol = [(a, b) for a, b in zip(anchors, anchors[1:]) if b[1] < a[1]]
print("anchor order violations:", len(viol), viol[:5])
gaps = sorted(((b[0] - a[0], a) for a, b in zip(anchors, anchors[1:])), reverse=True)
print("largest anchor gaps (lines, at):", gaps[:3])


def nearest(ln):
    """Page number of the last page anchor at or before line `ln` (1-based); the first anchor's
    page when none precedes it. Reads the module-level `anchors`; no side effects."""
    best = None
    for l, p in anchors:
        if l <= ln:
            best = p
        else:
            break
    return best if best is not None else anchors[0][1]


# -- direct scan of \begin{array} / \end{array} and the stack check for unterminated ones --
BEG = re.compile(r"\\begin\s*\{array\}")
END = re.compile(r"\\end\s*\{array\}")
begs = [md.count("\n", 0, m.start()) + 1 for m in BEG.finditer(md)]
ends = [md.count("\n", 0, m.start()) + 1 for m in END.finditer(md)]
print("direct scan begin{array}:", len(begs), "end{array}:", len(ends))
# push each begin's line, pop on each end; whatever remains on the stack is unterminated
stack = []
for m in re.finditer(r"\\(begin|end)\s*\{array\}", md):
    ln = md.count("\n", 0, m.start()) + 1
    if m.group(1) == "begin":
        stack.append(ln)
    elif stack:
        stack.pop()
print("unterminated array lines -> (line, nearest anchor page):", [(l, nearest(l)) for l in stack])

# -- column-spec widths of each array; "degenerate" = 6+ identical letters in the spec --
widths = Counter()
degenerate = []
for m in BEG.finditer(md):
    cm = re.match(r"\s*\{([^{}]*)\}", md[m.end():m.end() + 120])
    cs = cm.group(1) if cm else None
    if cs is None:
        widths["none"] += 1
        continue
    widths[len(cs)] += 1
    if len(cs) >= 6 and len(set(cs)) == 1:
        degenerate.append((md.count("\n", 0, m.start()) + 1, cs))
print("colspec widths:", dict(widths), "degenerate(>=6 identical):", degenerate)

# -- pipe-table rows and empty cells ("| |") counted per nearest page --
TR = re.compile(r"^\s*\|.*\|\s*$")
EC = re.compile(r"\|\s*\|")
rows = Counter()
empt = Counter()
nrows = 0
nempty = 0
for i, l in enumerate(lines, 1):
    if TR.match(l):
        nrows += 1
        p = nearest(i)
        rows[p] += 1
        e = len(EC.findall(l))
        empt[p] += e
        nempty += e
print("pipe rows:", nrows, "pages:", len(rows), "empty markers:", nempty, "pages w/ empty:", len([p for p in empt if empt[p]]))
print("top11 by empty:", sorted(empt.items(), key=lambda x: -x[1])[:11])
print("top6 by rows:", sorted(rows.items(), key=lambda x: -x[1])[:6])
# -- comparison against the anchor copies: arrays with a 30-or-more "c" column spec --
WIDE = re.compile(r"\\begin\{array\}\{c{30,}\}")
print("36-c shape in Damodaran held md:", len(WIDE.findall(md)))

for f in glob.glob(r"C:/Users/Bndit/ml/library/anchor/Ashby*/*.md"):
    t = Path(f).read_text(encoding="utf-8")
    r = fa.latex_balance(t)
    print("ASHBY anchor", Path(f).parent.name[:45], "| array:", r["environments"].get("array"), "| total unterminated:", r["unterminated_total"], "begins:", r["begins_seen"], "| 30+c shape:", len(WIDE.findall(t)))
for f in glob.glob(r"C:/Users/Bndit/ml/library/anchor/Investment Valuation, University*/*.md"):
    t = Path(f).read_text(encoding="utf-8")
    r = fa.latex_balance(t)
    print("ANCHOR IV-Univ", Path(f).parent.name[-28:], "| array:", r["environments"].get("array"), "begins:", r["begins_seen"])
for f in glob.glob(r"C:/Users/Bndit/ml/library/anchor/Investment Valuation - Aswath*/*.md"):
    t = Path(f).read_text(encoding="utf-8")
    r = fa.latex_balance(t)
    print("ANCHOR IV-2025", Path(f).parent.name[-28:], "| array:", r["environments"].get("array"), "begins:", r["begins_seen"])
