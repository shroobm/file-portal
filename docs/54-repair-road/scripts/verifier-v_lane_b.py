"""Verifier re-run of lane B's decisive probes (J31). Read-only; audits run on in-memory copies.
Three audit_convert runs: marker reference (unrepaired), held FULL file (unrepaired, as the
builder/lane B measured), marker reference repaired (runaway paragraph deleted). Plus the
negative control on the degeneration detector and compute_verdict with the historical analyst
block."""
import glob
import hashlib
import json
import sys
import time

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402

OUT = "C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/verify-tickets/verifier/v_lane_b_result.json"
PDF = ("C:/Users/Bndit/ml/library/drop/done/Investment Valuation, University Edition _ Tools and -- "
       "Aswath Damodaran -- Fourth Edition, 2023 -- Wiley & Sons, Incorporated, John.pdf")
LIB = "C:/Users/Bndit/ml/library/.chunk-work/14c66834bdfeaa2e"
HELD_DIR = "C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e"

R = {}
manifest = json.load(open(HELD_DIR + "/manifest.json", encoding="utf-8"))
sha = hashlib.sha256(open(PDF, "rb").read()).hexdigest()
R["pdf_sha_matches_manifest"] = sha == manifest["source_sha256"]
R["asset_count"] = len(glob.glob(HELD_DIR + "/assets/*"))
slices = sorted(glob.glob(LIB + "/slice-*/slice.md"))
marker = "\n\n".join(open(p, encoding="utf-8").read() for p in slices)
held_full = open(glob.glob(HELD_DIR + "/*.md")[0], encoding="utf-8").read()
hist_analyst = manifest["fidelity"]["analyst"]
stored = manifest["fidelity"]["convert"]
R["manifest_convert"] = {"doc_survival": stored["doc_survival"], "pages_scored": stored["pages_scored"],
                         "pages_flagged": len(stored["pages_flagged"]), "runs_total": stored["runs_total"],
                         "degeneration": stored["tripwires"]["degeneration"],
                         "asset_delta": stored["tripwires"].get("asset_delta")}


def run(name, text):
    t0 = time.perf_counter()
    conv = fa.audit_convert(PDF, text, "clean", asset_count=R["asset_count"])
    tw = conv["tripwires"]
    dd = tw.get("degeneration_detail") or {}
    rec = {"doc_survival": conv["doc_survival"], "pages_scored": conv["pages_scored"],
           "pages_flagged": len(conv["pages_flagged"]), "runs_total": conv.get("runs_total"),
           "degeneration": tw["degeneration"], "blocks_total": dd.get("blocks_total"),
           "worst": [(w["line"], w["chars"], w["zlib"], w["max_trigram"]) for w in dd.get("worst", [])[:3]],
           "asset_delta": tw.get("asset_delta"),
           "verdict_convert_alone": fa.compute_verdict(conv, None),
           "verdict_with_historical_analyst": fa.compute_verdict(conv, hist_analyst),
           "wall_s": round(time.perf_counter() - t0, 1)}
    print(name, rec, flush=True)
    R[name] = rec
    return rec


a = run("marker_ref_unrepaired", marker)
b = run("held_full_unrepaired", held_full)

# repair the marker text: delete the paragraph that starts at the worst block's line
lines = marker.split("\n")
start = a["worst"][0][0] - 1  # 0-based
end = start
while end < len(lines) and lines[end].strip():
    end += 1
removed = lines[start:end]
R["marker_repair"] = {"deleted_lines_1based": [start + 1, end], "deleted_chars": sum(len(x) for x in removed),
                      "head": removed[0][:60] if removed else None,
                      "tail_head": removed[-1][:60] if removed else None}
repaired = "\n".join(lines[:start] + lines[end:])
c = run("marker_ref_repaired", repaired)

# negative control on the detector alone (no PDF): a synthetic runaway appended to the REPAIRED text
synthetic = repaired + "\n\n" + ("{\\rm Int}\\left( {1 - t} \\right)/{\\rm E} \\\\ & - & " * 300) + "\n"
d = fa.degeneration(synthetic)
R["negative_control_synthetic_runaway"] = {"flagged": d.get("flagged"), "blocks_total": d.get("blocks_total"),
                                           "worst0": (d["worst"][0]["line"], d["worst"][0]["chars"]) if d.get("worst") else None}
# and the detector on the repaired text alone must be quiet
d2 = fa.degeneration(repaired)
R["repaired_degeneration_alone"] = {"flagged": d2.get("flagged"), "blocks_total": d2.get("blocks_total")}
print("controls:", R["negative_control_synthetic_runaway"], R["repaired_degeneration_alone"], flush=True)
json.dump(R, open(OUT, "w", encoding="utf-8"), indent=1)
print("DONE")
