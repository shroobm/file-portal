"""Verifier (Fable) - own re-run of lane B's decisive probes for J31. Read-only; audits on in-memory
copies. audit_convert on: the Marker body rebuilt from the LIBRARY slice cache (unrepaired), the held
FULL md (unrepaired), each with its runaway paragraph deleted. compute_verdict combos.
Negative controls on degeneration()."""
import glob
import hashlib
import json
import sys
import time

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402

V = ("C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/"
     "3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/verify-tickets/V")
PDF = ("C:/Users/Bndit/ml/library/drop/done/Investment Valuation, University Edition _ Tools and -- "
       "Aswath Damodaran -- Fourth Edition, 2023 -- Wiley & Sons, Incorporated, John.pdf")
LIB = "C:/Users/Bndit/ml/library/.chunk-work/14c66834bdfeaa2e"
HELD_DIR = "C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e"
R = {}
manifest = json.load(open(HELD_DIR + "/manifest.json", encoding="utf-8"))
R["pdf_sha_matches_manifest"] = hashlib.sha256(open(PDF, "rb").read()).hexdigest() == manifest["source_sha256"]
R["asset_count"] = len(glob.glob(HELD_DIR + "/assets/*"))
marker = "\n\n".join(open(p, encoding="utf-8").read() for p in sorted(glob.glob(LIB + "/slice-*/slice.md")))
held_full = open(glob.glob(HELD_DIR + "/*.md")[0], encoding="utf-8").read()
hist = manifest["fidelity"]["analyst"]
stored = manifest["fidelity"]["convert"]
R["manifest_convert"] = {"doc_survival": stored["doc_survival"], "pages_scored": stored["pages_scored"],
                         "pages_flagged": len(stored["pages_flagged"]), "runs_total": stored["runs_total"],
                         "degeneration": stored["tripwires"]["degeneration"],
                         "degeneration_worst0_line": stored["tripwires"]["degeneration_detail"]["worst"][0]["line"],
                         "degeneration_blocks_total": stored["tripwires"]["degeneration_detail"].get("blocks_total"),
                         "asset_delta": stored["tripwires"].get("asset_delta"),
                         "embedded_images": stored["tripwires"].get("embedded_images")}


def run(name, text):
    t = time.perf_counter()
    conv = fa.audit_convert(PDF, text, "clean", asset_count=R["asset_count"])
    tw = conv["tripwires"]
    dd = tw.get("degeneration_detail") or {}
    rec = {"doc_survival": conv["doc_survival"], "pages_scored": conv["pages_scored"],
           "pages_flagged": len(conv["pages_flagged"]),
           "pages_flagged_equal_manifest_list": conv["pages_flagged"] == stored["pages_flagged"],
           "runs_total": conv.get("runs_total"), "degeneration": tw["degeneration"],
           "blocks_total": dd.get("blocks_total"),
           "worst": [(w["line"], w["chars"], w["zlib"], w["max_trigram"]) for w in dd.get("worst", [])[:3]],
           "asset_delta": tw.get("asset_delta"), "embedded_images": tw.get("embedded_images"),
           "verdict_convert_alone": fa.compute_verdict(conv, None),
           "verdict_with_historical_analyst": fa.compute_verdict(conv, hist),
           "wall_s": round(time.perf_counter() - t, 1)}
    print(name, rec, flush=True)
    R[name] = rec
    return rec


a = run("marker_ref_unrepaired", marker)
b = run("held_full_unrepaired", held_full)
lines = marker.split("\n")
start = a["worst"][0][0] - 1
end = start
while end < len(lines) and lines[end].strip():
    end += 1
removed = lines[start:end]
R["marker_repair"] = {"deleted_lines_1based": [start + 1, end], "deleted_chars": sum(len(x) for x in removed),
                      "head": removed[0][:70]}
repaired = "\n".join(lines[:start] + lines[end:])
c = run("marker_ref_repaired", repaired)
# held: same repair shape at ITS worst line
hl = held_full.split("\n")
hs = b["worst"][0][0] - 1
he = hs
while he < len(hl) and hl[he].strip():
    he += 1
R["held_repair"] = {"deleted_lines_1based": [hs + 1, he], "deleted_chars": sum(len(x) for x in hl[hs:he]),
                    "head": hl[hs][:70],
                    "line_after_blank": hl[he + 1].strip() if he + 1 < len(hl) else None}
d = run("held_full_repaired", "\n".join(hl[:hs] + hl[he:]))
# controls on the detector alone (no PDF)
synthetic = repaired + "\n\n" + ("{\\rm Int}\\left( {1 - t} \\right)/{\\rm E} \\\\ & - & " * 300) + "\n"
dg = fa.degeneration(synthetic)
dq = fa.degeneration(repaired)
R["control_synthetic_runaway_trips"] = {"flagged": dg.get("flagged"), "blocks_total": dg.get("blocks_total")}
R["control_repaired_quiet"] = {"flagged": dq.get("flagged"), "blocks_total": dq.get("blocks_total")}
R["verdict_matrix"] = {"hist_analyst_with_a_clean_convert_block": fa.compute_verdict(
    {"tripwires": {}, "doc_survival": 1.0, "runs": [], "pages_flagged": []}, hist)}
print("controls:", R["control_synthetic_runaway_trips"], R["control_repaired_quiet"], R["verdict_matrix"], flush=True)
json.dump(R, open(V + "/v_b_result.json", "w", encoding="utf-8"), indent=1)
print("DONE")
