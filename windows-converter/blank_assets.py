# -*- coding: utf-8 -*-
"""blank_assets.py — SYM-053's tripwire, REPORT-ONLY (S188 E7): a bundle's image assets read for BLANK crops.

The defect (S108, Codex's visual pass; Beer p129): Marker selects a blank sub-region of a scan page and omits the hand-drawn
callouts beside it; the body then carries an image reference for that page, so the page LOOKS covered while the diagram's
words are gone — `_page_128_Picture_15.jpeg`, 511×70, grayscale extrema 240/240, standard deviation 0. Page-level asset
presence measures attribution, not survival; only the pixels say the crop is paper.

`scan(assets_dir, body)` opens every image under `assets/` (PIL, converted to grayscale) and names as BLANK any whose
standard deviation over the whole image is under BLANK_SD; for each: the name, size, extrema, std and whether the BODY
references it (a referenced blank is the SYM-053 shape — the page reads as covered). An image PIL cannot open is UNREAD and
listed as such, never counted blank. Counts follow NUM-3: the shown list is capped, the true total rides beside it.

A flag, never a gate: the verdict does not read this key, nothing is stripped, re-cropped or rejected — what a blank crop
DOES (a page flag, a re-crop, the bench) is a design Rab decides. The census that sized it (S188 E7): two distinct blank
assets in ~2,300 across the anchor and held bundles, both referenced.

CLI: `blank_assets.py <bundle_dir> ...` — exit 0 when no referenced blank, 1 when any bundle has one, 2 on usage.
"""
from __future__ import annotations

import os
import sys

# The lever: a crop whose grayscale standard deviation is under this is paper (or one flat tone). The S108 specimen reads
# 0.00; Equity Research's blank first page 0.00; a real crop reads tens. Kept low on purpose — a faint scan with a real
# drawing reads well above 1.0 — and named so the census (lever_census) and a reader can see it is a threshold.
BLANK_SD = 1.0  # lever-waiver: a REPORT-ONLY band's edge (nothing reads it as a gate) — the S108 specimen and Equity's blank page read 0.00, a real crop tens (S188 E7's census over ~2,300 assets); becomes a lever the day a consequence reads it (his gate)
# S189 E2: the second band. A SCANNED blank page is not flat — paper texture and the recto's bleed-through lift its
# standard deviation to 2–3 (DIAGNOSING's three blank versos, 1699×2800, sd 2.33–2.86, looked at by eye), and a page
# whose only content is a few words of text reads under 4 (Automate's dedication page, "For my nephew Jack", sd 3.89 —
# words that live only inside the image). Reported as `near_blank` beside `blank`; BLANK_SD is untouched. A band, not a
# verdict: what either class DOES is his gate.
NEAR_BLANK_SD = 4.0  # lever-waiver: a REPORT-ONLY band's edge (nothing reads it as a gate), set by eye on four specimens S189 E2 (three scanned versos sd 2.33–2.86, a text-only page 3.89) under the census's own bound; moves on a re-measured census, and becomes a lever the day a consequence reads it (his gate)
BLANK_SHOWN_CAP = 25  # lever-waiver: a display cap, NUM-3's shape — the TRUE total (`blank_total`, `near_blank_total`, `unread_total`) rides beside the shown list; it decides how much is printed, never what is counted
IMAGE_EXT = (".jpeg", ".jpg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff")


def _measure(path: str) -> dict:
    """One image's grayscale statistics, or an UNREAD record naming why."""
    try:
        from PIL import Image, ImageStat
    except Exception as exc:  # noqa: BLE001 — no PIL in this interpreter: every image is UNREAD, none blank
        return {"unread": "PIL unavailable: %s" % type(exc).__name__}
    try:
        with Image.open(path) as im:
            g = im.convert("L")
            st = ImageStat.Stat(g)
            lo, hi = st.extrema[0]
            w, h = g.size
            return {"width": w, "height": h, "extrema": [int(lo), int(hi)], "sd": round(float(st.stddev[0]), 3)}
    except Exception as exc:  # noqa: BLE001 — a corrupt or foreign file is UNREAD, not blank
        return {"unread": "%s: %s" % (type(exc).__name__, str(exc)[:80])}


def scan(assets_dir: str, body: str, blank_sd: float = BLANK_SD, near_blank_sd: float = NEAR_BLANK_SD) -> dict:
    """Read every image under `assets_dir`; return the record (a dict LITERAL leaves this function — glass's census reads
    literals, not subscripts). `body` is the markdown the assets are referenced from (the pre-analyst body).
    Two bands: blank (sd < blank_sd — flat paper) and near_blank (blank_sd <= sd < near_blank_sd — a scanned blank page,
    or a page whose only content is a few words); an image is in at most one."""
    names = []
    if assets_dir and os.path.isdir(assets_dir):
        names = sorted(f for f in os.listdir(assets_dir) if f.lower().endswith(IMAGE_EXT))
    blank, near, unread = [], [], []
    read = 0
    for f in names:
        m = _measure(os.path.join(assets_dir, f))
        if "unread" in m:
            unread.append({"name": f, "unread": m["unread"]})
            continue
        read += 1
        rec = {"name": f, "width": m["width"], "height": m["height"], "extrema": m["extrema"], "sd": m["sd"],
               "referenced": bool(body) and f in body}
        if m["sd"] < blank_sd:
            blank.append(rec)
        elif m["sd"] < near_blank_sd:
            near.append(rec)
    referenced = [b for b in blank if b["referenced"]]
    near_referenced = [b for b in near if b["referenced"]]
    return {
        "assets": len(names),
        "read": read,
        "unread": unread[:BLANK_SHOWN_CAP],
        "unread_total": len(unread),
        "blank": blank[:BLANK_SHOWN_CAP],
        "blank_total": len(blank),
        "blank_shown_cap": BLANK_SHOWN_CAP,
        "blank_referenced": len(referenced),
        "blank_sd": blank_sd,
        "near_blank": near[:BLANK_SHOWN_CAP],
        "near_blank_total": len(near),
        "near_blank_referenced": len(near_referenced),
        "near_blank_sd": near_blank_sd,
        "mode": "flag",
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: blank_assets.py <bundle_dir> ...")
        return 2
    red = 0
    for bundle in argv[1:]:
        body = ""
        try:
            for f in os.listdir(bundle):
                if f.endswith(".md") and not f.endswith(".marker.md"):
                    body += open(os.path.join(bundle, f), encoding="utf-8", errors="replace").read()
        except OSError as e:
            print("%s: UNREAD (%s)" % (bundle, e))
            red = 1
            continue
        r = scan(os.path.join(bundle, "assets"), body)
        red = red or (1 if r["blank_referenced"] else 0)
        fmt = lambda rows: "; ".join("%s %dx%d ext %d/%d sd %.2f %s" % (b["name"], b["width"], b["height"], b["extrema"][0], b["extrema"][1], b["sd"],  # noqa: E731
                                                                        "REF" if b["referenced"] else "unref") for b in rows)
        print("%s: assets=%d read=%d unread=%d blank=%d referenced=%d (sd < %s) %s | near-blank=%d referenced=%d (sd < %s) %s" % (
            bundle, r["assets"], r["read"], r["unread_total"], r["blank_total"], r["blank_referenced"], r["blank_sd"], fmt(r["blank"]),
            r["near_blank_total"], r["near_blank_referenced"], r["near_blank_sd"], fmt(r["near_blank"])))
    return red


if __name__ == "__main__":
    sys.exit(main(sys.argv))
