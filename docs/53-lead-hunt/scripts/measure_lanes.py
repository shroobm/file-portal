import json, os, sys
import pymupdf

DONE = r"C:/Users/Bndit/ml/library/drop/done"

works = [
    ("Ashby - An Introduction to Cybernetics (1956).pdf", "clean"),
    ("Best Practices for Equity Research Analysts - James J Valentine (2011).pdf", "scan"),
    ("bojieli_ai-agent-book： 《深入理解 AI Agent：设计原理与工程实践》（李博杰 著）开源主仓库：全书正文、编译版 PDF 与按章配套代码 (2026-07-18 3：4….pdf", "clean"),
    ("BRAIN OF THE FIRM STAFFORD BEER (WITH OCR) ISBN 13 9780471162131.pdf", "scan"),
    ("claude-code-up-and-running.pdf", "clean"),
    ("Cybernetics_Book_of_Models-v4.6b-complete.pdf", "clean"),
    ("DIAGNOSING THE SYSTEM FOR ORGANIZATIONS STAFFORD BEER.pdf", "scan"),
    ("Investment Valuation - Aswath Damodaran (4e, 2025).pdf", "clean"),
    ("Investment Valuation, University Edition _ Tools and -- Aswath Damodaran -- Fourth Edition, 2023 -- Wiley & Sons, Incorporated, John.pdf", "clean"),
]

MISSING = ["Designing with Freedom W Sketches from Stafford Beer, Chichester, West Sussex ISBN 13 9780471062202.pdf (scan, per manifest) -- SOURCE NOT ON DISK, UNREAD"]

results = []
for fname, manifest_lane in works:
    path = os.path.join(DONE, fname)
    if not os.path.exists(path):
        results.append({"file": fname, "manifest_lane": manifest_lane, "error": "MISSING FROM drop/done"})
        continue
    try:
        doc = pymupdf.open(path)
    except Exception as e:
        results.append({"file": fname, "manifest_lane": manifest_lane, "error": f"open failed: {e}"})
        continue
    total_spans = 0
    mode_counts = {}
    pages = doc.page_count
    # FULL document, every page -- matches probe()'s own loop exactly (convert_and_ship.py:766-773).
    sampled = 0
    for page in doc:
        try:
            trace = page.get_texttrace()
        except Exception as e:
            trace = []
        for span in trace:
            total_spans += 1
            t = span.get("type")
            mode_counts[t] = mode_counts.get(t, 0) + 1
        sampled += 1
    invisible = mode_counts.get(3, 0) + mode_counts.get(7, 0)
    ratio = (invisible / total_spans) if total_spans else 0.0
    meta = doc.metadata or {}
    producer = meta.get("producer", "")
    creator = meta.get("creator", "")
    results.append({
        "file": fname,
        "manifest_lane": manifest_lane,
        "pages_total": pages,
        "pages_sampled": sampled,
        "total_spans": total_spans,
        "mode_counts": mode_counts,
        "invisible_spans": invisible,
        "invisible_ratio": round(ratio, 4),
        "predicted_lane_by_ratio_gt_0.5": "scan" if ratio > 0.5 else "clean",
        "producer": producer,
        "creator": creator,
    })
    doc.close()

out_path = r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/d6f7a30f-66e5-40d2-a905-b2dd64ee7f44/scratchpad/leads/lane_measurements.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"results": results, "missing": MISSING}, f, indent=2, ensure_ascii=False)

for r in results:
    print(r.get("file", "?")[:70], "|", r.get("manifest_lane"), "|", r.get("invisible_ratio", r.get("error")), "|", r.get("predicted_lane_by_ratio_gt_0.5"), "|", r.get("producer","")[:40])
