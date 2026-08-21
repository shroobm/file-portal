"""P-1 — figure coverage: did the figures on each source page reach the output?

docs/41 §2 P-1, signed by Rab 2026-08-20 ("lets do items 6-9" / "lets do P-1"). Built S102.

WHAT THIS ANSWERS, precisely
    For every page of the source PDF that bears at least one figure-like region, does the
    converted bundle contain at least one figure asset attributed to that page?
    Numerator: source pages bearing >=1 figure region that have 0 output assets on that page.
    Denominator: source pages bearing >=1 figure region.
    Conditions: named per run in the report (pymupdf version, thresholds, bundle, lane).

WHAT IT DOES NOT ANSWER, and why
    docs/41 specified coverage by BBOX OVERLAP — "does each source figure region have some
    output image whose bbox overlaps it". That is not computable on this stack, measured S102:
    a shipped bundle is `<name>.md` + `assets/` + `manifest.json`, and marker's markdown-mode
    `_meta.json` carries only `table_of_contents` + `page_stats` (renderers/__init__.py:117)
    — no block bboxes anywhere. Output bboxes exist only under a different output format or
    the Python API, i.e. a converter rewrite. So coverage here is PER PAGE, which is the
    honest buildable unit, and a page with three source figures and one output asset counts
    as COVERED. That is a real ceiling on sensitivity and is printed in every report.

WHY COUNTS ARE NOT COVERAGE (the trap this instrument exists to avoid)
    The existing `asset_delta` compares two different KINDS of object: files marker wrote by
    cropping the rendered page, versus image XObjects in the source. A 465-page scan reads
    -416 because OCR worked; a vector-figure book reads +92 against ZERO XObjects. Neither is
    figure loss. This module never compares counts: it asks a per-page presence question, and
    it treats vector drawings as first-class figures because on this corpus they are the
    common case (Cybernetics: 0 raster XObjects, 92 figures).

REPORT-ONLY BY DOCTRINE
    docs/15 §6: all thresholds ship report-only until calibrated; §9 step 3: the tool must show
    its false alarms verbatim before it may pulse terracotta. This module returns a report and
    NOTHING ELSE. It writes no manifest key, sets no verdict, and is deliberately not wired
    into convert_and_ship.py — placement is Rab's open decision (docs/41 §2 P-1, variable 4).

CPU-only. Never touches the GPU; safe to run beside a conversion.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pymupdf

# ── thresholds, all in POINTS (72/inch), all named in the report ───────────────
# A "figure region" must be big enough to be a figure a reader would miss. These are first
# guesses, deliberately conservative, and CALIBRATION (docs/15 §9) is what earns them.
MIN_AREA_PT2 = 4900.0  # 70x70pt ~= 1x1 inch. Smaller marks are bullets, glyph art, rules.
MIN_SIDE_PT = 40.0  # a figure is not 3pt tall; kills rules, underlines, table borders
MAX_PAGE_FRACTION = 0.92  # a region covering ~the whole page is the SCAN ITSELF, not a figure
VECTOR_MIN_PATHS = 4  # a cluster needs real drawing activity, not one stray line
VECTOR_CLUSTER_GAP_PT = 18.0  # paths closer than this merge into one figure region

_ASSET_RE = re.compile(r"_page_(\d+)_(Figure|Picture)_(\d+)\.(?:jpe?g|png)$", re.I)


def _rect_area(r) -> float:
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _merge(a, b):
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _touches(a, b, gap: float) -> bool:
    return not (
        a[2] + gap < b[0] or b[2] + gap < a[0] or a[3] + gap < b[1] or b[3] + gap < a[1]
    )


def _cluster(rects, gap: float):
    """Greedy transitive merge — order-independent because it repeats to a fixed point."""
    boxes = [(r, 1) for r in rects]
    changed = True
    while changed:
        changed = False
        out = []
        for box, n in boxes:
            for i, (other, m) in enumerate(out):
                if _touches(box, other, gap):
                    out[i] = (_merge(box, other), m + n)
                    changed = True
                    break
            else:
                out.append((box, n))
        boxes = out
    return boxes


def source_figure_regions(pdf_path: Path, use_hashes: bool = True) -> dict:
    """Per 1-based page: the figure-like regions, raster and vector, with why each qualified.

    Rasters come from `get_image_info(hashes=...)` — DISPLAYED images including inline ones,
    with a bbox and an md5 digest. The digest collapses the repeated-header-logo case that a
    bare count gets wrong. `xrefs=True` is deliberately NOT requested (see the timing note in
    the loop: it costs 34.6 s/page on a large scan).
    Vectors come from `get_drawings()` clustered by proximity: a chart drawn with path
    operators has no image object at all and is invisible to every raster enumerator.
    """
    doc = pymupdf.open(pdf_path)
    pages: dict[int, list] = {}
    digest_pages: dict[str, set] = {}
    try:
        for pno in range(doc.page_count):
            page = doc[pno]
            parea = _rect_area(tuple(page.rect))
            regions = []

            # `xrefs=True` IS OMITTED, and that one flag is the whole performance story.
            # Measured S102 on DIAGNOSING (184pp scan, 12.5-megapixel pages), fresh document
            # per case so no warm cache could lie:
            #     plain          0.00 s/page
            #     hashes=True    0.16 s/page
            #     xrefs=True    34.60 s/page   <-- ~104 min for this one book
            #     both          34.96 s/page
            # MuPDF resolves each displayed image back through the xref table, and on a large
            # scanned PDF that search dominates everything else by four orders of magnitude.
            # It burned 28 CPU-minutes before Rab noticed the machine was busy.
            # RECORDED HONESTLY: the first diagnosis blamed `hashes=True` and was WRONG -- the
            # measurement that produced it timed the flags in one process, where the earlier
            # call had already warmed MuPDF's cache and made hashing look free. Fresh-document
            # timing reversed the verdict. We keep hashes (md5 is the correct furniture-dedup
            # identity and costs 0.16 s/page) and drop xrefs, which nothing here needed.
            # Two-pass, cheapest-first. The PLAIN call is free (0.00 s/page) and gives the
            # bboxes; hashing is only worth paying for if some image actually SURVIVES the
            # size filters and could therefore need furniture-dedup. On a scan every image is
            # full-page and is dropped as "the scan itself", so the hash was computed and
            # thrown away 184 times -- that is the 191 ms/page this avoids.
            probe = page.get_image_info()
            candidate = any(
                _rect_area(tuple(i.get("bbox") or (0, 0, 0, 0))) >= MIN_AREA_PT2
                and min(
                    (i.get("bbox") or (0, 0, 0, 0))[2] - (i.get("bbox") or (0, 0, 0, 0))[0],
                    (i.get("bbox") or (0, 0, 0, 0))[3] - (i.get("bbox") or (0, 0, 0, 0))[1],
                ) >= MIN_SIDE_PT
                and not (parea and _rect_area(tuple(i.get("bbox") or (0, 0, 0, 0))) / parea > MAX_PAGE_FRACTION)
                for i in probe
            )
            infos = page.get_image_info(hashes=True) if (use_hashes and candidate) else probe
            for info in infos:
                bbox = tuple(info.get("bbox") or (0, 0, 0, 0))
                area = _rect_area(bbox)
                if area < MIN_AREA_PT2:
                    continue
                if min(bbox[2] - bbox[0], bbox[3] - bbox[1]) < MIN_SIDE_PT:
                    continue
                if parea and area / parea > MAX_PAGE_FRACTION:
                    continue  # full-page image = the scan itself
                digest = (info.get("digest") or b"").hex() if info.get("digest") else ""
                # Identity key for furniture-dedup: the md5 when hashing was paid for,
                # otherwise the xref. Both answer "is this the SAME image again?".
                ident = digest or (f"xref:{info.get('xref')}" if info.get("xref") else "")
                regions.append({"kind": "raster", "bbox": [round(v, 1) for v in bbox],
                                "area": round(area, 1), "digest": digest,
                                "ident": ident, "xref": info.get("xref")})
                if ident:
                    digest_pages.setdefault(ident, set()).add(pno + 1)

            rects = []
            for d in page.get_drawings():
                r = tuple(d.get("rect") or (0, 0, 0, 0))
                if _rect_area(r) <= 0:
                    continue
                rects.append(r)
            for bbox, npaths in _cluster(rects, VECTOR_CLUSTER_GAP_PT):
                area = _rect_area(bbox)
                if npaths < VECTOR_MIN_PATHS or area < MIN_AREA_PT2:
                    continue
                if min(bbox[2] - bbox[0], bbox[3] - bbox[1]) < MIN_SIDE_PT:
                    continue
                if parea and area / parea > MAX_PAGE_FRACTION:
                    continue
                regions.append({"kind": "vector", "bbox": [round(v, 1) for v in bbox],
                                "area": round(area, 1), "paths": npaths})

            if regions:
                pages[pno + 1] = regions
        n_pages = doc.page_count
    finally:
        doc.close()

    # A raster repeated on many pages is furniture (a header logo), not a figure per page.
    # Drop any digest appearing on more than a quarter of the pages that carry figures.
    if pages:
        limit = max(3, int(0.25 * n_pages))
        furniture = {d for d, ps in digest_pages.items() if len(ps) > limit}
        if furniture:
            for pno in list(pages):
                kept = [r for r in pages[pno] if r.get("ident") not in furniture]
                if kept:
                    pages[pno] = kept
                else:
                    del pages[pno]
    return {"pages": pages, "page_count": n_pages,
            "furniture_digests": len(
                {d for d, ps in digest_pages.items() if len(ps) > max(3, int(0.25 * n_pages))}
            )}


def output_asset_pages(bundle_dir: Path) -> dict:
    """Per 1-based page: how many figure assets the bundle attributes to it.

    Marker names assets `_page_{page_id}_{BlockType}_{block_id}.jpeg` and `page_id` is
    ZERO-INDEXED, while audit pages and chunk seams are 1-based — three namespaces coexist in
    one manifest, so the +1 here is load-bearing, not cosmetic (docs/41 Appendix A §A5).
    """
    assets = bundle_dir / "assets"
    per_page: dict[int, int] = {}
    unparsed = []
    if assets.is_dir():
        for f in sorted(assets.iterdir()):
            m = _ASSET_RE.search(f.name)
            if not m:
                unparsed.append(f.name)
                continue
            per_page[int(m.group(1)) + 1] = per_page.get(int(m.group(1)) + 1, 0) + 1
    return {"per_page": per_page, "unparsed": unparsed}


def coverage(pdf_path: Path, bundle_dir: Path, use_hashes: bool = True) -> dict:
    src = source_figure_regions(pdf_path, use_hashes=use_hashes)
    out = output_asset_pages(bundle_dir)
    figure_pages = sorted(src["pages"])
    uncovered = [p for p in figure_pages if out["per_page"].get(p, 0) == 0]

    # Assets attributed to a page beyond the source's page count are the doubled-offset
    # signature of pre-S60 bundles (assets numbered to _page_2553_ on a 1,356-page book).
    # A report computed against those is poisoned, so it is named rather than averaged in.
    out_of_range = sorted(p for p in out["per_page"] if p > src["page_count"])

    detail = []
    for p in uncovered:
        regions = src["pages"][p]
        detail.append({
            "page": p,
            "regions": len(regions),
            "kinds": sorted({r["kind"] for r in regions}),
            "largest_area_pt2": round(max(r["area"] for r in regions), 1),
            "bboxes": [r["bbox"] for r in regions[:4]],
        })
    return {
        "bundle": bundle_dir.name,
        "source": pdf_path.name,
        "pages_total": src["page_count"],
        "pages_with_source_figures": len(figure_pages),
        "pages_uncovered": len(uncovered),
        "coverage": (
            round(1 - len(uncovered) / len(figure_pages), 4) if figure_pages else None
        ),
        "output_asset_pages": len(out["per_page"]),
        "output_assets_total": sum(out["per_page"].values()),
        "assets_out_of_range": out_of_range,
        "unparsed_asset_names": out["unparsed"][:5],
        "furniture_digests_dropped": src["furniture_digests"],
        "uncovered_detail": detail,
        "conditions": {
            "unit": "PER PAGE — a page with N source figures and >=1 output asset counts as "
                    "covered; bbox-overlap is not computable from a bundle (see module head)",
            "pymupdf": pymupdf.__doc__.strip() if pymupdf.__doc__ else pymupdf.version[0],
            "min_area_pt2": MIN_AREA_PT2,
            "min_side_pt": MIN_SIDE_PT,
            "max_page_fraction": MAX_PAGE_FRACTION,
            "vector_min_paths": VECTOR_MIN_PATHS,
            "vector_cluster_gap_pt": VECTOR_CLUSTER_GAP_PT,
            "image_identity": "md5" if use_hashes else "none (furniture-dedup disabled)",
            "verdict_effect": "NONE — report-only by docs/15 §6; writes nothing",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="P-1 figure coverage (report-only, CPU-only)")
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--bundle", required=True, type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-hashes", action="store_true",
                    help="skip md5 furniture-dedup (saves ~0.16 s/page; the expensive flag was "
                         "never hashing -- see the module comment on xrefs)")
    a = ap.parse_args()
    if not a.pdf.exists():
        print(f"no such pdf: {a.pdf}", file=sys.stderr)
        return 2
    if not a.bundle.is_dir():
        print(f"no such bundle dir: {a.bundle}", file=sys.stderr)
        return 2
    rep = coverage(a.pdf, a.bundle, use_hashes=not a.no_hashes)
    if a.json:
        print(json.dumps(rep, indent=1))
    else:
        print(f"{rep['bundle']}")
        print(f"  pages {rep['pages_total']} · with source figures "
              f"{rep['pages_with_source_figures']} · UNCOVERED {rep['pages_uncovered']} "
              f"· coverage {rep['coverage']}")
        if rep["assets_out_of_range"]:
            print(f"  ! assets attributed beyond page count: {rep['assets_out_of_range'][:6]}"
                  " — pre-S60 doubled-offset bundle, report not trustworthy")
        for d in rep["uncovered_detail"][:12]:
            print(f"    p{d['page']:>4}  {d['regions']} region(s) {','.join(d['kinds'])}"
                  f"  largest {d['largest_area_pt2']}pt²")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
