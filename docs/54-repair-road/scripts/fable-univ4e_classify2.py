"""(1) Normalisation experiments on the analyst gate: does unescaping Marker's backslash escapes
(+ space-free, + punctuation-free) clear 0.995 on University 4e? (2) Where do the ABSENT windows
live in the book? Read-only."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402

SP = Path(__file__).parent
HELD = Path("C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e")
marker = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted((SP / "univ4e-marker").glob("slice-*.md")))
held = next(HELD.glob("*.md")).read_text(encoding="utf-8")

ESC = re.compile(r"\\([\\`*_{}\[\]()#+\-.!$|<>~])")   # markdown backslash escapes


def unescape(t):
    return ESC.sub(r"\1", t)


def variants(m, h):
    out = {}
    ref0, out0 = fa.prepare_output(m), fa.prepare_output(h)
    out["as shipped"] = (ref0, out0)
    ref1, out1 = fa.prepare_output(unescape(m)), fa.prepare_output(unescape(h))
    out["+ unescape \\( \\) \\$ …"] = (ref1, out1)
    out["+ unescape + space-free"] = (ref1.replace(" ", ""), out1.replace(" ", ""))
    strip = lambda s: re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", s)  # noqa: E731
    out["+ unescape + punctuation-free"] = (fa._finalize(strip(ref1)), fa._finalize(strip(out1)))
    out["+ unescape + punct-free + space-free"] = (fa._finalize(strip(ref1)).replace(" ", ""), fa._finalize(strip(out1)).replace(" ", ""))
    return out


res = {}
base_windows = None
for name, (ref, out) in variants(marker, held).items():
    spacefree = " " not in ref[:5000]
    if spacefree:
        # windows must be cut on the SPACED text, then space-stripped, or the gate measures nothing
        continue
    windows = fa.make_windows(ref, False)
    failed = [w not in out for w in windows]
    runs = fa._merge_runs(windows, failed, page=None)
    mx = max((r["words"] for r in runs), default=0)
    doc = round(failed.count(False) / len(windows), 4)
    verdict = "PASS" if doc >= fa.ANALYST_DOC_FAIL and mx < fa.ANALYST_RUN_WORDS else "FAIL"
    print(f"{name:42s} doc_survival {doc}  failed {failed.count(True):5d}/{len(windows)}  runs {len(runs):4d}  max run {mx:4d} words  -> {verdict}")
    res[name] = {"doc": doc, "failed": failed.count(True), "windows": len(windows), "runs": len(runs), "max_run": mx}
    if base_windows is None:
        base_windows, base_failed = windows, failed
# the space-free variants: cut windows on spaced text, compare space-stripped
for name, (ref_sp, out_sp) in [("+ unescape + space-free", (fa.prepare_output(unescape(marker)), fa.prepare_output(unescape(held)).replace(" ", "")))]:
    windows = fa.make_windows(ref_sp, False)
    failed = [w.replace(" ", "") not in out_sp for w in windows]
    runs = fa._merge_runs(windows, failed, page=None)
    mx = max((r["words"] for r in runs), default=0)
    doc = round(failed.count(False) / len(windows), 4)
    print(f"{name:42s} doc_survival {doc}  failed {failed.count(True):5d}/{len(windows)}  runs {len(runs):4d}  max run {mx:4d} words  -> "
          f"{'PASS' if doc >= fa.ANALYST_DOC_FAIL and mx < fa.ANALYST_RUN_WORDS else 'FAIL'}")
    res[name] = {"doc": doc, "failed": failed.count(True), "windows": len(windows), "runs": len(runs), "max_run": mx}
    ns_windows, ns_failed = windows, failed

# (2) where do the windows that STILL fail after unescape + space-free live? map window -> marker line/page
ref_sp = fa.prepare_output(unescape(marker))
# build a char-offset map from the prepared ref back to marker lines is lossy; use the window's own words
# to locate it in the RAW marker text instead (first 6 words, case-insensitive)
mlines = marker.split("\n")
anchors = [(i, int(m.group(1))) for i, ln in enumerate(mlines) for m in [re.search(r'id="page-(\d+)-', ln)] if m]
import bisect
anchor_lines = [a[0] for a in anchors]
low = marker.lower()
line_starts = [0]
for ln in mlines[:-1]:
    line_starts.append(line_starts[-1] + len(ln) + 1)
buckets = Counter()
pages = Counter()
still = [w for w, f in zip(ns_windows, ns_failed) if f]
located = 0
for w in still:
    key = " ".join(w.split()[:5])
    k = low.find(key)
    if k < 0:
        continue
    located += 1
    line = bisect.bisect_right(line_starts, k) - 1
    buckets[line // 2000 * 2000] += 1
    j = bisect.bisect_right(anchor_lines, line) - 1
    pages[anchors[j][1] // 100 * 100 if j >= 0 else -1] += 1
print(f"\nstill-failing windows after unescape+space-free: {len(still)}; located in the raw Marker text: {located}")
print("by Marker line (2000-line buckets):", sorted(buckets.items())[:20])
print("by span-anchor page (100-page buckets):", sorted(pages.items()))
# the front-matter hypothesis: list-of-figures / list-of-tables entries present in marker vs held
for pat in (r"figure \d+\.\d+", r"table \d+\.\d+"):
    print(f"'{pat}' mentions: marker {len(re.findall(pat, marker.lower()))}  held {len(re.findall(pat, held.lower()))}")
json.dump({"variants": res, "still_failing": len(still), "by_line": dict(buckets), "by_page": dict(pages)},
          open(SP / "univ4e_classify2.json", "w", encoding="utf-8"), indent=1)
