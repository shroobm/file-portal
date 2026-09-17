#!/usr/bin/env python3
"""promise_audit.py — the promise-vs-actual line docs/18 §3.7 said was never filed (S189 E3; warn-only).

Every `convert/converted` event has carried the estimator's PROMISE beside the ACTUAL since OK-17 (`promised_s_per_page`,
`promised_eta_s`, `estimate_basis`, `estimate_samples` next to `s_per_page`, `wall_s`, `pages`). Nothing read them back at a
close; S188 E1 read them by hand once and found five of six of a day's promises outside 2×. This reads them every time.

  promise_audit.py [--events <events.jsonl>] [--last N] [--json]

Per promised conversion (newest last): the source, pages, promised vs actual s/page, the RATIO promise ÷ actual (2.0 = the
Dock promised twice the real time; 0.5 = half), the basis and its sample count. A conversion that carried no promise is
listed as `no promise` and never given a ratio (basis none is an honest absence, not a miss). The summary follows docs/34:
n, the median ratio, the share within 2× (0.5 ≤ ratio ≤ 2.0), the two worst named. The events file absent or unreadable
→ UNREAD, exit 0; a malformed line is skipped and COUNTED. A reading, never a gate: the exit code is 0 on every path but
usage (2).
"""
from __future__ import annotations

import argparse
import io
import json
import os
import statistics
import sys

DEFAULT_EVENTS = os.path.join(os.path.expanduser("~"), "ml", "library", "events.jsonl")


def read_events(path: str) -> tuple[list[dict], int]:
    """Every `convert/converted` event in file order, and the count of malformed lines skipped."""
    rows, bad = [], 0
    with io.open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                bad += 1
                continue
            if ev.get("stage") == "convert" and ev.get("event") == "converted":
                rows.append(ev)
    return rows, bad


def audit(rows: list[dict], last: int | None = None) -> dict:
    """The per-conversion lines and the summary; a dict LITERAL leaves the function (glass's census reads literals)."""
    if last:
        rows = rows[-last:]
    lines, ratios = [], []
    for ev in rows:
        actual = ev.get("s_per_page")
        promised = ev.get("promised_s_per_page")
        rec = {
            "ts": (ev.get("ts") or "")[:19],
            "source": (ev.get("source") or "")[:48],
            "pages": ev.get("pages"),
            "actual_s_per_page": actual,
            "promised_s_per_page": promised,
            "basis": ev.get("estimate_basis"),
            "samples": ev.get("estimate_samples"),
            "ratio": None,
            # "promised" (a ratio), "unpromised" (no promise was made), or "unmeasured" (a promise was made but the actual
            # s/page is 0 or absent — a run that resumed every slice from cache spends no wall on them; the field's own
            # Automate re-run read 0.0 and the first draft called it "no promise", which it was not)
            "class": "unpromised",
        }
        if promised is not None:
            rec["class"] = "unmeasured"
            try:
                if actual is not None and float(actual) > 0:
                    rec["ratio"] = round(float(promised) / float(actual), 2)
                    rec["class"] = "promised"
                    ratios.append((rec["ratio"], rec["source"]))
            except (TypeError, ValueError):
                rec["ratio"] = None
        lines.append(rec)
    within = [r for r, _ in ratios if 0.5 <= r <= 2.0]
    worst = sorted(ratios, key=lambda t: abs(__import__("math").log(t[0])) if t[0] > 0 else 0, reverse=True)[:2]
    unmeasured = sum(1 for r in lines if r["class"] == "unmeasured")
    return {
        "conversions": len(lines),
        "promised": len(ratios),
        "unpromised": len(lines) - len(ratios) - unmeasured,
        "unmeasured": unmeasured,
        "median_ratio": round(statistics.median([r for r, _ in ratios]), 2) if ratios else None,
        "within_2x": len(within),
        "worst": [{"ratio": r, "source": s} for r, s in worst],
        "lines": lines,
    }


def summary_line(a: dict, bad: int = 0) -> str:
    unm = (" · unmeasured %d (a promise, no actual — resumed runs)" % a["unmeasured"]) if a.get("unmeasured") else ""
    if a["promised"] == 0:
        return "no promised conversion in the window (%d conversion(s), %d unpromised)%s%s" % (
            a["conversions"], a["unpromised"], unm, (" · %d malformed line(s) skipped" % bad) if bad else "")
    worst = " · worst " + ", ".join("%.2fx %s" % (w["ratio"], w["source"][:28]) for w in a["worst"]) if a["worst"] else ""
    return "promise/actual over the last %d promised conversion(s): median %.2fx · within 2x %d of %d · unpromised %d%s%s%s" % (
        a["promised"], a["median_ratio"], a["within_2x"], a["promised"], a["unpromised"], unm, worst,
        (" · %d malformed line(s) skipped" % bad) if bad else "")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="promise vs actual over the converted events (warn-only)")
    ap.add_argument("--events", default=DEFAULT_EVENTS)
    ap.add_argument("--last", type=int, default=None, help="only the newest N converted events")
    ap.add_argument("--json", action="store_true")
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        return 2
    if not os.path.isfile(a.events):
        print("UNREAD — no events file at %s; NOT a statement that the promises were kept" % a.events)
        return 0
    try:
        rows, bad = read_events(a.events)
    except OSError as e:
        print("UNREAD — events file unreadable (%s); NOT a statement that the promises were kept" % e)
        return 0
    res = audit(rows, a.last)
    if a.json:
        res["malformed_skipped"] = bad
        print(json.dumps(res, indent=1))
        return 0
    for rec in res["lines"]:
        if rec["class"] == "unpromised":
            print("  %s %5s pp  actual %-7s  no promise (basis %s)  %s" % (rec["ts"], rec["pages"], rec["actual_s_per_page"], rec["basis"] or "none", rec["source"]))
        elif rec["class"] == "unmeasured":
            print("  %s %5s pp  actual %-7s promised %-7s ratio UNREAD (no actual — a resumed run?)  %s ×%s  %s" % (
                rec["ts"], rec["pages"], rec["actual_s_per_page"], rec["promised_s_per_page"], rec["basis"], rec["samples"], rec["source"]))
        else:
            print("  %s %5s pp  actual %-7s promised %-7s ratio %5.2fx  %s ×%s  %s" % (
                rec["ts"], rec["pages"], rec["actual_s_per_page"], rec["promised_s_per_page"], rec["ratio"], rec["basis"], rec["samples"], rec["source"]))
    print(summary_line(res, bad))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
