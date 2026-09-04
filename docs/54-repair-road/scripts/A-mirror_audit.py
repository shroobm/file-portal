"""Lane A — independent re-derivation of claim (1): audit_analyst mirror.

Rebuilds the Marker reference from the 7 slice.md files (join = "\n\n", verified against
convert_and_ship.py:1419/1456), loads the shipped analyst markdown from the held bundle,
and calls the REAL fidelity_audit.audit_analyst (imported directly from the repo source —
this is the pipeline's own code, not the builder's derived script) to see whether it lands
on doc_survival=0.9402 / runs_total=404 as recorded in manifest.json.

Run with marker-env python (imports pymupdf, rapidfuzz via fidelity_audit).
"""
import glob
import json
import sys

sys.path.insert(0, r"C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402

SLICE_DIR = r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/univ4e-marker"
ANALYST_MD = r"C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e/Investment Valuation, University Edition _ Tools and -- Aswath Damodaran -- Four.md"
MANIFEST = r"C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e/manifest.json"
OUT = r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/verify-tickets/A/mirror_result.json"


def main():
    files = sorted(glob.glob(SLICE_DIR + "/slice-*.md"))
    assert len(files) == 7, f"expected 7 slice files, found {len(files)}: {files}"
    parts = [open(f, encoding="utf-8").read() for f in files]
    marker_ref = "\n\n".join(parts)

    analyst_md = open(ANALYST_MD, encoding="utf-8").read()

    result = fa.audit_analyst(marker_ref, analyst_md)

    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    claimed = manifest["fidelity"]["analyst"]

    report = {
        "slice_files": files,
        "marker_ref_chars": len(marker_ref),
        "marker_ref_sha256_first16": __import__("hashlib").sha256(marker_ref.encode("utf-8")).hexdigest()[:16],
        "analyst_md_chars": len(analyst_md),
        "mirror_doc_survival": result["doc_survival"],
        "mirror_runs_total": result["runs_total"],
        "claimed_doc_survival": claimed["doc_survival"],
        "claimed_runs_total": claimed["runs_total"],
        "match_doc_survival": result["doc_survival"] == claimed["doc_survival"],
        "match_runs_total": result["runs_total"] == claimed["runs_total"],
        "windows_total_ref": None,
    }
    # also recompute windows_total for later ladder math re-use
    ref_prepared = fa.prepare_output(marker_ref)
    cjk = fa.is_cjk(ref_prepared[:4000])
    windows = fa.make_windows(ref_prepared, cjk)
    report["windows_total_ref"] = len(windows)
    report["failed_windows"] = int(round((1 - result["doc_survival"]) * len(windows)))

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
