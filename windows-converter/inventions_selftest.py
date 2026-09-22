# -*- coding: utf-8 -*-
"""inventions_selftest.py — the tripwires for fidelity_audit.audit_inventions (S209 B35, report-only). Hermetic: witness pages
as strings, blocks as dicts — no PDF, no pipeline. Each case violates the property its rule stands for: a clean page counts
0 invented and 0 lost; a planted invented word is counted with its specimen and its page; the witness's word the blocks lack
counts as lost, never as invented; a page with no blocks is not measured (pages_measured says so; the ratio's base is
Marker's words, never the witness's); an html entity is not a word; a short token (< 3 letters) and a number are not words;
the scan lane names its meaning as disagreement; no blocks at all → a measured zero over zero reads None, not 0.
S211 LANE B adds two more tripwires, also for audit_numbers: a missing figure inside a Figure/Picture block's own box is a
chart's axis tick (missing_in_figures), not a dropped table figure (missing) — the fixture PDF for this one IS drawn here by
pymupdf (a page with a boxed chart tick), same pattern as figure_text_selftest.py, and saved to a temp path; a lost witness
word that is a line-end fragment Marker correctly rejoined with the next witness word is named apart (lost_hyphen_joined),
lost_total keeping its old meaning. Prints `==== inventions selftest: N/N ====`, exit 0 green · 1 red."""
import os
import sys
import tempfile

import fitz

import fidelity_audit as fa

ok = n = 0


def case(name, cond, detail=""):
    global ok, n
    n += 1
    ok += 1 if cond else 0
    print("  [%d] %s %s%s" % (n, "ok " if cond else "RED", name, ("  <- " + str(detail)[:160]) if (detail and not cond) else ""))


def block(page, text):
    return {"page": page, "block_type": "Text", "html": "<p>%s</p>" % text}


# the fixtures' pages are one sentence each — under the audit's PAGE_MIN_WORDS (15), the line survival draws for a near-blank
# witness; cases 1–9 test the arithmetic, so the line is lowered to 1 for them and restored for case 10, which tests the line
_SAVED_MIN = fa.PAGE_MIN_WORDS
fa.PAGE_MIN_WORDS = 1
W1 = "The regulator can block only as much disturbance as it has variety to match."
W2 = "TLAC leverage ratio was 4.4 per cent in the third quarter of 2026."
# 1 · a clean page: 0 invented, 0 lost
r = fa.audit_inventions([W1, W2], [block(0, W1), block(1, W2)])
case("two clean pages count 0 invented / 0 lost, ratio 0.0, both measured",
     r["invented_total"] == 0 and r["lost_total"] == 0 and r["invented_ratio"] == 0.0 and r["pages_measured"] == 2 and r["pages_with_inventions"] == 0, r)
# 2 · a planted invention on page 2, with its specimen and page
r = fa.audit_inventions([W1, W2], [block(0, W1), block(1, "TLAC loverage satio was 4.4 per cent in the third guarter of 2026.")])
w = r["worst"][0] if r["worst"] else {}
case("three invented words on page 2 are counted with their specimens; page 1 clean",
     r["invented_total"] == 3 and r["pages_with_inventions"] == 1 and w.get("page") == 2 and set(w.get("specimens", [])) == {"loverage", "satio", "guarter"}, r)
case("the three replaced words read as lost on the same page (survival's view), not as invented",
     w.get("lost") == 3 and r["lost_total"] == 3, w)
# 3 · a page with no blocks is not measured; the ratio's base is Marker's words
r = fa.audit_inventions([W1, W2, "A third page the converter dropped entirely."], [block(0, W1), block(1, W2)])
case("a witness page with no blocks is not measured (2 of 3) and adds nothing to the base (19 Marker words)", r["pages_measured"] == 2 and r["marker_words_total"] == 19, r)
# 4 · an entity is not a word; short tokens and numbers are not words
r = fa.audit_inventions(["Fees &amp; commissions of 12 per cent."], [block(0, "Fees &amp; commissions of 12 per cent.")])
case("an html entity, a number and a 2-letter token are not words on either side (Fees, commissions, per, cent = 4)", r["invented_total"] == 0 and r["marker_words_total"] == 4, r)
# 5 · the scan lane's meaning is disagreement
r = fa.audit_inventions([W1], [block(0, W1)], kind="agreement")
case("the scan lane names its number disagreement, not invention", "disagreement" in r["meaning"], r["meaning"])
# 6 · no blocks at all: None, never 0
r = fa.audit_inventions([W1, W2], [])
case("no blocks → pages_measured 0 and invented_ratio None (not measured, never 0)", r["pages_measured"] == 0 and r["invented_ratio"] is None, r)
# 7 · audit_convert without blocks leaves the key None (not measured), never a zero-shaped block
try:
    import inspect
    sig = inspect.signature(fa.audit_convert)
    case("audit_convert takes `blocks` (default None → the key reads None, said in the block)", "blocks" in sig.parameters and sig.parameters["blocks"].default is None, str(sig))
