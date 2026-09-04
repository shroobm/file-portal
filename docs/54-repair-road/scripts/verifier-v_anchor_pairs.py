"""Does more than one Marker reference exist on disk? anchor/ holds original (Marker-only) bundles
beside [analyst-local] re-runs of the same PDF. apply_analyst() audits body-vs-new_body, so
audit_analyst(original body, rerun body) must reproduce the rerun manifest's fidelity.analyst if
the pair is a valid Marker-reference/analyst pair. Read-only."""
import glob
import json
import os
import sys
import time

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402

OUT = "C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/verify-tickets/verifier/v_anchor_pairs_result.json"
A = "C:/Users/Bndit/ml/library/anchor"
PAIRS = [
    ("claude-code-up-and-running", "claude-code-up-and-running [analyst-local]"),
    ("claude-code-up-and-running", "claude-code-up-and-running [analyst-local rerun]"),
    ("DIAGNOSING THE SYSTEM FOR ORGANIZATIONS STAFFORD BEER",
     "DIAGNOSING THE SYSTEM FOR ORGANIZATIONS STAFFORD BEER [analyst-local]"),
    ("Investment Valuation - Aswath Damodaran (4e, 2025)",
     "Investment Valuation - Aswath Damodaran (4e, 2025) [analyst-local]"),
]


def body_of(d):
    md = [p for p in glob.glob(os.path.join(d, "*.md")) if not p.endswith("REPAIRS.md")][0]
    raw = open(md, encoding="utf-8").read()
    return raw.split("---\n", 2)[2] if raw.startswith("---\n") else raw


R = []
for orig, rerun in PAIRS:
    t0 = time.perf_counter()
    mo = json.load(open(os.path.join(A, orig, "manifest.json"), encoding="utf-8"))
    mr = json.load(open(os.path.join(A, rerun, "manifest.json"), encoding="utf-8"))
    ob, rb = body_of(os.path.join(A, orig)), body_of(os.path.join(A, rerun))
    res = fa.audit_analyst(ob, rb)
    exp = (mr.get("fidelity") or {}).get("analyst") or {}
    rec = {"orig": orig, "rerun": rerun, "same_sha": mo["source_sha256"] == mr["source_sha256"],
           "orig_has_analyst_block": bool(mo.get("analyst")), "orig_chars": len(ob), "rerun_chars": len(rb),
           "recomputed_doc_survival": res["doc_survival"], "rerun_manifest_doc_survival": exp.get("doc_survival"),
           "recomputed_runs_total": res["runs_total"], "rerun_manifest_runs_shown": len(exp.get("runs", [])),
           "recomputed_max_run": max((r["words"] for r in res["runs"]), default=0),
           "rerun_manifest_max_run": max((r["words"] for r in exp.get("runs", [])), default=0),
           "wall_s": round(time.perf_counter() - t0, 1)}
    print(rec, flush=True)
    R.append(rec)
json.dump(R, open(OUT, "w", encoding="utf-8"), indent=1)
print("DONE")
