"""WHAT THIS FILE DOES: a one-off verification script (run directly, no arguments) for SYM-067. For
each of seven Markdown books (one held copy, six anchor copies under C:/Users/Bndit/ml/library) it
runs windows-converter/fidelity_audit.degeneration three ways (raw text, pipe-table lines removed,
and fidelity_audit._strip_markdown) and prints a short summary of each result. Reads files only;
prints to stdout; nothing imports it.
"""
import sys, glob, json, re
from pathlib import Path
sys.path.insert(0, r"C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa

# -- helpers: table-row stripper and a compact summary of a degeneration() result --
PIPE = re.compile(r"^\s*\|.*\|\s*$", re.M)


def strip_tables(md):
    """Return `md` with every pipe-table row (a line that, after optional whitespace, starts and ends with `|`)
    replaced by an empty string; because `\\s` also matches newlines, a match can take the blank line before a
    row and the newline after it, so blank lines beside a table go with it. Pure function."""
    return PIPE.sub("", md)


def keep(d):
    """Reduce a fidelity_audit.degeneration() result `d` to a small dict: flagged, repeated_lines,
    blocks_total, the largest max_trigram and smallest zlib among its "worst" blocks, and the first
    60 characters of the first worst excerpt. Pure function."""
    w = d.get("worst") or []
    return {"flagged": d["flagged"], "repeated_lines": d["repeated_lines"], "blocks_total": d["blocks_total"],
            "worst_max_trigram": max((x["max_trigram"] for x in w), default=0),
            "worst_min_zlib": min((x["zlib"] for x in w), default=None),
            "first_excerpt": (w[0]["excerpt"][:60] if w else None)}


# -- the books to test: label (with the expected outcome) -> glob pattern --
specs = {
    "HELD Damodaran Univ 4e (must NOT trip)": r"C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e/*.md",
    "ANCHOR Beer Brain of the Firm (must STILL trip)": r"C:/Users/Bndit/ml/library/anchor/BRAIN OF THE FIRM*/*.md",
    "ANCHOR Beer Diagnosing (scan lane)": r"C:/Users/Bndit/ml/library/anchor/DIAGNOSING*/*.md",
    "ANCHOR Valentine (scan, no text layer)": r"C:/Users/Bndit/ml/library/anchor/Best Practices*/*.md",
    "ANCHOR Ashby (clean; SYM-056 book)": r"C:/Users/Bndit/ml/library/anchor/Ashby*/*.md",
    "ANCHOR Damodaran 2025 4e": r"C:/Users/Bndit/ml/library/anchor/Investment Valuation - Aswath*/*.md",
    "ANCHOR Damodaran Univ 4e": r"C:/Users/Bndit/ml/library/anchor/Investment Valuation, University*/*.md",
}
# -- run the three variants on every matching file and print them --
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
