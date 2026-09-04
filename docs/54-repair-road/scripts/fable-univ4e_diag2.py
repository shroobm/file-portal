"""(1) Are the analyst-stage omission runs LOST text or REORDERED text? Test each manifest run
excerpt against the held markdown. (2) Locate the runaway formula's real PDF page. Read-only."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402
from rapidfuzz import fuzz  # noqa: E402

LIB = Path("C:/Users/Bndit/ml/library")
HELD = LIB / "held" / "14c66834bdfeaa2e"
man = json.loads((HELD / "manifest.json").read_text(encoding="utf-8"))
held = next(HELD.glob("*.md")).read_text(encoding="utf-8")
held_search = fa.prepare_output(held)

a = man["fidelity"]["analyst"]
am = man.get("analyst", {})
print("analyst counters: passed", am.get("chunks_passed"), "rejected", am.get("chunks_rejected"), "failed", am.get("chunks_failed"),
      "resumed", am.get("chunks_resumed"), "generated", am.get("chunks_generated"), "| program", am.get("program"))
print("analyst block: doc_survival", a["doc_survival"], "runs shown", len(a["runs"]), "of", a.get("runs_total"),
      "| words in shown runs", sum(r["words"] for r in a["runs"]))
found = 0
for r in sorted(a["runs"], key=lambda r: -r["words"])[:25]:
    ex = fa._finalize(fa._strip_markdown(fa._common(r["excerpt"])))
    score = fuzz.partial_ratio(ex, held_search) if ex else 0
    present = score >= 90
    found += present
    print(f"  run {r['words']:5d} words | present in held (partial_ratio {score:5.1f}): {str(present):5} | {r['excerpt'][:70]}")
print(f"excerpts of the 25 shown runs found in the held text: {found}/25 (>=90 partial_ratio on the audit's own normalisation)")

# convert-stage runs too: are the top convert omission excerpts present in the held text?
c = man["fidelity"]["convert"]
cf = 0
for r in sorted(c["runs"], key=lambda r: -r["words"])[:10]:
    ex = fa._finalize(fa._strip_markdown(fa._common(r["excerpt"])))
    sc = fuzz.partial_ratio(ex, held_search) if ex else 0
    cf += sc >= 90
    print(f"  convert run p{r.get('page')} {r['words']:4d} words | in held {sc:5.1f} | {r['excerpt'][:60]}")
print(f"convert-stage top-10 run excerpts present in held: {cf}/10 (witness text the markdown lacks: {10-cf})")

# (2) the runaway's real page: search the PDF for the ROC / D/E formula
import pymupdf
doc = pymupdf.open(str(LIB / "drop" / "done" / man["source"]))
hits = []
for i, p in enumerate(doc):
    t = p.get_text()
    if "ROC" in t and "D/E" in t and ("1 - t" in t or "1 − t" in t or "1 – t" in t or "(1 -" in t or "1-t" in t):
        hits.append(i)
print("PDF page indices with ROC + D/E + (1 - t):", hits[:12], "of", len(doc), "pages")
lines = held.split("\n")
after = "\n".join(lines[8776:8776 + 400])
m = re.search(r'id="page-(\d+)-', after)
print("next span anchor after line 8776 ->", m.group(1) if m else None, "; anchor before -> 439")
for i in hits[:2]:
    t = doc[i].get_text()
    k = t.find("ROC")
    print(f"--- page index {i} text around the formula:\n{t[max(0, k-200):k+400]!r}")
doc.close()
