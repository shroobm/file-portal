"""prototypes/analyst-lab/decoding/analyze_results.py -- post-hoc analysis of decoding_experiment.py's
JSONL ($TEMP/r2/gen_results.jsonl; book text stays there). Prints the per-setting table and writes
analysis.json (numbers only) beside this file.

Denominators, named:
  * per-setting rows = generations of that setting (a: shipped request; b: temperature 0 + seed 7;
    b2: b repeated on 5 chunks; c: b + stricter system line on 5 chunks)
  * "survival" = text_norm.chunk_survival(input chunk, output) -- the shipped per-chunk guard's number
  * "numerals changed" = a digit-token of the input's CONTENT (span anchors, ⟦IMG⟧ tokens, link targets
    stripped first) absent from the output
  * a-vs-b identity = byte-identical output strings for the same chunk
  * manifest_s = the 2026-09-09 production run's survival for the same chunk (same request shape as (a))
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import statistics
import sys
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ddia_pairs  # noqa: E402
import edit_taxonomy as et  # noqa: E402
import text_norm as tn  # noqa: E402

JSONL = pathlib.Path(os.environ.get("TEMP", r"C:\Temp")) / "r2" / "gen_results.jsonl"


def numerals_missing(inp: str, out: str) -> int:
    a = Counter(et.NUM.findall(et.numeral_view(inp)))
    b = Counter(et.NUM.findall(et.numeral_view(out)))
    return sum((a - b).values())


def main() -> None:
    m, chunks_in, outs, cs = ddia_pairs.pairs()
    rows = [json.loads(ln) for ln in JSONL.read_text(encoding="utf-8").splitlines() if ln.strip()]
    by = defaultdict(list)
    for r in rows:
        r["num_missing_clean"] = numerals_missing(chunks_in[r["i"] - 1], r["output"])
        by[r["setting"]].append(r)
    report = {"generations": len(rows), "settings": {}}
    print(f"generations analysed: {len(rows)}")
    for s, rs in by.items():
        sv = [r["survival"] for r in rs if r["survival"] is not None]
        rep = {
            "n": len(rs), "mean_survival": round(statistics.mean(sv), 4), "median_survival": statistics.median(sv),
            "below_0.80": sum(1 for x in sv if x < 0.80), "at_1.0": sum(1 for x in sv if x == 1.0),
            "numerals_changed_chunks": sum(1 for r in rs if r["num_missing_clean"]),
            "numerals_changed_tokens": sum(r["num_missing_clean"] for r in rs),
            "fence_fail": sum(1 for r in rs if not r["fence_ok"]), "think_leak": sum(1 for r in rs if r["think_leak"]),
            "mean_secs": round(statistics.mean(r["secs"] for r in rs), 1),
            "mean_ratio": round(statistics.mean(r["ratio"] for r in rs if r["ratio"] is not None), 4),
        }
        report["settings"][s] = rep
        print(f"  {s:3s} " + "  ".join(f"{k}={v}" for k, v in rep.items()))
    # a vs b on the same chunk
    a_by = {r["i"]: r for r in by.get("a", [])}
    b_by = {r["i"]: r for r in by.get("b", [])}
    common = sorted(set(a_by) & set(b_by))
    ident = sum(1 for i in common if a_by[i]["output"] == b_by[i]["output"])
    same_s = sum(1 for i in common if a_by[i]["survival"] == b_by[i]["survival"])
    d = [b_by[i]["survival"] - a_by[i]["survival"] for i in common if a_by[i]["survival"] is not None and b_by[i]["survival"] is not None]
    report["a_vs_b"] = {"pairs": len(common), "byte_identical": ident, "same_survival": same_s,
                        "mean_delta_b_minus_a": round(statistics.mean(d), 4) if d else None,
                        "b_better": sum(1 for x in d if x > 0), "b_worse": sum(1 for x in d if x < 0)}
    print("a vs b:", report["a_vs_b"])
    # manifest (production run, shape a) vs today's a: run-to-run variance of the shipped setting
    mv = [(i, a_by[i]["manifest_s"], a_by[i]["survival"]) for i in a_by if a_by[i]["manifest_s"] is not None and a_by[i]["manifest_x"] is None]
    same = sum(1 for _, x, y in mv if x == y)
    dd = [y - x for _, x, y in mv]
    report["manifest_vs_a"] = {"passed_chunks": len(mv), "same_survival": same,
                               "mean_delta_today_minus_run": round(statistics.mean(dd), 4) if dd else None,
                               "today_better": sum(1 for x in dd if x > 0), "today_worse": sum(1 for x in dd if x < 0),
                               "max_abs_delta": round(max(abs(x) for x in dd), 4) if dd else None}
    print("manifest(run, shape a) vs today's a:", report["manifest_vs_a"])
    # the 12 survival-rejected chunks: what do they score today under a and b?
    rej = [(i, a_by[i]["manifest_s"], a_by[i]["survival"], b_by.get(i, {}).get("survival")) for i in a_by if a_by[i]["manifest_x"] == "survival"]
    report["rejected12_today"] = rej
    print("survival-rejected in the run -> today (i, run_s, a_s, b_s):", rej)
    # determinism: b vs b2
    b2_by = {r["i"]: r for r in by.get("b2", [])}
    det = [(i, b_by[i]["output"] == b2_by[i]["output"], b_by[i]["survival"], b2_by[i]["survival"]) for i in b2_by if i in b_by]
    report["determinism_b_vs_b2"] = det
    print("determinism b vs b2 (i, identical, s_b, s_b2):", det)
    c_by = {r["i"]: r for r in by.get("c", [])}
    cc = [(i, b_by[i]["survival"], c_by[i]["survival"], c_by[i]["ratio"], c_by[i]["num_missing_clean"]) for i in c_by if i in b_by]
    report["c_vs_b"] = cc
    print("c (strict system) vs b (i, s_b, s_c, ratio_c, numerals_missing_c):", cc)
    # per-chunk rows
    report["rows"] = [{k: r[k] for k in ("n", "i", "setting", "manifest_s", "manifest_x", "survival", "ratio", "fence_ok",
                                          "think_leak", "num_missing_clean", "secs", "words_in", "words_out")} for r in rows]
    (HERE / "analysis.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
