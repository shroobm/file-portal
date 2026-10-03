"""WHAT THIS FILE DOES: a one-off run script (run directly, no functions). It runs fidelity_audit.audit_convert on
marker_ref.md in the current working directory against the University 4e source PDF, prints the elapsed time, and
writes and prints the key numbers (survival, flagged pages, runs, degeneration detail) to marker_ref_result.json
in the current directory. Nothing imports it.
"""
import sys, json, time
sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa

# -- audit the Marker reference against the PDF and summarise the convert-stage block --
pdf = r"C:/Users/Bndit/ml/library/drop/done/Investment Valuation, University Edition _ Tools and -- Aswath Damodaran -- Fourth Edition, 2023 -- Wiley & Sons, Incorporated, John.pdf"
md = open("marker_ref.md", encoding="utf-8").read()
t0 = time.time()
block = fa.audit_convert(pdf, md, "clean")
dt = time.time() - t0
print("elapsed_s", round(dt,1))
out = {
  "doc_survival": block["doc_survival"],
  "pages_scored": block["pages_scored"],
  "pages_flagged_count": len(block["pages_flagged"]),
  "runs_total": block["runs_total"],
  "degeneration": block["tripwires"]["degeneration"],
  "degeneration_detail_worst": block["tripwires"]["degeneration_detail"]["worst"],
  "blocks_total": block["tripwires"]["degeneration_detail"]["blocks_total"],
  "table_rows_stripped": block["tripwires"]["degeneration_detail"]["table_rows_stripped"],
  "md_lines": block["tripwires"]["degeneration_detail"]["md_lines"],
}
json.dump(out, open("marker_ref_result.json","w",encoding="utf-8"), indent=2)
print(json.dumps(out, indent=2)[:4000])