except Exception as e:  # noqa: BLE001
    case("audit_convert takes `blocks`", False, e)
# 9 · the layer's line-end hyphenation is joined before counting: a rejoined word is neither invented nor lost
r = fa.audit_inventions(["The amalga-\nmation of the two banks was approved by the regu-\nlator in the third quarter."],
                        [block(0, "The amalgamation of the two banks was approved by the regulator in the third quarter.")])
case("a word the layer broke at a line end (amalga-/mation) and Marker joined counts 0 invented / 0 lost", r["invented_total"] == 0 and r["lost_total"] == 0, r)
# 10 · a near-blank witness page (a chart baked into an image) is not judged: Marker's OCR of the picture is not garble
fa.PAGE_MIN_WORDS = _SAVED_MIN          # the audit's real line (15) for this case
chart = " ".join(["billion over years infrastructure starting housing defence transit"] * 10)
W3 = W1 + " " + W2                     # 19 words — a real page above the line; page 2 is a chart with a 2-word witness
r = fa.audit_inventions([W3, "Figure 2.3"], [block(0, W3), block(1, chart)])
case("a witness page under PAGE_MIN_WORDS is counted apart (pages_witness_blank 1, its Marker words noted) and adds 0 inventions",
     r["pages_witness_blank"] == 1 and r["blank_marker_words"] == 80 and r["invented_total"] == 0 and r["pages_measured"] == 1, r)
# 11 · S209 E12 (Waterloo): an equation Marker wrote as LaTeX inside <math> is neither invented words nor lost words —
# the commands are counted apart; the prose beside it is judged as before
EQ = ("<p>The closed loop response of the drive follows from the plant model and the compensator gain</p>"
      "<p block-type=\"Equation\"><math display=\"block\">\\hat{\\boldsymbol{\\theta}} = \\frac{1}{Js + B} \\begin{bmatrix} a \\\\ b \\end{bmatrix}</math></p>"
      "<p>and the steady state error vanishes for a step in the reference signal</p>")
WIT_EQ = "The closed loop response of the drive follows from the plant model and the compensator gain and the steady state error vanishes for a step in the reference signal"
r = fa.audit_inventions([WIT_EQ], [{"page": 0, "html": EQ}])
case("an equation inside <math> counts 0 invented and 0 lost; its six commands are latex_commands",
     r["invented_total"] == 0 and r["lost_total"] == 0 and r["latex_commands"] == 6 and r["pages_measured"] == 1, r)
# 12 · S209 E13 (SYM-143, Stanford CIFE p.32): one invented word written many times where the layer draws check marks — a
# recogniser's one word for a glyph — reads as its OWN class (`repeated`: the word, its count, its page) beside invented_total,
# which still counts every copy; a word under REPEAT_MIN copies is an ordinary invention and no repeat
WIT_CK = "Type of Project Delivery Method Project Size Case Projects Regional Office Building Washington Jackson Courthouse Mississippi Samsung Fab Facility Korea Camino Medical Campus Mountain View"
CK = ("<table><tr><td>Type of Project Delivery Method Project Size</td></tr><tr><td>Regional Office Building Washington</td>"
      "<td>" + " ".join(["second"] * 60) + "</td></tr><tr><td>Jackson Courthouse Mississippi</td><td>garble " + " ".join(["mark"] * 5) + "</td></tr></table>")
r = fa.audit_inventions([WIT_CK], [{"page": 0, "html": CK}])
case("`second` × 60 on one page reads as one repeat (word, count 60, page 1) with repeated_total 60; the 6 other inventions are no repeat; invented_total counts every copy",
     r["repeated"] == [{"page": 1, "word": "second", "count": 60}] and r["repeated_total"] == 60 and r["invented_total"] == 66
     and r["repeat_min"] == fa.REPEAT_MIN and r["worst"][0]["specimens"][0] == "second", r)
