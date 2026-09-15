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

import json
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

        # 8b — A18's repair must bite end to end, not merely have the formula in source. Build
        # a 401-page, slice-size-200 specimen with the only figure on true page 301. The old
        # converter would file its zero-based asset id 300 as 500; naive page 501 is out of
        # range and misses the figure, while the signed inverse maps it back to page 301.
        doc = pymupdf.open()
        for page_index in range(401):
            pg = doc.new_page()
            if page_index == 300:
                pg.insert_image(pymupdf.Rect(100, 100, 300, 300), stream=_png(200, 200, 110))
        poison_pdf = tmp / "sym050.pdf"
        doc.save(poison_pdf)
        doc.close()
        poison_bundle = _bundle(tmp, [500], "sym050")
        (poison_bundle / "manifest.json").write_text(
            json.dumps({"chunking": {"slice_size": 200}}), encoding="utf-8"
        )
        repaired = fc.coverage(poison_pdf, poison_bundle)
        check("SYM-050 REPAIR BITES: naive page 501 maps to true page 301 and covers it",
              repaired["page_map"] == "REPAIRED (SYM-050 doubled-offset)"
              and repaired["pages_uncovered"] == 0
              and repaired["sym050_doubled_offset"]["unrepaired"]["pages_uncovered"] == 1
              and repaired["sym050_doubled_offset"]["assets_out_of_range_after_repair"] == [],
              str(repaired["sym050_doubled_offset"]))
        check("SYM-050 scope refuses a different slice size and a mixed odd band",
              not fc.sym050_signature({501: 1}, 401, slice_size=100)
              and not fc.sym050_signature({501: 1, 601: 1}, 401, slice_size=200))

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
        # S157 E18 (B14): the two filters that could null a min_area_pt2 change are levers now, at the old constants
        d18 = fc.levers(text="")["values"]
        check("B14: min_side_pt and max_page_fraction are levers whose defaults are the old constants (nothing moves unwritten)",
              d18["min_side_pt"] == 40.0 and d18["max_page_fraction"] == 0.92, str(d18))
        r18 = fc.levers(text="min_side_pt=12\nmax_page_fraction=0.5\n")
        check("B14: an operator's in-range side and fraction take effect", r18["values"]["min_side_pt"] == 12.0 and r18["values"]["max_page_fraction"] == 0.5 and r18["rejected"] == [], str(r18))
        r18b = fc.levers(text="min_side_pt=0\nmax_page_fraction=3\n")
        check("B14 BITES: an out-of-range side or fraction is refused, named, and the default stands",
              r18b["values"]["min_side_pt"] == 40.0 and r18b["values"]["max_page_fraction"] == 0.92 and len(r18b["rejected"]) == 2, str(r18b))
        # the count the ticket asked for: a lever change admitted by area and killed by the side is VISIBLE in the report
        rules_pdf = tmp / "rules18.pdf"
        doc18 = pymupdf.open()
        pg18 = doc18.new_page(width=600, height=800)
        for k in range(6):
            pg18.draw_rect(pymupdf.Rect(60, 100 + 60 * k, 540, 108 + 60 * k), fill=(0, 0, 0))   # 480x8pt bars: area 3,840 each
        doc18.save(rules_pdf)
        doc18.close()
        loose = fc.source_figure_regions(rules_pdf, lv=fc.levers(text="min_area_pt2=100\nvector_min_paths=1\n")["values"])
        check("B14: at min_area_pt2=100 the bars pass the area filter and die on min_side_pt — the report COUNTS them",
              loose["filters_killed"]["vector"]["min_side_pt"] >= 1 and not loose["pages"], str(loose["filters_killed"]))
        strict = fc.source_figure_regions(rules_pdf, lv=fc.levers(text="")["values"])
        check("B14 negative control: under the defaults the same bars die on area first, min_side_pt kills none",
              strict["filters_killed"]["vector"]["min_side_pt"] == 0 and strict["filters_killed"]["vector"]["min_paths_or_area"] >= 1, str(strict["filters_killed"]))
        rep18 = fc.coverage(rules_pdf, _bundle(tmp, [], "b18"), lv=fc.levers(text="min_area_pt2=100\nvector_min_paths=1\n")["values"])
        check("B14: the report's conditions carry filters_killed and the EFFECTIVE side/fraction",
              rep18["conditions"]["filters_killed"]["vector"]["min_side_pt"] >= 1 and rep18["conditions"]["min_side_pt"] == 40.0, str(rep18["conditions"].get("filters_killed")))
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
        doc.save(tri)
        doc.close()
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
        doc.save(prec)
        doc.close()
        capt = fc.source_figure_regions(prec)["captioned_pages"]
        check("TRIAGE BITES: an ILLUSTRATION worked example that merely CITES a figure is NOT "
              "promoted, while a genuine caption on the next page is",
              capt == [2], f"captioned_pages={capt}, expected [2]")

        # ── S157 E25 (SYM-049): zero-area paths clustered when ANCHORED; the table veto disqualified by curves ──
        # The S104 note above records why the first synthetic diagram never clustered: its connectors were zero-area
        # lines and were dropped. That drop is the SYM-049 mechanism (Cyb p.34, p.78 measured lost at S105). The
        # fixtures below are the S105 specimens' SHAPES, not their bytes; the corpus measure is the E25 record.
        def _grid(pg, x0=100, y0=100, cols=4, rows=5, w=90, h=30):
            for i in range(cols + 1):
                pg.draw_line(pymupdf.Point(x0 + i * w, y0), pymupdf.Point(x0 + i * w, y0 + rows * h), color=(0, 0, 0))
            for j in range(rows + 1):
                pg.draw_line(pymupdf.Point(x0, y0 + j * h), pymupdf.Point(x0 + cols * w, y0 + j * h), color=(0, 0, 0))
            for i in range(cols):
                for j in range(rows):
                    pg.insert_text(pymupdf.Point(x0 + i * w + 6, y0 + j * h + 20), "c%d%d" % (i, j), fontsize=9)

        # 37 — Cyb p.78's shape: two boxes joined by two connector lines. Dropped lines = two 1-path clusters = silence.
        doc = pymupdf.open()
        pg = doc.new_page()
        pg.draw_rect(pymupdf.Rect(100, 100, 150, 150), color=(0, 0, 0))
        pg.draw_rect(pymupdf.Rect(400, 100, 450, 150), color=(0, 0, 0))
        pg.draw_line(pymupdf.Point(150, 115), pymupdf.Point(400, 115), color=(0, 0, 0))
        pg.draw_line(pymupdf.Point(150, 135), pymupdf.Point(400, 135), color=(0, 0, 0))
        p78 = tmp / "p78shape.pdf"
        doc.save(p78)
        doc.close()
        s78 = fc.source_figure_regions(p78)
        check("SYM-049: two boxes joined by zero-area connector lines cluster into ONE vector region (p.78's shape)",
              1 in s78["pages"] and [r["paths"] for r in s78["pages"][1]] == [4] and s78["zero_area_paths_clustered"] == 2,
              f"pages={s78['pages']} clustered={s78['zero_area_paths_clustered']}")
        s78off = fc.source_figure_regions(p78, lv=fc.levers(text="zero_area_min_len_pt=100000")["values"])
        check("SYM-049 NEGATIVE CONTROL: with no line ever admitted (the lever at its ceiling) the S104 silence returns",
              s78off["pages"] == {} and s78off["zero_area_paths_clustered"] == 0, f"pages={s78off['pages']}")

        # 38 — the flood guard: six parallel rules 10 pt apart (a ruled block 448x50) touch nothing and stay OUT
        doc = pymupdf.open()
        pg = doc.new_page()
        for k in range(6):
            pg.draw_line(pymupdf.Point(72, 200 + 10 * k), pymupdf.Point(520, 200 + 10 * k), color=(0, 0, 0))
        ruled = tmp / "ruled.pdf"
        doc.save(ruled)
        doc.close()
        sr = fc.source_figure_regions(ruled)
        check("SYM-049 flood guard: a stack of parallel rules with nothing else near them is NOT clustered (unanchored)",
              sr["pages"] == {} and sr["zero_area_paths_clustered"] == 0, f"pages={sr['pages']} clustered={sr['zero_area_paths_clustered']}")

        # 39 — a ruled TABLE drawn with lines only: its lines anchor each other (perpendiculars), it clusters, and the
        # table veto — still allowed, the cluster is rectilinear — removes it. The S104 report was silent by accident
        # (the lines never clustered); it is silent by the veto now, and the report says which.
        doc = pymupdf.open()
        pg = doc.new_page()
        _grid(pg)
        tab = tmp / "linetable.pdf"
        doc.save(tab)
        doc.close()
        st = fc.source_figure_regions(tab)
        check("a ruled table drawn with lines clusters (perpendiculars anchor) and is vetoed AS A TABLE, not reported",
              st["pages"] == {} and st["zero_area_paths_clustered"] == 11 and st["vetoed_table_regions"] == 1
              and st["table_vetoes_disqualified"] == 0, f"{st['pages']} clustered={st['zero_area_paths_clustered']} vetoed={st['vetoed_table_regions']}")

        # 40 — the same grid with a DIAGRAM over it (a circle and two diagonals): find_tables still calls it a table,
        # the cluster's curves and diagonals disqualify the veto, the region is REPORTED (Cyb p.42's mechanism)
        doc = pymupdf.open()
        pg = doc.new_page()
        _grid(pg)
        pg.draw_circle(pymupdf.Point(280, 175), 60, color=(0, 0, 0))
        pg.draw_line(pymupdf.Point(100, 100), pymupdf.Point(460, 250), color=(0, 0, 0))
        pg.draw_line(pymupdf.Point(100, 250), pymupdf.Point(460, 100), color=(0, 0, 0))
        dia = tmp / "diagram-over-grid.pdf"
        doc.save(dia)
        doc.close()
        sd = fc.source_figure_regions(dia)
        check("the table veto is DISQUALIFIED on a cluster with curves and diagonals: the diagram over a grid is reported",
              1 in sd["pages"] and sd["table_vetoes_disqualified"] == 1 and sd["vetoed_table_regions"] == 0,
              f"{sd['pages']} disq={sd['table_vetoes_disqualified']} vetoed={sd['vetoed_table_regions']}")
        sdoff = fc.source_figure_regions(dia, lv=fc.levers(text="table_max_nonrect=1000000")["values"])
        check("NEGATIVE CONTROL: with the disqualifier's lever at its ceiling the S104 table veto swallows the diagram again",
              sdoff["pages"] == {} and sdoff["vetoed_table_regions"] == 1 and sdoff["table_vetoes_disqualified"] == 0,
              f"{sdoff['pages']} vetoed={sdoff['vetoed_table_regions']}")

        # 41 — the helper's own arithmetic: bullets (2 pt circles) are not curves; a 4 pt diagonal is; the report names
        # the three E25 levers with their effective values
        doc = pymupdf.open()
        pg = doc.new_page()
        for k in range(12):
            pg.draw_circle(pymupdf.Point(110, 120 + 14 * k), 1.2, color=(0, 0, 0), fill=(0, 0, 0))   # a bullet column
        bul = tmp / "bullets.pdf"
        doc.save(bul)
        doc.close()
        dbul = pymupdf.open(bul)
        nb = fc._nonrect_items(dbul[0].get_drawings(), (0, 0, 612, 792), fc.NONRECT_MIN_SPAN_PT)
        dbul.close()
        ddia = pymupdf.open(dia)
        nd = fc._nonrect_items(ddia[0].get_drawings(), (0, 0, 612, 792), fc.NONRECT_MIN_SPAN_PT)
        ddia.close()
        check("_nonrect_items: twelve bullet glyphs count 0 (below the span); a circle + two diagonals count >= 3",
              nb == 0 and nd >= 3, f"bullets={nb} diagram={nd}")
        rep25 = fc.coverage(dia, _bundle(tmp, [], "e25"), lv=fc.levers(text="table_max_nonrect=7\nzero_area_min_len_pt=2.5")["values"])["conditions"]
        check("LEVER: the report states the three E25 levers' EFFECTIVE values",
              rep25["veto_table_max_nonrect"] == 7 and rep25["zero_area_min_len_pt"] == 2.5 and rep25["nonrect_min_span_pt"] == fc.NONRECT_MIN_SPAN_PT,
              str({k: rep25[k] for k in ("veto_table_max_nonrect", "zero_area_min_len_pt", "nonrect_min_span_pt")}))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"==== figure_coverage selftest: {PASS}/{TOTAL} ====")
    return 0 if PASS == TOTAL else 1


if __name__ == "__main__":
    raise SystemExit(main())
