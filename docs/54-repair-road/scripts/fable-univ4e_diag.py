"""Read-only diagnosis of the held University 4e (14c66834bdfeaa2e): why does the verdict fail?
(1) the convert-stage degeneration block after J29; (2) the analyst-stage near-exact loss —
re-run audit_analyst(marker_md, held_md) and classify the omission runs; (3) the real page and
witness text under the line-8776 runaway. Nothing is written outside the scratchpad."""
import glob
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402

LIB = Path("C:/Users/Bndit/ml/library")
HELD = LIB / "held" / "14c66834bdfeaa2e"
OUT = Path(__file__).with_name("univ4e_diag.json")

held_md = next(HELD.glob("*.md"))
man = json.loads((HELD / "manifest.json").read_text(encoding="utf-8"))
print("held md:", held_md.name, held_md.stat().st_size, "bytes")
print("manifest: verdict", man["fidelity"]["verdict"], "| convert doc_survival", man["fidelity"]["convert"]["doc_survival"],
      "| analyst doc_survival", man["fidelity"]["analyst"]["doc_survival"],
      "| analyst runs_total", man["fidelity"]["analyst"].get("runs_total"), "| convert runs_total", man["fidelity"]["convert"].get("runs_total"))
print("chunking:", json.dumps(man.get("chunking"))[:400])
print("analyst meta keys:", [k for k in man.get("analyst", {}).keys()][:20] if isinstance(man.get("analyst"), dict) else man.get("analyst"))

# ---- which anchor copy is the Marker (pre-analyst) markdown?
cands = sorted(LIB.glob("anchor/Investment Valuation, University Edition*/"))
marker_md = None
for d in cands:
    m = json.loads((d / "manifest.json").read_text(encoding="utf-8")) if (d / "manifest.json").exists() else {}
    md = next(d.glob("*.md"), None)
    has_analyst = bool(m.get("analyst"))
    print("anchor:", d.name[-40:], "| md bytes", md.stat().st_size if md else None, "| analyst block:", has_analyst,
          "| source_sha", (m.get("source_sha256") or "")[:12], "| converted_at", m.get("converted_at"))
    if md and not has_analyst and marker_md is None:
        marker_md = md
print("marker (pre-analyst) md:", marker_md)

held_text = held_md.read_text(encoding="utf-8")
res = {"held": held_md.name, "marker_md": str(marker_md)}

# ---- (1) convert-stage degeneration after J29
t = time.time()
deg = fa.degeneration(held_text)
print("\n[1] degeneration (J29): flagged", deg["flagged"], "blocks", deg["blocks_total"], "rows stripped", deg["table_rows_stripped"],
      "| %.1fs" % (time.time() - t))
for w in deg["worst"]:
    print("    line", w["line"], "chars", w["chars"], "zlib", w["zlib"], "tri", w["max_trigram"], "|", w["excerpt"][:60])
res["degeneration"] = deg

# ---- (3) the page under line 8776 and the witness text there
lines = held_text.split("\n")
ln = deg["worst"][0]["line"] if deg["worst"] else 8776
before = "\n".join(lines[:ln])
m = list(re.finditer(r'id="page-(\d+)-', before))
page_anchor = int(m[-1].group(1)) if m else None
print("\n[3] last span anchor before line", ln, "-> page", page_anchor)
para = lines[ln - 1]
print("    runaway paragraph: chars", len(para), "| head:", para[:120].replace("\n", " "))
print("    tail:", para[-160:].replace("\n", " "))
src_pdf = LIB / "drop" / "done" / man["source"]
res["page_anchor"] = page_anchor
res["runaway_head"] = para[:300]
res["runaway_tail"] = para[-300:]
if src_pdf.exists() and page_anchor:
    import pymupdf
    doc = pymupdf.open(str(src_pdf))
    for p in (page_anchor - 1, page_anchor, page_anchor + 1):
        if 0 <= p < len(doc):
            txt = doc[p].get_text()
            hit = "ROC" in txt and ("1 - t" in txt or "1 − t" in txt or "(1 –" in txt)
            print(f"    pdf page index {p}: {len(txt)} chars, ROC/1-t present: {hit} | {txt[:90]!r}")
            if hit:
                res["witness_page_index"] = p
                res["witness_text"] = txt
    doc.close()
else:
    print("    source pdf not on disk:", src_pdf)

# ---- (2) the analyst-stage audit, re-run
if marker_md:
    t = time.time()
    marker_text = marker_md.read_text(encoding="utf-8")
    ab = fa.audit_analyst(marker_text, held_text)
    print("\n[2] audit_analyst re-run: doc_survival", ab["doc_survival"], "| runs shown", len(ab["runs"]), "of", ab.get("runs_total"),
          "| %.0fs" % (time.time() - t))
    print("    run keys:", list(ab["runs"][0].keys()) if ab["runs"] else None)
    runs = sorted(ab["runs"], key=lambda r: -r["words"])
    tot = sum(r["words"] for r in ab["runs"])
    print("    words in shown runs:", tot, "| gate: doc <", fa.ANALYST_DOC_FAIL, "or any run >=", fa.ANALYST_RUN_WORDS, "words")
    for r in runs[:8]:
        ex = (r.get("excerpt") or r.get("text") or "")[:110]
        print("    run words", r["words"], "|", ex.replace("\n", " "))
    res["analyst_audit"] = {k: ab[k] for k in ab if k != "runs"}
    res["analyst_runs_top"] = runs[:12]
    # classify: how many of the shown runs are inside LaTeX / array regions vs prose?
    latexy = sum(1 for r in ab["runs"] if "\\" in (r.get("excerpt") or "") or "array" in (r.get("excerpt") or ""))
    print("    shown runs with LaTeX markers in excerpt:", latexy, "of", len(ab["runs"]))
OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print("\nwrote", OUT)