# 13 · S209 E13 (SYM-146, MIT's Real Analysis notes): the layer's LIGATURE glyphs (deﬁnition, ﬁnite, coeﬃcients — a LaTeX
# typesetting) against Marker's plain letters are neither invented nor lost words; a real invention beside them still counts
WIT_LIG = ("The deﬁnition of a ﬁnite sequence with real coeﬃcients follows from the ﬁrst chapter and the "
           "reﬁnement of the partition is diﬀerentiable on the closed interval of the real line")
LIG = ("<p>The definition of a finite sequence with real coefficients follows from the first chapter and the refinement of the "
       "partition is differentiable on the closed interval of the real line garble</p>")
r = fa.audit_inventions([WIT_LIG], [{"page": 0, "html": LIG}])
case("ligature glyphs in the layer (ﬁ ﬃ ﬀ) against Marker's plain letters count 0 invented and 0 lost; the one real invention counts",
     r["invented_total"] == 1 and r["lost_total"] == 0 and r["worst"][0]["specimens"] == ["garble"], r)
# 14 · S209 E14 (B40 BUILT): every invented word falls in one of four classes — JOINED (two neighbouring layer words run
# together), FRAGMENT (a piece of a lost word), DROPPED LETTER (one letter off a lost word — SYM-148), GARBLE (none of these)
WIT_CL = ("The electronics and the credentials of the field engineers were checked against the register of the province "
          "before the works began on the northern section of the line in the spring")
CL = ("<p>The electronicsand the cred of the feld engineers were checked against the register of the province "
      "before the works began on the northern section of the line in the spring xqzv</p>")
r = fa.audit_inventions([WIT_CL], [{"page": 0, "html": CL}])
case("the four classes: `electronicsand` joined, `cred` a fragment of `credentials`, `feld` a dropped letter of `field`, `xqzv` garble — one each, with specimens",
     r["classes"] == {"joined": 1, "fragment": 1, "dropped_letter": 1, "garble": 1} and r["invented_total"] == 4
     and r["class_specimens"]["dropped_letter"] == [{"page": 1, "word": "feld", "count": 1}]
     and r["class_specimens"]["joined"][0]["word"] == "electronicsand" and r["class_specimens"]["fragment"][0]["word"] == "cred", r)
case("`_one_edit`: a dropped, an added and a changed letter are one edit; two edits and equal words are not",
     fa._one_edit("feld", "field") and fa._one_edit("fieeld", "field") and fa._one_edit("fiend", "field")
     and not fa._one_edit("fld", "field") and not fa._one_edit("field", "field"), "")
# 16 · S210 E1 (SYM-147, NBC p.57): THE DUPLICATED-FIGURE TELL — a row's figures moved onto the row above leave every number
# on the page (survival sees no loss) but Marker carries a figure MORE often than the layer; the layer's 63,242 that Marker
# wrote as `62 242` (not a number token) reads missing; a page whose numbers match reads 0 / 0
LAY_N = ("Securities loaned 63,242 63,242 63,242 63,242 Derivative financial instruments 12,390 12,390 Other 1,040 13,010 "
         "Total assets 2,015,000 and the year 2026 in the heading")
MK_N = ("<table><tr><td>Securities loaned</td><td>62 242</td><td>62 242</td><td>62 242</td><td>62 242</td></tr>"
        "<tr><td>Derivative financial instruments</td><td>12,390</td><td>12,390</td><td>63,242</td><td>63,242 15,810</td></tr>"
        "<tr><td>Other</td><td>1,040</td><td>1,040</td><td>1,040</td><td>13,010</td></tr><tr><td>Total assets</td><td>2,015,000</td></tr></table>")
r = fa.audit_numbers([LAY_N, "A page with 4,321 and 9,876"], [{"page": 0, "html": MK_N}, {"page": 1, "html": "<p>4,321 and 9,876 again</p>"}])
case("audit_numbers: p.1 reads extra 3 (1,040 twice over, 15,810 once), missing 2 (two of the four 63,242 — the OCR'd `62 242` is no token) and missing_years 1 (the heading's 2026, counted apart); p.2 matches; worst names p.1 first",
     r["pages_measured"] == 2 and r["extra_total"] == 3 and r["missing_total"] == 2 and r["missing_years"] == 1 and r["pages_with_extra"] == 1
     and r["worst"][0]["page"] == 1 and r["worst"][0]["specimens"][0] == "1,040", r)
