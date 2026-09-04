"""Classify every analyst-stage FAILED window of the held University 4e against the rebuilt Marker
reference (the 7 slice.md files the converter merged). Mirrors fidelity_audit.audit_analyst exactly,
then asks of each failed window: what did the analyst change? Read-only; JSON to the scratchpad."""
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402
from rapidfuzz import fuzz  # noqa: E402

SP = Path(__file__).parent
HELD = Path("C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e")
slices = sorted((SP / "univ4e-marker").glob("slice-*.md"))
marker = "\n\n".join(p.read_text(encoding="utf-8") for p in slices)   # the converter's parts join
held = next(HELD.glob("*.md")).read_text(encoding="utf-8")
man = json.loads((HELD / "manifest.json").read_text(encoding="utf-8"))
print("slices:", len(slices), "| marker chars", len(marker), "| held chars", len(held))

t0 = time.time()
ref = fa.prepare_output(marker)
out = fa.prepare_output(held)
cjk = fa.is_cjk(ref[:4000])
windows = fa.make_windows(ref, cjk)
failed = [w not in out for w in windows]
doc = round(failed.count(False) / len(windows), 4)
runs = fa._merge_runs(windows, failed, page=None)
print(f"MIRROR of audit_analyst: doc_survival {doc} (manifest {man['fidelity']['analyst']['doc_survival']}) | windows {len(windows)} "
      f"| failed {failed.count(True)} | runs {len(runs)} (manifest runs_total {man['fidelity']['analyst'].get('runs_total')}) | {time.time()-t0:.0f}s")

# the sanctioned-edit hypothesis: does forgiving SPACES alone clear the gate?
out_ns = out.replace(" ", "")
failed_ns = [w.replace(" ", "") not in out_ns for w in windows]
doc_ns = round(failed_ns.count(False) / len(windows), 4)
runs_ns = fa._merge_runs(windows, failed_ns, page=None)
print(f"SPACE-FREE containment: doc_survival {doc_ns} | failed {failed_ns.count(True)} | runs {len(runs_ns)} | "
      f"gate {fa.ANALYST_DOC_FAIL} -> {'PASS' if doc_ns >= fa.ANALYST_DOC_FAIL and not any(r['words'] >= fa.ANALYST_RUN_WORDS for r in runs_ns) else 'still FAIL'}"
      f" (max run words {max((r['words'] for r in runs_ns), default=0)})")

# classify each failed window by its best local alignment in the held text (anchor-based, like _fuzzy_hit)
idx, freq = fa._build_index(out)
classes = Counter()
words_by_class = Counter()
examples = {}
t1 = time.time()
for w, f in zip(windows, failed):
    if not f:
        continue
    anchors = [a for a in w.split() if a in freq]
    best, seg_best = 0.0, ""
    if anchors:
        rare = min(anchors, key=lambda a: freq[a])
        span = len(w)
        for off in idx[rare][:fa.FUZZY_ANCHOR_CAP]:
            seg = out[max(0, off - span): off + span + len(rare)]
            al = fuzz.partial_ratio_alignment(w, seg)
            if al and al.score > best:
                best, seg_best = al.score, seg[al.dest_start:al.dest_end]
    if best >= 90:
        if w.replace(" ", "") == seg_best.replace(" ", ""):
            c = "space-only (word join/split)"
        elif re.sub(r"[^0-9a-z]", "", w) == re.sub(r"[^0-9a-z]", "", seg_best):
            c = "punctuation/format only"
        else:
            c = "small edit (>=90 similar)"
    elif best >= 60:
        c = "rewrite (60-89 similar)"
    else:
        c = "absent (<60)"
    classes[c] += 1
    words_by_class[c] += len(w.split())
    examples.setdefault(c, [])
    if len(examples[c]) < 4:
        examples[c].append({"ref": w, "held": seg_best[:160], "score": round(best, 1)})
print(f"classified {sum(classes.values())} failed windows in {time.time()-t1:.0f}s")
tot = sum(classes.values())
for c, n in classes.most_common():
    print(f"  {n:6d}  {100*n/tot:5.1f}%  {c}  (words {words_by_class[c]})")
for c in classes:
    print(f"\n-- {c}")
    for e in examples[c]:
        print(f"   ref : {e['ref'][:120]}\n   held: {e['held'][:120]}  [{e['score']}]")
json.dump({"doc_survival_mirror": doc, "doc_survival_spacefree": doc_ns, "windows": len(windows),
           "failed": failed.count(True), "failed_spacefree": failed_ns.count(True), "runs": len(runs), "runs_spacefree": len(runs_ns),
           "max_run_words_spacefree": max((r["words"] for r in runs_ns), default=0),
           "classes": dict(classes), "words_by_class": dict(words_by_class), "examples": examples},
          open(SP / "univ4e_classify.json", "w", encoding="utf-8"), indent=1)
print("\nwrote univ4e_classify.json")
