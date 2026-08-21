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

        # ── the vetoes (S104), tested on REAL measured statistics ──────────────────────────
        # Synthetic PDFs were tried first and abandoned: reproducing a textbook sidebar or a
        # flow diagram well enough to exercise the vetoes end-to-end takes a fixture more
        # delicate than the thing under test, and the first two attempts failed for reasons
        # that had nothing to do with vetoing (single-path shapes filtered before the veto ran;
        # then boxes that never clustered because their connectors are ZERO-AREA lines and are
        # dropped before clustering — a real finding about the module, recorded in its header).
        # The discriminator is therefore unit-tested against the numbers actually measured on
        # the corpus, and its end-to-end behaviour is verified by the calibration run in the
        # S104 closeout: p45/p63/p73 (sidebars and framed tables) and p84 (the Du Pont diagram).
        SIDEBAR = {"lines": 32, "mean_words_per_line": 9.25, "text_coverage": 0.731}   # IV p45
        DIAGRAM = {"lines": 29, "mean_words_per_line": 3.38, "text_coverage": 0.050}   # Cyb p84
        TABLE_IN_FRAME = {"lines": 51, "mean_words_per_line": 4.76, "text_coverage": 0.319}  # p63

        check("VETO fires on the measured prose sidebar (IV p45)", fc.is_prose_block(SIDEBAR))
        check("VETO does NOT fire on the measured diagram (Cyb p84) — the true positive lives",
              not fc.is_prose_block(DIAGRAM))
        check("VETO does not mistake a framed TABLE for prose (that is the table veto's job)",
              not fc.is_prose_block(TABLE_IN_FRAME), "p63 is 4.76 words/line: label-shaped")
        check("VETO thresholds keep real margin on both specimens, not tuned to the edge",
              SIDEBAR["text_coverage"] > fc.VETO_TEXT_COVERAGE * 1.5
              and DIAGRAM["text_coverage"] < fc.VETO_TEXT_COVERAGE * 0.5,
              f"threshold={fc.VETO_TEXT_COVERAGE}")
        # the accounted-for veto. CORRECTED S106: this case used to assert on the literals
        # `0.319 + 0.40`, which (a) was arithmetic on constants that invoked NO code under
        # test — S105 Lane B's finding — and (b) used a table fraction of 0.40 that Lane C
        # re-measured at 0.209. It now drives the REAL `_covered_frac` over real rects.
        frame = (100.0, 100.0, 400.0, 400.0)                  # 300x300 = 90,000 pt²
        tab = [(100.0, 100.0, 400.0, 162.7)]                  # 300x62.7 ~= 0.209 of the frame
        frac = fc._covered_frac(frame, tab)
        check("FRAME veto: the real coverage helper reproduces the MEASURED p63 fraction",
              abs(frac - 0.209) < 0.01, f"_covered_frac returned {frac:.3f}, expected ~0.209")
        check("FRAME veto: p63's measured text+table (0.319+0.209) stays BELOW the threshold "
              "— which is why p63 survives, and why this class is unfixed",
              min(1.0, 0.319 + frac) < fc.VETO_ACCOUNTED_FOR,
              f"{0.319 + frac:.3f} vs {fc.VETO_ACCOUNTED_FOR}")
        check("FRAME veto still FIRES when text+table genuinely accounts for the region",
              min(1.0, 0.45 + fc._covered_frac(frame, [(100.0, 100.0, 400.0, 250.0)]))
              >= fc.VETO_ACCOUNTED_FOR)

        # ---- the levers (signed Rab S106; docs/18 §2 modularity law) ----
        # Every case below drives fc.levers() or fc.coverage() for real. None asserts on a
        # literal it just defined — S105 Lane B proved that shape stays green while the guard
        # it claims to test goes red.
        d = fc.levers(text="")["values"]
        check("LEVER: an empty/absent lever file yields the signed DEFAULTS, never a crash",
              d["mode"] == "caption" and d["accounted_for"] == fc.VETO_ACCOUNTED_FOR)
        r = fc.levers(text="accounted_for=0.50\nmode=off\n")
        check("LEVER: an operator's in-range number actually TAKES EFFECT",
              r["values"]["accounted_for"] == 0.50 and r["values"]["mode"] == "off",
              str(r))
        r = fc.levers(text="accounted_for=7.5\n")
        check("LEVER BITES: an out-of-range number is REFUSED, falls back, and is NAMED",
              r["values"]["accounted_for"] == fc.VETO_ACCOUNTED_FOR and r["rejected"],
              f"rejected={r['rejected']}")
        r = fc.levers(text="mode=banana\nwibble=3\nnot a pair\n")
        check("LEVER BITES: bad enum, unknown key and malformed line are each refused and named",
              r["values"]["mode"] == "caption" and len(r["rejected"]) == 3, str(r["rejected"]))

        # ---- the triage: it ORDERS, it must never HIDE ----
        doc = pymupdf.open()
        p1 = doc.new_page()
        p1.insert_image(pymupdf.Rect(100, 100, 300, 300), stream=_png(200, 200))
        p1.insert_text(pymupdf.Point(72, 400), "FIGURE 1.1 A Captioned Thing")
        p2 = doc.new_page()
        p2.insert_image(pymupdf.Rect(100, 100, 300, 300), stream=_png(200, 200, 90))
        tri = tmp / "triage.pdf"
        doc.save(tri); doc.close()
        empty = _bundle(tmp, [], name="tri")             # nothing shipped: both pages uncovered
        on  = fc.coverage(tri, empty, lv=fc.levers(text="mode=caption")["values"])
        off = fc.coverage(tri, empty, lv=fc.levers(text="mode=off")["values"])
        check("TRIAGE: the captioned page is the one promoted to READ FIRST",
              on["uncovered_captioned"] == [1], str(on["uncovered_captioned"]))
        check("TRIAGE BITES: the partition is EXHAUSTIVE — captioned + other == uncovered",
              sorted(on["uncovered_captioned"] + on["uncovered_other"])
              == [d["page"] for d in on["uncovered_detail"]])
        check("TRIAGE CANNOT HIDE: mode=off surfaces exactly as many pages as mode=caption",
              on["pages_uncovered"] == off["pages_uncovered"] == 2
              and off["uncovered_captioned"] == [] and len(off["uncovered_other"]) == 2,
              f"on={on['pages_uncovered']} off={off['pages_uncovered']}")
        check("LEVER: the report states the EFFECTIVE values it ran on, not the defaults",
              fc.coverage(tri, empty, lv=fc.levers(text="accounted_for=0.42")["values"]
                          )["conditions"]["veto_accounted_for"] == 0.42)

        # The ILLUSTRATION precedence. This exact rule was measured but NOT shipped in the
        # first S106 build: the code promoted 16 of 49 pages while the 83 % had been measured
        # on the 8 the precedence leaves. Caught by re-measuring shipped-vs-measured. The case
        # below drives source_figure_regions on a page that names a FIGURE *inside* an
        # ILLUSTRATION worked example — the shape that was wrongly promoted (IV p682, p1111).
        doc = pymupdf.open()
        pg = doc.new_page()
        pg.insert_image(pymupdf.Rect(100, 100, 300, 300), stream=_png(200, 200))
        pg.insert_text(pymupdf.Point(72, 60), "ILLUSTRATION 18.15: Analyzing Value")
        pg.insert_text(pymupdf.Point(72, 400), "as evidenced in FIGURE 18.14 above")
        pg2 = doc.new_page()
        pg2.insert_image(pymupdf.Rect(100, 100, 300, 300), stream=_png(200, 200, 60))
        pg2.insert_text(pymupdf.Point(72, 400), "FIGURE 18.14 A Real Caption")
        prec = tmp / "prec.pdf"
        doc.save(prec); doc.close()
        capt = fc.source_figure_regions(prec)["captioned_pages"]
        check("TRIAGE BITES: an ILLUSTRATION worked example that merely CITES a figure is NOT "
              "promoted, while a genuine caption on the next page is",
              capt == [2], f"captioned_pages={capt}, expected [2]")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"==== figure_coverage selftest: {PASS}/{TOTAL} ====")
    return 0 if PASS == TOTAL else 1


if __name__ == "__main__":
    raise SystemExit(main())