r0 = fa.audit_numbers(["no figures on this page at all"], [{"page": 0, "html": "<p>none here either</p>"}])
case("audit_numbers: a page without number tokens on either side reads 0 / 0 and no worst row", r0["extra_total"] == 0 and r0["missing_total"] == 0 and r0["worst"] == [], r0)
# 18 · S210 E1 (B40's fifth shape, UofT's contents pages): a label glued to its page number across a dot leader —
# `Acknowledgements ........ ix` → `acknowledgementsix` — is JOINED, though `ix` is no word and the adjacent-pair test is blind
WIT_TOC = ("Table of Contents\nAbstract ................................ iii\nAcknowledgements ........................ ix\n"
           "List of Figures ......................... vii\nChapter One Introduction ................ 1\nMethodology ............................. 42\n"
           "The study examined the practices of the participants across the provinces of the country")
TOC = ("<p>Table of Contents Abstractiii Acknowledgementsix List of Figuresvii Chapter One Introduction1 Methodology42 "
       "The study examined the practices of the participants across the provinces of the country</p>")
r = fa.audit_inventions([WIT_TOC], [{"page": 0, "html": TOC}])
case("a contents page's labels glued to roman or arabic page numbers across dot leaders read as JOINED (acknowledgementsix, abstractiii, figuresvii), not garble",
     r["classes"]["joined"] == 3 and r["classes"]["garble"] == 0 and r["classes"]["fragment"] == 0
     and sorted(s["word"] for s in r["class_specimens"]["joined"]) == ["abstractiii", "acknowledgementsix", "figuresvii"], r)
# 19 · S210 E2 (SYM-154's next cut — Scotia Q3 p.51, the second `Secured funding` row dropped whole from a rendered table): a page
# whose missing figures reach NUMBERS_MISSING_MIN enters `worst` on its missing side alone, and the layer's rows that lost them are
# NAMED — the label before the first figure on each line, most figures lost first; a page under the floor stays out
LAY_ROWS = ("T34 Wholesale funding\nSecured funding 4,763 10,540 8,310\nUnsecured funding 1,200 2,300\nTotal 5,963 12,840 8,310")
MK_ROWS = "<table><tr><td>Unsecured funding</td><td>1,200</td><td>2,300</td></tr><tr><td>Total</td><td>5,963</td><td>12,840</td><td>8,310</td></tr></table>"
r = fa.audit_numbers([LAY_ROWS, "Another page 7,777 and 8,888"], [{"page": 0, "html": MK_ROWS}, {"page": 1, "html": "<p>7,777 and 8,888</p>"}])
case("audit_numbers: a page losing three figures enters worst on its missing side alone (extra 0), names the row `Secured funding` with "
     "3 figures, and counts pages_with_missing 1; the page with nothing lost stays out",
     r["extra_total"] == 0 and r["missing_total"] == 3 and r["pages_with_missing"] == 1 and r["pages_with_extra"] == 0
     and len(r["worst"]) == 1 and r["worst"][0]["page"] == 1 and r["worst"][0]["missing"] == 3
     and r["worst"][0]["missing_rows"] == [{"row": "Secured funding", "figures": 3}], r)
r2 = fa.audit_numbers(["Only two lost 1,111 2,222 here"], [{"page": 0, "html": "<p>nothing</p>"}])
case("audit_numbers: two missing figures stay under NUMBERS_MISSING_MIN — no worst row, pages_with_missing 0",
     r2["missing_total"] == 2 and r2["pages_with_missing"] == 0 and r2["worst"] == [], r2)
# 22 · S210 E5 (McGill-2: the numbers' worst pages were figure pages Marker rightly OCR'd, their plotted digits read as extra figures):
# each worst page says whether Marker OCR'd it, from the blocks record's extraction.pages_surya — None when no list was given
r_ocr = fa.audit_numbers([LAY_ROWS, "A chart page 1,111 2,222", "A chart page 1,111 2,222 and a table 9,999"],
                         [{"page": 0, "html": MK_ROWS}, {"page": 1, "html": "<p>1,111 1,111 2,222 2,222 1,111</p>"}, {"page": 2, "html": "<p>1,111 2,222 9,999 9,999 9,999 9,999</p>"}],
                         None, [2])
by_page = {w["page"]: w for w in r_ocr["worst"]}
case("audit_numbers: a worst page in the OCR'd list reads ocr True, a worst page outside it False (the OCR'd chart's extra digits told from a layer page's)",
     by_page[2]["ocr"] is True and by_page[3]["ocr"] is False and by_page[1]["ocr"] is False and by_page[2]["extra"] == 3 and by_page[3]["extra"] == 3, r_ocr["worst"])
