"""Tripwire for figure_coverage.py (P-1). A guard born today gets its tripwire today.

ASCII-only output on purpose: the first draft printed box-drawing characters and CRASHED on
its own summary line under Windows cp1252 -- after all 12 cases had passed. A guard that
reports failure by dying on its success banner is worse than no guard (S102).

Hermetic: every PDF is synthesised with pymupdf in a temp dir, so the suite has no corpus
dependency and can run anywhere, any time, with no GPU and no library. Each case names the
failure it exists to catch — a case that cannot fail is a proxy with a birth certificate.

Run: python windows-converter/figure_coverage_selftest.py
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
import figure_coverage as fc  # noqa: E402

PASS = 0
TOTAL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, TOTAL
    TOTAL += 1
    if ok:
        PASS += 1
        print(f"PASS {TOTAL} - {name}")
    else:
        print(f"FAIL {TOTAL} - {name}" + (f"\n      {detail}" if detail else ""))


def _png(w: int, h: int, colour: int = 200) -> bytes:
    """A real raster, not a stub — get_image_info only reports images it can decode."""
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, w, h), False)
    pix.set_rect(pix.irect, (colour, colour - 40, 90))
    return pix.tobytes("png")


def _bundle(tmp: Path, pages_with_assets: list[int], name: str = "b") -> Path:
    """A bundle shaped exactly like a real one: assets/ named with 0-INDEXED pages."""
    d = tmp / name
    (d / "assets").mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(pages_with_assets):
        (d / "assets" / f"_page_{p}_Figure_{i}.jpeg").write_bytes(b"jpegbytes")
    return d


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="fp-p1-"))
    try:
        # 1 — a genuine raster figure is found
        doc = pymupdf.open()
        pg = doc.new_page()
        pg.insert_image(pymupdf.Rect(100, 100, 300, 300), stream=_png(200, 200))
        doc.save(tmp / "raster.pdf")
        doc.close()
        src = fc.source_figure_regions(tmp / "raster.pdf")
        check("a 200x200pt raster is detected as a figure region",
              1 in src["pages"] and any(r["kind"] == "raster" for r in src["pages"][1]),
              f"got {src['pages']}")

        # 2 — a VECTOR chart is found: the blind spot every raster enumerator misses
        doc = pymupdf.open()
        pg = doc.new_page()
        for i in range(12):
            pg.draw_rect(pymupdf.Rect(100 + i * 12, 400 - i * 9, 108 + i * 12, 400),
                         color=(0, 0, 0), fill=(0.2, 0.4, 0.8))
        doc.save(tmp / "vector.pdf")
        doc.close()
        src = fc.source_figure_regions(tmp / "vector.pdf")
        check("a 12-bar VECTOR chart with ZERO image objects is detected",
              1 in src["pages"] and any(r["kind"] == "vector" for r in src["pages"][1]),
              f"got {src['pages']}")

        # 3 — a thin rule is NOT a figure (the false-positive class that would flood the report)
        doc = pymupdf.open()
        pg = doc.new_page()
        for y in (200, 220, 240, 260):
            pg.draw_line(pymupdf.Point(72, y), pymupdf.Point(520, y), color=(0, 0, 0))
        doc.save(tmp / "rules.pdf")
        doc.close()
        src = fc.source_figure_regions(tmp / "rules.pdf")
        check("horizontal rules/underlines are NOT figures (min-side filter bites)",
              src["pages"] == {}, f"got {src['pages']}")

        # 4 — a full-page image is the SCAN ITSELF, not a figure (else every scan page flags)
        doc = pymupdf.open()
        pg = doc.new_page()
        pg.insert_image(pg.rect, stream=_png(600, 800))
        doc.save(tmp / "scan.pdf")
        doc.close()
        src = fc.source_figure_regions(tmp / "scan.pdf")
        check("a full-page image is excluded (it is the scan, not a figure)",
              src["pages"] == {}, f"got {src['pages']}")

        # 5 — a logo repeated on every page is furniture, dropped
        doc = pymupdf.open()
        logo = _png(120, 120, 180)
        for _ in range(20):
            p = doc.new_page()
            p.insert_image(pymupdf.Rect(40, 40, 160, 160), stream=logo)
        doc.save(tmp / "logo.pdf")
        doc.close()
        src = fc.source_figure_regions(tmp / "logo.pdf")
        check("a logo on all 20 pages is furniture, not 20 figures",
              src["pages"] == {} and src["furniture_digests"] >= 1,
              f"pages={len(src['pages'])} furniture={src['furniture_digests']}")

        # 6 — the actual coverage question, both answers
        doc = pymupdf.open()
        for i in range(3):
            p = doc.new_page()
            if i in (0, 2):
                p.insert_image(pymupdf.Rect(100, 100, 300, 300), stream=_png(200, 200, 120 + i * 40))
        doc.save(tmp / "cov.pdf")
        doc.close()
        # assets on 0-indexed pages 0 and 2 => 1-based 1 and 3 => both figure pages covered
        rep = fc.coverage(tmp / "cov.pdf", _bundle(tmp, [0, 2], "covered"))
        check("covered: assets on both figure pages -> 0 uncovered, coverage 1.0",
              rep["pages_uncovered"] == 0 and rep["coverage"] == 1.0,
              f"{rep['pages_with_source_figures']} figpp, {rep['pages_uncovered']} uncov")
        rep2 = fc.coverage(tmp / "cov.pdf", _bundle(tmp, [0], "partial"))
        check("UNCOVERED: page 3 has a figure and no asset -> flagged with its page",
              rep2["pages_uncovered"] == 1 and rep2["uncovered_detail"][0]["page"] == 3,
              f"uncov={rep2['pages_uncovered']} detail={rep2['uncovered_detail']}")

        # 7 — the 0-indexed/1-based namespace seam, stated explicitly
        check("asset _page_0_ maps to source page 1 (three namespaces coexist; +1 is real)",
              fc.output_asset_pages(_bundle(tmp, [0], "ns"))["per_page"] == {1: 1})

        # 8 — pre-S60 doubled-offset bundles are NAMED, never silently averaged
        rep3 = fc.coverage(tmp / "cov.pdf", _bundle(tmp, [0, 2, 40], "offset"))
        check("assets beyond the page count are reported as out-of-range (poisoned bundle)",
              rep3["assets_out_of_range"] == [41], f"got {rep3['assets_out_of_range']}")

        # 9 — the module NEVER emits a verdict (report-only is doctrine, docs/15 §6)
        check("the report carries no verdict/flag key — report-only by construction",
              not any(k in rep for k in ("verdict", "flag", "flagged", "fail")),
              f"keys: {sorted(rep)}")

        # 10 — an empty bundle does not crash and reports total loss honestly
        empty = tmp / "empty"
        (empty / "assets").mkdir(parents=True)
        rep4 = fc.coverage(tmp / "cov.pdf", empty)
        check("a bundle with zero assets reports every figure page uncovered, coverage 0.0",
              rep4["pages_uncovered"] == 2 and rep4["coverage"] == 0.0,
              f"{rep4['pages_uncovered']} uncov, cov={rep4['coverage']}")

        # 11 — a PDF with no figures at all yields coverage None, never a fake 1.0
        doc = pymupdf.open()
        doc.new_page().insert_text(pymupdf.Point(72, 100), "text only")
        doc.save(tmp / "textonly.pdf")
        doc.close()
        rep5 = fc.coverage(tmp / "textonly.pdf", _bundle(tmp, [], "none"))
        check("no source figures -> coverage None (a ratio with no denominator is not 1.0)",
              rep5["coverage"] is None and rep5["pages_with_source_figures"] == 0,
              f"cov={rep5['coverage']}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"==== figure_coverage selftest: {PASS}/{TOTAL} ====")
    return 0 if PASS == TOTAL else 1


if __name__ == "__main__":
    raise SystemExit(main())
