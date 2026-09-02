"""Verifier: (1) resolve the survey-vs-corpus_probe disagreement on /MarkInfo /Marked by
reading it three ways; (2) read the held manifest 14c66834bdfeaa2e for the 404/531 question;
(3) quote exact ISO 32000-2 lines for NonStruct, Suspects, 14.8.1, Table 377 BBox, 14.8.4.8.3.
Read-only."""
import sys, io, json, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import pymupdf

DL = r"C:/Users/Bndit/Downloads/"
files = [
    "bojieli_ai-agent-book： 《深入理解 AI Agent：设计原理与工程实践》（李博杰 著）开源主仓库：全书正文、编译版 PDF 与按章配套代码 (2026-07-18 3：4….pdf",
    "ISO_TS_32003-2023_sponsored.pdf",
    "SDT_Comprehensive_Record.docx.pdf",
    "Untitled document.pdf",
    "Well-Tagged-PDF-WTPDF-1.0.pdf",
    "DIAGNOSING THE SYSTEM FOR ORGANIZATIONS STAFFORD BEER.pdf",
]
import glob, os
print("=== /MarkInfo /Marked read three ways ===")
for f in files:
    p = DL + f
    if not os.path.exists(p):
        cands = glob.glob(DL + f[:20] + "*")
        p = cands[0] if cands else None
    if not p:
        print("NOT FOUND", f[:40]); continue
    d = pymupdf.open(p)
    cat = d.pdf_catalog()
    mi = d.xref_get_key(cat, "MarkInfo")
    mm = d.xref_get_key(cat, "MarkInfo/Marked")
    # resolve indirect MarkInfo if needed
    raw = None
    if mi and mi[0] == "xref":
        x = int(mi[1].split()[0]); raw = d.xref_object(x)
    print(f"{os.path.basename(p)[:44]:46s} markinfo={d.markinfo!r:40s} MarkInfo={mi} MarkInfo/Marked={mm} raw={raw!r}")
    d.close()

print()
print("=== held manifest 14c66834bdfeaa2e ===")
m = json.load(open(r"C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e/manifest.json", encoding="utf-8"))
print("top keys:", sorted(m.keys()))
fid = m.get("fidelity", {})
print("fidelity keys:", sorted(fid.keys()) if isinstance(fid, dict) else fid)
for phase in ("convert", "analyst"):
    ph = fid.get(phase, {}) if isinstance(fid, dict) else {}
    if isinstance(ph, dict):
        keep = {k: v for k, v in ph.items() if k in ("doc_survival", "runs_total", "runs_capped_at", "verdict", "degeneration", "witness", "witness_label", "gates", "run_page")}
        runs = ph.get("runs")
        print(f"  {phase}: {json.dumps(keep, ensure_ascii=False)} | len(runs)={len(runs) if isinstance(runs, list) else runs}")
        if isinstance(runs, list) and runs:
            print(f"     first run keys: {sorted(runs[0].keys())} | page field: {runs[0].get('page')} run_page: {runs[0].get('run_page')}")
            print(f"     runs with page None: {sum(1 for r in runs if r.get('page') is None)} / {len(runs)}")
for k in ("verdict", "audit", "supersede", "held", "source", "pages", "lane", "lane_reason", "probe_evidence", "blocks"):
    if k in m:
        v = m[k]
        s = json.dumps(v, ensure_ascii=False)
        print(f"  {k}: {s[:300]}")

print()
print("=== exact ISO 32000-2 lines ===")
lines = open(r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/d6f7a30f-66e5-40d2-a905-b2dd64ee7f44/scratchpad/pdfua/iso32000-2.txt", encoding="utf-8", errors="replace").read().split("\n")
def show(a, b, label):
    print(f"--- {label} (L{a}-L{b})")
    for i in range(a - 1, b):
        print(f"  L{i+1}: {lines[i].rstrip()[:180]}")
show(55526, 55542, "NonStruct entry, Table 365 PAGE 773")
show(50950, 50966, "Suspects entry, Table 353 PAGE 738")
show(54744, 54760, "14.8.1 General PAGE 760")
show(56496, 56503, "Table 377 BBox row PAGE 789")
show(56186, 56196, "Figure BBox/Alt sentence PAGE 784")
# find the header-search algorithm sentence
for i, ln in enumerate(lines):
    if "direction implied by" in ln or "toward the first cell" in ln:
        show(max(1, i - 2), i + 4, "table header algorithm")
        break