r_none = fa.audit_numbers([LAY_ROWS], [{"page": 0, "html": MK_ROWS}])
case("audit_numbers: with no OCR'd-page list the worst page's ocr reads None (UNREAD), never False",
     r_none["worst"] and r_none["worst"][0]["ocr"] is None, r_none["worst"])
case("_row_label: the words before the first figure, at most six; empty when the line opens with a figure",
     fa._row_label("Secured funding 4,763 10,540") == "Secured funding" and fa._row_label("4,763 first") == ""
     and fa._row_label("a b c d e f g h 1,000") == "a b c d e f", None)
# 24 · S211 LANE B (RBC p.41: a bar chart's axis ticks — 100,000 / 150,000 / 200,000 / 250,000 — sit inside the chart's own
# Figure box, printed beside a table on the same y-bands): a missing figure whose OWN word sits inside a Figure/Picture
# block's bbox is a chart's tick, moved out of `missing` into `missing_in_figures`. Fixture PDF drawn here (never read from
# disk), same pattern as figure_text_selftest.py's page_with_chart — the geometry has to be real for a containment test.
_FIG_BOX = [72, 100, 400, 300]
_numfig_dir = tempfile.mkdtemp(prefix="fp-numfig-")
_numfig_doc = fitz.open()
_numfig_page = _numfig_doc.new_page(width=612, height=792)
_numfig_page.draw_rect(fitz.Rect(*_FIG_BOX), width=0.5)
_numfig_page.insert_text((_FIG_BOX[0] + 10, _FIG_BOX[1] + 20), "100,000", fontsize=9)
_numfig_pdf = os.path.join(_numfig_dir, "chart.pdf")
_numfig_doc.save(_numfig_pdf)
_numfig_raw = ["100,000 sits beside the chart, on the page but in no table row"]
r_fig1 = fa.audit_numbers(_numfig_raw, [{"page": 0, "block_type": "Figure", "bbox": _FIG_BOX, "html": ""}], pdf_path=_numfig_pdf)
case("audit_numbers: a missing figure inside a Figure box reads missing_in_figures_total 1 and missing_total 0 "
     "(the negative control below: before this cut, and whenever the box misses it, it read missing 1)",
     r_fig1["missing_total"] == 0 and r_fig1["missing_in_figures_total"] == 1, r_fig1)
# 25 · negative control for case 24: the SAME token, the SAME page, but the block's Figure box sits elsewhere on the page —
# the split must not fire just because a Figure/Picture block exists somewhere; only real containment moves it
r_fig2 = fa.audit_numbers(_numfig_raw, [{"page": 0, "block_type": "Figure", "bbox": [72, 500, 400, 600], "html": ""}], pdf_path=_numfig_pdf)
case("audit_numbers: the same figure outside any box stays a genuine missing figure (missing_total 1, missing_in_figures_total 0)",
     r_fig2["missing_total"] == 1 and r_fig2["missing_in_figures_total"] == 0, r_fig2)
# 26 · negative control: no Figure/Picture box anywhere in blocks — the split cannot be judged at all, so it reads UNREAD
# (None), never a guessed 0, and missing_total reads exactly what it would without this cut (1)
r_fig3 = fa.audit_numbers(_numfig_raw, [{"page": 0, "block_type": "Text", "html": ""}], pdf_path=_numfig_pdf)
case("audit_numbers: no Figure/Picture box in blocks reads missing_in_figures_total None (UNREAD), missing_total unchanged at 1",
     r_fig3["missing_total"] == 1 and r_fig3["missing_in_figures_total"] is None, r_fig3)
