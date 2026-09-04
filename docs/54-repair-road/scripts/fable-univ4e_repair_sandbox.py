"""SANDBOX proof of the re-audit path: copy the held University 4e to the scratchpad, replace the
line-8776 math-OCR runaway with the derivation as printed (transcribed from the witness text of the
footnote, PDF page index 118), re-run the convert-stage audit on the repaired markdown, and compute
the verdict with the manifest's analyst block. Writes ONLY under the scratchpad."""
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402

SP = Path(__file__).parent
LIB = Path("C:/Users/Bndit/ml/library")
HELD = LIB / "held" / "14c66834bdfeaa2e"
SB = SP / "univ4e-sandbox"
if SB.exists():
    shutil.rmtree(SB)
shutil.copytree(HELD, SB, ignore=shutil.ignore_patterns("assets"))
md_path = next(SB.glob("*.md"))
man = json.loads((SB / "manifest.json").read_text(encoding="utf-8"))
text = md_path.read_text(encoding="utf-8")
lines = text.split("\n")

deg0 = fa.degeneration(text)
assert deg0["blocks_total"] == 1, deg0["blocks_total"]
ln = deg0["worst"][0]["line"]
para = lines[ln - 1]
assert para.startswith("$$\\begin{array}{lll} {\\rm ROC}"), para[:60]
print(f"runaway at line {ln}: {len(para)} chars; replacing with the printed derivation")

REPAIR = (
    "$$\\begin{aligned}\n"
    "\\mathrm{ROC} + \\frac{D}{E}\\left[\\mathrm{ROC} - i(1-t)\\right]\n"
    "&= \\frac{\\mathrm{NI} + \\mathrm{Int}(1-t)}{D+E} + \\frac{D}{E}\\left\\{\\frac{\\mathrm{NI} + \\mathrm{Int}(1-t)}{D+E} - \\frac{\\mathrm{Int}(1-t)}{D}\\right\\} \\\\\n"
    "&= \\frac{\\mathrm{NI} + \\mathrm{Int}(1-t)}{D+E}\\left(1 + \\frac{D}{E}\\right) - \\frac{\\mathrm{Int}(1-t)}{E} \\\\\n"
    "&= \\frac{\\mathrm{NI}}{E} + \\frac{\\mathrm{Int}(1-t)}{E} - \\frac{\\mathrm{Int}(1-t)}{E} = \\frac{\\mathrm{NI}}{E} = \\mathrm{ROE}\n"
    "\\end{aligned}$$\n"
    "<!-- repair 2026-09-04 (sandbox proof, Fable): Marker math-OCR loop (21,870 chars, `{1 - t}` x 441) replaced by the "
    "derivation as printed; transcribed from the book's own footnote text (PDF page index 118). A human confirms against the page image. -->"
)
lines[ln - 1] = REPAIR
repaired = "\n".join(lines)
md_path.write_text(repaired, encoding="utf-8")

deg1 = fa.degeneration(repaired)
print("after repair: degeneration flagged", deg1["flagged"], "blocks", deg1["blocks_total"], "| md_lines", deg1["md_lines"])

lb = fa.latex_balance(repaired)
print("latex_balance after repair: unterminated_total", lb["unterminated_total"], "begins_seen", lb["begins_seen"],
      "(before: 87 begins / 3 unterminated per the fleet)")

pdf = LIB / "drop" / "done" / man["source"]
t0 = time.time()
block = fa.audit_convert(pdf, repaired, man["lane"], asset_count=None)
print(f"convert-stage re-audit: doc_survival {block['doc_survival']} (was {man['fidelity']['convert']['doc_survival']}) | pages_scored {block['pages_scored']} "
      f"| flagged pages {len(block['pages_flagged'])} | runs_total {block.get('runs_total')} | tripwires.degeneration {block['tripwires']['degeneration']} | {time.time()-t0:.0f}s")
v_new_with_old_analyst = fa.compute_verdict(block, man["fidelity"]["analyst"])
v_new_alone = fa.compute_verdict(block, None)
print("verdict with the manifest's analyst block:", v_new_with_old_analyst, "| convert stage alone:", v_new_alone)
fb = fa.build_fidelity_block(block, man["fidelity"]["analyst"])
(SB / "fidelity.reaudit.json").write_text(json.dumps(fb, indent=1), encoding="utf-8")
print("wrote", SB / "fidelity.reaudit.json")
