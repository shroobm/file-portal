# -*- coding: utf-8 -*-
"""inventions_selftest.py — the tripwires for fidelity_audit.audit_inventions (S209 B35, report-only). Hermetic: witness pages
as strings, blocks as dicts — no PDF, no pipeline. Each case violates the property its rule stands for: a clean page counts
0 invented and 0 lost; a planted invented word is counted with its specimen and its page; the witness's word the blocks lack
counts as lost, never as invented; a page with no blocks is not measured (pages_measured says so; the ratio's base is
Marker's words, never the witness's); an html entity is not a word; a short token (< 3 letters) and a number are not words;
the scan lane names its meaning as disagreement; no blocks at all → a measured zero over zero reads None, not 0.
Prints `==== inventions selftest: N/N ====`, exit 0 green · 1 red."""
import sys

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
print("==== inventions selftest: %d/%d ====" % (ok, n))
sys.exit(0 if ok == n else 1)