# 26b · S211 E3 (RBC p.122: the layout model boxed the whole capital table — Credit / Market / Operational, 19 figures — as ONE
# Figure, and containment alone read them as a chart's ticks; a conversion that boxes every table as a picture would read 0
# missing): a figure inside a box on a band that OPENS WITH WORDS INSIDE THE SAME BOX is a labelled row (a mis-boxed table
# or a chart's labelled bar) — it STAYS under missing and is counted apart as missing_in_figures_labelled. Fixture: the box
# holds `Credit 2,491,090` on one band (labelled) and a bare `150,000` on another (a tick).
_LAB_BOX = [72, 100, 400, 300]
_lab_dir = tempfile.mkdtemp(prefix="fp-numfig-lab-")
_lab_doc = fitz.open()
_lab_page = _lab_doc.new_page(width=612, height=792)
_lab_page.draw_rect(fitz.Rect(*_LAB_BOX), width=0.5)
_lab_page.insert_text((_LAB_BOX[0] + 10, _LAB_BOX[1] + 20), "Credit 2,491,090 590,306 61,432", fontsize=9)   # a labelled row: 3 figures
_lab_page.insert_text((_LAB_BOX[0] + 10, _LAB_BOX[1] + 60), "150,000", fontsize=9)                          # a tick on its own band
_lab_pdf = os.path.join(_lab_dir, "mixed.pdf")
_lab_doc.save(_lab_pdf)
_lab_raw = ["Credit 2,491,090 590,306 61,432 on a labelled band inside the box; 150,000 alone on its band inside the box"]
r_lab = fa.audit_numbers(_lab_raw, [{"page": 0, "block_type": "Figure", "bbox": _LAB_BOX, "html": ""}], pdf_path=_lab_pdf)
case("audit_numbers: inside one Figure box, the labelled row `Credit 2,491,090 590,306 61,432` STAYS missing (missing_total 3, "
     "missing_in_figures_labelled 3, the row named `Credit`); the bare `150,000` on its own band is the tick (missing_in_figures 1) "
     "— the negative control: containment alone read missing_total 0",
     r_lab["missing_total"] == 3 and r_lab["missing_in_figures_total"] == 1 and r_lab["missing_in_figures_labelled_total"] == 3
     and r_lab["worst"][0]["missing_in_figures_labelled"] == 3 and r_lab["worst"][0]["missing_in_figures"] == 1
     and r_lab["worst"][0]["missing_rows"][0] == {"row": "Credit", "figures": 3}, r_lab)
# 26c · the p.41 shape, the case that must NOT change: the chart's tick shares its band with a table row label printed OUTSIDE
# the box (the table beside the chart) — the label is not the chart's, so the tick stays a tick (missing_in_figures 1, labelled 0)
_beside_dir = tempfile.mkdtemp(prefix="fp-numfig-beside-")
_beside_doc = fitz.open()
_beside_page = _beside_doc.new_page(width=612, height=792)
_CHART_BOX = [300, 100, 560, 300]
_beside_page.draw_rect(fitz.Rect(*_CHART_BOX), width=0.5)
_beside_page.insert_text((72, 120), "Total revenue 12,345", fontsize=9)            # the table's row, outside the box
_beside_page.insert_text((_CHART_BOX[0] + 10, 120), "250,000", fontsize=9)          # the chart's tick, same band, inside
_beside_pdf = os.path.join(_beside_dir, "beside.pdf")
_beside_doc.save(_beside_pdf)
_beside_raw = ["Total revenue 12,345 250,000 on one band, the chart beside the table"]
r_beside = fa.audit_numbers(_beside_raw, [{"page": 0, "block_type": "Figure", "bbox": _CHART_BOX, "html": "<p>Total revenue 12,345</p>"}],
                            pdf_path=_beside_pdf)
case("audit_numbers: a tick whose band carries the TABLE's row label outside the chart box stays a tick (missing_in_figures 1, "
     "labelled 0, missing_total 0) — the label must lie inside the box to count",
     r_beside["missing_total"] == 0 and r_beside["missing_in_figures_total"] == 1 and r_beside["missing_in_figures_labelled_total"] == 0, r_beside)
# 27 · S211 LANE B (Bill C-288: `circons` + `tance` where Marker correctly wrote `circonstance`) — a lost witness word that
# is the LAST word on its raw line, with nothing (or a hyphen / soft hyphen) trailing it, and that joins with the very next
# witness word into a word Marker's blocks DO carry, is not a real omission: lost_hyphen_joined names it, lost_total keeps
# counting it (unchanged meaning), lost_total_excl_joined is the honest rest
WIT_FRAG = ("The situation depends heavily on the circons\n"
            "tance of the case and the outcome remains uncertain for every party involved in the proceedings before the "
            "tribunal reaches its final decision")
MK_FRAG = ("The situation depends heavily on the circonstance of the case and the outcome remains uncertain for every party "
           "involved in the proceedings before the tribunal reaches its final decision")
r_frag = fa.audit_inventions([WIT_FRAG], [{"page": 0, "block_type": "Text", "html": "<p>%s</p>" % MK_FRAG}])
case("audit_inventions: a line-end fragment pair Marker rejoined reads lost_hyphen_joined 2 (BOTH halves — S211 E3), lost_total "
     "unchanged (2), lost_total_excl_joined 0 (nothing of the pair is lost), one specimen per pair",
     r_frag["lost_total"] == 2 and r_frag["lost_hyphen_joined"] == 2 and r_frag["lost_total_excl_joined"] == 0
     and r_frag["lost_hyphen_joined_specimens"] == [{"page": 1, "fragment": "circons", "joined_with": "tance", "joined": "circonstance"}], r_frag)
