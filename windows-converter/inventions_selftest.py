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
print("==== inventions selftest: %d/%d ====" % (ok, n))
sys.exit(0 if ok == n else 1)
