"""Verifier: locate cited clauses/tables in the source .txt files and print the PAGE marker
each sits under, plus a few lines of context. Read-only."""
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SRC = r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/d6f7a30f-66e5-40d2-a905-b2dd64ee7f44/scratchpad/pdfua/"

_cache = {}
def pgmap(name):
    if name in _cache:
        return _cache[name]
    lines = open(SRC + name, encoding="utf-8", errors="replace").read().split("\n")
    page = None; pg = []
    for ln in lines:
        m = re.match(r"^--------- PAGE (\d+) ---------", ln)
        if m:
            page = int(m.group(1))
        pg.append(page)
    _cache[name] = (lines, pg)
    return _cache[name]

def find(name, pat, maxhits=6, ctx=0, flags=0):
    lines, pg = pgmap(name)
    rx = re.compile(pat, flags)
    n = 0
    for i, ln in enumerate(lines):
        if rx.search(ln):
            print(f"   {name} L{i+1:6d} PAGE {pg[i]} | {ln.strip()[:170]}")
            for j in range(1, ctx + 1):
                if i + j < len(lines):
                    print(f"        +{j} | {lines[i+j].strip()[:170]}")
            n += 1
            if n >= maxhits:
                break
    if n == 0:
        print(f"   {name}: NO MATCH for /{pat}/")