# 28 · negative control for case 27: a genuine lost word (Marker simply dropped it, mid-line, no line-end break to rejoin)
# must not be swept into lost_hyphen_joined
WIT_GENUINE = ("The regulator issued a warning about the pipeline safety standards across the northern region and the "
               "committee reviewed the submission carefully before reaching its final determination for the record")
MK_GENUINE = ("The regulator issued a warning about the pipeline standards across the northern region and the committee "
              "reviewed the submission carefully before reaching its final determination for the record")
r_genuine = fa.audit_inventions([WIT_GENUINE], [{"page": 0, "block_type": "Text", "html": "<p>%s</p>" % MK_GENUINE}])
case("audit_inventions: a genuine mid-line omission (`safety` simply dropped) reads lost_hyphen_joined 0, lost_total 1, "
     "lost_total_excl_joined 1 (nothing to subtract)",
     r_genuine["lost_total"] == 1 and r_genuine["lost_hyphen_joined"] == 0 and r_genuine["lost_total_excl_joined"] == 1, r_genuine)
# 29 · S211 E3 (the invented side of the same join — Bill C-30 ~160c: 167 invented on the layer path, 27 on the OCR path):
# Marker's `circonstance` is absent from a witness holding `circons` + `tance`, so it counts invented (class joined) — and
# invented_hyphen_joined names it apart; invented_total keeps its meaning; invented_total_excl_joined is the honest rest.
# Negative control: `electronicsand` (case 14) is a join too, but MID-line — the layer never wrapped there — so it stays 0.
r_cl = fa.audit_inventions([WIT_CL], [{"page": 0, "html": CL}])
case("audit_inventions: the rejoined pair's Marker word reads invented_total 1 (class joined), invented_hyphen_joined 1, "
     "invented_total_excl_joined 0; a mid-line join (`electronicsand`) reads invented_hyphen_joined 0 and excl 4; a genuine loss 0",
     r_frag["invented_total"] == 1 and r_frag["classes"]["joined"] == 1 and r_frag["invented_hyphen_joined"] == 1
     and r_frag["invented_total_excl_joined"] == 0
     and r_cl["invented_total"] == 4 and r_cl["invented_hyphen_joined"] == 0 and r_cl["invented_total_excl_joined"] == 4
     and r_genuine["invented_total"] == 0 and r_genuine["invented_hyphen_joined"] == 0,
     (r_frag["invented_total"], r_frag["classes"], r_frag["invented_hyphen_joined"], r_cl["invented_hyphen_joined"], r_genuine["invented_total"]))

# 30 · S211 E3 (the accounting's mechanism reading — the PBO's `Robert-Ouimet`, the MIT CIO report's `automation-vulnerable`):
# a GENUINE compound hyphen at a line wrap — the witness dehyphenation fuses it (`robertouimet`), Marker rightly keeps the
# hyphen (`robert`, `ouimet`) — read 1 lost + 2 invented where nothing was lost. Counted apart on both sides; the honest
# rests net of it; the specimens a reader sees net of it. Negative control: the same name NOT at a line wrap (`Robert
# Ouimet` printed as two words) counts nothing under the compound keys.
WIT_CMP = ("The report was tabled by Robert-\nOuimet before the committee adjourned for the season and every member present "
           "signed the record of the proceedings before leaving the chamber for the recess")
MK_CMP = ("The report was tabled by Robert-Ouimet before the committee adjourned for the season and every member present "
          "signed the record of the proceedings before leaving the chamber for the recess")
r_cmp = fa.audit_inventions([WIT_CMP], [{"page": 0, "block_type": "Text", "html": "<p>%s</p>" % MK_CMP}])
case("audit_inventions: a genuine compound hyphen at a line wrap reads lost_total 1 / invented_total 2 (raw, unchanged meaning), "
     "lost_compound_hyphen 1, invented_compound_hyphen 2, both honest rests 0, worst[] specimens empty",
     r_cmp["lost_total"] == 1 and r_cmp["invented_total"] == 2 and r_cmp["lost_compound_hyphen"] == 1 and r_cmp["invented_compound_hyphen"] == 2
     and r_cmp["lost_total_excl_joined"] == 0 and r_cmp["invented_total_excl_joined"] == 0
     and r_cmp["lost_compound_hyphen_specimens"] == [{"page": 1, "fused": "robertouimet", "marker_words": ["robert", "ouimet"]}]
     and r_cmp["worst"][0]["specimens"] == [] and r_cmp["worst"][0]["invented_net"] == 0 and r_cmp["worst"][0]["lost_net"] == 0, r_cmp)
