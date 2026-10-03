"""WHAT THIS FILE DOES: a one-off verification script (run directly, no arguments) for the residual
case of SYM-067. It reads one held Markdown book (Damodaran, Investment Valuation, University
Edition), removes its pipe-table rows, runs windows-converter/fidelity_audit.degeneration on the
rest and prints the surviving worst blocks; then it finds the same "$$" block in the unstripped text
and prints its line, size, head, tail and top trigram. Reads one file; prints to stdout; nothing
imports it.
"""
import sys, re, json
from pathlib import Path
sys.path.insert(0, r"C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa

# -- input: the held book's Markdown text and the pipe-row pattern --
MD = Path(r"C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e/Investment Valuation, University Edition _ Tools and -- Aswath Damodaran -- Four.md")
md = MD.read_text(encoding="utf-8")
PIPE = re.compile(r"^\s*\|.*\|\s*$", re.M)
# -- blocks that still look degenerate after the pipe rows are removed --
d = fa.degeneration(PIPE.sub("", md))
for w in d["worst"]:
    print("SURVIVOR after pipe-strip:", json.dumps(w))
# locate the same block in the ORIGINAL body by excerpt
# -- locate the first "$$" worst block in the unstripped text and describe it (stops after the first) --
raw = fa.degeneration(md)
for w in raw["worst"]:
    if w["excerpt"].startswith("$$"):
        print("in RAW body: line", w["line"], "chars", w["chars"], "zlib", w["zlib"], "max_trigram", w["max_trigram"])
        lines = md.splitlines()
        blk = lines[w["line"] - 1]
        print("   len(line):", len(blk))
        print("   head 300:", blk[:300])
        print("   tail 200:", blk[-200:])
        toks = blk.lower().split()
        from collections import Counter
        tri = Counter(" ".join(toks[i:i + 3]) for i in range(len(toks) - 2))
        print("   top trigram:", tri.most_common(2))
        print("   unterminated array opens near here (8776)?", "begin{array}" in blk, "end{array}" in blk)
        break
print("RAW worst table-shaped blocks (first 5 excerpts):", [w["excerpt"][:40] for w in raw["worst"][:5]])