ISO = "iso32000-2.txt"
Q = [
    ("14.8.2.5.1 heading", ISO, r"^14\.8\.2\.5\.1\b", 3, 2),
    ("depth-first", ISO, r"depth-first", 4, 1),
    ("Table 353", ISO, r"^Table 353", 2, 0),
    ("Suspects", ISO, r"\bSuspects\b", 6, 1),
    ("Table 354", ISO, r"^Table 354", 2, 0),
    ("Table 355", ISO, r"^Table 355", 2, 0),
    ("Table 359", ISO, r"^Table 359", 2, 0),
    ("Table 375", ISO, r"^Table 375", 2, 0),
    ("Table 377", ISO, r"^Table 377", 2, 0),
    ("Table 384", ISO, r"^Table 384", 2, 0),
    ("14.8.4.3 heading", ISO, r"^14\.8\.4\.3\b", 2, 1),
    ("14.8.4.4 heading", ISO, r"^14\.8\.4\.4\b", 2, 1),
    ("NonStruct", ISO, r"\bNonStruct\b", 6, 0),
    ("14.8.4.8.3 heading", ISO, r"^14\.8\.4\.8\.3\b", 2, 1),
    ("14.8.4.8.5 heading", ISO, r"^14\.8\.4\.8\.5\b", 2, 1),
    ("14.8.5.7 heading", ISO, r"^14\.8\.5\.7\b", 2, 1),
    ("14.8.5.4 heading", ISO, r"^14\.8\.5\.4\b", 2, 1),
    ("14.8.1 heading", ISO, r"^14\.8\.1\s", 2, 3),
    ("14.7.5.4 heading", ISO, r"^14\.7\.5\.4\b", 2, 1),
    ("14.8.2.2 heading", ISO, r"^14\.8\.2\.2\b", 3, 1),
    ("Table 104", ISO, r"^Table 104", 2, 0),
    ("9.3.6 heading", ISO, r"^9\.3\.6\b", 2, 1),
    ("BBox line start", ISO, r"^BBox\b", 8, 1),
    ("14.7.3 heading", ISO, r"^14\.7\.3\b", 2, 1),
    ("Table 365", ISO, r"^Table 365", 2, 0),
    ("Table 373", ISO, r"^Table 373", 2, 0),
    ("14.7.6 heading", ISO, r"^14\.7\.6\b", 3, 0),
    ("Marked true shall", ISO, r"Marked.*true", 6, 0),
    # PDF/UA-1
    ("UA1 Suspects", "pdfua1.txt", r"Suspects", 4, 1),
    ("UA1 do not by themselves", "pdfua1.txt", r"do not by themselves", 2, 1),
    ("UA1 7.4.2", "pdfua1.txt", r"^7\.4\.2", 2, 3),
    ("UA1 7.1 heading", "pdfua1.txt", r"^7\.1\s", 3, 2),
    ("UA1 Clause 5 heading", "pdfua1.txt", r"^5\s", 3, 3),
    ("UA1 7.3 Figure shall", "pdfua1.txt", r"Figure tags shall", 2, 1),
    ("UA1 Artifacts shall not be tagged", "pdfua1.txt", r"shall not be tagged", 2, 1),
    # PDF/UA-2
    ("UA2 Suspects", "pdfua2.txt", r"Suspects", 4, 1),
    ("UA2 do not determine", "pdfua2.txt", r"do not determine", 2, 1),
    ("UA2 H shall not", "pdfua2.txt", r"shall not use the H structure", 2, 1),
    ("UA2 tables regular", "pdfua2.txt", r"shall be regular", 3, 1),
    ("UA2 8.2.2 real content enclosed", "pdfua2.txt", r"enclosed within semantically", 2, 1),
    ("UA2 8.2.5.12", "pdfua2.txt", r"^8\.2\.5\.12", 2, 1),
    ("UA2 8.2.5.26", "pdfua2.txt", r"^8\.2\.5\.26", 2, 1),
    ("UA2 8.2.5.28", "pdfua2.txt", r"^8\.2\.5\.28", 3, 1),
    ("UA2 8.2.3 heading", "pdfua2.txt", r"^8\.2\.3\s", 2, 2),
    ("UA2 Clause 5 heading", "pdfua2.txt", r"^5\s", 3, 3),
    ("UA2 8.4.5.1", "pdfua2.txt", r"^8\.4\.5\.1", 2, 3),
    ("UA2 rendering mode 3", "pdfua2.txt", r"rendering mode 3", 3, 1),
    # WTPDF
    ("WT Annex/Appendix C", "wtpdf.txt", r"(Annex|Appendix) C", 4, 1),
    ("WT pdfuaid", "wtpdf.txt", r"pdfuaid", 6, 1),
    ("WT 6.2 heading", "wtpdf.txt", r"^6\.2\s", 2, 4),
    ("WT reuse1.0", "wtpdf.txt", r"reuse1\.0", 4, 0),
    ("WT 8.2.5.28.2", "wtpdf.txt", r"8\.2\.5\.28\.2", 2, 4),
    ("WT normative", "wtpdf.txt", r"normative", 6, 0),
    # BPG
    ("BPG 5.5.3.1", "tagged-bpg.txt", r"^5\.5\.3\.1", 2, 6),
    ("BPG OCR", "tagged-bpg.txt", r"\bOCR\b", 8, 1),
    ("BPG render mode", "tagged-bpg.txt", r"render(ing)? mode", 6, 1),
    ("BPG empty cell", "tagged-bpg.txt", r"[Ee]mpty cell", 6, 2),
    ("BPG 4.2.6.2", "tagged-bpg.txt", r"^4\.2\.6\.2", 2, 3),
    ("BPG 2.6", "tagged-bpg.txt", r"^2\.6\s", 2, 4),
    ("BPG 3.2 heading", "tagged-bpg.txt", r"^3\.2\s", 2, 3),
    # AN002
    ("AN002 4.2.2", "an002-af.txt", r"^4\.2\.[234]", 4, 2),
    ("AN002 Alternative", "an002-af.txt", r"Alternative", 6, 0),
    # TS32005
    ("TS32005 7.2", "ts32005.txt", r"^7\.2\s", 2, 3),
    # declarations
    ("DECL guarantee", "declarations.txt", r"guarantee", 3, 1),
]
for label, name, pat, mh, ctx in Q:
    print(f"### {label}   /{pat}/")
    find(name, pat, maxhits=mh, ctx=ctx)

# counts
wt = open(SRC + "wtpdf.txt", encoding="utf-8", errors="replace").read()
print("### WT tag counts: accessibility =", wt.count("Conformance level for accessibility"),
      "| reuse =", wt.count("Conformance level for reuse"))
ua2 = open(SRC + "pdfua2.txt", encoding="utf-8", errors="replace").read()
print("### UA2 'Suspects' occurrences:", ua2.count("Suspects"))
ua1 = open(SRC + "pdfua1.txt", encoding="utf-8", errors="replace").read()
print("### UA1 'Suspects' occurrences:", ua1.count("Suspects"))