WIT_CMP2 = WIT_CMP.replace("Robert-\nOuimet", "Robert\nOuimet")
r_cmp2 = fa.audit_inventions([WIT_CMP2], [{"page": 0, "block_type": "Text", "html": "<p>%s</p>" % MK_CMP.replace("Robert-Ouimet", "Robert Ouimet")}])
case("audit_inventions (negative control): the same two words with no hyphen read 0 lost, 0 invented, 0 under the compound keys",
     r_cmp2["lost_total"] == 0 and r_cmp2["invented_total"] == 0 and r_cmp2["lost_compound_hyphen"] == 0 and r_cmp2["invented_compound_hyphen"] == 0, r_cmp2)
# 31 · S211 E3 (Wiener's Cybernetics: worst[] named words the source spells correctly, split only by its soft hyphens): the
# rejoined pair's word is not a specimen; the per-page net counts read 0
case("audit_inventions: the rejoined pair page (case 27) shows specimens [] and invented_net 0 / lost_net 0 beside its raw 1 / 2",
     r_frag["worst"][0]["specimens"] == [] and r_frag["worst"][0]["invented_net"] == 0 and r_frag["worst"][0]["lost_net"] == 0
     and r_frag["worst"][0]["invented"] == 1 and r_frag["worst"][0]["lost"] == 2, r_frag["worst"])
# 32 · S211 E3 (McGill-1 p.188: `<i>VLSI 2023</i>,`): an inline text tag closing between a figure and its comma, stripped to a
# space, let _NUM_TOKEN take `2023` where the layer's own `2023,` refuses it — an "extra" figure never there. Inline tags strip
# to nothing; a <sup> footnote mark still strips to a space (never fused onto its figure); <br> is never a `b` tag.
r_tag = fa.audit_numbers(["as shown in VLSI 2023, the result holds"], [{"page": 0, "html": "<p>as shown in <i>VLSI 2023</i>, the result holds</p>"}])
r_sup = fa.audit_numbers(["revenue of 12,345 1 rose"], [{"page": 0, "html": "<p>revenue of 12,345<sup>1</sup> rose</p>"}])
r_br = fa.audit_numbers(["first 12,345 then 67,890"], [{"page": 0, "html": "<p>first 12,345<br>then 67,890</p>"}])
case("audit_numbers: `<i>VLSI 2023</i>,` reads extra 0 (the negative control read extra 1); `12,345<sup>1</sup>` reads extra 0 missing 0 "
     "(no fusing); `12,345<br>then` keeps both figures",
     r_tag["extra_total"] == 0 and r_tag["missing_total"] == 0 and r_sup["extra_total"] == 0 and r_sup["missing_total"] == 0
     and r_br["extra_total"] == 0 and r_br["missing_total"] == 0, (r_tag, r_sup, r_br))
# 33 · S211 E3 (Waterloo's AFM scan, `1000nm`): the page word carries a unit glued to the figure; the missing token is the digits
# alone — the key inside the word must reach the containment test, so the figure inside its own Figure box is a tick
_unit_dir = tempfile.mkdtemp(prefix="fp-numfig-unit-")
_unit_doc = fitz.open()
_unit_page = _unit_doc.new_page(width=612, height=792)
_unit_page.draw_rect(fitz.Rect(*_FIG_BOX), width=0.5)
_unit_page.insert_text((_FIG_BOX[0] + 10, _FIG_BOX[1] + 20), "1000nm", fontsize=9)
_unit_pdf = os.path.join(_unit_dir, "unit.pdf")
_unit_doc.save(_unit_pdf)
r_unit = fa.audit_numbers(["the scale bar reads 1000nm across the image"], [{"page": 0, "block_type": "Figure", "bbox": _FIG_BOX, "html": ""}], pdf_path=_unit_pdf)
case("audit_numbers: a unit-glued figure (`1000nm`) inside its Figure box reads missing_in_figures 1, missing 0 (the negative "
     "control: the verbatim-word key never matched — missing 1)",
     r_unit["missing_total"] == 0 and r_unit["missing_in_figures_total"] == 1, r_unit)

print("==== inventions selftest: %d/%d ====" % (ok, n))
sys.exit(0 if ok == n else 1)
