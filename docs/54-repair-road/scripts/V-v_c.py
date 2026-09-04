"""Verifier (Fable) - lane C probes for J33 + the 'only one Marker reference on disk' claim (J32).
(1) anchor/ pairs: original (no analyst block) vs [analyst-local] re-run of the SAME sha: does
audit_analyst(orig body, rerun body) reproduce the rerun manifest's fidelity.analyst? If yes, the pair is a
valid Marker-reference/analyst pair and a second (third...) book exists for J32's calibration. Then the
normalisation ladder on each valid pair. (2) slice sizes / merged size. (3) max asset page + span id.
Read-only."""
import glob
import json
import os
import re
import sys
import time

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402

V = ("C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/"
     "3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/verify-tickets/V")
A = "C:/Users/Bndit/ml/library/anchor"
LIB = "C:/Users/Bndit/ml/library/.chunk-work/14c66834bdfeaa2e"
HELD_DIR = "C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e"
R = {}
sizes = {os.path.basename(os.path.dirname(p)): os.path.getsize(p) for p in sorted(glob.glob(LIB + "/slice-*/slice.md"))}
merged = "\n\n".join(open(p, encoding="utf-8").read() for p in sorted(glob.glob(LIB + "/slice-*/slice.md")))
R["slices"] = {"sizes": sizes, "sum_bytes": sum(sizes.values()), "merged_utf8_bytes": len(merged.encode("utf-8")),
               "merged_chars": len(merged), "held_md_bytes": os.path.getsize(glob.glob(HELD_DIR + "/*.md")[0]),
               "pages": 1377}
R["slices"]["bytes_per_page"] = round(R["slices"]["merged_utf8_bytes"] / 1377)
held = open(glob.glob(HELD_DIR + "/*.md")[0], encoding="utf-8").read()
R["pages_in_held"] = {"max_asset_page": max(int(x) for x in re.findall(r"_page_(\d+)_", held)),
                      "max_span_page": max(int(x) for x in re.findall(r'id="page-(\d+)-', held)),
                      "count_2553": held.count("2553"), "count_page_2553": held.count("_page_2553_")}
h2025 = [p for p in glob.glob("C:/Users/Bndit/ml/library/held/0d68f0e02293970c/*.md")][0]
t2025 = open(h2025, encoding="utf-8").read()
R["pages_in_held_2025_edition"] = {
    "max_asset_page": max(int(x) for x in re.findall(r"_page_(\d+)_", t2025)),
    "count_page_2553": t2025.count("_page_2553_"),
    "pages_manifest": json.load(open("C:/Users/Bndit/ml/library/held/0d68f0e02293970c/manifest.json",
                                     encoding="utf-8")).get("pages")}
print("slices:", R["slices"], "\npages:", R["pages_in_held"], R["pages_in_held_2025_edition"], flush=True)


def body_of(d):
    # os.listdir, not glob: "[analyst-local]" in a dir name is a glob character class
    md = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".md") and f != "REPAIRS.md"][0]
    raw = open(md, encoding="utf-8").read()
    return raw.split("---\n", 2)[2] if raw.startswith("---\n") else raw


def unesc(t):
    return re.sub(r"\\(?=[^\w\s])", "", t)


def punct(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]|_", " ", t)).strip()


def ladder(mb, ab):
    ref0, out0 = fa.prepare_output(mb), fa.prepare_output(ab)
    cjk = fa.is_cjk(ref0[:4000])
    out = {"cjk": cjk}

    def rung(ref, o, sf):
        wins = fa.make_windows(ref, cjk)
        if sf or cjk:
            oo = o.replace(" ", "")
            f = [w.replace(" ", "") not in oo for w in wins]
        else:
            f = [w not in o for w in wins]
        runs = fa._merge_runs(wins, f, page=None)
        return {"windows": len(wins), "failed": sum(f),
                "doc_survival": round((len(wins) - sum(f)) / max(1, len(wins)), 4), "runs": len(runs),
                "max_run_words": max((r["words"] for r in runs), default=0)}
    out["0_baseline"] = rung(ref0, out0, False)
    r1, o1 = fa.prepare_output(unesc(mb)), fa.prepare_output(unesc(ab))
    out["1_unescape"] = rung(r1, o1, False)
    r2, o2 = punct(r1), punct(o1)
    out["3_unescape+punct+space"] = rung(r2, o2, True)
    return out


pairs = []
dirs = sorted(os.listdir(A))
for d in dirs:
    if "[analyst-" not in d:
        continue
    base = d.split(" [analyst-")[0]
    if base in dirs:
        pairs.append((base, d))
R["pairs"] = []
for orig, rerun in pairs:
    t = time.perf_counter()
    mo = json.load(open(os.path.join(A, orig, "manifest.json"), encoding="utf-8"))
    mr = json.load(open(os.path.join(A, rerun, "manifest.json"), encoding="utf-8"))
    ob, rb = body_of(os.path.join(A, orig)), body_of(os.path.join(A, rerun))
    res = fa.audit_analyst(ob, rb)
    exp = (mr.get("fidelity") or {}).get("analyst") or {}
    rec = {"orig": orig[:60], "rerun_suffix": rerun[len(orig):],
           "same_sha": mo["source_sha256"] == mr["source_sha256"], "sha16": mo["source_sha256"][:16],
           "pages": mo.get("pages"), "lane": mo.get("lane"), "orig_has_analyst_block": bool(mo.get("analyst")),
           "rerun_has_analyst_block": bool(mr.get("analyst")),
           "rerun_model": (mr.get("analyst") or {}).get("model"), "rerun_program": (mr.get("analyst") or {}).get("program"),
           "orig_chars": len(ob), "rerun_chars": len(rb), "recomputed_doc_survival": res["doc_survival"],
           "rerun_manifest_doc_survival": exp.get("doc_survival"), "recomputed_runs_total": res["runs_total"],
           "rerun_manifest_runs_total": exp.get("runs_total"), "rerun_manifest_runs_shown": len(exp.get("runs", [])),
           "recomputed_max_run": max((r["words"] for r in res["runs"]), default=0),
           "rerun_manifest_max_run": max((r["words"] for r in exp.get("runs", [])), default=0)}
    if exp.get("doc_survival") is None:
        rec["pair_valid_marker_reference"] = "no stored analyst block (computed only)"
    elif abs(res["doc_survival"] - exp["doc_survival"]) < 1e-9:
        rec["pair_valid_marker_reference"] = "reproduces manifest"
    else:
        rec["pair_valid_marker_reference"] = "DOES NOT reproduce"
    if mo.get("source_sha256") == mr.get("source_sha256") and not mo.get("analyst") and res["doc_survival"] < 0.995:
        rec["ladder"] = ladder(ob, rb)
    rec["wall_s"] = round(time.perf_counter() - t, 1)
    print(json.dumps(rec, ensure_ascii=False), flush=True)
    R["pairs"].append(rec)
json.dump(R, open(V + "/v_c_result.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("DONE")
