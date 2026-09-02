import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from gate_real import read_tree, SEMANTIC_ROLES, index  # noqa: E402

for name in ("bojieli_ai-agent-book： 《深入理解 AI Agent：设计原理与工程实践》（李博杰）.pdf",
             "DIAGNOSING THE SYSTEM FOR ORGANIZATIONS STAFFORD BEER.pdf"):
    p = index.get(name)
    if p is None:
        cand = [k for k in index if k.startswith(name[:20])]
        p = index.get(cand[0]) if cand else None
        name = cand[0] if cand else name
    if p is None:
        print("NOT FOUND", name[:40])
        continue
    rec = read_tree(p)
    print("\n===", name[:60], "| elems", rec["elems"], "| pages", rec["pages"],
          "| Alt", rec["alt"], "| ActualText", rec["actualtext"])
    for r, n in sorted(rec["roles"].items(), key=lambda kv: -kv[1]):
        mark = "SEM" if r in SEMANTIC_ROLES else "   "
        print("   %s %-16s %5d  %5.1f%%" % (mark, r, n, 100.0 * n / rec["elems"]))
