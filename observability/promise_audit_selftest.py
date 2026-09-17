#!/usr/bin/env python3
"""Tripwires for observability/promise_audit.py (docs/18 §3.7; S189 E3). Hermetic: a planted events file in a temp dir.

  (a) three promised conversions (ratios 0.50, 1.00, 4.00) and one unpromised: the ratios, the median 1.00, within 2x 2 of 3,
      the unpromised listed without a ratio and counted                 (b) the worst two named, the 4.00x first
  (c) --last 2 keeps the newest two only                                 (d) an absent file reads UNREAD, exit 0
  (e) a malformed line is skipped and COUNTED, never a crash             (f) the JSON form carries the same numbers
  (g) NEGATIVE CONTROL: a file with converted events but no promise reads 'no promised conversion', not a ratio of anything
  (h) a non-converted event (convert/slice, analyst/done) is never counted as a conversion
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import promise_audit as pa  # noqa: E402

fired = silent = 0


def check(cond: bool, label: str) -> None:
    global fired, silent
    print(("  ok    " if cond else "  RED   ") + label)
    if cond:
        fired += 1
    else:
        silent += 1


def ev(ts, source, pages, actual, promised=None, basis=None, samples=None, stage="convert", event="converted"):
    d = {"ts": ts, "pid": 1, "stage": stage, "event": event, "source": source, "pages": pages, "s_per_page": actual, "wall_s": round(actual * pages, 1)}
    if promised is not None:
        d.update({"promised_s_per_page": promised, "promised_eta_s": int(promised * pages), "estimate_basis": basis, "estimate_samples": samples})
    return json.dumps(d)


with tempfile.TemporaryDirectory() as td:
    p = os.path.join(td, "events.jsonl")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(ev("2026-09-17T05:00:00+00:00", "first.pdf", 100, 2.0, 1.0, "similar", 3) + "\n")          # ratio 0.50
        f.write(ev("2026-09-17T05:10:00+00:00", "sliceish.pdf", 10, 1.0, stage="convert", event="slice") + "\n")  # not a conversion
        f.write("{this is not json\n")
        f.write(ev("2026-09-17T06:00:00+00:00", "second.pdf", 200, 1.0, 1.0, "similar", 3) + "\n")         # ratio 1.00
        f.write(ev("2026-09-17T07:00:00+00:00", "unpromised.pdf", 50, 3.0) + "\n")                          # no promise
        f.write(ev("2026-09-17T08:00:00+00:00", "third.pdf", 400, 0.5, 2.0, "single-sample", 1) + "\n")    # ratio 4.00
    print("promise_audit — docs/18 §3.7's line")
    rows, bad = pa.read_events(p)
    res = pa.audit(rows)
    ratios = [r["ratio"] for r in res["lines"]]
    check(res["conversions"] == 4 and res["promised"] == 3 and res["unpromised"] == 1 and ratios == [0.5, 1.0, None, 4.0]
          and res["median_ratio"] == 1.0 and res["within_2x"] == 2,
          "(a) three promised (0.50, 1.00, 4.00) + one unpromised: the ratios in order, median 1.00, within 2x 2 of 3, the unpromised without a ratio")
    check([w["ratio"] for w in res["worst"]] == [4.0, 0.5] and res["worst"][0]["source"] == "third.pdf",
          "(b) the worst two named, the 4.00x first (by distance from 1 on the log scale)")
    res2 = pa.audit(rows, last=2)
    check(res2["conversions"] == 2 and [r["source"] for r in res2["lines"]] == ["unpromised.pdf", "third.pdf"] and res2["promised"] == 1,
          "(c) --last 2 keeps the newest two conversions only")
    py = sys.executable
    script = os.path.join(HERE, "promise_audit.py")
    r_abs = subprocess.run([py, script, "--events", os.path.join(td, "nope.jsonl")], capture_output=True, text=True, encoding="utf-8")
    check(r_abs.returncode == 0 and r_abs.stdout.startswith("UNREAD") and "NOT a statement" in r_abs.stdout,
          "(d) an absent file reads UNREAD, exit 0, and says it is not a statement of kept promises")
    check(bad == 1, "(e) the malformed line is skipped and COUNTED (1), never a crash")
    r_json = subprocess.run([py, script, "--events", p, "--json"], capture_output=True, text=True, encoding="utf-8")
    j = json.loads(r_json.stdout)
    check(r_json.returncode == 0 and j["promised"] == 3 and j["median_ratio"] == 1.0 and j["within_2x"] == 2 and j["malformed_skipped"] == 1,
          "(f) the JSON form carries the same numbers and the malformed count")
    r_txt = subprocess.run([py, script, "--events", p], capture_output=True, text=True, encoding="utf-8")
    check(r_txt.returncode == 0 and "median 1.00x" in r_txt.stdout and "within 2x 2 of 3" in r_txt.stdout and "unpromised 1" in r_txt.stdout
          and "1 malformed line(s) skipped" in r_txt.stdout and "no promise (basis none)" in r_txt.stdout,
          "(g') the text form's summary line: median, within 2x, unpromised, malformed; the unpromised row says so")
    q = os.path.join(td, "nopromise.jsonl")
    with io.open(q, "w", encoding="utf-8") as f:
        f.write(ev("2026-09-17T05:00:00+00:00", "a.pdf", 100, 2.0) + "\n")
        f.write(ev("2026-09-17T06:00:00+00:00", "b.pdf", 100, 2.0) + "\n")
    r_np = subprocess.run([py, script, "--events", q], capture_output=True, text=True, encoding="utf-8")
    check(r_np.returncode == 0 and "no promised conversion in the window (2 conversion(s), 2 unpromised)" in r_np.stdout and "ratio" not in r_np.stdout.split("\n")[-2],
          "(g) NEGATIVE CONTROL: conversions without a promise read 'no promised conversion', never a ratio")
    check(all(r["source"] != "sliceish.pdf" for r in res["lines"]),
          "(h) a convert/slice event is not a conversion")
    r_use = subprocess.run([py, script, "--last", "x"], capture_output=True, text=True, encoding="utf-8")
    check(r_use.returncode == 2, "(i) usage (a bad --last) exits 2")
    # (j) the field's own shape: a promise WITH an actual of 0.0 (a run that resumed every slice from cache) is UNMEASURED —
    # neither a ratio nor "no promise" (the first draft said "no promise (basis similar)" on Automate's re-run: a promise it had)
    u = os.path.join(td, "unmeasured.jsonl")
    with io.open(u, "w", encoding="utf-8") as f:
        f.write(ev("2026-09-17T09:24:17+00:00", "resumed.pdf", 675, 0.0, 1.056, "similar", 3) + "\n")
        f.write(ev("2026-09-17T09:30:00+00:00", "fresh.pdf", 100, 1.0, 2.0, "similar", 3) + "\n")
    ru, _ = pa.read_events(u)
    res_u = pa.audit(ru)
    r_ut = subprocess.run([py, script, "--events", u], capture_output=True, text=True, encoding="utf-8")
    check(res_u["unmeasured"] == 1 and res_u["promised"] == 1 and res_u["unpromised"] == 0 and res_u["lines"][0]["class"] == "unmeasured"
          and "ratio UNREAD" in r_ut.stdout and "no promise" not in r_ut.stdout and "unmeasured 1" in r_ut.stdout,
          "(j) a promise with an actual of 0.0 reads UNMEASURED (ratio UNREAD), never 'no promise', and the summary counts it apart")

print("%s (%d/%d)" % ("GREEN" if not silent else "RED", fired, fired + silent))
sys.exit(1 if silent else 0)
