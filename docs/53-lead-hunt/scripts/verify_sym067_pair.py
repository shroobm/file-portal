import sys, glob, json, re
from pathlib import Path
sys.path.insert(0, r"C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa

PIPE = re.compile(r"^\s*\|.*\|\s*$", re.M)


def strip_tables(md):
    return PIPE.sub("", md)


def keep(d):
    w = d.get("worst") or []
    return {"flagged": d["flagged"], "repeated_lines": d["repeated_lines"], "blocks_total": d["blocks_total"],
            "worst_max_trigram": max((x["max_trigram"] for x in w), default=0),
            "worst_min_zlib": min((x["zlib"] for x in w), default=None),
            "first_excerpt": (w[0]["excerpt"][:60] if w else None)}


specs = {
    "HELD Damodaran Univ 4e (must NOT trip)": r"C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e/*.md",
    "ANCHOR Beer Brain of the Firm (must STILL trip)": r"C:/Users/Bndit/ml/library/anchor/BRAIN OF THE FIRM*/*.md",
    "ANCHOR Beer Diagnosing (scan lane)": r"C:/Users/Bndit/ml/library/anchor/DIAGNOSING*/*.md",
    "ANCHOR Valentine (scan, no text layer)": r"C:/Users/Bndit/ml/library/anchor/Best Practices*/*.md",
    "ANCHOR Ashby (clean; SYM-056 book)": r"C:/Users/Bndit/ml/library/anchor/Ashby*/*.md",
    "ANCHOR Damodaran 2025 4e": r"C:/Users/Bndit/ml/library/anchor/Investment Valuation - Aswath*/*.md",
    "ANCHOR Damodaran Univ 4e": r"C:/Users/Bndit/ml/library/anchor/Investment Valuation, University*/*.md",
}
for label, pat in specs.items():
    for f in glob.glob(pat):
        md = Path(f).read_text(encoding="utf-8")
        raw = fa.degeneration(md)
        stripped = fa.degeneration(strip_tables(md))
        sm = fa.degeneration(fa._strip_markdown(md))
        print(label, "|", Path(f).parent.name[-34:])
        print("   RAW            :", json.dumps(keep(raw)))
        print("   PIPE-STRIPPED  :", json.dumps(keep(stripped)))
        print("   _strip_markdown:", json.dumps(keep(sm)))
